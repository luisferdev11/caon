"""Tests del explorador por equipo, temporada y DT (pipeline/explorer.py)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import explorer
import framework as fw

COL = 'team_match_possession'
POS = [('posesion', COL, False, 'Posesión')]


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
        self.assertEqual(explorer.window_of('2026-07-01'), 'temprano')

    def test_small_sample_is_below_medium_confidence(self):
        self.assertEqual(explorer.SMALL_SAMPLE_N, 12)
        self.assertEqual(explorer.confidence(explorer.SMALL_SAMPLE_N), 'media')
        self.assertEqual(explorer.confidence(explorer.SMALL_SAMPLE_N - 1), 'baja')

    def test_interval_narrows_with_n(self):
        lo1, hi1 = explorer.interval80(0.5, 0.1, 2)
        lo2, hi2 = explorer.interval80(0.5, 0.1, 40)
        self.assertLess(hi2 - lo2, hi1 - lo1)
        self.assertLess(lo1, 0.5)
        self.assertGreater(hi1, 0.5)

    def test_interval_follows_framework_ci_level(self):
        self.assertAlmostEqual(explorer.Z_CI, 1.2816, places=3)
        self.assertEqual(fw.CI_LEVEL, 0.80)
        lo, hi = explorer.interval80(0.0, 1.0, 0, k=1)
        self.assertAlmostEqual(hi - lo, 2 * explorer.Z_CI)

    def test_percentile_inverted(self):
        ref = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(explorer.percentile(ref, 3.5, False), 75)
        self.assertEqual(explorer.percentile(ref, 3.5, True), 25)

    def test_slug(self):
        self.assertEqual(explorer.slug('André Jardine'), 'andre-jardine')
        self.assertEqual(explorer.slug('Atlético San Luis'), 'atletico-san-luis')


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
               [rec(9, 'América', 'J', 3, 0.6, '2025-08-01'), rec(10, 'Atlas', 'J', 4, 0.6, '2026-08-01')]
        out = explorer.build_payload(rows, metrics=POS)
        coach = out['entrenadores'][0]
        self.assertEqual([(t['team'], t['n'], t['window']) for t in coach['tenencias']],
                         [('América', 4, 'oficial'), ('América', 1, 'epilogo'), ('Atlas', 1, 'temprano')])
        self.assertEqual(coach['clubes'], ['América', 'Atlas'])
        self.assertEqual([s['temporada'] for s in coach['temporadas']], ['S2', 'S3', 'S4'])   # carrera completa


def league_rows():
    rows = [rec(i, 'América', 'J', 2, 0.6) for i in range(3)] + \
           [rec(10 + i, 'Pachuca', 'X', 2, 0.4) for i in range(30)]
    rows += [rec(50, 'América', 'J', 3, 0.9, '2025-09-01')]                 # epílogo
    rows += [rec(60 + i, 'Atlante', 'Z', 3, 0.5, '2025-09-01') for i in range(2)]  # solo epílogo
    return rows


class PayloadTest(unittest.TestCase):
    def setUp(self):
        self.out = explorer.build_payload(league_rows(), metrics=POS)
        self.teams = {t['key']: t for t in self.out['equipos']}
        self.coaches = {c['key']: c for c in self.out['entrenadores']}

    def test_team_item_contract(self):
        ame = self.teams['america']
        for k in ('label', 'team', 'n', 'confidence', 'small_sample', 'window', 'prior', 'metrics', 'temporadas'):
            self.assertIn(k, ame)
        self.assertEqual(ame['label'], 'América')
        self.assertEqual((ame['n'], ame['window']), (3, 'oficial'))      # resumen solo con la ventana oficial
        self.assertEqual((ame['n_total'], ame['unidades']), (4, 2))      # unidades = número de temporadas
        self.assertTrue(ame['small_sample'])
        self.assertEqual(ame['confidence'], 'muy baja')
        self.assertEqual(self.teams['atlante']['window'], 'epilogo')    # sin oficial: se rotula

    def test_metric_record_contract(self):
        m = self.teams['america']['metrics']['posesion']               # dict por id, en orden de despliegue
        self.assertEqual((m['id'], m['nombre']), ('posesion', 'Posesión'))
        self.assertLess(m['value'], 0.6)            # encogido hacia la liga
        self.assertAlmostEqual(m['raw'], 0.6)
        self.assertEqual((m['n'], m['source'], m['window']), (3, 'team-stats', 'oficial'))
        self.assertEqual(m['unit'], fw.DEFINITIONS['posesion']['unidad'])
        self.assertEqual(len(m['ci']), 2)
        self.assertIn('ref_pct', m)
        self.assertEqual(fw.check_metric_record(m), [])

    def test_all_style_metrics_exist_in_framework(self):
        self.assertEqual([k for k, _c, _i, _l in explorer.METRICS if k not in fw.DEFINITIONS], [])

    def test_season_units_and_identity(self):
        units = self.teams['america']['temporadas']
        self.assertEqual([(u['temporada'], u['n'], u['window']) for u in units], [('S2', 3, 'oficial'),
                                                                                  ('S3', 1, 'epilogo')])
        self.assertEqual(units[0]['label'], 'América · J · S2')
        self.assertEqual(units[0]['prior'], 'liga')
        self.assertIn('posesion', units[0]['metrics'])
        ident = self.teams['america']['identity']
        self.assertTrue({'build', 'defense', 'attack', 'tags', 'map'} <= set(ident))

    def test_coach_items(self):
        j, x = self.coaches['j'], self.coaches['x']
        self.assertEqual((j['confidence'], x['confidence']), ('muy baja', 'alta'))
        self.assertTrue(j['small_sample'])
        self.assertFalse(x['small_sample'])
        self.assertEqual(j['label'], 'J')
        self.assertIn('metrics', x)
        self.assertEqual(len(j['tenencias']), 2)
        self.assertEqual(j['unidades'], 2)

    def test_null_metric_keeps_contract(self):
        rows = [rec(1, 'América', 'J', 2, None)] + [rec(10 + i, 'Pachuca', 'X', 2, 0.4) for i in range(12)]
        m = explorer.build_payload(rows, metrics=POS)['equipos'][0]['metrics']['posesion']
        self.assertIsNone(m['value'])
        self.assertIn('motivo', m)
        self.assertEqual(fw.check_metric_record(m), [])

    def test_metric_catalog(self):
        cat = self.out['metricas']
        self.assertEqual(cat[0]['id'], 'posesion')
        self.assertEqual(cat[0]['fuente'], 'team-stats')
        self.assertEqual(self.out['version'], 'explorer.v3')

    def test_json_safe(self):
        import json
        json.dumps(self.out, ensure_ascii=False, allow_nan=False)


class CompactTest(unittest.TestCase):
    """Unidades anidadas con métricas compactas (unidad del catálogo; ventana y fuente de la unidad)."""

    def setUp(self):
        self.out = explorer.build_payload(league_rows(), metrics=POS)

    def test_significant_rounding(self):
        self.assertEqual(explorer.sig(269.32421), 269.3)
        self.assertEqual(explorer.sig(0.507123), 0.5071)
        self.assertEqual(explorer.sig(0.0), 0.0)
        self.assertEqual(explorer.sig(-12.3456), -12.35)

    def test_nested_metrics_are_compact(self):
        season = {t['key']: t for t in self.out['equipos']}['america']['temporadas'][0]
        m = season['metrics']['posesion']
        self.assertNotIn('id', m)
        self.assertNotIn('window', m)
        self.assertTrue({'value', 'raw', 'ci', 'n', 'prior_value'} <= set(m))
        self.assertEqual((season['source'], season['window']), ('team-stats', 'oficial'))
        tenure = self.out['entrenadores'][0]['tenencias'][0]
        self.assertNotIn('id', tenure['metrics']['posesion'])

    def test_whole_payload_passes_coherence_ids(self):
        import audit_coherence as ac
        self.assertEqual(ac.check_metric_ids({'explorer.json': self.out}), [])


class EntityLinkTest(unittest.TestCase):
    """Enlace a las entidades del modelo (analítica de eventos/360 en model/analysis/<id>.json)."""

    def setUp(self):
        rows = [rec(1, 'América', 'J', 2, 0.6, '2024-01-10'), rec(2, 'América', 'J', 2, 0.6, '2024-02-10'),
                rec(3, 'América', 'K', 3, 0.6, '2026-08-10'), rec(4, 'Pachuca', 'X', 2, 0.4, '2024-01-10')]
        ents = [{'id': 'ame_j', 'label': 'América · J', 'team': 'América', 'd0': '2024-01-01', 'd1': '2024-03-01',
                 'window': 'oficial', 'kind': 'real'},
                {'id': 'ame_k', 'label': 'América · K', 'team': 'América', 'd0': '2026-07-01', 'd1': '2026-09-01',
                 'window': 'temprano', 'kind': 'real'},
                {'id': 'ghost', 'label': 'Nadie', 'team': 'Atlas', 'd0': '2024-01-01', 'd1': '2024-03-01',
                 'kind': 'real'}]
        self.out = explorer.link_entities(explorer.build_payload(rows, metrics=POS), ents, rows)

    def test_entity_coach_by_majority(self):
        rows = [rec(1, 'América', 'J', 2, 0.6, '2024-01-10'), rec(2, 'América', 'J', 2, 0.6, '2024-02-10'),
                rec(3, 'América', 'K', 2, 0.6, '2024-02-20')]
        ent = {'team': 'América', 'd0': '2024-01-01', 'd1': '2024-03-01'}
        self.assertEqual(explorer.entity_coach(ent, rows), 'J')
        self.assertIsNone(explorer.entity_coach(dict(ent, team='Atlas'), rows))

    def test_team_and_coach_links(self):
        teams = {t['key']: t for t in self.out['equipos']}
        coaches = {c['key']: c for c in self.out['entrenadores']}
        self.assertEqual([e['id'] for e in teams['america']['entidades']], ['ame_j', 'ame_k'])
        self.assertEqual(teams['pachuca']['entidades'], [])
        self.assertEqual([e['id'] for e in coaches['j']['entidades']], ['ame_j'])
        self.assertEqual(coaches['k']['entidades'][0], {'id': 'ame_k', 'label': 'América · K', 'window': 'temprano'})
        tenure = coaches['j']['tenencias'][0]
        self.assertEqual([e['id'] for e in tenure['entidades']], ['ame_j'])


if __name__ == '__main__':
    unittest.main()
