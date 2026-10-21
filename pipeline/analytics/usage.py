# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Uso de plantilla por ventana: XI base y % de minutos, roles en español, formaciones, rotación, momento de
los cambios por marcador y su asociación descriptiva con el juego (``usage_subs``).

Minutos desde las alineaciones v4 (``personnel.players_minutes``); sin alineación, desde los eventos
(Starting XI + Substitution). Nunca se habla de "efecto": los cambios se describen, no se evalúan.
"""
from __future__ import annotations

import json
import pathlib
import statistics
from collections import Counter, defaultdict
from typing import Any, Optional

import framework as fw
from personnel import players_minutes

from analytics import register
from analytics.context import band80, seed_for
from analytics.shape360_match import position_line
from analytics.usage_subs import FLOW_KEYS, match_substitutions

CACHE = pathlib.Path(__file__).resolve().parents[2] / 'data' / 'cache'
XI_SIZE = 11
SQUAD_TOP = 25            # jugadores listados en "plantilla"
ROLES_TOP = 3             # puestos por jugador
FORMATIONS_TOP = 5
PCT = 100.0
POS_ES = {
    'Goalkeeper': 'Portero', 'Right Back': 'Lateral derecho', 'Left Back': 'Lateral izquierdo',
    'Right Wing Back': 'Carrilero derecho', 'Left Wing Back': 'Carrilero izquierdo',
    'Right Center Back': 'Central derecho', 'Left Center Back': 'Central izquierdo',
    'Center Back': 'Central', 'Center Defensive Midfield': 'Contención',
    'Right Defensive Midfield': 'Contención derecha', 'Left Defensive Midfield': 'Contención izquierda',
    'Right Center Midfield': 'Interior derecho', 'Left Center Midfield': 'Interior izquierdo',
    'Center Midfield': 'Mediocentro', 'Right Midfield': 'Volante derecho', 'Left Midfield': 'Volante izquierdo',
    'Center Attacking Midfield': 'Mediapunta', 'Right Attacking Midfield': 'Mediapunta derecho',
    'Left Attacking Midfield': 'Mediapunta izquierdo', 'Right Wing': 'Extremo derecho',
    'Left Wing': 'Extremo izquierdo', 'Center Forward': 'Delantero centro',
    'Right Center Forward': 'Delantero derecho', 'Left Center Forward': 'Delantero izquierdo',
    'Secondary Striker': 'Segundo delantero',
}
LABELS_ES = {'mismo_puesto': 'Mismo puesto', 'ofensivo': 'Ofensivo', 'defensivo': 'Defensivo', 'mixto': 'Mixto',
             'sin_puesto': 'Sin puesto registrado', 'ventana_incompleta': 'Ventana incompleta (cambio muy '
             'temprano o muy tardío)', 'cambio_marcador': 'Hubo gol en las ventanas', 'alineaciones': 'Alineaciones',
             'eventos': 'Eventos', 'ganando': 'Ganando', 'empatando': 'Empatando', 'perdiendo': 'Perdiendo'}
LINE_ES = {0: 'Portero', 1: 'Defensa', 2: 'Medio', 3: 'Ataque'}
FLOW_UNITS = {'xg_favor': 'Δ xG sin penales (15 min)', 'xg_contra': 'Δ xG sin penales concedido (15 min)',
              'obv': 'Δ OBV propio (15 min)', 'field_tilt': 'Δ puntos porcentuales de field tilt'}
NOTE = ('Asociación descriptiva: compara 15 min antes y después de cada momento de cambio (±2 min excluidos, '
        'mismo marcador). No controla cansancio, rival ni contexto; no es un efecto.')


# ---------------------------------------------------------------- IO
def load_lineups(mid: int) -> Optional[list[dict]]:
    """Alineaciones v4 en caché (IO) o None."""
    try:
        return json.loads((CACHE / f'v4_lineups_{mid}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def match_names(ctx: Any, mid: int) -> dict[int, str]:
    """{player_id: apodo o nombre} de ambos equipos del partido, desde las alineaciones."""
    loader = getattr(ctx, 'load_lineups', None) or load_lineups
    out: dict[int, str] = {}
    for team in loader(mid) or []:
        for p in team.get('lineup') or []:
            name = p.get('player_nickname') or p.get('player_name')
            if p.get('player_id') is not None and name:
                out[p['player_id']] = name
    return out


# ---------------------------------------------------------------- un partido
def _tname(e: dict) -> str:
    return (e.get('type') or {}).get('name') or ''


def _team(e: dict) -> Optional[int]:
    return (e.get('team') or {}).get('id')


def formation_text(value: Any) -> Optional[str]:
    """4231 → '4-2-3-1'."""
    return '-'.join(str(value)) if value else None


def minutes_from_events(team_id: int, events: list[dict]) -> list[dict[str, Any]]:
    """Minutos por jugador sin alineación: titulares hasta su salida, suplentes desde su entrada."""
    end = max((e.get('minute') or 0 for e in events), default=0)
    rows: dict[int, dict[str, Any]] = {}
    for e in sorted(events, key=lambda x: x.get('index', 0)):
        if _team(e) != team_id:
            continue
        if _tname(e) == 'Starting XI':
            for p in (e.get('tactics') or {}).get('lineup') or []:
                pos = (p.get('position') or {}).get('name')
                rows[p['player']['id']] = {'player_id': p['player']['id'], 'name': p['player'].get('name'),
                                           'starter': True, 'minutes': end, 'pos': pos, 'from': 0}
        elif _tname(e) == 'Substitution':
            minute, off = e.get('minute') or 0, (e.get('player') or {}).get('id')
            if off in rows:
                rows[off]['minutes'] = minute - rows[off]['from']
            rep = (e.get('substitution') or {}).get('replacement') or {}
            pos = (e.get('position') or {}).get('name')
            rows[rep.get('id')] = {'player_id': rep.get('id'), 'name': rep.get('name'), 'starter': False,
                                   'minutes': max(0, end - minute), 'pos': pos, 'from': minute}
    return [{'player_id': r['player_id'], 'name': r['name'], 'starter': r['starter'], 'minutes': r['minutes'],
             'positions': {r['pos']: r['minutes']} if r['pos'] else {}} for r in rows.values() if r['minutes'] > 0]


def match_usage(team_id: int, events: list[dict], lineups: Optional[list[dict]] = None) -> dict[str, Any]:
    """XI, formación, minutos por jugador y momentos de cambio con sus ventanas (pura)."""
    xi_ev = next((e for e in events if _tname(e) == 'Starting XI' and _team(e) == team_id), None)
    tactics = (xi_ev or {}).get('tactics') or {}
    players = players_minutes(lineups, events, team_id) if lineups else None
    return {'xi': [p['player']['id'] for p in tactics.get('lineup') or []],
            'formacion': formation_text(tactics.get('formation')),
            'players': players if players else minutes_from_events(team_id, events),
            'fuente_minutos': 'alineaciones' if players else 'eventos',
            'cambios': match_substitutions(events, team_id)}


# ---------------------------------------------------------------- agregados
def _r(v: Optional[float], digits: int = fw.ROUND_DIGITS) -> Optional[float]:
    return None if v is None else round(v, digits)


def _accumulate(per: list[dict]) -> dict[int, dict[str, Any]]:
    acc: dict[int, dict[str, Any]] = {}
    for m in per:
        for p in m['players']:
            a = acc.setdefault(p['player_id'], {'name': p['name'], 'minutes': 0.0, 'starts': 0, 'apps': 0,
                                                'pos': Counter()})
            a['minutes'] += p['minutes']
            a['starts'] += bool(p['starter'])
            a['apps'] += 1
            a['pos'].update(p['positions'])
            a['name'] = a['name'] or p['name']
    return acc


def _player_row(pid: int, a: dict, total: float, names: dict) -> dict[str, Any]:
    main = a['pos'].most_common(1)[0][0] if a['pos'] else None
    pos_total = sum(a['pos'].values()) or 1.0
    return {'jugador': names.get(pid) or a['name'], 'id': pid, 'minutos': round(a['minutes']),
            'share_minutos': _r(PCT * a['minutes'] / total, 1) if total else None,
            'titularidades': a['starts'], 'partidos': a['apps'],
            'posicion': POS_ES.get(main, 'Otra') if main else None,
            'linea': LINE_ES.get(position_line(main)) if main else None,
            'roles': [{'posicion': POS_ES.get(k, 'Otra'), 'pct_minutos': _r(PCT * v / pos_total, 1)}
                      for k, v in a['pos'].most_common(ROLES_TOP)]}


def squad(per: list[dict], names: dict) -> dict[str, Any]:
    """XI base (11 con más minutos, ordenados por línea), plantilla y formaciones."""
    acc = _accumulate(per)
    total = sum(max((p['minutes'] for p in m['players']), default=0.0) for m in per)
    ranked = sorted(acc, key=lambda pid: -acc[pid]['minutes'])
    rows = {pid: _player_row(pid, acc[pid], total, names) for pid in ranked[:SQUAD_TOP]}
    line_order = {v: k for k, v in LINE_ES.items()}
    core = sorted(ranked[:XI_SIZE], key=lambda pid: (line_order.get(rows[pid]['linea'], 9), -acc[pid]['minutes']))
    forms = Counter(m['formacion'] for m in per if m['formacion'])
    n_forms = sum(forms.values())
    return {'xi_base': [rows[pid] for pid in core], 'plantilla': [rows[pid] for pid in ranked[:SQUAD_TOP]],
            'formaciones': [{'formacion': f, 'n': k, 'pct': _r(PCT * k / n_forms, 1)}
                            for f, k in forms.most_common(FORMATIONS_TOP)]}


def rotation(per: list[dict], window: str) -> dict[str, Any]:
    """Titulares distintos respecto del partido anterior (orden cronológico)."""
    xis = [m['xi'] for m in per if m['xi']]
    changes = [len(set(b) - set(a)) for a, b in zip(xis, xis[1:])]  # noqa: RUF007 - Python 3.9 sin pairwise
    value = statistics.fmean(changes) if changes else None
    return fw.metric('rotacion', value, len(changes), 'titulares distintos al partido anterior', 'eventos', window,
                     motivo='menos de 2 partidos con XI', titulares_distintos=len({p for x in xis for p in x}))


def _flow_records(moments: list[dict], seed: int, window: str) -> dict[str, Any]:
    out = {}
    for k in FLOW_KEYS:
        vals = [m['ventanas']['delta'][k] for m in moments if m['ventanas']['delta'][k] is not None]
        value = statistics.fmean(vals) if vals else None
        extra = {'ci': band80(vals, seed)} if vals else {}
        out[k] = fw.metric('impacto_cambio', value, len(vals), FLOW_UNITS[k], 'eventos', window,
                           motivo='sin momentos de cambio elegibles', **extra)
    return out


def association(moments: list[dict], seed: int, window: str) -> dict[str, Any]:
    """Δ medio (después − antes) por métrica, por tipo de cambio y forma 360."""
    ok = [m for m in moments if m['ventanas']['elegible']]
    by_type: dict[str, list[dict]] = defaultdict(list)
    for m in ok:
        by_type[m['tipo']].append(m)
    return {'etiqueta': 'asociación descriptiva', 'nota': NOTE, 'n_momentos': len(moments), 'elegibles': len(ok),
            'excluidos': dict(Counter(m['ventanas']['motivo'] for m in moments if not m['ventanas']['elegible'])),
            'metricas': _flow_records(ok, seed, window),
            'por_tipo': {t: {'n': len(ms), **{k: v['value'] for k, v in _flow_records(ms, seed, window).items()}}
                         for t, ms in sorted(by_type.items())},
            'forma_360': {'fuente': 'shape360', 'ver': f'shape360.ventanas.{window}.cambios',
                          'nota': 'Forma del bloque 15 min antes y después de cada cambio, calculada una sola vez '
                                  'en el tema 360 (misma regla de ventanas y marcador).'}}


def substitutions(per: list[dict], seed: int, window: str) -> dict[str, Any]:
    """Momento de los cambios (minuto medio, por marcador y tipo) y su asociación descriptiva."""
    moments = [c for m in per for c in m['cambios']]
    minutes = [c['minuto'] for c in moments for _ in range(c['n_cambios'])]
    firsts = [m['cambios'][0]['minuto'] for m in per if m['cambios']]
    by_state: dict[str, list[dict]] = defaultdict(list)
    for c in moments:
        by_state[c['estado']].append(c)
    n = len(per)
    return {
        'minuto_medio': fw.metric('cambios', statistics.fmean(minutes) if minutes else None, len(minutes), 'minuto',
                                  'eventos', window, motivo='sin cambios registrados'),
        'por_partido': _r(len(minutes) / n, 2) if n else None,
        'primer_cambio_medio': _r(statistics.fmean(firsts), 1) if firsts else None,
        'en_descanso': sum(c['en_descanso'] for c in moments),
        'por_estado': {k: {'n': sum(c['n_cambios'] for c in v),
                           'minuto_medio': _r(statistics.fmean(c['minuto'] for c in v), 1)}
                       for k, v in sorted(by_state.items())},
        'por_tipo': dict(Counter(c['tipo'] for c in moments)),
        'asociacion': association(moments, seed, window),
    }


def summarize(per: list[dict], window: str, seed: int = 0, names: Optional[dict] = None) -> dict[str, Any]:
    """Partidos de una ventana en orden cronológico → uso de plantilla (pura)."""
    out = {'n_partidos': len(per), 'fuente_minutos': dict(Counter(m['fuente_minutos'] for m in per))}
    out.update(squad(per, names or {}))
    out['rotacion'] = rotation(per, window)
    out['cambios'] = substitutions(per, seed, window)
    return out


def build(ctx: Any) -> dict[str, Any]:
    """Contrato analytics: por ventana, partidos en orden de fecha con sus alineaciones."""
    lineup_loader = getattr(ctx, 'load_lineups', None) or load_lineups
    wins: dict[str, Any] = {}
    for window in fw.WINDOWS:
        rows = sorted((r for r in ctx.matches if r.get('window') == window), key=lambda r: r.get('date') or '')
        per, names = [], {}
        for r in rows:
            events = ctx.load_events(r['id'])
            if not events:
                continue
            lineups = lineup_loader(r['id'])
            names.update(match_names(ctx, r['id']))
            per.append(match_usage(r['team_id'], events, lineups))
        if per:
            wins[window] = summarize(per, window, seed_for(ctx, window), names)
    return {'ventanas': wins, 'etiquetas': LABELS_ES}


register('usage', build)
