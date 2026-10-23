"""Tests de analytics.context_club ("¿Jardine o el club?")."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analytics import context_club

COLS = {'posesion': 'team_match_possession', 'presion': 'team_match_ppda', 'xg': 'team_match_np_xg'}


def _stats(pos, ppda, xg):
    return {'team_match_possession': pos, 'team_match_ppda': ppda, 'team_match_np_xg': xg}


def _league():
    """América previa: posesión 0.45; Jardine en San Luis y en América: 0.58–0.60; PPDA igual en todos."""
    spec = {'ame_solari': (1, 0.45), 'ame_ortiz': (2, 0.46), 'slp_jardine': (3, 0.58), 'ame_jardine': (1, 0.60)}
    rows, stats = {}, {}
    for k, (team, pos) in spec.items():
        base = 1000 * list(spec).index(k)
        rows[k] = [{'id': base + i, 'team_id': team, 'window': 'oficial'} for i in range(12)]
        for i in range(12):
            stats[(base + i, team)] = _stats(pos + 0.01 * (i % 3 - 1), 10.0 + 0.5 * (i % 2), 1.2 + 0.1 * (i % 2))
    units = {u: [{'posesion': 0.40 + 0.02 * u, 'presion': 9.0 + u * 0.2, 'xg': 1.0 + 0.05 * u}] * 12
             for u in range(10)}
    return {'team_stats': stats, 'entity_rows': lambda eid: rows.get(eid, []), 'league_units': units}


class ClubOrCoachTest(unittest.TestCase):
    def setUp(self):
        self.out = context_club.club_or_coach('ame_jardine', _league(), keys=tuple(COLS), cols=COLS)

    def test_pairs_and_deltas(self):
        pares = {p['otro']: p for p in self.out['pares']}
        self.assertEqual(set(pares), {'ame_solari', 'ame_ortiz', 'slp_jardine'})
        sol = pares['ame_solari']['metricas']['posesion']
        self.assertAlmostEqual(sol['dif'], 0.15, places=4)
        self.assertTrue(sol['supera_ruido'])
        self.assertEqual(pares['ame_solari']['n_otro'], 12)

    def test_verdicts(self):
        rasgos = {r['metrica']: r for r in self.out['rasgos']}
        self.assertEqual(rasgos['posesion']['lectura'], 'rasgo de Jardine')
        self.assertEqual(rasgos['presion']['lectura'], 'sin señal clara')
        self.assertIn('ame_jardine', rasgos['posesion']['pct'])
        self.assertTrue(rasgos['posesion']['texto'])
        self.assertEqual(self.out['window'], 'oficial')
        self.assertIn('descriptiv', self.out['nota'])

    def test_verdict_rule(self):
        self.assertEqual(context_club.verdict(80, [30, 35], 78, [True, True], False), 'rasgo de Jardine')
        self.assertEqual(context_club.verdict(32, [30, 35], 78, [False, False], True), 'rasgo del club')
        self.assertEqual(context_club.verdict(80, [30, 35], 78, [True, False], False), 'sin señal clara')

    def test_missing_entity(self):
        league = _league()
        league['entity_rows'] = lambda eid: [] if eid == 'slp_jardine' else _league()['entity_rows'](eid)
        out = context_club.club_or_coach('ame_jardine', league, keys=tuple(COLS), cols=COLS)
        self.assertIsNone(out['rasgos'])
        self.assertTrue(out['motivo'])


if __name__ == '__main__':
    unittest.main()
