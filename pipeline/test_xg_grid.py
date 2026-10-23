"""Tests de la rejilla de xG (pipeline/xg_grid.py)."""
import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xg_grid


def synthetic(n=4000, seed=5):
    rng = np.random.default_rng(seed)
    x = rng.uniform(70, 119, n)
    y = rng.uniform(10, 70, n)
    head = rng.random(n) < 0.2
    feats = xg_grid.features(x, y, head)
    true_w = np.array([-0.5, -0.12, 1.4, -0.9])
    p = 1 / (1 + np.exp(-(feats @ true_w)))
    goal = rng.random(n) < p
    return x, y, head, goal


class GeometryTest(unittest.TestCase):
    def test_distance_and_angle(self):
        f = xg_grid.features(np.array([108.0]), np.array([40.0]), np.array([False]))
        self.assertAlmostEqual(f[0, 1], 12.0)
        self.assertGreater(f[0, 2], 0.5)
        far = xg_grid.features(np.array([80.0]), np.array([40.0]), np.array([True]))
        self.assertLess(far[0, 2], f[0, 2])
        self.assertEqual(far[0, 3], 1.0)


class FitTest(unittest.TestCase):
    def test_calibration_mean(self):
        x, y, head, goal = synthetic()
        w = xg_grid.fit_logistic(xg_grid.features(x, y, head), goal.astype(float))
        pred = xg_grid.predict(w, x, y, head)
        self.assertAlmostEqual(float(pred.mean()), float(goal.mean()), delta=0.01)

    def test_closer_is_more_likely(self):
        x, y, head, goal = synthetic()
        w = xg_grid.fit_logistic(xg_grid.features(x, y, head), goal.astype(float))
        near, far = xg_grid.predict(w, np.array([112.0, 90.0]), np.array([40.0, 40.0]), np.array([False, False]))
        self.assertGreater(near, far)

    def test_grid_payload(self):
        x, y, head, goal = synthetic(n=500)
        w = xg_grid.fit_logistic(xg_grid.features(x, y, head), goal.astype(float))
        grid = xg_grid.make_grid(w, n_shots=500, goal_rate=float(goal.mean()))
        self.assertEqual(len(grid['pie']), len(grid['y']))
        self.assertEqual(len(grid['pie'][0]), len(grid['x']))
        self.assertEqual(len(grid['cabeza']), len(grid['y']))
        self.assertTrue(all(0 <= v <= 1 for row in grid['pie'] for v in row))
        self.assertEqual(grid['n'], 500)


def shot_ev(x, y, xg=0.1, goal=False, head=False, kind='Open Play', period=1):
    return {'type': {'name': 'Shot'}, 'period': period, 'location': [x, y],
            'shot': {'statsbomb_xg': xg, 'type': {'name': kind}, 'body_part': {'name': 'Head' if head else 'Right Foot'},
                     'outcome': {'name': 'Goal' if goal else 'Saved'}}}


class ShotsTest(unittest.TestCase):
    def test_excludes_penalties_shootout_and_keeps_statsbomb_xg(self):
        evs = [shot_ev(108, 40, xg=0.3, goal=True, head=True), shot_ev(108, 40, kind='Penalty'),
               shot_ev(100, 30, period=5), {'type': {'name': 'Own Goal For'}, 'period': 1},
               shot_ev(95, 50, xg=0.05)]
        rows = xg_grid.shots_from_events(evs)
        self.assertEqual(rows, [(108.0, 40.0, True, True, 0.3), (95.0, 50.0, False, False, 0.05)])


class ValidationTest(unittest.TestCase):
    def test_brier(self):
        self.assertAlmostEqual(xg_grid.brier(np.array([1.0, 0.0]), np.array([1.0, 0.0])), 0.0)
        self.assertAlmostEqual(xg_grid.brier(np.array([0.5, 0.5]), np.array([1.0, 0.0])), 0.25)

    def test_calibration_bins(self):
        x, y, head, goal = synthetic()
        w = xg_grid.fit_logistic(xg_grid.features(x, y, head), goal.astype(float))
        bins = xg_grid.calibration_bins(xg_grid.predict(w, x, y, head), goal.astype(float), n_bins=5)
        self.assertEqual(len(bins), 5)
        self.assertEqual(sum(b['n'] for b in bins), len(x))
        means = [b['p_media'] for b in bins]
        self.assertEqual(means, sorted(means))
        for b in bins:
            self.assertAlmostEqual(b['p_media'], b['tasa'], delta=0.06)

    def test_validation_block(self):
        x, y, head, goal = synthetic()
        sb = np.clip(xg_grid.predict(np.array([-0.5, -0.12, 1.4, -0.9]), x, y, head), 0, 1)
        data = np.column_stack([x, y, head, goal, sb])
        w = xg_grid.fit_logistic(xg_grid.features(x, y, head), goal.astype(float))
        val = xg_grid.validation(w, data)
        self.assertTrue({'brier_modelo', 'brier_statsbomb', 'brier_constante', 'media_predicha',
                         'media_observada', 'media_statsbomb', 'correlacion_statsbomb', 'calibracion'} <= set(val))
        self.assertLess(val['brier_modelo'], val['brier_constante'])
        self.assertGreater(val['correlacion_statsbomb'], 0.9)


class LookupTest(unittest.TestCase):
    def test_xg_at_matches_grid_cells_and_clamps(self):
        x, y, head, goal = synthetic(n=800)
        w = xg_grid.fit_logistic(xg_grid.features(x, y, head), goal.astype(float))
        grid = xg_grid.make_grid(w, n_shots=800, goal_rate=float(goal.mean()))
        i, j = 5, 20
        self.assertAlmostEqual(xg_grid.xg_at(grid, grid['x'][j], grid['y'][i], False), grid['pie'][i][j], places=4)
        self.assertAlmostEqual(xg_grid.xg_at(grid, grid['x'][j], grid['y'][i], True), grid['cabeza'][i][j], places=4)
        self.assertGreater(xg_grid.xg_at(grid, 114, 40, False), xg_grid.xg_at(grid, 90, 40, False))
        self.assertEqual(xg_grid.xg_at(grid, 130, 40, False), xg_grid.xg_at(grid, 120, 40, False))  # fuera del campo


if __name__ == '__main__':
    unittest.main()
