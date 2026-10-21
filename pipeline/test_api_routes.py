"""Rutas nuevas de la API sobre un directorio de modelo sintético (model/ dividido)."""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient

from app import main

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import labels


def _write(path: pathlib.Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')


def _fixture(root: pathlib.Path) -> None:
    ent = {'id': 'ame_jardine', 'label': 'América · Jardine', 'team': 'América', 'n': 2, 'official': True,
           'window': 'oficial', 'att': {}, 'dfn': {}}
    _write(root / 'model.json', {'meta': {'built': 'x'}, 'league': {}, 'map': {}, 'entities': [ent]})
    _write(root / 'entities' / 'ame_jardine.json', {'id': 'ame_jardine', 'temporal': {'periods': [1]},
                                                    'personnel': {'substitutions': [{'m': 1}], 'matches': [{'match_id': 7}]}})
    _write(root / 'analysis' / 'ame_jardine.json', {'replay': {'matches': [{'match_id': 7, 'xpts': 1.5}]}})
    _write(root / 'explorer.json', {'teams': [{'key': 'america', 'n': 10}], 'coaches': [{'key': 'jardine', 'n': 9}]})
    _write(root / 'story' / 'jardine.json', {'chapters': []})


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        _fixture(self.root)
        self.patch = patch.object(main, 'MODEL_DIR', self.root)
        self.patch.start()
        main.clear_cache()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.patch.stop()
        main.clear_cache()
        self.tmp.cleanup()

    def test_split_entity_endpoints_merge_details(self):
        self.assertEqual(self.client.get('/api/teams/ame_jardine/temporal').json()['temporal'], {'periods': [1]})
        self.assertEqual(self.client.get('/api/teams/ame_jardine/substitutions').json()['substitutions'], [{'m': 1}])
        self.assertEqual(self.client.get('/api/teams/ame_jardine').json()['personnel']['matches'][0]['match_id'], 7)

    def test_entities_and_analysis(self):
        ents = self.client.get('/api/entities').json()
        self.assertEqual(ents[0]['window'], 'oficial')
        self.assertTrue(ents[0]['has_analysis'])
        self.assertIn('replay', self.client.get('/api/entities/ame_jardine/analysis').json())
        missing = self.client.get('/api/entities/nadie/analysis')
        self.assertEqual(missing.status_code, 404)
        self.assertIn('No existe', missing.json()['detail'])

    def test_explorer_story_replay_matches(self):
        self.assertEqual(self.client.get('/api/explorer/teams').json()[0]['key'], 'america')
        self.assertEqual(self.client.get('/api/explorer/coach/jardine').json()['n'], 9)
        self.assertEqual(self.client.get('/api/explorer/coach/zzz').status_code, 404)
        self.assertEqual(self.client.get('/api/explorer/otros').status_code, 404)
        self.assertEqual(self.client.get('/api/story/jardine').json(), {'chapters': []})
        self.assertEqual(self.client.get('/api/story/..%2Fmodel').status_code, 404)
        self.assertEqual(self.client.get('/api/replay/ame_jardine').json()['matches'][0]['xpts'], 1.5)
        self.assertEqual(self.client.get('/api/matches/7').json()['xpts'], 1.5)
        self.assertEqual(self.client.get('/api/matches/8').status_code, 404)
        _write(self.root / 'analysis' / 'ame_jardine.json', {'replay': {'partidos': [{'match_id': 9, 'xpts': 2}]}})
        self.assertEqual(self.client.get('/api/matches/9').json()['xpts'], 2)

    def test_reload_on_mtime_for_split_files(self):
        self.client.get('/api/teams/ame_jardine/temporal')
        path = self.root / 'entities' / 'ame_jardine.json'
        _write(path, {'id': 'ame_jardine', 'temporal': {'periods': [2]}})
        import os
        st = path.stat()
        os.utime(path, (st.st_atime, st.st_mtime + 5))
        self.assertEqual(self.client.get('/api/teams/ame_jardine/temporal').json()['temporal'], {'periods': [2]})

    def test_explorer_spanish_payload_and_slugs(self):
        _write(self.root / 'explorer.json', {'equipos': [{'team': 'América', 'n': 3}],
                                             'entrenadores': [{'coach': 'André Jardine', 'n': 9}]})
        self.assertEqual(self.client.get('/api/explorer/teams').json()[0]['team'], 'América')
        self.assertEqual(self.client.get('/api/explorer/team/america').json()['n'], 3)
        self.assertEqual(self.client.get('/api/explorer/coach/andre-jardine').json()['n'], 9)

    def test_explorer_lists_are_light_and_details_are_full(self):
        team = {'key': 'america', 'team': 'América', 'n': 10, 'temporadas': [{'x': 1}] * 5, 'entidades': ['a'],
                'metrics': {'xg': {'id': 'xg', 'nombre': 'xG', 'unit': 'u', 'source': 's', 'prior_value': 1,
                                   'value': 1.2, 'raw': 1.1, 'ci': [1, 2], 'ref_pct': 40, 'n': 9, 'window': 'oficial'}}}
        coach = {'key': 'jardine', 'coach': 'Jardine', 'n': 9, 'tenencias': [{'x': 1}] * 5, 'temporadas': [1]}
        _write(self.root / 'explorer.json', {'equipos': [team], 'entrenadores': [coach], 'metricas': [{'id': 'xg'}],
                                             'metodo': {'k': 8}, 'version': 'explorer.v3'})
        lst = self.client.get('/api/explorer/teams').json()[0]
        self.assertNotIn('temporadas', lst)
        self.assertNotIn('entidades', lst)
        self.assertEqual(lst['metrics']['xg'], {'id': 'xg', 'value': 1.2, 'raw': 1.1, 'ci': [1, 2], 'ref_pct': 40,
                                                 'n': 9, 'window': 'oficial'})
        self.assertNotIn('tenencias', self.client.get('/api/explorer/coaches').json()[0])
        self.assertEqual(len(self.client.get('/api/explorer/team/america').json()['temporadas']), 5)
        self.assertEqual(len(self.client.get('/api/explorer/coach/jardine').json()['tenencias']), 5)
        self.assertIn('nombre', self.client.get('/api/explorer/team/america').json()['metrics']['xg'])

    def test_explorer_catalog_route(self):
        _write(self.root / 'explorer.json', {'equipos': [], 'entrenadores': [], 'metricas': [{'id': 'xg'}],
                                             'metodo': {'k': 8}, 'version': 'explorer.v3'})
        cat = self.client.get('/api/explorer/catalog').json()
        self.assertEqual(cat['metricas'], [{'id': 'xg'}])
        self.assertEqual(cat['metodo'], {'k': 8})

    def test_replay_route_serves_the_per_entity_file_and_summary_fallback(self):
        _write(self.root / 'replay' / 'ame_jardine.json', {'partidos': [{'match_id': 7, 'xpts': 3}]})
        self.assertEqual(self.client.get('/api/replay/ame_jardine').json()['partidos'][0]['xpts'], 3)
        (self.root / 'replay' / 'ame_jardine.json').unlink()
        self.assertEqual(self.client.get('/api/replay/ame_jardine').json()['matches'][0]['xpts'], 1.5)
        self.assertEqual(self.client.get('/api/replay/nadie').status_code, 404)

    def test_xg_grid_route(self):
        self.assertEqual(self.client.get('/api/xg_grid').status_code, 404)
        _write(self.root / 'xg_grid.json', {'version': 'xg_grid.v2', 'coef': {'intercepto': 0}})
        res = self.client.get('/api/xg_grid')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['version'], 'xg_grid.v2')

    def test_framework_route(self):
        res = self.client.get('/api/framework')
        self.assertIn(res.status_code, (200, 503))
        if res.status_code == 200:
            self.assertIsInstance(res.json()['definitions'], dict)

    def test_framework_route_exposes_label_names(self):
        res = self.client.get('/api/framework')
        self.assertEqual(res.status_code, 200)
        et = res.json()['etiquetas']
        self.assertEqual(et['cuadrantes']['dfn']['tr'], labels.QUADRANTS['dfn']['tr'])
        self.assertEqual(et['cuadrantes'], {k: dict(v) for k, v in labels.QUADRANTS.items()})
        self.assertEqual({k: list(v) for k, v in et['ejes'].items()}, {k: list(v) for k, v in labels.AXES.items()})


if __name__ == '__main__':
    unittest.main()
