# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Motor de etiquetas de estilo: una sola función ``identity(style)`` para tarjetas, etiquetas y mapa.

``style`` son percentiles 0–100 frente a la liga (``presion`` es el PPDA invertido: alto = deja pocos pases
por acción defensiva). La tarjeta "Enfoque defensivo" ES el nombre del punto en el mapa defensivo.

Coherencia: cada etiqueta declara lo que afirma sobre los números (``claims``: señal → intervalo). Dos
etiquetas con intervalos disjuntos sobre la misma señal nunca aparecen juntas, y ninguna etiqueta publicada
puede contradecir los percentiles de los que sale (``claim_violations``).

Regla de presión (``perfil_presion`` en DEFINITIONS): el eje y del mapa es la media de volumen, PPDA
invertido y contrapresión; cuando volumen y PPDA cuentan historias opuestas (uno ≥65 y el otro ≤45) el
perfil lo nombra ("presiona mucho, deja jugar" o "presión selectiva") y ese nombre sustituye al del
cuadrante, para que la tarjeta nunca diga "selectiva" de un equipo que presiona mucho ni lo contrario.
"""
from __future__ import annotations

import math
from typing import Any, Optional

NA = 'Datos insuficientes'
EQ = 'Equilibrado'
MID = 50
HI, LO = 80, 20                 # etiqueta extrema
CENTER_BAND = 9                 # |p-50| < 9 en ambos ejes → "Equilibrado"
VERTICAL_MIN, PATIENT_MAX = 70, 40  # "Directo pero paciente"
TOP_TAGS = 4
EPS = 1e-6
PROFILE_STRONG, PROFILE_WEAK = 65, 45   # volumen vs PPDA: uno ≥65 y el otro ≤45 → historias opuestas
SIN_ROBO_MAX_CP = 75            # "deja jugar" no se dice si la contrapresión es ≥75
ASFIXIANTE = {'volumen_presion': 75, 'presion': 60, 'contrapresion': 50}  # mínimos
ESPERA = {'volumen_presion': 30, 'presion': 40, 'contrapresion': 50, 'linea': 40}  # máximos
SHORT_POS, SHORT_POS_STRICT, SHORT_RITMO_MAX = 65, 80, 55  # tarjeta "Pase corto"
COUNTER_POS_MAX, COUNTER_MIN = 50, 65
DIRECT_GK_MIN, DIRECT_POS_MAX = 70, 45
WINGS_MIN, INSIDE_MAX = 67, 33
VEL, INT = 'vel_ataque', 'intensidad_presion'   # señales compuestas de los ejes del mapa

QUADRANTS = {
    'off': {'tl': 'Posesión elaborada', 'tr': 'Dominio vertical', 'bl': 'Reactivo', 'br': 'Contragolpe'},
    'dfn': {'tl': 'Bloque medio agresivo', 'tr': 'Presión alta', 'bl': 'Bloque bajo', 'br': 'Línea alta, sin asfixiar'},
}
AXES = {'off': ('Velocidad del ataque', 'Posesión'), 'dfn': ('Altura de línea', 'Intensidad de presión')}
SELECTIVE = 'Presión selectiva: pocas presiones, pero corta pronto el pase rival (PPDA bajo)'
SIN_ROBO = 'Presiona mucho, pero deja jugar al rival (PPDA alto)'
COMBINED = 'Directo pero paciente'
# Texto del control `presion` (percentil invertido: alto = PPDA bajo = el rival hace pocos pases). Sin la palabra «presión»: no se confunde con el volumen de presión.
PPDA_LABEL = 'Pases que permite al rival (PPDA · alto = permite pocos)'


def _ge(x: float) -> tuple:
    return (float(x), 100.0)


def _le(x: float) -> tuple:
    return (0.0, float(x))


def _lt(x: float) -> tuple:
    return (0.0, x - EPS)


VOL, PPDA, CP = 'volumen_presion', 'presion', 'contrapresion'


def _mean3(bounds: dict[str, int]) -> int:
    """Cota implícita del eje compuesto (media redondeada de volumen, PPDA y contrapresión)."""
    return round((bounds[VOL] + bounds[PPDA] + bounds[CP]) / 3)


# Perfiles de presión excluyentes: id → texto explicativo y lo que afirma sobre volumen, PPDA y contrapresión.
PRESS_PROFILES: dict[str, dict[str, Any]] = {
    'asfixiante': {'texto': 'Presión asfixiante', 'claims': dict({k: _ge(v) for k, v in ASFIXIANTE.items()},
                                                                  intensidad_presion=_ge(_mean3(ASFIXIANTE)))},
    'sin_robo': {'texto': SIN_ROBO, 'claims': {VOL: _ge(PROFILE_STRONG), PPDA: _le(PROFILE_WEAK), CP: _lt(SIN_ROBO_MAX_CP)}},
    'selectiva': {'texto': SELECTIVE, 'claims': {VOL: _le(PROFILE_WEAK), PPDA: _ge(PROFILE_STRONG)}},
    'espera': {'texto': 'Espera al rival', 'claims': dict({k: _le(v) for k, v in ESPERA.items()},
                                                          intensidad_presion=_le(_mean3(ESPERA)))},
}
PROFILE_TAGS = ('asfixiante', 'espera')         # perfiles de acuerdo: van como etiqueta
# Perfiles de desacuerdo: su nombre sustituye al del cuadrante (lado de la línea, perfil) → tarjeta.
DFN_QUALIFIED = {
    ('alta', 'sin_robo'): 'Línea alta: presiona mucho, deja jugar',
    ('baja', 'sin_robo'): 'Línea baja: presiona mucho, deja jugar',
    ('alta', 'selectiva'): 'Línea alta, presión selectiva',
    ('baja', 'selectiva'): 'Línea baja, presión selectiva',
}
_TOP, _BOT = _ge(MID), _lt(MID)
_CENTER = (MID - CENTER_BAND + EPS, MID + CENTER_BAND - EPS)
QUAD_CLAIMS = {'tl': ('bot', 'top'), 'tr': ('top', 'top'), 'bl': ('bot', 'bot'), 'br': ('top', 'bot')}
AXIS_SIGNALS = {'off': (VEL, 'posesion'), 'dfn': ('linea', INT)}
# (métrica, umbral alto, texto alto, umbral bajo, texto bajo, eje del mapa)
EXTREMES = (
    ('posesion', HI, 'Dueño del balón', LO, 'Cede el balón', 'off'),
    ('linea', HI, 'Línea muy alta', LO, 'Línea muy baja', 'dfn'),
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
AXIS_OF_TAG.update({PRESS_PROFILES[k]['texto']: 'dfn' for k in PROFILE_TAGS})
# Pares semánticos que no se deducen de los intervalos (los deducibles salen de ``conflict_pairs``).
CONFLICTS = (
    ('Ataques rápidos', 'Ataques pausados'), ('Muy vertical', 'Elabora en corto'),
    ('Pase corto', 'Muy vertical'), ('Pase corto', 'Juego directo'), ('Contragolpe', 'Ataques pausados'),
    ('Dueño del balón', 'Cede el balón'), ('Presión asfixiante', 'Espera al rival'),
    ('Línea muy alta', 'Línea muy baja'), ('Presión alta', 'Espera al rival'),
    ('Posesión elaborada', 'Ataques rápidos'), ('Contragolpe', 'Dueño del balón'),
    ('Muy sólido atrás', 'Concede mucho'), ('Presión asfixiante', SELECTIVE), ('Presión asfixiante', SIN_ROBO),
    ('Línea muy baja', 'Bloque medio agresivo'), ('Bloque medio agresivo', 'Espera al rival'),
    (DFN_QUALIFIED[('alta', 'sin_robo')], 'Roba y remata'), (DFN_QUALIFIED[('baja', 'sin_robo')], 'Roba y remata'),
)


def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _v(s: dict[str, Any], k: str) -> float:
    x = s.get(k)
    return float(x) if _num(x) else float('nan')


def _has(s: dict[str, Any], keys: tuple) -> bool:
    return all(_num(s.get(k)) for k in keys)


def signals(s: dict[str, Any]) -> dict[str, float]:
    """Percentiles del estilo más las dos señales compuestas de los ejes del mapa (redondeadas como el mapa)."""
    out = {k: float(v) for k, v in (s or {}).items() if _num(v)}
    if _has(s, ('ritmo', 'contragolpe')):
        out[VEL] = float(round((s['ritmo'] + s['contragolpe']) / 2))
    if _has(s, (VOL, PPDA, CP)):
        out[INT] = float(round((s[VOL] + s[PPDA] + s[CP]) / 3))
    return out


def satisfies(claims: dict[str, tuple], sig: dict[str, float]) -> bool:
    """True si todas las señales afirmadas existen y caen en su intervalo."""
    return all(k in sig and lo <= sig[k] <= hi for k, (lo, hi) in claims.items())


def disjoint(a: dict[str, tuple], b: dict[str, tuple]) -> bool:
    """Dos conjuntos de afirmaciones incompatibles: alguna señal con intervalos que no se tocan."""
    return any(k in b and (a[k][1] < b[k][0] or b[k][1] < a[k][0]) for k in a)


def pressing_profile(s: dict[str, Any]) -> Optional[str]:
    """Perfil de presión excluyente ('asfixiante', 'sin_robo', 'selectiva', 'espera') o None."""
    sig = signals(s)
    return next((k for k, p in PRESS_PROFILES.items() if satisfies(p['claims'], sig)), None)


def map_points(s: dict[str, Any]) -> dict[str, Optional[list[int]]]:
    """Puntos del mapa: ofensivo (velocidad del ataque, posesión) y defensivo (línea, intensidad de presión)."""
    sig = signals(s)
    off = [int(sig[VEL]), round(sig['posesion'])] if VEL in sig and 'posesion' in sig else None
    dfn = [round(sig['linea']), int(sig[INT])] if INT in sig and 'linea' in sig else None
    return {'off': off, 'dfn': dfn}


def _region(p: list[int]) -> str:
    if abs(p[0] - MID) < CENTER_BAND and abs(p[1] - MID) < CENTER_BAND:
        return 'c'
    return ('t' if p[1] >= MID else 'b') + ('r' if p[0] >= MID else 'l')


def quadrant(mk: str, p: Optional[list[int]], profile: Optional[str] = None) -> str:
    """Nombre del punto del mapa ``mk``; centro → 'Equilibrado'; en 'dfn' un perfil de desacuerdo manda."""
    if not p:
        return NA
    if mk == 'dfn' and (('alta' if p[0] >= MID else 'baja'), profile) in DFN_QUALIFIED:
        return DFN_QUALIFIED[('alta' if p[0] >= MID else 'baja', profile)]
    reg = _region(p)
    return EQ if reg == 'c' else QUADRANTS[mk][reg]


def build_card(s: dict[str, Any]) -> str:
    """Tarjeta "Salida": pase corto solo si no es muy vertical (evita la contradicción histórica)."""
    if not _has(s, ('posesion', 'ritmo', 'contragolpe', 'saque_largo')):
        return NA
    pos, vert = _v(s, 'posesion'), _v(s, 'verticalidad')
    short = pos >= SHORT_POS_STRICT or (pos >= SHORT_POS and _v(s, 'ritmo') <= SHORT_RITMO_MAX)
    if short and not vert >= VERTICAL_MIN:
        return 'Pase corto'
    if short:
        return 'Posesión con pase vertical'
    if pos <= COUNTER_POS_MAX and (_v(s, 'contragolpe') >= COUNTER_MIN or _v(s, 'ritmo') >= COUNTER_MIN):
        return 'Contragolpe'
    if _v(s, 'saque_largo') >= DIRECT_GK_MIN and pos <= DIRECT_POS_MAX:
        return 'Juego directo'
    return EQ


def attack_card(s: dict[str, Any]) -> str:
    """Tarjeta "Ataque": por bandas, por dentro o mixto según centros."""
    c = _v(s, 'centros')
    if math.isnan(c):
        return NA
    return 'Por bandas' if c >= WINGS_MIN else ('Por dentro' if c <= INSIDE_MAX else 'Mixto')


def _quad_claims(mk: str) -> dict[str, dict[str, tuple]]:
    sx, sy = AXIS_SIGNALS[mk]
    rng = {'top': _TOP, 'bot': _BOT}
    out = {QUADRANTS[mk][q]: {sx: rng[cx], sy: rng[cy]} for q, (cx, cy) in QUAD_CLAIMS.items()}
    out[EQ] = {sx: _CENTER, sy: _CENTER}
    return out


def _dfn_claims() -> dict[str, dict[str, tuple]]:
    out = _quad_claims('dfn')
    for (side, prof), name in DFN_QUALIFIED.items():
        out[name] = dict(PRESS_PROFILES[prof]['claims'], linea=_TOP if side == 'alta' else _BOT)
    return out


def _tag_claims() -> dict[str, dict[str, tuple]]:
    out = {COMBINED: {'verticalidad': _ge(VERTICAL_MIN), 'ritmo': _le(PATIENT_MAX)}}
    out.update({PRESS_PROFILES[k]['texto']: PRESS_PROFILES[k]['claims'] for k in PROFILE_TAGS})
    for k, hi, hl, lo, ll, _ax in EXTREMES:
        out[hl] = {k: _ge(hi)}
        if ll:
            out[ll] = {k: _le(lo)}
    return out


SLOT_CLAIMS: dict[str, dict[str, dict[str, tuple]]] = {
    'build': {'Pase corto': {'posesion': _ge(SHORT_POS), 'verticalidad': _lt(VERTICAL_MIN)},
              'Posesión con pase vertical': {'posesion': _ge(SHORT_POS), 'verticalidad': _ge(VERTICAL_MIN)},
              'Contragolpe': {'posesion': _le(COUNTER_POS_MAX)},
              'Juego directo': {'saque_largo': _ge(DIRECT_GK_MIN), 'posesion': _le(DIRECT_POS_MAX)}, EQ: {}},
    'attack': {'Por bandas': {'centros': _ge(WINGS_MIN)}, 'Por dentro': {'centros': _le(INSIDE_MAX)},
               'Mixto': {'centros': (INSIDE_MAX + EPS, WINGS_MIN - EPS)}},
    'off': _quad_claims('off'), 'dfn': _dfn_claims(), 'tag': _tag_claims(),
}


def _claims(item: tuple) -> Optional[dict[str, tuple]]:
    slot, text = item
    return {} if text == NA else SLOT_CLAIMS[slot].get(text)


def _pair(a: str, b: str) -> bool:
    return (a, b) in CONFLICTS or (b, a) in CONFLICTS


def _clash(a: tuple, b: tuple) -> bool:
    """Dos etiquetas (slot, texto) en conflicto: par semántico o afirmaciones disjuntas."""
    ca, cb = _claims(a), _claims(b)
    return _pair(a[1], b[1]) or (ca is not None and cb is not None and disjoint(ca, cb))


def _candidate_tags(s: dict[str, Any], profile: Optional[str]) -> list[tuple]:
    out = []
    if profile in PROFILE_TAGS:
        metric = VOL
        out.append((abs(_v(s, metric) - MID), PRESS_PROFILES[profile]['texto'], metric))
    if _v(s, 'verticalidad') >= VERTICAL_MIN and _v(s, 'ritmo') <= PATIENT_MAX:
        out.append((_v(s, 'verticalidad') - MID, COMBINED, 'verticalidad'))
    for k, hi, hl, lo, ll, _ax in EXTREMES:
        x = _v(s, k)
        if x >= hi:
            out.append((abs(x - MID), hl, k))
        elif lo is not None and x <= lo:
            out.append((abs(x - MID), ll, k))
    return out


def _drop_conflicts(fixed: list[tuple], quads: dict[str, str], cand: list[tuple]) -> list[tuple]:
    """Quita etiquetas que contradicen tarjetas, cuadrantes, la regla combinada o una etiqueta más fuerte."""
    names = {c[1] for c in cand}
    kept: list[tuple] = []
    for score, name, metric in sorted(cand, key=lambda c: -c[0]):
        if COMBINED in names and name in ('Muy vertical', 'Ataques pausados'):
            continue
        if quads.get(AXIS_OF_TAG.get(name, '')) == EQ:
            continue
        if any(_clash(('tag', name), other) for other in fixed + [('tag', k[1]) for k in kept]):
            continue
        kept.append((score, name, metric))
    return kept


def _pressing(s: dict[str, Any], profile: Optional[str]) -> dict[str, Any]:
    sig = signals(s)
    return {'perfil': profile, 'texto': PRESS_PROFILES[profile]['texto'] if profile else None,
            'evidencia': {k: (round(sig[k]) if k in sig else None) for k in (VOL, PPDA, CP, INT)}}


def identity(style: dict[str, Any]) -> dict[str, Any]:
    """Identidad completa: tarjetas, etiquetas (máx. 4), puntos y nombres del mapa, perfil de presión."""
    s = style or {}
    pts, profile = map_points(s), pressing_profile(s)
    quads = {'off': quadrant('off', pts['off']), 'dfn': quadrant('dfn', pts['dfn'], profile)}
    build, attack = build_card(s), attack_card(s)
    fixed = [('build', build), ('attack', attack), ('off', quads['off']), ('dfn', quads['dfn'])]
    tags = _drop_conflicts(fixed, quads, _candidate_tags(s, profile))[:TOP_TAGS]
    return {
        'build': build, 'defense': quads['dfn'], 'attack': attack, 'offense_style': quads['off'],
        'tags': [t[1] for t in tags],
        'map': {mk: (pts[mk] + [quads[mk]]) if pts[mk] else None for mk in ('off', 'dfn')},
        'regions': {mk: (QUADRANTS[mk].get(_region(pts[mk]), EQ) if pts[mk] else NA) for mk in ('off', 'dfn')},
        'pressing': _pressing(s, profile),
        'evidence': [{'metric': t[2], 'pct': round(_v(s, t[2]))} for t in tags],
        'axes': AXES,
    }


def _items(ident: dict[str, Any]) -> list[tuple]:
    off = ident.get('offense_style') or ((ident.get('map') or {}).get('off') or [None, None, NA])[2]
    items = [('build', ident.get('build') or NA), ('attack', ident.get('attack') or NA), ('off', off or NA),
             ('dfn', ident.get('defense') or NA)]
    return items + [('tag', t) for t in ident.get('tags') or []]


def conflicts(ident: dict[str, Any]) -> list[tuple]:
    """Pares en conflicto dentro de una identidad (vacío = coherente)."""
    items = _items(ident)
    out = [(a[1], b[1]) for i, a in enumerate(items) for b in items[i + 1:] if _clash(a, b)]
    for mk in ('off', 'dfn'):
        if ident.get('map') and ident['map'].get(mk) and ident['map'][mk][2] == EQ:
            out += [(EQ, t) for t in ident.get('tags') or [] if AXIS_OF_TAG.get(t) == mk]
    return out


def claim_violations(ident: dict[str, Any], style: dict[str, Any]) -> list[str]:
    """Etiquetas que afirman algo que los percentiles no sostienen, o que el motor no conoce."""
    sig, out = signals(style), []
    for slot, text in _items(ident):
        claims = _claims((slot, text))
        if claims is None:
            out.append(f'{text}: etiqueta desconocida para {slot}')
            continue
        for k, (lo, hi) in sorted(claims.items()):
            if k in sig and not lo <= sig[k] <= hi:
                out.append(f'{text}: {k}={sig[k]:g} fuera de {int_bounds((lo, hi))}')
    return out


def int_bounds(rng: tuple) -> list[int]:
    """Intervalo en percentiles enteros (los extremos abiertos se cierran hacia adentro)."""
    return [math.ceil(rng[0] - EPS / 2), math.floor(rng[1] + EPS / 2)]


def claims_by_text() -> dict[str, dict[str, tuple]]:
    """Afirmaciones por texto (si un texto vive en dos lugares, se unen sus afirmaciones)."""
    out: dict[str, dict[str, tuple]] = {}
    for table in SLOT_CLAIMS.values():
        for text, claims in table.items():
            out.setdefault(text, {}).update(claims)
    return out


def pressing_label_texts() -> list[str]:
    """Textos que hablan de la presión o de la línea: nombres del mapa defensivo y etiquetas de presión."""
    tags = [PRESS_PROFILES[k]['texto'] for k in PROFILE_TAGS] + ['Línea muy alta', 'Línea muy baja']
    return [t for t in SLOT_CLAIMS['dfn'] if t != EQ] + tags


def conflict_pairs() -> list[tuple]:
    """Todos los pares excluyentes: los semánticos de CONFLICTS y los deducidos de afirmaciones disjuntas."""
    entries = [(slot, text) for slot, table in SLOT_CLAIMS.items() for text in table]
    seen, out = set(), []
    for i, a in enumerate(entries):
        for b in entries[i + 1:]:
            key = frozenset((a[1], b[1]))
            if a[1] != b[1] and key not in seen and disjoint(SLOT_CLAIMS[a[0]][a[1]], SLOT_CLAIMS[b[0]][b[1]]):
                seen.add(key)
                out.append((a[1], b[1]))
    out += [p for p in CONFLICTS if frozenset(p) not in seen]
    return out
