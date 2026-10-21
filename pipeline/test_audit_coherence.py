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


if __name__ == '__main__':
    unittest.main()
