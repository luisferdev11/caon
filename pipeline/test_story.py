"""Historia (T-07): redacción condicional, ventanas, cobertura del reto, trazabilidad y no contradicción."""
import json
import pathlib
import re
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import framework as fw
import labels
import story
import story_almada as sa
import story_ch_a as ca
import story_ch_b as cb
import story_ch_c as cc
import story_ch_d as cd
import story_text as st
from story_text import Src

MODEL = HERE.parent / 'model'
BANNED = re.compile(r'\b(unknown|undefined|None|nan|NaN|null|Directness|losing|winning|xga:|posesion:|presion:|linea:)\b')


def rec(rid, value, pct=None, n=91, **kw):
    return dict({'id': rid, 'value': value, 'n': n, 'unit': 'u', 'source': 'eventos', 'window': 'oficial', 'ref_pct': pct}, **kw)


def src(analysis=None, kpis=None, style=None, window='oficial', entity='e1'):
    style = style or {}
    return Src(analysis or {}, kpis or [], style, labels.identity(style), window, entity, 'E1', 91)


def ocasiones(pct):
    return {'offense': {'ventanas': {'oficial': {'ocasiones': {'npxg_por_tiro': rec('npxg_por_tiro', 0.115, pct)}}}}}


class ConditionalWordingTests(unittest.TestCase):
    def test_chances_title_follows_the_percentile(self):
        hi = ca._chances(src(ocasiones(95)))
        mid = ca._chances(src(ocasiones(50)))
        lo = ca._chances(src(ocasiones(10)))
        self.assertIn('valen más', hi['titulo'])
        self.assertIn('lo normal', mid['titulo'])
        self.assertIn('valen menos', lo['titulo'])
        self.assertEqual(st.contradictions(hi) + st.contradictions(lo), [])

    def test_no_chapter_makes_up_a_finding_without_records(self):
        s = src()
        for chapter in (ca.portada(s), ca.con_balon(s), cb.sin_balon(s), cb.transiciones(s), cc.lo_que_mas_dolio(s),
                        cc.balon_parado(s), cc.consistencia_contexto(s)):
            self.assertEqual(chapter['hallazgos'], [], chapter['id'])
            self.assertTrue(chapter['motivo'])

    def test_empty_source_still_builds_twelve_chapters(self):
        doc = story.build_jardine(src(), None)
        self.assertEqual([c['orden'] for c in doc['capitulos']], list(range(1, 13)))
        self.assertTrue(all(not c['hallazgos'] for c in doc['capitulos']))
        json.dumps(doc, allow_nan=False)

    def test_pressing_title_uses_the_profile_and_ppda_meaning_follows_its_percentile(self):
        analysis = {'defense': {'ventanas': {'oficial': {'presion': {'ppda': rec('ppda', 14.0, 94.4)}}}}}
        style = {'volumen_presion': 67, 'presion': 8, 'contrapresion': 44, 'linea': 81}
        f = cb._pressing(src(analysis, style=style))
        self.assertEqual(f['titulo'], labels.SIN_ROBO)
        self.assertIn('muchos pases', f['hecho'])
        low = cb._pressing(src({'defense': {'ventanas': {'oficial': {'presion': {'ppda': rec('ppda', 8.0, 10)}}}}}))
        self.assertIn('Corta pronto', low['titulo'])

    def test_context_noise_is_said_when_the_band_includes_zero(self):
        def ctx(band):
            h = {'dimension': 'localia', 'grupo': 'local', 'metrica': 'puntos', 'valor': 2.0, 'resto': 1.9, 'dif': 0.1,
                 'banda_dif': band, 'n': 45, 'confianza': 'alta'}
            return src({'context': {'ventanas': {'oficial': {'hallazgos': [h], 'metricas': {'puntos': {'id': 'puntos', 'unidad': 'p', 'fuente': 'eventos'}}}}}})
        noisy, clear = cc._dim_finding(ctx([-0.2, 0.4]), 'localia'), cc._dim_finding(ctx([0.1, 0.5]), 'localia')
        self.assertIn('sin cambio claro', noisy['titulo'])
        self.assertIn('dentro del ruido', noisy['interpretacion'])
        self.assertNotIn('sin cambio claro', clear['titulo'])
        self.assertIn('supera el ruido', clear['interpretacion'])

    def test_context_groups_with_few_matches_are_never_cited(self):
        h = {'dimension': 'minuto', 'grupo': 'prorroga', 'metrica': 'field_tilt', 'valor': 83.0, 'resto': 60.0, 'dif': 23.0,
             'banda_dif': [21.0, 25.0], 'n': 1, 'confianza': 'muy baja'}
        s = src({'context': {'ventanas': {'oficial': {'hallazgos': [h], 'dimensiones': {'minuto': {'grupos': {'prorroga': {'field_tilt': dict(h, valor=83.0)}}}}}}}})
        self.assertIsNone(cc._dim_finding(s, 'minuto'))


