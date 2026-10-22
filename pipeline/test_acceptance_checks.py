"""Checks reales de aceptación AC-03…AC-15 sobre payloads (T-09)."""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import acceptance_checks as ck

OK, FAIL, PENDING = ck.OK, ck.FAIL, ck.PENDING


class AC03Test(unittest.TestCase):
    def test_complete_data_for_the_protagonist(self):
        model = {'entities': [{'id': 'ame_jardine', 'n': 91, 'official': True}, {'id': 'ame_jardine_epi', 'n': 38}, {'id': 'pac_almada', 'n': 139}]}
        def rows(ids):
            return [{'match_id': i} for i in ids]
        status, ev = ck.ac03(model, rows(range(91)), rows(range(1000, 1139)), lambda kind, mid: True)
        self.assertEqual(status, OK, ev)

    def test_missing_extracts_fail_and_lack_of_data_dir_is_pending(self):
        model = {'entities': [{'id': 'ame_jardine', 'n': 91, 'official': True}, {'id': 'ame_jardine_epi', 'n': 38}, {'id': 'pac_almada', 'n': 139}]}
        rows = [{'match_id': i} for i in range(91)]
        status, ev = ck.ac03(model, rows, rows, lambda kind, mid: not (kind == 'f360' and mid == 3))
        self.assertEqual(status, FAIL)
        self.assertIn('f360', ev)
        self.assertEqual(ck.ac03(model, rows, rows, None)[0], PENDING)

    def test_wrong_match_count_fails(self):
        model = {'entities': [{'id': 'ame_jardine', 'n': 70, 'official': True}, {'id': 'ame_jardine_epi', 'n': 38}]}
        self.assertEqual(ck.ac03(model, [], [], lambda k, m: True)[0], FAIL)


def story_doc():
    chapters = [{'id': f'c{i}', 'orden': i, 'hallazgos': [{'id': f'f{i}', 'window': 'oficial', 'evidencia': [{'window': 'oficial'}]}]}
                for i in range(1, 12)]
    chapters.append({'id': 'epilogo', 'orden': 12, 'hallazgos': [{'id': 'e1', 'window': 'epilogo', 'evidencia': [{'window': 'epilogo'}]}]})
    return {'capitulos': chapters, 'ventana': 'oficial', 'cobertura': {'construccion': ['f3'], 'xg': ['f1']}}


class AC06AndAC15Test(unittest.TestCase):
    def test_ac06_needs_twelve_chapters_with_findings_and_full_component_coverage(self):
        self.assertEqual(ck.ac06(story_doc())[0], OK)
        gap = story_doc()
        gap['cobertura']['presion'] = []
        self.assertEqual(ck.ac06(gap)[0], FAIL)
        short = story_doc()
        short['capitulos'][4]['hallazgos'] = []
        self.assertEqual(ck.ac06(short)[0], FAIL)
        self.assertEqual(ck.ac06(None)[0], PENDING)

    def test_ac15_official_window_only_in_conclusions(self):
        almada = {'capitulos': [{'hallazgos': [{'window': 'oficial'}]}, {'hallazgos': [{'window': 'temprano'}]}], 'evidencia_temprana': True}
        self.assertEqual(ck.ac15(story_doc(), almada)[0], OK)
        bad = story_doc()
        bad['capitulos'][2]['hallazgos'][0]['window'] = 'epilogo'
        self.assertEqual(ck.ac15(bad, almada)[0], FAIL)
        mixed = story_doc()
        mixed['capitulos'][2]['hallazgos'][0]['evidencia'].append({'window': 'epilogo'})
        self.assertEqual(ck.ac15(mixed, almada)[0], FAIL)
        no_flag = dict(almada, evidencia_temprana=False)
        self.assertEqual(ck.ac15(story_doc(), no_flag)[0], FAIL)
        self.assertEqual(ck.ac15(None, None)[0], PENDING)


def shape360():
    return {'kpi': {'value': 4.5, 'coverage': {'n_valid': 10}}, 'errores': {'tipos': [1], 'zonas': [1], 'jugadores': [1]},
            'bloque': {'por_zona': {}}, 'metricas': {'rompe_pct': {'value': 20.1}}, 'cambios': {'validos': 3}, 'corners': {'n': 4},
            'cordura': {'aprobado': True, 'n': 100}}


class AC07Test(unittest.TestCase):
    def test_all_360_blocks_present_with_sanity_approved(self):
        self.assertEqual(ck.ac07({'shape360': {'ventanas': {'oficial': shape360()}}})[0], OK)

    def test_missing_block_or_failed_sanity_fails(self):
        s = shape360()
        s['cordura']['aprobado'] = False
        self.assertEqual(ck.ac07({'shape360': {'ventanas': {'oficial': s}}})[0], FAIL)
        s = shape360()
        del s['bloque']
        self.assertEqual(ck.ac07({'shape360': {'ventanas': {'oficial': s}}})[0], FAIL)
        self.assertEqual(ck.ac07(None)[0], PENDING)


class AC08Test(unittest.TestCase):
    def analysis(self):
        return {'transitions': {'ventanas': {'oficial': {'perdidas': {
            'por_tipo': [{'tipo': t} for t in ('a', 'b', 'c', 'd', 'e')], 'por_zona': {'rows': [[0, 1]]}, 'por_jugador': [{'jugador': 'x'}]}}}}}

    def test_payload_and_story_finding_are_required_and_ui_makes_it_ok(self):
        story = {'capitulos': [{'hallazgos': [{'id': 'transiciones_tipologia'}]}]}
        self.assertEqual(ck.ac08(self.analysis(), story, ui=False)[0], PENDING)
        self.assertEqual(ck.ac08(self.analysis(), story, ui=True)[0], OK)
        self.assertEqual(ck.ac08(self.analysis(), {'capitulos': []}, ui=True)[0], FAIL)
        thin = self.analysis()
        thin['transitions']['ventanas']['oficial']['perdidas']['por_tipo'] = []
        self.assertEqual(ck.ac08(thin, story, ui=True)[0], FAIL)


