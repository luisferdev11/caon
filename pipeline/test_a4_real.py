"""Integración A4 sobre datos reales (América·Jardine, ventana oficial): cordura de marcos, xG, OBV y PPDA.

Se salta si no hay datos en caché. Usa los primeros SAMPLE partidos para que la suite siga siendo rápida.
"""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import analytics
import framework
from analytics import a4_reference, dangerous, defense, offense, transitions
from fixtures import a4_match as fx

ROOT = pathlib.Path(__file__).resolve().parents[1]
SAMPLE = 25
ENTITY = 'ame_jardine'
_CTX = {}


def _context():
    if 'ctx' in _CTX:
        return _CTX['ctx']
    import build_analysis as ba
    from build_model import display
    from entities import build_entities
    ents, ms = build_entities()
    ent = ba.index_by_model_id(ents, display).get(ENTITY)
    rows = ba.context_matches(ent['matches'], {m['match_id']: m for m in ms}) if ent else []
    rows = [r for r in rows if r['window'] == 'oficial' and (ROOT / 'data' / 'extract' / f"an_{r['id']}.json").exists()]
    ctx = analytics.EntityContext(entity_id=ENTITY, label=ENTITY, team='América', coach='', matches=rows[:SAMPLE],
                                  league_ref={'a4_unidades': a4_reference.load_units(build=False)})
    _CTX['ctx'] = ctx
    return ctx


def _has_data():
    try:
        return len(_context().matches) >= SAMPLE
    except Exception:  # noqa: BLE001 - sin caché o sin calendario: se salta
        return False


@unittest.skipUnless(_has_data(), 'sin datos reales en caché')
class TestA4Real(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ctx = _context()
        cls.ctx = ctx
        cls.off = offense.build(ctx)['ventanas']['oficial']
        cls.dfn = defense.build(ctx)['ventanas']['oficial']
        cls.tr = transitions.build(ctx)['ventanas']['oficial']
        cls.dang = dangerous.build(ctx)

    def test_own_shots_attack_right(self):
        rows = self.off['ocasiones']['mapa_tiros']['rows']
        self.assertGreater(sum(r[0] for r in rows) / len(rows), 95)

    def test_conceded_shots_defend_left(self):
        rows = self.dfn['concedido']['mapa_tiros']['rows']
        self.assertLess(sum(r[0] for r in rows) / len(rows), 25)
        self.assertLess(self.dfn['concedido']['x_media_tiros_concedidos']['value'], 25)
        win = self.dang['ventanas']['oficial']
        shots = [s for p in win['juego_abierto'] + win['balon_parado'] for s in p['tiros']]
        self.assertLess(sum(s['x'] for s in shots) / len(shots), 25)

    def test_possession_xg_equals_events_np_xg(self):
        """Σ xG sin penal de las posesiones an_ = Σ statsbomb_xg de los eventos; los tiros propios dentro de
        una posesión rival (sequences los omite) se cuentan aparte y deben ser < 1 % del xG."""
        lost = total = 0.0
        for row in self.ctx.matches:
            an, ev = self.ctx.load_an(row['id']), self.ctx.load_events(row['id'])
            mine = sum(s['xg'] for p in an['possessions'] if p['team'] == row['team_id'] and p['period'] < 5
                       for s in p['shots'] if not s['penalty'])
            shots = [e for e in ev if e['type']['name'] == 'Shot' and e['team']['id'] == row['team_id']
                     and e['period'] < 5 and e['shot']['type']['name'] != 'Penalty']
            inside = sum(e['shot'].get('statsbomb_xg') or 0 for e in shots
                         if e['possession_team']['id'] == row['team_id'])
            self.assertAlmostEqual(mine, inside, places=6)
            lost += sum(e['shot'].get('statsbomb_xg') or 0 for e in shots
                        if e['possession_team']['id'] != row['team_id'])
            total += mine
        self.assertLess(lost / total, 0.01)

    def test_xg_tracks_team_stats(self):
        v = self.off['obv']['validacion']['xg_np']
        self.assertGreaterEqual(v['n'], SAMPLE - 2)
        self.assertGreater(v['r'], 0.95)  # versiones de xG distintas entre endpoints: no se exige ±0.01

    def test_obv_matches_team_stats(self):
        v = self.off['obv']['validacion']
        self.assertGreater(v['obv_total']['r'], 0.9)
        self.assertGreater(v['obv_pase']['r'], 0.9)
        self.assertGreater(v['obv_conduccion']['r'], 0.9)

    def test_ppda_tracks_team_stats(self):
        self.assertGreater(self.dfn['presion']['validacion_ppda']['r'], 0.9)

    def test_dangerous_contract(self):
        raw = json.dumps(self.dang, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.assertLessEqual(len(raw), dangerous.PAYLOAD_MAX_BYTES)
        win = self.dang['ventanas']['oficial']
        for cat in dangerous.CATEGORIES:
            self.assertLessEqual(len(win[cat]), dangerous.TOP_N)
            for p in win[cat]:
                self.assertLessEqual(len(p['acciones'] or []), dangerous.MAX_ACTIONS)
                self.assertTrue(p['hecho'] and p['interpretacion'])
        ranked = win['juego_abierto']
        self.assertEqual(ranked, dangerous.rank(ranked))

    def test_no_rival_player_names_in_dangerous(self):
        blob = json.dumps(self.dang, ensure_ascii=False)
        mids = {p['match_id'] for cat in dangerous.CATEGORIES for p in self.dang['ventanas']['oficial'][cat]}
        team_of = {r['id']: r['team_id'] for r in self.ctx.matches}
        names = {e['player']['name'] for mid in mids for e in self.ctx.load_events(mid) or []
                 if e.get('player') and e['team']['id'] != team_of[mid]}
        self.assertTrue(names)
        self.assertEqual([n for n in names if n in blob], [])

    def test_records_contract_and_reference(self):
        for payload in (self.off, self.dfn, self.tr):
            recs = fx.records(payload)
            for r in recs:
                self.assertEqual(framework.check_metric_record(r), [], r)
            keys = [(r['id'], r['window'], r.get('scope')) for r in recs]
            self.assertEqual(len(keys), len(set(keys)))
        if a4_reference.load_units(build=False):
            self.assertIsNotNone(self.off['dominio']['field_tilt'].get('ref_pct'))

    def test_losses_plausible(self):
        p = self.tr['perdidas']
        self.assertTrue(30 <= p['por_partido']['value'] <= 80)
        self.assertTrue(0 < p['tasa_costosa']['value'] < 20)
        thirds = {r['tercio']: r['tasa_costosa']['value'] for r in p['por_tercio']}
        self.assertGreater(thirds['propio'], thirds['final'])  # perder cerca de la propia portería cuesta más



if __name__ == '__main__':
    unittest.main()