ALMADA_EXPLORER = {
    'metricas': [{'id': 'xg', 'nombre': 'xG a favor', 'unit': 'xG por partido'}, {'id': 'posesion', 'nombre': 'Posesión', 'unit': 'proporción'}],
    'entrenadores': [{'tenencias': [
        {'n': 10, 'confidence': 'baja', 'entidades': [{'id': 'ame_almada'}],
         'metrics': {'xg': {'n': 10, 'value': 1.4, 'raw': 1.5, 'prior_value': 1.2, 'ci': [1.3, 1.6], 'ref_pct': 80},
                     'posesion': {'n': 10, 'value': 0.53, 'raw': 0.55, 'prior_value': 0.5, 'ci': [0.48, 0.58], 'ref_pct': 70}}},
        {'n': 139, 'confidence': 'alta', 'entidades': [{'id': 'pac_almada'}],
         'metrics': {'xg': {'n': 139, 'value': 1.1, 'raw': 1.1, 'ci': [1.0, 1.2], 'ref_pct': 50},
                     'posesion': {'n': 139, 'value': 0.52, 'raw': 0.52, 'ci': [0.5, 0.54], 'ref_pct': 60}}}]}]}


def kpi(kid, nombre, mejor, value, pct, **extra):
    return dict({'id': kid, 'nombre': nombre, 'mejor': mejor, 'value': value, 'n': 91, 'unit': 'u', 'window': 'oficial',
                 'ref_pct': pct, 'kpi': 1}, **extra)


class KpiWordingTests(unittest.TestCase):
    def rows(self):
        return [kpi('field_tilt', 'Dominio territorial', 'alto', 59.8, 99), kpi('progresion_limpia', 'Progresión limpia', 'alto', 36.8, 97),
                kpi('npxg_por_tiro', 'Calidad de ocasión', 'alto', 0.12, 99),
                kpi('perdida_costosa', 'Pérdidas costosas por partido', 'bajo', 2.76, 33)]

    def test_a_strength_where_less_is_better_is_named_in_the_positive(self):
        f = ca._four_kpis(src(kpis=self.rows()))
        self.assertIn('pocas pérdidas costosas', f['titulo'])
        self.assertNotIn('Fuerte en dominio territorial, progresión limpia, calidad de ocasión y pérdidas costosas', f['titulo'])

    def test_a_weakness_where_less_is_better_is_named_as_many(self):
        rows = self.rows()
        rows[3]['ref_pct'] = 90
        f = ca._four_kpis(src(kpis=rows))
        self.assertIn('muchas pérdidas costosas', f['titulo'])

    def test_board_uses_positive_names_too(self):
        s = src(kpis=self.rows())
        f = cd._board(s, s.kpi_rows)
        self.assertIn('pocas pérdidas costosas', f['interpretacion'])


