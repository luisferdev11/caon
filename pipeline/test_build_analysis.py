"""Pruebas del esqueleto build_analysis (partes puras)."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_analysis as ba

SB_MATCH = {'match_id': 7, 'match_date': '2024-03-01', 'home_score': 2, 'away_score': 1,
            'home_team': {'home_team_id': 1, 'home_team_name': 'América'},
            'away_team': {'away_team_id': 2, 'away_team_name': 'Pachuca'}}


class BuildAnalysisTests(unittest.TestCase):
    def test_match_window(self):
        self.assertEqual(ba.match_window('2025-06-30'), 'oficial')
        self.assertEqual(ba.match_window('2025-07-01'), 'epilogo')
        self.assertEqual(ba.match_window('2026-07-02'), 'temprano')

    def test_context_matches(self):
        rows = ba.context_matches([{'mid': 7, 'side': 'home', 'date': '2024-03-01'}], {7: SB_MATCH})
        self.assertEqual(rows, [{'id': 7, 'date': '2024-03-01', 'window': 'oficial', 'venue': 'local',
                                 'opponent': 'Pachuca', 'score': [2, 1], 'team_id': 1}])

    def test_replay_meta(self):
        meta = ba.replay_meta(SB_MATCH)
        self.assertEqual((meta['home_id'], meta['away_id'], meta['home_score'], meta['match_id']), (1, 2, 2, 7))

    def test_entities_to_build(self):
        ents = [{'id': 'ame_jardine', 'kind': 'real'}, {'id': 'x', 'kind': 'real'}, {'id': 'barca', 'kind': 'opendata'}]
        self.assertEqual(ba.entities_to_build(ents, has_data=lambda e: e['id'] == 'x'), ['ame_jardine', 'x'])

    def test_enforce_budget_drops_largest_topic(self):
        payload = {'meta': {'id': 'a'}, 'big': {'v': 'x' * 500}, 'small': {'v': 1}}
        out, warnings = ba.enforce_budget(payload, limit=200)
        self.assertEqual(out['small'], {'v': 1})
        self.assertIsNone(out['big']['valor'])
        self.assertIn('presupuesto', out['big']['motivo'])
        self.assertTrue(warnings)
        self.assertLessEqual(len(json.dumps(out, ensure_ascii=False).encode('utf-8')), 200)

    def test_index_by_model_id_uses_display(self):
        ents = [{'id': 'juárez_lema', 'team': 'Juárez', 'coach_key': 'Lema', 'matches': []}]
        out = ba.index_by_model_id(ents, lambda e: ('juarez_lema', 'Juárez · Lema', 'Lema'))
        self.assertEqual(list(out), ['juarez_lema'])
        self.assertEqual(out['juarez_lema']['coach'], 'Lema')

    def test_run_build_step_ends_with_analysis(self):
        import run
        self.assertTrue(run.STEPS['build'][0][-1].endswith('build_model.py'))
        self.assertTrue(run.STEPS['build'][-1][-1].endswith('build_analysis.py'))


if __name__ == '__main__':
    unittest.main()
