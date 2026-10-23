"""Tests de analytics.a4_common y analytics.a4_reference (registros, percentiles, caché, referencia)."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import analytics
import framework
from analytics import a4_common as ac
from analytics import a4_reference as ar
from fixtures import a4_match as fx


def ctx(rows=None, league_ref=None):
    rows = rows if rows is not None else [{'id': fx.MID, 'date': '2024-01-01', 'window': 'oficial',
                                           'team_id': fx.US, 'opponent': 'Rival FC', 'venue': 'local'}]
    an, ev = fx.an(), fx.events()
    return analytics.EntityContext(entity_id='ent', label='Ent', team='X', coach='c', matches=rows,
                                   load_an=lambda m: an, load_events=lambda m: ev, load_f360=lambda m: None,
                                   league_ref=league_ref or {})


class TestNumbers(unittest.TestCase):
    def test_pct_rank_with_ties(self):
        self.assertEqual(ac.pct_rank(5, [1, 5, 9, 10]), 37.5)
        self.assertIsNone(ac.pct_rank(None, [1]))
        self.assertIsNone(ac.pct_rank(3, []))

    def test_pearson(self):
        self.assertAlmostEqual(ac.pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)
        self.assertIsNone(ac.pearson([1, 2], [1, 2]))
        self.assertIsNone(ac.pearson([1, 1, 1], [1, 2, 3]))

    def test_ratio(self):
        self.assertEqual(ac.ratio(1, 4, 100), 25.0)
        self.assertIsNone(ac.ratio(1, 0))


class TestRecorder(unittest.TestCase):
    def test_record_contract_ref_and_scope(self):
        rec = ac.Recorder('ent', 'oficial', {'k': [1.0, 2.0, 3.0]})('field_tilt', 2.5, 10, '%',
                                                                           scope='s', ref_key='k')
        self.assertEqual(framework.check_metric_record(rec), [])
        self.assertEqual((rec['entity'], rec['scope'], rec['ref_pct'], rec['ref_n']), ('ent', 's', 66.7, 3))

    def test_missing_value_has_reason_and_no_ref(self):
        rec = ac.Recorder('ent', 'oficial', {'k': [1.0]})('field_tilt', None, 0, '%', ref_key='k')
        self.assertIsNone(rec['value'])
        self.assertTrue(rec['motivo'])
        self.assertNotIn('ref_pct', rec)

    def test_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            ac.Recorder('ent', 'oficial')('no_existe', 1.0, 1, 'x')


class TestWindowsAndPlayers(unittest.TestCase):
    def test_window_facts_groups_and_caches(self):
        c = ctx()
        wf = ac.window_facts(c)
        self.assertEqual(list(wf), ['oficial'])
        self.assertEqual(wf['oficial']['agg']['n']['partidos'], 1)
        self.assertIs(ac.match_facts(c, fx.MID), ac.match_facts(c, fx.MID))

    def test_rows_without_data_are_dropped(self):
        c = ctx(rows=[{'id': 1, 'window': 'oficial', 'team_id': fx.US}])
        c.load_an = lambda m: None
        self.assertEqual(ac.window_facts(c), {})

    def test_player_names_prefer_nickname(self):
        rows = [{'id': fx.MID}]
        names = ac.player_names(rows, {11, 12}, lambda m: fx.lineups())
        self.assertEqual(names, {11: 'Defensa', 12: 'Medio'})

    def test_top_players(self):
        top = ac.top_players({11: 3, 12: 5, 99: 1}, [{'id': fx.MID}], key=lambda v: -v, limit=2,
                             lineups_fn=lambda m: fx.lineups())
        self.assertEqual([(p['player_id'], p['n'], p['jugador']) for p in top], [(12, 5, 'Medio'), (11, 3, 'Defensa')])


class TestReference(unittest.TestCase):
    def test_unit_counts_groups_team_season_and_min_matches(self):
        facts = ac.cached_facts(lambda m: fx.an(), lambda m: fx.events(), lambda m: None, fx.MID)
        units = ar.unit_counts([1, 2, 3], lambda m: facts, {1: 'A', 2: 'A', 3: 'B'}, min_matches=2)
        self.assertEqual(set(units), {f'{fx.US}:A', f'{fx.THEM}:A'})
        self.assertEqual(units[f'{fx.US}:A']['partidos'], 2)

    def test_official_only_drops_matches_after_the_window_and_without_date(self):
        dates = {1: '2025-06-30', 2: '2025-07-01', 3: '2023-08-01'}
        self.assertEqual(ar.official_only([1, 2, 3, 4], dates, '2025-06-30'), [1, 3])

    def test_reference_is_labelled_official_window(self):
        self.assertIn('ventana oficial', ar.REF_LABEL)

    def test_populations_apply_values_fn(self):
        units = {'a': {'x': 1}, 'b': {'x': 3}, 'c': {'x': 0}}
        pops = ar.populations(units, lambda n: {'k': (n['x'] or None, 1)})
        self.assertEqual(sorted(pops['k']), [1, 3])

    def test_injected_units_win(self):
        c = ctx(league_ref={'a4_unidades': {'u': {'x': 2}}})
        self.assertEqual(ar.populations_for(c, lambda n: {'k': (n['x'], 1)}), {'k': [2]})

    def test_disk_cache_signature(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'ref.json'
            p.write_text(json.dumps({'firma': ar.signature(ar.official_only(ar.an_match_ids(), ar.match_dates())),
                                     'unidades': {'u': {}}}),
                         encoding='utf-8')
            self.assertEqual(ar.load_units(p, build=False), {'u': {}})
            p.write_text(json.dumps({'firma': 'otra', 'unidades': {'u': {}}}), encoding='utf-8')
            self.assertEqual(ar.load_units(p, build=False), {})


if __name__ == '__main__':
    unittest.main()
