"""Tests de audit_coherence sobre payloads sintéticos."""
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import audit_coherence as ac

REC = {'id': 'ppda', 'value': 9.0, 'n': 30, 'unit': 'pases', 'source': 'eventos', 'window': 'oficial',
       'entity': 'ame_jardine'}
GOOD_STYLE = {'posesion': 74, 'verticalidad': 81, 'ritmo': 31, 'linea': 59, 'volumen_presion': 58, 'presion': 10,
              'contrapresion': 30, 'saque_largo': 61, 'centros': 31, 'contragolpe': 58}


class AuditTests(unittest.TestCase):
    def test_unknown_metric_and_value_mismatch(self):
        payloads = {'story/jardine.json': {'chapters': [{'evidencia': [REC, dict(REC, id='inventada')]}]},
                    'explorer/coaches.json': {'rows': [dict(REC, value=9.5)]}}
        errs = ac.check_metric_ids(payloads) + ac.check_same_values(payloads)
        self.assertTrue(any('inventada' in e for e in errs))
        self.assertTrue(any('ppda' in e and '9.5' in e for e in errs))

    def test_clean_payloads_pass(self):
        payloads = {'story/jardine.json': {'k': [REC]}, 'explorer/x.json': {'k': [dict(REC)]}}
        self.assertEqual(ac.check_metric_ids(payloads) + ac.check_same_values(payloads), [])

    def test_label_conflicts_and_card_vs_quadrant(self):
        model = {'entities': [{'id': 'a', 'style': GOOD_STYLE}], 'map': {'units': []}}
        self.assertEqual(ac.check_labels(model), [])
        bad = {'entities': [{'id': 'b', 'style': GOOD_STYLE,
                             'identity': {'defense': 'Presión alta', 'map': {'dfn': [59, 33, 'Bloque bajo']}}}],
               'map': {'units': []}}
        self.assertTrue(ac.check_labels(bad))

    def test_single_threshold_per_concept(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / 'otro.py'
            mod.write_text('REC_ALTA_X = 75\n', encoding='utf-8')
            errs = ac.check_thresholds([mod])
            self.assertTrue(any('REC_ALTA_X' in e for e in errs))
            mod.write_text('import framework as fw\nX = fw.REC_ALTA_X\n', encoding='utf-8')
            self.assertEqual(ac.check_thresholds([mod]), [])

    def test_load_payloads_reads_known_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'story').mkdir()
            (root / 'story' / 'j.json').write_text(json.dumps({'a': [REC]}), encoding='utf-8')
            self.assertEqual(list(ac.load_payloads(root)), ['story/j.json'])


class AuditCompletionTests(unittest.TestCase):
    def test_same_value_duplicate_is_warning_and_different_value_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / 'otro.py'
            mod.write_text('MIN_ROI_VISIBLE = 0.70\n', encoding='utf-8')
            self.assertEqual(ac.check_thresholds([mod]), [])
            self.assertTrue(any('MIN_ROI_VISIBLE' in w for w in ac.threshold_warnings([mod])))
            mod.write_text('MIN_ROI_VISIBLE = 0.60\n', encoding='utf-8')
            self.assertTrue(any('MIN_ROI_VISIBLE' in e for e in ac.check_thresholds([mod])))

    def test_alias_of_framework_x_threshold_is_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = pathlib.Path(tmp) / 'otro.py'
            mod.write_text('FINAL_THIRD_X = 80.0\nTOP_N = 10\n', encoding='utf-8')
            warns = ac.threshold_warnings([mod])
            self.assertTrue(any('FINAL_THIRD_X' in w and 'THIRD_FINAL_MIN_X' in w for w in warns))
            self.assertFalse(any('TOP_N' in w for w in warns))

    def test_top_level_payload_files_are_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'explorer.json').write_text(json.dumps({'equipos': [REC]}), encoding='utf-8')
            (root / 'model.json').write_text('{}', encoding='utf-8')
            self.assertEqual(list(ac.load_payloads(root)), ['explorer.json'])

    def test_story_records_outside_official_window_need_badge(self):
        payloads = {'story/jardine.json': {'c': [dict(REC, window='epilogo'),
                                                 dict(REC, window='epilogo', fuera_de_ventana=True), REC]},
                    'analysis/x.json': {'c': [dict(REC, window='epilogo')]}}
        warns = ac.window_badge_warnings(payloads)
        self.assertEqual(len(warns), 1)
        self.assertIn('story/jardine.json', warns[0])

    def test_run_reports_warnings_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            rep = ac.run(pathlib.Path(tmp))
            self.assertIn('avisos', rep)
            self.assertIn('ok', rep)


