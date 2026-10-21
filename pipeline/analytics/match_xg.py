# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Primitivas de tiros y xG de un partido real, y datos de la ficha de partido (sin sorteos).

Lo usa ``analytics.replay``; no se registra como tema. Los tiros de la tanda de penales se excluyen, los
penales se separan del juego abierto y los autogoles cuentan como goles fijos del equipo beneficiado.
"""
from __future__ import annotations

from typing import Any, Optional

import framework as fw

BIG_CHANCE_XG = 0.30           # "gran ocasión": tiro con xG >= 0.30

ON_BALL = ('Pass', 'Carry', 'Dribble', 'Shot')
Event = dict[str, Any]


def tname(ev: Event) -> str:
    """Nombre del tipo de evento StatsBomb."""
    return (ev.get('type') or {}).get('name', '')


def team_of(ev: Event) -> Optional[int]:
    """Id del equipo del evento."""
    return (ev.get('team') or {}).get('id')


def in_play(ev: Event) -> bool:
    """Fuera de la tanda de penales."""
    return ev.get('period', 1) != fw.SHOOTOUT_PERIOD


def is_penalty(ev: Event) -> bool:
    return ((ev.get('shot') or {}).get('type') or {}).get('name') == 'Penalty'


def shot_xg(ev: Event) -> float:
    return float((ev.get('shot') or {}).get('statsbomb_xg') or 0.0)


def is_goal(ev: Event) -> bool:
    return ((ev.get('shot') or {}).get('outcome') or {}).get('name') == 'Goal'


def team_shots(events: list[Event], team_id: int) -> list[Event]:
    """Tiros del equipo en juego (sin tanda de penales)."""
    return [e for e in events if tname(e) == 'Shot' and team_of(e) == team_id and in_play(e)]


def own_goals_for(events: list[Event], team_id: int) -> int:
    """Autogoles a favor de team_id (StatsBomb: 'Own Goal For' lleva el equipo beneficiado)."""
    return sum(1 for e in events if tname(e) == 'Own Goal For' and team_of(e) == team_id and in_play(e))


def team_chances(events: list[Event], team_id: int) -> dict[str, Any]:
    """Probabilidad de gol por posesión 1-Π(1-xg) sin penales; penales aparte; autogoles fijos."""
    by_poss: dict[Any, float] = {}
    pens: list[float] = []
    for e in team_shots(events, team_id):
        if is_penalty(e):
            pens.append(shot_xg(e))
            continue
        key = (e.get('period'), e.get('possession'))
        by_poss[key] = 1.0 - (1.0 - by_poss.get(key, 0.0)) * (1.0 - shot_xg(e))
    return {'open': list(by_poss.values()), 'pens': pens, 'own_goals': own_goals_for(events, team_id)}


def field_tilt(events: list[Event], team_id: int) -> Optional[float]:
    """Acciones con balón propias en el último tercio ÷ (propias + rival); igual que el simulador."""
    own = riv = 0
    for e in events:
        loc = e.get('location')
        if tname(e) in ON_BALL and loc and loc[0] >= fw.THIRD_FINAL_MIN_X and in_play(e):
            if team_of(e) == team_id:
                own += 1
            else:
                riv += 1
    return own / (own + riv) if own + riv else None


def clock(ev: Event) -> tuple:
    """Orden cronológico real: (periodo, minuto, segundo); el descuento del 1T va antes del 2T."""
    return (int(ev.get('period', 1)), int(ev.get('minute', 0)), int(ev.get('second', 0)))


def _moment(e: Event, side: str, kind: str) -> dict[str, Any]:
    own_goal = kind == 'autogol'
    out = {'periodo': int(e.get('period', 1)), 'minuto': int(e.get('minute', 0)), 'equipo': side, 'tipo': kind,
           'xg': None if own_goal else round(shot_xg(e), 2),
           'jugador': None if own_goal else (e.get('player') or {}).get('name')}
    if not own_goal and is_penalty(e):
        out['penal'] = True
    return out


def moments(events: list[Event], team_id: int, rival: int) -> list[dict[str, Any]]:
    """Goles, grandes ocasiones (xG ≥ 0.30) y autogoles, en orden cronológico (periodo, minuto)."""
    out = []
    for side, tid in (('propio', team_id), ('rival', rival)):
        for e in team_shots(events, tid):
            if is_goal(e) or shot_xg(e) >= BIG_CHANCE_XG:
                out.append((clock(e), _moment(e, side, 'gol' if is_goal(e) else 'gran_ocasion')))
    for e in events:
        if tname(e) == 'Own Goal For' and in_play(e):
            out.append((clock(e), _moment(e, 'propio' if team_of(e) == team_id else 'rival', 'autogol')))
    return [m for _c, m in sorted(out, key=lambda cm: cm[0])]


def xg_timeline(events: list[Event], team_id: int, rival: int) -> dict[str, list]:
    """xG acumulado en columnas {periodo, minuto, propio, rival}: arranque en 0 y un punto por minuto con tiro."""
    shots = sorted(team_shots(events, team_id) + team_shots(events, rival), key=clock)
    acc = {'propio': 0.0, 'rival': 0.0}
    points = [(1, 0, 0.0, 0.0)]
    for e in shots:
        acc['propio' if team_of(e) == team_id else 'rival'] += shot_xg(e)
        row = (int(e.get('period', 1)), int(e.get('minute', 0)), round(acc['propio'], 2), round(acc['rival'], 2))
        if points[-1][:2] == row[:2]:
            points[-1] = row
        else:
            points.append(row)
    cols = list(zip(*points))
    return {'periodo': list(cols[0]), 'minuto': list(cols[1]), 'propio': list(cols[2]), 'rival': list(cols[3])}


def fun_facts(events: list[Event], team_id: int, rival: int) -> list[str]:
    """Tres datos curiosos calculados del partido (texto es-MX)."""
    own, opp = team_shots(events, team_id), team_shots(events, rival)
    best = max(own + opp, key=shot_xg, default=None)
    facts = [f'Tiros: {len(own)} propios contra {len(opp)} del rival.']
    if best is not None:
        quien = 'propia' if team_of(best) == team_id else 'del rival'
        facts.append(f"La ocasión más clara ({quien}) fue al minuto {best.get('minute', 0)}, "
                     f'con {round(100 * shot_xg(best))}% de probabilidad de gol.')
    else:
        facts.append('Ningún equipo remató en todo el partido.')
    tilt = field_tilt(events, team_id)
    facts.append('Sin datos de territorio.' if tilt is None else
                 f'De cada 100 acciones en un último tercio, {round(100 * tilt)} fueron propias.')
    return facts


def sides(meta: dict[str, Any], team_id: int) -> tuple:
    """(rival_id, goles_propios, goles_rival, localía) desde la óptica de team_id."""
    home = meta['home_id'] == team_id
    rival = meta['away_id'] if home else meta['home_id']
    gf, ga = (meta['home_score'], meta['away_score']) if home else (meta['away_score'], meta['home_score'])
    return rival, gf, ga, 'local' if home else 'visita'


def match_card(events: list[Event], meta: dict[str, Any], team_id: int) -> dict[str, Any]:
    """Ficha de partido: marcador, momentos clave, xG acumulado y 3 datos curiosos."""
    rival, gf, ga, _venue = sides(meta, team_id)
    return {'match_id': meta['match_id'], 'marcador': {'propio': gf, 'rival': ga},
            'momentos': moments(events, team_id, rival),
            'xg_acumulado': xg_timeline(events, team_id, rival),
            'datos_curiosos': fun_facts(events, team_id, rival)}
