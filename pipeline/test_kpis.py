"""KPIs (T-06): valores copiados de analysis, semáforo en los terciles propios y frase descriptiva."""
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import framework as fw
import kpis

N = 12


def rec(mid, value, n=91, **extra):
    return dict({'id': mid, 'value': value, 'n': n, 'unit': 'u', 'source': 'eventos', 'window': 'oficial',
                 'entity': 'e1', 'ref_pct': 70.0}, **extra)


def serie(cols, count=N):
    """Serie sintética: la columna k vale (i + 1) · (k + 1) en el partido i."""
    return {'cols': ['match_id', 'fecha'] + cols,
            'rows': [[100 + i, '2024-01-01'] + [(i + 1) * (k + 1) / 10 for k in range(len(cols))] for i in range(count)]}


def analysis(count=N, with_360=True):
    win = {'offense': {'dominio': {'field_tilt': rec('field_tilt', 6.5)},
                       'progresion': {'progresion_limpia': rec('progresion_limpia', 5.0)},
                       'ocasiones': {'npxg_por_tiro': rec('npxg_por_tiro', 0.115, ref_pct=40.0),
                                     'tiros_zona_remate': rec('tiros_zona_remate', 45.7)},
                       'serie': serie(['field_tilt', 'progresion_limpia', 'npxg_tiro', 'tiros_zona', 'salida_limpia'], count)},
           'transitions': {'contrapresion_efectiva': rec('contrapresion_efectiva', 13.4),
                           'perdidas': {'costosas_por_partido': rec('perdida_costosa', 2.76, ref_pct=33.3),
                                        'por_tipo': [{'tipo': 'no_forzado', 'pct': rec('tipo_error', 5.6)}],
                                        'por_tercio': [{'tercio': 'propio', 'pct': rec('tipo_error', 9.0)}]},
                           'serie': serie(['contrapresion_efectiva', 'costosas_partido', 'perdidas_partido'], count)},
           'setpieces': {'diferencial': rec('bp_diferencial', 0.07, ref_pct=None,
                                            por_partido=[[100 + i, (i - 5) / 10] for i in range(count)]),
                         'ofensivo': {'xg_bp': rec('bp_ofensivo', 0.35)}, 'defensivo': {'xg_bp': rec('bp_defensivo', 0.28)}}}
    shape = {'kpi': rec('vigilancias', 4.55, ref_pct=33, kpi=6, nombre='Vigilancias 360', mejor='alto', n_partidos=count,
                        por_partido=[[100 + i, 4 + i / 10] for i in range(count)]),
             'metricas': {'vig_pct_max2': rec('vigilancias_bajas', 14.3)}} if with_360 else {'kpi': {'id': 'vigilancias', 'value': None, 'motivo': 'sin 360'}}
    return {'meta': {'id': 'e1', 'label': 'E1'},
            'offense': {'ventanas': {'oficial': win['offense']}}, 'defense': {'ventanas': {'oficial': {}}},
            'transitions': {'ventanas': {'oficial': win['transitions']}},
            'setpieces': {'ventanas': {'oficial': win['setpieces']}}, 'shape360': {'ventanas': {'oficial': shape}}}


def points(count=N, fn=lambda i: 3 if i >= 6 else 0):
    return {100 + i: fn(i) for i in range(count)}


class QuantileTests(unittest.TestCase):
    def test_type7_quantile_keeps_four_decimals(self):
        self.assertAlmostEqual(kpis.quantile([0.11, 0.12, 0.15], 0.5), 0.12)
        self.assertAlmostEqual(kpis.quantile(list(range(1, 13)), 0.33), 4.63)
        self.assertAlmostEqual(kpis.quantile(list(range(1, 13)), 0.67), 8.37)
        self.assertIsNone(kpis.quantile([], 0.5))


class TrafficLightTests(unittest.TestCase):
    def series(self):
        return [(100 + i, float(i + 1)) for i in range(N)]

    def test_high_is_good_green_is_the_top_tercile(self):
        out = kpis.traffic_light(self.series(), points(fn=lambda i: 3 if i >= 8 else 0), 'alto')
        self.assertEqual(out['umbrales'], {'p33': 4.63, 'p67': 8.37})
        self.assertEqual(out['semaforo']['verde'], {'n': 4, 'pts_partido': 3.0})
        self.assertEqual(out['semaforo']['rojo'], {'n': 4, 'pts_partido': 0.0})
        self.assertEqual(out['semaforo']['ambar']['n'], 4)
        self.assertEqual(out['frase'], 'En partidos en verde sumó 3.0 pts/partido vs 0.0 en rojo (n=4/4); descriptivo.')
        self.assertEqual(out['iqr'], [3.75, 9.25])
        self.assertEqual(out['n_partidos'], N)

    def test_low_is_good_green_is_the_bottom_tercile(self):
        out = kpis.traffic_light(self.series(), points(fn=lambda i: 3 if i < 4 else 0), 'bajo')
        self.assertEqual(out['semaforo']['verde'], {'n': 4, 'pts_partido': 3.0})
        self.assertEqual(out['semaforo']['rojo'], {'n': 4, 'pts_partido': 0.0})

    def test_small_sample_has_no_traffic_light_but_keeps_the_iqr(self):
        short = self.series()[:fw.KPI_MIN_MATCHES - 1]
        out = kpis.traffic_light(short, points(), 'alto')
        self.assertIsNone(out['semaforo'])
        self.assertIsNone(out['frase'])
        self.assertIn('muestra chica', out['motivo'])
        self.assertEqual(len(out['iqr']), 2)

    def test_without_points_there_is_no_phrase(self):
        out = kpis.traffic_light(self.series(), {}, 'alto')
        self.assertIsNone(out['semaforo']['verde']['pts_partido'])
        self.assertIsNone(out['frase'])

    def test_no_series_says_so_instead_of_small_sample(self):
        out = kpis.traffic_light([], points(), 'alto')
        self.assertEqual(out['motivo'], 'sin serie por partido')
        self.assertEqual(out['iqr'], [None, None])

    def test_phrase_is_descriptive_even_when_green_scored_less(self):
        out = kpis.traffic_light(self.series(), points(fn=lambda i: 0 if i >= 8 else 3), 'alto')
        self.assertTrue(out['frase'].endswith('descriptivo.'))
        self.assertNotIn('causa', out['frase'])


