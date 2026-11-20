"""Coupled renewal paths with continuous hazard across imposed drifts."""
from dataclasses import dataclass

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.optimize import brentq

SEED = 20261112
NODES, WEIGHTS = leggauss(24)


def hazard_increment(age, rate, duration, beta, eta_left, eta_right):
    if duration == 0 or rate == 0:
        return 0.
    if eta_left == eta_right:
        return ((age + rate * duration) / eta_left) ** beta - (age / eta_left) ** beta
    power = max(1, int(np.ceil(4 / beta))) if age == 0 else 1
    z = (NODES + 1) / 2
    t = duration * z ** power
    jacobian = duration * power * z ** (power - 1)
    eta = eta_left + (eta_right - eta_left) * t / duration
    a = age + rate * t
    hazard = beta * rate * a ** (beta - 1) / eta ** beta
    return float(np.sum(WEIGHTS / 2 * jacobian * hazard))


@dataclass
class UnitState:
    key: tuple
    beta: float
    nu: float
    age: float = 0.
    renewal: int = 0
    time: float = 0.
    birth: float = 0.
    remaining_u: float = None
    remaining_c: float = None

    def __post_init__(self):
        if self.beta <= 0 or self.nu < 0:
            raise ValueError('Invalid unit parameters')
        self.draw()

    def draw(self):
        self.remaining_u = float(np.random.default_rng(
            np.random.SeedSequence([SEED, *self.key, self.renewal, 1])).exponential())
        self.remaining_c = float(np.random.default_rng(
            np.random.SeedSequence([SEED, *self.key, self.renewal, 2])).exponential())

    def renew(self, time):
        self.birth, self.time, self.age = time, time, 0.
        self.renewal += 1
        self.draw()

    def advance(self, end, rate, eta_left, eta_right):
        """One linear-eta segment. Natural events precede preventive ties."""
        if end < self.time or rate < 0 or min(eta_left, eta_right) <= 0:
            raise ValueError('Invalid event segment')
        segment_start = self.time
        width = end - segment_start
        events = []
        while self.time < end:
            now = self.time
            duration = end - now
            eta_now = eta_left + (eta_right - eta_left) * (now - segment_start) / width
            hazard = hazard_increment(self.age, rate, duration, self.beta, eta_now, eta_right)
            if hazard >= self.remaining_u:
                def difference(dt):
                    e = eta_now + (eta_right - eta_now) * dt / duration
                    return hazard_increment(self.age, rate, dt, self.beta, eta_now, e) - self.remaining_u
                du = brentq(difference, 0., duration, xtol=1e-12)
            else:
                du = np.inf
            dc = self.remaining_c / self.nu if self.nu else np.inf
            risk = 2 if dc <= du else 1
            dt = min(du, dc, duration)
            if not np.isfinite(dt) or dt <= 0:
                raise ArithmeticError('Renewal did not advance continuous time')
            eta_finish = eta_now + (eta_right - eta_now) * dt / duration
            self.remaining_u -= hazard_increment(self.age, rate, dt, self.beta, eta_now, eta_finish)
            self.remaining_c -= self.nu * dt
            self.age += rate * dt
            self.time = now + dt
            happened = min(du, dc) <= duration
            if happened:
                events.append(dict(start=self.birth, end=self.time, risk=risk,
                                   age=self.age, renewal=self.renewal,
                                   exact_risk_tie=bool(dc == du)))
                self.renew(self.time)
            elif self.time >= end:
                break
        return events


def eta_factor(family, scenario, time, change, finish):
    if family != 'rotor' or time < change:
        return 1.
    if scenario == 'B-eta':
        return .7
    if scenario == 'B-gradual':
        return 1 - .3 * np.clip((time - change) / (finish - change), 0, 1)
    return 1.
