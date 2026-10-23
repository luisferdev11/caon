# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Forma 360 por contexto y ante los cambios (funciones puras sobre los paquetes por partido).

Paquete por partido (lo arma shape360): ``{mid, team, tier, mctx, own: {tabla: filas}, opp: {tabla: filas}}``
con ``mctx`` = shape360_match.match_context (None sin eventos).

* Bloque defensivo por zona del balón (con el rival de los mismos partidos en la misma zona), por marcador,
  por tramo de minuto y por nivel del rival.
* Forma 15 min antes y después de cada momento de cambio (±2 min fuera; ventanas recortadas por el cambio
  vecino), solo si el marcador no cambia en todo el intervalo. Δ = después − antes, con el Δ del rival en
  las mismas ventanas como control de cansancio/contexto. Descriptivo, nunca "efecto".
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any, Optional

from framework import PITCH_X, SUB_GAP_MIN, SUB_WINDOW_MIN, ZONE_DX

from analytics import shape360_match as sm
from analytics.shape360_base import ROUND, Row, mean, values

BLOCK_KEYS = ('altura_sin_balon', 'bloque_largo', 'bloque_ancho', 'bloque_area', 'bloque_entre')
SUB_KEYS = {'altura_sin_balon': 'bloque', 'bloque_ancho': 'bloque', 'bloque_largo': 'bloque',
            'bloque_area': 'bloque', 'altura_con_balon': 'salida', 'vig_media': 'perdidas'}
SUB_MIN_FRAMES = 5        # cuadros válidos mínimos por lado y métrica para publicar un Δ
EXAMPLE_MIN_FRAMES = 2 * SUB_MIN_FRAMES   # un momento de ejemplo necesita ≥10 cuadros de bloque por lado
BALL_X = {'bloque': 'bx', 'salida': 'bx', 'perdidas': 'x'}   # columna con la x del balón por tabla
X_MAX = PITCH_X - 1e-3
SUB_EXAMPLES = 4
SEC_PER_MIN = 60.0
GROUP_AXES = ('por_marcador', 'por_minuto', 'por_rival')

Bundle = dict[str, Any]


def _block_means(rs: Sequence[Row]) -> dict[str, Optional[float]]:
    return {k: mean(values(rs, k)) for k in BLOCK_KEYS}


def _group(items: Iterable[tuple[Any, Row, int]]) -> dict[str, dict[str, Any]]:
    by: dict[str, list[Row]] = defaultdict(list)
    mids: dict[str, set] = defaultdict(set)
    for label, r, mid in items:
        if label is not None:
            by[str(label)].append(r)
            mids[str(label)].add(mid)
    return {k: dict(_block_means(v), n=len(v), partidos=len(mids[k])) for k, v in sorted(by.items())}


def _labels(b: Bundle, r: Row) -> dict[str, Any]:
    mctx = b.get('mctx')
    if mctx is None:
        return {'por_rival': b.get('tier')}
    return {'por_marcador': mctx['state'](r['period'], r['t']), 'por_minuto': mctx['minute_bin'](r['period'], r['t']),
            'por_rival': b.get('tier')}


def block_groups(bundles: Sequence[Bundle]) -> dict[str, Any]:
    """Bloque (cuadros válidos) por zona con referencia rival, y por marcador, minuto y nivel del rival."""
    own = [(b, r) for b in bundles for r in b['own'].get('bloque', []) if r.get('valid')]
    opp = [(b, r) for b in bundles for r in b['opp'].get('bloque', []) if r.get('valid')]
    zones = _group((r.get('zone'), r, b['mid']) for b, r in own)
    ref = _group((r.get('zone'), r, b['mid']) for b, r in opp)
    for z, g in zones.items():
        g.update({'ref_' + k: (ref.get(z) or {}).get(k) for k in BLOCK_KEYS})
    labelled = [(b, r, _labels(b, r)) for b, r in own]
    out: dict[str, Any] = {'por_zona': zones}
    for axis in GROUP_AXES:
        out[axis] = _group((lab.get(axis), r, b['mid']) for b, r, lab in labelled)
    out['cobertura'] = {'cuadros_validos': len(own), 'partidos': len({b['mid'] for b in bundles}),
                        'partidos_sin_eventos': sum(1 for b in bundles if b.get('mctx') is None)}
    return out


# ---------------------------------------------------------------- cambios
def _windows(cl: dict[str, Any], prev_end: Optional[float], next_start: Optional[float]) -> tuple[tuple, tuple]:
    w, g = SUB_WINDOW_MIN * SEC_PER_MIN, SUB_GAP_MIN * SEC_PER_MIN
    lo = cl['start'] - w if prev_end is None else max(cl['start'] - w, prev_end + g)
    hi = cl['end'] + w if next_start is None else min(cl['end'] + w, next_start - g)
    return (lo, cl['start'] - g), (cl['end'] + g, hi)


def _in(rows: Sequence[Row], clock: Any, win: tuple[float, float]) -> list[Row]:
    return [r for r in rows if win[0] <= clock(r['period'], r['t']) <= win[1]]


