"""Terminal-cycle integration with distinct tail and quadrature checks."""
import numpy as np
from numpy.polynomial.legendre import leggauss


def _integrate(ages, daily, beta, eta, nu, r, tolerance, order):
    z, weights = leggauss(order)
    z, weights = (z + 1) / 2, weights / 2
    cumulative = np.r_[0., np.cumsum(daily)]
    elapsed, operational = 0, 0.
    pc = np.zeros_like(ages)
    h0 = (ages / eta) ** beta
    for _ in range(10000):
        for j, age in enumerate(ages):
            before = age + operational + cumulative[:-1]
            power = np.where((before == 0) & (daily > 0), max(1, int(np.ceil(4 / beta))), 1)
            lag = z[None, :] ** power[:, None]
            jacobian = power[:, None] * z[None, :] ** (power[:, None] - 1)
            t = elapsed + np.arange(len(daily))[:, None] + lag
            x = before[:, None] + daily[:, None] * lag
            survival = np.exp(-((x / eta) ** beta - h0[j]) - nu * t)
            pc[j] += nu * (survival * jacobian * weights).sum()
        elapsed += len(daily)
        operational += cumulative[-1]
        residual = np.exp(-(((ages + operational) / eta) ** beta - h0) - nu * elapsed)
        bound = float(residual.max()) * max(1., r)
        if bound <= tolerance:
            return r - (r - 1) * pc, bound
    raise ArithmeticError('Terminal-cycle tail could not be bounded')


def terminal_cycle(ages, future_daily, beta, eta, nu, r, tolerance=1e-9, order=8, diagnostics=None):
    ages, daily = np.atleast_1d(np.asarray(ages, float)), np.asarray(future_daily, float)
    if (not len(daily) or not np.isfinite(daily).all() or daily.min() < 0 or
            not np.isfinite(ages).all() or np.any(ages < 0) or beta <= 0 or eta <= 0 or nu < 0):
        raise ValueError('Invalid terminal cycle inputs')
    exact = None
    if daily.sum() == 0:
        exact = np.full_like(ages, 1. if nu else 0.)
    elif nu == 0:
        exact = np.full_like(ages, r)
    elif beta == 1 and np.all(daily == daily[0]):
        lam = daily[0] / eta
        exact = np.full_like(ages, (r * lam + nu) / (lam + nu))
    if exact is not None:
        if diagnostics is not None:
            diagnostics.update(order=0, quadrature_difference=0., tail_bound=0.)
        return exact, 0.
    previous = None
    for quadrature_order in sorted(set([order, 2 * order, 4 * order, 8 * order, 16 * order])):
        values, bound = _integrate(ages, daily, beta, eta, nu, r, tolerance, quadrature_order)
        if previous is not None:
            error = np.abs(values - previous)
            if np.all(error <= 1e-8 * (1 + np.abs(values))):
                if diagnostics is not None:
                    diagnostics.update(order=quadrature_order, quadrature_difference=float(error.max()),
                                       tail_bound=bound)
                return values, bound
        previous = values
    raise ArithmeticError('Terminal-cycle quadrature did not meet its fixed tolerance')