class FieldTiltNoteTests(unittest.TestCase):
    def ctx(self, perdiendo, ganando):
        grupos = {'perdiendo': {'field_tilt': {'valor': perdiendo}}, 'ganando': {'field_tilt': {'valor': ganando}}}
        return {'context': {'ventanas': {'oficial': {'dimensiones': {'marcador': {'grupos': grupos}}}}}}

    def tilt(self, green, red):
        return kpi('field_tilt', 'Dominio territorial', 'alto', 59.8, 99, semaforo={'verde': {'n': 30, 'pts_partido': green},
                   'ambar': {'n': 30, 'pts_partido': 1.9}, 'rojo': {'n': 30, 'pts_partido': red}},
                   frase='En partidos en verde sumó 1.73 pts/partido vs 2.13 en rojo (n=30/30); descriptivo.',
                   umbrales={'p33': 54.0, 'p67': 69.0})

    def test_the_marker_effect_is_explained_when_green_scored_less(self):
        s = src(self.ctx(74.1, 48.4), kpis=[self.tilt(1.73, 2.13)])
        note = cd.tilt_note(s)
        self.assertIn('74.1', note)
        self.assertIn('48.4', note)
        f = cd._lights(s, s.kpi_rows)
        self.assertIn('va perdiendo', f['interpretacion'])

    def test_no_note_when_green_scored_more_or_the_marker_effect_is_absent(self):
        self.assertEqual(cd.tilt_note(src(self.ctx(74.1, 48.4), kpis=[self.tilt(2.4, 1.2)])), '')
        self.assertEqual(cd.tilt_note(src(self.ctx(50.0, 60.0), kpis=[self.tilt(1.7, 2.1)])), '')
        self.assertEqual(cd.tilt_note(src()), '')


class SetPieceWordingTests(unittest.TestCase):
    def sp(self):
        zones = {'ofensivo': {'xg_bp': rec('bp_ofensivo', 0.35), 'saques_banda': {'n': 440, 'con_remate_pct': 10.9, 'xg': 5.3},
                              'corners': {'entrega': [{'zona': 'punto_penal', 'n': 205, 'pct': 45.1}, {'zona': 'corto', 'n': 113, 'pct': 24.8},
                                                      {'zona': 'primer_palo', 'n': 48, 'pct': 10.5}],
                                          'remates': {'por_zona': [{'zona': 'zona_remate', 'n': 97}, {'zona': 'fuera_area', 'n': 39}]}}},
                 'defensivo': {'xg_bp': rec('bp_defensivo', 0.28),
                               'zonas_vulnerables': [{'zona': 'zona_remate', 'remates': 190, 'xg': 20.2, 'goles': 12},
                                                     {'zona': 'fuera_area', 'remates': 190, 'xg': 5.0, 'goles': 8}]}}
        return src({'setpieces': {'ventanas': {'oficial': zones}}})

    def test_zones_findings_cover_delivery_shot_zones_throw_ins_and_vulnerability(self):
        off, dfn = cc._sp_zones_off(self.sp()), cc._sp_zones_def(self.sp())
        self.assertEqual(set(off['componentes']), {'bp_entrega_corner', 'bp_zonas_remate', 'bp_saques_banda'})
        self.assertIn('punto penal', off['hecho'])
        self.assertIn('zona de remate', off['hecho'])
        self.assertIn('440', off['hecho'])
        self.assertEqual(dfn['componentes'], ['bp_zonas_vulnerables'])
        self.assertIn('zona de remate', dfn['titulo'])
        self.assertIn('tentativ', dfn['interpretacion'])

    def test_two_definitions_of_set_piece_xg_are_named_in_both_texts(self):
        s = self.sp()
        self.assertIn('de peligro', cc._sp_off(s)['titulo'])
        self.assertIn('de peligro', cc._sp_def(s)['titulo'])
        dang = src({'dangerous': {'ventanas': {'oficial': {'resumen': {
            'jugadas_por_partido': rec('jugada_peligrosa_concedida', 10.7),
            'xg_por_tipo': {'juego_abierto': rec('xg_concedido', 0.45), 'balon_parado': rec('xg_concedido', 0.41)}}}}}})
        self.assertIn('cualquier reanudación', cc._danger_summary(dang)['hecho'])


