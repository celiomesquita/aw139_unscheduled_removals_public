"""Age replacement on an empirical periodic visit calendar, without Monte Carlo."""
import heapq
import math

import numpy as np
from scipy.special import gamma, gammaincc

from a9_renewal import first_event_weights


class CalendarRenewal:
    """Markov-renewal phases on a fixed time grid; exhaustive age breakpoints."""
    def __init__(self, daily, visits, beta, eta, nu, r, weight=1., subdivisions=1,
                 probability_tolerance=1e-10, duration_tolerance=1e-7):
        self.daily = np.asarray(daily, float)
        self.n = len(daily) * subdivisions
        self.step = 1 / subdivisions
        self.increment = np.repeat(self.daily / subdivisions, subdivisions)
        self.visits = np.array(sorted(set(int(v * subdivisions) % self.n for v in visits)), int)
        if (not len(self.visits) or self.n == 0 or beta <= 1 or eta <= 0 or nu < 0 or
                self.increment.min() < 0 or self.increment.sum() <= 0):
            raise ValueError('Static renewal calendar requires ageing, exposure and visits')
        self.beta, self.eta, self.nu, self.r, self.weight = beta, eta, nu, r, weight
        self.rows = []
        self.P = np.zeros((self.n, self.n))
        self.cost, self.duration = np.zeros(self.n), np.zeros(self.n)
        self.mass_error, self.max_tail_probability, self.max_tail_duration = 0., 0., 0.
        self.updates = 0
        for phase in range(self.n):
            # End at a whole number of periods, so the tail-duration bound is explicit.
            periods = 1
            total = self.increment.sum()
            while True:
                elapsed = periods * len(daily)
                exposure = periods * total
                probability = math.exp(-(exposure / eta) ** beta - nu * elapsed)
                if nu:
                    duration_bound = probability / nu
                else:
                    integrated = eta * gamma(1 / beta) * gammaincc(1 / beta, (exposure / eta) ** beta) / beta
                    duration_bound = len(daily) * (probability + integrated / total)
                if probability <= probability_tolerance and duration_bound <= duration_tolerance:
                    break
                periods *= 2
                if periods > 65536:
                    raise ArithmeticError('Static calibration tail could not be bounded')
            increments = np.tile(np.roll(self.increment, -phase), periods)
            clock = np.r_[0., np.cumsum(increments)]
            times = np.arange(len(clock)) * self.step
            u, c, left, right = first_event_weights(times, clock, 0., beta, eta, nu, order=32)
            survival = np.exp(-(clock / eta) ** beta - nu * times)
            error = abs(float((u + c).sum()) - (1 - survival[-1]))
            if error > 1e-7:
                raise ArithmeticError('Static first-event quadrature does not conserve probability')
            self.mass_error = max(self.mass_error, error)
            self.max_tail_probability = max(self.max_tail_probability, probability)
            self.max_tail_duration = max(self.max_tail_duration, duration_bound)
            positions = np.arange(1, len(clock))
            stops = positions[np.isin((phase + positions) % self.n, self.visits)]
            row = dict(phase=phase, clock=clock, survival=survival,
                left=left, right=right, reward=np.r_[0., np.cumsum(r * u + c)],
                moment=np.r_[0., np.cumsum(left * times[:-1] + right * times[1:])],
                stops=stops, cursor=0)
            self.rows.append(row)
            self.replace_row(phase, update_inverse=False)
        self.refactor()

    def refactor(self):
        matrix = np.eye(self.n) - self.P.T + np.ones((self.n, self.n))
        self.inverse = np.linalg.inv(matrix)
        self.stationary = self.inverse @ np.ones(self.n)
        if (np.min(self.stationary) < -1e-8 or
                np.max(np.abs(self.P.T @ self.stationary - self.stationary)) > 1e-7):
            raise ArithmeticError('Static phase distribution is not stationary')

    def replace_row(self, phase, update_inverse=True):
        row = self.rows[phase]
        finite = row['cursor'] < len(row['stops'])
        stop = int(row['stops'][row['cursor']]) if finite else len(row['clock']) - 1
        j = np.arange(stop)
        probability = (np.bincount((phase + j) % self.n, weights=row['left'][:stop], minlength=self.n) +
                       np.bincount((phase + j + 1) % self.n, weights=row['right'][:stop], minlength=self.n))
        survival = row['survival'][stop]
        cost = row['reward'][stop]
        duration = row['moment'][stop]
        if finite:
            probability[(phase + stop) % self.n] += survival
            cost += survival
            duration += stop * self.step * survival
        else:
            # Conditional truncation error is bounded above and recorded.
            mass = probability.sum()
            probability /= mass
            cost, duration = cost / mass, duration / mass
        delta = probability - self.P[phase]
        self.P[phase] = probability
        self.cost[phase], self.duration[phase] = cost, duration
        if update_inverse:
            self.updates += 1
            vector = self.inverse @ delta
            denominator = 1 - vector[phase]
            if abs(denominator) < 1e-8 or self.updates % 128 == 0:
                self.refactor()
            else:
                previous = self.stationary[phase]
                self.inverse += np.outer(vector, self.inverse[phase].copy()) / denominator
                self.stationary += vector * previous / denominator
                if abs(self.stationary.sum() - 1) > 1e-7 or self.stationary.min() < -1e-8:
                    self.refactor()

    def next_breakpoint(self, phase):
        row = self.rows[phase]
        if row['cursor'] >= len(row['stops']):
            return math.inf
        return float(row['clock'][row['stops'][row['cursor']]])

    def extend(self, phase):
        self.rows[phase]['cursor'] += 1
        self.replace_row(phase)

    def rate(self):
        duration = float(self.stationary @ self.duration)
        if duration <= 0:
            raise ArithmeticError('Nonpositive expected renewal duration')
        return self.weight * float(self.stationary @ self.cost) / duration


