"""T14 draft adapters: corrected exposure history, original estimators untouched.

Do not run corrected real-data studies or A16 flow 17 before amendment 006 is committed.
"""
import numpy as np
import pandas as pd

from a5_models import Exposure
from a5_validation import Evaluation
from a4_validation import HierarchicalEvaluation


class ObservedExposure(Exposure):
    def __init__(self, flights, minimum_days=30):
        if minimum_days not in (30, 60):
            raise ValueError('Only the prespecified 30/60-day rules are supported')
        super().__init__(flights)
        self.minimum_days = minimum_days
        self.first_record = self.flights.groupby('Aircraft #').d.min()
        self.legacy = Exposure(flights)

    def observed_days(self, origin):
        """Calendar coverage in [origin-90 days, origin), including zero-flight days."""
        origin = pd.Timestamp(origin)
        start = origin - pd.Timedelta(days=90)
        return self.first_record.map(lambda first: max(0, min(90, (origin - max(start, first)).days)))

    def rates(self, clock, origin, field):
        if field not in ('Hours', 'cycles'):
            return super().rates(clock, origin, field)
        cutoff = origin - pd.Timedelta(days=1)
        earlier = cutoff - pd.Timedelta(days=90)
        increment = clock['cum'][field].loc[cutoff] - clock['cum'][field].loc[earlier]
        days = self.observed_days(origin).reindex(increment.index)
        return increment.div(days.where(days.ge(self.minimum_days)))


def exposure_fallback(frame, observed_days, pipeline, minimum_days=30, variant='principal'):
    if pipeline not in ('A5', 'A4'):
        raise ValueError('Unknown fallback contract')
    if variant == 'realized_fh' or frame.empty:
        return frame
    out = frame.copy()
    out['observed_days_90d'] = out.aircraft.map(observed_days)
    out['exposure_available_90d'] = out.observed_days_90d.ge(minimum_days)
    out['exposure_min_days'] = minimum_days
    unavailable = ~out.exposure_available_90d
    for prefix in ('w', 'e'):
        for scale in ('FH', 'takeoffs'):
            name = prefix + '_' + scale
            fallback = out[prefix + '_calendar'] if pipeline == 'A5' else out.baseline
            out.loc[unavailable, name] = fallback[unavailable]
            out.loc[unavailable, name + '_fallback'] = True
            out.loc[unavailable, name + '_reason'] = (
                ('calendar' if pipeline == 'A5' else 'baseline') + f'_observed_days_lt_{minimum_days}')
    out.loc[unavailable, 'takeoffs_complete'] = False
    return out


class ExposureErrataMixin:
    pipeline = None

    def __init__(self, *args, minimum_days=30, **kwargs):
        super().__init__(*args, **kwargs)
        flights = args[1] if len(args) > 1 else kwargs['flights']
        self.exposure = ObservedExposure(flights, minimum_days)

    def forecast(self, origin, variant):
        corrected = self.exposure
        if variant == 'realized_fh':
            # Preserve the entire original control, including diagnostics/columns.
            self.exposure = corrected.legacy
            try:
                return super().forecast(origin, variant)
            finally:
                self.exposure = corrected
        frame = super().forecast(origin, variant)
        return exposure_fallback(frame, corrected.observed_days(origin), self.pipeline,
                                 corrected.minimum_days, variant)


class CorrectedA5(ExposureErrataMixin, Evaluation):
    pipeline = 'A5'


class CorrectedA4(ExposureErrataMixin, HierarchicalEvaluation):
    pipeline = 'A4'