class AlmadaTests(unittest.TestCase):
    def build(self):
        pac, ame, base = src(entity='pac_almada'), src(window='temprano', entity='ame_almada'), src(entity='ame_jardine')
        return sa.build_almada(pac, ame, base, ALMADA_EXPLORER)

    def test_two_chapters_and_early_evidence_flag(self):
        doc = self.build()
        self.assertEqual([c['id'] for c in doc['capitulos']], ['almada_pachuca', 'almada_america'])
        self.assertTrue(doc['evidencia_temprana'])
        self.assertEqual(doc['ventana'], 'temprano')

    def test_only_metrics_whose_interval_excludes_the_pachuca_value_are_listed_as_changed(self):
        doc = self.build()
        changed = next(f for c in doc['capitulos'] for f in c['hallazgos'] if f['id'] == 'almada_ya_cambio')
        self.assertIn('xG a favor sube', changed['titulo'])      # 1.1 queda fuera de [1.3, 1.6]
        self.assertNotIn('Posesión', changed['titulo'])          # 0.52 queda dentro de [0.48, 0.58]
        self.assertEqual({e['window'] for e in changed['evidencia']}, {'temprano'})

    def test_early_findings_show_raw_and_shrunk_values_with_interval_and_low_confidence(self):
        doc = self.build()
        early = next(f for c in doc['capitulos'] for f in c['hallazgos'] if f['id'] == 'almada_america_temprano')
        self.assertIn('1.5 crudo', early['hecho'])
        self.assertIn('1.4 ajustado', early['hecho'])
        self.assertIn('55 %', early['hecho'])                    # la posesión sale en porcentaje
        self.assertIn('Confianza baja', early['interpretacion'])
        self.assertIn('evidencia temprana', early['titulo'])
        self.assertTrue(all(e.get('ci') for e in early['evidencia']))

    def test_no_change_is_said_when_no_interval_excludes_the_pachuca_value(self):
        ex = json.loads(json.dumps(ALMADA_EXPLORER))
        ex['entrenadores'][0]['tenencias'][1]['metrics']['xg']['value'] = 1.45
        pac, ame, base = src(entity='pac_almada'), src(window='temprano', entity='ame_almada'), src(entity='ame_jardine')
        doc = sa.build_almada(pac, ame, base, ex)
        changed = next(f for c in doc['capitulos'] for f in c['hallazgos'] if f['id'] == 'almada_ya_cambio')
        self.assertIn('Aún no hay un cambio', changed['titulo'])


def numbers(node, out):
    if isinstance(node, dict):
        for v in node.values():
            numbers(v, out)
    elif isinstance(node, list):
        for v in node:
            numbers(v, out)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out.add(round(float(node), 4))
    return out


SYNTHETIC_SCOPES = ('percentil', 'encogido')


