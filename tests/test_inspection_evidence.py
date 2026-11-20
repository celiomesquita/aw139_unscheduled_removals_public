"""Avoid conflating preventive removal and inspection signoff with failure."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'analysis'))
from inspection_evidence import audit, description_flags

TASK = '139 FIXED S/P AND SCISSORS DI'


class TestInspectionEvidence(unittest.TestCase):
    def fixture(self, description):
        intervals = pd.DataFrame({'Part #':['3G6230A00833'], 'Serial #':['S1'],
            'Aircraft #':['AC-01'], 'att':[pd.Timestamp('2024-01-01')],
            'rem':[pd.Timestamp('2024-02-01')], 'Source Doc #':['D2'],
            'lower_date':[pd.Timestamp('2024-01-15')], 'inspection_task':[TASK],
            'interval_event':[True]})
        tasks = pd.DataFrame({'Aircraft #':['AC-01']*3,
            'Execution Doc #':['D1','D2','D2'], 'Task #':[TASK,TASK,'NST-1'],
            'd':pd.to_datetime(['2024-01-15','2024-02-02','2024-02-02']),
            'Task Description':['Inspect scissors','Inspect scissors',description],
            'Sign Off Remarks':['Inspection with satisfactory result',
                                'Inspection with satisfactory result',
                                'Replacement with satisfactory result']})
        return intervals, tasks

    def test_margin_is_not_failure_even_with_named_inspection(self):
        i, t = self.fixture(f'During {TASK} was found play near the limit on scissors')
        row = audit(i,t).iloc[0]
        self.assertTrue(row.named_detection)
        self.assertEqual(row.verdict, 'preventive_margin_not_confirmed_failure')

    def test_different_inspection_not_attributed_to_proposed_task(self):
        i, t = self.fixture('During airframe inspection was found scissors with excessive play')
        self.assertEqual(audit(i,t).verdict.iloc[0],
                         'detection_by_different_or_unspecified_inspection')

    def test_previous_corrective_work_invalidates_negative_proxy(self):
        i, t = self.fixture(f'During {TASK} was found scissors with excessive play')
        previous = t.iloc[[2]].copy()
        previous['Execution Doc #'] = 'D1'
        row = audit(i, pd.concat([t,previous])).iloc[0]
        self.assertFalse(row.previous_negative_proxy)
        self.assertEqual(row.verdict,'previous_negative_not_supported')

    def test_unsatisfactory_does_not_count_as_satisfactory(self):
        i, t = self.fixture(f'During {TASK} was found scissors with excessive play')
        t.loc[0,'Sign Off Remarks'] = 'Inspection with unsatisfactory result'
        self.assertFalse(audit(i,t).previous_satisfactory.iloc[0])

    def test_condition_on_other_component_is_not_transferred(self):
        flags = description_flags(['Scissor inspected', 'During inspection was found window out of limit'], TASK)
        self.assertFalse(flags['exceeded_limit'])

    def test_document_support_still_requires_unit_review(self):
        i, t = self.fixture(f'During {TASK} was found scissors with excessive play')
        self.assertEqual(audit(i,t).verdict.iloc[0],
                         'document_supported_candidate_requires_unit_mode_review')


if __name__ == '__main__':
    unittest.main()
