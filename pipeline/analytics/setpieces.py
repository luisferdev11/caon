# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Balón parado ofensivo y defensivo de una entidad, por ventana (oficial | epilogo | temprano).

Eventos v8: córners (zona de caída, técnica, % cortos, primer contacto, remates por zona, cobradores y
destinos), tiros libres de peligro (x ≥ DANGER_FK_MIN_X: directos e indirectos) y saques de banda de peligro
(x ≥ DANGER_THROW_MIN_X). Posesiones ``an_``: xG de balón parado a favor, en contra y diferencial (mismo
criterio que el KPI 7: Σ xG de posesiones nacidas de un balón parado de peligro, sin penales). 360: la
organización en córner rival se toma tal cual de ``shape360.corners`` (un solo cálculo por métrica).
Cada evento viene en el marco de su equipo; lo del rival se pasa al marco del atacante con ``to_frame``.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Optional  # noqa: UP035 - Python 3.9

import framework as fw
from extract import corner_target

from analytics import register
from analytics.context import band80, seed_for
from analytics.usage import match_names

SP_PATTERN_KIND = {'From Corner': 'corner', 'From Free Kick': 'fk', 'From Throw In': 'throw'}
CORNER_ZONES = ('corto', 'primer_palo', 'centro_area_chica', 'segundo_palo', 'punto_penal', 'fuera_area')
LABELS_ES = {'corto': 'Córner en corto', 'primer_palo': 'Primer palo', 'centro_area_chica': 'Centro del área chica',
             'segundo_palo': 'Segundo palo', 'punto_penal': 'Punto penal', 'fuera_area': 'Fuera del área',
             'area_chica': 'Área chica', 'zona_remate': 'Zona de remate', 'resto_area': 'Resto del área',
             'sin_dato': 'Sin dato', 'corner': 'Córner', 'fk': 'Tiro libre', 'throw': 'Saque de banda',
             'atacante': 'Atacante', 'defensor': 'Defensor'}
TECHNIQUE_ES = {'Inswinging': 'Cerrado', 'Outswinging': 'Abierto', 'Straight': 'Recto'}
CONTACT_TYPES = {'Ball Receipt*', 'Clearance', 'Shot', 'Interception', 'Goal Keeper', 'Block', 'Miscontrol',
                 'Pass', 'Ball Recovery', 'Dribble', 'Carry'}
SHORT_CORNER_YD = fw.SHORT_CORNER_YD
DEAD_BALL_OUTCOMES = {'Out', 'Pass Offside', 'Unknown', 'Injury Clearance'}
CONTACT_SCAN_EVENTS = fw.CONTACT_SCAN_EVENTS
LONG_PASS_LENGTH = 99.0      # longitud ficticia para reutilizar extract.corner_target en un punto cualquiera
TOP_N = fw.SETPIECES_TOP_N
PCT = 100.0
NO_AN = 'sin extractos de posesión (an_) en la ventana'
NO_360 = 'sin córners rivales con cuadro 360 válido en la ventana'
XG_UNIT = 'xG por partido (sin penales)'
LOWER_BOUND = 'jugadores visibles (cota inferior)'


# ---------------------------------------------------------------- geometría
def shot_zone(loc: Optional[list]) -> str:
    """Zona de remate en el marco del atacante: área chica, zona de remate, resto del área o fuera."""
    if not loc:
        return 'sin_dato'
    x, y = loc[0], loc[1]
    lo, hi = fw.SHOOTING_ZONE_Y
    if x >= fw.SIX_YARD_MIN_X and lo <= y <= hi:
        return 'area_chica'
    if x >= fw.BOX_MIN_X and lo <= y <= hi:
        return 'zona_remate'
    return 'resto_area' if fw.in_box(loc) else 'fuera_area'


def landing_zone(loc: list, corner_y: float) -> str:
    """Zona de caída (= extract.corner_target sin la regla de córner corto), normalizada al lado y=0."""
    fake = {'pass': {'length': LONG_PASS_LENGTH, 'end_location': loc[:2]}, 'location': [fw.PITCH_X, corner_y]}
    return CORNER_ZONES[corner_target(fake)]


