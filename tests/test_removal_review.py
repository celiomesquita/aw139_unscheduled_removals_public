"""Unit-role and administrative-delay checks for documentary review."""
import sys
import hashlib
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'analysis'))
from removal_review import unit_scope, review


class TestRemovalReview(unittest.TestCase):
    def fixture(self):
        row = pd.Series({'Part #':'S-7200-514-PLB','Serial #':'OLD123',
                          'Aircraft #':'AC-01'})
        task = pd.Series({'Execution Doc #':'D1','Task Description':'OLD123 removed; NEW123 installed'})
        removals = pd.DataFrame({'Aircraft #':['AC-01'],'Source Doc #':['D1'],
                                 'Attached Serial #':['NEW123']})
        return row, task, removals

    def test_both_serial_roles_are_ambiguous(self):
        self.assertEqual(unit_scope(*self.fixture()),'removed_and_installed_serials_present')

    def test_installed_serial_is_not_removed_unit_evidence(self):
        row, task, r = self.fixture()
        task['Task Description'] = 'NEW123 installed'
        self.assertEqual(unit_scope(row,task,r),'installed_serial_present')

    def test_missing_diagnosis_does_not_drop_event(self):
        row, task, r = self.fixture()
        a = pd.DataFrame([row.to_dict() | dict(audit_id='R1', category='condition_unspecified',
                           source_documents='D1', rem=pd.Timestamp('2024-02-01'))])
        t = pd.DataFrame({'Aircraft #':['AC-02'],'Execution Doc #':['D1'],
             'Task #':['NST1'],'Task Description':['OLD123 removed'],
             'd':[pd.Timestamp('2024-02-01')]})
        _, queue = review(a,t,r)
        self.assertEqual(len(queue),1)
        self.assertEqual(queue.review_status.iloc[0],'no_relevant_diagnosis_in_source_document')
        self.assertFalse(queue.endpoint_confirmed.iloc[0])

    def test_plural_vest_and_late_signoff_can_be_retrieved(self):
        row, task, r = self.fixture()
        a = pd.DataFrame([row.to_dict() | dict(audit_id='R1', category='condition_unspecified',
                           source_documents='D1', rem=pd.Timestamp('2024-02-01'))])
        t = pd.DataFrame({'Aircraft #':['AC-01'],'Execution Doc #':['D1'],
             'Task #':['ALNST-019954-2024'],'Task Description':['LIFE VESTS WITH THE COVER TORN.'],
             'd':[pd.Timestamp('2024-02-10')]})
        evidence, queue = review(a,t,r)
        self.assertEqual(evidence.signoff_lag_days.iloc[0],9)
        self.assertFalse(evidence.detection_date_confirmed.iloc[0])
        self.assertEqual(queue.reviewed_diagnoses.iloc[0],1)

    def test_catalog_does_not_apply_to_changed_description(self):
        row, task, r = self.fixture()
        a = pd.DataFrame([row.to_dict() | dict(audit_id='R1', category='condition_unspecified',
                           source_documents='D1', rem=pd.Timestamp('2024-02-01'))])
        t = pd.DataFrame({'Aircraft #':['AC-01'],'Execution Doc #':['D1'],
             'Task #':['NST1'],'Task Description':['OLD123 with damaged cover'],
             'd':[pd.Timestamp('2024-02-01')]})
        catalog = {('NST1',hashlib.sha256(b'old text').hexdigest()):'damage'}
        _, queue = review(a,t,r,catalog=catalog)
        self.assertEqual(queue.reviewed_diagnoses.iloc[0],0)
        digest = hashlib.sha256(b'OLD123 with damaged cover').hexdigest()
        catalog = {('NST1',digest):'damage'}
        _, queue = review(a,t,r,catalog=catalog,unit_decisions={('R1',digest):'unit reviewed'})
        self.assertTrue(queue.unit_confirmed.iloc[0])
        self.assertFalse(queue.endpoint_confirmed.iloc[0])


if __name__ == '__main__':
    unittest.main()
