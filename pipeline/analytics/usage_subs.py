# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Cambios de un partido y su asociación descriptiva con el juego (funciones puras).

Para cada momento de cambio (cambios del mismo equipo a ≤2 min se agrupan, ``shape360_match``) se comparan
dos ventanas de SUB_WINDOW_MIN minutos en reloj continuo: antes (terminando SUB_GAP_MIN antes del primer
cambio) y después (empezando SUB_GAP_MIN tras el último). Solo es elegible si nadie marca entre el inicio de
la ventana previa y el final de la posterior (mismo marcador). Métricas: xG sin penales a favor y en contra,
OBV propio y field tilt. La forma 360 ante los cambios vive en el tema ``shape360`` (un solo cálculo).
Es una asociación descriptiva, nunca un efecto: no controla cansancio, rival ni marcador previo.
"""
from __future__ import annotations

from typing import Any, Optional

import framework as fw
from extract import ts
from sequences import ONBALL

from analytics.shape360_match import elapsed, goal_between, match_context, score_state

MIN_S = 60.0
WINDOW_S = fw.SUB_WINDOW_MIN * MIN_S
GAP_S = fw.SUB_GAP_MIN * MIN_S
FLOW_KEYS = ('xg_favor', 'xg_contra', 'obv', 'field_tilt')
PCT = 100.0
HALFTIME_MINUTE = 45                          # minuto de StatsBomb al reanudar el segundo tiempo


def _tname(e: dict) -> str:
    return (e.get('type') or {}).get('name') or ''


def flow_events(events: list[dict], team_id: int, offsets: dict[int, float]) -> list[tuple]:
    """[(t continuo, propio?, xG sin penal, OBV propio, acción en último tercio?)] sin tanda de penales."""
    out = []
    for e in events:
        period = e.get('period') or 1
        if period >= fw.SHOOTOUT_PERIOD or 'team' not in e:
            continue
        own = e['team'].get('id') == team_id
        shot = e.get('shot') or {}
        xg = float(shot.get('statsbomb_xg') or 0.0) if _tname(e) == 'Shot' and \
            (shot.get('type') or {}).get('name') != 'Penalty' else 0.0
        f3 = _tname(e) in ONBALL and bool(e.get('location')) and e['location'][0] >= fw.THIRD_FINAL_MIN_X
        obv = float(e.get('obv_total_net') or 0.0) if own else 0.0
        out.append((elapsed(offsets, period, ts(e)), own, xg, obv, f3))
    return out


def window_flow(flow: list[tuple], lo: float, hi: float) -> dict[str, Optional[float]]:
    """Totales de una ventana [lo, hi) del reloj continuo."""
    sel = [f for f in flow if lo <= f[0] < hi]
    f3_own = sum(1 for f in sel if f[1] and f[4])
    f3_all = sum(1 for f in sel if f[4])
    return {'xg_favor': sum(f[2] for f in sel if f[1]), 'xg_contra': sum(f[2] for f in sel if not f[1]),
            'obv': sum(f[3] for f in sel), 'field_tilt': PCT * f3_own / f3_all if f3_all else None}


def _delta(before: dict, after: dict) -> dict[str, Optional[float]]:
    return {k: None if before.get(k) is None or after.get(k) is None else after[k] - before[k] for k in before}


def moment_windows(moment: dict, flow: list[tuple], goals: list[tuple[float, int]], end_s: float) -> dict[str, Any]:
    """Ventanas antes/después de un momento de cambio, elegibilidad y Δ (después − antes)."""
    lo_b, hi_b = moment['start'] - GAP_S - WINDOW_S, moment['start'] - GAP_S
    lo_a, hi_a = moment['end'] + GAP_S, moment['end'] + GAP_S + WINDOW_S
    if lo_b < 0 or hi_a > end_s:
        return {'elegible': False, 'motivo': 'ventana_incompleta'}
    if goal_between(goals, lo_b, hi_a):
        return {'elegible': False, 'motivo': 'cambio_marcador'}
    before, after = window_flow(flow, lo_b, hi_b), window_flow(flow, lo_a, hi_a)
    return {'elegible': True, 'antes': before, 'despues': after, 'delta': _delta(before, after)}


def match_substitutions(events: list[dict], team_id: int) -> list[dict[str, Any]]:
    """Momentos de cambio de ``team_id`` con minuto, marcador, tipo y ventanas antes/después."""
    mc = match_context(events, team_id)
    if mc is None:
        return []
    flow = flow_events(events, team_id, mc['offsets'])
    end_s = max((f[0] for f in flow), default=0.0)
    out = []
    for moment in mc['cambios']:
        first = moment['subs'][0]
        out.append({'minuto': moment['minute'], 'estado': score_state(mc['goals'], moment['start'], team_id),
                    'tipo': moment['tipo'], 'n_cambios': len(moment['subs']),
                    'en_descanso': first['period'] == 2 and first['minute'] == HALFTIME_MINUTE,
                    'sale': [s['off'] for s in moment['subs']], 'entra': [s['on'] for s in moment['subs']],
                    'ventanas': moment_windows(moment, flow, mc['goals'], end_s)})
    return out