def plays(n=10, oficial=True):
    out = [{'gol': i < 3, 'xg_posesion': 1.0 - i / 20, 'obv_max': 0.5, 'hecho': 'h', 'interpretacion': 'i', 'categoria': 'juego_abierto',
            'etiquetas': ['transicion']} for i in range(n)]
    return out


class AC09Test(unittest.TestCase):
    def analysis(self, **over):
        win = {'juego_abierto': plays(10), 'balon_parado': plays(10), 'penales': plays(5), 'resumen': {}}
        win.update(over)
        return {'dangerous': {'ventanas': {'oficial': win}},
                'defense': {'ventanas': {'oficial': {'concedido': {'x_media_tiros_concedidos': {'value': 17.5}}}}}}

    def test_top_ten_sorted_with_hecho_and_interpretacion(self):
        self.assertEqual(ck.ac09(self.analysis())[0], OK)

    def test_unsorted_or_missing_text_or_oversize_fails(self):
        shuffled = plays(10)
        shuffled[0], shuffled[9] = shuffled[9], shuffled[0]
        self.assertEqual(ck.ac09(self.analysis(juego_abierto=shuffled))[0], FAIL)
        no_text = plays(10)
        no_text[0].pop('hecho')
        self.assertEqual(ck.ac09(self.analysis(balon_parado=no_text))[0], FAIL)
        self.assertEqual(ck.ac09(self.analysis(juego_abierto=plays(11)))[0], FAIL)
        far = self.analysis()
        far['defense']['ventanas']['oficial']['concedido']['x_media_tiros_concedidos']['value'] = 30
        self.assertEqual(ck.ac09(far)[0], FAIL)
        self.assertEqual(ck.ac09(None)[0], PENDING)


def explorer_doc():
    item = {'label': 'X', 'identity': {'build': 'a'}, 'confidence': 'media', 'small_sample': False, 'metrics': {'xg': {'value': 1}}, 'n': 20,
            'prior': 'liga'}
    return {'equipos': [dict(item)], 'entrenadores': [dict(item, small_sample=True)]}


class AC12AndAC14Test(unittest.TestCase):
    def test_explorer_without_empty_cards(self):
        self.assertEqual(ck.ac12(explorer_doc())[0], OK)
        empty = explorer_doc()
        empty['equipos'][0]['metrics'] = {}
        self.assertEqual(ck.ac12(empty)[0], FAIL)
        no_conf = explorer_doc()
        del no_conf['entrenadores'][0]['confidence']
        self.assertEqual(ck.ac12(no_conf)[0], FAIL)
        self.assertEqual(ck.ac12(None)[0], PENDING)

    def test_replay_with_xg_and_the_not_a_forecast_label(self):
        analysis = {'replay': {'resumen': {'puntos': 10, 'xpts': 9.5}, 'por_ventana': {'oficial': {'metricas': [{'id': 'xpts'}]}}}}
        self.assertEqual(ck.ac14(analysis, 'Duelo de estilos en el modelo (no es un pronóstico)')[0], OK)
        self.assertEqual(ck.ac14(analysis, 'sin la leyenda')[0], FAIL)
        self.assertEqual(ck.ac14({'replay': {'resumen': {}}}, 'no es un pronóstico')[0], FAIL)
        self.assertEqual(ck.ac14(None, None)[0], PENDING)


class AC10Test(unittest.TestCase):
    TABLE = ('| Modelo | Tipos | Zonas |\n|---|---|---|\n| Parser de reglas (propio) | 100% | 100% |\n'
             '| mistralai/mistral-small-3.2-24b-instruct | 72% | 52% |\n| google/gemini-2.5-flash-lite | 68% | 48% |\n'
             '| openai/gpt-4.1-nano | 48% | 28% |\n')

    def test_three_non_anthropic_models_and_rules_at_ninety(self):
        self.assertEqual(ck.ac10(self.TABLE)[0], OK)
        self.assertEqual(ck.ac10(self.TABLE + '| anthropic/claude-x | 90% | 90% |\n')[0], OK)   # extra no cuenta, pero no estorba
        two = '\n'.join(self.TABLE.splitlines()[:-1]) + '\n'
        self.assertEqual(ck.ac10(two)[0], FAIL)
        weak = self.TABLE.replace('| 100% | 100% |', '| 80% | 70% |')
        self.assertEqual(ck.ac10(weak)[0], FAIL)
        self.assertEqual(ck.ac10(None)[0], PENDING)

    def test_anthropic_models_are_not_counted(self):
        only = '| Parser de reglas (propio) | 100% | 100% |\n| anthropic/a | 1% | 1% |\n| anthropic/b | 1% | 1% |\n| anthropic/c | 1% | 1% |\n'
        self.assertEqual(ck.ac10(only)[0], FAIL)


class ImmutabilityTest(unittest.TestCase):
    def test_checks_do_not_mutate_their_inputs(self):
        s = story_doc()
        before = copy.deepcopy(s)
        ck.ac06(s)
        ck.ac15(s, {'capitulos': [], 'evidencia_temprana': True})
        self.assertEqual(s, before)


if __name__ == '__main__':
    unittest.main()
