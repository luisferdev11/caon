"""Tests de analytics.shape360_errors: tipología del error 360 unida a las pérdidas de an_ (sintético)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from analytics import shape360_errors as se
from framework import zone


def loss(eid, tipo, x=30.0, y=40.0, player=7, valid=True, iso=False, shot=False, goal=False, team=1):
    return {'team': team, 'eid': eid, 'player': player, 'x': x, 'y': y, 'tipo': tipo, 'err_linked': True,
            'err_valid': valid, 'isolated': iso, 'shot15': shot, 'goal15': goal}


AN = {'possessions': [
    {'id': 3, 'team': 1, 'loss': {'kind': 'lossO', 'event_id': 'a', 'costly': True, 'lethal': True}},
    {'id': 4, 'team': 1, 'loss': {'kind': 'lossO', 'event_id': 'zz', 'costly': False, 'lethal': False}},
    {'id': 5, 'team': 2, 'loss': {'kind': 'lossO', 'event_id': 'q', 'costly': True, 'lethal': False}},
    {'id': 6, 'team': 1, 'loss': {'kind': 'lossXT', 'event_id': 'd', 'costly': False, 'lethal': False}},
    {'id': 7, 'team': 1, 'loss': None}]}


class TestFinalType(unittest.TestCase):
    def test_isolated_replaces_other_only(self):
        self.assertEqual(se.final_type(loss('a', 'otro', iso=True)), 'aislado')
        self.assertEqual(se.final_type(loss('a', 'bajo_presion', iso=True)), 'bajo_presion')
        self.assertEqual(se.final_type(loss('a', 'otro')), 'otro')
        self.assertEqual(se.final_type(loss('a', None)), 'otro')

    def test_every_type_has_spanish_name(self):
        for t in se.ERROR_TYPES:
            self.assertTrue(se.ERROR_NAMES[t])


class TestJoin(unittest.TestCase):
    def test_index_only_open_play_losses(self):
        idx = se.an_loss_index(AN)
        self.assertEqual(set(idx), {(1, 3), (1, 4), (2, 5)})
        self.assertEqual(se.an_loss_index(None), {})

    def test_join_by_possession_of_error_event(self):
        rows = [loss('a', 'otro'), loss('b', 'otro', shot=True, goal=True), loss('c', 'otro', shot=True)]
        out = se.join_an(rows, {'a': 3, 'b': 4}, se.an_loss_index(AN))
        self.assertEqual([(r['costly'], r['lethal'], r['joined']) for r in out],
                         [(True, True, True), (False, False, True), (True, False, False)])
        self.assertNotIn('costly', rows[0])


class TestTaxonomy(unittest.TestCase):
    def setUp(self):
        rows = [dict(loss('a', 'bajo_presion', x=10, y=40, player=7), costly=True, lethal=True, joined=True),
                dict(loss('b', 'bajo_presion', x=10, y=40, player=7), costly=False, lethal=False, joined=True),
                dict(loss('c', 'no_forzado', x=70, y=10, player=8), costly=False, lethal=False, joined=False),
                dict(loss('d', 'otro', x=70, y=10, player=8, iso=True), costly=True, lethal=False, joined=True),
                dict(loss('e', 'otro', valid=False), costly=True, lethal=False, joined=True)]
        opp = [dict(loss('r', 'duelo_perdido', team=2), costly=True, lethal=False, joined=True)]
        self.out = se.taxonomy(rows, opp, {7: 'Siete'}, 'oficial')

    def test_types_with_costly_rate_valid_only(self):
        t = {r['tipo']: r for r in self.out['tipos']}
        self.assertEqual(t['bajo_presion']['n'], 2)
        self.assertEqual(t['bajo_presion']['pct_costosa'], 50.0)
        self.assertEqual(t['bajo_presion']['letales'], 1)
        self.assertEqual(t['bajo_presion']['pct'], 50.0)
        self.assertEqual(t['aislado']['n'], 1)
        self.assertEqual(t['bajo_presion']['nombre'], se.ERROR_NAMES['bajo_presion'])
        self.assertEqual([r['tipo'] for r in self.out['tipos']],
                         [x for x in se.ERROR_TYPES if x in t])

    def test_coverage(self):
        self.assertEqual(self.out['cobertura'], {'n_perdidas': 5, 'n_linked': 5, 'n_valid': 4, 'n_unidas_an': 3})

    def test_by_zone_and_third(self):
        z = self.out['zonas'][str(zone([10, 40]))]
        self.assertEqual((z['n'], z['costosas'], z['tipo_principal']), (2, 1, 'bajo_presion'))
        self.assertEqual(self.out['tercios']['propio']['n'], 2)
        self.assertEqual(self.out['tercios']['medio']['n'], 2)

    def test_players_named_and_sorted(self):
        p = self.out['jugadores']
        self.assertEqual(p[0]['nombre'], 'Siete')
        self.assertEqual(p[0]['n'], 2)
        self.assertIsNone(p[1]['nombre'])

    def test_rival_reference(self):
        self.assertEqual(self.out['ref_rivales']['duelo_perdido'], {'pct': 100.0, 'pct_costosa': 100.0, 'n': 1})

    def test_empty(self):
        out = se.taxonomy([], [], {}, 'oficial')
        self.assertEqual(out['tipos'], [])
        self.assertIn('motivo', out)


if __name__ == '__main__':
    unittest.main()
