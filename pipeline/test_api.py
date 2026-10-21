import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from targets import agg

from app.main import app


class APITests(unittest.TestCase):
    def test_missing_fields_and_existing_endpoints(self):
        model = {'meta': {}, 'entities': [{'id': 'empty', 'label': 'América · Histórico', 'n': 0}]}
        with patch('app.main.load_model', return_value=model), TestClient(app) as client:
            detail = client.get('/api/teams/empty')
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.json()['style'], {})
            self.assertEqual(detail.json()['shape'], [])
            self.assertIsNone(client.get('/api/teams/empty/context').json()['context'])
            for suffix in ('temporal', 'personnel', 'lineups', 'substitutions'):
                self.assertEqual(client.get('/api/teams/empty/' + suffix).status_code, 200)
            self.assertEqual(client.get('/api/teams/missing/context').status_code, 404)
            self.assertEqual(client.get('/api/teams').json()[0]['label'], 'América · Histórico')

    def test_real_model_served_as_utf8(self):
        with TestClient(app) as client:
            model = client.get('/api/model')
            self.assertEqual(model.status_code, 200)
            self.assertEqual(model.json()['entities'][0]['team'], 'América')
            self.assertEqual(client.get('/context_view.js').status_code, 200)

    def test_real_model_is_slim_once_split(self):
        path = pathlib.Path(__file__).resolve().parents[1] / 'model' / 'model.json'
        with TestClient(app) as client:
            model = client.get('/api/model').json()
        if 'window' not in model['entities'][0]:
            self.skipTest('model.json aún no está dividido (falta correr pipeline/run.py build)')
        self.assertLessEqual(path.stat().st_size, 4 * 1024 * 1024)
        self.assertNotIn('personnel', model['entities'][0])

    def test_empty_targets_and_nonfinite_data(self):
        self.assertIsNone(agg([])['goals'])
        observed = agg([{'team_match_goals': 0}, {'team_match_goals': None}, {'team_match_goals': float('inf')}])
        self.assertEqual(observed['goals'], 0)
        self.assertEqual(observed['coverage']['valid_matches']['goals'], 1)


if __name__ == '__main__': unittest.main()
