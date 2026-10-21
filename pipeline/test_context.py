"""Tests de analytics.context (contexto, ruido por bootstrap y consistencia)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'fixtures'))

from a5_events import THEM, US, an_match
from analytics import context


def _ts(xg, xga, pos=0.5, ppda=10.0):
    return {'team_id': US, 'team_match_np_xg': xg, 'team_match_np_xg_conceded': xga,
            'team_match_possession': pos, 'team_match_ppda': ppda, 'team_match_directness': 0.3,
            'team_match_pace_towards_goal': 2.0, 'team_match_defensive_distance': 40.0,
            'team_match_pressures_adj': 300.0}


def _row(i, venue, score):
    return {'id': i, 'team_id': US, 'venue': venue, 'score': score, 'opponent': 'R', 'window': 'oficial',
            'date': f'2024-01-{i + 1:02d}'}


def _records(n=10):
    recs = []
    for i in range(n):
        home = i % 2 == 0
        row = _row(i, 'local' if home else 'visita', [2, 0] if home else [0, 1])
        recs.append(context.match_record(row, an_match(i), _ts(1.5 if home else 0.5, 0.7),
                                         'alto' if i < 4 else 'bajo', 'regular'))
    return recs


class BandTest(unittest.TestCase):
    def test_band80_brackets_mean_and_is_deterministic(self):
        vals = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        lo, hi = context.band80(vals, seed=3)
        self.assertLess(lo, 3.5)
        self.assertGreater(hi, 3.5)
        self.assertEqual(context.band80(vals, seed=3), [lo, hi])
        self.assertIsNone(context.band80([], seed=3))
        self.assertEqual(context.band80([2.0], seed=3), [2.0, 2.0])

    def test_ratio_band80_pools_matches(self):
        lo, hi = context.ratio_band80([1.0, 3.0], [1.0, 1.0], seed=1)
        self.assertGreaterEqual(lo, 1.0)
        self.assertLessEqual(hi, 3.0)
        self.assertIsNone(context.ratio_band80([1.0], [0.0], seed=1))

    def test_group_stat_against_rest(self):
        g = context.group_stat([3.0] * 5, [1.0] * 5, [0.0] * 5, [1.0] * 5, seed=1)
        self.assertEqual(g['valor'], 3.0)
        self.assertEqual(g['resto'], 0.0)
        self.assertEqual(g['dif'], 3.0)
        self.assertTrue(g['supera_ruido'])
        same = context.group_stat([1.0, 2.0, 3.0], [1.0] * 3, [1.0, 2.0, 3.0], [1.0] * 3, seed=1)
        self.assertFalse(same['supera_ruido'])
        self.assertIsNone(context.group_stat([], [], [1.0], [1.0], seed=1))

    def test_small_group_never_exceeds_noise(self):
        tiny = context.group_stat([9.0] * 2, [1.0] * 2, [0.0, 1.0] * 20, [1.0] * 40, seed=1)
        self.assertFalse(tiny['supera_ruido'])
        self.assertEqual(tiny['confianza'], 'muy baja')


class PossessionGroupsTest(unittest.TestCase):
    def test_state_is_seen_from_protagonist(self):
        g = context.poss_groups(an_match(1), US)
        win = g['marcador']['ganando']
        self.assertAlmostEqual(win['min'], 20.0)
        self.assertAlmostEqual(win['xg_f'], 0.7)
        self.assertAlmostEqual(win['xg_c'], 0.35)
        self.assertEqual((win['f3_own'], win['f3_opp']), (3, 2))
        self.assertAlmostEqual(g['marcador']['empatando']['min'], 10.0)
        self.assertNotIn('perdiendo', g['marcador'])
        self.assertAlmostEqual(g['minuto']['46-60']['min'], 15.0)

    def test_rival_view_flips(self):
        g = context.poss_groups(an_match(1), THEM)
        self.assertIn('perdiendo', g['marcador'])
        self.assertAlmostEqual(g['marcador']['perdiendo']['xg_f'], 0.35)


class SplitTest(unittest.TestCase):
    def test_match_record(self):
        r = _records(2)[0]
        self.assertEqual(r['vals']['puntos'], (3.0, 1.0))
        self.assertEqual(r['vals']['xg'], (1.5, 1.0))
        self.assertAlmostEqual(r['vals']['xg_dif'][0], 0.8)
        self.assertEqual(r['vals']['field_tilt'], (600.0, 10.0))

    def test_venue_split_exceeds_noise(self):
        out = context.split(_records(), 'venue', seed=1)
        loc = out['grupos']['local']['puntos']
        self.assertEqual(loc['valor'], 3.0)
        self.assertEqual(loc['n'], 5)
        self.assertTrue(loc['supera_ruido'])
        self.assertFalse(out['grupos']['local']['xga']['supera_ruido'])

    def test_missing_dimension(self):
        recs = _records()
        for r in recs:
            r['rival_tier'] = None
        out = context.split(recs, 'rival_tier', seed=1)
        self.assertIsNone(out['grupos'])
        self.assertTrue(out['motivo'])

    def test_findings_carry_confidence(self):
        dims = {'localia': context.split(_records(), 'venue', seed=1)}
        found = context.findings(dims, top=5)
        self.assertTrue(found)
        self.assertTrue(all(f['confianza'] == 'baja' for f in found))   # 5 partidos por grupo

    def test_possession_split_rates(self):
        out = context.poss_split(_records(), 'marcador', seed=1)
        win = out['grupos']['ganando']
        self.assertAlmostEqual(win['xg_90']['valor'], 0.7 / 20 * 90)
        self.assertEqual(win['xg_90']['n'], 10)
        self.assertAlmostEqual(win['minutos'], 200.0)


class ConsistencyTest(unittest.TestCase):
    def test_index_and_league_percentile(self):
        own = [{'xg': 1.0 + 0.1 * (i % 3), 'xga': 1.0, 'posesion': 0.5, 'presion': 10.0, 'verticalidad': 0.3}
               for i in range(12)]
        league = {'A': [{'xg': float(i % 4), 'xga': float(i % 5), 'posesion': 0.5, 'presion': 10.0,
                         'verticalidad': 0.3} for i in range(12)]}
        c = context.consistency(own, league, 'oficial', 'ent')
        self.assertEqual(c['id'], 'consistencia')
        self.assertEqual(c['n'], 12)
        self.assertGreaterEqual(c['value'], 0)
        self.assertLessEqual(c['value'], 100)
        self.assertIn('ref_pct', c)
        self.assertEqual(c['dispersion']['xga']['iqr'], 0.0)

    def test_too_few_matches(self):
        c = context.consistency([{'xg': 1.0}], {}, 'oficial', 'ent')
        self.assertIsNone(c['value'])
        self.assertTrue(c['motivo'])


class BuildTest(unittest.TestCase):
    def test_build_with_injected_league(self):
        rows = [_row(i, 'local' if i % 2 == 0 else 'visita', [1, 0] if i % 2 == 0 else [1, 1]) for i in range(6)]
        stats = {(i, US): _ts(1.0 + i / 10, 0.8) for i in range(6)}
        calendar = {i: {'stage': 'Apertura' if i < 4 else 'Apertura - Quarter-finals', 'season_id': 1,
                        'teams': [US, THEM]} for i in range(6)}
        season = {1: [{'team_id': THEM, 'team_season_xgd_pg': 0.5, 'team_season_matches': 17},
                      {'team_id': US, 'team_season_xgd_pg': 0.1, 'team_season_matches': 17}]}

        class Ctx:
            entity_id = 'ent'
            matches = rows
            def __init__(self):
                self.league_ref = {'context': {'team_stats': stats, 'calendar': calendar, 'season_stats': season,
                                               'season_order': [1], 'league_units': {}}}

            def load_an(self, mid):
                return an_match(mid)
        out = context.build(Ctx())
        w = out['ventanas']['oficial']
        self.assertEqual(w['n_partidos'], 6)
        self.assertEqual(set(w['dimensiones']['fase']['grupos']), {'regular', 'liguilla'})
        self.assertEqual(list(w['dimensiones']['rival']['grupos']), ['alto'])
        self.assertEqual(w['general']['xg']['id'], 'xg')
        self.assertEqual(w['general']['xg']['entity'], 'ent')
        self.assertEqual(w['general']['xg']['source'], 'team-stats')
        self.assertIn('metricas', w)
        self.assertEqual(w['metricas']['field_tilt']['id'], 'field_tilt')
        self.assertIsInstance(w['hallazgos'], list)


if __name__ == '__main__':
    unittest.main()
