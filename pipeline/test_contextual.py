import unittest

from contextual import (
    comparisons,
    context_summary,
    defensive_action,
    extract_context,
    period_seconds,
)


def event(index, kind='Pass', tid=10, second=0, period=1, **extra):
    e = {'index': index, 'type': {'name': kind}, 'team': {'id': tid}, 'period': period,
             'timestamp': f'00:{second // 60:02d}:{second % 60:02d}.000',
             'possession': index, 'possession_team': {'id': tid}, 'location': [60, 40],
             'play_pattern': {'name': 'Regular Play'}}
    if kind == 'Pass': e['pass'] = {'end_location': [80, 40], 'length': 20}
    e.update(extra)
    return e


def metadata(h=1, a=0):
    return {'home_team': {'home_team_id': 10}, 'away_team': {'away_team_id': 20}, 'home_score': h, 'away_score': a}


class ContextTests(unittest.TestCase):
    def sample(self):
        return [event(1, 'Half Start'), event(2, second=10),
                event(3, 'Shot', second=60, shot={'outcome': {'name': 'Goal'}, 'statsbomb_xg': .4}),
                event(4, tid=20, second=150), event(5, 'Half End', second=180)]

    def test_goal_before_state_and_full_interval_after(self):
        counts, status = extract_context(list(reversed(self.sample())), metadata())
        self.assertTrue(status['score_valid'])
        home, away = counts[10], counts[20]
        self.assertEqual(home['score_state']['drawing']['xg'], .4)
        self.assertEqual(home['score_state']['winning']['seconds'], 120)
        self.assertEqual(home['score_state']['drawing']['seconds'], 60)
        self.assertEqual(away['score_state']['drawing']['xga'], .4)
        self.assertEqual(home['venue']['home']['seconds'], 180)
        self.assertEqual(away['venue']['away']['seconds'], 180)

    def test_unknown_venue_and_score_mismatch(self):
        counts, status = extract_context(self.sample())
        self.assertIn('localia_sin_metadatos', status['warnings'])
        self.assertEqual(counts[10]['venue']['away']['matches'], 0)
        self.assertEqual(counts[10]['venue']['unknown']['matches'], 1)
        counts, status = extract_context(self.sample(), metadata(2))
        self.assertFalse(status['score_valid'])
        self.assertEqual(counts[10]['score_state']['unknown']['seconds'], 180)
        self.assertEqual(counts[10]['score_state']['winning']['matches'], 0)

    def test_own_goal_pairs_and_shootout(self):
        ev = [event(1, 'Half Start'), event(2, 'Own Goal Against', tid=20, second=60),
              event(3, 'Own Goal For', second=60), event(4, 'Half End', second=120),
              event(5, 'Shot', period=5, shot={'outcome': {'name': 'Goal'}})]
        c, status = extract_context(ev, metadata())
        self.assertTrue(status['score_valid'])
        self.assertEqual(status['final_score'], {'10': 1})
        c, status = extract_context([e for e in ev if e['index'] != 3], metadata())
        self.assertTrue(status['score_valid'])
        self.assertEqual(c[10]['score_state']['winning']['seconds'], 60)

    def test_periods_stoppage_and_red_card(self):
        ev = [event(1, 'Half Start'), event(2, 'Bad Behaviour', second=60, bad_behaviour={'card': {'name': 'Red Card'}}),
              event(3, 'Half End', second=2800), event(4, 'Half Start', period=2),
              event(5, tid=20, period=2, second=20), event(6, 'Half End', period=2, second=2700)]
        c, _ = extract_context(ev, metadata(0))
        self.assertEqual(c[10]['venue']['home']['seconds'], 5500)
        self.assertEqual(c[10]['venue']['home']['seconds_with_red_card'], 5440)
        self.assertEqual(c[20]['venue']['away']['opponent_red_cards'], 1)

    def test_missing_xg_and_ppda_definition(self):
        ev = self.sample(); ev[2]['shot']['statsbomb_xg'] = None
        ev.insert(2, event(2.5, 'Duel', tid=20, second=30, duel={'type': {'name': 'Aerial Lost'}}))
        c, _ = extract_context(ev, metadata())
        s = context_summary(c[10])
        self.assertIsNone(s['venue']['home']['xg'])
        self.assertIsNone(s['venue']['home']['xg_per90'])
        self.assertEqual(c[20]['venue']['away']['ppda_def_actions'], 0)
        self.assertFalse(defensive_action(ev[2]))
        self.assertIsNone(s['score_state']['losing']['shots'])
        self.assertIsNone(s['venue']['home']['ppda'])

    def test_transition_counts_shots_not_possessions(self):
        ev = [event(1, 'Half Start'), event(2, tid=20, second=1), event(3, second=2, possession=3),
              event(4, 'Shot', second=5, possession=3, shot={'statsbomb_xg': .2}),
              event(5, 'Shot', second=8, possession=3, shot={'statsbomb_xg': .1}), event(6, 'Half End', second=20)]
        c, _ = extract_context(ev, metadata(0))
        self.assertEqual(c[10]['venue']['home']['transition_shots'], 2)
        self.assertEqual(c[10]['venue']['home']['possessions'], 1)

    def test_missing_clock_and_indexes(self):
        ev = self.sample(); ev[1].pop('timestamp'); ev[1].pop('index')
        c, status = extract_context(ev, metadata())
        self.assertFalse(status['score_valid'])
        s = context_summary(c[10])
        self.assertIsNone(s['venue']['home']['shots_per90'])
        self.assertIsNone(period_seconds({}))

    def test_comparison_zero_baseline(self):
        c, _ = extract_context(self.sample(), metadata())
        s = context_summary(c[10]); s['venue']['away'] = dict(s['venue']['home'], xg_per90=0)
        rows = comparisons(s)
        row = next(r for r in rows if r['dimension'] == 'venue' and r['metric'] == 'xg_per90')
        self.assertIsNone(row['relative_difference'])
        self.assertIsNotNone(row['absolute_difference'])
        self.assertFalse(row['sufficient_sample'])




class FrameworkAlignmentTests(unittest.TestCase):
    def test_pace_uses_framework_floor(self):
        import framework as fw
        evs = [event(1, 'Half Start'), event(2, second=10, location=[60, 40]),
               event(3, 'Shot', second=10, possession=2, location=[70, 40],
                     shot={'outcome': {'name': 'Off T'}, 'statsbomb_xg': .1}),
               event(4, tid=20, second=15), event(5, 'Half End', second=20)]
        counts, _ = extract_context(evs, metadata(0, 0))
        drawing = counts[10]['score_state']['drawing']
        self.assertEqual(drawing['pace_n'], 1)
        self.assertAlmostEqual(drawing['pace_sum'], 10 / fw.PACE_FLOOR_S)


if __name__ == '__main__':
    unittest.main()
