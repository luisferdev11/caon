# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Hechos por partido y equipo para ofensiva, defensa y transiciones (A4). Funciones puras.

``match_facts(mid, an, events, f360)`` → ``{team_id: hechos}``. Cada bloque de hechos tiene ``n`` (conteos
sumables entre partidos: ventanas, equipos-temporada de referencia) más listas de detalle (tiros, jugadores).
``merge`` suma conteos y concatena listas. Coordenadas: cada equipo en su marco de ataque (x → 120); los tiros
concedidos se voltean con ``framework.to_frame`` para que el protagonista defienda la portería izquierda.
La tanda de penales (period 5) queda fuera de todo.
"""
from __future__ import annotations

import copy
from collections import defaultdict
from typing import Any, Optional

import extract_360 as x360
import framework as fw
import sequences

from analytics import a4_transition_facts as trf

Event = dict[str, Any]
RESTART_PASS_TYPES = frozenset({'Goal Kick', 'Corner', 'Free Kick', 'Throw-in', 'Kick Off'})
LONG_PASS_YD = 35.0          # pase largo (convención StatsBomb "long ball": ≥ 35 yd)
GK_POSITION = 'Goalkeeper'
ORIGIN_GROUP = {'gk': 'portero', 'keeper': 'portero', 'regain_open': 'robo'}
OBV_GROUP = {'Pass': 'pase', 'Carry': 'conduccion', 'Dribble': 'conduccion', 'Shot': 'tiro',
             'Goal Keeper': 'portero'}
ON_BALL = frozenset({'Pass', 'Carry', 'Dribble', 'Shot'})
PPDA_ACTIONS = frozenset({'Interception', 'Foul Committed', 'Dribbled Past'})  # + Duel de tipo Tackle
BANDS = ('alta', 'bloque_medio', 'bajo')
MERGE_SKIP = frozenset({'perdida_por_posesion_rival', 'obv_max_rival'})


# ---------------------------------------------------------------- utilidades
def band(x: float) -> str:
    """Fase de presión por la ubicación del balón en el marco propio (alta ≥80, bloque medio 40–80, bajo <40)."""
    if x >= fw.THIRD_FINAL_MIN_X:
        return 'alta'
    return 'bloque_medio' if x >= fw.THIRD_OWN_MAX_X else 'bajo'


def live_events(events: list[Event]) -> list[Event]:
    """Eventos sin tanda de penales, en orden de índice."""
    return sorted((e for e in events if e.get('period', 1) < fw.SHOOTOUT_PERIOD), key=lambda e: e.get('index', 0))


def live_possessions(an: dict[str, Any]) -> list[dict[str, Any]]:
    """Posesiones del extracto an_ sin tanda de penales."""
    return [p for p in an.get('possessions') or [] if p.get('period', 1) < fw.SHOOTOUT_PERIOD]


def pkey(period: int, poss: int) -> str:
    """Clave de posesión dentro de un partido: 'periodo:posesión'."""
    return f'{period}:{poss}'


def _pass_type(e: Event) -> Optional[str]:
    return ((e.get('pass') or {}).get('type') or {}).get('name')


def _completed(e: Event) -> bool:
    body = e.get(e['type']['name'].lower()) or {}
    return (body.get('outcome') or {}).get('name') not in sequences.FAILED


def is_prog(e: Event) -> bool:
    """Acción progresiva del framework (``prog``), sin la primera acción de un balón parado."""
    return _pass_type(e) not in RESTART_PASS_TYPES and sequences._is_prog(e)  # definición única de sequences


def enters_box(pe: list[Event], team: int) -> bool:
    """La posesión lleva el balón al área: pase/conducción completados que terminan dentro, o tiro sin penal."""
    for e in pe:
        if e['team']['id'] != team:
            continue
        name = e['type']['name']
        if name == 'Shot' and ((e.get('shot') or {}).get('type') or {}).get('name') != 'Penalty':
            return True
        end = (e.get('pass') or e.get('carry') or {}).get('end_location') if name in ('Pass', 'Carry') else None
        if end and _completed(e) and fw.in_box(end):
            return True
    return False


def shot_row(s: dict[str, Any], flip: bool) -> list[Any]:
    xy = fw.to_frame([s['x'], s['y']], flip)
    return [round(xy[0], 1), round(xy[1], 1), round(float(s.get('xg') or 0.0), 3), int(bool(s.get('goal'))),
            int(bool(s.get('penalty')))]


def _in_shooting_zone(s: dict[str, Any]) -> bool:
    lo, hi = fw.SHOOTING_ZONE_Y
    return s['x'] >= fw.BOX_MIN_X and lo <= s['y'] <= hi


# ---------------------------------------------------------------- tiros (an_)
def shot_counts(poss: list[dict[str, Any]], suffix: str = '') -> dict[str, Any]:
    """Tiros sin penal, xG, goles, tiros en zona de remate y penales de una lista de posesiones."""
    shots = [s for p in poss for s in p['shots']]
    np_ = [s for s in shots if not s.get('penalty')]
    return {f'tiros_np{suffix}': len(np_), f'xg_np{suffix}': sum(float(s['xg'] or 0.0) for s in np_),
            f'goles_np{suffix}': sum(bool(s['goal']) for s in np_),
            f'tiros_zona{suffix}': sum(_in_shooting_zone(s) for s in np_),
            f'penales{suffix}': len(shots) - len(np_)}


def origin_counts(poss: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Posesiones, tiros sin penal, xG y goles por tipo de origen."""
    out: dict[str, dict[str, float]] = {}
    for p in poss:
        row = out.setdefault(p['origin']['type'], {'posesiones': 0, 'tiros': 0, 'xg': 0.0, 'goles': 0})
        np_ = [s for s in p['shots'] if not s.get('penalty')]
        row['posesiones'] += 1
        row['tiros'] += len(np_)
        row['xg'] += sum(float(s['xg'] or 0.0) for s in np_)
        row['goles'] += sum(bool(s['goal']) for s in np_)
    return out


