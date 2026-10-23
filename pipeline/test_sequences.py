"""Tests de sequences.build_possessions sobre un partido sintético mínimo."""
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sequences

FIX = json.loads((HERE / 'fixtures' / 'mini_match_events.json').read_text(encoding='utf-8'))


class PossessionTests(unittest.TestCase):
    def setUp(self):
        out = sequences.build_possessions(FIX['events'], FIX['metadata'])
        self.poss = {p['id']: p for p in out['possessions']}
        self.light = out['events_light']

    def test_admin_only_possessions_ignored(self):
        self.assertEqual(sorted(self.poss), [2, 3, 4, 5])

    def test_loss_and_costly_loss(self):
        loss = self.poss[2]['loss']
        self.assertEqual(loss['kind'], 'lossO')
        self.assertEqual(loss['xpass'], 0.9)
        self.assertFalse(loss['under_pressure'])
        self.assertTrue(loss['costly'])
        self.assertTrue(loss['lethal'])
        self.assertEqual(self.poss[2]['end']['type'], 'loss')

    def test_regain_transition_counter(self):
        p = self.poss[3]
        self.assertEqual(p['origin']['type'], 'regain_open')
        self.assertTrue(p['transition'])
        self.assertTrue(p['counter'])
        self.assertEqual(p['opp_pressures'], 1)
        self.assertEqual(p['score_state'], 'empatando')
        self.assertEqual(p['venue'], 'visitante')

    def test_score_state_and_shots(self):
        p = self.poss[4]
        self.assertEqual(p['score_state'], 'perdiendo')
        self.assertTrue(p['box_entry'])
        self.assertAlmostEqual(p['xg'], 0.5)
        self.assertTrue(p['shots'][0]['header'])
        self.assertEqual(p['origin']['type'], 'kickoff')
        self.assertEqual(p['end']['type'], 'shot')

    def test_possession_xg_combines(self):
        self.assertAlmostEqual(sequences.possession_xg([0.5, 0.5]), 0.75)
        self.assertEqual(sequences.possession_xg([]), 0.0)

    def test_events_light(self):
        self.assertEqual(len(self.light['pressures']), 1)
        self.assertTrue(self.light['pressures'][0]['counterpress'])
        self.assertEqual(len(self.light['subs']), 1)
        self.assertEqual(self.light['tactical_shifts'][0]['formation'], 4231)
        self.assertEqual(self.light['regains'][0]['event_id'], 'e4')



def _ev(idx, kind, team, loc, poss=7, body=None, pattern='Regular Play'):
    e = {'id': f'r{idx}', 'index': idx, 'period': 1, 'minute': 10, 'second': idx, 'timestamp': f'00:10:{idx:02d}.000',
         'type': {'name': kind}, 'team': {'id': team}, 'possession': poss, 'possession_team': {'id': team},
         'play_pattern': {'name': pattern}, 'player': {'id': 100 + idx}, 'location': loc}
    if body is not None:
        e[kind.lower()] = body
    return e


class ReachTests(unittest.TestCase):
    """max_x y box_entry solo cuentan acciones completadas (salida/progresión limpia, entradas al área)."""

    def _one(self, events):
        tail = _ev(99, 'Pass', 2, [50, 40], poss=8, body={'end_location': [60, 40]})
        return sequences.build_possessions(events + [tail], {'home_team': {'home_team_id': 1}})['possessions'][0]

    def test_incomplete_pass_does_not_reach_or_enter_the_box(self):
        p = self._one([_ev(1, 'Pass', 1, [30, 40], body={'end_location': [50, 40]}),
                       _ev(2, 'Pass', 1, [50, 40], body={'end_location': [110, 40], 'outcome': {'name': 'Incomplete'}})])
        self.assertEqual(p['max_x'], 50)
        self.assertFalse(p['box_entry'])

    def test_completed_pass_and_carry_reach(self):
        p = self._one([_ev(1, 'Pass', 1, [30, 40], body={'end_location': [70, 40]}),
                       _ev(2, 'Carry', 1, [70, 40], body={'end_location': [104, 40]})])
        self.assertEqual(p['max_x'], 104)
        self.assertTrue(p['box_entry'])

    def test_shot_end_location_is_not_a_reach(self):
        p = self._one([_ev(1, 'Pass', 1, [30, 40], body={'end_location': [60, 40]}),
                       _ev(2, 'Shot', 1, [70, 40], body={'end_location': [120, 40], 'statsbomb_xg': 0.02,
                                                         'outcome': {'name': 'Off T'}})])
        self.assertEqual(p['max_x'], 70)
        self.assertTrue(p['box_entry'])


