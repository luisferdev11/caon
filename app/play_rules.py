# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Parser de reglas (español) → play.v1. Determinista, sin red; respaldo del LLM.

Flujo: normalizar → reanudación → cláusulas (, ; : y luego después que) → por cláusula:
zona (la última mencionada), tipo de paso (por prioridad), actor/receptor, desenlace.
Todo valor por defecto queda escrito en `assumptions`.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from app.play_schema import Actor, Play, Start, Step

EXAMPLES = [
    'el 10 centra al segundo palo y el 9 cabecea: gol',
    'Salida desde el portero: el 4 pasa al 6, cambio de orientación a la banda derecha y centro al área',
    'Recuperación alta del 6 y contra: pase filtrado al 9 que define: gol',
    'Tiro libre directo del 10: poste',
    'Córner al primer palo y remate de cabeza del 4: atajada',
]
SPLIT_RE = re.compile(r'[,;:.]|\by luego\b|\bluego\b|\bdespues\b|\by\b|\bque\b')
RESTARTS = [
    ('free_kick', r'tiro libre'), ('corner', r'corner|tiro de esquina|saque de esquina'),
    ('goal_kick', r'saque de meta|salida desde (el )?(portero|arquero)|(portero|arquero) saca'),
    ('throw_in', r'saque de banda|lateral a mano'), ('kickoff', r'saque (de centro|inicial)'),
]
# (zona, patrón) — orden: lo más específico primero; dentro de una cláusula gana la última mencionada.
ZONE_PATTERNS = [
    ('area_chica', r'area chica'), ('primer_palo', r'primer palo'), ('segundo_palo', r'segundo palo'),
    ('punto_penal', r'punto penal|punto de penal'), ('borde_area', r'borde del area|media luna|fuera del area'),
    ('area', r'\b(dentro del|en el|al|el) area'), ('zona_alta', r'(?<=presion )alt[ao]'),
    ('zona_alta', r'(?<=recuperacion )alt[ao]'), ('zona_alta', r'(?<=robo )alt[ao]'), ('zona_alta', r'campo rival'),
    ('banda_izq', r'(banda|costado|carril|lado|la|por) izquierd[ao]|banda izquierda'),
    ('banda_der', r'(banda|costado|carril|lado|la|por) derech[ao]|banda derecha'),
    ('campo_propio', r'campo propio|propia mitad'),
    ('medio', r'medio ?campo|media cancha|mitad de (la )?cancha|por el centro|al centro'),
]
SHOT_TARGET_RE = re.compile(r'al (primer|segundo) palo|al angulo|a (la )?porteria|al arco')
# (tipo, patrón) en orden de prioridad: una cláusula produce un solo tipo (salvo 'pared').
STEP_PATTERNS = [
    ('header', r'cabece|cabezazo|de cabeza'),
    ('cross', r'\bcentr(a|o|ar)\b|cuelga|\bmanda un centro'),
    ('shot', r'dispar|remat|\btir(a|o)\b(?! (libre|de esquina))|chut|\bdefine\b|tiro libre directo'),
    ('recovery', r'recupera|\broba|robo|intercept'),
    ('loss', r'\bpierde|perdida'),
    ('clearance', r'despej'),
    ('dribble', r'regate|encara|gambete|dribl|recorta|se quita'),
    ('pass', r'\bpas(a|e)\b|\btoca\b|\babre\b|filtr|cambi\w* de orientacion|\bentrega|\bsaca\b|\bjuega\b'),
    ('carry', r'conduc|avanza|\blleva\b|\bsube\b'),
]
OUTCOMES = [
    ('poste', r'poste|travesano|larguero|\bal palo\b|pega en el palo'),
    ('atajada', r'atajad|\bataja|detiene|para el portero|salva el portero'),
    ('bloqueado', r'bloque|rebota|despej'),
    ('fuera', r'\bfuera\b|afuera|desviad|por encima|por un lado'),
    ('gol', r'\bgol\b|golazo|\banota|\bmarca\b'),
]
POSITIONS = [
    (r'portero|arquero', 'Goalkeeper'), (r'lateral izquierdo', 'Left Back'), (r'lateral derecho', 'Right Back'),
    (r'\bcentral\b|defensa central', 'Center Back'), (r'extremo izquierdo', 'Left Wing'),
    (r'extremo derecho', 'Right Wing'), (r'centro ?delantero|delantero|el nueve', 'Center Forward'),
    (r'volante|contencion|mediocampista|medio centro', 'Midfield'),
]
SHOOT_ZONES = {'borde_area', 'area', 'punto_penal', 'area_chica', 'primer_palo', 'segundo_palo'}
BASE_CONFIDENCE, ASSUMPTION_PENALTY, MIN_CONFIDENCE = 0.95, 0.08, 0.2
MAX_INPUT = 500


