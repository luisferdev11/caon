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

    def test_run_build_step_runs_analysis_after_model(self):
        import run
        names = [c[-1].rsplit('/', 1)[-1] for c in run.STEPS['build']]
        self.assertLess(names.index('build_model.py'), names.index('build_analysis.py'))
        self.assertEqual(names[-1], 'story.py')

    def test_replay_has_no_adapter_any_more(self):
        self.assertFalse(hasattr(ba, 'replay_ctx'))
        self.assertFalse(hasattr(ba, 'replay_meta'))


REPLAY = {'resumen': {'n': 2}, 'por_torneo': [], 'por_ventana': {}, 'textos': {'veredicto': {}},
          'partidos': [{'match_id': 7, 'xpts': 1.5, 'ficha': {'merecio': {}}}, {'match_id': 8, 'xpts': 0.4, 'ficha': {}}]}


class ReplaySplitTests(unittest.TestCase):
    def test_split_replay_separates_summary_rows_and_cards(self):
        summary, light, cards = ba.split_replay(REPLAY, 'ame_jardine')
        self.assertNotIn('partidos', summary)
        self.assertEqual(summary['resumen'], {'n': 2})
        self.assertEqual(summary['archivo'], 'replay/ame_jardine.json')
        self.assertTrue(all('ficha' not in r for r in light['partidos']))
        self.assertEqual(sorted(cards), [7, 8])
        self.assertIn('ficha', cards[7])
        self.assertIn('textos', cards[7])

    def test_publish_replay_writes_files_and_first_entity_keeps_the_card(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            written: set = set()
            ba.publish_replay(root, 'ame_jardine', REPLAY, cards=True, written=written)
            other = json.loads(json.dumps(REPLAY))
            other['partidos'][0]['xpts'] = 9
            ba.publish_replay(root, 'pac_almada', other, cards=True, written=written)
            self.assertTrue((root / 'replay' / 'ame_jardine.json').exists())
            self.assertTrue((root / 'replay' / 'pac_almada.json').exists())
            self.assertEqual(json.loads((root / 'matches' / '7.json').read_text(encoding='utf-8'))['xpts'], 1.5)
            self.assertNotIn('ficha', json.loads((root / 'replay' / 'ame_jardine.json').read_text(encoding='utf-8'))['partidos'][0])

    def test_publish_replay_without_cards_writes_only_the_replay_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            ba.publish_replay(root, 'x', REPLAY, cards=False, written=set())
            self.assertTrue((root / 'replay' / 'x.json').exists())
            self.assertFalse((root / 'matches').exists())

    def test_replay_error_payload_is_left_untouched(self):
        summary, light, cards = ba.split_replay({'error': 'boom'}, 'x')
        self.assertEqual((summary, light, cards), ({'error': 'boom'}, None, {}))


if __name__ == '__main__':
    unittest.main()
