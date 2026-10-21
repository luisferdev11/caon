"""Tests de analytics.shape360 (agregados 360 por entidad) con extractos, eventos y an_ sintéticos."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import analytics
from analytics import shape360
from analytics import shape360_base as sb
from framework import check_metric_record

PCOLS = ['team', 'player', 'eid', 'rid', 'period', 't', 'x', 'y', 'kind', 'xpass', 'up', 'fwd', 'shot15',
         'goal15', 'tipo', 'err_linked', 'err_valid', 'tm10', 'op5', 'op3', 'nearest', 'isolated', 'vig_linked',
         'vig_valid', 'vig_gs', 'vig_central', 'vig_ahead', 'vig_sup']
BCOLS = ['team', 'eid', 'period', 't', 'bx', 'by', 'zone', 'n_vis', 'last_line', 'length', 'width', 'hull_area',
         'between', 'valid']


def _loss(team, eid, tipo, x, y, shot, vig, valid=True, iso=False):
    return [team, 10, eid, 'r', 1, 600.0, x, y, 'pase', 0.8, False, True, shot, False, tipo, True, valid, 1, 1, 0,
            3.0, iso, True, valid, vig, 1, 0, 0]


def _f360(mid, vig_own=(1, 4), line=30.0):
    loss_rows = [_loss(1, f'l{mid}-{i}', 'bajo_presion' if i == 0 else 'no_forzado', 30 + 40 * i, 40, i == 0, v)
                 for i, v in enumerate(vig_own)]
    loss_rows += [_loss(1, f'l{mid}-x', 'otro', 70, 10, False, 3, valid=False),
                  _loss(2, f'l{mid}-r', 'bajo_presion', 50, 40, False, 5)]
    return {'mid': mid, 'teams': [1, 2], 'tables': {
        'perdidas': {'cols': PCOLS, 'rows': loss_rows},
        'bloque': {'cols': BCOLS, 'rows': [[1, 'b', 1, 5.0, 90, 40, 13, 9, line, 20.0, 40.0, 500.0, 4, True],
                                           [2, 'b', 1, 5.0, 90, 40, 13, 9, 40.0, 30.0, 50.0, 700.0, 3, True]]},
        'salida': {'cols': ['team', 'eid', 'period', 't', 'bx', 'n_vis', 'height', 'valid'],
                   'rows': [[1, 'e', 1, 5.0, 10, 8, 30.0, True], [2, 'e', 1, 5.0, 10, 8, 20.0, True]]},
        'rompe': {'cols': ['team', 'eid', 'period', 't', 'x0', 'x1', 'lbp', 'bypassed', 'valid'],
                  'rows': [[1, 'e', 1, 5.0, 40, 70, True, 3, True]]},
        'presion': {'cols': ['team', 'eid', 'period', 't', 'x', 'y', 'counterpress', 'support', 'free_options',
                             'valid'], 'rows': [[1, 'e', 1, 5.0, 90, 40, True, 2, 1, True]]},
        'corner_def': {'cols': ['team', 'eid', 'period', 't', 'def_box', 'def_six', 'att_box', 'near_post',
                                'far_post', 'pairing', 'unpaired_six', 'marking', 'valid'],
                       'rows': [[1, 'e', 1, 5.0, 9, 3, 6, 1, 2, 0.7, 0, 'al_hombre', True],
                                [2, 'e', 1, 5.0, 8, 2, 6, 1, 2, 0.2, 4, 'zonal', True]]},
        'saque_meta': {'cols': ['team', 'eid', 'period', 't', 'kick_mean_x', 'def_mean_x', 'n_kick', 'n_def',
                                'valid'], 'rows': [[1, 'g', 1, 5.0, 95.0, 85.0, 8, 9, True]]}},
        'snapshots': [{'team': 1, 'shooter_team': 2, 'eid': 's1', 'period': 1, 't': 100.0, 'xg': 0.4, 'goal': True,
                       'penalty': False, 'pattern': 'Regular Play', 'kp': None, 'kp_pts': None,
                       'ff': [[10.0, 40.0, 0], [12.0, 41.0, 1], [11.0, 40.0, 4]]},
                      {'team': 2, 'shooter_team': 1, 'eid': 's2', 'period': 1, 't': 200.0, 'xg': 0.3,
                       'goal': False, 'penalty': False, 'pattern': 'Regular Play', 'kp': None, 'kp_pts': None,
                       'ff': [[10.0, 30.0, 0], [11.0, 30.0, 2], [12.0, 31.0, 4]]}]}


def _events(mid):
    return [{'id': f'l{mid}-0', 'type': {'name': 'Pass'}, 'period': 1, 'minute': 10, 'second': 0,
             'timestamp': '00:10:00.000', 'team': {'id': 1}, 'possession': 3, 'player': {'id': 10, 'name': 'Diez'}},
            {'id': 's2', 'type': {'name': 'Shot'}, 'period': 1, 'minute': 3, 'second': 20,
             'timestamp': '00:03:20.000', 'team': {'id': 1}, 'possession': 4, 'player': {'id': 10, 'name': 'Diez'},
             'shot': {'outcome': {'name': 'Saved'}}}]


AN = {'possessions': [{'id': 3, 'team': 1, 'loss': {'kind': 'lossO', 'costly': True, 'lethal': True}}]}

REF = {'cobertura': {'oficial': {'con_360': 10, 'calendario': 10}},
       'ventanas': {'oficial': {'vig_media': {'liga': 3.0, 'n': 100, 'equipos': [1.0, 2.0, 3.0, 4.0], 'n_equipos': 4}}},
       'neutral': {'vig_media': {'valor': 2.0, 'n': 50}}, 'n_neutral': 40,
       'temporada': {'7': '317', '8': '317', '9': '317'}, 'niveles': {'317': {'2': 'alto'}}}

MATCHES = [{'id': 7, 'window': 'oficial', 'team_id': 1, 'score': [2, 0], 'date': '2024-01-01', 'opponent': 'R'},
           {'id': 8, 'window': 'oficial', 'team_id': 1, 'score': [0, 1], 'date': '2024-02-01', 'opponent': 'R'},
           {'id': 9, 'window': 'oficial', 'team_id': 1, 'score': [1, 1], 'date': '2024-03-01', 'opponent': 'R'},
           {'id': 10, 'window': 'epilogo', 'team_id': 1, 'score': [1, 1], 'date': '2025-09-01', 'opponent': 'R'}]
F360 = {7: _f360(7, (5, 6, 7, 5, 6)), 8: _f360(8, (0, 1, 1, 2, 0)), 9: _f360(9, (3, 3, 3, 3, 3))}


def _ctx(with_360=True, ref=REF):
    return analytics.EntityContext(entity_id='x', label='X', team='T', coach='C', matches=MATCHES,
                                   load_f360=(lambda mid: F360.get(mid) if with_360 else None),
                                   load_events=_events, load_an=lambda mid: AN if mid == 7 else None,
                                   league_ref={'shape360': ref})


class TestShape360(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = shape360.build(_ctx())
        cls.w = cls.out['ventanas']['oficial']

    def test_registered(self):
        self.assertIn('shape360', analytics.topics())

    def test_coverage_counts_matches(self):
        p = self.w['partidos']
        self.assertEqual((p['con_360'], p['total'], p['con_eventos']), (3, 3, 3))
        self.assertEqual(self.out['ventanas']['epilogo']['partidos']['sin_360'], [10])

    def test_every_metric_record_meets_contract(self):
        for key, rec in self.w['metricas'].items():
            self.assertEqual(check_metric_record(rec), [], key)
            self.assertEqual(rec['entity'], 'x')
            self.assertEqual(rec['scope'], sb.SPECS[key].scope)

    def test_vigilancias_value_reference_and_percentile(self):
        v = self.w['metricas']['vig_media']
        self.assertEqual(v['value'], round((29 + 4 + 15) / 15, 2))
        self.assertEqual(v['coverage'], {'n_valid': 15, 'n_linked': 18})
        self.assertEqual(v['ref']['rivales'], 5.0)
        self.assertEqual(v['ref']['liga'], 3.0)
        self.assertEqual(v['ref']['neutral'], 2.0)
        self.assertEqual(v['ref_pct'], 75)
        self.assertEqual(v['n_partidos'], 3)
        self.assertLessEqual(v['ci'][0], v['value'])
        self.assertGreaterEqual(v['ci'][1], v['value'])
        self.assertIn('equipos', self.w['referencia']['poblacion_percentil'])

    def test_incomplete_league_is_not_called_liga(self):
        ref = dict(REF, cobertura={'oficial': {'con_360': 5, 'calendario': 10}})
        v = shape360.build(_ctx(ref=ref))['ventanas']['oficial']['metricas']['vig_media']
        self.assertNotIn('liga', v['ref'])
        self.assertEqual(v['ref']['partidos_con_360'], 3.0)

    def test_kpi_traffic_light_points(self):
        k = self.w['kpi']
        self.assertEqual(check_metric_record(k), [])
        self.assertEqual(k['value'], self.w['metricas']['vig_media']['value'])
        self.assertEqual(k['semaforo']['verde']['pts_partido'], 3.0)
        self.assertEqual(k['semaforo']['rojo']['pts_partido'], 0.0)
        self.assertIn('descriptivo', k['frase'])
        self.assertEqual(len(k['por_partido']), 3)
        self.assertEqual(len(k['por_partido'][0]), 2)

    def test_errors_joined_with_an(self):
        e = self.w['errores']
        self.assertEqual(e['cobertura']['n_unidas_an'], 1)
        tipos = {t['tipo']: t for t in e['tipos']}
        self.assertEqual(tipos['bajo_presion']['letales'], 1)

    def test_block_groups_and_rival_tier(self):
        self.assertEqual(self.w['bloque']['por_zona']['13']['altura_sin_balon'], 30.0)
        self.assertEqual(self.w['bloque']['por_rival']['alto']['partidos'], 3)

    def test_snapshots_protagonist_frame_and_codes(self):
        conc = self.w['jugadas']['concedidas'][0]
        self.assertEqual(conc['ff'][0], [10.0, 40.0, 0])
        fav = self.w['jugadas']['a_favor'][0]
        self.assertEqual(fav['ff'][0], [110.0, 50.0, 1])
        self.assertEqual(fav['ff'][1], [109.0, 50.0, 3])
        self.assertEqual(fav['ff'][2][2], 4)
        self.assertEqual(fav['jugador'], 'Diez')
        self.assertEqual(fav['minuto'], 3)

    def test_penalties_excluded_from_snapshots(self):
        f = _f360(7)
        f['snapshots'][0]['penalty'] = True
        b = shape360.bundle(MATCHES[0], f, None, None, {})
        out = shape360.jugadas([b])
        self.assertEqual(out['concedidas'], [])
        self.assertEqual(len(out['a_favor']), 1)

    def test_orientation_sanity(self):
        c = self.w['cordura']
        self.assertEqual(c['x_media_rival_saque_meta'], 95.0)
        self.assertTrue(c['aprobado'])

    def test_corners_marking(self):
        c = self.w['corners']
        self.assertEqual(c['marcaje'], {'al_hombre': 3})
        self.assertEqual(c['ref_marcaje'], {'zonal': 3})

    def test_no_360_is_null_with_reason(self):
        w = shape360.build(_ctx(with_360=False))['ventanas']['oficial']
        v = w['metricas']['vig_media']
        self.assertIsNone(v['value'])
        self.assertEqual(v['motivo'], sb.NO_360)
        self.assertIsNone(w['kpi']['value'])


if __name__ == '__main__':
    unittest.main()
