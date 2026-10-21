import unittest

from temporal import _period_rows, aggregate_period, build_temporal


def row(index, date):
    return {'mid': index, 'date': date, 'side': 'home'}


class TemporalTests(unittest.TestCase):
    def test_periods_are_chronological_and_merge_small_tail(self):
        rows = [{'date': f'2024-01-{index:02d}'} for index in range(1, 10)]
        periods = _period_rows(rows)
        self.assertEqual([len(period) for period in periods], [9])
        self.assertEqual(periods[0][0]['date'], '2024-01-01')

    def test_exact_eight_and_five_match_blocks(self):
        eight = _period_rows([{'date': str(index)} for index in range(8)])
        five = _period_rows([{'date': str(index)} for index in range(5)])
        self.assertEqual([len(period) for period in eight], [8])
        self.assertEqual([len(period) for period in five], [5])

    def test_missing_denominators_remain_missing(self):
        period = aggregate_period([{
            'date': '2024-01-01',
            'metrics': {
                'possession': None, 'directness': None,
                'pace_towards_goal': None, 'ppda': None,
                'pressures_per_opp_pass': None, 'shots': 2,
                'xg': None, 'xga': None,
                'transition_shots_per_possession': None,
            },
            'context': {},
        }])
        self.assertIsNone(period['metrics']['possession'])
        self.assertEqual(period['metrics']['shots'], 2)
        self.assertEqual(period['observations']['possession']['missing_matches'], 1)

    def test_build_temporal_is_reproducible_and_deduplicates(self):
        entity_matches = [row(1, '2024-01-01'), row(1, '2024-01-01')]
        match_by_id = {
            1: {'match_date': '2024-01-01', '_entity_team': 'Team',
                '_opponent': 'Rival', '_score': [1, 0]}
        }
        extracts = {1: {'teams': {
            '1': {'name': 'Team', 'm': {'passes': 10, 'opp_passes': 10},
                  'poss': 1, 'shot': [[1]], 'context': {}}
        }}}
        first = build_temporal(entity_matches, match_by_id, extracts)
        second = build_temporal(entity_matches, match_by_id, extracts)
        self.assertEqual(first, second)
        self.assertEqual(first['coverage']['observed_matches'], 1)
        self.assertEqual(len(first['matches']), 1)


if __name__ == '__main__':
    unittest.main()
