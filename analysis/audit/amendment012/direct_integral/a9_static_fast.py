"""Equivalent low-allocation P1 linear algebra under amendment 012."""
from functools import lru_cache
import math

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.linalg.blas import dger
from scipy.special import gamma, gammainc, gammaincc

import a9_static as reference

_Z, _W = leggauss(32)
_Z, _W = (_Z + 1) / 2, _W / 2


def _kernel(increments, beta, eta, nu, r, step):
    clock = np.r_[0., np.cumsum(increments)]
    times = np.arange(len(clock)) * step
    lo, hi = (clock[:-1] / eta) ** beta, (clock[1:] / eta) ** beta
    survival = np.exp(-(clock / eta) ** beta - nu * times)
    mass = survival[:-1] - survival[1:]
    if nu == 0:
        shape = 1 + 1 / beta
        lower = gammainc(shape, hi) - gammainc(shape, lo)
        upper = gammaincc(shape, lo) - gammaincc(shape, hi)
        truncated_moment = eta * gamma(shape) * np.where(lo > 1, upper, lower)
        rate = increments / step
        moment = np.divide(truncated_moment - clock[:-1] * mass, rate,
                           out=np.zeros_like(rate), where=rate > 0)
        right = moment / step
        left, u, c = mass - right, mass, np.zeros_like(mass)
        kind = 'analytic_no_competing'
    else:
        power = np.where((clock[:-1] == 0) & (increments > 0), max(1, int(np.ceil(4 / beta))), 1)
        lag = step * _Z[None, :] ** power[:, None]
        jacobian = step * power[:, None] * _Z[None, :] ** (power[:, None] - 1)
        age = clock[:-1, None] + increments[:, None] * lag / step
        with np.errstate(over='ignore', invalid='ignore'):
            s = np.exp(-(age / eta) ** beta - nu * (times[:-1, None] + lag))
            hazard = beta / eta * (age / eta) ** (beta - 1) * increments[:, None] / step
            pu = s * hazard * jacobian * _W
            pc = s * nu * jacobian * _W
        u, c = pu.sum(axis=1), pc.sum(axis=1)
        left = ((pu + pc) * (1 - lag / step)).sum(axis=1)
        right = ((pu + pc) * lag / step).sum(axis=1)
        kind = 'direct_time_integral'
    valid = (all(np.isfinite(a).all() for a in (u, c, left, right)) and
             min(float(left.min()), float(right.min())) >= -1e-12 and
             np.max(np.abs(u + c - mass)) <= 1e-12 and
             np.max(np.abs(left + right - mass)) <= 1e-12 and
             abs(float((u + c).sum()) - (1 - survival[-1])) <= 1e-10)
    if not valid:
        u, c, left, right = reference.first_event_weights(times, clock, 0., beta, eta, nu, order=32)
        kind = 'reference_fallback'
    else:
        # Only round-off below the stricter internal bound can reach zero.
        left, right = np.maximum(left, 0.), np.maximum(right, 0.)
    result = dict(clock=clock, survival=survival, left=left, right=right,
        reward=np.r_[0., np.cumsum(r * u + c)],
        moment=np.r_[0., np.cumsum(left * times[:-1] + right * times[1:])],
        error=abs(float((u + c).sum()) - (1 - survival[-1])), kind=kind)
    return result


@lru_cache(maxsize=32)
def _constant_kernel(length, increment, beta, eta, nu, r, step):
    result = _kernel(np.full(length, increment), beta, eta, nu, r, step)
    for value in result.values():
        if isinstance(value, np.ndarray):
            value.flags.writeable = False
    return result


