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
