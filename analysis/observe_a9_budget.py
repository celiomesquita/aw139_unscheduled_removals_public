"""Read-only lower bound on a complete pilot time; never selects R or stops work."""
import argparse
import json
import math
import time

import psutil

from a16_generator import ROOT
from round5_execution import atomic_json

OUT = ROOT / 'data/derived/a9/pilot'


def snapshot():
    state = json.loads((OUT / 'state.json').read_text())
    process = psutil.Process(state['pid'])
    if state['status'] != 'running' or process.status() == psutil.STATUS_ZOMBIE:
        raise RuntimeError('Pilot is not actively running')
    if (OUT / f"replica_{state['replicate']:02d}.json").exists():
        raise RuntimeError('Current replica already has a final checkpoint')
    return dict(monotonic=time.perf_counter(), pid=process.pid,
                process_created=process.create_time(), replicate=state['replicate'],
                configuration_sha256=state['configuration_sha256'])


def observe(start=False):
    path = OUT / 'budget_observation_start.json'
    if start:
        if path.exists():
            raise RuntimeError('Preserve the first budget-observation endpoint')
        atomic_json(path, snapshot())
        return
    first, last = json.loads(path.read_text()), snapshot()
    for key in ('pid', 'process_created', 'replicate', 'configuration_sha256'):
        if first[key] != last[key]:
            raise RuntimeError('Observation endpoints do not belong to the same unfinished replica')
    lower = last['monotonic'] - first['monotonic']
    maximum = 120 * 3600 / (72 * 1.5 * 200)
    upper_r = 50 * math.floor(120 * 3600 / (72 * 1.5 * lower) / 50)
    result = dict(replica=first['replicate'], pid=first['pid'],
        configuration_sha256=first['configuration_sha256'],
        complete_replica_seconds_strict_lower_bound=lower,
        largest_replica_seconds_allowed_for_R200=maximum,
        common_R_upper_bound=upper_r, budget_minimum_provably_infeasible=upper_r < 200,
        R_selected=False, fixed_R=None, full_pilot_complete=False,
        outcomes_opened=False, pilot_stopped_by_observer=False,
        method='same unfinished replica, same live process, monotonic-clock endpoints')
    atomic_json(OUT / 'budget_lower_bound.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', action='store_true')
    observe(parser.parse_args().start)
