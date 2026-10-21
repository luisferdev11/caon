"""Tests for the acceptance registry (AC-01..AC-17)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acceptance as A
import labels


class RegistryTest(unittest.TestCase):
    def test_all_ids_registered_in_order(self):
        ids = [c.ac_id for c in A.CHECKS]
        self.assertEqual(ids, [f'AC-{i:02d}' for i in range(1, 18)])

    def test_failing_check_becomes_fail_not_crash(self):
        res = A.run_check(A.Check('AC-99', 'x', lambda ctx: 1 / 0), A.Context(Path('.'), http=False))
        self.assertEqual(res['status'], A.FAIL)
        self.assertIn('ZeroDivisionError', res['evidence'])

    def test_markdown_symbols(self):
        rows = [{'id': 'AC-01', 'title': 't', 'status': A.OK, 'evidence': 'a|b'},
                {'id': 'AC-02', 'title': 't', 'status': A.FAIL, 'evidence': 'e'},
                {'id': 'AC-03', 'title': 't', 'status': A.PENDING, 'evidence': 'r'}]
        md = A.render_markdown(rows, '2026-10-21 07:00')
        self.assertIn('| AC-01 | t | ✅ |', md)
        self.assertIn('❌', md)
        self.assertIn('⏳', md)
        self.assertIn('a\\|b', md)


class PureHelpersTest(unittest.TestCase):
    def test_extract_digest_ignores_names_and_key_order(self):
        a = {'src': 'x', 'mid': 1, 'teams': {'1': {'n': [1], 'shot': [2]}}, 'names': {'5': 'A'}}
        b = {'names': {'5': 'B'}, 'mid': 1, 'src': 'x', 'teams': {'1': {'shot': [2], 'n': [1]}}}
        self.assertEqual(A.extract_digest(a), A.extract_digest(b))
        b['teams']['1']['n'] = [2]
        self.assertNotEqual(A.extract_digest(a), A.extract_digest(b))

    def test_label_contradictions(self):
        row = {'id': 'e', 'build': 'Pase corto', 'def': 'Alto', 'att': 'Mixto',
               'tags': ['Muy vertical', 'Ataques pausados'], 'q_off': 'Dominio vertical', 'q_dfn': 'Bloque bajo',
               'map_off': [60, 70], 'map_dfn': [30, 30]}
        found = {c['rule'] for c in A.label_contradictions(row)}
        self.assertIn('pase_corto_vs_muy_vertical', found)
        self.assertIn('ataques_pausados_vs_mapa_rapido', found)
        self.assertIn('def_alto_vs_mapa_bajo', found)

    def test_no_contradiction_for_coherent_row(self):
        row = {'id': 'e', 'build': 'Equilibrado', 'def': 'Profundo', 'att': 'Mixto', 'tags': ['Bloque bajo'],
               'q_off': 'Reactivo', 'q_dfn': 'Bloque bajo', 'map_off': [30, 30], 'map_dfn': [20, 20]}
        self.assertEqual(A.label_contradictions(row), [])

    def test_markdown_sections(self):
        text = '# V\n## Antes\nx\n## Después\ny\n'
        self.assertEqual(A.md_sections(text), ['V', 'Antes', 'Después'])


class CheckFunctionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'docs').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_ac01_pending_without_after_section(self):
        (self.root / 'docs' / 'VALIDACION_MODELOS.md').write_text('# V\n## Antes\nok\n', encoding='utf-8')
        res = A.check_ac01(A.Context(self.root, http=False))
        self.assertEqual(res[0], A.PENDING)

    def test_ac01_ok_with_both_sections(self):
        (self.root / 'docs' / 'VALIDACION_MODELOS.md').write_text('# V\n## Antes\nok\n## Después\nok\n', encoding='utf-8')
        self.assertEqual(A.check_ac01(A.Context(self.root, http=False))[0], A.OK)

    def test_ac01_pending_when_after_section_is_placeholder(self):
        (self.root / 'docs' / 'VALIDACION_MODELOS.md').write_text('# V\n## Antes\nok\n## Después\n⏳ Pendiente\n', encoding='utf-8')
        self.assertEqual(A.check_ac01(A.Context(self.root, http=False))[0], A.PENDING)

    def test_ac03_reads_model_entities(self):
        (self.root / 'model').mkdir()
        model = {'entities': [{'id': 'ame_jardine', 'n': 70, 'official': True}]}
        (self.root / 'model' / 'model.json').write_text(json.dumps(model), encoding='utf-8')
        status, evidence = A.check_ac03(A.Context(self.root, http=False))
        self.assertEqual(status, A.FAIL)
        self.assertIn('n=70', evidence)

    def test_ac11_counts_tofixed3(self):
        (self.root / 'frontend').mkdir()
        (self.root / 'frontend' / 'a.js').write_text('x.toFixed(3); y.toFixed(2)', encoding='utf-8')
        status, evidence = A.check_ac11(A.Context(self.root, http=False))
        self.assertEqual(status, A.FAIL)
        self.assertIn('toFixed(3)', evidence)


class QuadrantNamesFromLabelsTest(unittest.TestCase):
    def test_rule_sets_use_only_names_defined_in_labels(self):
        known = set(labels.QUADRANTS['off'].values()) | set(labels.QUADRANTS['dfn'].values()) | set(labels.DFN_QUALIFIED.values())
        for group in (A._FAST, A._SLOW, A._PRESS, A._WAIT, A.LINE_HIGH, A.LINE_LOW):
            self.assertTrue(group and set(group) <= known, group)

    def test_qualified_names_count_as_line_side_and_wait(self):
        alta = labels.DFN_QUALIFIED[('alta', 'selectiva')]
        row = {'id': 'x', 'tags': ['Bloque bajo', 'Presión asfixiante'], 'q_dfn': alta}
        found = {c['rule'] for c in A.label_contradictions(row)}
        self.assertIn('bloque_bajo_vs_mapa', found)
        self.assertIn('asfixiante_vs_espera', found)

    def test_line_sides_follow_quadrant_keys(self):
        self.assertEqual(set(A.LINE_HIGH) & set(A.LINE_LOW), set())
        self.assertIn(labels.QUADRANTS['dfn']['tr'], A.LINE_HIGH)
        self.assertIn(labels.QUADRANTS['dfn']['bl'], A.LINE_LOW)


class FrontendLabelsTest(unittest.TestCase):
    def test_rows_for_every_entity_and_unit(self):
        rows = A.frontend_label_rows(A.ROOT)
        model = json.loads((A.ROOT / 'model' / 'model.json').read_text(encoding='utf-8'))
        self.assertEqual(len(rows), len(model['entities']) + len(model['map']['units']))
        jardine = next(r for r in rows if r['id'] == 'ame_jardine')
        names = set(labels.QUADRANTS['dfn'].values()) | set(labels.DFN_QUALIFIED.values()) | {labels.EQ}
        self.assertIn(jardine['q_dfn'], names)
        self.assertTrue(jardine['build'])


if __name__ == '__main__':
    unittest.main()
