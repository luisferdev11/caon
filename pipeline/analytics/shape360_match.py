# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Contexto de un partido desde los eventos v8 para cruzar con los registros 360 (funciones puras).

Reloj continuo (el añadido del primer tiempo no se encima con el segundo), marcador por momento visto
por un equipo, cambios con el puesto de quien sale y de quien entra, y el tipo de cada cambio
(mismo puesto / ofensivo / defensivo) por línea del puesto. Sin tanda de penales.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Optional

from extract import ts
from framework import SHOOTOUT_PERIOD, SUB_GAP_MIN, minute_bin

PERIOD_START_S = {1: 0.0, 2: 2700.0, 3: 5400.0, 4: 6300.0}   # reloj nominal de StatsBomb por periodo
SUB_CLUSTER_S = SUB_GAP_MIN * 60.0   # cambios a ≤2 min (la franja excluida) forman un solo momento de cambio
LINE_GK, LINE_DEF, LINE_MID, LINE_FWD = 0, 1, 2, 3
SUB_TYPES = ('mismo_puesto', 'ofensivo', 'defensivo', 'mixto', 'sin_puesto')


def _tname(e: dict[str, Any]) -> str:
    return (e.get('type') or {}).get('name') or ''


def clock(events: Sequence[dict[str, Any]]) -> dict[int, float]:
    """Desfase por periodo para un reloj continuo: suma de lo jugado en los periodos previos."""
    last: dict[int, float] = {}
    for e in events:
        p = e.get('period') or 1
        last[p] = max(last.get(p, 0.0), ts(e))
    offsets, acc = {}, 0.0
    for p in sorted(last):
        offsets[p] = acc
        acc += max(0.0, last[p] - PERIOD_START_S.get(p, 0.0))
    return offsets


def elapsed(offsets: dict[int, float], period: int, t: float) -> float:
    """Segundos jugados al instante (period, t) en el reloj continuo."""
    return offsets.get(period, 0.0) + t - PERIOD_START_S.get(period, 0.0)


def goals(events: Sequence[dict[str, Any]], offsets: dict[int, float]) -> list[tuple[float, int]]:
    """[(segundo continuo, equipo que suma)] con autogoles ('Own Goal For'); sin tanda de penales."""
    out = []
    for e in events:
        p = e.get('period') or 1
        if p >= SHOOTOUT_PERIOD or 'team' not in e:
            continue
        name = _tname(e)
        is_goal = name == 'Own Goal For' or (
            name == 'Shot' and ((e.get('shot') or {}).get('outcome') or {}).get('name') == 'Goal')
        if is_goal:
            out.append((elapsed(offsets, p, ts(e)), e['team']['id']))
    return sorted(out)


def score_state(goal_list: Sequence[tuple[float, int]], at: float, team: int) -> str:
    """ganando / empatando / perdiendo de ``team`` antes del instante ``at``."""
    gf = sum(1 for t, k in goal_list if t < at and k == team)
    ga = sum(1 for t, k in goal_list if t < at and k != team)
    return 'ganando' if gf > ga else ('perdiendo' if gf < ga else 'empatando')


def goal_between(goal_list: Sequence[tuple[float, int]], lo: float, hi: float) -> bool:
    """¿Hubo gol de cualquiera en [lo, hi]?"""
    return any(lo <= t <= hi for t, _ in goal_list)


def position_line(name: Optional[str]) -> Optional[int]:
    """Línea del puesto StatsBomb: 0 portero, 1 defensa (incluye carrileros), 2 medio, 3 ataque."""
    if not name:
        return None
    if name == 'Goalkeeper':
        return LINE_GK
    if 'Back' in name:
        return LINE_DEF
    if 'Midfield' in name:
        return LINE_MID
    if 'Wing' in name or 'Forward' in name or 'Striker' in name:
        return LINE_FWD
    return None


def sub_type(off_line: Optional[int], on_line: Optional[int]) -> str:
    """Tipo de cambio por la línea de quien entra frente a la de quien sale."""
    if off_line is None or on_line is None:
        return 'sin_puesto'
    if on_line == off_line:
        return 'mismo_puesto'
    return 'ofensivo' if on_line > off_line else 'defensivo'


def _first_positions(events: Sequence[dict[str, Any]]) -> dict[int, str]:
    pos: dict[int, str] = {}
    for e in events:
        pid = (e.get('player') or {}).get('id')
        name = (e.get('position') or {}).get('name')
        if pid is not None and name and _tname(e) != 'Substitution':
            pos.setdefault(pid, name)
    return pos


def substitutions(events: Sequence[dict[str, Any]], team: int, offsets: dict[int, float]) -> list[dict[str, Any]]:
    """Cambios de ``team`` con el puesto de quien sale (evento) y el primero de quien entra."""
    first = _first_positions(events)
    out = []
    for e in events:
        if _tname(e) != 'Substitution' or (e.get('team') or {}).get('id') != team:
            continue
        off, on = e['player']['id'], e['substitution']['replacement']['id']
        off_pos, on_pos = (e.get('position') or {}).get('name'), first.get(on)
        out.append({'t': elapsed(offsets, e['period'], ts(e)), 'period': e['period'], 'minute': e['minute'],
                    'off': off, 'on': on, 'off_pos': off_pos, 'on_pos': on_pos,
                    'tipo': sub_type(position_line(off_pos), position_line(on_pos))})
    return sorted(out, key=lambda s: s['t'])


def cluster_subs(subs: Sequence[dict[str, Any]], gap: float = SUB_CLUSTER_S) -> list[dict[str, Any]]:
    """Agrupa cambios a ≤``gap`` s del primero del grupo; tipo 'mixto' si los tipos difieren."""
    groups: list[list[dict[str, Any]]] = []
    for s in subs:
        if groups and s['t'] - groups[-1][0]['t'] <= gap:
            groups[-1].append(s)
        else:
            groups.append([s])
    out = []
    for g in groups:
        kinds = {s['tipo'] for s in g}
        out.append({'start': g[0]['t'], 'end': g[-1]['t'], 'minute': g[0]['minute'], 'subs': g,
                    'tipo': kinds.pop() if len(kinds) == 1 else 'mixto'})
    return out


def player_names(events: Sequence[dict[str, Any]]) -> dict[int, str]:
    """{id: nombre} de los jugadores que aparecen en eventos."""
    out: dict[int, str] = {}
    for e in events:
        p = e.get('player') or {}
        if p.get('id') is not None and p.get('name'):
            out.setdefault(p['id'], p['name'])
    return out


def match_context(events: Optional[Sequence[dict[str, Any]]], team: int) -> Optional[dict[str, Any]]:
    """Paquete por partido: reloj, goles, cambios agrupados, nombres y funciones de marcador/tramo."""
    if not events:
        return None
    offsets = clock(events)
    goal_list = goals(events, offsets)

    def state(period: int, t: float) -> str:
        return score_state(goal_list, elapsed(offsets, period, t), team)

    def mbin(period: int, t: float) -> Optional[str]:
        return minute_bin(int(t // 60), period)

    return {'offsets': offsets, 'goals': goal_list, 'names': player_names(events),
            'cambios': cluster_subs(substitutions(events, team, offsets)),
            'state': state, 'minute_bin': mbin, 'clock': (lambda p, t: elapsed(offsets, p, t))}