class PlayParseError(ValueError):
    """Texto sin ninguna acción reconocible; trae sugerencias para la UI (422)."""

    def __init__(self, message: str, suggestions: list[str]):
        super().__init__(message)
        self.suggestions = suggestions


def normalize(text: str) -> str:
    """Minúsculas, sin acentos, espacios colapsados."""
    t = unicodedata.normalize('NFD', text.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', t).strip()


def detect_restart(t: str) -> str:
    for rid, pat in RESTARTS:
        if re.search(pat, t):
            return rid
    first = SPLIT_RE.split(t)[0]
    return 'recovery' if re.search(r'recupera|\broba|robo|intercept|presion alta', first) else 'open'


def find_zone(clause: str) -> tuple[Optional[str], str]:
    """Zona mencionada al final de la cláusula y la cláusula sin las frases de zona.

    Los patrones más específicos se aplican primero y borran su texto (sin solaparse).
    """
    hits, rest = [], clause
    for zid, pat in ZONE_PATTERNS:
        for m in re.finditer(pat, rest):
            hits.append((m.start(), zid))
        rest = re.sub(pat, lambda m: ' ' * len(m.group(0)), rest)
    return (max(hits)[1] if hits else None), rest


def find_type(clause: str) -> Optional[str]:
    for typ, pat in STEP_PATTERNS:
        if re.search(pat, clause):
            return typ
    return None


def find_outcome(clause: str) -> Optional[str]:
    for oid, pat in OUTCOMES:
        if re.search(pat, clause):
            return oid
    return None


def _name_hits(clause: str, shape: list[dict]) -> list[tuple[int, dict, bool]]:
    hits = []
    for p in shape or []:
        toks = normalize(p.get('name') or '').split()
        keys = {' '.join(toks[-2:]), toks[-1]} if toks else set()
        for key in sorted(keys, key=len, reverse=True):
            m = re.search(r'(\b(a|al|con)\s+)?\b' + re.escape(key) + r'\b', clause) if len(key) >= 4 else None
            if m:
                hits.append((m.start(), {'name': p['name'], 'num': p.get('num')}, bool(m.group(1))))
                break
    return hits


def find_people(clause: str, shape: list[dict]) -> tuple[Optional[Actor], Optional[Actor]]:
    """(actor, receptor): 'al 9'/'a Martín'/'con X' → receptor; 'el 10'/'del 10'/'Valdés' → actor."""
    hits = [(m.start(), {'num': int(m.group(2))}, m.group(1) in ('al', 'a', 'con'))
            for m in re.finditer(r'\b(el|del|al|a|con)\s+(\d{1,2})\b', clause)]
    hits += _name_hits(clause, shape)
    for pat, pos in POSITIONS:
        m = re.search(r'(\b(a|al|con)\s+(el\s+)?)?' + pat, clause)
        if m:
            hits.append((m.start(), _by_pos(pos, shape), bool(m.group(1))))
    actor = next((Actor(**h) for _, h, rec in sorted(hits, key=lambda x: x[0]) if not rec), None)
    recv = next((Actor(**h) for _, h, rec in sorted(hits, key=lambda x: x[0]) if rec), None)
    return actor, recv


def _by_pos(pos: str, shape: list[dict]) -> dict:
    for p in shape or []:
        if pos in (p.get('pos') or ''):
            return {'name': p.get('name'), 'num': p.get('num'), 'pos': pos}
    return {'pos': pos}


class _State:
    """Acumulador mutable del parseo de una frase (solo vive dentro de parse_rules)."""

    def __init__(self, restart: str):
        self.restart, self.steps, self.assumptions = restart, [], []
        self.pending_zone, self.wing = None, None


def _restart_step(clause: str, st: _State) -> Optional[Step]:
    """Cláusula de reanudación sin verbo: córner directo → centro; saque de meta 'al N' → pase."""
    if st.restart == 'corner' and re.search(RESTARTS[1][1], clause) and 'corto' not in clause:
        return Step(type='cross', height='alto')
    if st.restart == 'goal_kick' and re.search(r'\bal?\s+\d|corto|largo', clause):
        return Step(type='pass')
    return None


def _default_zone(step: Step, st: _State, clause: str) -> Optional[str]:
    prev = st.steps[-1].zone if st.steps else None
    if step.type in ('shot', 'header'):
        if st.restart == 'free_kick' and not st.steps:
            return 'borde_area'
        return prev if prev in SHOOT_ZONES else 'area'
    if step.type == 'pass' and re.search(r'filtr', clause):
        return 'area'
    if step.type == 'pass' and re.search(r'orientacion', clause):
        return 'banda_izq' if st.wing == 'banda_der' else 'banda_der'
    if not st.steps and st.restart == 'goal_kick':
        return 'campo_propio'
    if step.type == 'cross':
        return 'punto_penal'
    return None


def _fill_actor(step: Step, st: _State) -> None:
    if step.actor.num is not None or step.actor.name or step.actor.pos:
        return
    prev = st.steps[-1] if st.steps else None
    if prev is not None:
        src = prev.receiver if prev.receiver is not None else prev.actor
        step.actor = src.model_copy()
    else:
        st.assumptions.append('No se dijo quién inicia: se asigna al jugador más cercano al balón.')


def _add(step: Step, clause: str, zone: Optional[str], st: _State) -> None:
    step.zone = zone or st.pending_zone or step.zone
    if step.zone is None:
        step.zone = _default_zone(step, st, clause)
        if step.zone and step.type not in ('shot', 'header'):
            st.assumptions.append(f'Paso {len(st.steps) + 1} ({step.type}): zona supuesta "{step.zone}".')
    st.pending_zone = None
    if step.type == 'cross' and step.height is None:
        step.height = 'raso' if 'raso' in clause else 'alto'
    _fill_actor(step, st)
    if step.zone in ('banda_izq', 'banda_der'):
        st.wing = step.zone
    st.steps.append(step)


def _clause(clause: str, shape: list[dict], st: _State) -> None:
    raw = clause
    if find_type(clause) in ('shot', 'header'):
        clause = SHOT_TARGET_RE.sub(' ', clause)
    zone, rest = find_zone(clause)
    typ = find_type(rest)
    outcome = find_outcome(rest)
    actor, recv = find_people(rest, shape)
    if typ is None and re.search(r'\bpared\b', rest):
        typ = 'pared'
    if typ is None:
        step = _restart_step(raw, st)
        if step is None:
            if zone and st.steps and outcome is None:
                st.steps[-1].zone = zone
                st.assumptions = [a for a in st.assumptions if not a.startswith(f'Paso {len(st.steps)} ')]
            elif zone:
                st.pending_zone = zone
            if outcome and st.steps:
                st.steps[-1].outcome = outcome
            return
        typ = step.type
    if typ == 'pared':
        _add(Step(type='pass', actor=actor or Actor(), receiver=recv), raw, None, st)
        back = recv or Actor()
        _add(Step(type='pass', actor=back, receiver=st.steps[-1].actor.model_copy()), raw, zone, st)
        return
    step = Step(type=typ, actor=actor or Actor(), receiver=recv)
    if typ == 'clearance':
        step.outcome = 'bloqueado'
        step.actor = Actor(pos='Rival')
    _add(step, raw, zone, st)
    if outcome and typ != 'clearance':
        st.steps[-1].outcome = outcome


def parse_rules(text: str, shape: Optional[list[dict]] = None, team: Optional[str] = None) -> Play:
    """Texto en español → Play (source='rules'). Lanza PlayParseError si no hay acciones."""
    t = normalize(text[:MAX_INPUT])
    st = _State(detect_restart(t))
    for clause in SPLIT_RE.split(t):
        if clause.strip():
            _clause(' ' + clause.strip() + ' ', shape or [], st)
    if not st.steps:
        raise PlayParseError('No reconocí ninguna acción (pase, conducción, centro, remate…).', EXAMPLES)
    last = st.steps[-1]
    if last.type in ('shot', 'header') and last.outcome is None:
        st.assumptions.append('No se dijo el desenlace del remate: se muestra sin resultado.')
    conf = max(MIN_CONFIDENCE, BASE_CONFIDENCE - ASSUMPTION_PENALTY * len(st.assumptions))
    return Play(team=team, start=Start(restart=st.restart), steps=st.steps,
                assumptions=st.assumptions, confidence=round(conf, 2), source='rules')
