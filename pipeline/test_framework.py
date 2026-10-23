"""Tests del marco analítico canónico (framework.py) y del registro de analítica."""
import pathlib
import random
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import extract
import framework as fw

from pipeline import analytics

REQUIRED_KEYS = {'nombre', 'definicion', 'formula', 'unidad', 'limites', 'fuente'}


class ZoneTests(unittest.TestCase):
    def test_zone_identical_to_extract_on_10k_points(self):
        rng = random.Random(7)
        for _ in range(10000):
            loc = [rng.uniform(-5, 125), rng.uniform(-5, 85)]
            self.assertEqual(fw.zone(loc), extract.zone(loc), loc)

    def test_transition_window_matches_extract(self):
        self.assertEqual(fw.TRANSITION_PHASE_S, extract.T_WINDOW)
        self.assertEqual(fw.OUTCOME_WINDOW_S, 15.0)


class HelperTests(unittest.TestCase):
    def test_to_frame_flips_and_is_involution(self):
        self.assertEqual(fw.to_frame([30.0, 20.0], flip=True), [90.0, 60.0])
        self.assertEqual(fw.to_frame([30.0, 20.0], flip=False), [30.0, 20.0])
        self.assertEqual(fw.to_frame(fw.to_frame([1.5, 2.5], True), True), [1.5, 2.5])

    def test_third(self):
        self.assertEqual(fw.third(39.9), 'propio')
        self.assertEqual(fw.third(40), 'medio')
        self.assertEqual(fw.third(80), 'final')

    def test_minute_bin(self):
        self.assertEqual(fw.minute_bin(0, 1), '0-15')
        self.assertEqual(fw.minute_bin(15, 1), '0-15')
        self.assertEqual(fw.minute_bin(16, 1), '16-30')
        self.assertEqual(fw.minute_bin(47, 1), '31-45+')
        self.assertEqual(fw.minute_bin(46, 2), '46-60')
        self.assertEqual(fw.minute_bin(95, 2), '76-90+')
        self.assertEqual(fw.minute_bin(100, 3), 'prorroga')
        self.assertIsNone(fw.minute_bin(120, 5))

    def test_rival_tier(self):
        rows = [{'team_id': i, 'team_season_xgd_pg': float(i)} for i in range(1, 19)]
        self.assertEqual(fw.rival_tier(18, rows), 'alto')
        self.assertEqual(fw.rival_tier(13, rows), 'alto')
        self.assertEqual(fw.rival_tier(12, rows), 'medio')
        self.assertEqual(fw.rival_tier(1, rows), 'bajo')
        self.assertIsNone(fw.rival_tier(99, rows))

    def test_is_danger_sp(self):
        self.assertTrue(fw.is_danger_sp('corner', [119, 1]))
        self.assertTrue(fw.is_danger_sp('fk', [80, 40]))
        self.assertFalse(fw.is_danger_sp('fk', [79.9, 40]))
        self.assertTrue(fw.is_danger_sp('throw', [90, 0]))
        self.assertFalse(fw.is_danger_sp('throw', [89, 0]))

    def test_named_thresholds_distinct(self):
        self.assertEqual(fw.REC_CAMPO_RIVAL_X, 60)
        self.assertEqual(fw.REC_ALTA_X, 80)
        self.assertEqual(fw.PPDA_DEF_MIN_X, 48)
        self.assertEqual(fw.PPDA_OPP_MAX_X, 72)
        self.assertEqual(fw.PACE_FLOOR_S, 0.5)


