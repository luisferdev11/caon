"""Tests de analytics.shape360_base (especificación de métricas) y shape360_ref (referencia liga/neutral)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import framework
from analytics import shape360_base as sb
from analytics import shape360_ref as sr

BCOLS = ['team', 'eid', 'period', 't', 'bx', 'by', 'zone', 'n_vis', 'last_line', 'length', 'width', 'hull_area',
         'between', 'valid']
PCOLS = ['team', 'eid', 'period', 't', 'x', 'y', 'tipo', 'shot15', 'goal15', 'err_linked', 'err_valid',
         'vig_linked', 'vig_valid', 'vig_gs']


def f360(mid, lines, vigs):
    """Extracto mínimo: bloque de ambos equipos y pérdidas del equipo 1."""
    brows = [[1, 'b', 1, 10.0, 90, 40, 13, 9, ll, 20.0, 40.0, 500.0, 4, True] for ll in lines]
    brows += [[2, 'b', 1, 10.0, 90, 40, 13, 9, 50.0, 30.0, 50.0, 700.0, 3, True],
              [2, 'b', 1, 10.0, 90, 40, 13, 9, 99.0, 30.0, 50.0, 700.0, 3, False]]
    prows = [[1, 'p', 1, 20.0, 30, 40, 'otro', v <= 1, False, True, True, True, True, v] for v in vigs]
    return {'mid': mid, 'teams': [1, 2], 'tables': {'bloque': {'cols': BCOLS, 'rows': brows},
                                                    'perdidas': {'cols': PCOLS, 'rows': prows}},
            'coverage': {'bloque': {'1': {'candidates': 5, 'rows': 4, 'valid': 4}}}}


class TestSpecs(unittest.TestCase):
    def test_every_spec_has_known_table_and_scope(self):
        for key, spec in sb.SPECS.items():
            self.assertIn(spec.table, sb.TABLES, key)
            self.assertTrue(spec.scope and spec.unit, key)

    def test_values_respect_validity_gate(self):
        rows = sb.rows(f360(1, [30.0, 40.0], []), 'bloque')
        self.assertEqual(sb.values(rows, 'altura_sin_balon'), [30.0, 40.0, 50.0])

    def test_indicator_metrics_are_percent(self):
        rows = sb.rows(f360(1, [], [1, 2, 3, 4]), 'perdidas')
        self.assertEqual(sb.values(rows, 'vig_pct_max2'), [100.0, 100.0, 0.0, 0.0])
        self.assertEqual(sb.values(rows, 'error_costosa'), [100.0, 0.0, 0.0, 0.0])

    def test_percentile_midrank(self):
        self.assertEqual(sb.percentile(5.0, [1.0, 5.0, 9.0, 10.0]), 38)
        self.assertIsNone(sb.percentile(5.0, []))
        self.assertIsNone(sb.percentile(None, [1.0]))

    def test_metric_ids_exist_in_framework(self):
        for key, spec in sb.SPECS.items():
            self.assertIn(spec.metric_id, framework.DEFINITIONS, key)

    def test_threshold_comes_from_framework(self):
        self.assertIs(sb.VIG_LOW_MAX, framework.VIG_LOW_MAX)

    def test_error_context_specs(self):
        rows = [{'err_valid': True, 'tm10': 0, 'op5': 2, 'nearest': 1.5, 'isolated': True},
                {'err_valid': True, 'tm10': 2, 'op5': 0, 'nearest': 6.0, 'isolated': False},
                {'err_valid': False, 'tm10': 9, 'isolated': True}]
        self.assertEqual(sb.values(rows, 'err_apoyos'), [0.0, 2.0])
        self.assertEqual(sb.values(rows, 'err_aislado'), [100.0, 0.0])
        self.assertEqual(sb.values(rows, 'err_distancia'), [1.5, 6.0])


class TestStats(unittest.TestCase):
    def test_quantile_linear(self):
        self.assertEqual(sb.quantile([1.0, 2.0, 3.0, 4.0], 0.5), 2.5)
        self.assertEqual(sb.quantile([5.0], 0.25), 5.0)
        self.assertIsNone(sb.quantile([], 0.5))

    def test_ci80_from_match_means(self):
        lo, hi = sb.ci80([1.0, 3.0])
        self.assertAlmostEqual((lo + hi) / 2, 2.0)
        self.assertAlmostEqual(hi - 2.0, 1.28, places=2)  # sd=√2, n=2 → z·1, redondeado
        self.assertIsNone(sb.ci80([2.0]))

    def test_ci80_centered_on_pooled_value(self):
        lo, hi = sb.ci80([1.0, 3.0], center=2.5)
        self.assertAlmostEqual((lo + hi) / 2, 2.5)


class TestRecord(unittest.TestCase):
    def test_contract_and_extras(self):
        rec = sb.record('vig_media', 3.456, 40, 'oficial', entity='ame_jardine', n_partidos=12,
                        coverage={'n_valid': 40, 'n_linked': 60})
        self.assertEqual(framework.check_metric_record(rec), [])
        self.assertEqual((rec['id'], rec['scope'], rec['source']), ('vigilancias', 'media', '360'))
        self.assertEqual(rec['entity'], 'ame_jardine')
        self.assertEqual(rec['confidence'], framework.confidence(12))
        self.assertEqual(rec['value'], 3.46)

    def test_missing_value_reason(self):
        none = sb.record('vig_media', None, 0, 'oficial', entity='x', n_partidos=0)
        self.assertIsNone(none['value'])
        self.assertEqual(none['motivo'], sb.NO_360)
        gate = sb.record('vig_media', None, 0, 'oficial', entity='x', n_partidos=3)
        self.assertEqual(gate['motivo'], sb.NO_VALID)


class TestTeamMatchSummary(unittest.TestCase):
    def test_sums_and_counts_per_key(self):
        s = sr.team_match_summary(f360(1, [30.0, 40.0], [1, 3]), 1)
        self.assertEqual(s['altura_sin_balon'], [70.0, 2])
        self.assertEqual(s['vig_media'], [4.0, 2])
        self.assertNotIn('rompe_pct', s)

    def test_rival_side(self):
        s = sr.team_match_summary(f360(1, [30.0], []), 2)
        self.assertEqual(s['altura_sin_balon'], [50.0, 1])


class TestLeague(unittest.TestCase):
    def setUp(self):
        items = []
        for mid in range(10):
            f = f360(mid, [30.0 + mid], [2])
            items += [(mid, 1, sr.team_match_summary(f, 1)), (mid, 2, sr.team_match_summary(f, 2))]
        windows = {mid: ('oficial' if mid < 8 else 'epilogo') for mid in range(10)}
        self.ref = sr.summarize_league(items, windows, neutral_ids={0, 1})

    def test_pooled_league_mean_by_window(self):
        w = self.ref['ventanas']['oficial']['altura_sin_balon']
        self.assertEqual(w['n'], 16)
        self.assertAlmostEqual(w['liga'], (sum(30.0 + m for m in range(8)) + 8 * 50.0) / 16, places=2)
        self.assertEqual(w['n_equipos'], 2)

    def test_team_means_need_min_matches(self):
        self.assertEqual(self.ref['ventanas']['epilogo']['altura_sin_balon']['n_equipos'], 0)

    def test_league_coverage_per_window(self):
        items = [(0, 1, {'vig_media': [2.0, 1]})]
        ref = sr.summarize_league(items, {0: 'oficial', 1: 'oficial', 2: 'oficial', 3: 'epilogo'}, [])
        self.assertEqual(ref['cobertura']['oficial'], {'con_360': 1, 'calendario': 3})
        self.assertEqual(ref['cobertura']['epilogo'], {'con_360': 0, 'calendario': 1})
        self.assertFalse(sr.league_complete(ref, 'oficial'))
        full = sr.summarize_league(items, {0: 'oficial'}, [])
        self.assertTrue(sr.league_complete(full, 'oficial'))
        self.assertFalse(sr.league_complete({}, 'oficial'))

    def test_neutral_sample_pooled(self):
        self.assertEqual(self.ref['neutral']['altura_sin_balon']['valor'], round((30 + 31 + 100) / 4, 2))


class TestTiers(unittest.TestCase):
    def test_previous_season_when_few_matches(self):
        def row(tid, xgd, n):
            return {'team_id': tid, 'team_season_xgd_pg': xgd, 'team_season_matches': n}
        old = [row(t, -t, 30) for t in range(1, 19)]
        new = [row(t, t, 3) for t in range(1, 19)]
        tiers = sr.season_tiers({'a': old, 'b': new}, ['a', 'b'])
        self.assertEqual(tiers['a'][1], 'alto')
        self.assertEqual(tiers['b'][1], 'alto')
        self.assertEqual(tiers['a'][18], 'bajo')

    def test_short_team_only_uses_previous(self):
        old = [{'team_id': t, 'team_season_xgd_pg': -t, 'team_season_matches': 30} for t in range(1, 19)]
        new = [{'team_id': t, 'team_season_xgd_pg': t, 'team_season_matches': 20} for t in range(1, 19)]
        new[0] = dict(new[0], team_season_matches=2)
        tiers = sr.season_tiers({'a': old, 'b': new}, ['a', 'b'])
        self.assertEqual(tiers['b'][1], 'alto')
        self.assertEqual(tiers['b'][18], 'alto')

    def test_current_season_when_enough(self):
        rows = [{'team_id': t, 'team_season_xgd_pg': t, 'team_season_matches': 20} for t in range(1, 19)]
        self.assertEqual(sr.season_tiers({'a': rows}, ['a'])['a'][18], 'alto')


if __name__ == '__main__':
    unittest.main()
