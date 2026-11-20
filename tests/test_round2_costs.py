"""T4 acceptance checks: unique removal, missingness and parameter schema."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'analysis'))
from round2_costs import single_removal_documents,summarize,validate_parameters


class TestRound2Costs(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame({'Aircraft #':['A']*4,'Source Doc #':['D1','D2','D2','D3'],
            'Part #':['PN']*4,'event':[1,1,0,1],'document_linked':[True]*4,
            'mh_row_sum':[np.nan,6.,6.,4.],'mh_task_max_sum':[np.nan,3.,3.,4.],
            'mh_row_sum_equal_share':[np.nan,3.,3.,4.],
            'mh_task_max_sum_equal_share':[np.nan,1.5,1.5,4.]})

    def test_scheduled_removal_also_breaks_single_document_rule(self):
        selected=single_removal_documents(self.fixture())
        self.assertEqual(set(selected['Source Doc #']),{'D1','D3'})

    def test_missing_mh_not_counted_as_zero(self):
        events=self.fixture()
        stats=summarize(single_removal_documents(events),events)
        row=stats[(stats.cohort=='single_document')&(stats.aggregation=='row_sum')].iloc[0]
        self.assertEqual(row.documents,2)
        self.assertEqual(row.n_observed,1)
        self.assertEqual(row['median'],4.)

    def test_parameter_contract(self):
        p=pd.DataFrame([dict(parametro='rate',valor_central='AUTOR_DEFINIR',
            faixa_min='AUTOR_DEFINIR',faixa_max='AUTOR_DEFINIR',fonte='AUTOR_DEFINIR'),
            dict(parametro='mh',valor_central=4,faixa_min=2,faixa_max=5,fonte='dados')])
        validate_parameters(p)
        p.loc[1,'faixa_max']=3
        with self.assertRaises(ValueError):
            validate_parameters(p)


if __name__=='__main__':
    unittest.main()
