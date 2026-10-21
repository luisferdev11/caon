"""Tests del explorador por equipo, temporada y DT (pipeline/explorer.py)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import explorer

COL = 'team_match_possession'


def rec(mid, team, coach, season, val, date='2024-01-10'):
    return {'match_id': mid, 'date': date, 'season_id': season, 'season_name': f'S{season}',
            'team': team, 'coach': coach, 'stats': {COL: val}}


class MathTest(unittest.TestCase):
    def test_shrink(self):
        self.assertAlmostEqual(explorer.shrink(8, 0.6, 0.5), 0.55)
        self.assertAlmostEqual(explorer.shrink(0, None, 0.5), 0.5)

    def test_confidence_bands(self):
        self.assertEqual([explorer.confidence(n) for n in (0, 4, 5, 11, 12, 24, 25)],
                         ['muy baja', 'muy baja', 'baja', 'baja', 'media', 'media', 'alta'])

    def test_window(self):
        self.assertEqual(explorer.window_of('2025-06-30'), 'oficial')
        self.assertEqual(explorer.window_of('2025-07-01'), 'epilogo')
        self.assertEqual(explorer.window_of('2021-06-30'), 'temprano')

    def test_interval_narrows_with_n(self):
        lo1, hi1 = explorer.interval80(0.5, 0.1, 2)
        lo2, hi2 = explorer.interval80(0.5, 0.1, 40)
        self.assertLess(hi2 - lo2, hi1 - lo1)
        self.assertLess(lo1, 0.5)
        self.assertGreater(hi1, 0.5)

    def test_percentile_inverted(self):
        ref = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(explorer.percentile(ref, 3.5, False), 75)
        self.assertEqual(explorer.percentile(ref, 3.5, True), 25)


class CoachTest(unittest.TestCase):
    def test_single_manager_only(self):
        side = {'managers': [{'name': 'André Jardine', 'nickname': None}]}
        self.assertEqual(explorer.match_coach(side), 'André Jardine')
        self.assertIsNone(explorer.match_coach({'managers': [{'name': 'A'}, {'name': 'B'}]}))
        self.assertIsNone(explorer.match_coach({}))

    def test_career_prior_uses_other_clubs(self):
        rows = [rec(1, 'San Luis', 'J', 1, 0.40, '2022-02-01'), rec(2, 'San Luis', 'J', 1, 0.40, '2022-03-01'),
                rec(3, 'América', 'J', 2, 0.60, '2024-01-10'), rec(4, 'Pachuca', 'X', 2, 0.50)]
        prior, src = explorer.career_prior(rows, 'J', '2024-01-10', {COL: 0.5}, [COL])
        self.assertAlmostEqual(prior[COL], 0.40)
        self.assertEqual(src, 'carrera')
        prior, src = explorer.career_prior(rows, 'J', '2022-02-01', {COL: 0.5}, [COL])
        self.assertEqual((prior[COL], src), (0.5, 'liga'))   # solo carrera previa

    def test_tenure_split_by_window(self):
        rows = [rec(i, 'América', 'J', 2, 0.6, f'2025-0{i + 1}-01') for i in range(4)] + \
               [rec(9, 'América', 'J', 3, 0.6, '2025-08-01')]
        out = explorer.build_payload(rows, metrics=[('posesion', COL, False, 'Posesión')])
        tenures = out['carrera']['J']
        self.assertEqual([(t['n'], t['ventana']) for t in tenures], [(4, 'oficial'), (1, 'epilogo')])


class PayloadTest(unittest.TestCase):
    def test_payload_shapes(self):
        rows = [rec(i, 'América', 'J', 2, 0.6) for i in range(3)] + \
               [rec(10 + i, 'Pachuca', 'X', 2, 0.4) for i in range(30)]
        out = explorer.build_payload(rows, metrics=[('posesion', COL, False, 'Posesión')])
        teams = {t['team']: t for t in out['equipos']}
        self.assertEqual(teams['América']['n'], 3)
        coaches = {c['coach']: c for c in out['entrenadores']}
        self.assertEqual(coaches['J']['confianza'], 'muy baja')
        self.assertTrue(coaches['J']['muestra_chica'])
        self.assertEqual(coaches['X']['confianza'], 'alta')
        unit = out['linea_tiempo']['América'][0]
        m = unit['metricas']['posesion']
        self.assertEqual(m['n'], 3)
        self.assertLess(m['value'], 0.6)           # encogido hacia la liga
        self.assertEqual(m['source'], 'team-stats')
        self.assertEqual(m['window'], 'oficial')
        self.assertIn('unit', m)
        self.assertEqual(len(m['ci']), 2)
        self.assertIn('J', out['carrera'])


if __name__ == '__main__':
    unittest.main()
