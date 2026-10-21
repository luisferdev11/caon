# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Hechos de transiciones y pérdidas de un equipo en un partido (A4). Funciones puras.

Pérdidas = ``extract_360.find_losses`` (la siguiente posesión rival nace en juego abierto) con la tipología
única ``frames360.classify_error`` vía ``extract_360.loss_record``. Si hay extracto 360 de la pérdida se usa su
tipo (con contexto 360) y la marca de aislamiento: un tipo 'otro' sin compañero a ≤10 yd pasa a 'aislado'
(misma regla que la vista 360). Costosa = tiro rival ≤15 s tras el robo; letal = gol.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

import extract_360 as x360
import framework as fw
import sequences

Event = dict[str, Any]
ERROR_TYPES = ('no_forzado', 'bajo_presion', 'decision_arriesgada', 'duelo_perdido', 'aislado', 'otro')


def _empty() -> dict[str, int]:
    return {'n': 0, 'costosa': 0, 'letal': 0}


def _bump(row: dict[str, int], costly: bool, lethal: bool) -> None:
    row['n'] += 1
    row['costosa'] += int(costly)
    row['letal'] += int(lethal)


def f360_losses(f360: Optional[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Filas de la tabla 360 'perdidas' por id del evento del error."""
    table = ((f360 or {}).get('tables') or {}).get('perdidas')
    if not table:
        return {}
    return {r['eid']: r for r in x360.rows_as_dicts(table) if r.get('eid')}


def final_type(rec: dict[str, Any], row360: Optional[dict[str, Any]]) -> str:
    """Tipo publicado: el 360 si existe (si no, el de eventos); 'otro' + aislado → 'aislado'."""
    tipo = (row360 or {}).get('tipo') or rec.get('tipo') or 'otro'
    if tipo == 'otro' and (row360 or {}).get('isolated'):
        return 'aislado'
    return tipo


def recovered_quickly(loss: dict[str, Any], poss: list[dict[str, Any]], team: int) -> bool:
    """Contrapresión efectiva: tras el robo rival, la siguiente posesión es propia, nace de robo en ≤5 s."""
    reg = loss['regain']
    t_reg, period = sequences.ts(reg), reg.get('period')
    rival_poss = reg.get('possession')
    for p in poss:
        if p['period'] != period or p['t0'] < t_reg or (p['team'] != team and p['id'] == rival_poss):
            continue
        return (p['team'] == team and p['origin']['type'] == 'regain_open'
                and p['t0'] - t_reg <= fw.COUNTERPRESS_WINDOW_S)
    return False


def _transitions(poss: list[dict[str, Any]]) -> dict[str, Any]:
    """Posesiones nacidas de robo: tiros/xG/goles en la fase de 10 s."""
    out = {'n': 0, 'tiros10': 0, 'xg10': 0.0, 'goles10': 0}
    for p in poss:
        if p['origin']['type'] != 'regain_open':
            continue
        quick = [s for s in p['shots'] if not s.get('penalty')
                 and s.get('t', p['t0']) - p['t0'] <= fw.TRANSITION_PHASE_S]
        out['n'] += 1
        out['tiros10'] += len(quick)
        out['xg10'] += sum(float(s['xg'] or 0.0) for s in quick)
        out['goles10'] += sum(bool(s['goal']) for s in quick)
    return out


def _counters(poss: list[dict[str, Any]]) -> dict[str, Any]:
    """Contraataques (robo x<60 → tiro ≤15 s, marca ``counter`` de sequences)."""
    cs = [p for p in poss if p.get('counter')]
    shots = [s for p in cs for s in p['shots'] if not s.get('penalty')]
    return {'n': len(cs), 'goles': sum(bool(s['goal']) for s in shots),
            'xg': sum(float(s['xg'] or 0.0) for s in shots)}


def _loss_rows(team: int, poss: list[dict[str, Any]], losses: list[dict[str, Any]],
               f360: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    rows360 = f360_losses(f360)
    out = []
    for lo in losses:
        rec = x360.loss_record(lo, {})
        r360 = rows360.get(rec['eid'])
        out.append({'eid': rec['eid'], 'player': rec['player'], 'x': rec['x'], 'y': rec['y'],
                    'tipo': final_type(rec, r360), 'costosa': bool(rec['shot15']), 'letal': bool(rec['goal15']),
                    'rec5': recovered_quickly(lo, poss, team), 'valid360': bool((r360 or {}).get('err_valid')),
                    'isolated': bool((r360 or {}).get('isolated')),
                    'rival_key': f"{lo['regain'].get('period')}:{lo['regain'].get('possession')}"})
    return out


def transition_facts(team: int, poss: list[dict[str, Any]], losses: list[dict[str, Any]],
                     f360: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Conteos de pérdidas (tipo, tercio, zona, jugador), contrapresión efectiva y transiciones en ambos sentidos."""
    rows = _loss_rows(team, poss, losses, f360)
    by_type = {t: _empty() for t in ERROR_TYPES}
    by_third: dict[str, dict[str, int]] = defaultdict(_empty)
    by_zone: dict[str, dict[str, int]] = defaultdict(_empty)
    by_player: dict[int, dict[str, int]] = defaultdict(_empty)
    for r in rows:
        for table, key in ((by_type, r['tipo']), (by_third, fw.third(r['x'])),
                           (by_zone, str(fw.zone([r['x'], r['y']]))), (by_player, r['player'])):
            _bump(table[key], r['costosa'], r['letal'])
    valid = [r for r in rows if r['valid360']]
    own = [p for p in poss if p['team'] == team]
    opp = [p for p in poss if p['team'] != team]
    n = {'perdidas': {'n': len(rows), 'costosa': sum(r['costosa'] for r in rows),
                      'letal': sum(r['letal'] for r in rows), 'rec5': sum(r['rec5'] for r in rows)},
         'por_tipo': by_type, 'por_tercio': dict(by_third), 'por_zona': dict(by_zone),
         'aislado': {'validas': len(valid), 'aisladas': sum(r['isolated'] for r in valid)},
         'transiciones': _transitions(own), 'contras': _counters(own),
         'transiciones_c': _transitions(opp), 'contras_c': _counters(opp)}
    link = {r['rival_key']: {'event_id': r['eid'], 'jugador': r['player'], 'tipo': r['tipo'],
                             'costosa': r['costosa'], 'letal': r['letal'], 'x': r['x'], 'y': r['y']} for r in rows}
    return {'n': n, 'por_jugador': {k: v for k, v in by_player.items() if k is not None}, 'enlace': link}


def max_obv_by_possession(rev: list[Event], opp: list[dict[str, Any]]) -> dict[str, float]:
    """OBV máximo de una acción rival en cada posesión rival con tiro (desempate del ranking de peligro)."""
    keys = {f"{p['period']}:{p['id']}" for p in opp if p['shots']}
    out: dict[str, float] = {}
    for e in rev:
        k = f"{e['period']}:{e.get('possession')}"
        if k in keys:
            out[k] = max(out.get(k, float('-inf')), float(e.get('obv_total_net') or 0.0))
    return {k: round(v, 4) for k, v in out.items()}
