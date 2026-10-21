"""Rejilla de xG para el laboratorio de jugadas por texto.

Ajuste logístico (numpy, sin sklearn) de gol ~ distancia + ángulo + cabeza sobre todos
los tiros sin penal en caché; se exporta una rejilla (pie / cabeza) en coordenadas
StatsBomb 120×80 del equipo que ataca hacia x=120.
Uso: .venv/bin/python -X utf8 pipeline/xg_grid.py [--out ruta.json]
"""
import argparse
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data' / 'cache'
DEFAULT_OUT = ROOT / 'data' / 'out' / 'preview' / 'A6' / 'xg_grid.json'
GOAL_X, GOAL_Y, POST_HALF = 120.0, 40.0, 4.0   # centro y medio ancho de la portería (yd)
GRID_X = np.arange(60.0, 120.0, 2.0) + 1.0      # centros de celda de 2 yd, último medio campo
GRID_Y = np.arange(0.0, 80.0, 2.0) + 1.0
L2_REG = 1e-4
NEWTON_ITERS = 50


def features(x: np.ndarray, y: np.ndarray, head: np.ndarray) -> np.ndarray:
    """Matriz [1, distancia, ángulo de portería (rad), cabeza]."""
    dx = np.maximum(GOAL_X - x, 0.0)
    dist = np.hypot(dx, GOAL_Y - y)
    a1 = np.arctan2(GOAL_Y + POST_HALF - y, dx)
    a2 = np.arctan2(GOAL_Y - POST_HALF - y, dx)
    angle = np.abs(a1 - a2)
    return np.column_stack([np.ones_like(dist), dist, angle, head.astype(float)])


def fit_logistic(feats: np.ndarray, goal: np.ndarray) -> np.ndarray:
    """Máxima verosimilitud por Newton-Raphson con L2 leve (sin penalizar el intercepto)."""
    w = np.zeros(feats.shape[1])
    reg = np.full(feats.shape[1], L2_REG)
    reg[0] = 0.0
    for _ in range(NEWTON_ITERS):
        p = 1.0 / (1.0 + np.exp(-(feats @ w)))
        grad = feats.T @ (p - goal) + reg * w
        hess = (feats * (p * (1 - p))[:, None]).T @ feats + np.diag(reg)
        step = np.linalg.solve(hess, grad)
        w -= step
        if np.max(np.abs(step)) < 1e-9:
            break
    return w


def predict(w: np.ndarray, x: np.ndarray, y: np.ndarray, head: np.ndarray) -> np.ndarray:
    """Probabilidad de gol para tiros en (x, y)."""
    return 1.0 / (1.0 + np.exp(-(features(x, y, head) @ w)))


def make_grid(w: np.ndarray, n_shots: int, goal_rate: float) -> dict:
    """Payload JSON: rejillas [fila y][columna x] para pie y cabeza."""
    gx, gy = np.meshgrid(GRID_X, GRID_Y)

    def layer(is_head: bool) -> list:
        p = predict(w, gx.ravel(), gy.ravel(), np.full(gx.size, is_head)).reshape(gx.shape)
        return np.round(p, 4).tolist()
    return {'version': 'xg_grid.v1', 'marco': 'StatsBomb 120x80, ataque hacia x=120',
            'x': GRID_X.tolist(), 'y': GRID_Y.tolist(), 'celda_yd': 2.0,
            'pie': layer(False), 'cabeza': layer(True),
            'coef': {'intercepto': float(w[0]), 'distancia': float(w[1]),
                     'angulo': float(w[2]), 'cabeza': float(w[3])},
            'n': int(n_shots), 'tasa_gol': round(goal_rate, 4),
            'nota': 'Modelo propio simple (distancia, ángulo, cabeza) sobre tiros sin penal.'}


def shots_from_events(events: list) -> list:
    """(x, y, cabeza, gol) de tiros sin penal y fuera de la tanda."""
    rows = []
    for e in events:
        sh = e.get('shot')
        if (e.get('type') or {}).get('name') != 'Shot' or not sh or not e.get('location'):
            continue
        if (sh.get('type') or {}).get('name') == 'Penalty' or e.get('period') == 5:
            continue
        head = (sh.get('body_part') or {}).get('name') == 'Head'
        goal = (sh.get('outcome') or {}).get('name') == 'Goal'
        rows.append((float(e['location'][0]), float(e['location'][1]), head, goal))
    return rows


def load_all_shots(cache: pathlib.Path = CACHE) -> np.ndarray:
    """Lee todos los v8_events en caché y devuelve un arreglo (n, 4)."""
    rows = []
    for path in sorted(cache.glob('v8_events_*.json')):
        rows.extend(shots_from_events(json.loads(path.read_text(encoding='utf-8'))))
    return np.array(rows, dtype=float)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    args = ap.parse_args()
    data = load_all_shots()
    x, y, head, goal = data[:, 0], data[:, 1], data[:, 2] > 0, data[:, 3]
    w = fit_logistic(features(x, y, head), goal)
    grid = make_grid(w, n_shots=len(data), goal_rate=float(goal.mean()))
    grid['calibracion'] = {'media_predicha': round(float(predict(w, x, y, head).mean()), 4),
                           'media_observada': round(float(goal.mean()), 4)}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(grid, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(f"{len(data)} tiros → {out} calibración {grid['calibracion']}")


if __name__ == '__main__':
    main()