def real_story(name):
    try:
        return json.loads((MODEL / 'story' / f'{name}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


@unittest.skipUnless(real_story('jardine'), 'historia aún no generada')
class PublishedJardineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = real_story('jardine')
        cls.findings = [f for c in cls.doc['capitulos'] for f in c['hallazgos']]

    def test_twelve_chapters_each_with_at_least_one_finding(self):
        self.assertEqual([c['orden'] for c in self.doc['capitulos']], list(range(1, 13)))
        for c in self.doc['capitulos']:
            self.assertTrue(c['hallazgos'], c['id'])
            self.assertTrue(c['aficionado']['visual'], c['id'])

    def test_chapters_one_to_eleven_use_only_the_official_window_and_the_epilogue_is_marked(self):
        for c in self.doc['capitulos'][:11]:
            for f in c['hallazgos']:
                self.assertEqual(f['window'], 'oficial', f['id'])
                self.assertEqual({e['window'] for e in f['evidencia']}, {'oficial'}, f['id'])
        self.assertEqual({f['window'] for f in self.doc['capitulos'][11]['hallazgos']}, {'epilogo'})

    def test_every_component_of_the_challenge_has_a_finding_with_evidence(self):
        for comp, ids in self.doc['cobertura'].items():
            self.assertTrue(ids, comp)
        self.assertEqual(set(self.doc['cobertura']), set(story.REQUIRED_COMPONENTS))
        for comp in ('bp_entrega_corner', 'bp_zonas_remate', 'bp_saques_banda', 'bp_zonas_vulnerables'):
            self.assertIn(comp, story.REQUIRED_COMPONENTS)

    def test_no_finding_contradicts_its_main_percentile(self):
        self.assertEqual([m for f in self.findings for m in st.contradictions(f)], [])

    def test_finding_contract_and_registered_evidence(self):
        for f in self.findings:
            for k in ('id', 'titulo', 'hecho', 'interpretacion', 'evidencia', 'accion', 'modo', 'window'):
                self.assertTrue(f.get(k) not in (None, ''), (f['id'], k))
            self.assertIn(f['modo'], ('aficionado', 'dt', 'ambos'))
            for e in f['evidencia']:
                self.assertIn(e['id'], fw.DEFINITIONS)
        self.assertEqual(len({f['id'] for f in self.findings}), len(self.findings))

    def test_every_cited_number_exists_in_analysis_or_kpis(self):
        pool = numbers(json.loads((MODEL / 'analysis' / 'ame_jardine.json').read_text(encoding='utf-8')), set())
        pool = numbers(json.loads((MODEL / 'kpis' / 'ame_jardine.json').read_text(encoding='utf-8')), pool)
        pool = numbers(json.loads((MODEL / 'analysis' / 'ame_jardine_epi.json').read_text(encoding='utf-8')), pool)
        pool = numbers(json.loads((MODEL / 'kpis' / 'ame_jardine_epi.json').read_text(encoding='utf-8')), pool)
        for f in self.findings:
            for e in f['evidencia']:
                if e.get('scope') in SYNTHETIC_SCOPES:
                    continue
                self.assertIn(round(float(e['value']), 4), pool, (f['id'], e['id'], e['value']))

    def test_user_text_has_no_raw_ids_or_english(self):
        for f in self.findings:
            for k in ('titulo', 'hecho', 'interpretacion', 'accion'):
                self.assertIsNone(BANNED.search(f[k]), (f['id'], k, BANNED.search(f[k])))

    def test_identity_is_cited_by_card_never_by_region(self):
        for name in ('story_ch_a.py', 'story_ch_b.py', 'story_ch_c.py', 'story_ch_d.py', 'story_almada.py', 'story.py'):
            self.assertNotIn("['regions']", (HERE / name).read_text(encoding='utf-8'), name)
            self.assertNotIn("'regions'", (HERE / name).read_text(encoding='utf-8'), name)

    def test_aficionado_cards_do_not_pile_up_numbers_in_the_title(self):
        for f in self.findings:
            plain = re.sub(r'\b\d+-\d+\b', 'tramo', f['titulo'])      # un rango de minutos («16-30») es una sola cifra
            self.assertLessEqual(len(re.findall(r'\d+(?:\.\d+)?', plain)), 3, f['titulo'])


@unittest.skipUnless(real_story('almada'), 'historia de Almada aún no generada')
class PublishedAlmadaTests(unittest.TestCase):
    def test_pachuca_is_official_and_the_america_chapter_is_early_evidence(self):
        doc = real_story('almada')
        wins = [{f['window'] for f in c['hallazgos']} for c in doc['capitulos']]
        self.assertEqual(wins, [{'oficial'}, {'temprano'}])
        self.assertTrue(doc['evidencia_temprana'])
        early = next(f for f in doc['capitulos'][1]['hallazgos'] if f['id'] == 'almada_america_temprano')
        self.assertIn('Confianza', early['interpretacion'])


if __name__ == '__main__':
    unittest.main()