# ---------------------------------------------------------------- ofensiva
def _buildup(own: list[dict[str, Any]]) -> dict[str, Any]:
    """Salida limpia (x<40 → x≥60) por grupo de origen y progresión limpia (x<60 → x≥80), juego abierto."""
    s_lo, s_hi = fw.SALIDA_LIMPIA
    g_lo, g_hi = fw.PROGRESION_LIMPIA
    sal = {k: {'n': 0, 'ok': 0} for k in ('total', 'portero', 'robo', 'otro')}
    prg = {'n': 0, 'ok': 0}
    for p in own:
        loc = p['origin'].get('loc')
        if p.get('sp') or not loc:
            continue
        if loc[0] < s_lo:
            for k in ('total', ORIGIN_GROUP.get(p['origin']['type'], 'otro')):
                sal[k]['n'] += 1
                sal[k]['ok'] += int(p['max_x'] >= s_hi)
        if loc[0] < g_lo:
            prg['n'] += 1
            prg['ok'] += int(p['max_x'] >= g_hi)
    return {'salida': sal, 'progresion': prg}


def _goalkeeper(tev: list[Event]) -> dict[str, int]:
    """Pases del portero: saques de puerta y en juego, cuántos largos (≥ LONG_PASS_YD)."""
    out = {'gk_saque': 0, 'gk_saque_largo': 0, 'gk_juego': 0, 'gk_juego_largo': 0}
    for e in tev:
        if e['type']['name'] != 'Pass' or (e.get('position') or {}).get('name') != GK_POSITION:
            continue
        kind = 'gk_saque' if _pass_type(e) == 'Goal Kick' else ('gk_juego' if _pass_type(e) is None else None)
        if kind:
            out[kind] += 1
            out[kind + '_largo'] += int(float(e['pass'].get('length') or 0.0) >= LONG_PASS_YD)
    return out


def _obv(tev: list[Event]) -> dict[str, Any]:
    """OBV (obv_total_net) por tipo de acción y por zona 6×3 de inicio (acciones con balón)."""
    by = {'pase': 0.0, 'conduccion': 0.0, 'tiro': 0.0, 'portero': 0.0, 'otras': 0.0, 'total': 0.0}
    zones: dict[str, float] = defaultdict(float)
    for e in tev:
        v = float(e.get('obv_total_net') or 0.0)
        name = e['type']['name']
        by[OBV_GROUP.get(name, 'otras')] += v
        by['total'] += v
        if name in ('Pass', 'Carry', 'Dribble') and 'location' in e:
            zones[str(fw.zone(e['location']))] += v
    return {'obv': by, 'obv_zona': dict(zones)}


