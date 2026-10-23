# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Secuencias ofensivas (posesiones) desde eventos StatsBomb v8, según el marco de ``framework``.

``build_possessions(events, metadata)`` es pura: devuelve {'possessions': [...], 'events_light': {...}, 'rival_shots': {...}}.
Contrato de ejemplo: ``pipeline/fixtures/an_sample.json``.
"""
from __future__ import annotations

import math
from itertools import groupby
from typing import Any, Optional

import framework as fw

ONBALL = {'Pass', 'Carry', 'Dribble', 'Shot'}
ADMIN = {'Foul Committed', 'Foul Won', 'Bad Behaviour', 'Injury Stoppage', 'Substitution', 'Referee Ball-Drop',
         'Tactical Shift', 'Player Off', 'Player On', 'Half Start', 'Half End', 'Starting XI', 'Camera On',
         'Camera off'}
ORIGIN_BY_PATTERN = {'From Goal Kick': 'gk', 'From Throw In': 'throw', 'From Free Kick': 'fk',
                     'From Corner': 'corner', 'From Kick Off': 'kickoff', 'From Keeper': 'keeper'}
OPEN_PATTERNS = {'Regular Play', 'From Counter'}
LOSS_OPEN_PATTERNS = {'Regular Play', 'From Counter', 'From Keeper'}  # = extract.OPEN_RESTARTS
LOSS_BY_PATTERN = {'From Throw In': 'lossXT', 'From Goal Kick': 'lossXG'}  # resto de balón muerto: lossXF
RESTARTS = {'From Goal Kick', 'From Throw In', 'From Free Kick', 'From Corner', 'From Kick Off'}  # su 1.ª acción no es progresiva
SP_KIND = {'From Corner': 'corner', 'From Free Kick': 'fk', 'From Throw In': 'throw'}
REGAIN_TYPES = {'Ball Recovery', 'Interception'}
FAILED = {'Incomplete', 'Out', 'Unknown', 'Pass Offside', 'Lost', 'Lost In Play', 'Lost Out', 'Fail'}
Event = dict[str, Any]


def ts(e: Event) -> float:
    """Segundo del periodo con milisegundos (como extract.ts)."""
    ms = 0.0
    try:
        ms = float('0.' + e['timestamp'].split('.')[1])
    except (KeyError, IndexError, ValueError):
        pass
    return e['minute'] * 60 + e['second'] + ms


def possession_xg(xgs: list[float]) -> float:
    """xG de la posesión: 1-Π(1-xg)."""
    return 1.0 - math.prod(1.0 - x for x in xgs) if xgs else 0.0


def _onball(pe: list[Event], tid: int) -> list[Event]:
    return [e for e in pe if e['type']['name'] in ONBALL and 'location' in e and e['team']['id'] == tid]


def _is_prog(e: Event) -> bool:
    """Pase/conducción progresiva completada (definición 'prog')."""
    kind = e['type']['name'].lower()
    body = e.get(kind) or {}
    end = body.get('end_location')
    if kind not in ('pass', 'carry') or not end or (body.get('outcome') or {}).get('name') in FAILED:
        return False
    x0, y0 = e['location'][:2]
    if kind == 'pass' and fw.in_box(end) and not fw.in_box([x0, y0]):
        return True
    d0 = math.hypot(fw.GOAL[0] - x0, fw.GOAL[1] - y0)
    d1 = math.hypot(fw.GOAL[0] - end[0], fw.GOAL[1] - end[1])
    gain = d0 - d1
    return x0 >= fw.PROG_MIN_START_X and gain >= fw.PROG_MIN_YARDS and gain >= fw.PROG_MIN_REDUCTION * d0


def _reach(e: Event) -> Optional[list[float]]:
    """Destino de un pase o conducción completados (None si falló o no es pase/conducción)."""
    kind = e['type']['name'].lower()
    body = e.get(kind) or {}
    if kind not in ('pass', 'carry') or not body.get('end_location'):
        return None
    return None if (body.get('outcome') or {}).get('name') in FAILED else body['end_location']


def _shot(e: Event) -> dict[str, Any]:
    s = e['shot']
    return {'id': e['id'], 'x': e['location'][0], 'y': e['location'][1], 'xg': s.get('statsbomb_xg') or 0.0,
            'goal': (s.get('outcome') or {}).get('name') == 'Goal',
            'penalty': (s.get('type') or {}).get('name') == 'Penalty',
            'header': (s.get('body_part') or {}).get('name') == 'Head',
            'pattern': e['play_pattern']['name'], 'freeze_frame_ref': e['id'] if s.get('freeze_frame') else None}


def _score_state(goals: dict[int, int], tid: int) -> str:
    mine = goals.get(tid, 0)
    other = sum(v for k, v in goals.items() if k != tid)
    return 'ganando' if mine > other else ('perdiendo' if mine < other else 'empatando')


def _origin(pe: list[Event], tid: int, prev_team: Optional[int]) -> dict[str, Any]:
    pattern = pe[0]['play_pattern']['name']
    kind = ORIGIN_BY_PATTERN.get(pattern, 'other')
    if pattern in OPEN_PATTERNS and prev_team is not None and prev_team != tid:
        kind = 'regain_open'
    first = next((e for e in pe if e['team']['id'] == tid and 'location' in e), None)
    return {'type': kind, 'loc': first['location'][:2] if first else None}


def _loss(last: Event, nxt: Optional[list[Event]]) -> Optional[dict[str, Any]]:
    """Registro de pérdida si la siguiente posesión no administrativa es rival (como extract: tras tiro no hay)."""
    if nxt is None or nxt[0]['possession_team']['id'] == last['team']['id'] or last['type']['name'] == 'Shot':
        return None
    body = last.get('pass') or {}
    pattern = nxt[0]['play_pattern']['name']
    kind = 'lossO' if pattern in LOSS_OPEN_PATTERNS else LOSS_BY_PATTERN.get(pattern, 'lossXF')
    return {'kind': kind,
            'xpass': body.get('pass_success_probability'), 'under_pressure': bool(last.get('under_pressure')),
            'player': (last.get('player') or {}).get('id'), 'event_id': last['id'], 'type': last['type']['name'],
            'costly': False, 'lethal': False}


def _record(pe: list[Event], ctx: dict[str, Any], nxt: Optional[list[Event]]) -> dict[str, Any]:
    """Una posesión con balón del equipo poseedor → registro del contrato."""
    tid = pe[0]['possession_team']['id']
    ob = _onball(pe, tid)
    shots = [_shot(e) for e in ob if e['type']['name'] == 'Shot']
    t0, t1 = ts(pe[0]), ts(pe[-1])
    origin = _origin(pe, tid, ctx['prev_team'])
    transition = origin['type'] == 'regain_open'
    first_shot_t = next((ts(e) for e in ob if e['type']['name'] == 'Shot'), None)
    reach = [r for r in (_reach(e) for e in ob) if r]
    max_x = max([e['location'][0] for e in ob] + [r[0] for r in reach])
    loss = _loss(ob[-1], nxt)
    end_type = 'shot' if ob[-1]['type']['name'] == 'Shot' else ('loss' if loss else 'fin')
    pattern = pe[0]['play_pattern']['name']
    skip = 1 if pattern in RESTARTS else 0   # la jugada que reanuda no cuenta como progresión
    sp = None
    if pattern in SP_KIND:
        sp = {'type': SP_KIND[pattern], 'danger': fw.is_danger_sp(SP_KIND[pattern], ob[0]['location'])}
    return {
        'id': pe[0]['possession'], 'team': tid, 'period': pe[0]['period'], 't0': t0, 't1': t1,
        'minute_bin': fw.minute_bin(pe[0]['minute'], pe[0]['period']),
        'score_state': _score_state(ctx['goals'], tid), 'venue': 'local' if tid == ctx['home'] else 'visitante',
        'origin': origin, 'end': {'type': end_type, 'loc': ob[-1]['location'][:2], 'event_id': ob[-1]['id']},
        'shots': shots, 'xg': possession_xg([s['xg'] for s in shots if not s['penalty']]),
        'obv': round(sum(e.get('obv_total_net') or 0.0 for e in pe if e['team']['id'] == tid), 4),
        'n_passes': sum(e['type']['name'] == 'Pass' for e in ob), 'n_prog': sum(_is_prog(e) for e in ob[skip:]),
        'n_final_third': sum(e['location'][0] >= fw.THIRD_FINAL_MIN_X for e in ob), 'max_x': max_x,
        'box_entry': any(fw.in_box(r) for r in reach) or any(fw.in_box(e['location']) for e in ob) or bool(shots),
        'transition': transition,
        'counter': bool(transition and origin['loc'] and origin['loc'][0] < fw.REC_CAMPO_RIVAL_X
                        and first_shot_t is not None and first_shot_t - t0 <= fw.OUTCOME_WINDOW_S),
        'sp': sp, 'loss': loss,
        'opp_pressures': sum(e['type']['name'] == 'Pressure' and e['team']['id'] != tid for e in pe),
    }


def rival_possession_shots(events: list[Event]) -> dict[str, Any]:
    """Tiros (sin penal ni tanda) que un equipo realiza dentro de una posesión del rival: se excluyen de las posesiones.

    Es una exclusión medible: en los 91 partidos de Jardine fue 1 de 2,241 tiros (xG 0.007 de 216.8, el 0.003 %).
    """
    shots = [e for e in events if e['type']['name'] == 'Shot' and e.get('period', 1) < fw.SHOOTOUT_PERIOD
             and e['team']['id'] != e['possession_team']['id'] and (e['shot'].get('type') or {}).get('name') != 'Penalty']
    return {'n': len(shots), 'xg': round(sum(e['shot'].get('statsbomb_xg') or 0.0 for e in shots), 4)}


def _mark_costly(poss: list[dict[str, Any]]) -> None:
    """Pérdida en juego → costosa si la posesión rival siguiente tira en ≤15 s; letal si es gol."""
    for cur, nxt in zip(poss, poss[1:]):  # noqa: RUF007 - pairwise no existe en 3.9
        loss = cur['loss']
        if not loss or loss['kind'] != 'lossO' or nxt['team'] == cur['team'] or nxt['period'] != cur['period']:
            continue
        quick = [s for s in nxt['shots'] if s.get('t', nxt['t0']) - nxt['t0'] <= fw.OUTCOME_WINDOW_S]
        loss['costly'] = bool(quick)
        loss['lethal'] = any(s['goal'] for s in quick)


def _goals_in(pe: list[Event]) -> list[int]:
    out = []
    for e in pe:
        name = e['type']['name']
        if name == 'Shot' and (e['shot'].get('outcome') or {}).get('name') == 'Goal' or name == 'Own Goal For':
            out.append(e['team']['id'])
    return out


def build_possessions(events: list[Event], metadata: dict[str, Any]) -> dict[str, Any]:
    """Posesiones del contrato + listas ligeras de eventos (presiones, robos, pérdidas, cambios).

    La tanda de penales (``period`` ≥ SHOOTOUT_PERIOD) queda fuera de todo análisis.
    """
    evs = sorted((e for e in events if e.get('period', 1) < fw.SHOOTOUT_PERIOD), key=lambda e: e['index'])
    groups = [list(g) for _, g in groupby(evs, key=lambda e: (e['period'], e['possession']))]
    live = [g for g in groups if _onball(g, g[0]['possession_team']['id'])]
    ctx = {'home': (metadata.get('home_team') or {}).get('home_team_id'), 'goals': {}, 'prev_team': None}
    poss = []
    for i, pe in enumerate(live):
        nxt = live[i + 1] if i + 1 < len(live) else None
        rec = _record(pe, ctx, nxt)
        shot_t = {e['id']: ts(e) for e in pe if e['type']['name'] == 'Shot'}
        for s in rec['shots']:
            s['t'] = shot_t[s['id']]
        poss.append(rec)
        for tid in _goals_in(pe):
            ctx['goals'][tid] = ctx['goals'].get(tid, 0) + 1
        ctx['prev_team'] = rec['team']
    _mark_costly(poss)
    return {'possessions': poss, 'events_light': events_light(evs), 'rival_shots': rival_possession_shots(evs)}


def events_light(evs: list[Event]) -> dict[str, list[dict[str, Any]]]:
    """Eventos sueltos con id para enlazar con 360: presiones, robos, pérdidas, cambios y ajustes tácticos."""
    out: dict[str, list[dict[str, Any]]] = {'pressures': [], 'regains': [], 'losses': [], 'subs': [],
                                            'tactical_shifts': []}
    for e in evs:
        name = e['type']['name']
        base = {'event_id': e['id'], 'team': e['team']['id'], 't': ts(e), 'period': e['period']}
        if name == 'Pressure':
            out['pressures'].append(dict(base, loc=e.get('location'), counterpress=bool(e.get('counterpress'))))
        elif name in REGAIN_TYPES and ((e.get(name.lower().replace(' ', '_')) or {}).get('outcome') or {}).get(
                'name') not in FAILED:
            out['regains'].append(dict(base, loc=e.get('location'), type=name))
        elif name in ('Dispossessed', 'Miscontrol'):
            out['losses'].append(dict(base, loc=e.get('location'), type=name))
        elif name == 'Substitution':
            out['subs'].append(dict(base, off=(e.get('player') or {}).get('id'),
                                    on=((e.get('substitution') or {}).get('replacement') or {}).get('id')))
        elif name == 'Tactical Shift':
            out['tactical_shifts'].append(dict(base, formation=(e.get('tactics') or {}).get('formation')))
    return out
