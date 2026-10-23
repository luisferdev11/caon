# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Jugadas peligrosas concedidas (tema 'dangerous', id ``jugada_peligrosa_concedida``). Implementación propia.

Una jugada es una posesión rival (sin tanda de penales) con al menos un tiro. Orden: gol → xG de la posesión
1-Π(1-xg) (sin penales; en la lista de penales, con ellos) → OBV máximo de una acción rival → fecha (la más
antigua primero). Tres listas por ventana: juego abierto (por defecto), balón parado y penales, top 10 cada una.
Etiquetas: penal, balón parado, transición (+ pérdida propia costosa que la originó), ataque establecido.
Coordenadas en el marco del protagonista: defiende la portería IZQUIERDA. Sin nombres de jugadores rivales.
"""
from __future__ import annotations

import json
import math
from typing import Any, Optional

import framework as fw

from analytics import a4_common as ac
from analytics import a4_facts, register
from analytics import dangerous_detail as dd
from analytics.dangerous_detail import MAX_ACTIONS, possession_actions

TOP_N = fw.DANGEROUS_TOP_N
PAYLOAD_MAX_BYTES = fw.DANGEROUS_PAYLOAD_MAX_BYTES
CATEGORIES = ('juego_abierto', 'balon_parado', 'penales')
SP_ORIGINS = frozenset({'corner', 'fk', 'throw'})
SP_PATTERNS = frozenset({'From Corner', 'From Free Kick', 'From Throw In'})
TRIM_ORDER = ('foto', 'acciones')
FRAME_NOTE = 'Protagonista defiende la portería izquierda (x=0); el rival ataca hacia la izquierda.'
ORDER_NOTE = 'gol → xG de la posesión (sin penales) → OBV máximo rival → fecha'


def possession_xg(shots: list[dict[str, Any]], with_penalties: bool = False) -> float:
    """1-Π(1-xg) sobre los tiros (sin penales salvo ``with_penalties``)."""
    xs = [float(s.get('xg') or 0.0) for s in shots if with_penalties or not s.get('penalty')]
    return round(1.0 - math.prod(1.0 - x for x in xs), 4) if xs else 0.0


def category(p: dict[str, Any]) -> str:
    """juego_abierto | balon_parado | penales."""
    if any(s.get('penalty') for s in p['shots']):
        return 'penales'
    if p.get('sp') or p['origin']['type'] in SP_ORIGINS or any(s.get('pattern') in SP_PATTERNS for s in p['shots']):
        return 'balon_parado'
    return 'juego_abierto'


def tags(p: dict[str, Any], cat: str, loss: Optional[dict[str, Any]]) -> list[str]:
    if cat == 'penales':
        return ['penal']
    if cat == 'balon_parado':
        return ['balon_parado']
    if p['origin']['type'] == 'regain_open':
        return ['transicion'] + (['tras_perdida_costosa'] if loss and loss.get('costosa') else [])
    return ['ataque_establecido']


def _shots(p: dict[str, Any]) -> list[dict[str, Any]]:
    return [{'x': r[0], 'y': r[1], 'xg': r[2], 'gol': bool(r[3]), 'penal': bool(r[4])}
            for r in (a4_facts.shot_row(s, True) for s in p['shots'])]


def candidates(row: dict[str, Any], an: dict[str, Any], facts: dict[str, Any]) -> list[dict[str, Any]]:
    """Posesiones rivales con tiro de un partido, ya en el marco del protagonista."""
    us, out = row['team_id'], []
    links, obv_max = facts.get('perdida_por_posesion_rival') or {}, facts.get('obv_max_rival') or {}
    for p in a4_facts.live_possessions(an):
        if p['team'] == us or not p['shots']:
            continue
        key = a4_facts.pkey(p['period'], p['id'])
        cat, loss = category(p), links.get(key)
        last_t = max(s.get('t', p['t0']) for s in p['shots'])
        out.append({'match_id': row['id'], 'fecha': row.get('date'), 'rival': row.get('opponent'),
                    'local': row.get('venue'), 'marcador_final': row.get('score'), 'periodo': p['period'],
                    'posesion': p['id'], 'categoria': cat, 'etiquetas': tags(p, cat, loss),
                    'bp_tipo': (p.get('sp') or {}).get('type') or (p['origin']['type'] if cat == 'balon_parado'
                                                                    else None),
                    'gol': any(s.get('goal') for s in p['shots']),
                    'xg_posesion': possession_xg(p['shots'], with_penalties=cat == 'penales'),
                    'obv_max': obv_max.get(key, 0.0), 'duracion_s': round(last_t - p['t0']),
                    'tiros': _shots(p), 'perdida_previa': dict(loss) if loss else None})
    return out


def rank(plays: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gol → xG de la posesión → OBV máximo → fecha (más antigua primero)."""
    return sorted(plays, key=lambda p: (not p['gol'], -p['xg_posesion'], -p['obv_max'], p.get('fecha') or ''))


