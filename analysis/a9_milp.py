"""CBC selection of renewal-sequence columns; costs supplied by renewal model."""
from dataclasses import dataclass
import math
import time

import mip


@dataclass(frozen=True)
class SequenceColumn:
    unit: str
    visits: tuple
    expected_cost: float


def feasible_plan(columns, mh, capacities):
    if len(columns) != len(mh) or {c.unit for c in columns} != set(mh):
        return False
    return all(sum(mh[c.unit] for c in columns if j in c.visits) <= cap + 1e-8
               for j, cap in enumerate(capacities))


def solve_sequences(columns, mh, capacities, previous=()):
    """Solve one decision; a nonoptimal result uses the preregistered fallback."""
    if not columns or not mh or any(not math.isfinite(v) or v <= 0 for v in mh.values()):
        raise ValueError('Missing positive preventive MH or sequence columns')
    if any(not math.isfinite(v) or v < 0 for v in capacities):
        raise ValueError('Invalid preventive capacity')
    groups = {unit: [] for unit in sorted(mh)}
    keys = set()
    for i, column in enumerate(columns):
        if (column.unit not in groups or not math.isfinite(column.expected_cost) or
                tuple(sorted(set(column.visits))) != column.visits or
                any(j < 0 or j >= len(capacities) for j in column.visits)):
            raise ValueError('Invalid renewal-sequence column')
        key = (column.unit, column.visits)
        if key in keys:
            raise ValueError('Duplicate renewal-sequence column')
        keys.add(key)
        groups[column.unit].append(i)
    if any((unit, ()) not in keys for unit in groups):
        raise ValueError('No-preventive option required for every unit')
    model = mip.Model(solver_name=mip.CBC)
    model.verbose = 0
    model.threads = 1
    model.seed = 20261112
    model.max_mip_gap = 1e-6
    variables = [model.add_var(var_type=mip.BINARY) for _ in columns]
    model.objective = mip.minimize(mip.xsum(c.expected_cost * x
                                          for c, x in zip(columns, variables)))
    for indices in groups.values():
        model += mip.xsum(variables[i] for i in indices) == 1
    for j, capacity in enumerate(capacities):
        model += mip.xsum(mh[c.unit] * variables[i] for i, c in enumerate(columns)
                          if j in c.visits) <= capacity
    start = time.perf_counter()
    status = model.optimize(max_seconds=300)
    elapsed = time.perf_counter() - start
    proven = status == mip.OptimizationStatus.OPTIMAL
    if proven:
        selected = [c for c, x in zip(columns, variables) if x.x > .5]
        if not feasible_plan(selected, mh, capacities):
            raise RuntimeError('CBC returned an infeasible preventive plan')
        fallback = None
    elif feasible_plan(previous, mh, capacities) and all(
            (c.unit, c.visits) in keys for c in previous):
        # Use current expected costs for the preserved action sequence.
        requested = {(c.unit, c.visits) for c in previous}
        selected = [c for c in columns if (c.unit, c.visits) in requested]
        fallback = 'previous_feasible'
    else:
        selected = [c for c in columns if not c.visits]
        fallback = 'no_preventive'
    finite = lambda value: float(value) if value is not None and math.isfinite(value) else None
    diagnostics = dict(status=status.name, proven_optimal=proven, fallback=fallback,
                       objective_bound=finite(model.objective_bound), gap=finite(model.gap),
                       incumbent_objective=finite(model.objective_value), runtime_seconds=elapsed,
                       selected_expected_cost=sum(c.expected_cost for c in selected),
                       columns=len(columns), units=len(mh), visits=len(capacities))
    return selected, diagnostics
