"""Preserve source integrity when replaying documentary decisions."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'analysis'))
from extended_review import snapshot_hash, validate_decisions


class TestExtendedReview(unittest.TestCase):
    def fixture(self):
        tasks=pd.DataFrame({'Aircraft #':['AC-01','AC-01'], 'Execution Doc #':['D1','D1'],
            'Task #':['INSP','NST1'], 'Task Description':['Inspect','Near limit'],
            'Sign Off Remarks':['Satisfactory','Replaced scissors'],
            'Tech Sign Off Date':['01/02/2024','01/02/2024']})
        q=pd.DataFrame({'audit_id':['R1'],'pn':['PN1'],'serial':['SN1'],
                         'aircraft':['AC-01'],'source_documents':['D1']})
        c=pd.DataFrame({'audit_id':['R1'],'aircraft':['AC-01'],'document':['D1'],
            'evidence_task':['NST1'],'source_sha256':[snapshot_hash(tasks)],
            'documentary_decision':['near_limit'],'detector_reference':['not_stated']})
        return q,tasks,c

    def test_snapshot_ignores_duplicate_rows_and_order(self):
        _,t,_=self.fixture()
        self.assertEqual(snapshot_hash(t),snapshot_hash(pd.concat([t.iloc[::-1],t])))

    def test_changed_repair_remark_invalidates_decision(self):
        q,t,c=self.fixture()
        t.loc[1,'Sign Off Remarks']='Replaced another component'
        result=validate_decisions(q,t,c).iloc[0]
        self.assertEqual(result.review_status,'source_changed_review_required')
        self.assertEqual(result.documentary_decision,'unresolved')

    def test_valid_source_does_not_confirm_physical_failure(self):
        q,t,c=self.fixture()
        result=validate_decisions(q,t,c).iloc[0]
        self.assertEqual(result.review_status,'source_review_completed')
        self.assertFalse(result.unit_confirmed)
        self.assertFalse(result.physical_failure_confirmed)
        self.assertFalse(result.detection_date_confirmed)

    def test_wrong_aircraft_rejected(self):
        q,t,c=self.fixture()
        c.loc[0,'aircraft']='AC-02'
        with self.assertRaises(ValueError):
            validate_decisions(q,t,c)


if __name__=='__main__':
    unittest.main()
