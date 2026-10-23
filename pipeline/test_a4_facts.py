"""Tests de analytics.a4_facts: hechos por partido y equipo (conteos sumables) sobre el partido sintético A4."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from analytics import a4_facts as af
from fixtures import a4_match as fx

US, THEM = fx.US, fx.THEM


def _facts():
    return af.match_facts(fx.MID, fx.an(), fx.events())


class TestOffenseFacts(unittest.TestCase):
    def setUp(self):
        self.n = _facts()[US]['n']['off']

    def test_both_teams_and_match_count(self):
        f = _facts()
        self.assertEqual(set(f), {US, THEM})
        self.assertEqual(f[US]['n']['partidos'], 1)

    def test_goalkeeper_distribution(self):
        self.assertEqual((self.n['gk_saque'], self.n['gk_saque_largo']), (2, 1))
        self.assertEqual((self.n['gk_juego'], self.n['gk_juego_largo']), (1, 0))

    def test_salida_limpia_by_origin(self):
        sal = self.n['salida']
        self.assertEqual(sal['total'], {'n': 4, 'ok': 1})
        self.assertEqual(sal['portero'], {'n': 2, 'ok': 1})
        self.assertEqual(sal['robo'], {'n': 2, 'ok': 0})

    def test_progression(self):
        self.assertEqual(self.n['posesiones'], 8)
        self.assertEqual(self.n['progresion'], {'n': 5, 'ok': 1})
        self.assertEqual((self.n['prog'], self.n['prog_pase'], self.n['prog_conduccion']), (4, 3, 1))
        self.assertEqual(_facts()[US]['prog_jugador'], {12: 2, 11: 1, 13: 1})

    def test_field_tilt_counts(self):
        self.assertEqual((self.n['f3'], self.n['f3_rival']), (7, 6))

    def test_shots_np_and_penalties(self):
        self.assertEqual(self.n['tiros_np'], 2)
        self.assertAlmostEqual(self.n['xg_np'], 0.35)
        self.assertEqual((self.n['goles_np'], self.n['tiros_zona'], self.n['penales']), (1, 1, 1))
        self.assertEqual(self.n['posesiones_area'], 2)  # el pase fallado al área no cuenta como entrada

    def test_origin_breakdown_excludes_penalties(self):
        o = self.n['origen']
        self.assertEqual(o['regain_open']['posesiones'], 4)
        self.assertEqual(o['regain_open']['tiros'], 2)
        self.assertAlmostEqual(o['regain_open']['xg'], 0.35)
        self.assertEqual(o['other']['tiros'], 0)

    def test_obv_by_type_and_zone(self):
        obv = self.n['obv']
        self.assertAlmostEqual(obv['pase'], 0.20)
        self.assertAlmostEqual(obv['conduccion'], 0.06)
        self.assertAlmostEqual(obv['tiro'], 0.23)
        self.assertAlmostEqual(obv['otras'], -0.05)
        self.assertAlmostEqual(obv['total'], 0.44)
        self.assertAlmostEqual(self.n['obv_zona']['10'], 0.01)
        self.assertAlmostEqual(self.n['obv_zona']['7'], 0.05)

    def test_own_shot_list_in_own_frame(self):
        shots = _facts()[US]['tiros']
        self.assertEqual(len(shots), 3)
        self.assertGreater(sum(s[0] for s in shots) / len(shots), 95)


class TestDefenseFacts(unittest.TestCase):
    def setUp(self):
        self.n = _facts()[US]['n']['def']

    def test_pressing_bands_and_intensity_counts(self):
        self.assertEqual(self.n['presiones'], {'alta': 1, 'bloque_medio': 1, 'bajo': 0})
        self.assertEqual(self.n['acciones_def'], {'alta': 1, 'bloque_medio': 3, 'bajo': 1})  # intercepción en x=30
        self.assertEqual(self.n['acciones_rival'], {'alta': 4, 'bloque_medio': 5, 'bajo': 5})
        self.assertEqual(self.n['contrapresiones'], 1)

    def test_ppda_counts(self):
        self.assertEqual((self.n['ppda_pases'], self.n['ppda_acciones']), (7, 2))

    def test_recoveries_named_thresholds(self):
        self.assertEqual(self.n['robos'], {'total': 3, 'campo_rival': 1, 'alta': 1})
        self.assertEqual(self.n['robos_tiro'], {'campo_rival': 1, 'alta': 1})

    def test_conceded(self):
        self.assertEqual(self.n['tiros_np_c'], 3)
        self.assertAlmostEqual(self.n['xg_np_c'], 0.75)
        self.assertEqual((self.n['goles_np_c'], self.n['tiros_zona_c'], self.n['penales_c']), (1, 2, 1))
        self.assertEqual(self.n['posesiones_area_c'], 3)
        self.assertAlmostEqual(self.n['x_tiros_np_c'], 42.0)  # 20 + 12 + 10 en el marco del protagonista

    def test_conceded_shots_flipped_to_protagonist_frame(self):
        shots = _facts()[US]['tiros_c']
        np_x = [s[0] for s in shots if not s[4]]
        self.assertAlmostEqual(sum(np_x) / len(np_x), 14.0)


class TestTransitionFacts(unittest.TestCase):
    def setUp(self):
        self.f = _facts()[US]
        self.n = self.f['n']['tr']

    def test_losses_and_costly(self):
        self.assertEqual(self.n['perdidas'], {'n': 4, 'costosa': 2, 'letal': 1, 'rec5': 2})

    def test_typology(self):
        t = self.n['por_tipo']
        self.assertEqual(t['no_forzado'], {'n': 1, 'costosa': 1, 'letal': 0})
        self.assertEqual(t['duelo_perdido'], {'n': 1, 'costosa': 1, 'letal': 1})
        self.assertEqual(t['bajo_presion']['n'], 1)
        self.assertEqual(t['decision_arriesgada']['n'], 1)

    def test_by_third_zone_player(self):
        self.assertEqual(self.n['por_tercio']['medio'], {'n': 2, 'costosa': 2, 'letal': 1})
        self.assertEqual(self.n['por_zona']['15'], {'n': 1, 'costosa': 0, 'letal': 0})
        self.assertEqual(self.f['perdida_jugador'][11], {'n': 2, 'costosa': 1, 'letal': 1})

    def test_isolation_needs_360(self):
        self.assertEqual(self.n['aislado'], {'validas': 0, 'aisladas': 0})
        f360 = {'tables': {'perdidas': {'cols': ['team', 'eid', 'tipo', 'err_valid', 'isolated'],
                                        'rows': [[US, 'e27', 'otro', True, True], [US, 'e3', 'no_forzado', True,
                                                                                    False]]}}}
        n = af.match_facts(fx.MID, fx.an(), fx.events(), f360)[US]['n']['tr']
        self.assertEqual(n['aislado'], {'validas': 2, 'aisladas': 1})
        self.assertEqual(n['por_tipo']['aislado']['n'], 1)  # 'otro' del 360 + aislado → aislado

    def test_transitions_and_counters(self):
        self.assertEqual(self.n['transiciones'], {'n': 4, 'tiros10': 2, 'xg10': 0.35, 'goles10': 1})
        self.assertEqual(self.n['contras'], {'n': 1, 'goles': 1, 'xg': 0.3})
        self.assertEqual(self.n['transiciones_c'], {'n': 4, 'tiros10': 2, 'xg10': 0.55, 'goles10': 1})
        self.assertEqual(self.n['contras_c'], {'n': 1, 'goles': 0, 'xg': 0.1})

    def test_loss_link_for_dangerous(self):
        link = self.f['perdida_por_posesion_rival']
        self.assertEqual(link['1:8']['event_id'], 'e21')
        self.assertTrue(link['1:8']['letal'])
        self.assertEqual(self.f['obv_max_rival']['1:8'], 0.30)


class TestMerge(unittest.TestCase):
    def test_merge_sums_counts_and_concatenates(self):
        f = _facts()[US]
        m = af.merge([f, f])
        self.assertEqual(m['n']['partidos'], 2)
        self.assertEqual(m['n']['off']['salida']['total'], {'n': 8, 'ok': 2})
        self.assertAlmostEqual(m['n']['off']['xg_np'], 0.70)
        self.assertEqual(len(m['tiros']), 6)
        self.assertEqual(m['prog_jugador'][12], 4)
        self.assertEqual(f['n']['partidos'], 1)  # sin mutar la entrada

    def test_merge_empty(self):
        self.assertEqual(af.merge([]), {})

    def test_shootout_excluded(self):
        ev = fx.events()
        extra = dict(ev[-1], id='so', index=999, period=5, possession=99, type={'name': 'Shot'},
                     shot={'statsbomb_xg': 0.76, 'outcome': {'name': 'Goal'}, 'type': {'name': 'Penalty'}},
                     location=[108, 40], team={'id': US}, possession_team={'id': US})
        import sequences
        an = dict(sequences.build_possessions(ev + [extra], fx.metadata()), match_id=fx.MID)
        f = af.match_facts(fx.MID, an, ev + [extra])
        self.assertEqual(f[US]['n']['off']['penales'], 1)
        self.assertEqual(f[US]['n']['off']['posesiones'], 8)


if __name__ == '__main__':
    unittest.main()
