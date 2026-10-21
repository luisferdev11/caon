# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Motor de etiquetas de estilo: una sola función ``identity(style)`` para tarjetas, etiquetas y mapa.

``style`` son percentiles 0–100 frente a la liga. La tarjeta "Enfoque defensivo" ES el cuadrante del mapa
defensivo, y ninguna etiqueta puede contradecir a una tarjeta o a otra etiqueta (``CONFLICTS``).
"""
from __future__ import annotations

import math
from typing import Any, Optional

NA = 'Datos insuficientes'
HI, LO = 80, 20                 # etiqueta extrema
CENTER_BAND = 9                 # |p-50| < 9 en ambos ejes → "Equilibrado"
VERTICAL_MIN, PATIENT_MAX = 70, 40  # "Directo pero paciente"
TOP_TAGS = 4
QUADRANTS = {
    'off': {'tl': 'Posesión elaborada', 'tr': 'Dominio vertical', 'bl': 'Reactivo', 'br': 'Contragolpe'},
    'dfn': {'tl': 'Bloque medio agresivo', 'tr': 'Presión alta', 'bl': 'Bloque bajo',
            'br': 'Línea alta, presión selectiva'},
}
AXES = {'off': ('Velocidad del ataque', 'Posesión'), 'dfn': ('Altura de línea', 'Intensidad de presión')}
SELECTIVE = 'Presión selectiva: pocas presiones, pero roba pronto (PPDA bajo)'
COMBINED = 'Directo pero paciente'
# (métrica, umbral alto, texto alto, umbral bajo, texto bajo, eje del mapa)
EXTREMES = (
    ('posesion', HI, 'Dueño del balón', LO, 'Cede el balón', 'off'),
    ('linea', HI, 'Línea muy alta', LO, 'Bloque bajo', 'dfn'),
    ('verticalidad', HI, 'Muy vertical', LO, 'Elabora en corto', None),
    ('ritmo', HI, 'Ataques rápidos', LO, 'Ataques pausados', 'off'),
    ('centros', HI, 'Centrador', LO, 'Evita el centro', None),
    ('contragolpe', HI, 'Letal al contragolpe', None, None, 'off'),
    ('presion_alta_tiros', HI, 'Roba y remata', None, None, None),
    ('xga', HI, 'Muy sólido atrás', LO, 'Concede mucho', None),
    ('bp_xg', HI, 'Peligro a balón parado', None, None, None),
    ('saque_largo', 85, 'Portero en largo', 15, 'Sale jugando desde el portero', None),
)
AXIS_OF_TAG = {t: ax for _, _, th, _, tl, ax in EXTREMES for t in (th, tl) if t and ax}
AXIS_OF_TAG.update({'Presión asfixiante': 'dfn', 'Espera al rival': 'dfn', SELECTIVE: 'dfn'})
CONFLICTS = (
    ('Ataques rápidos', 'Ataques pausados'), ('Muy vertical', 'Elabora en corto'),
    ('Pase corto', 'Muy vertical'), ('Pase corto', 'Juego directo'), ('Contragolpe', 'Ataques pausados'),
    ('Dueño del balón', 'Cede el balón'), ('Presión asfixiante', 'Espera al rival'),
    ('Línea muy alta', 'Bloque bajo'), ('Presión alta', 'Espera al rival'), ('Bloque bajo', 'Línea muy alta'),
    ('Posesión elaborada', 'Ataques rápidos'), ('Contragolpe', 'Dueño del balón'),
    ('Muy sólido atrás', 'Concede mucho'), ('Presión asfixiante', SELECTIVE),
)


def _v(s: dict[str, Any], k: str) -> float:
    x = s.get(k)
    return float(x) if isinstance(x, (int, float)) else float('nan')


def _has(s: dict[str, Any], keys: tuple) -> bool:
    return all(isinstance(s.get(k), (int, float)) for k in keys)


def map_points(s: dict[str, Any]) -> dict[str, Optional[list[int]]]:
    """Puntos del mapa: ofensivo (velocidad del ataque, posesión) y defensivo (línea, intensidad de presión)."""
    off = dfn = None
    if _has(s, ('ritmo', 'contragolpe', 'posesion')):
        off = [round((s['ritmo'] + s['contragolpe']) / 2), round(s['posesion'])]
    if _has(s, ('linea', 'volumen_presion', 'presion', 'contrapresion')):
        dfn = [round(s['linea']), round((s['volumen_presion'] + s['presion'] + s['contrapresion']) / 3)]
    return {'off': off, 'dfn': dfn}


def quadrant(mk: str, p: Optional[list[int]]) -> str:
    """Nombre del cuadrante del mapa ``mk`` ('off'|'dfn'); centro → 'Equilibrado'."""
    if not p:
        return NA
    if abs(p[0] - 50) < CENTER_BAND and abs(p[1] - 50) < CENTER_BAND:
        return 'Equilibrado'
    q = QUADRANTS[mk]
    return (q['tr'] if p[0] >= 50 else q['tl']) if p[1] >= 50 else (q['br'] if p[0] >= 50 else q['bl'])


def build_card(s: dict[str, Any]) -> str:
    """Tarjeta "Salida": pase corto solo si no es muy vertical (evita la contradicción histórica)."""
    if not _has(s, ('posesion', 'ritmo', 'contragolpe', 'saque_largo')):
        return NA
    pos, vert = _v(s, 'posesion'), _v(s, 'verticalidad')
    short = pos >= 80 or (pos >= 65 and _v(s, 'ritmo') <= 55)
    if short and not vert >= VERTICAL_MIN:
        return 'Pase corto'
    if short:
        return 'Posesión con pase vertical'
    if pos <= 50 and (_v(s, 'contragolpe') >= 65 or _v(s, 'ritmo') >= 65):
        return 'Contragolpe'
    if _v(s, 'saque_largo') >= 70 and pos <= 45:
        return 'Juego directo'
    return 'Equilibrado'


def attack_card(s: dict[str, Any]) -> str:
    """Tarjeta "Ataque": por bandas, por dentro o mixto según centros."""
    c = _v(s, 'centros')
    if math.isnan(c):
        return NA
    return 'Por bandas' if c >= 67 else ('Por dentro' if c <= 33 else 'Mixto')


def _candidate_tags(s: dict[str, Any]) -> list[tuple]:
    out = []
    vol, prs = _v(s, 'volumen_presion'), _v(s, 'presion')
    if vol >= 75 and not prs < 60:
        out.append((vol - 50, 'Presión asfixiante', 'volumen_presion'))
    elif prs >= 80 and vol <= 40:
        out.append((prs - 50, SELECTIVE, 'presion'))
    elif vol <= 25 and _v(s, 'linea') <= 30:
        out.append((50 - vol, 'Espera al rival', 'volumen_presion'))
    if _v(s, 'verticalidad') >= VERTICAL_MIN and _v(s, 'ritmo') <= PATIENT_MAX:
        out.append((_v(s, 'verticalidad') - 50, COMBINED, 'verticalidad'))
    for k, hi, hl, lo, ll, _ax in EXTREMES:
        x = _v(s, k)
        if x >= hi:
            out.append((abs(x - 50), hl, k))
        elif lo is not None and x <= lo:
            out.append((abs(x - 50), ll, k))
    return out


def _drop_conflicts(cards: list[str], quads: dict[str, str], cand: list[tuple]) -> list[tuple]:
    """Quita etiquetas que contradicen tarjetas, cuadrantes, la regla combinada o una etiqueta más fuerte."""
    names = {c[1] for c in cand}
    kept: list[tuple] = []
    for score, name, metric in sorted(cand, key=lambda c: -c[0]):
        if COMBINED in names and name in ('Muy vertical', 'Ataques pausados'):
            continue
        if quads.get(AXIS_OF_TAG.get(name, '')) == 'Equilibrado':
            continue
        fixed = cards + list(quads.values()) + [k[1] for k in kept]
        if any(_pair(name, other) for other in fixed):
            continue
        kept.append((score, name, metric))
    return kept


def _pair(a: str, b: str) -> bool:
    return (a, b) in CONFLICTS or (b, a) in CONFLICTS


def identity(style: dict[str, Any]) -> dict[str, Any]:
    """Identidad completa: tarjetas, etiquetas (máx. 4), puntos y cuadrantes del mapa, evidencia."""
    s = style or {}
    pts = map_points(s)
    quads = {mk: quadrant(mk, pts[mk]) for mk in ('off', 'dfn')}
    build, attack = build_card(s), attack_card(s)
    tags = _drop_conflicts([build, attack], quads, _candidate_tags(s))[:TOP_TAGS]
    return {
        'build': build, 'defense': quads['dfn'], 'attack': attack, 'offense_style': quads['off'],
        'tags': [t[1] for t in tags],
        'map': {mk: (pts[mk] + [quads[mk]]) if pts[mk] else None for mk in ('off', 'dfn')},
        'evidence': [{'metric': t[2], 'pct': round(_v(s, t[2]))} for t in tags],
        'axes': AXES,
    }


def conflicts(ident: dict[str, Any]) -> list[tuple]:
    """Pares en conflicto dentro de una identidad (vacío = coherente)."""
    items = [ident['build'], ident['defense'], ident['attack'], ident.get('offense_style', '')] + ident['tags']
    out = [(a, b) for i, a in enumerate(items) for b in items[i + 1:] if _pair(a, b)]
    for mk in ('off', 'dfn'):
        if ident['map'].get(mk) and ident['map'][mk][2] == 'Equilibrado':
            out += [('Equilibrado', t) for t in ident['tags'] if AXIS_OF_TAG.get(t) == mk]
    return out
