# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Biblioteca pura para frames 360 de StatsBomb: geometría, visibilidad y métricas por frame.

Convención: cada frame viene en el marco de ataque del equipo del ``actor`` (x→120), con
``teammate`` relativo al actor. ``view`` normaliza un frame a la perspectiva de un equipo X:
si X no es el equipo del actor, sus jugadores son ``teammate == False`` y todo se invierte con
``framework.to_frame``. En el marco de X, X defiende la portería en x=0 y ataca hacia x=120.

Solo se ven jugadores dentro de ``visible_area``: todos los conteos son cota inferior y cada
métrica pasa una puerta de visibilidad (fracción visible de su región de interés, ROI).
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Optional

from framework import (
    BOX_Y,
    DEEP_LINE_N,
    ERROR_OPP_RADIUS_YD,
    FREE_OPTION_MARGIN_YD,
    FREE_OPTION_RADIUS_YD,
    GRID_STEP_YD,
    ISOLATION_RADIUS_YD,
    MIN_ROI_VISIBLE,
    MIN_SHAPE_PLAYERS,
    PAIRING_RADIUS_YD,
    PITCH_X,
    PITCH_Y,
    PRESS_SUPPORT_RADIUS_YD,
    PRESSURE_RADIUS_YD,
    ROI_BACK_YD,
    ROI_FRONT_YD,
    ROI_HALF_WIDTH_YD,
    XPASS_EASY,
    XPASS_RISKY,
    to_frame,
)

Point = tuple[float, float]
Rect = tuple[float, float, float, float]  # x0, y0, x1, y1

# --- Constantes 360 propias de la geometría (los umbrales de visibilidad y radios viven en framework.py) ---
ERROR_ROI_YD = 10.0           # ROI del contexto del error: cuadrado ±10 yd del actor
OWN_BOX_MAX_X = 18.0          # área propia en el marco de X (x < 18, 18 ≤ y ≤ 62)
OWN_SIX_MAX_X = 6.0           # área chica propia (x < 6, 30 ≤ y ≤ 50)
SIX_Y = (30.0, 50.0)
MARK_MAN_MIN_PAIRING = 0.60   # ≥60 % de atacantes emparejados → "al hombre" (inferido)
MARK_MAN_MAX_UNPAIRED_SIX = 1
MARK_ZONAL_MAX_PAIRING = 0.35  # ≤35 % emparejados y ≥3 libres en área chica → "zonal"
MARK_ZONAL_MIN_UNPAIRED_SIX = 3
SAME_POINT_YD = 0.01
COMPACT_DECIMALS = 1
CODE_OWN, CODE_OPP, CODE_OWN_GK, CODE_OPP_GK, CODE_ACTOR = 0, 1, 2, 3, 4


# ---------------------------------------------------------------- geometría
def polygon_from_flat(flat: Sequence[float]) -> list[Point]:
    """Lista plana x,y,x,y,... → polígono (sin repetir el cierre)."""
    pts = [(float(flat[i]), float(flat[i + 1])) for i in range(0, len(flat) - 1, 2)]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return pts


def point_in_polygon(pt: Sequence[float], poly: Sequence[Point]) -> bool:
    """Ray casting (par-impar)."""
    x, y = pt[0], pt[1]
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xc:
                inside = not inside
    return inside


def clip_rect(rect: Rect) -> Rect:
    """Recorta un rectángulo a la cancha."""
    x0, y0, x1, y1 = rect
    return (max(0.0, x0), max(0.0, y0), min(PITCH_X, x1), min(PITCH_Y, y1))


def roi_visible_fraction(poly: Sequence[Point], rect: Rect, step: float = GRID_STEP_YD) -> float:
    """Fracción de centros de celda (malla ``step``) de la ROI que caen dentro del polígono."""
    x0, y0, x1, y1 = clip_rect(rect)
    if not poly or x1 - x0 <= 0 or y1 - y0 <= 0:
        return 0.0
    nx = max(1, math.ceil((x1 - x0) / step))
    ny = max(1, math.ceil((y1 - y0) / step))
    dx, dy = (x1 - x0) / nx, (y1 - y0) / ny
    hits = sum(point_in_polygon((x0 + (i + 0.5) * dx, y0 + (j + 0.5) * dy), poly)
               for i in range(nx) for j in range(ny))
    return hits / (nx * ny)


