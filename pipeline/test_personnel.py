import unittest

from personnel import build_match_personnel, clock_seconds, players_minutes


def player(player_id, name, positions):
    return {'player_id': player_id, 'player_name': name, 'positions': positions}


def segment(position, start, end, start_reason='Starting XI', end_reason='Final Whistle'):
    return {
        'position': position,
        'from': start,
        'to': end,
        'start_reason': start_reason,
        'end_reason': end_reason,
    }


class PersonnelTests(unittest.TestCase):
    def test_clock_seconds_and_starting_lineup(self):
        self.assertEqual(clock_seconds('01:08:20.920'), 4100.92)
        lineup = [{'team_id': 1, 'team_name': 'Team', 'lineup': [
            player(index, f'Player {index}', [segment('Center Back', '00:00:00.000', None)])
            for index in range(1, 12)
        ]}]
        result, warnings = build_match_personnel(1, lineup, [
            {'index': 1, 'minute': 45, 'second': 0, 'timestamp': '00:45:00.000',
             'type': {'name': 'Half End'}, 'team': {'id': 1}},
        ], 'Team', venue='home')
        self.assertEqual(len(result['starting_lineup']), 11)
        self.assertEqual(result['coverage']['players_identified'], 11)
        self.assertEqual(warnings, [])

    def test_substitution_and_score_state(self):
        positions = [segment('Center Forward', '00:00:00.000', '00:30:00.000',
                             end_reason='Substitution - Off (Tactical)')]
        replacement_positions = [segment('Center Forward', '00:30:00.000', None,
                                         start_reason='Substitution - On (Tactical)')]
        lineup = [{'team_id': 1, 'team_name': 'Team', 'lineup': [
            player(1, 'Starter', positions),
            player(2, 'Replacement', replacement_positions),
        ]}]
        events = [
            {'index': 1, 'minute': 10, 'second': 0, 'timestamp': '00:10:00.000',
             'type': {'name': 'Shot'}, 'team': {'id': 1},
             'shot': {'outcome': {'name': 'Goal'}}},
            {'index': 2, 'minute': 30, 'second': 0, 'timestamp': '00:30:00.000',
             'type': {'name': 'Substitution'}, 'team': {'id': 1},
             'player': {'id': 1, 'name': 'Starter'},
             'position': {'name': 'Center Forward'},
             'substitution': {'replacement': {'id': 2, 'name': 'Replacement'}}},
            {'index': 3, 'minute': 60, 'second': 0, 'timestamp': '01:00:00.000',
             'type': {'name': 'Half End'}, 'team': {'id': 1}},
        ]
        result, _ = build_match_personnel(2, lineup, events, 'Team', venue='home')
        self.assertEqual(len(result['substitutions']), 1)
        substitution = result['substitutions'][0]
        self.assertEqual(substitution['score_state'], 'winning')
        self.assertEqual(substitution['player_out']['player_id'], 1)
        self.assertEqual(substitution['player_in']['player_id'], 2)
        self.assertEqual(result['players'][0]['minutes_played'], 30)

    def test_missing_id_and_position_are_reported(self):
        lineup = [{'team_id': 1, 'team_name': 'Team', 'lineup': [
            {'player_name': 'Unknown', 'positions': []},
        ]}]
        result, warnings = build_match_personnel(
            3, lineup, [{'minute': 1, 'second': 0, 'timestamp': '00:01:00.000',
                        'type': {'name': 'Half End'}, 'team': {'id': 1}}],
            'Team')
        self.assertTrue(any('player_id' in warning for warning in warnings))
        self.assertEqual(result['players'], [])
        self.assertTrue(result['warnings'])

    def test_players_minutes_by_team_id(self):
        positions = [segment('Center Forward', '00:00:00.000', '00:30:00.000',
                             end_reason='Substitution - Off (Tactical)')]
        lineup = [{'team_id': 1, 'team_name': 'Team', 'lineup': [
            dict(player(1, 'Starter', positions), player_nickname='Titular'),
            player(2, 'Replacement', [segment('Left Wing', '00:30:00.000', None,
                                              start_reason='Substitution - On (Tactical)')]),
            player(3, 'Bench', []),
        ]}, {'team_id': 9, 'team_name': 'Other', 'lineup': []}]
        events = [{'index': 1, 'minute': 90, 'second': 0, 'timestamp': '01:30:00.000',
                   'type': {'name': 'Half End'}, 'team': {'id': 1}}]
        rows = players_minutes(lineup, events, 1)
        by_id = {r['player_id']: r for r in rows}
        self.assertEqual(set(by_id), {1, 2})            # el suplente sin minutos no aparece
        self.assertEqual(by_id[1]['name'], 'Titular')   # apodo primero
        self.assertTrue(by_id[1]['starter'])
        self.assertEqual(by_id[1]['minutes'], 30)
        self.assertEqual(by_id[2]['minutes'], 60)
        self.assertEqual(by_id[2]['positions'], {'Left Wing': 60})
        self.assertIsNone(players_minutes(lineup, events, 5))


if __name__ == '__main__':
    unittest.main()