class BuildKpiTests(unittest.TestCase):
    def setUp(self):
        self.out = kpis.build_entity(analysis(), points(), 'e1')

    def test_seven_kpis_in_framework_order_with_registered_ids(self):
        rows = self.out['kpis']['oficial']
        self.assertEqual([k['id'] for k in rows], [k['id'] for k in fw.KPIS])
        self.assertEqual([k['kpi'] for k in rows], list(range(1, 8)))
        for k in rows:
            self.assertIn(k['id'], fw.DEFINITIONS)

    def test_values_are_copied_from_the_analysis_records(self):
        by = {k['id']: k for k in self.out['kpis']['oficial']}
        self.assertEqual(by['field_tilt']['value'], 6.5)
        self.assertEqual(by['npxg_por_tiro']['value'], 0.115)
        self.assertEqual(by['npxg_por_tiro']['ref_pct'], 40.0)
        self.assertEqual(by['perdida_costosa']['value'], 2.76)
        self.assertEqual(by['bp_diferencial']['value'], 0.07)
        self.assertEqual(by['npxg_por_tiro']['apoyo']['tiros_zona_remate']['value'], 45.7)
        self.assertEqual(by['bp_diferencial']['apoyo']['bp_ofensivo']['value'], 0.35)
        self.assertEqual(by['perdida_costosa']['apoyo']['por_tipo'][0]['tipo'], 'no_forzado')
        self.assertEqual(by['perdida_costosa']['apoyo']['por_tercio'][0]['tercio'], 'propio')

    def test_percentile_is_also_published_with_high_equals_good(self):
        by = {k['id']: k for k in self.out['kpis']['oficial']}
        self.assertEqual(by['npxg_por_tiro']['pct_bueno'], 40.0)       # mejor = alto
        self.assertAlmostEqual(by['perdida_costosa']['pct_bueno'], 66.7)  # mejor = bajo: 100 - 33.3
        self.assertIsNone(by['bp_diferencial']['pct_bueno'])

    def test_vigilancias_value_comes_from_shape360_and_the_light_from_the_same_rule(self):
        v = {k['id']: k for k in self.out['kpis']['oficial']}['vigilancias']
        self.assertEqual(v['value'], 4.55)
        self.assertEqual(v['umbrales'], {'p33': 4.363, 'p67': 4.737})
        self.assertEqual(v['n_partidos'], N)
        self.assertEqual(v['apoyo']['vigilancias_bajas']['value'], 14.3)

    def test_vigilancias_with_few_matches_has_no_traffic_light(self):
        out = kpis.build_entity(analysis(count=fw.KPI_MIN_MATCHES - 3), points(), 'e1')
        v = {k['id']: k for k in out['kpis']['oficial']}['vigilancias']
        self.assertIsNone(v['semaforo'])
        self.assertIn('muestra chica', v['motivo'])

    def test_missing_360_gives_a_null_kpi_with_reason(self):
        out = kpis.build_entity(analysis(with_360=False), points(), 'e1')
        v = {k['id']: k for k in out['kpis']['oficial']}['vigilancias']
        self.assertIsNone(v['value'])
        self.assertTrue(v['motivo'])

    def test_every_kpi_has_window_n_and_no_nan(self):
        json.dumps(self.out, allow_nan=False)
        for k in self.out['kpis']['oficial']:
            self.assertEqual(k['window'], 'oficial')
            self.assertIn('n', k)

    def test_only_windows_present_in_the_analysis_are_built(self):
        a = analysis()
        a['offense']['ventanas']['epilogo'] = a['offense']['ventanas']['oficial']
        self.assertEqual(sorted(kpis.build_entity(a, points(), 'e1')['kpis']), ['epilogo', 'oficial'])

    def test_bp_series_uses_the_published_per_match_list(self):
        bp = {k['id']: k for k in self.out['kpis']['oficial']}['bp_diferencial']
        self.assertEqual(bp['n_partidos'], N)
        self.assertEqual(bp['por_partido'][0], [100, -0.5])


@unittest.skipUnless((HERE.parent / 'model' / 'kpis' / 'ame_jardine.json').exists(), 'kpis aún no publicados')
class PublishedKpisTests(unittest.TestCase):
    def test_jardine_has_the_seven_kpis_equal_to_analysis(self):
        root = HERE.parent / 'model'
        doc = json.loads((root / 'kpis' / 'ame_jardine.json').read_text(encoding='utf-8'))
        ana = json.loads((root / 'analysis' / 'ame_jardine.json').read_text(encoding='utf-8'))
        rows = {k['id']: k for k in doc['kpis']['oficial']}
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(k['value'] is not None for k in rows.values()))
        win = ana['offense']['ventanas']['oficial']
        self.assertEqual(rows['field_tilt']['value'], win['dominio']['field_tilt']['value'])
        self.assertEqual(rows['progresion_limpia']['value'], win['progresion']['progresion_limpia']['value'])
        self.assertEqual(rows['vigilancias']['value'], ana['shape360']['ventanas']['oficial']['kpi']['value'])
        json.dumps(doc, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