AME = dict(GOOD_STYLE, linea=70, volumen_presion=71, presion=18, contrapresion=44, ritmo=30, verticalidad=84,
           posesion=78)
STALE = {'build': 'Posesión con pase vertical', 'defense': 'Línea alta, presión selectiva', 'attack': 'Mixto',
         'offense_style': 'Posesión elaborada', 'tags': ['Directo pero paciente'],
         'map': {'off': [44, 78, 'Posesión elaborada'], 'dfn': [70, 44, 'Línea alta, presión selectiva']}}


def _fresh_entity(eid='ame_jardine', style=AME):
    import labels
    pts = labels.map_points(style)
    return {'id': eid, 'style': style, 'identity': labels.identity(style), 'map': dict(pts, traj=[])}


class PressingAuditTests(unittest.TestCase):
    """AC-05: lo publicado (tarjetas, mapa, etiquetas, explorador) dice lo mismo que los percentiles."""

    def test_fresh_identity_and_map_pass(self):
        self.assertEqual(ac.check_labels({'entities': [_fresh_entity()], 'map': {'units': []}}), [])

    def test_stale_selective_card_is_an_error(self):
        ent = dict(_fresh_entity(), identity=STALE)
        errs = ac.check_labels({'entities': [ent], 'map': {'units': []}})
        self.assertTrue(any('desactualizada' in e for e in errs), errs)
        self.assertTrue(any('volumen_presion' in e and 'presión selectiva' in e for e in errs), errs)

    def test_map_point_must_be_the_engine_point(self):
        ent = _fresh_entity()
        ent['map'] = {'off': ent['map']['off'], 'dfn': [70, 58], 'traj': []}
        errs = ac.check_labels({'entities': [ent], 'map': {'units': []}})
        self.assertTrue(any('punto del mapa dfn' in e for e in errs), errs)

    def test_identities_inside_payloads_are_checked_against_their_percentiles(self):
        import labels
        metrics = [{'clave': k, 'ref_pct': v, 'id': 'estilo_' + k} for k, v in AME.items()]
        payloads = {'explorer.json': {'equipos': [{'key': 'América', 'identity': STALE, 'metrics': metrics},
                                                  {'key': 'ok', 'identity': labels.identity(AME), 'metrics': metrics}]}}
        errs = ac.check_payload_identities(payloads)
        self.assertTrue(errs)
        self.assertTrue(all('América' in e for e in errs), errs)
        self.assertTrue(any('presión selectiva' in e for e in errs), errs)

    def test_metrics_keyed_by_clave_also_give_the_style(self):
        metrics = {k: {'id': k, 'ref_pct': v, 'value': 1.0} for k, v in AME.items()}
        errs = ac.check_payload_identities({'explorer.json': {'equipos': [{'key': 'América', 'identity': STALE,
                                                                           'metrics': metrics}]}})
        self.assertTrue(any('desactualizada' in e for e in errs), errs)

    def test_run_reports_payload_identity_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            rep = ac.run(pathlib.Path(tmp))
            self.assertIn('etiquetas_vistas', rep['errores'])


if __name__ == '__main__':
    unittest.main()
