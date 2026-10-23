"""Tests de analytics.setpieces (balón parado ofensivo y defensivo)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'fixtures'))

from a5_events import THEM, US, an_match, f360_corner, match_events
from analytics import setpieces


class _Ctx:
    """Contexto mínimo del contrato analytics con cargadores sobre fixtures."""

    def __init__(self, rows, f360=None, an=True):
        self.entity_id = 'test'
        self.matches = rows
        self._f360 = f360
        self._an = an

    def load_events(self, mid):
        return match_events()

    def load_an(self, mid):
        return an_match(mid) if self._an else None

    def load_f360(self, mid):
        return self._f360

    def load_lineups(self, mid):
        return [{'team_id': US, 'lineup': [{'player_id': 109, 'player_name': 'Jugador 109',
                                            'player_nickname': 'Cobrador'}]}]


class ZonesTest(unittest.TestCase):
    def test_shot_zone(self):
        self.assertEqual(setpieces.shot_zone([115, 40]), 'area_chica')
        self.assertEqual(setpieces.shot_zone([105, 45]), 'zona_remate')
        self.assertEqual(setpieces.shot_zone([105, 20]), 'resto_area')
        self.assertEqual(setpieces.shot_zone([95, 40]), 'fuera_area')
        self.assertEqual(setpieces.shot_zone(None), 'sin_dato')

    def test_landing_zone_normalizes_corner_side(self):
        # cobrado desde y≈0: y<36 es primer palo; desde y≈80 se espeja
        self.assertEqual(setpieces.landing_zone([116, 33], 0.1), 'primer_palo')
        self.assertEqual(setpieces.landing_zone([116, 47], 79.9), 'primer_palo')
        self.assertEqual(setpieces.landing_zone([116, 40], 0.1), 'centro_area_chica')
        self.assertEqual(setpieces.landing_zone([108, 40], 0.1), 'punto_penal')
        self.assertEqual(setpieces.landing_zone([90, 40], 0.1), 'fuera_area')


class MatchRecordsTest(unittest.TestCase):
    def setUp(self):
        self.rec = setpieces.match_records(match_events(), US)

    def test_own_corners(self):
        corners = self.rec['own']['corners']
        self.assertEqual(len(corners), 2)
        first, short = corners
        self.assertEqual(first['zona'], 'centro_area_chica')
        self.assertEqual(first['tecnica'], 'Cerrado')
        self.assertEqual(first['contacto'], {'equipo': 'atacante', 'zona': 'centro_area_chica'})
        self.assertEqual(first['remates'][0]['zona'], 'area_chica')
        self.assertTrue(first['remates'][0]['cabeza'])
        self.assertTrue(short['corto'])
        self.assertEqual(short['zona'], 'corto')

    def test_short_and_out_corners_have_no_first_contact(self):
        self.assertIsNone(self.rec['own']['corners'][1]['contacto'])
        corner = {'team': {'id': US}, 'location': [120, 0.1], 'type': {'name': 'Pass'},
                  'pass': {'length': 40, 'outcome': {'name': 'Out'}, 'end_location': [118, 50]}}
        goal_kick = {'team': {'id': THEM}, 'type': {'name': 'Pass'}, 'location': [6, 40],
                     'pass': {'type': {'name': 'Goal Kick'}}}
        self.assertIsNone(setpieces.first_contact([goal_kick], US, corner))
        corner['pass'] = {'length': 40, 'outcome': {'name': 'Incomplete'}, 'end_location': [110, 40]}
        failed = {'team': {'id': US}, 'type': {'name': 'Ball Receipt*'}, 'location': [110, 40],
                  'ball_receipt': {'outcome': {'name': 'Incomplete'}}}
        clear = {'team': {'id': THEM}, 'type': {'name': 'Clearance'}, 'location': [10, 40]}
        self.assertEqual(setpieces.first_contact([failed, clear], US, corner),
                         {'equipo': 'defensor', 'zona': 'punto_penal'})

    def test_rival_corner_first_contact_is_ours_flipped(self):
        corner = self.rec['opp']['corners'][0]
        self.assertEqual(corner['contacto']['equipo'], 'defensor')
        self.assertEqual(corner['contacto']['zona'], 'centro_area_chica')

    def test_fk_throw_and_shots(self):
        self.assertEqual(len(self.rec['own']['throws']), 1)
        fk = self.rec['opp']['fks'][0]
        self.assertTrue(fk['directo'])
        self.assertAlmostEqual(fk['remates'][0]['xg'], 0.06)
        kinds = [s['tipo'] for s in self.rec['opp']['sp_shots']]
        self.assertEqual(kinds, ['fk'])

    def test_penalty_excluded(self):
        evs = match_events(penalty=True)
        rec = setpieces.match_records(evs, US)
        self.assertTrue(all(s['xg'] != 0.76 for s in rec['own']['sp_shots']))


class WindowPayloadTest(unittest.TestCase):
    def setUp(self):
        items = [{'events': match_events(), 'an': an_match(1), 'team_id': US, 'names': {109: 'Cobrador'}}]
        self.out = setpieces.window_payload(items, 'oficial', seed=1)

    def test_offensive_corners(self):
        c = self.out['ofensivo']['corners']
        self.assertEqual(c['n'], 2)
        self.assertAlmostEqual(c['corto_pct'], 50.0)
        self.assertEqual(c['cobradores'][0], {'nombre': 'Cobrador', 'n': 2})
        self.assertEqual(c['remates']['n'], 1)
        self.assertAlmostEqual(c['remates']['xg'], 0.3)
        self.assertEqual(c['remates']['goles'], 1)
        self.assertAlmostEqual(c['primer_contacto']['ganado_pct'], 100.0)
        zonas = {z['zona']: z['n'] for z in c['entrega']}
        self.assertEqual(zonas, {'centro_area_chica': 1, 'corto': 1})

    def test_defensive_side(self):
        d = self.out['defensivo']
        self.assertEqual(d['corners']['n'], 1)
        self.assertAlmostEqual(d['corners']['primer_contacto']['ganado_pct'], 0.0)
        self.assertEqual(d['tiros_libres']['directos']['n'], 1)
        self.assertEqual(d['zonas_vulnerables'][0]['zona'], 'fuera_area')
        self.assertAlmostEqual(d['zonas_vulnerables'][0]['xg'], 0.06)

    def test_differential_metric_records(self):
        diff = self.out['diferencial']
        self.assertEqual(diff['id'], 'bp_diferencial')
        self.assertEqual(diff['window'], 'oficial')
        self.assertAlmostEqual(diff['value'], 0.1)
        self.assertEqual(diff['n'], 1)
        self.assertEqual(self.out['ofensivo']['xg_bp']['id'], 'bp_ofensivo')
        self.assertAlmostEqual(self.out['ofensivo']['xg_bp']['value'], 0.2)
        self.assertAlmostEqual(self.out['defensivo']['xg_bp']['value'], 0.1)
        por_tipo = self.out['ofensivo']['por_tipo']
        self.assertEqual(por_tipo['corner']['n'], 1)
        self.assertAlmostEqual(por_tipo['corner']['xg_por_jugada'], 0.2)

    def test_differential_publishes_the_per_match_series(self):
        diff = self.out['diferencial']
        self.assertEqual([m for m, _ in diff["por_partido"]], [1])
        self.assertAlmostEqual(diff['por_partido'][0][1], diff['value'], places=4)

    def test_missing_an_gives_null_with_reason(self):
        items = [{'events': match_events(), 'an': None, 'team_id': US, 'names': {}}]
        out = setpieces.window_payload(items, 'oficial', seed=1)
        self.assertIsNone(out['diferencial']['value'])
        self.assertTrue(out['diferencial']['motivo'])
        self.assertEqual(out['ofensivo']['corners']['n'], 2)


class BuildTest(unittest.TestCase):
    def test_build_by_window_and_360(self):
        rows = [{'id': 1, 'team_id': US, 'window': 'oficial'}, {'id': 2, 'team_id': US, 'window': 'epilogo'}]
        f360 = f360_corner([(US, 9, 4, 0.6, 'mixto', True), (THEM, 7, 2, 0.2, 'zonal', True)])
        out = setpieces.build(_Ctx(rows, f360=f360))
        self.assertEqual(set(out['ventanas']), {'oficial', 'epilogo'})
        org = out['ventanas']['oficial']['defensivo']['organizacion_360']
        self.assertEqual(org['id'], 'corner_def')
        self.assertEqual(org['n'], 1)
        self.assertEqual(org['marcaje'], {'mixto': 1})
        self.assertAlmostEqual(org['defensores_area'], 9.0)
        self.assertAlmostEqual(org['emparejamiento_pct'], 60.0)
        self.assertEqual(org['source'], '360')
        self.assertEqual(out['ventanas']['oficial']['ofensivo']['corners']['cobradores'][0]['nombre'], 'Cobrador')

    def test_build_has_spanish_labels_for_codes(self):
        out = setpieces.build(_Ctx([{'id': 1, 'team_id': US, 'window': 'oficial'}]))
        labels = out['etiquetas']
        for code in setpieces.CORNER_ZONES + ('area_chica', 'zona_remate', 'resto_area', 'fuera_area', 'sin_dato'):
            self.assertIn(code, labels)
        self.assertEqual(labels['primer_palo'], 'Primer palo')

    def test_build_without_360(self):
        out = setpieces.build(_Ctx([{'id': 1, 'team_id': US, 'window': 'oficial'}]))
        org = out['ventanas']['oficial']['defensivo']['organizacion_360']
        self.assertIsNone(org['value'])
        self.assertTrue(org['motivo'])


if __name__ == '__main__':
    unittest.main()
