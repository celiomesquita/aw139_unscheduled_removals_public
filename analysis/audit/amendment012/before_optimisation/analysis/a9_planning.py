"""Renewal-cost arcs for a six-month decision, with measured grid refinement."""
import numpy as np

from a9_arcflow import RenewalArc, solve_paths
from a9_renewal import RenewalCosts


def cost_arcs(unit, age, daily, visits, beta, eta, nu, r, terminal_daily,
              step=1., order=32):
    daily = np.asarray(daily, float)
    horizon = len(daily)
    if any(not 0 < v <= horizon for v in visits) or list(visits) != sorted(set(visits)):
        raise ValueError('Visits must be unique, increasing, inside the decision horizon')
    subdivisions = int(round(1 / step))
    if subdivisions < 1 or not np.isclose(subdivisions * step, 1):
        raise ValueError('Grid must subdivide calendar days exactly')
    times = np.arange(horizon * subdivisions + 1) / subdivisions
    daily_clock = np.r_[0., np.cumsum(daily)]
    clock = np.interp(times, np.arange(horizon + 1), daily_clock)
    model = RenewalCosts(times, clock, beta, eta, nu, r, order)
    arcs, bound = [], 0.
    for end in range(len(visits) + 1):
        terminal = end == len(visits)
        end_day = horizon if terminal else visits[end]
        index = int(round(end_day * subdivisions))
        future = terminal_daily if terminal else None
        values, residual = model.values(index, future)
        bound = max(bound, residual)
        root, residual = model.current(age, index, future)
        bound = max(bound, residual)
        preventive = 0 if terminal else 1
        arcs.append(RenewalArc(unit, -1, end, root + preventive))
        for start in range(end):
            begin = int(round(visits[start] * subdivisions))
            arcs.append(RenewalArc(unit, start, end, float(values[begin]) + preventive))
    return arcs, dict(step_days=step, probability_mass_error=model.mass_error,
                      terminal_residual_bound=bound,
                      terminal_quadrature_difference=max((d['quadrature_difference']
                          for d in model.terminal_checks), default=0.))


def refined_arcs(unit, age, daily, visits, beta, eta, nu, r, terminal_daily,
                 absolute_tolerance=.001, relative_tolerance=1e-4, max_subdivisions=64):
    """Refine every arc, not only the objective of the selected plan."""
    previous, history = None, []
    for subdivision in (1, 2, 4, 8, 16, 32, 64):
        if subdivision > max_subdivisions:
            break
        arcs, diagnostic = cost_arcs(unit, age, daily, visits, beta, eta, nu, r,
                                      terminal_daily, 1 / subdivision)
        values = np.array([a.cost for a in arcs])
        accepted = False
        if previous is not None:
            error = np.abs(values - previous)
            limits = absolute_tolerance + relative_tolerance * np.abs(values)
            diagnostic['max_arc_refinement_difference'] = float(error.max())
            accepted = bool(np.all(error <= limits) and diagnostic['probability_mass_error'] < 1e-7)
        history.append(diagnostic)
        if accepted:
            return arcs, history
        previous = values
    raise ArithmeticError('Renewal arc integration failed the fixed refinement tolerances')


def optimise_visit_plan(specifications, capacities, previous=None):
    """Each specification has observed age and a frozen, information-feasible clock."""
    all_arcs, mh, quadrature = [], {}, {}
    count = len(capacities)
    for spec in specifications:
        unit = spec['unit']
        if unit in mh:
            raise ValueError('Duplicate synthetic unit')
        if 'visit_indices' not in spec and count != len(spec['visits']):
            raise ValueError('Units must share visit indices')
        mh[unit] = spec['mh']
        arguments = {k: spec[k] for k in ('unit', 'age', 'daily', 'visits', 'beta', 'eta',
                                          'nu', 'r', 'terminal_daily')}
        arcs, diagnostic = refined_arcs(**arguments)
        indices = spec.get('visit_indices', list(range(count)))
        if len(indices) != len(spec['visits']) or any(j < 0 or j >= count for j in indices):
            raise ValueError('Invalid unit-specific visit mapping')
        for arc in arcs:
            start = -1 if arc.start == -1 else indices[arc.start]
            end = count if arc.end == len(indices) else indices[arc.end]
            all_arcs.append(RenewalArc(unit, start, end, arc.cost))
        quadrature[unit] = diagnostic
    if count != len(capacities):
        raise ValueError('Capacity and visit indices differ')
    paths, diagnostics = solve_paths(all_arcs, mh, capacities, previous)
    diagnostics['quadrature'] = quadrature
    return paths, diagnostics