class DefinitionsTests(unittest.TestCase):
    def test_every_definition_complete(self):
        self.assertGreaterEqual(len(fw.DEFINITIONS), 20)
        for key, d in fw.DEFINITIONS.items():
            self.assertTrue(REQUIRED_KEYS <= set(d), key)
            for k in REQUIRED_KEYS:
                self.assertTrue(str(d[k]).strip(), (key, k))

    def test_core_ids_present(self):
        for key in ('zona', 'posesion', 'field_tilt', 'transicion', 'contraataque', 'perdida',
                    'perdida_costosa', 'ppda', 'rec_campo_rival', 'rec_alta', 'rival_tier', 'ventana'):
            self.assertIn(key, fw.DEFINITIONS)

    def test_metric_record_validation(self):
        good = {'id': 'ppda', 'value': 9.1, 'n': 30, 'unit': 'pases', 'source': 'eventos', 'window': 'oficial'}
        self.assertEqual(fw.check_metric_record(good), [])
        self.assertTrue(fw.check_metric_record(dict(good, id='inventada')))
        self.assertTrue(fw.check_metric_record(dict(good, window='otra')))


class RegistryTests(unittest.TestCase):
    def tearDown(self):
        analytics._clear_registry_for_tests()

    def test_register_and_build_all_isolates_errors(self):
        analytics._clear_registry_for_tests()
        analytics.register('ok', lambda ctx: {'n': len(ctx.matches)})
        analytics.register('boom', lambda ctx: 1 / 0)
        ctx = analytics.EntityContext('e', 'E', 'T', 'C', matches=[{'id': 1, 'window': 'oficial'}])
        out = analytics.build_all(ctx)
        self.assertEqual(out['ok'], {'n': 1})
        self.assertIn('ZeroDivisionError', out['boom']['error'])
        self.assertEqual(ctx.match_ids('oficial'), [1])
        self.assertEqual(ctx.match_ids('epilogo'), [])

    def test_registering_a_topic_during_the_run_does_not_break_it(self):
        analytics._clear_registry_for_tests()

        def first(ctx):
            analytics.register('late', lambda c: {'late': True})
            return {'ok': 1}
        analytics.register('first', first)
        ctx = analytics.EntityContext('e', 'E', 'T', 'C')
        out = analytics.build_all(ctx)
        self.assertEqual(out['first'], {'ok': 1})
        self.assertIn('late', analytics.topics())

    def test_events_cache_loads_each_match_once_and_is_bounded(self):
        calls = []

        def loader(mid):
            calls.append(mid)
            return [{'mid': mid}]
        ctx = analytics.EntityContext('e', 'E', 'T', 'C', load_events=loader, events_cache_size=2)
        for mid in (1, 2, 1, 2, 1):
            ctx.load_events(mid)
        self.assertEqual(calls, [1, 2])
        ctx.load_events(3)          # expulsa el menos reciente
        ctx.load_events(1)          # 1 se usó después que 2: sigue en caché
        ctx.load_events(2)          # 2 ya salió: se vuelve a leer
        self.assertEqual(calls, [1, 2, 3, 2])
        ctx.clear_events_cache()
        ctx.load_events(1)
        self.assertEqual(calls[-1], 1)
        self.assertEqual(len(calls), 5)

    def test_events_cache_can_be_disabled(self):
        calls = []
        ctx = analytics.EntityContext('e', 'E', 'T', 'C', load_events=lambda m: calls.append(m) or [], events_cache_size=0)
        ctx.load_events(1)
        ctx.load_events(1)
        self.assertEqual(calls, [1, 1])



class MarcoDocTests(unittest.TestCase):
    def test_render_marco_has_every_definition_and_sections(self):
        text = fw.render_marco()
        for key in fw.DEFINITIONS:
            self.assertIn(f'`{key}`', text)
        for sec in ('## Supuestos', '## Alcance', '## Límites', '## Umbrales con nombre'):
            self.assertIn(sec, text)

    def test_doc_on_disk_is_current(self):
        doc = HERE.parent / 'docs' / 'MARCO_ANALITICO.md'
        self.assertEqual(doc.read_text(encoding='utf-8'), fw.render_marco())

    def test_framework_payload_json_safe(self):
        import json
        json.dumps(fw.framework_payload(), ensure_ascii=False, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