def _cross(o: Point, a: Point, b: Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(points: Sequence[Point]) -> list[Point]:
    """Envolvente convexa por cadena monótona (Andrew)."""
    pts = sorted({(float(p[0]), float(p[1])) for p in points})
    if len(pts) <= 2:
        return pts
    lower: list[Point] = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[Point] = []
    for p in reversed(pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def polygon_area(poly: Sequence[Point]) -> float:
    """Área por fórmula del cordón (0 si hay menos de 3 vértices)."""
    if len(poly) < 3:
        return 0.0
    s = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
            for i in range(len(poly)))
    return abs(s) / 2.0


def dist(a: Sequence[float], b: Sequence[float]) -> float:
    """Distancia euclídea en yardas."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def deepest_line(points: Sequence[Point], n: int = DEEP_LINE_N) -> Optional[float]:
    """Media x de los ``n`` jugadores más retrasados (None si hay menos de ``n``)."""
    if len(points) < n:
        return None
    return sum(sorted(p[0] for p in points)[:n]) / n


def goal_side(points: Sequence[Point], ball_x: float) -> int:
    """Jugadores entre el balón y la portería propia (x < balón en el marco propio)."""
    return sum(1 for p in points if p[0] < ball_x)


def mean_x(points: Sequence[Point]) -> Optional[float]:
    """Media de x (None si no hay puntos)."""
    return sum(p[0] for p in points) / len(points) if points else None


# ---------------------------------------------------------------- normalización
def view(frame: dict[str, Any], team_is_actor: bool) -> dict[str, Any]:
    """Frame → vista en el marco del equipo X (propios, rivales, porteros, actor, polígono)."""
    flip = not team_is_actor
    out: dict[str, Any] = {'own': [], 'opp': [], 'own_gk': [], 'opp_gk': [], 'actor': None}
    for p in frame.get('freeze_frame') or []:
        loc = tuple(to_frame(p['location'], flip))
        mine = bool(p.get('teammate')) == team_is_actor
        key = ('own' if mine else 'opp') + ('_gk' if p.get('keeper') else '')
        out[key].append(loc)
        if p.get('actor'):
            out['actor'] = loc
    poly = polygon_from_flat(frame.get('visible_area') or [])
    out['poly'] = [tuple(to_frame(q, flip)) for q in poly]
    return out


def _vis(v: dict[str, Any], rect: Rect) -> float:
    return roi_visible_fraction(v['poly'], rect)


def rnd(x: Optional[float], nd: int = 2) -> Optional[float]:
    """Redondeo tolerante a None."""
    return None if x is None else round(float(x), nd)


# ---------------------------------------------------------------- métricas por frame
def rest_defense(v: dict[str, Any], ball: Point) -> dict[str, Any]:
    """Vigilancias: propios detrás del balón (centrales), rivales por delante y superioridad."""
    bx = ball[0]
    vis = _vis(v, (bx - ROI_BACK_YD, ball[1] - ROI_HALF_WIDTH_YD, bx, ball[1] + ROI_HALF_WIDTH_YD))
    gs = [p for p in v['own'] if p[0] < bx]
    ahead = goal_side(v['opp'], bx)
    return {'own_goal_side': len(gs), 'own_central': sum(1 for p in gs if BOX_Y[0] <= p[1] <= BOX_Y[1]),
            'opp_ahead': ahead, 'superiority': len(gs) - ahead, 'roi_vis': rnd(vis),
            'valid': vis >= MIN_ROI_VISIBLE}


def error_context(v: dict[str, Any], actor: Point) -> dict[str, Any]:
    """Contexto del último evento con balón antes de la pérdida."""
    vis = _vis(v, (actor[0] - ERROR_ROI_YD, actor[1] - ERROR_ROI_YD,
                   actor[0] + ERROR_ROI_YD, actor[1] + ERROR_ROI_YD))
    mates = [d for d in (dist(p, actor) for p in v['own']) if d > SAME_POINT_YD]
    opps = [dist(p, actor) for p in v['opp']]
    near = sum(1 for d in mates if d <= ISOLATION_RADIUS_YD)
    return {'teammates_near': near, 'opps_near': sum(1 for d in opps if d <= ERROR_OPP_RADIUS_YD),
            'opps_pressing': sum(1 for d in opps if d <= PRESSURE_RADIUS_YD),
            'nearest_opp': rnd(min(opps)) if opps else None, 'isolated': near == 0,
            'roi_vis': rnd(vis), 'valid': vis >= MIN_ROI_VISIBLE}


def _shape_roi(ball: Point) -> Rect:
    return (ball[0] - ROI_BACK_YD, ball[1] - ROI_HALF_WIDTH_YD, ball[0] + ROI_FRONT_YD, ball[1] + ROI_HALF_WIDTH_YD)


def block_shape(v: dict[str, Any], ball: Point) -> dict[str, Any]:
    """Bloque defensivo: última línea, largo, ancho, área convexa y jugadores tras el balón."""
    own = v['own']
    vis = _vis(v, _shape_roi(ball))
    xs, ys = [p[0] for p in own], [p[1] for p in own]
    return {'n_vis': len(own), 'last_line': rnd(deepest_line(own)),
            'length': rnd(max(xs) - min(xs)) if own else None,
            'width': rnd(max(ys) - min(ys)) if own else None,
            'hull_area': rnd(polygon_area(convex_hull(own)), 1), 'between': goal_side(own, ball[0]),
            'roi_vis': rnd(vis), 'valid': vis >= MIN_ROI_VISIBLE and len(own) >= MIN_SHAPE_PLAYERS}


def line_height(v: dict[str, Any], ball: Point) -> dict[str, Any]:
    """Altura de la última línea propia con balón (salida)."""
    own = v['own']
    vis = _vis(v, _shape_roi(ball))
    return {'n_vis': len(own), 'height': deepest_line(own), 'roi_vis': rnd(vis),
            'valid': vis >= MIN_ROI_VISIBLE and len(own) >= MIN_SHAPE_PLAYERS}


def packing(v: dict[str, Any], start: Point, end: Point) -> dict[str, Any]:
    """Rivales de campo visibles superados (x0 < x < x1): cota inferior del packing."""
    x0, x1 = start[0], end[0]
    if x1 <= x0:
        return {'bypassed': 0, 'roi_vis': None, 'valid': False}
    ylo, yhi = min(start[1], end[1]), max(start[1], end[1])
    vis = _vis(v, (x0, ylo - ROI_HALF_WIDTH_YD, x1, yhi + ROI_HALF_WIDTH_YD))
    return {'bypassed': sum(1 for p in v['opp'] if x0 < p[0] < x1), 'roi_vis': rnd(vis),
            'valid': vis >= MIN_ROI_VISIBLE}


def coordinated_pressure(v: dict[str, Any], presser: Point) -> dict[str, Any]:
    """Presión: compañeros a ≤10 yd del balón y opciones libres del rival a ≤15 yd."""
    if not v['opp']:
        return {'support': None, 'free_options': None, 'roi_vis': None, 'valid': False}
    carrier = min(v['opp'], key=lambda p: dist(p, presser))
    vis = _vis(v, (carrier[0] - FREE_OPTION_RADIUS_YD, carrier[1] - FREE_OPTION_RADIUS_YD,
                   carrier[0] + FREE_OPTION_RADIUS_YD, carrier[1] + FREE_OPTION_RADIUS_YD))
    support = sum(1 for p in v['own'] if dist(p, carrier) <= PRESS_SUPPORT_RADIUS_YD)
    free = 0
    for p in v['opp']:
        if p == carrier or dist(p, carrier) > FREE_OPTION_RADIUS_YD:
            continue
        if all(dist(p, q) > FREE_OPTION_MARGIN_YD for q in v['own']):
            free += 1
    return {'support': support, 'free_options': free, 'carrier_dist': rnd(dist(carrier, presser)),
            'roi_vis': rnd(vis), 'valid': vis >= MIN_ROI_VISIBLE}


def _in_own_box(p: Point) -> bool:
    return p[0] < OWN_BOX_MAX_X and BOX_Y[0] <= p[1] <= BOX_Y[1]


def _in_own_six(p: Point) -> bool:
    return p[0] < OWN_SIX_MAX_X and SIX_Y[0] <= p[1] <= SIX_Y[1]


def marking_style(pairing: Optional[float], unpaired_six: int) -> Optional[str]:
    """Tipo de marca inferido (con reservas): zonal, mixto o al hombre."""
    if pairing is None:
        return None
    if pairing >= MARK_MAN_MIN_PAIRING and unpaired_six <= MARK_MAN_MAX_UNPAIRED_SIX:
        return 'al hombre'
    if pairing <= MARK_ZONAL_MAX_PAIRING and unpaired_six >= MARK_ZONAL_MIN_UNPAIRED_SIX:
        return 'zonal'
    return 'mixto'


def corner_organization(v: dict[str, Any], corner: Point) -> dict[str, Any]:
    """Organización defensiva en córner rival (marco del defensor, área propia en x<18)."""
    defs = [p for p in v['own'] + v['own_gk'] if _in_own_box(p)]
    atts = [p for p in v['opp'] if _in_own_box(p)]
    six = [p for p in defs if _in_own_six(p)]
    near_side = corner[1] > PITCH_Y / 2
    paired = sum(1 for a in atts if any(dist(a, d) <= PAIRING_RADIUS_YD for d in defs))
    unpaired_six = sum(1 for d in six if all(dist(a, d) > PAIRING_RADIUS_YD for a in atts))
    pairing = paired / len(atts) if atts else None
    vis = _vis(v, (0.0, BOX_Y[0], OWN_BOX_MAX_X, BOX_Y[1]))
    return {'def_box': len(defs), 'def_six': len(six), 'att_box': len(atts),
            'near_post': sum(1 for p in six if (p[1] > PITCH_Y / 2) == near_side),
            'far_post': sum(1 for p in six if (p[1] > PITCH_Y / 2) != near_side),
            'pairing': rnd(pairing), 'unpaired_six': unpaired_six,
            'marking': marking_style(pairing, unpaired_six), 'roi_vis': rnd(vis),
            'valid': vis >= MIN_ROI_VISIBLE}


def classify_error(kind: str, xpass: Optional[float], under_pressure: bool, forward: bool,
                   opps_pressing: Optional[int]) -> str:
    """Tipología del error (precedencia: duelo > presión > no forzado > arriesgada > otro)."""
    if kind == 'duelo':
        return 'duelo_perdido'
    if under_pressure or (opps_pressing or 0) > 0:
        return 'bajo_presion'
    if kind == 'pase' and xpass is not None and xpass >= XPASS_EASY:
        return 'no_forzado'
    if kind == 'pase' and forward and xpass is not None and xpass < XPASS_RISKY:
        return 'decision_arriesgada'
    return 'otro'


def compact_points(v: dict[str, Any]) -> list[list[float]]:
    """Puntos [x, y, código] con 1 decimal (0 propio, 1 rival, 2 portero propio, 3 rival, 4 actor)."""
    out: list[list[float]] = []
    for key, code in (('own', CODE_OWN), ('opp', CODE_OPP), ('own_gk', CODE_OWN_GK), ('opp_gk', CODE_OPP_GK)):
        for p in v[key]:
            c = CODE_ACTOR if v['actor'] is not None and p == v['actor'] else code
            out.append([round(p[0], COMPACT_DECIMALS), round(p[1], COMPACT_DECIMALS), c])
    return out
