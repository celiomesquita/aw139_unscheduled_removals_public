"""Two deterministic artificial integration runs, then the complete test suite."""
import itertools
import json
import time
import unittest

import numpy as np

from a16_generator import ROOT, sha
from a9_arcflow import RenewalArc, solve_paths
from a9_events import UnitState
from a9_renewal import RenewalCosts
from round5_execution import atomic_json, check_historical

OUT = ROOT / 'data/derived/a9/numerical_validation'


def integrated_fixture(step):
    times = np.arange(0., 6. + step / 2, step)
    visits = [2., 4.]
    parameters = {'A': (2., 4., .1), 'B': (1.5, 3., .05)}
    arcs, errors = [], []
    for unit, (beta, eta, nu) in parameters.items():
        for start in range(-1, len(visits)):
            t0 = 0. if start == -1 else visits[start]
            grid = times[times >= t0]
            model = RenewalCosts(grid, grid - t0, beta, eta, nu, 5., order=32)
            errors.append(model.mass_error)
            for end in range(start + 1, len(visits) + 1):
                t1 = 6. if end == len(visits) else visits[end]
                index = int(round((t1 - t0) / step))
                future = [1.] if end == len(visits) else None
                value, bound = model.current(0., index, future)
                arcs.append(RenewalArc(unit, start, end, value + (1 if future is None else 0)))
    plan, diagnostics = solve_paths(arcs, {'A': 1., 'B': 1.}, [1., 1.])
    # Independent enumeration of every feasible preventive sequence pair.
    table = {(a.unit, a.start, a.end): a.cost for a in arcs}
    sequences = [tuple(i for i, include in enumerate(mask) if include)
                 for mask in itertools.product((False, True), repeat=2)]
    exhaustive = []
    for first, second in itertools.product(sequences, repeat=2):
        if set(first).intersection(second):
            continue
        cost = sum(table[u, a, b] for u, p in (('A', first), ('B', second))
                   for a, b in zip((-1,) + p, p + (2,)))
        exhaustive.append(cost)
    if not diagnostics['proven_optimal'] or abs(min(exhaustive) - diagnostics['selected_expected_cost']) > 1e-8:
        raise RuntimeError('Integrated renewal costs/path MILP disagree with enumeration')
    realised = []
    for i, (unit, (beta, eta, nu)) in enumerate(parameters.items()):
        state = UnitState((9, 900, i), beta, nu)
        for end in visits + [6.]:
            events = state.advance(end, 1., eta, eta)
            realised.extend(dict(unit=unit, **event) for event in events)
            if end in visits and visits.index(end) in plan[unit]:
                realised.append(dict(unit=unit, start=state.birth, end=end, risk=3,
                                     age=state.age, renewal=state.renewal, exact_risk_tie=False))
                state.renew(end)
    return dict(step_days=step, plan=plan, expected_cost=diagnostics['selected_expected_cost'],
                events=realised, max_first_event_mass_error=max(errors),
                terminal_residual_bound=bound, proven_optimal=True,
                manual_enumeration_equal=True)


def main():
    frozen = json.loads((ROOT / 'data/derived/a16/flow17/configuration.json').read_text())
    check_historical(frozen['historical'])
    OUT.mkdir(parents=True, exist_ok=True)
    first = [integrated_fixture(step) for step in (1., .5, .25, .125, .0625)]
    second = [integrated_fixture(step) for step in (1., .5, .25, .125, .0625)]
    if first != second:
        raise RuntimeError('Artificial integrated validation is not deterministic')
    differences = [abs(first[i]['expected_cost'] - first[i + 1]['expected_cost'])
                   for i in range(len(first) - 1)]
    if any(b > a for a, b in zip(differences, differences[1:])) or differences[-1] > .01:
        raise RuntimeError('Renewal grid refinement did not converge in the fixed fixture')
    atomic_json(OUT / 'artificial_fixture.json', dict(results=first, refinement_differences=differences))
    paths = [ROOT / 'data/derived' / name for name in
             ('a15/manifest.json', 'pipeline_manifest.json', 'pipeline_verification.json')]
    before = {p: p.read_bytes() for p in paths if p.exists()}
    started = time.perf_counter()
    try:
        result = unittest.TextTestRunner().run(unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    finally:
        for p, content in before.items():
            if p.read_bytes() != content:
                p.write_bytes(content)
    check_historical(frozen['historical'])
    sources = ['analysis/a9_renewal.py', 'analysis/a9_events.py', 'analysis/a9_arcflow.py',
               'analysis/a9_fitting.py', 'analysis/verify_a9_numerics.py']
    atomic_json(OUT / 'verification.json', dict(tests_run=result.testsRun,
        errors=len(result.errors), failures=len(result.failures),
        test_seconds=time.perf_counter() - started, two_artificial_runs_identical=True,
        policy_fleet_replicas=0, pilot_started=False, historical_hashes_unchanged=True,
        sources={p: sha(ROOT / p) for p in sources},
        artificial_fixture_sha256=sha(OUT / 'artificial_fixture.json')))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
