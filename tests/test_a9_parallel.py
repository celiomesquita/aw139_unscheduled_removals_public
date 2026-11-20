from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'analysis'))
from a9_parallel import CalibrationExecutor


class TestIndependentParallelCalibration(unittest.TestCase):
    def test_spawned_and_serial_calibrations_return_identical_results(self):
        models = {f'PN-{i}': dict(beta=2., eta=20., nu=.05, converged=True) for i in range(3)}
        contexts = {pn: [dict(daily=[1.], visits=[0.], weight=1.)] for pn in models}
        with CalibrationExecutor(1) as serial:
            first = serial.calibrate(models, contexts, 5.)
        with CalibrationExecutor(2) as parallel:
            second = parallel.calibrate(models, contexts, 5.)
        self.assertEqual(list(first[0]), sorted(models))
        self.assertEqual(first, second)

    def test_memory_limit_does_not_silently_lower_the_phase_resolution(self):
        models = {'PN': dict(beta=2., eta=20., nu=.05, converged=True)}
        contexts = {'PN': [dict(daily=[1.], visits=[0.], weight=1.)]}
        with self.assertRaises(MemoryError):
            with CalibrationExecutor(2, memory_budget_bytes=1) as executor:
                executor.calibrate(models, contexts, 5.)


if __name__ == '__main__':
    unittest.main()
