"""Product integration of the renewal equation on an operational clock."""
import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.linalg import solve_triangular
from a9_terminal import terminal_cycle


def first_event_weights(times, clock, age, beta, eta, nu, order=16):
    """Integrate each competing CIF in its own probability coordinate."""
    times, clock = np.asarray(times, float), np.asarray(clock, float)
    if (len(times) != len(clock) or np.any(np.diff(times) <= 0) or
            np.any(np.diff(clock) < 0) or age < 0 or beta <= 0 or eta <= 0 or nu < 0):
        raise ValueError('Invalid renewal clock or parameters')
    n = len(times) - 1
    if n == 0:
        return np.zeros((4, 0))
    nodes, weights = leggauss(order)
    nodes, weights = (nodes + 1) / 2, weights / 2
    width = np.diff(times)
    rate = np.diff(clock) / width
    a = age + clock[:-1] - clock[0]
    h0 = (age / eta) ** beta
    hl, hr = (a / eta) ** beta, ((a + np.diff(clock)) / eta) ** beta
    survival = np.exp(-(hl - h0) - nu * (times[:-1] - times[0]))
    qu = -np.expm1(-(hr - hl))
    qc = -np.expm1(-nu * width)
    power_u = np.where(a == 0, max(1, int(np.ceil(4 * beta))), 1)
    coordinate_u = nodes[None, :] ** power_u[:, None]
    weight_u = weights * power_u[:, None] * nodes[None, :] ** (power_u[:, None] - 1)
    q = qu[:, None] * coordinate_u
    operational = eta * (hl[:, None] - np.log1p(-q)) ** (1 / beta) - a[:, None]
    lag = np.divide(operational, rate[:, None], out=np.zeros_like(operational),
                    where=rate[:, None] > 0)
    lag = np.clip(lag, 0, width[:, None])
    pu = survival[:, None] * qu[:, None] * weight_u * np.exp(-nu * lag)
    power_c = np.where(a == 0, max(1, int(np.ceil(4 / beta))), 1)
    coordinate_c = nodes[None, :] ** power_c[:, None]
    weight_c = weights * power_c[:, None] * nodes[None, :] ** (power_c[:, None] - 1)
    q = qc[:, None] * coordinate_c
    lag_c = -np.log1p(-q) / (nu if nu else 1.)
    hc = ((a[:, None] + rate[:, None] * lag_c) / eta) ** beta - hl[:, None]
    pc = survival[:, None] * qc[:, None] * weight_c * np.exp(-hc)
    left = (pu * (1 - lag / width[:, None]) +
            pc * (1 - lag_c / width[:, None])).sum(axis=1)
    right = (pu * lag / width[:, None] + pc * lag_c / width[:, None]).sum(axis=1)
    return np.array([pu.sum(axis=1), pc.sum(axis=1), left, right])


def legacy_terminal_cycle(ages, future_daily, beta, eta, nu, r, tolerance=1e-9, order=8):
    """Cost of the first future renewal only; periodic clock, residual bound."""
    ages = np.atleast_1d(np.asarray(ages, float))
    daily = np.asarray(future_daily, float)
    if (not len(daily) or not np.isfinite(daily).all() or daily.min() < 0 or
            np.any(ages < 0) or beta <= 0 or eta <= 0 or nu < 0):
        raise ValueError('Invalid terminal cycle inputs')
    if daily.sum() == 0:
        return np.full_like(ages, 1. if nu else 0.), 0.
    if nu == 0:
        return np.full_like(ages, r), 0.
    if beta == 1 and np.all(daily == daily[0]):
        lam = daily[0] / eta
        return np.full_like(ages, (r * lam + nu) / (lam + nu)), 0.
    nodes, weights = leggauss(order)
    nodes, weights = (nodes + 1) / 2, weights / 2
    elapsed, operational, pc = 0, 0., np.zeros_like(ages)
    h0 = (ages / eta) ** beta
    # The stopping criterion is a bound on missing probability, not policy gain.
    for _ in range(10000):
        cumulative = np.r_[0., np.cumsum(daily)]
        t = elapsed + np.arange(len(daily))[:, None] + nodes
        x = operational + cumulative[:-1, None] + daily[:, None] * nodes
        for j, age in enumerate(ages):
            survival = np.exp(-(((age + x) / eta) ** beta - h0[j]) - nu * t)
            pc[j] += nu * (survival * weights).sum()
        elapsed += len(daily)
        operational += cumulative[-1]
        residual = np.exp(-(((ages + operational) / eta) ** beta - h0) - nu * elapsed)
        bound = float(residual.max()) * max(1., r)
        if bound <= tolerance:
            return r - (r - 1) * pc, bound
    raise ArithmeticError('Terminal cycle residual did not meet the fixed tolerance')