def exhaustive_threshold(contexts, beta, eta, nu, r, subdivisions=1, calendar_type=CalendarRenewal):
    """Enumerate every breakpoint of the phase-discretised age policy, plus infinity."""
    if beta <= 1:
        return math.inf, dict(reason='nonincreasing_hazard_no_preventive', subdivisions=subdivisions,
                               global_discrete_search=True)
    calendars = []
    zero_threshold_extra = 0.
    omitted_constants = 0
    for context in contexts:
        daily, visits = np.asarray(context['daily'], float), context['visits']
        weight = float(context.get('weight', 1.))
        if not len(visits) or daily.sum() == 0:
            omitted_constants += 1
            if len(visits) and daily.sum() == 0:
                zero_threshold_extra += weight * len(set(visits)) / len(daily)
            continue
        calendars.append(calendar_type(daily, visits, beta, eta, nu, r, weight, subdivisions))
    if not calendars:
        return math.inf, dict(reason='no_informative_initial_visit_calendar',
                               subdivisions=subdivisions, global_discrete_search=True)
    rates = [calendar.rate() for calendar in calendars]
    rate = lambda: sum(rates)
    best_age, best_rate = 0., rate() + zero_threshold_extra
    heap = []
    for i, calendar in enumerate(calendars):
        for phase in range(calendar.n):
            heapq.heappush(heap, (calendar.next_breakpoint(phase), i, phase))
    if zero_threshold_extra and heap[0][0] > 0:
        # The open interval (0, first positive breakpoint] avoids preventive
        # visits in zero-exposure groups without changing other groups' rows.
        candidate = rate()
        if candidate < best_rate - 1e-12:
            best_age, best_rate = float(np.nextafter(0., math.inf)), candidate
    candidates = 1
    while heap:
        age = heap[0][0]
        if not math.isfinite(age):
            break
        changed = set()
        while heap and heap[0][0] == age:
            _, i, phase = heapq.heappop(heap)
            calendars[i].extend(phase)
            changed.add(i)
            heapq.heappush(heap, (calendars[i].next_breakpoint(phase), i, phase))
        for i in changed:
            rates[i] = calendars[i].rate()
        candidate_rate = rate()
        candidates += 1
        if candidate_rate < best_rate - 1e-12:
            best_rate, best_age = candidate_rate, float(np.nextafter(age, math.inf))
    infinity_rate = rate()
    # Deterministic tie preference for fewer interventions.
    if infinity_rate <= best_rate + 1e-12:
        best_age, best_rate = math.inf, infinity_rate
    for calendar in calendars:
        calendar.refactor()
    return best_age, dict(subdivisions=subdivisions, global_discrete_search=True,
        reason='expected_cost_rate_minimum', candidate_breakpoints=candidates,
        expected_rate_variable_groups=best_rate, no_preventive_rate_variable_groups=infinity_rate,
        omitted_threshold_independent_groups=omitted_constants,
        probability_mass_error=max(c.mass_error for c in calendars),
        tail_probability_bound=max(c.max_tail_probability for c in calendars),
        tail_duration_bound=max(c.max_tail_duration for c in calendars))


def calibrate_threshold(contexts, beta, eta, nu, r, max_subdivisions=4, calendar_type=CalendarRenewal):
    if beta <= 1:
        return exhaustive_threshold(contexts, beta, eta, nu, r, calendar_type=calendar_type)
    previous, history = None, []
    for subdivisions in (1, 2, 4):
        if subdivisions > max_subdivisions:
            break
        age, diagnostic = exhaustive_threshold(contexts, beta, eta, nu, r, subdivisions, calendar_type)
        history.append(diagnostic)
        if 'expected_rate_variable_groups' not in diagnostic:
            return age, dict(refinements=history, converged=True)
        value = diagnostic['expected_rate_variable_groups']
        if previous is not None and abs(value - previous) <= 1e-4 + 1e-3 * abs(value):
            return age, dict(refinements=history, converged=True)
        previous = value
    raise ArithmeticError('P1 phase refinement did not meet fixed cost-rate tolerance')
