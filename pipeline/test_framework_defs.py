"""Tests de la segunda parte del marco: ids publicados, KPIs, constantes 360, helpers de registro y ventana."""
import json
import math
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import framework as fw

STYLE_IDS = ('posesion', 'verticalidad', 'ritmo', 'linea', 'volumen_presion', 'presion', 'contrapresion',
             'saque_largo', 'centros', 'contragolpe', 'presion_alta_tiros', 'xg', 'xga', 'bp_xg')
EVENT_IDS = ('secuencia', 'npxg_por_tiro', 'tiros_zona_remate', 'entradas_area', 'xg_concedido',
             'x_media_tiros_concedidos', 'perdida_letal', 'contrapresion_efectiva', 'bp_ofensivo', 'bp_defensivo',
             'bp_diferencial', 'xpts', 'resultado_sorpresivo', 'consistencia', 'xi_base', 'rotacion',
             'cambios', 'impacto_cambio')
F360_IDS = ('bloque_360', 'rompe_lineas', 'presion_360', 'corner_def', 'contexto_error', 'forma_cambio',
            'vigilancias_bajas')
SHARED_360 = ('GRID_STEP_YD', 'MIN_ROI_VISIBLE', 'MIN_SHAPE_PLAYERS', 'DEEP_LINE_N', 'ROI_BACK_YD',
              'ROI_FRONT_YD', 'ROI_HALF_WIDTH_YD', 'ERROR_OPP_RADIUS_YD', 'PRESS_SUPPORT_RADIUS_YD',
              'FREE_OPTION_RADIUS_YD', 'FREE_OPTION_MARGIN_YD', 'PAIRING_RADIUS_YD')


class PublishedIdsTests(unittest.TestCase):
    def test_style_event_and_360_ids_are_defined(self):
        for key in STYLE_IDS + EVENT_IDS + F360_IDS:
            self.assertIn(key, fw.DEFINITIONS, key)

    def test_every_definition_source_is_valid(self):
        for key, d in fw.DEFINITIONS.items():
            self.assertIn(d['fuente'], fw.SOURCES, key)

    def test_posesion_is_the_ball_share_and_secuencia_the_sequence(self):
        self.assertIn('%', fw.DEFINITIONS['posesion']['unidad'])
        self.assertIn('secuencia', fw.DEFINITIONS['secuencia']['nombre'].lower())


class KpiTests(unittest.TestCase):
    def test_seven_kpis_with_defined_ids(self):
        self.assertEqual(len(fw.KPIS), 7)
        for kpi in fw.KPIS:
            self.assertIn(kpi['id'], fw.DEFINITIONS)
            for extra in kpi.get('apoyo', ()):
                self.assertIn(extra, fw.DEFINITIONS)
            self.assertTrue(kpi['nombre'])
            self.assertIn(kpi['mejor'], ('alto', 'bajo'))
        self.assertEqual(fw.KPI_TRAFFIC_PCT, (33, 67))

    def test_vigilancias_low_threshold(self):
        self.assertEqual(fw.VIG_LOW_MAX, 2)


class Shared360Tests(unittest.TestCase):
    def test_360_constants_live_in_framework_with_frames360_values(self):
        import frames360
        for name in SHARED_360:
            self.assertTrue(hasattr(fw, name), name)
            self.assertEqual(getattr(fw, name), getattr(frames360, name), name)
        self.assertEqual(fw.MIN_ROI_VISIBLE, 0.70)
        self.assertEqual(fw.MIN_SHAPE_PLAYERS, 7)


class MetricHelperTests(unittest.TestCase):
    def test_metric_builds_a_valid_contract_record(self):
        rec = fw.metric('ppda', 9.123456, 30, 'pases', 'eventos', 'oficial', entity='ame_jardine', ci=[8, 10])
        self.assertEqual(fw.check_metric_record(rec), [])
        self.assertEqual(rec['value'], 9.1235)
        self.assertEqual(rec['entity'], 'ame_jardine')
        self.assertEqual(rec['ci'], [8, 10])

    def test_missing_or_non_finite_value_becomes_null_with_reason(self):
        for bad in (None, float('nan'), math.inf):
            rec = fw.metric('ppda', bad, 0, 'pases', 'eventos', 'oficial')
            self.assertIsNone(rec['value'])
            self.assertTrue(rec['motivo'])
            json.dumps(rec, allow_nan=False)
        rec = fw.metric('ppda', None, 0, 'pases', 'eventos', 'oficial', motivo='sin 360')
        self.assertEqual(rec['motivo'], 'sin 360')

    def test_unknown_id_window_or_source_raises(self):
        with self.assertRaises(KeyError):
            fw.metric('inventada', 1, 1, 'u', 'eventos', 'oficial')
        with self.assertRaises(ValueError):
            fw.metric('ppda', 1, 1, 'u', 'eventos', 'otra')
        with self.assertRaises(ValueError):
            fw.metric('ppda', 1, 1, 'u', 'opinión', 'oficial')