# ---------------------------------------------------------------- eventos de un partido
def _name(obj: Optional[dict]) -> Optional[str]:
    return (obj or {}).get('name')


def _team(e: dict) -> Optional[int]:
    return (e.get('team') or {}).get('id')


def _shot_rec(e: dict, kind: str) -> dict[str, Any]:
    s = e.get('shot') or {}
    return {'tipo': kind, 'zona': shot_zone(e.get('location')), 'xg': float(s.get('statsbomb_xg') or 0.0),
            'gol': _name(s.get('outcome')) == 'Goal', 'cabeza': _name(s.get('body_part')) == 'Head',
            'jugador': (e.get('player') or {}).get('id'), 'jugador_nombre': _name(e.get('player'))}


def _is_sp_shot(e: dict) -> bool:
    return (_name(e.get('type')) == 'Shot' and _name(e.get('play_pattern')) in SP_PATTERN_KIND
            and _name((e.get('shot') or {}).get('type')) != 'Penalty')


def _is_contact(e: dict) -> bool:
    """Toque real del balón: excluye recepciones fallidas y reanudaciones (saque de meta, banda, falta)."""
    typ = _name(e.get('type'))
    if typ not in CONTACT_TYPES or not e.get('location'):
        return False
    if typ == 'Ball Receipt*' and (e.get('ball_receipt') or {}).get('outcome'):
        return False
    return not (typ == 'Pass' and (e.get('pass') or {}).get('type'))


def first_contact(after: list[dict], attacker: Optional[int], corner: dict) -> Optional[dict[str, str]]:
    """Primer toque tras un córner centrado: quién lo gana y dónde (marco del atacante).

    None si el córner es corto o sale del campo sin que nadie lo toque.
    """
    p = corner.get('pass') or {}
    if (p.get('length') or 0) < SHORT_CORNER_YD or _name(p.get('outcome')) in DEAD_BALL_OUTCOMES:
        return None
    for e in after[:CONTACT_SCAN_EVENTS]:
        if not _is_contact(e):
            continue
        ours = _team(e) == attacker
        loc = fw.to_frame(e['location'], flip=not ours)
        return {'equipo': 'atacante' if ours else 'defensor', 'zona': landing_zone(loc, corner['location'][1])}
    return None


def _corner_rec(e: dict, after: list[dict], shots: list[dict]) -> dict[str, Any]:
    p = e.get('pass') or {}
    short = (p.get('length') or 0) < SHORT_CORNER_YD
    return {'cobrador': (e.get('player') or {}).get('id'), 'cobrador_nombre': _name(e.get('player')),
            'destino': (p.get('recipient') or {}).get('id') if p.get('outcome') is None else None,
            'destino_nombre': _name(p.get('recipient')) if p.get('outcome') is None else None,
            'zona': CORNER_ZONES[corner_target(e)] if p.get('end_location') and p.get('length') is not None
            else 'sin_dato',
            'tecnica': TECHNIQUE_ES.get(_name(p.get('technique')) or '', 'Sin dato'), 'corto': short,
            'contacto': first_contact(after, _team(e), e), 'remates': shots}


def _possession_shots(events: list[dict], team: Optional[int], possession: Any) -> list[dict]:
    return [_shot_rec(s, SP_PATTERN_KIND.get(_name(s.get('play_pattern')), 'otro')) for s in events
            if _is_sp_shot(s) and _team(s) == team and s.get('possession') == possession]


def _restart(e: dict) -> Optional[str]:
    """Tipo de reanudación de peligro de un evento (córner, tiro libre x≥80, banda x≥90) o None."""
    typ, loc = _name(e.get('type')), e.get('location') or [0, 0]
    kind = _name((e.get('pass') or {}).get('type')) if typ == 'Pass' else _name((e.get('shot') or {}).get('type'))
    by_kind = {'Corner': 'corner', 'Free Kick': 'fk', 'Throw-in': 'throw'}
    sp = by_kind.get(kind or '')
    if sp is None or (typ == 'Shot' and sp != 'fk'):
        return None
    return sp if fw.is_danger_sp(sp, loc) else None


