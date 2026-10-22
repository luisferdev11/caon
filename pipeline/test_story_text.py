"""Helpers de la historia (T-07): números, rangos descriptivos, niveles y hallazgos."""
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import framework as fw
import story_text as st


def rec(**kw):
    return dict({'id': 'xg', 'value': 1.515, 'n': 91, 'unit': 'xG sin penal por partido', 'source': 'eventos',
                 'window': 'oficial', 'entity': 'e1', 'ref_pct': 97.2}, **kw)


class NumberTests(unittest.TestCase):
    def test_numbers_have_at_most_two_decimals_and_drop_trailing_zeros(self):
        self.assertEqual(st.num(1.515), '1.52')
        self.assertEqual(st.num(46.542), '46.54')
        self.assertEqual(st.num(2.0), '2')
        self.assertEqual(st.num(0.0756), '0.08')
        self.assertEqual(st.num(None), 's/d')

    def test_percent_and_signed(self):
        self.assertEqual(st.pct(59.792), '59.8 %')
        self.assertEqual(st.signed(0.658), '+0.66')
        self.assertEqual(st.signed(-0.19), '-0.19')


class RankTests(unittest.TestCase):
    def test_rank_is_descriptive_above_and_below_the_median(self):
        self.assertEqual(st.rank(94.4), 'más que 94 de cada 100 equipos-temporada')
        self.assertEqual(st.rank(33.3), 'menos que 67 de cada 100 equipos-temporada')
        self.assertEqual(st.rank(50.0), 'a la par de la mitad de los equipos-temporada')
        self.assertIsNone(st.rank(None))

    def test_rank_never_says_one_hundred_of_one_hundred(self):
        self.assertEqual(st.rank(100), 'más que 99 de cada 100 equipos-temporada')
        self.assertEqual(st.rank(0), 'menos que 99 de cada 100 equipos-temporada')
        self.assertEqual(st.rank(99.6), 'más que 99 de cada 100 equipos-temporada')

    def test_style_phrase_uses_human_names_and_orientation(self):
        self.assertEqual(st.style_phrase('xga', 88), 'solidez defensiva (xG en contra): mejor que 88 de cada 100 equipos-temporada')
        self.assertEqual(st.style_phrase('xga', 20), 'solidez defensiva (xG en contra): peor que 80 de cada 100 equipos-temporada')
        self.assertEqual(st.style_phrase('posesion', 81), 'posesión: más que 81 de cada 100 equipos-temporada')
        self.assertEqual(st.style_phrase('verticalidad', 31), 'verticalidad: menos que 69 de cada 100 equipos-temporada')
        self.assertEqual(st.style_phrase('raro', 60), 'raro: más que 60 de cada 100 equipos-temporada')

    def test_auto_number_uses_one_decimal_from_ten_up(self):
        self.assertEqual(st.auto(59.792), '59.8')
        self.assertEqual(st.auto(0.1153), '0.12')
        self.assertEqual(st.auto(36.8333), '36.8')
        self.assertEqual(st.auto(None), 's/d')

    def test_level_buckets(self):
        self.assertEqual([st.level(p) for p in (97, 70, 50, 30, 5, None)], ['alto', 'alto', 'medio', 'bajo', 'bajo', None])

    def test_pick_never_gives_the_high_text_below_the_median(self):
        texts = {'alto': 'A', 'medio': 'M', 'bajo': 'B'}
        for p in range(50):
            self.assertNotEqual(st.pick(p, texts), 'A')
        for p in range(51, 101):
            self.assertNotEqual(st.pick(p, texts), 'B')
        self.assertEqual(st.pick(None, texts), 'M')

    def test_good_percentile_flips_with_lower_is_better(self):
        self.assertEqual(st.good_pct(33.3, 'bajo'), 66.7)
        self.assertEqual(st.good_pct(33.3, 'alto'), 33.3)
        self.assertIsNone(st.good_pct(None, 'bajo'))


class EvidenceTests(unittest.TestCase):
    def test_evidence_copies_the_contract_fields_only(self):
        e = st.ev(rec(ci=[1.4, 1.6], extra='x'))
        self.assertEqual(sorted(e), ['ci', 'entity', 'id', 'n', 'ref_pct', 'source', 'unit', 'value', 'window'])
        self.assertEqual(e['value'], 1.515)

    def test_evidence_keeps_scope_and_source_when_present(self):
        e = st.ev(rec(scope='concedido', source='360'))
        self.assertEqual(e['scope'], 'concedido')
        self.assertEqual(e['source'], '360')

    def test_evidence_of_a_missing_record_is_none(self):
        self.assertIsNone(st.ev(None))
        self.assertIsNone(st.ev({'id': 'xg', 'value': None, 'motivo': 'sin dato'}))

    def test_evidence_with_unregistered_id_is_rejected(self):
        with self.assertRaises(KeyError):
            st.ev(rec(id='inventada'))


