# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Detalle de una jugada peligrosa concedida: acciones, foto del tiro y textos "Hecho / Interpretación".

Marco del protagonista: defiende la portería IZQUIERDA. Eventos rivales (en su marco de ataque) se voltean con
``framework.to_frame``; los propios se quedan. Nunca se publican nombres de jugadores rivales.
"""
from __future__ import annotations

from typing import Any, Optional

import framework as fw

MAX_ACTIONS = 15
ACTION_ES = {'Pass': 'Pase', 'Carry': 'Conducción', 'Dribble': 'Regate', 'Shot': 'Tiro',
             'Ball Recovery': 'Recuperación', 'Interception': 'Intercepción', 'Clearance': 'Despeje',
             'Block': 'Bloqueo', 'Duel': 'Duelo', 'Pressure': 'Presión', 'Dispossessed': 'Pérdida por entrada',
             'Miscontrol': 'Mal control', 'Goal Keeper': 'Portero', 'Foul Won': 'Falta recibida'}
SP_ES = {'corner': 'un córner', 'fk': 'un tiro libre', 'throw': 'un saque de banda'}
LOSS_ES = {'no_forzado': 'error no forzado', 'bajo_presion': 'bajo presión', 'decision_arriesgada':
           'decisión arriesgada', 'duelo_perdido': 'duelo perdido', 'aislado': 'jugador aislado', 'otro': 'otra causa'}
THIRD_ES = {'propio': 'en el tercio propio', 'medio': 'en el medio campo', 'final': 'en el último tercio'}


def _xy(loc: list[float], ours: bool) -> list[float]:
    return [round(v, 1) for v in fw.to_frame(loc[:2], not ours)]


def _action(e: dict[str, Any], us: int) -> dict[str, Any]:
    ours = e['team']['id'] == us
    x, y = _xy(e['location'], ours)
    rec: dict[str, Any] = {'accion': ACTION_ES.get(e['type']['name'], 'Otra acción'),
                           'equipo': 'propio' if ours else 'rival', 'x': x, 'y': y,
                           'min': e.get('minute'), 'seg': e.get('second')}
    body = e.get('pass') or e.get('carry') or e.get('shot') or {}
    if body.get('end_location'):
        rec['x_fin'], rec['y_fin'] = _xy(body['end_location'], ours)
    if (e.get('pass') or {}).get('cross'):
        rec['centro'] = True
    if ours and e.get('player'):
        rec['jugador'] = e['player'].get('name')
        rec['player_id'] = e['player'].get('id')
    return rec


def possession_actions(events: list[dict[str, Any]], period: int, poss: int, us: int) -> list[dict[str, Any]]:
    """Hasta MAX_ACTIONS acciones con ubicación de la posesión, terminando en su último tiro."""
    pe = [e for e in sorted(events, key=lambda e: e.get('index', 0))
          if e.get('period') == period and e.get('possession') == poss and e['type']['name'] in ACTION_ES
          and 'location' in e]
    shots = [i for i, e in enumerate(pe) if e['type']['name'] == 'Shot']
    if shots:
        pe = pe[:shots[-1] + 1]
    return [_action(e, us) for e in pe[-MAX_ACTIONS:]]


def last_shot_event(events: list[dict[str, Any]], period: int, poss: int) -> Optional[dict[str, Any]]:
    shots = [e for e in events if e.get('period') == period and e.get('possession') == poss
             and e['type']['name'] == 'Shot']
    return max(shots, key=lambda e: e.get('index', 0)) if shots else None


def photo(shot_ev: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    """Freeze frame del tiro rival (marco del tirador) → marco del protagonista, sin nombres."""
    out = []
    for f in ((shot_ev or {}).get('shot') or {}).get('freeze_frame') or []:
        x, y = _xy(f['location'], False)
        out.append({'x': x, 'y': y, 'equipo': 'rival' if f.get('teammate') else 'propio',
                    'portero': (f.get('position') or {}).get('name') == 'Goalkeeper'})
    return out


def _date_es(iso: Optional[str]) -> str:
    if not iso or len(iso) < 10:
        return 'fecha desconocida'
    return f'{iso[8:10]}/{iso[5:7]}/{iso[:4]}'


def fact_text(play: dict[str, Any]) -> str:
    """Solo lo observado: minuto, rival, fecha, tiros, xG de la posesión, desenlace y pérdida de origen."""
    n = len(play['tiros'])
    minute = f"Min {play['minuto']}' · " if play.get('minuto') is not None else ''
    venue = f", {play['local']}" if play.get('local') else ''
    end = 'terminó en gol' if play['gol'] else 'sin gol'
    txt = (f"{minute}vs {play.get('rival') or 'rival'} ({_date_es(play.get('fecha'))}{venue}): "
           f"{n} {'tiro' if n == 1 else 'tiros'}, xG de la posesión {play['xg_posesion']:.2f}, {end}.")
    loss = play.get('perdida_previa')
    if loss:
        who = loss.get('jugador') or 'un jugador propio'
        txt += (f" Nació de una pérdida de {who} ({LOSS_ES.get(loss.get('tipo'), 'otra causa')}) "
                f"{THIRD_ES.get(fw.third(loss['x']), '')}.")
    return txt


def interpretation_text(play: dict[str, Any]) -> str:
    """Lectura condicionada a las etiquetas (nunca contradice los números del hecho)."""
    tags, secs = play['etiquetas'], play.get('duracion_s')
    quick = '' if secs is None else (' de inmediato' if secs <= 1 else f' en {secs} s')
    if 'penal' in tags:
        return 'Penal concedido: se lista aparte porque su xG no depende de la jugada colectiva.'
    if 'balon_parado' in tags:
        return (f"Llegó desde {SP_ES.get(play.get('bp_tipo'), 'una pelota parada')}: el peligro depende de la "
                'organización defensiva a balón parado y de las segundas jugadas.')
    if 'tras_perdida_costosa' in tags:
        return (f'La jugada nace de una pérdida propia en juego: el rival recuperó y llegó a tiro{quick}, '
                'antes de que el equipo se reorganizara.')
    if 'transicion' in tags:
        return (f'El rival recuperó el balón en juego y llegó a tiro{quick}, antes de que el equipo terminara de '
                'reorganizarse.')
    cross = any(a.get('centro') for a in play.get('acciones') or [])
    how = ' y terminó con un centro al área' if cross else ''
    return f'El rival atacó con el equipo ya organizado{how}: el peligro llegó contra el bloque defensivo.'
