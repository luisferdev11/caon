"""Tests de analytics.transitions (pérdidas, tipología, contrapresión efectiva, transiciones y contraataques)."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import analytics
import framework
from analytics import transitions
from fixtures import a4_match as fx


def _f360():
    return {'tables': {'perdidas': {'cols': ['team', 'eid', 'tipo', 'err_valid', 'isolated'],
                                    'rows': [[fx.US, 'e27', 'otro', True, True],
                                             [fx.US, 'e3', 'no_forzado', True, False]]}}}


class TestTransitions(unittest.TestCase):
    def setUp(self):
        self.out = transitions.build(fx.context())
        self.w = self.out['ventanas']['oficial']
        self.p = self.w['perdidas']

    def test_registered(self):
        self.assertIn('transitions', analytics.topics())

    def test_loss_totals(self):
        self.assertAlmostEqual(self.p['por_partido']['value'], 4.0)
        self.assertAlmostEqual(self.p['costosas_por_partido']['value'], 2.0)
        self.assertAlmostEqual(self.p['tasa_costosa']['value'], 50.0)
        self.assertEqual(self.p['letales']['value'], 1)

    def test_typology_with_costly_rate(self):
        t = {r['tipo']: r for r in self.p['por_tipo']}
        self.assertEqual(t['no_forzado']['nombre'], 'No forzado')
        self.assertAlmostEqual(t['no_forzado']['tasa_costosa']['value'], 100.0)
        self.assertAlmostEqual(t['bajo_presion']['tasa_costosa']['value'], 0.0)
        self.assertAlmostEqual(t['duelo_perdido']['pct']['value'], 25.0)
        self.assertEqual(t['duelo_perdido']['letales'], 1)
        self.assertNotIn('aislado', t)  # sin 360 no hay aislados

    def test_by_third_zone_and_player(self):
        thirds = {r['tercio']: r for r in self.p['por_tercio']}
        self.assertEqual(thirds['medio']['n'], 2)
        self.assertAlmostEqual(thirds['medio']['tasa_costosa']['value'], 100.0)
        z = self.p['por_zona']
        self.assertEqual(z['cols'], ['zona', 'n', 'costosas', 'letales'])
        self.assertEqual(len(z['rows']), 18)
        self.assertEqual(sum(r[1] for r in z['rows']), 4)
        top = self.p['por_jugador'][0]
        self.assertEqual((top['jugador'], top['n'], top['costosas'], top['letales']), ('Defensa', 2, 1, 1))
        self.assertAlmostEqual(top['tasa_costosa'], 50.0)

    def test_counterpress_effective(self):
        rec = self.w['contrapresion_efectiva']
        self.assertAlmostEqual(rec['value'], 50.0)
        self.assertEqual(rec['n'], 4)

    def test_transitions_both_ways(self):
        t = self.w['transiciones']
        self.assertAlmostEqual(t['ofensivas']['por_partido']['value'], 4.0)
        self.assertAlmostEqual(t['ofensivas']['xg_10s_por_partido']['value'], 0.35)
        self.assertAlmostEqual(t['contraataques']['por_partido']['value'], 1.0)
        self.assertEqual(t['contraataques']['goles'], 1)
        self.assertAlmostEqual(t['defensivas']['xg_10s_por_partido']['value'], 0.55)
        self.assertAlmostEqual(t['contraataques_concedidos']['por_partido']['value'], 1.0)

    def test_isolation_from_360(self):
        p = transitions.build(fx.context(f360_doc=_f360()))['ventanas']['oficial']['perdidas']
        iso = p['aislado_360']
        self.assertEqual((iso['validas'], iso['aisladas']), (2, 1))
        self.assertAlmostEqual(iso['pct']['value'], 50.0)
        self.assertEqual(iso['pct']['source'], '360')
        self.assertIn('aislado', {r['tipo'] for r in p['por_tipo']})

    def test_records_contract_unique(self):
        recs = fx.records(self.out)
        for r in recs:
            self.assertEqual(framework.check_metric_record(r), [], r)
        keys = [(r['id'], r['window'], r.get('scope')) for r in recs]
        self.assertEqual(len(keys), len(set(keys)))
        json.dumps(self.out, ensure_ascii=False, allow_nan=False)

    def test_series(self):
        s = self.w['serie']
        self.assertIn('contrapresion_efectiva', s['cols'])
        self.assertEqual(len(s['rows']), 1)


if __name__ == '__main__':
    unittest.main()
