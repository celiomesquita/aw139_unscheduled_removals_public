"""Fresh pilot directory under amendment 012; original checkpoints remain immutable."""
import argparse

import a9_pilot as pilot

pilot.OUT = pilot.ROOT / 'data/derived/a9/pilot_optimised'
pilot.REPORT = pilot.ROOT / 'analysis/a9_pilot_optimised_report.md'
pilot.CALIBRATION_WORKERS = 6
pilot.PRIOR_COSTS_PATH = pilot.ROOT / 'data/derived/a9/optimisation/prior_costs.json'
pilot.ALLOW_COMPLETE_REPLICA_BUDGET_CERTIFICATE = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.run:
        raise SystemExit(pilot.run())
    if args.prepare:
        print(pilot.prepare()['configuration_sha256'])
