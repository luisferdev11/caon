"""Tests de analytics.usage (XI base, minutos, rotación, roles, cambios y asociación descriptiva)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'fixtures'))

from a5_events import US, match_events
from analytics import usage


class NamesTest(unittest.TestCase):
    def test_match_names_prefers_nickname(self):
        class Ctx:
            def load_lineups(self, mid):
                return [{'team_id': 1, 'lineup': [{'player_id': 5, 'player_name': 'Nombre Largo',
                                                   'player_nickname': 'Apodo'},
                                                  {'player_id': 6, 'player_name': 'Sin Apodo'}]}]
        self.assertEqual(usage.match_names(Ctx(), 1), {5: 'Apodo', 6: 'Sin Apodo'})

    def test_match_names_without_loader_or_file(self):
        class Ctx:
            def load_lineups(self, mid):
                return None
        self.assertEqual(usage.match_names(Ctx(), 1), {})


class MatchUsageTest(unittest.TestCase):
    def test_minutes_from_events_fallback(self):
        m = usage.match_usage(US, match_events(sub_minute=60))
        mins = {p['player_id']: p['minutes'] for p in m['players']}
        self.assertEqual(mins[110], 60)
        self.assertEqual(mins[111], 30)
        self.assertEqual(len(m['xi']), 11)
        self.assertEqual(m['formacion'], '4-3-3')
        self.assertEqual(m['cambios'][0]['estado'], 'ganando')
        self.assertEqual(m['cambios'][0]['minuto'], 60)

    def test_minutes_from_lineups(self):
        lineups = [{'team_id': US, 'lineup': [
            {'player_id': 100, 'player_name': 'Portero Largo', 'player_nickname': 'Portero',
             'positions': [{'position': 'Goalkeeper', 'from': '00:00:00.000', 'to': None,
                            'start_reason': 'Starting XI'}]}]}]
        m = usage.match_usage(US, match_events(), lineups=lineups)
        self.assertEqual([p['player_id'] for p in m['players']], [100])
        self.assertEqual(m['players'][0]['name'], 'Portero')
        self.assertEqual(m['fuente_minutos'], 'alineaciones')

    def test_sub_window_association(self):
        m = usage.match_usage(US, match_events(sub_minute=60))
        w = m['cambios'][0]['ventanas']
        self.assertTrue(w['elegible'])
        self.assertAlmostEqual(w['delta']['xg_favor'], 0.2)
        self.assertAlmostEqual(w['delta']['xg_contra'], -0.06)
        self.assertGreater(w['delta']['field_tilt'], 0)

    def test_goal_inside_windows_excludes_moment(self):
        m = usage.match_usage(US, match_events(goal_minute=52, sub_minute=60))
        w = m['cambios'][0]['ventanas']
        self.assertFalse(w['elegible'])
        self.assertEqual(w['motivo'], 'cambio_marcador')

    def test_windows_carry_no_360_shape(self):
        # la forma 360 ante los cambios se calcula una sola vez en el tema shape360 (sin duplicar cifras)
        w = usage.match_usage(US, match_events(sub_minute=60))['cambios'][0]['ventanas']
        self.assertNotIn('forma_360', w)


class SummaryTest(unittest.TestCase):
    def setUp(self):
        per = [usage.match_usage(US, match_events()), usage.match_usage(US, match_events(sub_minute=70))]
        self.out = usage.summarize(per, 'oficial', seed=1)

    def test_core_xi_and_roles(self):
        xi = self.out['xi_base']
        self.assertEqual(len(xi), 11)
        self.assertEqual(xi[0]['posicion'], 'Portero')
        self.assertEqual(xi[0]['titularidades'], 2)
        self.assertAlmostEqual(xi[0]['share_minutos'], 100.0)
        self.assertEqual(self.out['formaciones'][0], {'formacion': '4-3-3', 'n': 2, 'pct': 100.0})
        roles = {r['linea'] for r in self.out['plantilla']}
        self.assertTrue({'Portero', 'Defensa', 'Medio', 'Ataque'} <= roles)

    def test_rotation_metric(self):
        rot = self.out['rotacion']
        self.assertEqual(rot['id'], 'rotacion')
        self.assertEqual(rot['value'], 0)
        self.assertEqual(rot['n'], 1)

    def test_substitution_timing(self):
        c = self.out['cambios']
        self.assertEqual(c['minuto_medio']['id'], 'cambios')
        self.assertAlmostEqual(c['minuto_medio']['value'], 65.0)
        self.assertEqual(c['por_estado']['ganando']['n'], 2)
        self.assertAlmostEqual(c['por_partido'], 1.0)

    def test_association_is_descriptive(self):
        a = self.out['cambios']['asociacion']
        self.assertEqual(a['etiqueta'], 'asociación descriptiva')
        self.assertNotIn('efecto', a['nota'].replace('no es un efecto', ''))
        rec = a['metricas']['xg_favor']
        self.assertEqual(rec['id'], 'impacto_cambio')
        self.assertEqual(rec['n'], 2)
        self.assertGreater(rec['value'], 0)
        self.assertEqual(a['forma_360']['fuente'], 'shape360')
        self.assertIn('oficial', a['forma_360']['ver'])

    def test_build_by_window(self):
        class Ctx:
            entity_id = 't'
            matches = ({'id': 1, 'team_id': US, 'window': 'oficial', 'date': '2024-01-02'},
                       {'id': 2, 'team_id': US, 'window': 'oficial', 'date': '2024-01-01'})

            def load_events(self, mid):
                return match_events(sub_minute=60 if mid == 1 else 70)

            def load_f360(self, mid):
                return None

            def load_lineups(self, mid):
                return None
        out = usage.build(Ctx())
        self.assertEqual(out['etiquetas']['mismo_puesto'], 'Mismo puesto')
        self.assertIn('ventana_incompleta', out['etiquetas'])
        self.assertEqual(list(out['ventanas']), ['oficial'])
        self.assertEqual(out['ventanas']['oficial']['n_partidos'], 2)


if __name__ == '__main__':
    unittest.main()
