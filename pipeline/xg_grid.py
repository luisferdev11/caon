"""Rejilla de xG para el laboratorio de jugadas por texto.

Ajuste logístico (numpy, sin sklearn) de gol ~ distancia + ángulo + cabeza sobre todos
los tiros sin penal en caché (sin tanda de penales); se exporta una rejilla (pie / cabeza) en
coordenadas StatsBomb 120×80 del equipo que ataca hacia x=120, los coeficientes (``xg_at`` calcula
cualquier punto) y una validación contra el xG de StatsBomb (Brier, correlación, calibración por bins).
Uso: .venv/bin/python -X utf8 pipeline/xg_grid.py [--out ruta.json]
"""
import argparse
import json
import pathlib

import framework as fw
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data' / 'cache'
DEFAULT_OUT = ROOT / 'data' / 'out' / 'preview' / 'A6' / 'xg_grid.json'
GOAL_X, GOAL_Y, POST_HALF = 120.0, 40.0, 4.0   # centro y medio ancho de la portería (yd)
GRID_X = np.arange(60.0, 120.0, 2.0) + 1.0      # centros de celda de 2 yd, último medio campo
GRID_Y = np.arange(0.0, 80.0, 2.0) + 1.0
PITCH_X, PITCH_Y = 120.0, 80.0
L2_REG = 1e-4
NEWTON_ITERS = 50
CALIBRATION_BINS = 10           # bins por cuantil de probabilidad predicha
VERSION = 'xg_grid.v2'


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
    return {'version': VERSION, 'marco': 'StatsBomb 120x80, ataque hacia x=120',
            'x': GRID_X.tolist(), 'y': GRID_Y.tolist(), 'celda_yd': 2.0,
            'pie': layer(False), 'cabeza': layer(True),
            'coef': {'intercepto': float(w[0]), 'distancia': float(w[1]),
                     'angulo': float(w[2]), 'cabeza': float(w[3])},
            'n': int(n_shots), 'tasa_gol': round(goal_rate, 4),
            'nota': 'Modelo propio simple (distancia, ángulo, cabeza) sobre tiros sin penal.'}


def xg_at(grid: dict, x: float, y: float, head: bool) -> float:
    """xG del modelo en cualquier punto (coeficientes de la rejilla); la ubicación se acota al campo."""
    c = grid['coef']
    w = np.array([c['intercepto'], c['distancia'], c['angulo'], c['cabeza']])
    cx, cy = min(max(float(x), 0.0), PITCH_X), min(max(float(y), 0.0), PITCH_Y)
    return float(predict(w, np.array([cx]), np.array([cy]), np.array([bool(head)]))[0])


def brier(pred: np.ndarray, goal: np.ndarray) -> float:
    """Error cuadrático medio de la probabilidad (Brier)."""
    return float(np.mean((pred - goal) ** 2))


def calibration_bins(pred: np.ndarray, goal: np.ndarray, n_bins: int = CALIBRATION_BINS) -> list:
    """Bins por cuantil de la probabilidad predicha: [{p_media, tasa, n}] en orden creciente."""
    order = np.argsort(pred, kind='stable')
    out = []
    for idx in np.array_split(order, n_bins):
        if idx.size:
            out.append({'p_media': round(float(pred[idx].mean()), 4), 'tasa': round(float(goal[idx].mean()), 4),
                        'n': int(idx.size)})
    return out


def validation(w: np.ndarray, data: np.ndarray) -> dict:
    """Comparación con el xG de StatsBomb sobre los mismos tiros (columnas x, y, cabeza, gol, xg_sb)."""
    x, y, head, goal, sb = data[:, 0], data[:, 1], data[:, 2] > 0, data[:, 3], data[:, 4]
    pred = predict(w, x, y, head)
    rate = float(goal.mean())
    return {'brier_modelo': round(brier(pred, goal), 4), 'brier_statsbomb': round(brier(sb, goal), 4),
            'brier_constante': round(brier(np.full(goal.size, rate), goal), 4),
            'media_predicha': round(float(pred.mean()), 4), 'media_observada': round(rate, 4),
            'media_statsbomb': round(float(sb.mean()), 4),
            'correlacion_statsbomb': round(float(np.corrcoef(pred, sb)[0, 1]), 4),
            'calibracion': calibration_bins(pred, goal)}


def shots_from_events(events: list) -> list:
    """(x, y, cabeza, gol, xg StatsBomb) de tiros sin penal y fuera de la tanda."""
    rows = []
    for e in events:
        sh = e.get('shot')
        if (e.get('type') or {}).get('name') != 'Shot' or not sh or not e.get('location'):
            continue
        if (sh.get('type') or {}).get('name') == 'Penalty' or e.get('period') == fw.SHOOTOUT_PERIOD:
            continue
        head = (sh.get('body_part') or {}).get('name') == 'Head'
        goal = (sh.get('outcome') or {}).get('name') == 'Goal'
        rows.append((float(e['location'][0]), float(e['location'][1]), head, goal,
                     float(sh.get('statsbomb_xg') or 0.0)))
    return rows


def load_all_shots(cache: pathlib.Path = CACHE) -> np.ndarray:
    """IO: lee todos los v8_events en caché y devuelve un arreglo (n, 5)."""
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
    grid['validacion'] = validation(w, data)
    grid['calibracion'] = {k: grid['validacion'][k] for k in ('media_predicha', 'media_observada')}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(grid, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    val = {k: v for k, v in grid['validacion'].items() if k != 'calibracion'}
    print(f"{len(data)} tiros → {out} validación {val}")


if __name__ == '__main__':
    main()