def match_records(events: list[dict], team_id: int) -> dict[str, dict[str, list]]:
    """Registros de balón parado de peligro de un partido: {'own'|'opp': {corners, fks, throws, sp_shots}}."""
    evs = sorted(events, key=lambda e: e.get('index', 0))
    out: dict[str, dict[str, list]] = {s: {'corners': [], 'fks': [], 'throws': [], 'sp_shots': []}
                                       for s in ('own', 'opp')}
    for i, e in enumerate(evs):
        side = out['own' if _team(e) == team_id else 'opp']
        if _is_sp_shot(e):
            side['sp_shots'].append(_shot_rec(e, SP_PATTERN_KIND[_name(e.get('play_pattern'))]))
        kind = _restart(e)
        if kind is None:
            continue
        shots = _possession_shots(evs, _team(e), e.get('possession'))
        if kind == 'corner':
            side['corners'].append(_corner_rec(e, evs[i + 1:], shots))
        elif kind == 'fk':
            direct = _name(e.get('type')) == 'Shot'
            side['fks'].append({'cobrador': (e.get('player') or {}).get('id'),
                                'cobrador_nombre': _name(e.get('player')), 'directo': direct,
                                'remates': [_shot_rec(e, 'fk')] if direct else shots})
        else:
            side['throws'].append({'cobrador': (e.get('player') or {}).get('id'), 'remates': shots})
    return out


# ---------------------------------------------------------------- agregados
def _pct(num: float, den: float) -> Optional[float]:
    return round(PCT * num / den, 1) if den else None


def _r(v: Optional[float]) -> Optional[float]:
    return None if v is None else round(v, fw.ROUND_DIGITS)


def _top(pairs: Iterable[tuple], names: dict) -> list[dict[str, Any]]:
    """[(id, nombre del evento)] → los TOP_N más frecuentes con apodo si existe."""
    counts: Counter = Counter()
    label: dict = {}
    for pid, name in pairs:
        if pid is None:
            continue
        counts[pid] += 1
        label[pid] = names.get(pid) or name or str(pid)
    return [{'nombre': label[pid], 'n': n} for pid, n in counts.most_common(TOP_N)]


def _shots_summary(shots: list[dict]) -> dict[str, Any]:
    return {'n': len(shots), 'xg': _r(sum(s['xg'] for s in shots)), 'goles': sum(s['gol'] for s in shots),
            'cabeza_pct': _pct(sum(s['cabeza'] for s in shots), len(shots)),
            'por_zona': [{'zona': z, 'n': n} for z, n in Counter(s['zona'] for s in shots).most_common()]}


def corner_summary(corners: list[dict], names: dict, n_matches: int) -> dict[str, Any]:
    """Córners de un lado: entrega, técnica, primer contacto, remates, cobradores y destinos."""
    n = len(corners)
    contacts = [c['contacto'] for c in corners if c['contacto']]
    shots = [s for c in corners for s in c['remates']]
    return {
        'n': n, 'por_partido': _r(n / n_matches) if n_matches else None,
        'corto_pct': _pct(sum(c['corto'] for c in corners), n),
        'entrega': [{'zona': z, 'n': k, 'pct': _pct(k, n)} for z, k in Counter(c['zona'] for c in corners).most_common()],
        'tecnica': [{'tecnica': t, 'n': k} for t, k in Counter(c['tecnica'] for c in corners).most_common()],
        'primer_contacto': {'n': len(contacts),
                            'ganado_pct': _pct(sum(c['equipo'] == 'atacante' for c in contacts), len(contacts)),
                            'zonas': [{'zona': z, 'n': k} for z, k in Counter(c['zona'] for c in contacts).most_common()]},
        'remates': _shots_summary(shots), 'xg_por_corner': _r(sum(s['xg'] for s in shots) / n) if n else None,
        'cobradores': _top(((c['cobrador'], c['cobrador_nombre']) for c in corners), names),
        'destinos': _top(((c['destino'], c['destino_nombre']) for c in corners), names),
        'rematadores': _top(((s['jugador'], s['jugador_nombre']) for s in shots), names),
    }


