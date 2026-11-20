"""Compact path MILP equivalent to all renewal-sequence columns."""
from dataclasses import dataclass
import math
import time

import mip


@dataclass(frozen=True)
class RenewalArc:
    unit: str
    start: int
    end: int
    cost: float


def solve_paths(arcs, mh, capacities, previous=None):
    """Source=-1; visits=0..J-1; sink=J. Every preventive resets age."""
    jmax = len(capacities)
    units = sorted(mh)
    if (not units or any(not math.isfinite(v) or v <= 0 for v in mh.values()) or
            any(not math.isfinite(v) or v < 0 for v in capacities)):
        raise ValueError('Invalid MH or preventive capacity')
    by_key = {}
    for arc in arcs:
        key = (arc.unit, arc.start, arc.end)
        if (key in by_key or arc.unit not in mh or not -1 <= arc.start < arc.end <= jmax or
                not math.isfinite(arc.cost)):
            raise ValueError('Invalid or duplicated renewal arc')
        by_key[key] = arc
    if any((u, -1, jmax) not in by_key for u in units):
        raise ValueError('A direct no-preventive arc is required for each unit')
    model = mip.Model(solver_name=mip.CBC)
    model.verbose, model.threads, model.seed = 0, 1, 20261112
    model.max_mip_gap = 1e-6
    variables = [model.add_var(var_type=mip.BINARY) for _ in arcs]
    model.objective = mip.minimize(mip.xsum(a.cost * x for a, x in zip(arcs, variables)))
    for u in units:
        for node in range(-1, jmax + 1):
            incoming = [i for i, a in enumerate(arcs) if a.unit == u and a.end == node]
            outgoing = [i for i, a in enumerate(arcs) if a.unit == u and a.start == node]
            model += (mip.xsum(variables[i] for i in outgoing) -
                      mip.xsum(variables[i] for i in incoming) ==
                      (1 if node == -1 else -1 if node == jmax else 0))
    for j, capacity in enumerate(capacities):
        model += mip.xsum(mh[a.unit] * x for a, x in zip(arcs, variables)
                          if a.end == j) <= capacity
    started = time.perf_counter()
    status = model.optimize(max_seconds=300)
    runtime = time.perf_counter() - started
    proven = status == mip.OptimizationStatus.OPTIMAL
    fallback = None
    if proven:
        selected = [a for a, x in zip(arcs, variables) if x.x > .5]
        paths = {u: tuple(sorted(a.end for a in selected if a.unit == u and a.end < jmax))
                 for u in units}
    else:
        paths = previous if previous is not None else {}
        valid = set(paths) == set(units)
        if valid:
            valid &= all(tuple(sorted(set(p))) == p and all(0 <= j < jmax for j in p)
                         for p in paths.values())
        if valid:
            valid &= all(sum(mh[u] for u in units if j in paths[u]) <= c + 1e-8
                         for j, c in enumerate(capacities))
            valid &= all((u, a, b) in by_key for u in units
                         for a, b in zip((-1,) + paths[u], paths[u] + (jmax,)))
        if not valid:
            paths = {u: () for u in units}
        fallback = 'previous_feasible' if valid else 'no_preventive'
        selected = [by_key[(u, a, b)] for u in units
                    for a, b in zip((-1,) + paths[u], paths[u] + (jmax,))]
    if any(sum(mh[u] for u in units if j in paths[u]) > c + 1e-7
           for j, c in enumerate(capacities)):
        raise RuntimeError('Path MILP capacity violation')
    finite = lambda x: float(x) if x is not None and math.isfinite(x) else None
    return paths, dict(status=status.name, proven_optimal=proven, fallback=fallback,
                       runtime_seconds=runtime, bound=finite(model.objective_bound),
                       gap=finite(model.gap), incumbent=finite(model.objective_value),
                       selected_expected_cost=sum(a.cost for a in selected),
                       arcs=len(arcs), units=len(units), visits=jmax)
