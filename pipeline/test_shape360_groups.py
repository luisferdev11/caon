"""Tests de analytics.shape360_groups: bloque por zona/marcador/minuto/rival y forma ante cambios (sintético)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from analytics import shape360_groups as sg
from analytics import shape360_match as sm


def ev(typ, period, minute, team, **kw):
    e = {'id': f'{typ}-{period}-{minute}-{team}', 'type': {'name': typ}, 'period': period, 'minute': minute,
         'second': 0, 'timestamp': '00:00:00.000', 'team': {'id': team}}
    e.update(kw)
    return e


def sub(period, minute, off, on, pos):
    return ev('Substitution', period, minute, 1, player={'id': off, 'name': f'J{off}'}, position={'name': pos},
              substitution={'replacement': {'id': on, 'name': f'J{on}'}})


def events(goal_minute=None):
    evs = [ev('Pass', 1, 0, 1, player={'id': 9, 'name': 'Nueve'}, position={'name': 'Center Back'}),
           ev('Pass', 1, 46, 2),
           sub(2, 60, 9, 19, 'Center Back'),
           ev('Pass', 2, 61, 1, player={'id': 19, 'name': 'Diecinueve'}, position={'name': 'Center Forward'}),
           ev('Pass', 2, 94, 1)]
    if goal_minute is not None:
        evs.append(ev('Shot', 2, goal_minute, 2, shot={'outcome': {'name': 'Goal'}}))
    return evs


def block(team, minute, line, width=40.0, zone=13, valid=True, period=2):
    return {'team': team, 'period': period, 't': minute * 60.0, 'zone': zone, 'last_line': line, 'length': 30.0,
            'width': width, 'hull_area': 600.0, 'between': 4, 'valid': valid}


def bundle(goal_minute=None, tier='alto'):
    own = [block(1, m, 30.0) for m in range(46, 58)] + [block(1, m, 40.0, width=50.0) for m in range(63, 75)]
    opp = [block(2, m, 20.0) for m in range(46, 58)] + [block(2, m, 22.0) for m in range(63, 75)]
    own.append(block(1, 10, 99.0, period=1, zone=7))
    vig_rows = [{'team': 1, 'period': 2, 't': m * 60.0, 'vig_valid': True, 'vig_linked': True, 'vig_gs': g}
                for m, g in ((50, 2), (52, 2), (54, 2), (56, 2), (57, 2), (64, 4), (66, 4), (68, 4), (70, 4),
                             (72, 4))]
    return {'mid': 1, 'team': 1, 'tier': tier, 'mctx': sm.match_context(events(goal_minute), 1),
            'own': {'bloque': own, 'perdidas': vig_rows, 'salida': []},
            'opp': {'bloque': opp, 'perdidas': [], 'salida': []}}


class TestBlockGroups(unittest.TestCase):
    def setUp(self):
        self.g = sg.block_groups([bundle()])

    def test_by_zone_with_rival_reference(self):
        z = self.g['por_zona']['13']
        self.assertEqual(z['n'], 24)
        self.assertEqual(z['altura_sin_balon'], 35.0)
        self.assertEqual(z['ref_altura_sin_balon'], 21.0)
        self.assertEqual(self.g['por_zona']['7']['n'], 1)

    def test_by_score_minute_and_tier(self):
        self.assertEqual(self.g['por_marcador']['empatando']['n'], 25)
        self.assertEqual(self.g['por_minuto']['46-60']['n'], 12)
        self.assertEqual(self.g['por_minuto']['61-75']['altura_sin_balon'], 40.0)
        self.assertEqual(self.g['por_rival']['alto']['partidos'], 1)

    def test_without_events_only_zone_and_tier(self):
        b = dict(bundle(), mctx=None)
        g = sg.block_groups([b])
        self.assertEqual(g['por_marcador'], {})
        self.assertEqual(g['cobertura']['partidos_sin_eventos'], 1)
        self.assertEqual(g['por_zona']['13']['n'], 24)


class TestSubMoments(unittest.TestCase):
    def test_delta_after_minus_before(self):
        ms = sg.sub_moments(bundle())
        self.assertEqual(len(ms), 1)
        m = ms[0]
        self.assertEqual(m['tipo'], 'ofensivo')
        self.assertEqual(m['delta']['altura_sin_balon'], 10.0)
        self.assertEqual(m['delta']['bloque_ancho'], 10.0)
        self.assertEqual(m['delta']['vig_media'], 2.0)
        self.assertEqual(m['delta_rival']['altura_sin_balon'], 2.0)
        self.assertEqual(m['subs'][0]['entra'], 'Diecinueve')
        self.assertEqual((m['n_antes'], m['n_despues']), (12, 12))

    def test_goal_inside_windows_excludes_moment(self):
        ms = sg.sub_moments(bundle(goal_minute=66))
        self.assertTrue(ms[0]['excluido'])
        self.assertIsNone(ms[0].get('delta'))

    def test_few_frames_give_null_delta(self):
        b = bundle()
        b['own']['bloque'] = [r for r in b['own']['bloque'] if r['t'] < 3600 or r['t'] > 71 * 60]
        m = sg.sub_moments(b)[0]
        self.assertIsNone(m['delta']['altura_sin_balon'])

    def test_ball_position_adjustment(self):
        b = bundle()
        b['own']['bloque'] = ([dict(block(1, m, 20.0), bx=30.0) for m in range(46, 58)]
                              + [dict(block(1, m, 40.0), bx=90.0) for m in range(63, 75)])
        raw = sg.sub_moments(b)[0]['delta']['altura_sin_balon']
        adj = sg.sub_moments(b, sg.baselines([b]))[0]['delta']['altura_sin_balon']
        self.assertEqual((raw, adj), (20.0, 0.0))

    def test_baselines_by_ball_column(self):
        b = bundle()
        b['own']['bloque'] = [dict(block(1, 50, 20.0), bx=30.0), dict(block(1, 51, 40.0), bx=95.0),
                              dict(block(1, 52, 30.0), bx=99.0)]
        base = sg.baselines([b])
        self.assertEqual(base['own']['altura_sin_balon'][1], 20.0)
        self.assertEqual(base['own']['altura_sin_balon'][4], 35.0)

    def test_no_events_no_moments(self):
        self.assertEqual(sg.sub_moments(dict(bundle(), mctx=None)), [])

    def test_summary_by_type(self):
        moments = sg.sub_moments(bundle()) + sg.sub_moments(bundle(goal_minute=66))
        s = sg.sub_summary(moments, 'oficial')
        self.assertEqual((s['n_momentos'], s['validos']), (2, 1))
        t = s['por_tipo']['ofensivo']
        self.assertEqual(t['n'], 1)
        self.assertEqual(t['delta']['altura_sin_balon'], 10.0)
        self.assertEqual(len(s['ejemplos']), 1)
        self.assertEqual(t['n_cuadros']['altura_sin_balon'], [12, 12])
        self.assertEqual(t['delta_rival']['altura_sin_balon'], 2.0)
        self.assertNotIn('suma', s['ejemplos'][0])

    def test_summary_pools_frames_of_thin_moments(self):
        b = bundle()
        b['own']['bloque'] = [r for r in b['own']['bloque'] if r['t'] < 49 * 60 or r['t'] > 71 * 60]
        moments = sg.sub_moments(b) * 2
        self.assertIsNone(moments[0]['delta']['altura_sin_balon'])
        s = sg.sub_summary(moments, 'oficial')
        self.assertEqual(s['por_tipo']['ofensivo']['delta']['altura_sin_balon'], 10.0)
        self.assertEqual(s['por_tipo']['ofensivo']['n_cuadros']['altura_sin_balon'], [6, 6])
        self.assertEqual(s['ejemplos'], [])


if __name__ == '__main__':
    unittest.main()
