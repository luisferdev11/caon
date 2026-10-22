import pathlib
import re
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


MODEL_DIR = pathlib.Path(__file__).resolve().parents[1] / 'model'
KB = 1024
# (ruta, tope de tamaño en bytes) del portal; se prueban con el modelo publicado
PORTAL_ROUTES = (('/api/health', 4 * KB), ('/api/framework', 600 * KB), ('/api/entities', 120 * KB),
                 ('/api/story/jardine', 300 * KB), ('/api/story/almada', 100 * KB),
                 ('/api/entities/ame_jardine/analysis', 400 * KB), ('/api/entities/ame_jardine/matches', 120 * KB),
                 ('/api/replay/ame_jardine', 300 * KB), ('/api/kpis/ame_jardine', 100 * KB),
                 ('/api/explorer/teams', 300 * KB), ('/api/explorer/coaches', 300 * KB), ('/api/explorer/catalog', 40 * KB),
                 ('/api/xg_grid', 60 * KB))


@unittest.skipUnless((MODEL_DIR / 'kpis' / 'ame_jardine.json').exists() and (MODEL_DIR / 'story' / 'jardine.json').exists()
                     and (MODEL_DIR / 'replay' / 'ame_jardine.json').exists(), 'modelo del portal aún no construido')
class PortalRoutesTest(unittest.TestCase):
    def test_every_portal_route_answers_200_within_its_size_budget(self):
        with TestClient(app) as client:
            for path, limit in PORTAL_ROUTES:
                res = client.get(path)
                self.assertEqual(res.status_code, 200, path)
                self.assertLessEqual(len(res.content), limit, f'{path}: {len(res.content)} bytes')

    def test_a_real_match_card_fits_and_has_the_deserved_to_win_block(self):
        with TestClient(app) as client:
            rows = client.get('/api/entities/ame_jardine/matches').json()['partidos']
            res = client.get(f"/api/matches/{rows[0]['match_id']}")
            self.assertEqual(res.status_code, 200)
            self.assertLessEqual(len(res.content), 60 * KB)
            self.assertIn('merecio', res.json()['ficha'])

    def test_missing_resources_answer_404_in_spanish(self):
        with TestClient(app) as client:
            for path in ('/api/story/nadie', '/api/kpis/nadie', '/api/matches/1', '/api/entities/nadie/matches',
                         '/api/entities/nadie/analysis', '/api/replay/nadie', '/api/explorer/team/nadie'):
                res = client.get(path)
                self.assertEqual(res.status_code, 404, path)
                self.assertRegex(res.json()['detail'], r'No existe|No existen', path)

    def test_no_secret_in_any_portal_response(self):
        key = (pathlib.Path(__file__).resolve().parents[1] / '.env')
        values = []
        if key.exists():
            values = [ln.split('=', 1)[1].strip().strip('"\'') for ln in key.read_text(encoding='utf-8').splitlines()
                      if '=' in ln and not ln.startswith('#') and re.search(r'KEY|TOKEN|SECRET|PASSWORD', ln.split('=', 1)[0].upper())
                      and len(ln.split('=', 1)[1].strip()) >= 12]
        with TestClient(app) as client:
            for path, _ in PORTAL_ROUTES + (('/api/play/capabilities', 0),):
                text = client.get(path).text
                for v in values:
                    self.assertNotIn(v, text, path)


if __name__ == '__main__': unittest.main()