def ball_col(r: Row, table: str) -> Optional[int]:
    """Columna de 20 yd (0–5, como framework.zone) de la x del balón del registro."""
    x = r.get(BALL_X[table])
    return None if x is None else int(min(max(x, 0.0), X_MAX) // ZONE_DX)


def baselines(bundles: Sequence[Bundle]) -> dict[str, dict[str, dict[Optional[int], float]]]:
    """{lado: {métrica: {columna del balón: media}}} de la ventana, para ajustar la forma por la posición del balón."""
    out: dict[str, dict[str, dict[Optional[int], float]]] = {}
    for side in ('own', 'opp'):
        out[side] = {}
        for key, table in SUB_KEYS.items():
            by: dict[Optional[int], list[float]] = defaultdict(list)
            for b in bundles:
                for r in b[side].get(table, []):
                    v = values([r], key)
                    if v:
                        by[ball_col(r, table)].append(v[0])
            out[side][key] = {c: sum(v) / len(v) for c, v in by.items()}
    return out


def _side(tables: dict[str, list[Row]], clock: Any, win: tuple[float, float],
          base: Optional[dict[str, dict[Optional[int], float]]]) -> dict[str, list[float]]:
    """{métrica: [suma, n]} de los cuadros válidos en una ventana (residuo frente a la base si la hay)."""
    out = {}
    for key, table in SUB_KEYS.items():
        rs = _in(tables.get(table, []), clock, win)
        vals = []
        for r in rs:
            v = values([r], key)
            if v:
                ref = base[key].get(ball_col(r, table), 0.0) if base else 0.0
                vals.append(v[0] - ref)
        out[key] = [sum(vals), len(vals)]
    return out


def _delta(before: dict[str, list[float]], after: dict[str, list[float]],
           min_frames: int = SUB_MIN_FRAMES) -> dict[str, Optional[float]]:
    """Δ = media después − media antes por métrica (None si algún lado tiene < ``min_frames`` cuadros)."""
    out = {}
    for k in SUB_KEYS:
        (s_b, nb), (s_a, na) = before[k], after[k]
        ok = min(nb, na) >= max(min_frames, 1)
        out[k] = round(s_a / na - s_b / nb, ROUND) if ok else None
    return out


def _sub_names(cl: dict[str, Any], names: dict[int, str]) -> list[dict[str, Any]]:
    return [{'sale': names.get(s['off']), 'entra': names.get(s['on']), 'puesto_sale': s['off_pos'],
             'puesto_entra': s['on_pos'], 'tipo': s['tipo']} for s in cl['subs']]


def sub_moments(b: Bundle, base: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Momentos de cambio del equipo: Δ propio y del rival, y las sumas por ventana (``suma``) para agrupar.

    Con ``base`` (``baselines`` de la ventana) cada cuadro se mide contra la media de su columna del balón,
    así el Δ no refleja solo que el balón estuvo en otra zona."""
    mctx = b.get('mctx')
    if mctx is None:
        return []
    clock, cls, out = mctx['clock'], mctx['cambios'], []
    for i, cl in enumerate(cls):
        before, after = _windows(cl, cls[i - 1]['end'] if i else None, cls[i + 1]['start'] if i + 1 < len(cls) else None)
        m: dict[str, Any] = {'mid': b['mid'], 'minuto': cl['minute'], 'tipo': cl['tipo'],
                             'subs': _sub_names(cl, mctx['names'])}
        if sm.goal_between(mctx['goals'], before[0], after[1]):
            out.append(dict(m, excluido=True, motivo='cambió el marcador en la ventana'))
            continue
        bs = base or {}
        suma = {side: (_side(b[side], clock, before, bs.get(side)), _side(b[side], clock, after, bs.get(side)))
                for side in ('own', 'opp')}
        m.update(excluido=False, n_antes=suma['own'][0]['altura_sin_balon'][1],
                 n_despues=suma['own'][1]['altura_sin_balon'][1], delta=_delta(*suma['own']),
                 delta_rival=_delta(*suma['opp']), suma=suma)
        out.append(m)
    return out


def _pooled(ms: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Δ con todos los cuadros de los momentos (después − antes), propio y del rival."""
    out: dict[str, Any] = {}
    for side, name in (('own', 'delta'), ('opp', 'delta_rival')):
        tot = [{k: [0.0, 0] for k in SUB_KEYS}, {k: [0.0, 0] for k in SUB_KEYS}]
        for m in ms:
            for j in (0, 1):
                for k, (s, n) in m['suma'][side][j].items():
                    tot[j][k][0] += s
                    tot[j][k][1] += n
        out[name] = _delta(tot[0], tot[1], min_frames=1)
        if side == 'own':
            out['n_cuadros'] = {k: [tot[0][k][1], tot[1][k][1]] for k in SUB_KEYS}
    return out


def sub_summary(moments: Sequence[dict[str, Any]], window: str) -> dict[str, Any]:
    """Δ agrupado por tipo de cambio (solo marcador estable) y ejemplos con mayor Δ de línea por momento."""
    ok = [m for m in moments if not m.get('excluido')]
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in ok:
        by[m['tipo']].append(m)
    ranked = sorted((m for m in ok if m['delta'].get('altura_sin_balon') is not None
                     and min(m['n_antes'], m['n_despues']) >= EXAMPLE_MIN_FRAMES),
                    key=lambda m: -abs(m['delta']['altura_sin_balon']))
    return {'definicion': 'forma_cambio', 'source': '360', 'window': window, 'n_momentos': len(moments),
            'validos': len(ok), 'excluidos_por_marcador': len(moments) - len(ok),
            'por_tipo': {t: dict(_pooled(v), n=len(v)) for t, v in sorted(by.items())},
            'todos': dict(_pooled(ok), n=len(ok)),
            'ejemplos': [{k: v for k, v in m.items() if k != 'suma'} for m in ranked[:SUB_EXAMPLES]],
            'nota': 'Descriptivo: después − antes en 15 min (±2 min fuera), mismo marcador, con todos los cuadros '
                    'válidos de los momentos, cada uno contra la media de su columna del balón; el Δ del rival en '
                    'las mismas ventanas sirve de control. Solo jugadores visibles.'}
