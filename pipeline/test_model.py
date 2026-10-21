import gzip
import json
import tempfile
import unittest
from pathlib import Path

from build_model import Acc, my_metrics, publish_model
from check_model import validate
from extract import new_team
from metric_utils import fit_calibration


class ModelTests(unittest.TestCase):
    def test_same_population_and_utf8(self):
        a, d = Acc(), Acc()
        a.add(new_team()); d.add(new_team())
        entity = {'id': 'america', 'label': 'América · Histórico · Posesión', 'n': 1,
                      'att': a.to(), 'dfn': d.to(False), 'style': {}, 'kind': 'opendata'}
        model = json.loads(json.dumps({'entities': [entity]}, ensure_ascii=False, allow_nan=False))
        self.assertEqual(validate(model)[0], [])
        self.assertEqual(model['entities'][0]['label'], entity['label'])
        entity['n'] = 0
        self.assertTrue(validate({'entities': [entity]})[0])

    def test_no_matches(self):
        self.assertEqual(Acc().to()['matches'], 0)
        self.assertEqual(my_metrics({}), {})

    def test_denominators_not_imputed(self):
        metrics = my_metrics({'passes': 20, 'opp_passes': 30, 'ppda_den': 0})
        self.assertIsNone(metrics['team_match_ppda'])
        self.assertIsNone(metrics['team_match_directness'])
        self.assertEqual(metrics['team_match_possession'], .4)
        self.assertEqual(metrics['team_match_counterpressures'], 0)

    def test_calibration_absence_and_constants(self):
        self.assertIsNone(fit_calibration([])[0])
        self.assertIsNone(fit_calibration([(1, 2)] * 3)[0])
        fit, reason = fit_calibration([(1, 2), (2, 4), (3, 6), (float('nan'), 3)])
        self.assertIsNone(reason)
        self.assertAlmostEqual(fit[2], 1)

    def test_core_formulas(self):
        import math
        m = {'passes': 60, 'opp_passes': 40, 'dir_fwd': 30, 'dir_tot': 100,
                 'pace2_sum': 12, 'pace2_n': 4, 'def_x': 200, 'def_n': 4,
                 'pressures': 10, 'opp_passes_own60': 20, 'ppda_den': 5,
                 'counterpressures': 4, 'gk_long': 2, 'gk_passes': 8, 'crosses_box': 3,
                 'counter_shots2': 2, 'high_press_shots': 1, 'np_xg': 1.2, 'np_xga': .8, 'sp_xg': .3}
        expected = {'possession': .6, 'directness': .3, 'pace_towards_goal': 3,
                        'defensive_distance': 50, 'pressures_adj': 25, 'ppda': math.log(4),
                        'counterpressures': 4, 'gk_long_pass_ratio': .25, 'crosses_into_box': 3,
                        'counter_attacking_shots': 2, 'high_press_shots': 1, 'np_xg': 1.2, 'np_xg_conceded': .8, 'sp_xg': .3}
        actual = my_metrics(m)
        for key, value in expected.items(): self.assertAlmostEqual(actual['team_match_' + key], value)
        self.assertIsNone(my_metrics({'passes': None})['team_match_possession'])
        self.assertIsNone(my_metrics({'passes': float('nan')})['team_match_possession'])

    def test_recursive_validation(self):
        invalid, _ = validate({'entities': [None, {'id': 'broken', 'n': None, 'att': None, 'dfn': None, 'style': None,
                                                     'context': {'venue': {'home': {'matches': 1}}}}]})
        self.assertGreaterEqual(len(invalid), 4)
        e = {'id': 'test', 'n': 1, 'att': {'matches': 1}, 'dfn': {'matches': 1}, 'style': {'posesion': 101}, 'raw': {'xg': float('inf')}}
        errors, _ = validate({'entities': [e]})
        self.assertTrue(any('percentil' in x for x in errors))
        self.assertTrue(any('no finito' in x for x in errors))
        e.update(style={}, raw={}, label='AmÃ©rica')
        self.assertTrue(any('codificación' in x for x in validate({'entities': [e]})[0]))

    def test_generation_backup_and_invalid_model_preserved(self):
        e = {'id': 'ame', 'label': 'América', 'n': 0, 'att': {'matches': 0}, 'dfn': {'matches': 0}, 'style': {}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.json'
            path.write_bytes(b'{"previous":true}')
            publish_model({'entities': [e]}, path)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['entities'][0]['label'], 'América')
            self.assertEqual(gzip.decompress(next(Path(folder).glob('*.gz')).read_bytes()), b'{"previous":true}')
            previous = path.read_bytes()
            e['n'] = 2
            with self.assertRaises(ValueError): publish_model({'entities': [e]}, path)
            self.assertEqual(path.read_bytes(), previous)

    def test_publish_validates_full_but_writes_slim_payload(self):
        e = {'id': 'ame', 'label': 'América', 'n': 0, 'att': {'matches': 0}, 'dfn': {'matches': 0}, 'style': {}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.json'
            publish_model({'entities': [e]}, path, payload={'entities': [{'id': 'ame'}], 'slim': True})
            self.assertTrue(json.loads(path.read_text(encoding='utf-8'))['slim'])

    def test_check_model_merges_split_entity_files(self):
        from check_model import load_full_model, size_errors
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.json'
            path.write_text(json.dumps({'entities': [{'id': 'a', 'n': 1}]}), encoding='utf-8')
            (Path(folder) / 'entities').mkdir()
            (Path(folder) / 'entities' / 'a.json').write_text(json.dumps({'id': 'a', 'temporal': {'x': 1}}), encoding='utf-8')
            model = load_full_model(path)
            self.assertEqual(model['entities'][0]['temporal'], {'x': 1})
            self.assertEqual(size_errors(path, limit=10 ** 6), [])
            self.assertTrue(size_errors(path, limit=5))


if __name__ == '__main__':
    unittest.main()
