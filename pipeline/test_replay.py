"""Tests de la repetición con xG (pipeline/analytics/replay.py)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analytics import replay

HOME, AWAY = 1, 2


def shot(team, poss, xg, goal=False, minute=10, kind='Open Play', x=105.0, player='Ana', period=1):
    return {'id': f's{team}-{poss}-{minute}', 'type': {'name': 'Shot'}, 'team': {'id': team},
            'possession': poss, 'minute': minute, 'period': period, 'player': {'name': player},
            'location': [x, 40.0],
            'shot': {'statsbomb_xg': xg, 'type': {'name': kind},
                     'outcome': {'name': 'Goal' if goal else 'Saved'}}}


def touch(team, x, poss=1):
    return {'type': {'name': 'Pass'}, 'team': {'id': team}, 'possession': poss, 'period': 1,
            'minute': 1, 'location': [x, 40.0]}


META = {'match_id': 99, 'home_id': HOME, 'away_id': AWAY, 'home_score': 1, 'away_score': 0}


class PossessionProbTest(unittest.TestCase):
    def test_combines_shots_in_same_possession(self):
        evs = [shot(HOME, 3, 0.5), shot(HOME, 3, 0.5, minute=11), shot(HOME, 4, 0.2)]
        parts = replay.team_chances(evs, HOME)
        self.assertEqual(sorted(round(p, 4) for p in parts['open']), [0.2, 0.75])
        self.assertEqual(parts['pens'], [])

    def test_penalty_tagged_apart_and_shootout_excluded(self):
        evs = [shot(HOME, 3, 0.78, kind='Penalty'), shot(HOME, 9, 0.7, kind='Penalty', period=5)]
        parts = replay.team_chances(evs, HOME)
        self.assertEqual(parts['open'], [])
        self.assertEqual(parts['pens'], [0.78])

    def test_own_goal_fixed_for_beneficiary(self):
        evs = [{'type': {'name': 'Own Goal For'}, 'team': {'id': AWAY}, 'period': 1, 'minute': 30}]
        self.assertEqual(replay.team_chances(evs, AWAY)['own_goals'], 1)
        self.assertEqual(replay.team_chances(evs, HOME)['own_goals'], 0)


class SimulationTest(unittest.TestCase):
    def test_certain_outcomes(self):
        res = replay.simulate_result([1.0], [], 0, 0, draws=2000, seed=1)
        self.assertAlmostEqual(res['p_win'], 1.0)
        res = replay.simulate_result([], [], 0, 0, draws=2000, seed=1)
        self.assertAlmostEqual(res['p_draw'], 1.0)

    def test_seeded_and_sums_to_one(self):
        a = replay.simulate_result([0.3, 0.2], [0.4], 0, 1, draws=5000, seed=7)
        b = replay.simulate_result([0.3, 0.2], [0.4], 0, 1, draws=5000, seed=7)
        self.assertEqual(a, b)
        self.assertAlmostEqual(a['p_win'] + a['p_draw'] + a['p_loss'], 1.0, places=6)

    def test_symmetric_probabilities_close(self):
        res = replay.simulate_result([0.5], [0.5], 0, 0, draws=20000, seed=3)
        self.assertAlmostEqual(res['p_win'], 0.25, delta=0.02)
        self.assertAlmostEqual(res['p_draw'], 0.5, delta=0.02)


class MatchReplayTest(unittest.TestCase):
    def test_surprise_and_xpts(self):
        evs = [shot(HOME, 1, 0.05, goal=True), shot(AWAY, 2, 0.6), shot(AWAY, 3, 0.6)] + \
              [touch(HOME, 90)] + [touch(AWAY, 85) for _ in range(3)]
        rep = replay.match_replay(evs, META, HOME)
        self.assertEqual(rep['actual'], 'G')
        self.assertEqual(rep['points'], 3)
        self.assertTrue(rep['sorpresivo'])
        self.assertLess(rep['xpts'], 1.0)
        self.assertAlmostEqual(rep['dominio']['field_tilt'], 2 / 7, places=4)  # tiros también son acciones con balón
        self.assertAlmostEqual(rep['dominio']['xg_share'], 0.05 / 1.25, places=3)

    def test_away_perspective(self):
        evs = [shot(HOME, 1, 0.9, goal=True)]
        rep = replay.match_replay(evs, META, AWAY)
        self.assertEqual(rep['actual'], 'P')
        self.assertEqual(rep['points'], 0)
        self.assertFalse(rep['sorpresivo'])


class MatchCardTest(unittest.TestCase):
    def test_card_moments_timeline_facts(self):
        evs = [shot(HOME, 1, 0.05, goal=True, minute=12, player='Zendejas'),
               shot(AWAY, 2, 0.45, minute=40, player='Rival'), shot(AWAY, 3, 0.1, minute=80)]
        card = replay.match_card(evs, META, HOME)
        self.assertEqual(card['marcador'], {'propio': 1, 'rival': 0})
        kinds = [(m['minuto'], m['tipo']) for m in card['momentos']]
        self.assertEqual(kinds, [(12, 'gol'), (40, 'gran_ocasion')])
        self.assertEqual(card['xg_acumulado'][-1]['rival'], 0.55)
        self.assertEqual(len(card['datos_curiosos']), 3)
        self.assertTrue(all(isinstance(f, str) and f for f in card['datos_curiosos']))


class BuildTest(unittest.TestCase):
    def test_build_aggregates(self):
        ctx = {'team_id': HOME, 'matches': [{'meta': META, 'events': [shot(HOME, 1, 0.9, goal=True)]}]}
        out = replay.build(ctx)
        self.assertEqual(out['resumen']['n'], 1)
        self.assertEqual(out['resumen']['puntos'], 3)
        self.assertEqual(len(out['partidos']), 1)
        self.assertIn('ficha', out['partidos'][0])


class EntityContextTest(unittest.TestCase):
    def test_build_from_registry_context(self):
        from analytics import EntityContext
        evs = [dict(shot(HOME, 1, 0.9, goal=True), team={'id': HOME, 'name': 'América'}),
               dict(shot(AWAY, 2, 0.1), team={'id': AWAY, 'name': 'Rival'}),
               {'type': {'name': 'Own Goal For'}, 'team': {'id': HOME, 'name': 'América'},
                'period': 2, 'minute': 70}]
        ctx = EntityContext(entity_id='x', label='x', team='América', coach='J',
                            matches=[{'id': 5, 'date': '2024-01-01', 'window': 'oficial'}],
                            load_events=lambda mid: evs)
        out = replay.build(ctx)
        row = out['partidos'][0]
        self.assertEqual(row['ficha']['marcador'], {'propio': 2, 'rival': 0})
        self.assertEqual(row['actual'], 'G')
        self.assertEqual(row['window'], 'oficial')
        self.assertEqual(out['resumen']['n'], 1)


if __name__ == '__main__':
    unittest.main()
