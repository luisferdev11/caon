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


if __name__ == '__main__':
    unittest.main()
