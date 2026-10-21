"""Pruebas del modelo ligero (model.json) y los archivos por entidad (model/entities/<id>.json)."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from model_split import (
    DETAIL_KEYS,
    league_match_ids,
    merge_entity,
    split_model,
    window_of,
    write_split,
)


def _entity(eid, group='Histórico', official=True):
    return {'id': eid, 'label': eid, 'team': 'América', 'coach': 'X', 'group': group, 'kind': 'real', 'n': 3,
                'official': official, 'att': {'matches': 3}, 'dfn': {'matches': 3}, 'style': {}, 'shape': [],
                'temporal': {'matches': []}, 'personnel': {'players': []}, 'context': {}, 'raw': {'a': 1},
                'coverage': {'requested_matches': 3}, 'context_comparisons': [], 'context_status': {}}


class SplitTests(unittest.TestCase):
    def test_window_rules(self):
        self.assertEqual(window_of({'official': True, 'group': 'Histórico'}), 'oficial')
        self.assertEqual(window_of({'official': False, 'group': 'Epílogo'}), 'epilogo')
        self.assertEqual(window_of({'official': False, 'group': 'Actual'}), 'temprano')
        self.assertIsNone(window_of({'official': False, 'kind': 'synthetic'}))

    def test_split_moves_heavy_fields(self):
        model = {'meta': {}, 'league': {}, 'map': {}, 'entities': [_entity('ame_jardine')]}
        slim, details = split_model(model, identities={'ame_jardine': {'tags': ['x']}})
        ent = slim['entities'][0]
        for key in DETAIL_KEYS:
            self.assertNotIn(key, ent)
            self.assertIn(key, details['ame_jardine'])
        self.assertEqual(ent['window'], 'oficial')
        self.assertEqual(ent['identity'], {'tags': ['x']})
        self.assertEqual(ent['att'], {'matches': 3})
        self.assertIn('temporal', model['entities'][0], 'no debe mutar la entrada')

    def test_merge_restores_full_entity(self):
        model = {'meta': {}, 'league': {}, 'map': {}, 'entities': [_entity('e1')]}
        slim, details = split_model(model)
        full = merge_entity(slim['entities'][0], details['e1'])
        self.assertEqual(full['temporal'], {'matches': []})
        self.assertEqual(full['raw'], {'a': 1})

    def test_write_split_files(self):
        model = {'meta': {}, 'league': {}, 'map': {}, 'entities': [_entity('e1'), _entity('e2', 'Epílogo', False)]}
        with tempfile.TemporaryDirectory() as tmp:
            slim = write_split(model, pathlib.Path(tmp))
            detail = json.loads((pathlib.Path(tmp) / 'entities' / 'e2.json').read_text(encoding='utf-8'))
            self.assertEqual(detail['id'], 'e2')
            self.assertIn('personnel', detail)
            self.assertEqual(slim['entities'][1]['window'], 'epilogo')

    def test_league_scope_legacy_excludes_comparison_only(self):
        ents = [{'group': 'Histórico', 'matches': [{'mid': 1}, {'mid': 2}]},
                {'group': 'Comparación', 'matches': [{'mid': 2}, {'mid': 3}]}]
        self.assertEqual(league_match_ids(ents, 'all'), [1, 2, 3])
        self.assertEqual(league_match_ids(ents, 'legacy'), [1, 2])
        with self.assertRaises(ValueError):
            league_match_ids(ents, 'otro')


if __name__ == '__main__':
    unittest.main()
