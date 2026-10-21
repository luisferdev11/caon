import unittest

from build_model import context_summary
from extract import _score_context, _state_for


class ContextMetricTests(unittest.TestCase):
    def test_score_state_changes_after_goal(self):
        events = [
            {'index': 1, 'team': {'id': 10}, 'type': {'name': 'Pass'}},
            {'index': 2, 'team': {'id': 10}, 'type': {'name': 'Shot'},
             'shot': {'outcome': {'name': 'Goal'}}},
            {'index': 3, 'team': {'id': 20}, 'type': {'name': 'Pass'}},
        ]
        scores = _score_context(events)
        self.assertEqual(_state_for(scores[1], 10), 'drawing')
        self.assertEqual(_state_for(scores[3], 20), 'losing')

    def test_context_preserves_missing_rates(self):
        summary = context_summary({
            'score_state': {'winning': {'possessions': 2}},
            'venue': {},
        })
        winning = summary['score_state']['winning']
        self.assertIsNone(winning['ppda'])
        self.assertIsNone(winning['directness'])
        self.assertFalse(winning['sufficient_sample'])

    def test_context_normalizes_rates(self):
        summary = context_summary({
            'score_state': {'drawing': {
                'seconds': 5400, 'matches': 5, 'possessions': 30, 'passes': 20,
                'forward_passes': 8, 'ppda_passes': 30,
                'ppda_def_actions': 10, 'pass_distance': 100,
                'forward_distance': 40,
            }},
            'venue': {},
        })
        drawing = summary['score_state']['drawing']
        self.assertEqual(drawing['minutes'], 90)
        self.assertEqual(drawing['forward_pass_rate'], 0.4)
        self.assertEqual(drawing['ppda'], 3)
        self.assertEqual(drawing['directness'], 0.4)
        self.assertTrue(drawing['sufficient_sample'])


if __name__ == '__main__':
    unittest.main()