def offense_counts(own: list[dict[str, Any]], opp: list[dict[str, Any]], tev: list[Event],
                   pev: dict[str, list[Event]], team: int) -> dict[str, Any]:
    """Conteos ofensivos de un equipo en un partido."""
    prog = [e for e in tev if e['type']['name'] in ('Pass', 'Carry') and 'location' in e and is_prog(e)]
    out: dict[str, Any] = {'posesiones': len(own), 'prog': len(prog),
                           'prog_pase': sum(e['type']['name'] == 'Pass' for e in prog),
                           'prog_conduccion': sum(e['type']['name'] == 'Carry' for e in prog),
                           'f3': sum(p.get('n_final_third') or 0 for p in own),
                           'f3_rival': sum(p.get('n_final_third') or 0 for p in opp),
                           'posesiones_area': sum(enters_box(pev.get(pkey(p['period'], p['id']), []), team)
                                                  for p in own),
                           'origen': origin_counts(own)}
    out.update(_buildup(own), **_goalkeeper(tev), **shot_counts(own), **_obv(tev))
    return out


def prog_by_player(tev: list[Event]) -> dict[int, int]:
    """Acciones progresivas por jugador."""
    out: dict[int, int] = defaultdict(int)
    for e in tev:
        if e['type']['name'] in ('Pass', 'Carry') and 'location' in e and e.get('player') and is_prog(e):
            out[e['player']['id']] += 1
    return dict(out)


# ---------------------------------------------------------------- defensa
def _is_def_action(e: Event) -> bool:
    name = e['type']['name']
    if name == 'Duel':
        return ((e.get('duel') or {}).get('type') or {}).get('name') == 'Tackle'
    return name in PPDA_ACTIONS


def _is_regain(e: Event) -> bool:
    name = e['type']['name']
    if name == 'Ball Recovery':
        return not (e.get('ball_recovery') or {}).get('recovery_failure')
    if name == 'Interception':
        return ((e.get('interception') or {}).get('outcome') or {}).get('name') not in sequences.FAILED
    return False


def _pressing(tev: list[Event], rev: list[Event]) -> dict[str, Any]:
    press = {b: 0 for b in BANDS}
    acts = {b: 0 for b in BANDS}
    rival = {b: 0 for b in BANDS}
    for e in tev:
        if 'location' not in e:
            continue
        if e['type']['name'] == 'Pressure':
            press[band(e['location'][0])] += 1
            acts[band(e['location'][0])] += 1
        elif _is_def_action(e):
            acts[band(e['location'][0])] += 1
    for e in rev:
        if e['type']['name'] in ON_BALL and 'location' in e:
            rival[band(fw.to_frame(e['location'], True)[0])] += 1
    return {'presiones': press, 'acciones_def': acts, 'acciones_rival': rival,
            'contrapresiones': sum(e['type']['name'] == 'Pressure' and bool(e.get('counterpress')) for e in tev),
            'ppda_pases': sum(e['type']['name'] == 'Pass' and 'location' in e and e['location'][0] < fw.PPDA_OPP_MAX_X
                              and _pass_type(e) not in RESTART_PASS_TYPES for e in rev),
            'ppda_acciones': sum(_is_def_action(e) and 'location' in e and e['location'][0] >= fw.PPDA_DEF_MIN_X
                                 for e in tev)}


def _regains(tev: list[Event], own: list[dict[str, Any]]) -> dict[str, Any]:
    xs = [e['location'][0] for e in tev if _is_regain(e) and 'location' in e]
    zones: dict[str, int] = defaultdict(int)
    for e in tev:
        if _is_regain(e) and 'location' in e:
            zones[str(fw.zone(e['location']))] += 1

    def shot_after(p: dict[str, Any], min_x: float) -> bool:
        loc = p['origin'].get('loc')
        return (p['origin']['type'] == 'regain_open' and bool(loc) and loc[0] >= min_x
                and any(s.get('t', p['t0']) - p['t0'] <= fw.OUTCOME_WINDOW_S for s in p['shots']))
    return {'robos': {'total': len(xs), 'campo_rival': sum(x >= fw.REC_CAMPO_RIVAL_X for x in xs),
                      'alta': sum(x >= fw.REC_ALTA_X for x in xs)},
            'robos_zona': dict(zones),
            'robos_tiro': {'campo_rival': sum(shot_after(p, fw.REC_CAMPO_RIVAL_X) for p in own),
                           'alta': sum(shot_after(p, fw.REC_ALTA_X) for p in own)}}


