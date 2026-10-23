"""Presupuesto de tamaño sobre el modelo publicado (se salta si aún no se reconstruyó con explorer v3 y replay/)."""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'pipeline'))
MODEL = ROOT / 'model'
KB = 1024
ANALYSIS_MAX, LIST_MAX, MATCH_MAX, MODEL_MAX = 400 * KB, 300 * KB, 60 * KB, 4 * 1024 * KB


def built() -> bool:
    try:
        return 'metricas' in json.loads((MODEL / 'explorer.json').read_text(encoding='utf-8')) and (MODEL / 'replay').is_dir()
    except (OSError, ValueError):
        return False


@unittest.skipUnless(built(), 'el modelo aún no se reconstruyó con explorer v3 y replay/')
class PublishedBudgetTests(unittest.TestCase):
    def test_every_analysis_file_fits_and_keeps_its_replay_summary(self):
        files = sorted((MODEL / 'analysis').glob('*.json'))
        self.assertTrue(files)
        for f in files:
            self.assertLessEqual(f.stat().st_size, ANALYSIS_MAX, f.name)
            replay = json.loads(f.read_text(encoding='utf-8')).get('replay')
            if isinstance(replay, dict) and 'resumen' in replay:
                self.assertNotIn('partidos', replay, f.name)
                self.assertTrue(replay.get('archivo'), f.name)

    def test_every_match_card_fits(self):
        files = list((MODEL / 'matches').glob('*.json'))
        self.assertTrue(files)
        for f in files:
            self.assertLessEqual(f.stat().st_size, MATCH_MAX, f.name)

    def test_model_json_is_light(self):
        self.assertLessEqual((MODEL / 'model.json').stat().st_size, MODEL_MAX)

    def test_explorer_lists_are_light_through_the_api(self):
        from fastapi.testclient import TestClient

        from app import main
        main.clear_cache()
        client = TestClient(main.app)
        for kind in ('teams', 'coaches'):
            res = client.get(f'/api/explorer/{kind}')
            self.assertEqual(res.status_code, 200)
            self.assertLessEqual(len(res.content), LIST_MAX, kind)
            self.assertTrue(all('temporadas' not in u and 'tenencias' not in u for u in res.json()), kind)


if __name__ == '__main__':
    unittest.main()
