"""Tests de analytics.shape360_match: reloj continuo, marcador, cambios y su tipo (eventos sintéticos)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from analytics import shape360_match as sm


def ev(typ, period, minute, second, team, **kw):
    e = {'id': kw.pop('id', f'{typ}-{period}-{minute}-{second}'), 'type': {'name': typ}, 'period': period,
         'minute': minute, 'second': second, 'timestamp': '00:00:00.000', 'team': {'id': team}}
    e.update(kw)
    return e


def goal(period, minute, team):
    return ev('Shot', period, minute, 0, team, shot={'outcome': {'name': 'Goal'}})


def sub(period, minute, team, off, on, pos):
    return ev('Substitution', period, minute, 0, team, player={'id': off, 'name': f'J{off}'},
              position={'name': pos}, substitution={'replacement': {'id': on, 'name': f'J{on}'}})


EVENTS = [
    ev('Pass', 1, 0, 0, 1, player={'id': 10, 'name': 'Diez'}, position={'name': 'Center Forward'}),
    goal(1, 20, 1),
    ev('Pass', 1, 47, 0, 2, player={'id': 20, 'name': 'Veinte'}, position={'name': 'Left Back'}),
    sub(2, 45, 1, 10, 11, 'Center Forward'),
    ev('Pass', 2, 50, 0, 1, player={'id': 11, 'name': 'Once'}, position={'name': 'Center Back'}),
    ev('Own Goal For', 2, 60, 0, 2),
    sub(2, 70, 1, 12, 13, 'Center Back'),
    sub(2, 71, 1, 14, 15, 'Left Back'),
    ev('Pass', 2, 75, 0, 1, player={'id': 13, 'name': 'Trece'}, position={'name': 'Right Wing'}),
    ev('Pass', 2, 76, 0, 1, player={'id': 15, 'name': 'Quince'}, position={'name': 'Left Back'}),
    ev('Pass', 2, 93, 0, 1),
    goal(5, 121, 1),
]


class TestClock(unittest.TestCase):
    def test_second_half_continues_after_first_half_added_time(self):
        off = sm.clock(EVENTS)
        self.assertEqual(sm.elapsed(off, 1, 600.0), 600.0)
        self.assertEqual(sm.elapsed(off, 2, 2700.0), 47 * 60.0)
        self.assertEqual(sm.elapsed(off, 2, 2760.0), 48 * 60.0)


class TestScore(unittest.TestCase):
    def setUp(self):
        self.off = sm.clock(EVENTS)
        self.goals = sm.goals(EVENTS, self.off)

    def test_goals_include_own_goal_and_exclude_shootout(self):
        self.assertEqual([g[1] for g in self.goals], [1, 2])

    def test_score_state_from_team_view(self):
        self.assertEqual(sm.score_state(self.goals, 10 * 60.0, 1), 'empatando')
        self.assertEqual(sm.score_state(self.goals, 30 * 60.0, 1), 'ganando')
        self.assertEqual(sm.score_state(self.goals, 30 * 60.0, 2), 'perdiendo')
        late = sm.elapsed(self.off, 2, 61 * 60.0)
        self.assertEqual(sm.score_state(self.goals, late, 1), 'empatando')

    def test_goals_between(self):
        self.assertTrue(sm.goal_between(self.goals, 0.0, 25 * 60.0))
        self.assertFalse(sm.goal_between(self.goals, 25 * 60.0, 40 * 60.0))


class TestSubs(unittest.TestCase):
    def setUp(self):
        self.subs = sm.substitutions(EVENTS, 1, sm.clock(EVENTS))

    def test_positions_and_type(self):
        first = self.subs[0]
        self.assertEqual((first['off'], first['on']), (10, 11))
        self.assertEqual(first['tipo'], 'defensivo')
        self.assertEqual(self.subs[1]['tipo'], 'ofensivo')
        self.assertEqual(self.subs[2]['tipo'], 'mismo_puesto')

    def test_only_team_subs(self):
        self.assertEqual(sm.substitutions(EVENTS, 2, sm.clock(EVENTS)), [])

    def test_clusters_join_close_subs(self):
        cl = sm.cluster_subs(self.subs)
        self.assertEqual(len(cl), 2)
        self.assertEqual(cl[1]['tipo'], 'mixto')
        self.assertEqual(len(cl[1]['subs']), 2)
        self.assertLess(cl[1]['start'], cl[1]['end'])

    def test_line_of_position(self):
        self.assertEqual(sm.position_line('Goalkeeper'), 0)
        self.assertEqual(sm.position_line('Right Wing Back'), 1)
        self.assertEqual(sm.position_line('Center Attacking Midfield'), 2)
        self.assertEqual(sm.position_line('Left Wing'), 3)
        self.assertIsNone(sm.position_line(None))


class TestMatchContext(unittest.TestCase):
    def test_context_bundle(self):
        ctx = sm.match_context(EVENTS, 1)
        self.assertEqual(ctx['names'][10], 'Diez')
        self.assertEqual(len(ctx['cambios']), 2)
        self.assertEqual(ctx['state'](1, 600.0), 'empatando')
        self.assertEqual(ctx['minute_bin'](2, 50 * 60.0), '46-60')

    def test_no_events_is_none(self):
        self.assertIsNone(sm.match_context(None, 1))


if __name__ == '__main__':
    unittest.main()