def _attach(ctx: Any, tops: dict[str, list[dict[str, Any]]], rows: list[dict[str, Any]]) -> None:
    """Acciones, foto, nombres de nuestros jugadores y textos (eventos cargados una vez por partido)."""
    team_of = {r['id']: r['team_id'] for r in rows}
    plays = [p for cat in CATEGORIES for p in tops[cat]]
    cache: dict[int, list[dict[str, Any]]] = {}
    for p in plays:
        mid = p['match_id']
        if mid not in cache:
            cache[mid] = a4_facts.live_events(ctx.load_events(mid) or [])
        p['acciones'] = possession_actions(cache[mid], p['periodo'], p['posesion'], team_of[mid])
        p['minuto'] = next((a['min'] for a in reversed(p['acciones']) if a['accion'] == 'Tiro'), None)
        p['foto'] = dd.photo(dd.last_shot_event(cache[mid], p['periodo'], p['posesion']))
    _own_names(ctx, plays, rows)
    for p in plays:
        p['hecho'] = dd.fact_text(p)
        p['interpretacion'] = dd.interpretation_text(p)


def _own_names(ctx: Any, plays: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    """Apodos de nuestros jugadores (pérdida de origen y acciones); los rivales nunca llevan nombre."""
    pids = {p['perdida_previa']['jugador'] for p in plays if p['perdida_previa']}
    pids |= {a['player_id'] for p in plays for a in p['acciones'] if a.get('player_id')}
    names = ac.player_names(rows, pids, getattr(ctx, 'load_lineups', ac.load_lineups))
    for p in plays:
        if p['perdida_previa']:
            p['perdida_previa']['jugador'] = names.get(p['perdida_previa']['jugador']) or None
        for a in p['acciones']:
            if a.get('player_id'):
                a['jugador'] = names.get(a['player_id']) or a.get('jugador')


def _summary(rec: ac.Recorder, plays: list[dict[str, Any]], m: int) -> dict[str, Any]:
    by_cat = {c: [p for p in plays if p['categoria'] == c] for c in CATEGORIES}
    lethal = sum(1 for p in plays if p['gol'] and 'tras_perdida_costosa' in p['etiquetas'])
    return {
        'jugadas_por_partido': rec('jugada_peligrosa_concedida', ac.ratio(len(plays), m), m,
                                   'posesiones rivales con tiro por partido'),
        'xg_por_tipo': {c: rec('xg_concedido', ac.ratio(sum(p['xg_posesion'] for p in ps), m), m,
                               'xG de posesión por partido', scope=f'jugadas:{c}') for c, ps in by_cat.items()},
        'goles_por_tipo': {c: sum(p['gol'] for p in ps) for c, ps in by_cat.items()},
        'por_etiqueta': {t: sum(t in p['etiquetas'] for p in by_cat['juego_abierto'])
                         for t in ('transicion', 'tras_perdida_costosa', 'ataque_establecido')},
        'goles_tras_perdida': rec('perdida_letal', lethal, m, 'goles concedidos tras pérdida propia (total)',
                                  scope='goles_concedidos'),
    }


def window_payload(ctx: Any, wf: dict[str, Any], window: str) -> dict[str, Any]:
    rows, plays = wf['rows'], []
    for row, facts in zip(rows, wf['facts']):
        an = ctx.load_an(row['id'])
        if an:
            plays.extend(candidates(row, an, facts))
    tops = {c: rank([p for p in plays if p['categoria'] == c])[:TOP_N] for c in CATEGORIES}
    _attach(ctx, tops, rows)
    rec = ac.Recorder(ctx.entity_id, window)
    return dict({'n_partidos': len(rows), 'resumen': _summary(rec, plays, len(rows))}, **tops)


def _size(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, allow_nan=False).encode('utf-8'))


def fit_budget(payload: dict[str, Any], limit: int = PAYLOAD_MAX_BYTES) -> dict[str, Any]:
    """Si excede ``limit``, quita fotos y luego acciones de todas las jugadas (anotando la razón)."""
    for key in TRIM_ORDER:
        if _size(payload) <= limit:
            break
        for win in payload['ventanas'].values():
            for cat in CATEGORIES:
                for p in win.get(cat) or []:
                    p[key] = None
        payload.setdefault('recortes', []).append(f'{key}: omitido por tamaño (> {limit} B)')
    return payload


def build(ctx: Any) -> dict[str, Any]:
    """Payload por ventana: top juego abierto / balón parado / penales + resumen."""
    wins = ac.window_facts(ctx)
    payload = {'marco': FRAME_NOTE, 'orden': ORDER_NOTE, 'top_n': TOP_N, 'max_acciones': MAX_ACTIONS,
               'ventanas': {w: window_payload(ctx, wf, w) for w, wf in wins.items()}}
    return fit_budget(payload)


register('dangerous', build)