class RenewalCosts:
    """Solve V(s)=first-event reward + integral f(t|s)V(t) + survivor tail."""
    def __init__(self, times, clock, beta, eta, nu, r, order=16):
        self.times, self.clock = np.asarray(times, float), np.asarray(clock, float)
        self.beta, self.eta, self.nu, self.r, self.order = beta, eta, nu, r, order
        n = len(times)
        self.W = np.zeros((n, n))
        self.reward = np.zeros((n, n - 1))
        self.mass_error = 0.
        for i in range(n - 1):
            u, c, left, right = first_event_weights(self.times[i:], self.clock[i:],
                                                    0., beta, eta, nu, order)
            self.W[i, i:-1] += left
            self.W[i, i + 1:] += right
            self.reward[i, i:] = r * u + c
            expected = 1 - np.exp(-((self.clock[-1] - self.clock[i]) / eta) ** beta -
                                 nu * (self.times[-1] - self.times[i]))
            self.mass_error = max(self.mass_error, abs(float((u + c).sum()) - expected))
        self._cache = {}
        self.terminal_checks = []

    def values(self, end, future_daily=None):
        key = (end, None if future_daily is None else tuple(future_daily))
        if key in self._cache:
            return self._cache[key]
        boundary = 0.
        tail = np.zeros(end + 1)
        residual = 0.
        if future_daily is not None:
            ages = self.clock[end] - self.clock[:end + 1]
            diagnostic = {}
            tail, residual = terminal_cycle(ages, future_daily, self.beta, self.eta,
                                            self.nu, self.r, diagnostics=diagnostic)
            self.terminal_checks.append(diagnostic)
            boundary = tail[-1]
        if end == 0:
            result = np.array([boundary]), residual
        else:
            survival = np.exp(-((self.clock[end] - self.clock[:end]) / self.eta) ** self.beta -
                              self.nu * (self.times[end] - self.times[:end]))
            rhs = self.reward[:end, :end].sum(axis=1) + survival * tail[:end]
            rhs += self.W[:end, end] * boundary
            solution = solve_triangular(np.eye(end) - self.W[:end, :end], rhs, lower=False)
            result = np.r_[solution, boundary], residual
        self._cache[key] = result
        return result

    def current(self, age, end, future_daily=None):
        values, residual = self.values(end, future_daily)
        if age == 0:
            return float(values[0]), residual
        u, c, left, right = first_event_weights(self.times[:end + 1], self.clock[:end + 1],
                                                age, self.beta, self.eta, self.nu, self.order)
        result = float((self.r * u + c).sum() + left @ values[:-1] + right @ values[1:])
        if future_daily is not None:
            ending_age = age + self.clock[end] - self.clock[0]
            diagnostic = {}
            tail, tail_bound = terminal_cycle([ending_age], future_daily, self.beta,
                                              self.eta, self.nu, self.r, diagnostics=diagnostic)
            self.terminal_checks.append(diagnostic)
            survival = np.exp(-((ending_age / self.eta) ** self.beta -
                                (age / self.eta) ** self.beta) -
                              self.nu * (self.times[end] - self.times[0]))
            result += survival * tail[0]
            residual = max(residual, tail_bound)
        return float(result), residual
