"""Equivalent low-allocation P1 linear algebra under amendment 012."""
import numpy as np
from scipy.linalg.blas import dger

import a9_static as reference


class FastCalendarRenewal(reference.CalendarRenewal):
    def __init__(self, *args, **kwargs):
        self.previous_stops = {}
        self.previous_finite = {}
        self.row_updates = {}
        self.full_refactors = 0
        self.sparse_products = 0
        super().__init__(*args, **kwargs)

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
