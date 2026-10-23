# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Tipología del error al perder (AC-08): contexto 360 de la última acción + desenlace de ``an_``.

Tipos (framework ``tipo_error``): no forzado, bajo presión, decisión arriesgada, duelo perdido y aislado.
``aislado`` (sin compañero visible a ≤10 yd) explica las pérdidas que no encajan en otro tipo. La tasa de
"costosa" (tiro rival en ≤15 s) y "letal" (gol) sale de la pérdida canónica de ``an_<mid>`` unida por la
posesión del evento del error; sin unión se usa el desenlace medido por extract_360 (mismo umbral).
Solo cuentan pérdidas con contexto 360 válido (puerta de visibilidad).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from typing import Any, Optional

from framework import confidence, third, zone

from analytics.shape360_base import SOURCE, Row, pct

ERROR_TYPES = ('no_forzado', 'bajo_presion', 'decision_arriesgada', 'duelo_perdido', 'aislado', 'otro')
ERROR_NAMES = {'no_forzado': 'No forzado', 'bajo_presion': 'Bajo presión',
               'decision_arriesgada': 'Decisión arriesgada', 'duelo_perdido': 'Duelo perdido',
               'aislado': 'Aislado', 'otro': 'Otro'}
OPEN_LOSS = 'lossO'
PLAYERS_TOP = 12
NO_LOSSES = 'sin pérdidas con contexto 360 válido'


def final_type(r: Row) -> str:
    """Tipo publicado: el de extract_360, con 'aislado' en lugar de 'otro' si no había apoyo a ≤10 yd."""
    tipo = r.get('tipo') or 'otro'
    return 'aislado' if tipo == 'otro' and r.get('isolated') else tipo


def an_loss_index(an: Optional[dict[str, Any]]) -> dict[tuple[int, int], dict[str, Any]]:
    """{(equipo, posesión): pérdida en juego} de un extracto an_."""
    out = {}
    for p in (an or {}).get('possessions') or []:
        lo = p.get('loss') or {}
        if lo.get('kind') == OPEN_LOSS:
            out[(p['team'], p['id'])] = lo
    return out


def join_an(rows: Sequence[Row], poss_of: dict[str, int],
            index: dict[tuple[int, int], dict[str, Any]]) -> list[Row]:
    """Copia de las filas con costly/lethal de an_ (``joined``) o, si no unen, del extracto 360."""
    out = []
    for r in rows:
        lo = index.get((r.get('team'), poss_of.get(r.get('eid'))))
        if lo is not None:
            out.append(dict(r, costly=bool(lo.get('costly')), lethal=bool(lo.get('lethal')), joined=True))
        else:
            out.append(dict(r, costly=bool(r.get('shot15')), lethal=bool(r.get('goal15')), joined=False))
    return out


def _summary(rs: Sequence[Row], total: int) -> dict[str, Any]:
    costly = sum(1 for r in rs if r.get('costly'))
    kinds = Counter(final_type(r) for r in rs)
    return {'n': len(rs), 'pct': pct(len(rs), total), 'costosas': costly, 'pct_costosa': pct(costly, len(rs)),
            'letales': sum(1 for r in rs if r.get('lethal')),
            'tipo_principal': kinds.most_common(1)[0][0] if kinds else None}


def _groups(rs: Sequence[Row], key: Callable[[Row], Any]) -> dict[str, dict[str, Any]]:
    by: dict[str, list[Row]] = defaultdict(list)
    for r in rs:
        by[str(key(r))].append(r)
    return {k: _summary(v, len(rs)) for k, v in sorted(by.items())}


def _players(rs: Sequence[Row], names: dict[int, str]) -> list[dict[str, Any]]:
    by: dict[Any, list[Row]] = defaultdict(list)
    for r in rs:
        by[r.get('player')].append(r)
    top = sorted(by.items(), key=lambda kv: (-len(kv[1]), -sum(1 for r in kv[1] if r.get('costly'))))
    return [dict(_summary(v, len(rs)), player=pid, nombre=names.get(pid), confidence=confidence(len(v)))
            for pid, v in top[:PLAYERS_TOP]]


def _types(rs: Sequence[Row]) -> list[dict[str, Any]]:
    by = _groups(rs, final_type)
    return [dict({k: v for k, v in by[t].items() if k != 'tipo_principal'}, tipo=t, nombre=ERROR_NAMES[t])
            for t in ERROR_TYPES if t in by]


def taxonomy(own: Sequence[Row], opp: Sequence[Row], names: dict[int, str], window: str) -> dict[str, Any]:
    """Tipos con tasa costosa/letal, por zona 6×3, por tercio y por jugador; referencia: rivales."""
    valid = [r for r in own if r.get('err_valid')]
    rv = [r for r in opp if r.get('err_valid')]
    ref = {t: {'pct': s['pct'], 'pct_costosa': s['pct_costosa'], 'n': s['n']}
           for t, s in _groups(rv, final_type).items()}
    out: dict[str, Any] = {
        'definicion': 'tipo_error', 'source': SOURCE, 'window': window, 'n': len(valid),
        'cobertura': {'n_perdidas': len(own), 'n_linked': sum(1 for r in own if r.get('err_linked')),
                      'n_valid': len(valid), 'n_unidas_an': sum(1 for r in valid if r.get('joined'))},
        'tipos': _types(valid), 'zonas': _groups(valid, lambda r: zone([r['x'], r['y']])),
        'tercios': _groups(valid, lambda r: third(r['x'])), 'jugadores': _players(valid, names),
        'ref_rivales': ref, 'nota': 'Costosa = tiro rival en ≤15 s; letal = gol. Contexto 360 = visibles.'}
    if not valid:
        out['motivo'] = NO_LOSSES
    return out
