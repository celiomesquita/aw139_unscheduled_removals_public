"""Verify missingness, allocation and interval bounds in A6."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'analysis'))
from event_costs import document_labour, flight_gaps, event_inputs


class TestEventCosts(unittest.TestCase):
    def test_missing_mh_not_zero(self):
        t=pd.DataFrame({'Aircraft #':['AC1'],'Execution Doc #':['D1'],
                        'Task #':['T1'],'Tot Man Hours':[np.nan]})
        result=document_labour(t).iloc[0]
        self.assertTrue(pd.isna(result.mh_row_sum))
        self.assertTrue(pd.isna(result.mh_task_max_sum))
        self.assertEqual(result.mh_observed_rows,0)

    def test_repeated_task_aggregation_is_visible(self):
        t=pd.DataFrame({'Aircraft #':['AC1']*3,'Execution Doc #':['D1']*3,
                        'Task #':['T1','T1','T2'],'Tot Man Hours':[2.,3.,4.]})
        result=document_labour(t).iloc[0]
        self.assertEqual(result.mh_row_sum,9.)
        self.assertEqual(result.mh_task_max_sum,7.)

    def test_equal_allocation_conserves_document_mh(self):
        r=pd.DataFrame({'Aircraft #':['AC1']*2,'Source Doc #':['D1']*2,
                        'rem':pd.to_datetime(['2024-01-01']*2)})
        t=pd.DataFrame({'Aircraft #':['AC1'],'Execution Doc #':['D1'],
                        'Task #':['T1'],'Tot Man Hours':[8.]})
        visits=pd.DataFrame({'Aircraft #':['AC1'],'start':pd.to_datetime(['2024-01-01']),
                             'end':pd.to_datetime(['2024-01-01'])})
        result=event_inputs(r,document_labour(t),visits)
        self.assertEqual(result.mh_row_sum_equal_share.sum(),8.)
        self.assertTrue(result.inside_visit_proxy.all())

    def test_next_flight_dates_and_same_day_ambiguity(self):
        r=pd.DataFrame({'Aircraft #':['AC1','AC1','AC2'],'rem':pd.to_datetime(['2024-01-01']*3),
                        'event':[1]*3})
        f=pd.DataFrame({'Aircraft #':['AC1','AC1','AC2'],
                        'Flight Date':['01/01/2024','04/01/2024','04/01/2024'],'Hours':[1.,1.,1.]})
        g=flight_gaps(r,f).set_index('aircraft')
        self.assertEqual(len(g),2)
        self.assertEqual(g.loc['AC1','removals'],2)
        self.assertEqual(g.loc['AC1','gap_lower_hours'],0)
        self.assertEqual(g.loc['AC2','gap_lower_hours'],48)
        self.assertEqual(g.loc['AC2','gap_upper_hours'],96)

    def test_window_end_and_missing_hours(self):
        r=pd.DataFrame({'Aircraft #':['AC1'],'rem':pd.to_datetime(['2024-01-01']),'event':[1]})
        f=pd.DataFrame({'Aircraft #':['AC1'],'Flight Date':['02/01/2024'],'Hours':[np.nan]})
        g=flight_gaps(r,f,end=pd.Timestamp('2024-01-04')).iloc[0]
        self.assertFalse(g.later_flight_observed)
        self.assertTrue(pd.isna(g.gap_upper_hours))
        self.assertEqual(g.gap_lower_hours,72)


if __name__=='__main__':
    unittest.main()
