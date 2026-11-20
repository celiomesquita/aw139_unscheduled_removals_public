"""Prevent duplicated labour and silent imputation in candidate attribution."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'analysis'))
from labour_attribution import attribute, identifier_hit, link_strength


class TestLabourAttribution(unittest.TestCase):
    def fixture(self):
        e=pd.DataFrame({'cost_event_id':['C1','C2'],'Part #':['PN001','PN002'],
            'Serial #':['SN111','SN222'],'Aircraft #':['AC1']*2,'Source Doc #':['D1']*2,'event':[1,0]})
        t=pd.DataFrame({'Aircraft #':['AC1']*2,'Execution Doc #':['D1']*2,
            'Task #':['T1','T2'],'Task Description':['Replace SN111 and SN222','Wash airframe'],
            'Sign Off Remarks':['Completed','Completed'],'Tot Man Hours':[8.,3.]})
        return e,t

    def test_shared_task_conserves_budget_and_unrelated_work_not_allocated(self):
        e,t=self.fixture()
        links,ledger,result=attribute(e,t)
        self.assertEqual(links.allocated_mh_row_sum.sum(),8.)
        self.assertEqual(ledger.unallocated_mh_row_sum.sum(),3.)
        self.assertTrue(result.allocated_mh_row_sum.eq(4.).all())
        self.assertEqual(ledger.mh_row_sum.sum(),11.)

    def test_multiple_signoffs_do_not_duplicate_task_in_ledger(self):
        e,t=self.fixture()
        t=pd.concat([t,t.iloc[[0]]],ignore_index=True)
        links,ledger,_=attribute(e,t)
        self.assertEqual(len(ledger),2)
        self.assertEqual(links.allocated_mh_max.sum(),8.)
        self.assertEqual(links.allocated_mh_row_sum.sum(),16.)

    def test_unknown_identifier_not_evidence(self):
        self.assertFalse(identifier_hit('UNKNOWN','UNKNOWN component replaced'))
        self.assertFalse(identifier_hit(np.nan,'nan'))
        self.assertFalse(identifier_hit('SN111','SN1111'))

    def test_replacement_serial_is_distinguished(self):
        row=pd.Series({'Part #':'PN001','Serial #':'SN111','Attached Serial #':'NEW123'})
        strength,reason=link_strength(row,'Installed NEW123')
        self.assertEqual(reason,'installed_serial_reference')
        self.assertEqual(strength,3)

    def test_absent_labour_stays_missing(self):
        e,t=self.fixture()
        t.loc[0,'Tot Man Hours']=np.nan
        _,_,result=attribute(e,t)
        self.assertTrue(result.allocated_mh_row_sum.isna().all())
        self.assertTrue(result.attribution_status.eq('candidate_tasks_missing_mh').all())


if __name__=='__main__':
    unittest.main()