class FindingTests(unittest.TestCase):
    def test_finding_has_the_contract_keys_and_registered_evidence(self):
        f = st.finding('f1', 'con_balon', ['xg'], 'Crea ocasiones de calidad', 'Hecho.', 'Interpretación.',
                       [rec()], 'Vigilar xG.', pct=97.2)
        for k in ('id', 'capitulo', 'componentes', 'titulo', 'hecho', 'interpretacion', 'evidencia', 'accion', 'modo',
                  'window', 'pct_principal'):
            self.assertIn(k, f)
        self.assertEqual(f['window'], 'oficial')
        self.assertEqual(f['modo'], 'ambos')
        self.assertEqual(f['evidencia'][0]['id'], 'xg')
        json.dumps(f, allow_nan=False)

    def test_finding_without_any_evidence_is_dropped(self):
        self.assertIsNone(st.finding('f1', 'c', ['xg'], 't', 'h', 'i', [None, {'id': 'xg', 'value': None}], 'a'))

    def test_finding_window_follows_its_evidence_and_rejects_mixed_windows(self):
        f = st.finding('f', 'c', ['xg'], 't', 'h', 'i', [rec(window='epilogo')], 'a')
        self.assertEqual(f['window'], 'epilogo')
        with self.assertRaises(ValueError):
            st.finding('f', 'c', ['xg'], 't', 'h', 'i', [rec(), rec(window='epilogo')], 'a')

    def test_hecho_and_interpretacion_are_separate_fields(self):
        f = st.finding('f', 'c', ['xg'], 't', 'Dato.', 'Lectura.', [rec()], 'a')
        self.assertNotEqual(f['hecho'], f['interpretacion'])

    def test_contradiction_check_flags_high_words_for_a_low_percentile(self):
        bad = st.finding('f', 'c', ['xg'], 'Tiene un nivel entre los más altos', 'h', 'i', [rec()], 'a', pct=20.0)
        self.assertTrue(st.contradictions(bad))
        ok = st.finding('f', 'c', ['xg'], 'Está por debajo de la mayoría', 'h', 'i', [rec()], 'a', pct=20.0)
        self.assertEqual(st.contradictions(ok), [])
        bad2 = st.finding('f', 'c', ['xg'], 't', 'h', 'Está por debajo de la liga', [rec()], 'a', pct=90.0)
        self.assertTrue(st.contradictions(bad2))

    def test_contradiction_check_ignores_findings_without_a_main_percentile(self):
        f = st.finding('f', 'c', ['xg'], 'entre los más altos', 'h', 'i', [rec()], 'a')
        self.assertEqual(st.contradictions(f), [])


class BadgeAndEntityTests(unittest.TestCase):
    def test_out_of_window_findings_and_their_evidence_carry_the_badge(self):
        for window in ('epilogo', 'temprano'):
            f = st.finding('f', 'c', ['xg'], 't', 'h', 'i', [rec(window=window)], 'a')
            self.assertTrue(f['fuera_de_ventana'])
            self.assertTrue(all(e['fuera_de_ventana'] for e in f['evidencia']))
        official = st.finding('f', 'c', ['xg'], 't', 'h', 'i', [rec()], 'a')
        self.assertNotIn('fuera_de_ventana', official)
        self.assertNotIn('fuera_de_ventana', official['evidencia'][0])

    def test_tag_entities_fills_missing_entities_without_overwriting(self):
        f = st.finding('f', 'c', ['xg'], 't', 'h', 'i', [rec(), rec(id='xga', entity='otra')], 'a')
        ch = st.chapter('c', 1, 'C', [f])
        st.tag_entities([ch], 'e1')
        self.assertEqual([e['entity'] for e in f['evidencia']], ['e1', 'otra'])


class ChapterTests(unittest.TestCase):
    def test_chapter_shape_and_empty_chapter_is_kept_with_reason(self):
        f = st.finding('f', 'con_balon', ['xg'], 't', 'h', 'i', [rec()], 'a')
        ch = st.chapter('con_balon', 3, 'Con balón', [f, None], conclusion='C', curioso='D', visual='shot_map')
        self.assertEqual(len(ch['hallazgos']), 1)
        self.assertEqual(ch['aficionado'], {'conclusion': 'C', 'curioso': 'D', 'visual': 'shot_map'})
        empty = st.chapter('x', 4, 'X', [None])
        self.assertEqual(empty['hallazgos'], [])
        self.assertTrue(empty['motivo'])


class WindowKnownTests(unittest.TestCase):
    def test_framework_windows(self):
        self.assertEqual(set(fw.WINDOWS), {'oficial', 'epilogo', 'temprano'})


if __name__ == '__main__':
    unittest.main()
