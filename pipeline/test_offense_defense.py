"""Tests de analytics.offense y analytics.defense sobre el partido sintético A4 (contrato EntityContext)."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import analytics
import framework
from analytics import defense, offense
from fixtures import a4_match as fx


def _unique_keys(test, payload):
    recs = fx.records(payload)
    test.assertTrue(recs)
    for r in recs:
        test.assertEqual(framework.check_metric_record(r), [], r)
    keys = [(r['id'], r['window'], r.get('scope')) for r in recs]
    test.assertEqual(len(keys), len(set(keys)), 'mismo (id, ventana, scope) con dos registros')


class TestOffense(unittest.TestCase):
    def setUp(self):
        self.out = offense.build(fx.context())
        self.w = self.out['ventanas']['oficial']

    def test_registered_with_eventcontext(self):
        self.assertIn('offense', analytics.topics())
        self.assertIn('defense', analytics.topics())
        self.assertEqual(self.w['n_partidos'], 1)

    def test_buildup(self):
        c = self.w['construccion']
        self.assertAlmostEqual(c['saque_puerta_largo']['value'], 50.0)
        self.assertEqual(c['saque_puerta_largo']['n'], 2)
        self.assertAlmostEqual(c['salida_limpia']['value'], 25.0)
        self.assertAlmostEqual(c['salida_limpia_tras_portero']['value'], 50.0)
        self.assertAlmostEqual(c['salida_limpia_tras_robo']['value'], 0.0)

    def test_progression_and_top_progressors(self):
        p = self.w['progresion']
        self.assertAlmostEqual(p['progresion_limpia']['value'], 20.0)
        self.assertAlmostEqual(p['prog_por_100']['value'], 50.0)
        self.assertAlmostEqual(p['prog_por_partido']['value'], 4.0)
        top = p['top_progresores']
        self.assertEqual((top[0]['jugador'], top[0]['n']), ('Medio', 2))
        self.assertAlmostEqual(top[0]['pct_equipo'], 50.0)

    def test_chances(self):
        o = self.w['ocasiones']
        self.assertAlmostEqual(o['npxg_por_tiro']['value'], 0.175)
        self.assertAlmostEqual(o['tiros_zona_remate']['value'], 50.0)
        self.assertAlmostEqual(o['entradas_area']['value'], 2.0)
        self.assertAlmostEqual(o['creacion']['value'], 25.0)
        robo = next(r for r in o['por_origen'] if r['origen'] == 'regain_open')
        self.assertEqual((robo['nombre'], robo['tiros'], robo['goles']), ('Robo en juego', 2, 1))

    def test_real_shot_map_own_frame_without_penalties(self):
        m = self.w['ocasiones']['mapa_tiros']
        self.assertEqual(m['cols'][:3], ['x', 'y', 'xg'])
        self.assertEqual(len(m['rows']), 2)
        self.assertGreater(sum(r[0] for r in m['rows']) / len(m['rows']), 95)

    def test_obv_by_type_zone_and_validation(self):
        obv = self.w['obv']
        self.assertAlmostEqual(obv['por_partido']['value'], 0.44)
        self.assertAlmostEqual(obv['por_tipo']['pase']['value'], 0.20)
        self.assertEqual(len(obv['por_zona']), 18)
        self.assertAlmostEqual(obv['por_zona'][10], 0.01)
        self.assertIn('obv_total', obv['validacion'])
        self.assertEqual(obv['validacion']['obv_total']['n'], 1)

    def test_field_tilt(self):
        self.assertAlmostEqual(self.w['dominio']['field_tilt']['value'], 700 / 13, places=3)

    def test_series_for_kpis(self):
        s = self.w['serie']
        self.assertEqual(s['cols'][:2], ['match_id', 'fecha'])
        self.assertEqual(s['rows'][0][0], fx.MID)
        self.assertIn('field_tilt', s['cols'])

    def test_records_contract_unique_and_entity(self):
        _unique_keys(self, self.out)
        self.assertEqual(self.w['dominio']['field_tilt']['entity'], 'ent')

    def test_reference_percentile(self):
        units = {'a': {'partidos': 1, 'off': {'f3': 1, 'f3_rival': 9}}, 'b': {'partidos': 1, 'off': {'f3': 9,
                                                                                                     'f3_rival': 1}}}
        out = offense.build(fx.context(league_ref={'a4_unidades': units}))
        rec = out['ventanas']['oficial']['dominio']['field_tilt']
        self.assertEqual(rec['ref_pct'], 50.0)
        self.assertEqual(rec['ref_n'], 2)

    def test_empty_context(self):
        self.assertEqual(offense.build(fx.context(rows=[]))['ventanas'], {})

    def test_json_safe(self):
        json.dumps(self.out, ensure_ascii=False, allow_nan=False)


class TestDefense(unittest.TestCase):
    def setUp(self):
        self.out = defense.build(fx.context())
        self.w = self.out['ventanas']['oficial']

    def test_pressing_by_band(self):
        b = self.w['presion']['intensidad_por_fase']
        self.assertAlmostEqual(b['alta']['value'], 0.25)
        self.assertAlmostEqual(b['bloque_medio']['value'], 0.6)
        self.assertAlmostEqual(b['bajo']['value'], 0.2)
        self.assertAlmostEqual(self.w['presion']['presiones_por_fase']['alta']['value'], 1.0)
        self.assertAlmostEqual(self.w['presion']['contrapresiones']['value'], 1.0)

    def test_ppda_from_events(self):
        self.assertAlmostEqual(self.w['presion']['ppda']['value'], 3.5)
        self.assertEqual(self.w['presion']['ppda']['n'], 2)

    def test_named_recoveries(self):
        r = self.w['recuperaciones']
        self.assertAlmostEqual(r['rec_campo_rival']['value'], 1.0)
        self.assertAlmostEqual(r['rec_alta']['value'], 1.0)
        self.assertAlmostEqual(r['rec_alta_con_tiro']['value'], 1.0)
        self.assertEqual(len(r['por_zona']), 18)
        self.assertEqual(sum(r['por_zona']), 3)

    def test_conceded(self):
        c = self.w['concedido']
        self.assertAlmostEqual(c['xg_concedido']['value'], 0.75)
        self.assertAlmostEqual(c['npxg_por_tiro']['value'], 0.25)
        self.assertAlmostEqual(c['entradas_area']['value'], 3.0)
        self.assertAlmostEqual(c['x_media_tiros_concedidos']['value'], 14.0)

    def test_conceded_map_left_goal(self):
        rows = self.w['concedido']['mapa_tiros']['rows']
        self.assertLess(sum(r[0] for r in rows) / len(rows), 25)

    def test_ppda_validation_block(self):
        v = self.w['presion']['validacion_ppda']
        self.assertEqual(v['n'], 1)

    def test_records_contract_unique(self):
        _unique_keys(self, self.out)
        json.dumps(self.out, ensure_ascii=False, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
