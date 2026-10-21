"""Tests del motor de etiquetas: identidad coherente (sin pares en conflicto) para toda entidad y unidad."""
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import labels

ROOT = HERE.parent
MODEL = ROOT / 'model' / 'model.json'
CONTRA = ROOT / 'data' / 'out' / 'baseline' / 'label_contradictions.json'
JARDINE = {'posesion': 74, 'verticalidad': 81, 'ritmo': 31, 'linea': 59, 'volumen_presion': 58, 'presion': 10,
           'contrapresion': 30, 'saque_largo': 61, 'centros': 31, 'contragolpe': 58, 'presion_alta_tiros': 60,
           'xg': 93, 'xga': 88, 'bp_xg': 64}


def _model():
    return json.loads(MODEL.read_text(encoding='utf-8'))


class IdentityTests(unittest.TestCase):
    def test_jardine_combined_rule_and_no_pase_corto_with_vertical(self):
        ident = labels.identity(JARDINE)
        self.assertIn('Directo pero paciente', ident['tags'])
        self.assertNotIn('Muy vertical', ident['tags'])
        self.assertNotEqual(ident['build'], 'Pase corto')
        self.assertEqual(labels.conflicts(ident), [])

    def test_defense_card_is_map_quadrant(self):
        ident = labels.identity(JARDINE)
        self.assertEqual(ident['defense'], ident['map']['dfn'][2])
        self.assertEqual(ident['map']['dfn'][1], round((58 + 10 + 30) / 3))
        self.assertEqual(ident['map']['off'][0], round((31 + 58) / 2))

    def test_presion_selectiva_text(self):
        ident = labels.identity(dict(JARDINE, presion=90, volumen_presion=30))
        self.assertIn('Presión selectiva: pocas presiones, pero roba pronto (PPDA bajo)', ident['tags'])
        self.assertNotIn('Corta con duelos, no presiona', ident['tags'])

    def test_missing_data(self):
        ident = labels.identity({})
        self.assertEqual(ident['build'], 'Datos insuficientes')
        self.assertIsNone(ident['map']['off'])
        self.assertEqual(ident['defense'], 'Datos insuficientes')

    def test_equilibrado_drops_extreme_tag_same_axis(self):
        st = dict(JARDINE, ritmo=85, contragolpe=15, posesion=50, verticalidad=50)
        ident = labels.identity(st)
        self.assertEqual(ident['map']['off'][2], 'Equilibrado')
        self.assertNotIn('Ataques rápidos', ident['tags'])
        self.assertEqual(labels.conflicts(ident), [])

    def test_no_conflicts_in_any_model_entity(self):
        for e in _model()['entities']:
            ident = labels.identity(e.get('style') or {})
            self.assertEqual(labels.conflicts(ident), [], e['id'])
            self.assertEqual(ident['defense'], ident['map']['dfn'][2] if ident['map']['dfn'] else 'Datos insuficientes')

    def test_map_units_quadrants_consistent(self):
        for u in _model()['map']['units']:
            q = labels.quadrant('dfn', u['dfn'])
            self.assertIn(q, set(labels.QUADRANTS['dfn'].values()) | {'Equilibrado'})

    def test_every_baseline_contradiction_resolved(self):
        ents = {e['id']: e for e in _model()['entities']}
        for c in json.loads(CONTRA.read_text(encoding='utf-8'))['contradicciones']:
            if c['id'] not in ents:
                continue
            ident = labels.identity(ents[c['id']].get('style') or {})
            self.assertEqual(labels.conflicts(ident), [], c)


if __name__ == '__main__':
    unittest.main()
