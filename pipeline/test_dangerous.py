"""Tests de analytics.dangerous (jugadas peligrosas concedidas) sobre el partido sintético A4."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import analytics
import framework
from analytics import dangerous
from fixtures import a4_match as fx

RIVAL_NAMES = ('Rival Uno', 'Rival Dos', 'Rival Portero')


def _passes(n):
    ev = [{'id': f'p{i}', 'index': i, 'period': 1, 'possession': 3, 'minute': 5, 'second': i,
           'type': {'name': 'Pass'}, 'team': {'id': fx.THEM}, 'player': {'name': 'Rival Uno'},
           'location': [40 + i, 40], 'pass': {'end_location': [41 + i, 40]}} for i in range(n)]
    ev.append({'id': 's3', 'index': n, 'period': 1, 'possession': 3, 'minute': 5, 'second': 59,
               'type': {'name': 'Shot'}, 'team': {'id': fx.THEM}, 'player': {'name': 'Rival Dos'},
               'location': [112, 41], 'shot': {'end_location': [120, 40]}})
    return ev


class TestDangerous(unittest.TestCase):
    def setUp(self):
        self.out = dangerous.build(fx.context())
        self.win = self.out['ventanas']['oficial']

    def test_registered(self):
        self.assertIn('dangerous', analytics.topics())

    def test_lists_and_order_goal_then_xg(self):
        self.assertEqual([p['posesion'] for p in self.win['juego_abierto']], [8, 2])
        self.assertEqual([p['posesion'] for p in self.win['balon_parado']], [15])
        self.assertEqual([p['posesion'] for p in self.win['penales']], [16])
        self.assertTrue(self.win['juego_abierto'][0]['gol'])

    def test_possession_xg_and_obv(self):
        p = self.win['juego_abierto'][0]
        self.assertAlmostEqual(p['xg_posesion'], 0.45)
        self.assertAlmostEqual(p['obv_max'], 0.30)
        self.assertAlmostEqual(self.win['penales'][0]['xg_posesion'], 0.76)

    def test_tags_and_link_to_costly_loss(self):
        goal, other = self.win['juego_abierto']
        self.assertEqual(goal['etiquetas'], ['transicion', 'tras_perdida_costosa'])
        self.assertEqual(goal['perdida_previa']['event_id'], 'e21')
        self.assertEqual(goal['perdida_previa']['jugador'], 'Defensa')
        self.assertEqual(goal['perdida_previa']['tipo'], 'duelo_perdido')
        self.assertIn('tras_perdida_costosa', other['etiquetas'])
        self.assertEqual(self.win['balon_parado'][0]['etiquetas'], ['balon_parado'])
        self.assertEqual(self.win['penales'][0]['etiquetas'], ['penal'])

    def test_protagonist_defends_left(self):
        shots = [s for cat in ('juego_abierto', 'balon_parado') for p in self.win[cat] for s in p['tiros']]
        self.assertLess(sum(s['x'] for s in shots) / len(shots), 25)
        acts = self.win['juego_abierto'][0]['acciones']
        self.assertEqual([a['accion'] for a in acts], ['Recuperación', 'Pase', 'Tiro'])
        self.assertEqual((acts[-1]['x'], acts[-1]['y']), (12.0, 40.0))
        self.assertEqual(acts[-1]['equipo'], 'rival')

    def test_photo_flipped_without_names(self):
        foto = self.win['juego_abierto'][0]['foto']
        self.assertEqual(len(foto), 2)
        keeper = next(f for f in foto if f['portero'])
        self.assertEqual((keeper['x'], keeper['equipo']), (4.0, 'propio'))
        blob = json.dumps(self.out, ensure_ascii=False)
        for name in RIVAL_NAMES:
            self.assertNotIn(name, blob)

    def test_fact_and_interpretation_texts(self):
        p = self.win['juego_abierto'][0]
        self.assertIn('gol', p['hecho'])
        self.assertIn('0.45', p['hecho'])
        self.assertIn('pérdida', p['interpretacion'])
        self.assertIn('Penal', self.win['penales'][0]['interpretacion'])

    def test_summary_records_and_size(self):
        r = self.win['resumen']
        self.assertAlmostEqual(r['jugadas_por_partido']['value'], 4.0)
        self.assertAlmostEqual(r['xg_por_tipo']['penales']['value'], 0.76)
        self.assertEqual(r['goles_tras_perdida']['value'], 1)
        recs = fx.records(self.out)
        for rec in recs:
            self.assertEqual(framework.check_metric_record(rec), [], rec)
        keys = [(x['id'], x['window'], x.get('scope')) for x in recs]
        self.assertEqual(len(keys), len(set(keys)))
        raw = json.dumps(self.out, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.assertLess(len(raw), dangerous.PAYLOAD_MAX_BYTES)

    def test_own_actions_carry_nickname(self):
        acts = self.win['juego_abierto'][1]['acciones']
        own = [a for a in acts if a['equipo'] == 'propio']
        self.assertEqual([(a['accion'], a['jugador']) for a in own], [('Presión', 'Medio')])
        self.assertIn('en 7 s', self.win['juego_abierto'][1]['interpretacion'])

    def test_immediate_shot_wording(self):
        from analytics import dangerous_detail as dd
        txt = dd.interpretation_text({'etiquetas': ['transicion', 'tras_perdida_costosa'], 'duracion_s': 0})
        self.assertIn('de inmediato', txt)

    def test_actions_capped_end_at_last_shot(self):
        acts = dangerous.possession_actions(_passes(20), 1, 3, fx.US)
        self.assertEqual(len(acts), dangerous.MAX_ACTIONS)
        self.assertEqual(acts[-1]['accion'], 'Tiro')
        self.assertNotIn('jugador', acts[0])

    def test_rank_tiebreak_obv_then_date(self):
        plays = [{'gol': False, 'xg_posesion': 0.2, 'obv_max': 0.1, 'fecha': '2024-02-01', 'k': 'a'},
                 {'gol': False, 'xg_posesion': 0.2, 'obv_max': 0.3, 'fecha': '2024-03-01', 'k': 'b'},
                 {'gol': False, 'xg_posesion': 0.2, 'obv_max': 0.1, 'fecha': '2024-01-01', 'k': 'c'},
                 {'gol': True, 'xg_posesion': 0.01, 'obv_max': 0.0, 'fecha': '2024-05-01', 'k': 'd'}]
        self.assertEqual([p['k'] for p in dangerous.rank(plays)], ['d', 'b', 'c', 'a'])

    def test_budget_trims_photos_first(self):
        big = {'ventanas': {'oficial': {c: [{'foto': ['x' * 1000], 'acciones': ['y']}] for c in dangerous.CATEGORIES}}}
        out = dangerous.fit_budget(big, limit=2000)
        self.assertIsNone(out['ventanas']['oficial']['juego_abierto'][0]['foto'])
        self.assertEqual(out['ventanas']['oficial']['juego_abierto'][0]['acciones'], ['y'])
        self.assertTrue(out['recortes'])


if __name__ == '__main__':
    unittest.main()