def defense_counts(own: list[dict[str, Any]], opp: list[dict[str, Any]], tev: list[Event], rev: list[Event],
                   pev: dict[str, list[Event]], rival_id: Optional[int]) -> dict[str, Any]:
    """Conteos defensivos de un equipo en un partido (presión, PPDA, robos, lo concedido)."""
    out = _pressing(tev, rev)
    out.update(_regains(tev, own), **shot_counts(opp, '_c'))
    out['posesiones_c'] = len(opp)
    out['x_tiros_np_c'] = sum(fw.PITCH_X - s['x'] for p in opp for s in p['shots'] if not s.get('penalty'))
    out['posesiones_area_c'] = sum(enters_box(pev.get(pkey(p['period'], p['id']), []), rival_id) for p in opp)
    out['origen_c'] = origin_counts(opp)
    return out


# ---------------------------------------------------------------- partido
def _team_ids(an: dict[str, Any], evs: list[Event]) -> list[int]:
    ids = [t for t in (an.get('home'), an.get('away')) if t is not None]
    if len(ids) == 2:
        return ids
    seen = [e['team']['id'] for e in evs if e.get('team')]
    return sorted(set(seen) | set(ids))


def _group_events(evs: list[Event]) -> dict[str, list[Event]]:
    out: dict[str, list[Event]] = defaultdict(list)
    for e in evs:
        out[pkey(e['period'], e.get('possession', 0))].append(e)
    return out


def match_facts(mid: int, an: dict[str, Any], events: list[Event],
                f360: Optional[dict[str, Any]] = None) -> dict[int, dict[str, Any]]:
    """Hechos de los dos equipos de un partido."""
    evs = live_events(events)
    poss = live_possessions(an)
    pev = _group_events(evs)
    losses = x360.find_losses(evs)
    out = {}
    teams = _team_ids(an, evs)
    for team in teams:
        rival = next((t for t in teams if t != team), None)
        own = [p for p in poss if p['team'] == team]
        opp = [p for p in poss if p['team'] != team]
        tev = [e for e in evs if e['team']['id'] == team]
        rev = [e for e in evs if e['team']['id'] != team]
        tr = trf.transition_facts(team, poss, [lo for lo in losses if lo['team'] == team], f360)
        out[team] = {
            'n': {'partidos': 1, 'off': offense_counts(own, opp, tev, pev, team),
                  'def': defense_counts(own, opp, tev, rev, pev, rival), 'tr': tr['n']},
            'tiros': [shot_row(s, False) for p in own for s in p['shots']],
            'tiros_c': [shot_row(s, True) for p in opp for s in p['shots']],
            'prog_jugador': prog_by_player(tev), 'perdida_jugador': tr['por_jugador'],
            'perdida_por_posesion_rival': tr['enlace'],
            'obv_max_rival': trf.max_obv_by_possession(rev, opp),
        }
    return out


# ---------------------------------------------------------------- suma
def _add(dst: Any, src: Any) -> Any:
    if isinstance(src, dict):
        for k, v in src.items():
            dst[k] = _add(dst[k], v) if k in dst else copy.deepcopy(v)
        return dst
    if isinstance(src, list):
        return dst + copy.deepcopy(src)
    if isinstance(src, (int, float)) and not isinstance(src, bool):
        return dst + src
    return dst


def merge(facts: list[dict[str, Any]]) -> dict[str, Any]:
    """Suma conteos (dicts anidados) y concatena listas; omite los enlaces propios de cada partido."""
    out: dict[str, Any] = {}
    for f in facts:
        _add(out, {k: v for k, v in f.items() if k not in MERGE_SKIP})
    return out
