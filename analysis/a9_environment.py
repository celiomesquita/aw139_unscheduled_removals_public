"""Exogenous clocks and visits; decisions expose only their authorised information."""
import numpy as np
import pandas as pd

from a16_generator import START

EVALUATION_END = pd.Timestamp('2025-12-31')
END_DAY = (EVALUATION_END - START).days
CHANGE_DAY = (pd.Timestamp('2025-01-01') - START).days - 1


class Environment:
    def __init__(self, flights, stoppages, scenario='A', minimum_days=30):
        if scenario not in ('A', 'B-eta', 'B-util', 'B-gradual') or minimum_days not in (30, 60):
            raise ValueError('Unknown A9 scenario or exposure threshold')
        self.scenario, self.minimum_days = scenario, minimum_days
        self.flights = flights[['Aircraft #', 'Flight Date', 'Hours', 'Take Off']].copy()
        dates = pd.to_datetime(self.flights['Flight Date'], format='%d/%m/%Y')
        self.flights = self.flights[dates.between(START, EVALUATION_END)].copy()
        dates = dates.loc[self.flights.index]
        if scenario == 'B-util':
            self.flights.loc[dates.ge('2025-01-01'), ['Hours', 'Take Off']] *= 1.3
        self.aircraft = sorted(flights['Aircraft #'].dropna().unique())
        self.days = pd.date_range(START - pd.Timedelta(days=1), EVALUATION_END)
        frame = self.flights.assign(d=dates)
        self.hours = frame.groupby(['d', 'Aircraft #']).Hours.sum().unstack().reindex(
            index=self.days, columns=self.aircraft).fillna(0.)
        self.known = frame.assign(known=frame.Hours.notna().astype(int)).groupby(
            ['d', 'Aircraft #']).known.sum().unstack().reindex(index=self.days, columns=self.aircraft).fillna(0.)
        self.cumulative = self.hours.cumsum()
        self.first = frame.groupby('Aircraft #').d.min()
        self.stops = {}
        start_dates = pd.to_datetime(stoppages.start)
        for aircraft in self.aircraft:
            self.stops[aircraft] = sorted(set((start_dates[
                stoppages['Aircraft #'].eq(aircraft) & start_dates.between(START, EVALUATION_END)] - START).dt.days))
        # Full first-year period for the explicitly synthetic terminal extension.
        self.period = len(pd.date_range('2024-01-01', '2024-12-31'))

    def date(self, day):
        return START + pd.Timedelta(days=int(day))

    def increment(self, aircraft, day):
        if day < 0:
            raise ValueError('Evaluation cannot borrow auxiliary clock increments')
        if day <= END_DAY:
            return float(self.hours.at[self.date(day), aircraft])
        mapped = (day - END_DAY - 1) % self.period
        value = float(self.hours.at[self.date(mapped), aircraft])
        if self.scenario == 'B-util':
            value *= 1.3
        return value

    def observed_rate(self, aircraft, origin):
        origin = pd.Timestamp(origin)
        first = self.first.get(aircraft)
        if first is None or pd.isna(first):
            return None
        left = max(origin - pd.Timedelta(days=90), first)
        duration = max(0, min(90, (origin - left).days))
        if duration < self.minimum_days:
            return None
        past = pd.date_range(max(left, START), origin - pd.Timedelta(days=1))
        if not len(past) or self.known.loc[past, aircraft].sum() <= 0:
            return None
        return float(self.hours.loc[past, aircraft].sum() / duration)

    def forecast(self, aircraft, origin, length, knowledge, scale):
        if scale == 'calendar':
            return np.ones(length), None
        if knowledge == 'principal':
            rate = self.observed_rate(aircraft, origin)
            return (None, 'unavailable_90d_exposure') if rate is None else (np.full(length, rate), None)
        if knowledge != 'realized_fh':
            raise ValueError('Unknown utilisation information axis')
        first = (pd.Timestamp(origin) - START).days
        return np.array([self.increment(aircraft, first + j) for j in range(length)]), None

    def visits(self, aircraft, cutoff, horizon):
        values = [day for day in self.stops[aircraft] if cutoff < day <= horizon]
        if horizon > END_DAY:
            pattern = [day for day in self.stops[aircraft] if day < self.period]
            offset = END_DAY + 1
            while offset <= horizon:
                values += [offset + day for day in pattern if cutoff < offset + day <= horizon]
                offset += self.period
        return sorted(set(values))

    def age(self, entry, cutoff):
        """Observed rounded birth and realised past clock; no latent fractional age."""
        birth = int(np.ceil(entry['state'].birth))
        observed = any(left <= entry['state'].birth and cutoff <= right
                       for left, right in entry['intervals'])
        if not observed:
            return None
        if entry['scale'] == 'calendar':
            return float(max(0, cutoff - birth))
        return float(self.cumulative.at[self.date(cutoff), entry['aircraft']] -
                     self.cumulative.at[self.date(birth), entry['aircraft']])


def historical_calendars(spells, flights, stoppages, domain, origin):
    """P1 calibration receives only the history available before this origin."""
    origin = pd.Timestamp(origin)
    dates = pd.to_datetime(flights['Flight Date'], format='%d/%m/%Y')
    first = origin - pd.Timedelta(days=365)
    clocks = flights[dates.ge(first) & dates.lt(origin)].copy()
    clocks['d'] = dates.loc[clocks.index]
    observed = spells[spells.att.lt(origin)].copy()
    # Owned synthetic identifier: AUX-P/N-index-aircraft-index-channel-observation-renewal.
    observed['synthetic_channel'] = observed['Serial #'].str.split('-').map(lambda x: '-'.join(x[:4]))
    stops = stoppages.copy()
    stops['d'] = pd.to_datetime(stops.start) - pd.Timedelta(days=365)
    stops = stops[stops.d.ge(first) & stops.d.lt(origin)]
    result, initial_utilisation = {}, {}
    for row in domain.itertuples():
        contexts = []
        for aircraft, group in observed[observed['Part #'].eq(row.pn)].groupby('Aircraft #', sort=True):
            base = aircraft.removesuffix('-AUX')
            visit_days = sorted(set((stops.loc[stops['Aircraft #'].eq(base), 'd'] - first).dt.days))
            g = clocks[clocks['Aircraft #'].eq(aircraft)]
            daily = g.groupby('d').Hours.sum().reindex(pd.date_range(first, periods=365)).fillna(0.).to_numpy()
            if row.scale == 'calendar':
                daily = np.ones(365)
            contexts.append(dict(daily=daily, visits=visit_days,
                                 weight=int(group.synthetic_channel.nunique())))
            if base not in initial_utilisation:
                known = g[g.Hours.notna()]
                if known.empty:
                    initial_utilisation[base] = None
                else:
                    denominator = max(1, (origin - max(first, g.d.min())).days)
                    initial_utilisation[base] = float(known.Hours.sum() / denominator)
        result[row.pn] = contexts
    return result, initial_utilisation
