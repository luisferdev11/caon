"""Tests de la repetición con xG (pipeline/analytics/replay.py)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analytics import replay

HOME, AWAY = 1, 2


def shot(team, poss, xg, goal=False, minute=10, kind='Open Play', x=105.0, player='Ana', period=1):
    return {'id': f's{team}-{poss}-{minute}', 'type': {'name': 'Shot'}, 'team': {'id': team},
            'possession': poss, 'minute': minute, 'period': period, 'player': {'name': player},
            'location': [x, 40.0],
            'shot': {'statsbomb_xg': xg, 'type': {'name': kind},
                     'outcome': {'name': 'Goal' if goal else 'Saved'}}}


def touch(team, x, poss=1):
    return {'type': {'name': 'Pass'}, 'team': {'id': team}, 'possession': poss, 'period': 1,
            'minute': 1, 'location': [x, 40.0]}


META = {'match_id': 99, 'home_id': HOME, 'away_id': AWAY, 'home_score': 1, 'away_score': 0}


class PossessionProbTest(unittest.TestCase):
    def test_combines_shots_in_same_possession(self):
        evs = [shot(HOME, 3, 0.5), shot(HOME, 3, 0.5, minute=11), shot(HOME, 4, 0.2)]
        parts = replay.team_chances(evs, HOME)
        self.assertEqual(sorted(round(p, 4) for p in parts['open']), [0.2, 0.75])
        self.assertEqual(parts['pens'], [])

    def test_penalty_tagged_apart_and_shootout_excluded(self):
        evs = [shot(HOME, 3, 0.78, kind='Penalty'), shot(HOME, 9, 0.7, kind='Penalty', period=5)]
        parts = replay.team_chances(evs, HOME)
        self.assertEqual(parts['open'], [])
        self.assertEqual(parts['pens'], [0.78])

    def test_own_goal_fixed_for_beneficiary(self):
        evs = [{'type': {'name': 'Own Goal For'}, 'team': {'id': AWAY}, 'period': 1, 'minute': 30}]
        self.assertEqual(replay.team_chances(evs, AWAY)['own_goals'], 1)
        self.assertEqual(replay.team_chances(evs, HOME)['own_goals'], 0)


class SimulationTest(unittest.TestCase):
    def test_certain_outcomes(self):
        res = replay.simulate_result([1.0], [], 0, 0, draws=2000, seed=1)
        self.assertAlmostEqual(res['p_win'], 1.0)
        res = replay.simulate_result([], [], 0, 0, draws=2000, seed=1)
        self.assertAlmostEqual(res['p_draw'], 1.0)

    def test_seeded_and_sums_to_one(self):
        a = replay.simulate_result([0.3, 0.2], [0.4], 0, 1, draws=5000, seed=7)
        b = replay.simulate_result([0.3, 0.2], [0.4], 0, 1, draws=5000, seed=7)
        self.assertEqual(a, b)
        self.assertAlmostEqual(a['p_win'] + a['p_draw'] + a['p_loss'], 1.0, places=6)

    def test_symmetric_probabilities_close(self):
        res = replay.simulate_result([0.5], [0.5], 0, 0, draws=20000, seed=3)
        self.assertAlmostEqual(res['p_win'], 0.25, delta=0.02)
        self.assertAlmostEqual(res['p_draw'], 0.5, delta=0.02)


class MatchReplayTest(unittest.TestCase):
    def test_surprise_and_xpts(self):
        evs = [shot(HOME, 1, 0.05, goal=True), shot(AWAY, 2, 0.6), shot(AWAY, 3, 0.6)] + \
              [touch(HOME, 90)] + [touch(AWAY, 85) for _ in range(3)]
        rep = replay.match_replay(evs, META, HOME)
        self.assertEqual(rep['actual'], 'G')
        self.assertEqual(rep['points'], 3)
        self.assertTrue(rep['sorpresivo'])
        self.assertLess(rep['xpts'], 1.0)
        self.assertAlmostEqual(rep['dominio']['field_tilt'], 2 / 7, places=4)  # tiros también son acciones con balón
        self.assertAlmostEqual(rep['dominio']['xg_share'], 0.05 / 1.25, places=3)

    def test_away_perspective(self):
        evs = [shot(HOME, 1, 0.9, goal=True)]
        rep = replay.match_replay(evs, META, AWAY)
        self.assertEqual(rep['actual'], 'P')
        self.assertEqual(rep['points'], 0)
        self.assertFalse(rep['sorpresivo'])


class MatchCardTest(unittest.TestCase):
    def test_card_moments_timeline_facts(self):
        evs = [shot(HOME, 1, 0.05, goal=True, minute=12, player='Zendejas'),
               shot(AWAY, 2, 0.45, minute=40, player='Rival'), shot(AWAY, 3, 0.1, minute=80)]
        card = replay.match_card(evs, META, HOME)
        self.assertEqual(card['marcador'], {'propio': 1, 'rival': 0})
        kinds = [(m['minuto'], m['tipo']) for m in card['momentos']]
        self.assertEqual(kinds, [(12, 'gol'), (40, 'gran_ocasion')])
        self.assertEqual(card['xg_acumulado']['rival'][-1], 0.55)
        self.assertEqual(len(card['datos_curiosos']), 3)
        self.assertTrue(all(isinstance(f, str) and f for f in card['datos_curiosos']))


class BuildTest(unittest.TestCase):
    def test_build_aggregates(self):
        ctx = {'team_id': HOME, 'matches': [{'meta': META, 'events': [shot(HOME, 1, 0.9, goal=True)]}]}
        out = replay.build(ctx)
        self.assertEqual(out['resumen']['n'], 1)
        self.assertEqual(out['resumen']['puntos'], 3)
        self.assertEqual(len(out['partidos']), 1)
        self.assertIn('ficha', out['partidos'][0])


class EntityContextTest(unittest.TestCase):
    def test_build_from_registry_context(self):
        from analytics import EntityContext
        evs = [dict(shot(HOME, 1, 0.9, goal=True), team={'id': HOME, 'name': 'América'}),
               dict(shot(AWAY, 2, 0.1), team={'id': AWAY, 'name': 'Rival'}),
               {'type': {'name': 'Own Goal For'}, 'team': {'id': HOME, 'name': 'América'},
                'period': 2, 'minute': 70}]
        ctx = EntityContext(entity_id='x', label='x', team='América', coach='J',
                            matches=[{'id': 5, 'date': '2024-01-01', 'window': 'oficial'}],
                            load_events=lambda mid: evs)
        out = replay.build(ctx)
        row = out['partidos'][0]
        self.assertEqual(row['ficha']['marcador'], {'propio': 2, 'rival': 0})
        self.assertEqual(row['actual'], 'G')
        self.assertEqual(row['window'], 'oficial')
        self.assertEqual(out['resumen']['n'], 1)


class WindowAndTournamentTest(unittest.TestCase):
    def test_window_of(self):
        self.assertEqual(replay.window_of('2025-06-30'), 'oficial')
        self.assertEqual(replay.window_of('2025-07-01'), 'epilogo')
        self.assertEqual(replay.window_of('2026-06-30'), 'epilogo')
        self.assertEqual(replay.window_of('2026-07-01'), 'temprano')   # = build_analysis.match_window
        self.assertEqual(replay.window_of('2021-07-23'), 'oficial')
        self.assertIsNone(replay.window_of(None))

    def test_tournament_label(self):
        self.assertEqual(replay.tournament_of('2023-08-01'), 'Ap2023')
        self.assertEqual(replay.tournament_of('2024-05-20'), 'Cl2024')
        self.assertEqual(replay.tournament_of('2024-12-15'), 'Ap2024')
        self.assertIsNone(replay.tournament_of(None))


def ctx_match(mid, date, home_id, away_id, hs, as_, events):
    meta = {'match_id': mid, 'date': date, 'home_id': home_id, 'away_id': away_id,
            'home_name': 'América' if home_id == HOME else 'Rival',
            'away_name': 'América' if away_id == HOME else 'Rival', 'home_score': hs, 'away_score': as_}
    return {'meta': meta, 'events': events}


class BuildRowsTest(unittest.TestCase):
    def setUp(self):
        self.out = replay.build({'team_id': HOME, 'matches': [
            ctx_match(7, '2024-03-01', AWAY, HOME, 0, 1, [shot(HOME, 1, 0.9, goal=True)]),
            ctx_match(8, '2024-09-01', HOME, AWAY, 0, 0, [shot(AWAY, 1, 0.2)]),
            ctx_match(9, '2025-08-01', HOME, AWAY, 0, 1, [shot(AWAY, 1, 0.3, goal=True)])]})

    def test_rows_get_date_window_venue_from_meta(self):
        row = self.out['partidos'][0]
        self.assertEqual(row['fecha'], '2024-03-01')
        self.assertEqual(row['window'], 'oficial')
        self.assertEqual(row['torneo'], 'Cl2024')
        self.assertEqual(row['localia'], 'visita')
        self.assertEqual(row['rival'], 'Rival')
        self.assertEqual(self.out['partidos'][2]['window'], 'epilogo')

    def test_aggregates_by_tournament_and_window(self):
        tor = {t['torneo']: t for t in self.out['por_torneo']}
        self.assertEqual(sorted(tor), ['Ap2024', 'Ap2025', 'Cl2024'])
        self.assertEqual((tor['Cl2024']['n'], tor['Cl2024']['puntos']), (1, 3))
        self.assertEqual(tor['Ap2024']['window'], 'oficial')
        win = self.out['por_ventana']
        self.assertEqual((win['oficial']['n'], win['epilogo']['n']), (2, 1))
        self.assertEqual(self.out['resumen']['window'], 'mixta')
        self.assertEqual(self.out['resumen']['n'], 3)

    def test_card_has_verdict(self):
        card = self.out['partidos'][0]['ficha']
        self.assertEqual(card['merecio']['veredicto'], 'merecio_ganar')
        self.assertIn('de cada 100', card['merecio']['texto'])
        self.assertEqual(self.out['partidos'][0]['veredicto'], 'merecio_ganar')      # también en la fila
        self.assertEqual(self.out['textos']['veredicto']['merecio_ganar'], 'Mereció ganar')
        self.assertIn('acorde', self.out['textos']['balance'])


class VerdictTest(unittest.TestCase):
    def test_verdicts_and_balance(self):
        rep = {'p': {'G': 0.70, 'E': 0.2, 'P': 0.1}, 'points': 0, 'xpts': 2.3, 'actual': 'P'}
        v = replay.verdict(rep)
        self.assertEqual(v['veredicto'], 'merecio_ganar')
        self.assertEqual(v['balance'], 'por_debajo')
        self.assertIn('70 de cada 100', v['texto'])
        even = replay.verdict({'p': {'G': 0.35, 'E': 0.3, 'P': 0.35}, 'points': 1, 'xpts': 1.35, 'actual': 'E'})
        self.assertEqual((even['veredicto'], even['balance']), ('parejo', 'acorde'))
        lost = replay.verdict({'p': {'G': 0.1, 'E': 0.2, 'P': 0.7}, 'points': 3, 'xpts': 0.5, 'actual': 'G'})
        self.assertEqual((lost['veredicto'], lost['balance']), ('merecio_perder', 'por_encima'))


class EntityContextRowsTest(unittest.TestCase):
    def test_uses_row_score_venue_and_team_id(self):
        from analytics import EntityContext
        evs = [dict(shot(HOME, 1, 0.4, goal=True), team={'id': HOME, 'name': 'América'}),
               dict(shot(AWAY, 2, 0.1), team={'id': AWAY, 'name': 'Rival'})]
        row = {'id': 5, 'date': '2024-01-01', 'window': 'oficial', 'venue': 'visita',
               'opponent': 'Rival', 'score': [1, 0], 'team_id': HOME}
        ctx = EntityContext(entity_id='x', label='x', team='América', coach='J', matches=[row],
                            load_events=lambda mid: evs)
        out = replay.build(ctx)
        rep = out['partidos'][0]
        self.assertEqual(rep['localia'], 'visita')
        self.assertEqual(rep['rival'], 'Rival')
        self.assertEqual(rep['ficha']['marcador'], {'propio': 1, 'rival': 0})
        self.assertEqual(rep['torneo'], 'Cl2024')


def _two_window_ctx():
    return {'team_id': HOME, 'entity_id': 'ame_x', 'team': 'América', 'matches': iter([
        ctx_match(7, '2024-03-01', AWAY, HOME, 0, 1, [shot(HOME, 1, 0.9, goal=True), touch(HOME, 90)]),
        ctx_match(8, '2024-09-01', HOME, AWAY, 1, 0, [shot(HOME, 1, 0.05, goal=True), shot(AWAY, 2, 0.6),
                                                      shot(AWAY, 3, 0.6), touch(AWAY, 85)]),
        dict(ctx_match(9, '2026-08-01', HOME, AWAY, 0, 1, [shot(AWAY, 1, 0.3, goal=True)]), window='temprano')])}


class MetricRecordsTest(unittest.TestCase):
    """Registros del contrato (xpts, resultado_sorpresivo) por ventana, con entidad para la auditoría."""

    def setUp(self):
        self.out = replay.build(_two_window_ctx())   # matches como generador (así llega de build_analysis)

    def test_records_per_window_follow_contract(self):
        import framework as fw
        recs = {r['id']: r for r in self.out['por_ventana']['oficial']['metricas']}
        self.assertEqual(sorted(recs), ['resultado_sorpresivo', 'xpts'])
        for r in recs.values():
            self.assertEqual(fw.check_metric_record(r), [])
            self.assertEqual((r['entity'], r['window'], r['source'], r['n']), ('ame_x', 'oficial', 'eventos', 2))
        self.assertAlmostEqual(recs['xpts']['value'], self.out['por_ventana']['oficial']['xpts_por_partido'], 2)
        self.assertAlmostEqual(recs['resultado_sorpresivo']['value'], 0.5)
        self.assertEqual(recs['resultado_sorpresivo']['conteo'], 1)

    def test_row_window_overrides_date(self):
        self.assertEqual(self.out['partidos'][2]['window'], 'temprano')
        self.assertIn('temprano', self.out['por_ventana'])

    def test_rows_name_team_and_entity(self):
        row = self.out['partidos'][0]
        self.assertEqual((row['equipo'], row['entity']), ('América', 'ame_x'))

    def test_summary_dominance_means(self):
        dom = self.out['por_ventana']['oficial']['dominio']
        self.assertAlmostEqual(dom['xg_share'], (1.0 + 0.05 / 1.25) / 2, places=3)
        self.assertAlmostEqual(dom['field_tilt'], (1.0 + 1 / 4) / 2, places=3)

    def test_json_safe(self):
        import json
        json.dumps(self.out, ensure_ascii=False, allow_nan=False)


class CoverageTest(unittest.TestCase):
    def test_entity_context_counts_matches_without_events(self):
        from analytics import EntityContext
        evs = [dict(shot(HOME, 1, 0.4, goal=True), team={'id': HOME, 'name': 'América'}),
               dict(shot(AWAY, 2, 0.1), team={'id': AWAY, 'name': 'Rival'})]
        rows = [{'id': 5, 'date': '2024-01-01', 'window': 'oficial', 'venue': 'local', 'opponent': 'Rival',
                 'score': [1, 0], 'team_id': HOME},
                {'id': 6, 'date': '2024-01-08', 'window': 'oficial', 'venue': 'local', 'opponent': 'Rival',
                 'score': [0, 0], 'team_id': HOME}]
        ctx = EntityContext(entity_id='ame_x', label='x', team='América', coach='J', matches=rows,
                            load_events=lambda mid: evs if mid == 5 else None)
        out = replay.build(ctx)
        self.assertEqual(out['resumen']['cobertura'], {'partidos': 2, 'con_eventos': 1})
        self.assertEqual(out['partidos'][0]['entity'], 'ame_x')


class TimelineOrderTest(unittest.TestCase):
    """Descuento del primer tiempo (min 47) va antes del inicio del segundo (min 46)."""

    def setUp(self):
        self.evs = [shot(HOME, 1, 0.2, minute=47, period=1), shot(AWAY, 2, 0.4, goal=True, minute=46, period=2),
                    shot(HOME, 3, 0.1, minute=10, period=1)]

    def test_timeline_is_columnar_and_period_ordered(self):
        tl = replay.match_card(self.evs, META, HOME)['xg_acumulado']
        self.assertEqual(tl['periodo'], [1, 1, 1, 2])
        self.assertEqual(tl['minuto'], [0, 10, 47, 46])
        self.assertEqual(tl['propio'], [0.0, 0.1, 0.3, 0.3])
        self.assertEqual(tl['rival'], [0.0, 0.0, 0.0, 0.4])

    def test_moments_period_ordered(self):
        evs = self.evs + [shot(HOME, 4, 0.5, goal=True, minute=45, period=1)]
        moms = replay.match_card(evs, META, HOME)['momentos']
        self.assertEqual([(m['periodo'], m['minuto']) for m in moms], [(1, 45), (2, 46)])
        self.assertNotIn('penal', moms[0])                                  # solo se marca cuando es penal


class SplitCardsTest(unittest.TestCase):
    def test_split_moves_cards_out_of_rows(self):
        out = replay.build({'team_id': HOME, 'matches': [
            ctx_match(7, '2024-03-01', AWAY, HOME, 0, 1, [shot(HOME, 1, 0.9, goal=True)])]})
        self.assertEqual(out['resumen']['sorteos'], replay.REPLAY_DRAWS)
        self.assertNotIn('sorteos', out['partidos'][0])
        light, cards = replay.split_cards(out)
        self.assertNotIn('ficha', light['partidos'][0])
        self.assertIn('ficha', out['partidos'][0])                         # no muta la entrada
        self.assertEqual(list(cards), [7])
        self.assertEqual(cards[7]['ficha']['marcador'], {'propio': 1, 'rival': 0})
        self.assertEqual(cards[7]['textos'], out['textos'])
        self.assertEqual(light['partidos'][0]['veredicto'], 'merecio_ganar')
        self.assertEqual(light['partidos'][0]['marcador'], {'propio': 1, 'rival': 0})   # la lista de partidos lo muestra


class ThresholdsTest(unittest.TestCase):
    def test_no_local_copies_of_framework_constants(self):
        import audit_coherence as ac
        here = pathlib.Path(__file__).resolve().parent / 'analytics'
        self.assertEqual(ac.threshold_warnings([here / 'replay.py', here / 'match_xg.py']), [])


if __name__ == '__main__':
    unittest.main()