class LossKindTests(unittest.TestCase):
    """Pérdida como en extract: en juego si el rival reanuda en juego (incl. portero); si no, balón muerto."""

    def _first(self, last, pattern):
        evs = [_ev(1, 'Pass', 1, [30, 40], body={'end_location': [50, 40]}), last,
               _ev(9, 'Pass', 2, [40, 40], poss=8, pattern=pattern, body={'end_location': [60, 40]})]
        return sequences.build_possessions(evs, {'home_team': {'home_team_id': 1}})['possessions'][0]

    def test_rival_corner_is_a_dead_ball_loss(self):
        p = self._first(_ev(2, 'Pass', 1, [50, 40], body={'end_location': [70, 40], 'outcome': {'name': 'Out'}}),
                        'From Corner')
        self.assertEqual(p['loss']['kind'], 'lossXF')

    def test_keeper_restart_is_an_open_play_loss(self):
        p = self._first(_ev(2, 'Pass', 1, [90, 40], body={'end_location': [115, 40], 'outcome': {'name': 'Incomplete'}}),
                        'From Keeper')
        self.assertEqual(p['loss']['kind'], 'lossO')

    def test_possession_ending_in_a_shot_is_not_a_loss(self):
        p = self._first(_ev(2, 'Shot', 1, [100, 40], body={'statsbomb_xg': 0.1, 'outcome': {'name': 'Saved'}}),
                        'From Keeper')
        self.assertEqual(p['end']['type'], 'shot')
        self.assertIsNone(p['loss'])


class ProgressiveTests(unittest.TestCase):
    """T-03.11b: la primera acción de un balón parado (córner, tiro libre, saque de banda o de puerta, inicial) no es progresiva."""

    def _first(self, evs):
        tail = _ev(99, 'Pass', 2, [50, 40], poss=8, body={'end_location': [60, 40]})
        return sequences.build_possessions(evs + [tail], {'home_team': {'home_team_id': 1}})['possessions'][0]

    def test_corner_delivery_into_the_box_is_not_progressive(self):
        corner = _ev(1, 'Pass', 1, [120, 0], pattern='From Corner', body={'end_location': [108, 40]})
        self.assertEqual(self._first([corner])['n_prog'], 0)

    def test_same_pass_in_open_play_is_progressive(self):
        p = self._first([_ev(1, 'Pass', 1, [90, 10], body={'end_location': [108, 40]})])
        self.assertEqual(p['n_prog'], 1)

    def test_only_the_restart_is_excluded_not_the_rest_of_the_possession(self):
        evs = [_ev(1, 'Pass', 1, [50, 0], pattern='From Free Kick', body={'end_location': [75, 30]}),
               _ev(2, 'Pass', 1, [75, 30], pattern='From Free Kick', body={'end_location': [105, 40]})]
        self.assertEqual(self._first(evs)['n_prog'], 1)

    def test_goal_kick_and_throw_in_restarts_are_excluded(self):
        for pattern in ('From Goal Kick', 'From Throw In', 'From Kick Off'):
            p = self._first([_ev(1, 'Pass', 1, [60, 0], pattern=pattern, body={'end_location': [108, 40]})])
            self.assertEqual(p['n_prog'], 0, pattern)


class RivalPossessionShotTests(unittest.TestCase):
    """T-03.11c (decisión del advisor): un tiro dentro de una posesión rival se excluye y la exclusión es medible."""

    def test_shot_by_the_non_possessing_team_is_not_counted_in_any_possession(self):
        stray = _ev(2, 'Shot', 2, [105, 40], body={'statsbomb_xg': 0.05, 'outcome': {'name': 'Saved'}})
        stray['possession_team'] = {'id': 1}
        evs = [_ev(1, 'Pass', 1, [60, 40], body={'end_location': [80, 40]}), stray,
               _ev(3, 'Pass', 2, [50, 40], poss=8, body={'end_location': [60, 40]})]
        out = sequences.build_possessions(evs, {'home_team': {'home_team_id': 1}})
        self.assertEqual([len(p['shots']) for p in out['possessions']], [0, 0])
        self.assertEqual(sequences.rival_possession_shots(evs), {'n': 1, 'xg': 0.05})

    def test_counter_ignores_penalties_and_normal_shots(self):
        shot = _ev(1, 'Shot', 1, [100, 40], body={'statsbomb_xg': 0.1, 'outcome': {'name': 'Saved'}})
        self.assertEqual(sequences.rival_possession_shots([shot]), {'n': 0, 'xg': 0.0})


class ShootoutTests(unittest.TestCase):
    def test_penalty_shootout_is_outside_every_analysis(self):
        evs = [_ev(1, 'Pass', 1, [30, 40], body={'end_location': [50, 40]}),
               _ev(2, 'Pass', 2, [50, 40], poss=8, body={'end_location': [60, 40]})]
        for i, team in ((3, 1), (4, 2)):
            shot = _ev(i, 'Shot', team, [108, 40], poss=10 + i, pattern='Other',
                       body={'statsbomb_xg': 0.78, 'type': {'name': 'Penalty'}, 'outcome': {'name': 'Goal'}})
            shot['period'] = 5
            evs.append(shot)
        out = sequences.build_possessions(evs, {'home_team': {'home_team_id': 1}})
        self.assertEqual([p['period'] for p in out['possessions']], [1, 1])
        self.assertFalse(any(p['shots'] for p in out['possessions']))
        self.assertFalse(any(r['period'] >= 5 for lst in out['events_light'].values() for r in lst))


class ContractTests(unittest.TestCase):
    def test_an_sample_matches_builder_output(self):
        sample = json.loads((HERE / 'fixtures' / 'an_sample.json').read_text(encoding='utf-8'))
        out = sequences.build_possessions(FIX['events'], FIX['metadata'])
        self.assertEqual(sample['possessions'], json.loads(json.dumps(out['possessions'])))
        self.assertEqual(set(sample['events_light']), set(out['events_light']))
        for key in ('version', 'match_id', 'status', 'home', 'away'):
            self.assertIn(key, sample)


if __name__ == '__main__':
    unittest.main()