def fk_summary(fks: list[dict], names: dict) -> dict[str, Any]:
    """Tiros libres de peligro: directos (remate) e indirectos (centro/pase y remates de la posesión)."""
    direct = [f for f in fks if f['directo']]
    indirect = [f for f in fks if not f['directo']]
    return {'n': len(fks), 'directos': _shots_summary([s for f in direct for s in f['remates']]),
            'indirectos': dict(_shots_summary([s for f in indirect for s in f['remates']]), n_jugadas=len(indirect)),
            'cobradores': _top(((f['cobrador'], f['cobrador_nombre']) for f in fks), names)}


def throw_summary(throws: list[dict]) -> dict[str, Any]:
    """Saques de banda en x ≥ DANGER_THROW_MIN_X (solo análisis)."""
    with_shot = [t for t in throws if t['remates']]
    return {'n': len(throws), 'con_remate_pct': _pct(len(with_shot), len(throws)),
            'xg': _r(sum(s['xg'] for t in throws for s in t['remates']))}


def vulnerable_zones(shots: list[dict]) -> list[dict[str, Any]]:
    """Zonas desde donde remata el rival a balón parado (marco del rival), ordenadas por xG."""
    acc: dict[str, dict[str, float]] = {}
    for s in shots:
        z = acc.setdefault(s['zona'], {'remates': 0, 'xg': 0.0, 'goles': 0})
        z['remates'] += 1
        z['xg'] += s['xg']
        z['goles'] += s['gol']
    rows = [{'zona': k, 'remates': int(v['remates']), 'xg': _r(v['xg']), 'goles': int(v['goles'])}
            for k, v in acc.items()]
    return sorted(rows, key=lambda r: -r['xg'])


# ---------------------------------------------------------------- posesiones an_ (KPI 7)
def possession_sp(an: dict, team_id: int) -> dict[str, dict[str, dict[str, float]]]:
    """xG, jugadas y goles de posesiones nacidas de un balón parado de peligro, por lado y tipo."""
    out: dict[str, dict[str, dict[str, float]]] = {'own': {}, 'opp': {}}
    for p in an.get('possessions') or []:
        sp = p.get('sp')
        if not sp or not sp.get('danger'):
            continue
        acc = out['own' if p.get('team') == team_id else 'opp'].setdefault(sp['type'], {'n': 0, 'xg': 0.0, 'goles': 0})
        acc['n'] += 1
        acc['xg'] += float(p.get('xg') or 0.0)
        acc['goles'] += sum(bool(s.get('goal')) and not s.get('penalty') for s in p.get('shots') or [])
    return out


def _by_type(per_match: list[dict], side: str) -> dict[str, Any]:
    tot: dict[str, dict[str, float]] = {}
    for m in per_match:
        for kind, v in m[side].items():
            t = tot.setdefault(kind, {'n': 0, 'xg': 0.0, 'goles': 0})
            for k in t:
                t[k] += v[k]
    return {k: {'n': int(v['n']), 'xg': _r(v['xg']), 'goles': int(v['goles']),
                'xg_por_jugada': _r(v['xg'] / v['n']) if v['n'] else None} for k, v in tot.items()}


def _xg_records(per_match: list[dict], window: str, seed: int) -> dict[str, dict[str, Any]]:
    """Registros bp_ofensivo, bp_defensivo y bp_diferencial (por partido, banda bootstrap 80 %)."""
    n = len(per_match)
    series = {
        'bp_ofensivo': [sum(v['xg'] for v in m['own'].values()) for m in per_match],
        'bp_defensivo': [sum(v['xg'] for v in m['opp'].values()) for m in per_match],
    }
    series['bp_diferencial'] = [a - b for a, b in zip(series['bp_ofensivo'], series['bp_defensivo'])]
    out = {}
    for mid, vals in series.items():
        value = sum(vals) / n if n else None
        extra = {'ci': band80(vals, seed)} if n else {}
        out[mid] = fw.metric(mid, value, n, XG_UNIT, 'eventos', window, motivo=NO_AN, **extra)
    return out


# ---------------------------------------------------------------- payload
def table_rows(f360: dict, table: str) -> list[dict]:
    """Tabla en columnas de un extracto ``f360_`` → lista de dicts."""
    tab = (f360.get('tables') or {}).get(table) or {}
    return [dict(zip(tab.get('cols') or [], r)) for r in tab.get('rows') or []]