class WindowAndTierTests(unittest.TestCase):
    def test_window_of_date(self):
        self.assertEqual(fw.window_of('2023-07-01'), 'oficial')
        self.assertEqual(fw.window_of('2025-06-30'), 'oficial')
        self.assertEqual(fw.window_of('2025-07-01'), 'epilogo')
        self.assertIsNone(fw.window_of(None))

    def test_rival_tier_uses_previous_season_when_current_is_short(self):
        cur = [{'team_id': i, 'team_season_xgd_pg': float(i), 'team_season_matches': 17} for i in range(1, 19)]
        cur[0]['team_season_matches'] = 4
        prev = [{'team_id': i, 'team_season_xgd_pg': float(-i), 'team_season_matches': 17} for i in range(1, 19)]
        self.assertEqual(fw.rival_tier(1, cur), 'bajo')
        self.assertEqual(fw.rival_tier(1, cur, prev), 'alto')
        self.assertEqual(fw.rival_tier(18, cur, prev), 'alto')
        self.assertEqual(fw.rival_tier(1, cur, [r for r in prev if r['team_id'] != 1]), 'bajo')


class DriftTests(unittest.TestCase):
    CITED = (('rec_alta', 'formula', 'REC_ALTA_X'), ('rec_campo_rival', 'formula', 'REC_CAMPO_RIVAL_X'),
             ('ppda', 'formula', 'PPDA_OPP_MAX_X'), ('ppda', 'formula', 'PPDA_DEF_MIN_X'),
             ('contraataque', 'formula', 'OUTCOME_WINDOW_S'), ('perdida_costosa', 'formula', 'OUTCOME_WINDOW_S'),
             ('contrapresion_efectiva', 'formula', 'COUNTERPRESS_WINDOW_S'), ('transicion', 'formula',
             'TRANSITION_PHASE_S'), ('prog', 'definicion', 'PROG_MIN_START_X'), ('vigilancias_bajas', 'formula',
             'VIG_LOW_MAX'), ('encogimiento', 'formula', 'SHRINK_N0'), ('tercio', 'definicion', 'THIRD_FINAL_MIN_X'))

    def test_numbers_cited_in_definitions_match_constants(self):
        for key, field, const in self.CITED:
            value = getattr(fw, const)
            text = f'{value:g}'
            self.assertIn(text, fw.DEFINITIONS[key][field], (key, const))

    def test_loads_by_path_without_pipeline_on_sys_path(self):
        import subprocess
        code = ('import importlib.util, json, sys; p = sys.argv[1]; '
                's = importlib.util.spec_from_file_location("caon_framework", p); '
                'm = importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                'print(len(m.DEFINITIONS), len(json.dumps(m.framework_payload(), ensure_ascii=False)) > 0)')
        out = subprocess.run([sys.executable, '-I', '-c', code, str(HERE / 'framework.py')], check=False,
                             capture_output=True, text=True, cwd='/', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.split(), [str(len(fw.DEFINITIONS)), 'True'])


class PayloadTests(unittest.TestCase):
    def test_payload_exposes_kpis_and_thresholds(self):
        p = fw.framework_payload()
        self.assertEqual(len(p['kpis']), 7)
        self.assertEqual(p['thresholds']['REC_ALTA_X'], 80.0)
        self.assertEqual(p['thresholds']['MIN_ROI_VISIBLE'], 0.70)
        self.assertIn('etiquetas', p)
        json.dumps(p, ensure_ascii=False, allow_nan=False)

    def test_marco_has_kpis_and_label_engine(self):
        text = fw.render_marco()
        for sec in ('## KPIs de identidad', '## Motor de etiquetas', 'Directo pero paciente', 'Presión selectiva'):
            self.assertIn(sec, text)


class PressingRuleDocTests(unittest.TestCase):
    """La regla de presión de labels.py está documentada en DEFINITIONS, /api/framework y el marco."""

    def test_pressing_rule_and_axes_are_defined_with_label_numbers(self):
        import labels
        for key in ('perfil_presion', 'intensidad_presion', 'vel_ataque'):
            self.assertIn(key, fw.DEFINITIONS)
        text = fw.DEFINITIONS['perfil_presion']['definicion'] + fw.DEFINITIONS['perfil_presion']['formula']
        for num in (labels.PROFILE_STRONG, labels.PROFILE_WEAK, labels.SIN_ROBO_MAX_CP):
            self.assertIn(f'{num:g}', text)
        for name in labels.DFN_QUALIFIED.values():
            self.assertIn(name, text)

    def test_payload_exposes_profiles_claims_and_all_exclusive_pairs(self):
        import labels
        et = fw.framework_payload()['etiquetas']
        self.assertEqual(set(et['perfiles_presion']), set(labels.PRESS_PROFILES))
        self.assertEqual(et['cuadrantes']['dfn']['br'], 'Línea alta, sin asfixiar')
        self.assertEqual(len(et['conflictos']), len(labels.conflict_pairs()))
        self.assertIn('Línea alta: presiona mucho, deja jugar', et['nombres_calificados'])
        json.dumps(et, ensure_ascii=False, allow_nan=False)

    def test_marco_documents_the_pressing_rule(self):
        text = fw.render_marco()
        self.assertIn('### Regla de presión', text)
        self.assertIn('Línea alta: presiona mucho, deja jugar', text)
        self.assertIn(labels_selective(), text)


def labels_selective() -> str:
    import labels
    return labels.SELECTIVE


if __name__ == '__main__':
    unittest.main()
