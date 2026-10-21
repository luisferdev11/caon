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
        self.assertEqual(ident['defense'], 'Línea alta, presión selectiva')
        self.assertEqual(ident['pressing']['texto'], 'Presión selectiva: pocas presiones, pero roba pronto (PPDA bajo)')
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


# América·Jardine real (model.json G1): volumen P71, PPDA invertido P18, contrapresión P44, línea P70.
AME_JARDINE = dict(JARDINE, linea=70, volumen_presion=71, presion=18, contrapresion=44, ritmo=30, verticalidad=84,
                   posesion=78)
GRID = (5, 20, 35, 45, 55, 65, 80, 95)


def _grid_styles():
    for v in GRID:
        for i in GRID:
            for c in GRID:
                for li in GRID:
                    yield dict(JARDINE, volumen_presion=v, presion=i, contrapresion=c, linea=li)


class PressingCoherenceTests(unittest.TestCase):
    """Volumen, PPDA y contrapresión nunca cuentan historias opuestas (regla documentada en DEFINITIONS)."""

    def test_ame_jardine_presses_a_lot_but_wins_little_not_selective(self):
        ident = labels.identity(AME_JARDINE)
        self.assertEqual(ident['pressing']['perfil'], 'sin_robo')
        self.assertEqual(ident['defense'], 'Línea alta: presiona mucho, roba poco')
        self.assertEqual(ident['defense'], ident['map']['dfn'][2])
        self.assertNotIn('selectiva', ident['defense'].lower())
        self.assertFalse(any('selectiva' in t.lower() for t in ident['tags']))
        self.assertEqual(labels.conflicts(ident), [])
        self.assertEqual(labels.claim_violations(ident, AME_JARDINE), [])

    def test_selectiva_needs_few_pressures_and_good_ppda(self):
        sel = labels.identity(dict(AME_JARDINE, volumen_presion=15, presion=80))
        self.assertEqual(sel['pressing']['perfil'], 'selectiva')
        self.assertEqual(sel['defense'], 'Línea alta, presión selectiva')
        busy = labels.identity(dict(AME_JARDINE, volumen_presion=71, presion=80, contrapresion=60))
        self.assertNotIn('selectiva', busy['defense'].lower())
        low = labels.identity(dict(AME_JARDINE, linea=30, volumen_presion=15, presion=80))
        self.assertEqual(low['defense'], 'Línea baja, presión selectiva')

    def test_high_line_low_intensity_base_name_is_neutral(self):
        ident = labels.identity(dict(AME_JARDINE, volumen_presion=6, presion=21, contrapresion=7, linea=65))
        self.assertEqual(ident['pressing']['perfil'], None)
        self.assertEqual(ident['defense'], 'Línea alta, baja intensidad')
        self.assertEqual(labels.QUADRANTS['dfn']['br'], 'Línea alta, baja intensidad')

    def test_region_names_speak_only_of_line_and_combined_intensity(self):
        for name in labels.QUADRANTS['dfn'].values():
            self.assertEqual(set(labels.SLOT_CLAIMS['dfn'][name]), {'linea', 'intensidad_presion'}, name)
            self.assertNotIn('poca presión', name)
            self.assertNotIn('presiona', name.lower())
        for name in labels.DFN_QUALIFIED.values():
            self.assertIn('volumen_presion', labels.SLOT_CLAIMS['dfn'][name], name)

    def test_profiles_are_exclusive_and_documented(self):
        self.assertEqual(set(labels.PRESS_PROFILES), {'asfixiante', 'sin_robo', 'selectiva', 'espera'})
        for key, prof in labels.PRESS_PROFILES.items():
            self.assertTrue(prof['texto'] and prof['claims'], key)
        hits = [k for k, p in labels.PRESS_PROFILES.items()
                if labels.satisfies(p['claims'], labels.signals(AME_JARDINE))]
        self.assertEqual(hits, ['sin_robo'])

    def test_no_label_contradicts_the_pressing_numbers_on_a_grid(self):
        for st in _grid_styles():
            ident = labels.identity(st)
            self.assertEqual(labels.conflicts(ident), [], st)
            self.assertEqual(labels.claim_violations(ident, st), [], st)
            self.assertEqual(ident['defense'], ident['map']['dfn'][2], st)

    def test_conflicts_cover_every_pair_of_opposite_pressing_stories(self):
        pairs = {frozenset(p) for p in labels.conflict_pairs()}
        texts = labels.pressing_label_texts()
        claims = labels.claims_by_text()
        for a in texts:
            for b in texts:
                if a != b and labels.disjoint(claims[a], claims[b]):
                    self.assertIn(frozenset((a, b)), pairs, (a, b))
        for a, b in (('Presión asfixiante', 'Línea alta: presiona mucho, roba poco'),
                     ('Presión asfixiante', 'Línea alta, presión selectiva'), ('Espera al rival', 'Presión alta'),
                     ('Línea alta, presión selectiva', 'Línea alta: presiona mucho, roba poco'),
                     ('Presión asfixiante', 'Línea alta, baja intensidad'), ('Línea muy alta', 'Bloque bajo')):
            self.assertIn(frozenset((a, b)), pairs, (a, b))

    def test_stale_selective_card_is_a_claim_violation(self):
        stale = {'build': 'Posesión con pase vertical', 'defense': 'Línea alta, presión selectiva', 'attack': 'Mixto',
                 'offense_style': 'Posesión elaborada', 'tags': ['Directo pero paciente'],
                 'map': {'off': [49, 78, 'Posesión elaborada'], 'dfn': [70, 44, 'Línea alta, presión selectiva']}}
        bad = labels.claim_violations(stale, AME_JARDINE)
        self.assertTrue(any('volumen_presion' in b for b in bad), bad)
        self.assertTrue(any('presion' in b for b in bad), bad)

    def test_offense_labels_respect_their_numbers(self):
        for r in GRID:
            for cg in GRID:
                for pos in GRID:
                    for vert in GRID:
                        st = dict(JARDINE, ritmo=r, contragolpe=cg, posesion=pos, verticalidad=vert)
                        ident = labels.identity(st)
                        self.assertEqual(labels.conflicts(ident), [], st)
                        self.assertEqual(labels.claim_violations(ident, st), [], st)

    def test_real_entities_respect_their_numbers(self):
        for e in _model()['entities']:
            st = e.get('style') or {}
            self.assertEqual(labels.claim_violations(labels.identity(st), st), [], e['id'])


if __name__ == '__main__':
    unittest.main()
