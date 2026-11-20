"""Check screening attribution and preserve ambiguous evidence."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'analysis'))
from removal_labels import screen, category, token_present, audit


class TestRemovalLabels(unittest.TestCase):
    def test_reference_boundaries(self):
        self.assertTrue(token_present('ABC-123', 'removed ABC-123.'))
        self.assertFalse(token_present('ABC-123', 'removed ABC-1234'))
        self.assertFalse(token_present(float('nan'), 'nan'))

    def test_unrelated_component_condition_is_not_transferred(self):
        flags = screen('Window was found inoperative', '3G6230A00833', 'S123')
        self.assertFalse(flags['functional'])
        self.assertFalse(flags['relevant'])

    def test_mixed_condition_not_resolved_by_priority(self):
        flags = screen('Scissors near the limit and excessive play on another scissors',
                       '3G6230A00833','S123')
        self.assertEqual(category(flags),'mixed_document_evidence')

    def test_damage_does_not_imply_functional_loss(self):
        flags = screen('Damper with corrosion damage', '3G6220V02051','S123')
        self.assertTrue(flags['damage'])
        self.assertFalse(flags['functional'])
        self.assertEqual(category(flags),'damage_evidence')

    def test_aircraft_and_date_protect_linkage(self):
        spell = pd.DataFrame({'Part #':['3G6230A00833'],'Serial #':['S123'],
             'Aircraft #':['AC-01'],'att':[pd.Timestamp('2024-01-01')],
             'rem':[pd.Timestamp('2024-02-01')],'event':[1], 'source':['in_window_removed']})
        removals = spell.assign(**{'Source Doc #':'D1'})
        tasks = pd.DataFrame({'Aircraft #':['AC-02','AC-01','AC-01'],
             'Execution Doc #':['D1']*3,'Task #':['NST1','NST2','NST3'],
             'd':pd.to_datetime(['2024-02-01','2024-02-10','2024-02-02']),
             'Task Description':['Scissors excessive play','Scissors inoperative','Scissors near limit']})
        rows, evidence = audit(spell,removals,tasks,['3G6230A00833'])
        self.assertEqual(len(evidence),1)
        self.assertEqual(evidence.task.iloc[0],'NST3')
        self.assertEqual(rows.category.iloc[0],'margin_evidence')


if __name__ == '__main__':
    unittest.main()
