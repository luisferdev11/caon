"""Integración sobre datos reales (A5): balón parado, contexto y uso de plantilla de ame_jardine.

Se omite si faltan los datos en caché. Invariantes: contrato de métricas, sin NaN, córners = team-stats,
minutos ≤ 100 %, ventana oficial con 91 partidos y tamaño de payload acotado.
"""
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CACHE = HERE.parent / 'data' / 'cache'
EXTRACT = HERE.parent / 'data' / 'extract'
ENTITY = 'ame_jardine'
PAYLOAD_MAX_BYTES = 60_000      # por tema; el presupuesto total por entidad es 400 KB


def _records(obj):
    if isinstance(obj, dict):
        if {'id', 'value', 'window'} <= set(obj):
            yield obj
        for v in obj.values():
            yield from _records(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _records(v)


def _context():
    import analytics
    from build_analysis import context_matches, index_by_model_id
    from build_model import display
    from entities import build_entities
    ents, ms = build_entities()
    e = index_by_model_id(ents, display)[ENTITY]
    rows = context_matches(e['matches'], {m['match_id']: m for m in ms})
    return analytics.EntityContext(entity_id=ENTITY, label=ENTITY, team=e['team'], coach='', matches=rows)


@unittest.skipUnless((CACHE / 'v6_competitions_73_seasons_317_matches.json').exists()
                     and any(EXTRACT.glob('an_*.json')), 'sin datos reales en caché')
class RealDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import framework
        from analytics import context, setpieces, usage
        cls.fw = framework
        cls.ctx = _context()
        cls.out = {'setpieces': setpieces.build(cls.ctx), 'context': context.build(cls.ctx),
                   'usage': usage.build(cls.ctx)}

    def test_contract_and_json(self):
        for topic, payload in self.out.items():
            text = json.dumps(payload, ensure_ascii=False, allow_nan=False)
            self.assertLess(len(text.encode('utf-8')), PAYLOAD_MAX_BYTES, topic)
            for rec in _records(payload):
                self.assertEqual(self.fw.check_metric_record(rec), [], (topic, rec.get('id')))
            self.assertNotIn('unknown', text.lower(), topic)

    def test_official_window_only(self):
        for payload in self.out.values():
            self.assertEqual(list(payload['ventanas']), ['oficial'])
        self.assertEqual(self.out['context']['ventanas']['oficial']['n_partidos'], 91)

    def test_corners_match_team_stats(self):
        total = 0
        for r in self.ctx.matches:
            ts = json.loads((CACHE / f"v1_matches_{r['id']}_team-stats.json").read_text(encoding='utf-8'))
            total += next(t for t in ts if t['team_id'] == r['team_id'])['team_match_corners']
        own = self.out['setpieces']['ventanas']['oficial']['ofensivo']['corners']['n']
        self.assertEqual(own, total)

    def test_usage_invariants(self):
        w = self.out['usage']['ventanas']['oficial']
        self.assertEqual(len(w['xi_base']), 11)
        self.assertTrue(all(0 < p['share_minutos'] <= 100 for p in w['plantilla']))
        self.assertEqual(w['xi_base'][0]['linea'], 'Portero')
        self.assertEqual(w['cambios']['asociacion']['etiqueta'], 'asociación descriptiva')

    def test_club_comparison_present(self):
        club = self.out['context']['jardine_o_club']
        self.assertEqual({p['otro'] for p in club['pares']}, {'ame_solari', 'ame_ortiz', 'slp_jardine'})
        self.assertTrue(club['rasgos'])


if __name__ == '__main__':
    unittest.main()