def corner_org(f360s: list[tuple[dict, int]], window: str) -> dict[str, Any]:
    """Organización propia en córner rival (filas ``corner_def`` válidas del equipo; misma regla que shape360)."""
    rows = [r for f, team in f360s for r in table_rows(f, 'corner_def') if r.get('team') == team and r.get('valid')]
    if not rows:
        return fw.metric('corner_def', None, 0, LOWER_BOUND, '360', window, motivo=NO_360)
    pairing = [float(r['pairing']) for r in rows if r.get('pairing') is not None]
    return {'id': 'corner_def', 'n': len(rows), 'unit': LOWER_BOUND, 'source': '360', 'window': window,
            'marcaje': dict(Counter(r.get('marking') or 'sin_dato' for r in rows)),
            'defensores_area': _r(sum(r['def_box'] for r in rows) / len(rows)),
            'defensores_area_chica': _r(sum(r['def_six'] for r in rows) / len(rows)),
            'emparejamiento_pct': _r(PCT * sum(pairing) / len(pairing)) if pairing else None,
            'nota': 'Marca inferida por emparejamiento (≤1.5 yd); tentativa. Jugadores visibles (cota inferior).'}


def window_payload(items: list[dict], window: str, seed: int = 0,
                   f360s: Optional[list[tuple[dict, int]]] = None) -> dict[str, Any]:
    """``items``: [{'events', 'an', 'team_id', 'names'}] de una ventana → balón parado ofensivo y defensivo."""
    recs = [match_records(it['events'], it['team_id']) for it in items if it.get('events')]
    names: dict = {}
    for it in items:
        names.update(it.get('names') or {})
    per_match = [possession_sp(it['an'], it['team_id']) for it in items if it.get('an')]
    xg = _xg_records(per_match, window, seed)
    n_ev = len(recs)

    def side(key: str) -> dict[str, list]:
        return {k: [r for m in recs for r in m[key][k]] for k in ('corners', 'fks', 'throws', 'sp_shots')}
    own, opp = side('own'), side('opp')
    return {
        'n_partidos': len(items), 'cobertura': {'eventos': n_ev, 'an': len(per_match), '360': len(f360s or [])},
        'ofensivo': {'xg_bp': xg['bp_ofensivo'], 'por_tipo': _by_type(per_match, 'own'),
                     'corners': corner_summary(own['corners'], names, n_ev),
                     'tiros_libres': fk_summary(own['fks'], names), 'saques_banda': throw_summary(own['throws']),
                     'remates': _shots_summary(own['sp_shots'])},
        'defensivo': {'xg_bp': xg['bp_defensivo'], 'por_tipo': _by_type(per_match, 'opp'),
                      'corners': corner_summary(opp['corners'], {}, n_ev),
                      'tiros_libres': fk_summary(opp['fks'], {}), 'saques_banda': throw_summary(opp['throws']),
                      'zonas_vulnerables': vulnerable_zones(opp['sp_shots']),
                      'organizacion_360': corner_org(f360s or [], window)},
        'diferencial': xg['bp_diferencial'],
        'nota': 'Balón parado de peligro: todos los córners, tiros libres en x≥80 y saques de banda en x≥90. '
                'Zonas en el marco del equipo que cobra; penales excluidos.',
    }


def build(ctx: Any) -> dict[str, Any]:
    """Contrato analytics: payload por ventana con eventos, ``an_``, alineaciones (apodos) y 360."""
    wins: dict[str, Any] = {}
    for window in fw.WINDOWS:
        rows = [r for r in ctx.matches if r.get('window') == window]
        if not rows:
            continue
        items, f360s = [], []
        for r in rows:
            items.append({'events': ctx.load_events(r['id']), 'an': ctx.load_an(r['id']),
                          'team_id': r['team_id'], 'names': match_names(ctx, r['id'])})
            f = ctx.load_f360(r['id'])
            if f:
                f360s.append((f, r['team_id']))
        wins[window] = window_payload(items, window, seed_for(ctx, window), f360s)
    return {'ventanas': wins, 'etiquetas': LABELS_ES,
            'marco': 'zonas en el marco del equipo que cobra (ataca hacia x=120)'}


register('setpieces', build)