class FastCalendarRenewal(reference.CalendarRenewal):
    def __init__(self, daily, visits, beta, eta, nu, r, weight=1., subdivisions=1,
                 probability_tolerance=1e-10, duration_tolerance=1e-7):
        self.previous_stops = {}
        self.previous_finite = {}
        self.row_updates = {}
        self.full_refactors = 0
        self.sparse_products = 0
        self.daily = np.asarray(daily, float)
        self.n, self.step = len(daily) * subdivisions, 1 / subdivisions
        self.increment = np.repeat(self.daily / subdivisions, subdivisions)
        self.visits = np.array(sorted(set(int(v * subdivisions) % self.n for v in visits)), int)
        if (not len(self.visits) or self.n == 0 or beta <= 1 or eta <= 0 or nu < 0 or
                self.increment.min() < 0 or self.increment.sum() <= 0):
            raise ValueError('Static renewal calendar requires ageing, exposure and visits')
        self.beta, self.eta, self.nu, self.r, self.weight = beta, eta, nu, r, weight
        self.rows, self.kernel_kinds = [], {}
        self.P = np.zeros((self.n, self.n))
        self.cost, self.duration = np.zeros(self.n), np.zeros(self.n)
        self.mass_error, self.max_tail_probability, self.max_tail_duration = 0., 0., 0.
        self.updates = 0
        periods, total = 1, self.increment.sum()
        while True:
            elapsed, exposure = periods * len(daily), periods * total
            probability = math.exp(-(exposure / eta) ** beta - nu * elapsed)
            integrated = eta * gamma(1 / beta) * gammaincc(1 / beta, (exposure / eta) ** beta) / beta
            duration_bound = probability / nu if nu else len(daily) * (probability + integrated / total)
            if probability <= probability_tolerance and duration_bound <= duration_tolerance:
                break
            periods *= 2
            if periods > 65536:
                raise ArithmeticError('Static calibration tail could not be bounded')
        self.max_tail_probability, self.max_tail_duration = probability, duration_bound
        constant = bool(np.all(self.increment == self.increment[0]))
        length = periods * self.n
        for phase in range(self.n):
            kernel = (_constant_kernel(length, self.increment[0], beta, eta, nu, r, self.step)
                      if constant else _kernel(np.tile(np.roll(self.increment, -phase), periods),
                                               beta, eta, nu, r, self.step))
            if kernel['error'] > 1e-7:
                raise ArithmeticError('Static first-event quadrature does not conserve probability')
            self.mass_error = max(self.mass_error, kernel['error'])
            self.kernel_kinds[kernel['kind']] = self.kernel_kinds.get(kernel['kind'], 0) + 1
            offsets = np.arange((length + phase) // self.n + 1) * self.n
            stops = (offsets[:, None] + self.visits[None, :] - phase).ravel()
            stops = stops[(stops > 0) & (stops <= length)]
            row = {k: kernel[k] for k in ('clock', 'survival', 'left', 'right', 'reward', 'moment')}
            row.update(phase=phase, stops=stops, cursor=0)
            self.rows.append(row)
            self.replace_row(phase, update_inverse=False)
        self.refactor()

    def refactor(self):
        super().refactor()
        self.inverse = np.asfortranarray(self.inverse)
        self.full_refactors += 1

    def replace_row(self, phase, update_inverse=True):
        row = self.rows[phase]
        finite = row['cursor'] < len(row['stops'])
        stop = int(row['stops'][row['cursor']]) if finite else len(row['clock']) - 1
        count = self.row_updates.get(phase, 0)
        incremental = (update_inverse and finite and self.previous_finite.get(phase, False)
                       and count % 64 != 0)
        if incremental:
            old = self.previous_stops[phase]
            j = np.arange(old, stop)
            delta = (np.bincount((phase + j) % self.n, weights=row['left'][old:stop], minlength=self.n) +
                     np.bincount((phase + j + 1) % self.n, weights=row['right'][old:stop], minlength=self.n))
            delta[(phase + old) % self.n] -= row['survival'][old]
            delta[(phase + stop) % self.n] += row['survival'][stop]
            self.P[phase] += delta
            survival = row['survival'][stop]
            self.cost[phase] = row['reward'][stop] + survival
            self.duration[phase] = row['moment'][stop] + stop * self.step * survival
        else:
            previous = self.P[phase].copy()
            super().replace_row(phase, update_inverse=False)
            delta = self.P[phase] - previous
        self.previous_stops[phase], self.previous_finite[phase] = stop, finite
        self.row_updates[phase] = count + 1
        if not update_inverse:
            return
        self.updates += 1
        indices = np.flatnonzero(delta)
        if len(indices) < self.n // 4:
            vector = self.inverse[:, indices] @ delta[indices]
            self.sparse_products += 1
        else:
            vector = self.inverse @ delta
        denominator = 1 - vector[phase]
        if abs(denominator) < 1e-8 or self.updates % 8192 == 0:
            self.refactor()
            return
        previous_mass = self.stationary[phase]
        self.inverse = dger(1 / denominator, vector, self.inverse[phase].copy(),
                             a=self.inverse, overwrite_a=1)
        self.stationary += vector * previous_mass / denominator
        invalid = abs(self.stationary.sum() - 1) > 1e-7 or self.stationary.min() < -1e-8
        if self.updates % 128 == 0:
            invalid |= np.max(np.abs(self.P.T @ self.stationary - self.stationary)) > 1e-10
        if invalid:
            self.refactor()


def exhaustive_threshold(contexts, beta, eta, nu, r, subdivisions=1):
    return reference.exhaustive_threshold(contexts, beta, eta, nu, r, subdivisions,
                                          calendar_type=FastCalendarRenewal)


def calibrate_threshold(contexts, beta, eta, nu, r, max_subdivisions=4):
    return reference.calibrate_threshold(contexts, beta, eta, nu, r, max_subdivisions,
                                         calendar_type=FastCalendarRenewal)
