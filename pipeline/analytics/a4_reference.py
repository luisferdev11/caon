# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Población de referencia de los temas A4: equipos-temporada de la Liga MX con extracto an_ y eventos.

Cada unidad (equipo, temporada) suma los conteos ``n`` de ``a4_facts`` de sus partidos (≥ REF_MIN_MATCHES).
Los percentiles (``ref_pct``) de cada tema se calculan aplicando su propia función ``values`` a cada unidad,
así entidad y referencia usan exactamente la misma definición. Las unidades se guardan en disco
(``data/out/a4/a4_reference.json``) con una firma del conjunto de partidos; si cambia, se recalculan.
"""
from __future__ import annotations

import json
import pathlib
from collections import defaultdict
from typing import Any, Callable, Optional  # noqa: UP035 - Python 3.9

import framework as fw

from analytics import CACHE, EXTRACT, ROOT, a4_facts

REF_VERSION = 3  # súbase cuando cambie a4_facts o la población (3: solo ventana oficial)
REF_MIN_MATCHES = fw.REF_MIN_MATCHES
REF_PATH = ROOT / 'data' / 'out' / 'a4' / 'a4_reference.json'
REF_LABEL = 'equipos-temporada de la Liga MX con eventos, ventana oficial'
_MEMO: dict[str, Any] = {}


# ---------------------------------------------------------------- puro
def unit_counts(mids: list[int], facts_fn: Callable[[int], Optional[dict[int, dict]]],
                season_of: dict[int, Any], min_matches: int = REF_MIN_MATCHES) -> dict[str, dict[str, Any]]:
    """{'equipo:temporada': conteos n sumados} para unidades con ≥ ``min_matches`` partidos."""
    acc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for mid in mids:
        season = season_of.get(mid)
        facts = facts_fn(mid) if season is not None else None
        for team, f in (facts or {}).items():
            acc[f'{team}:{season}'].append({'n': f['n']})
    return {k: a4_facts.merge(v)['n'] for k, v in acc.items() if len(v) >= min_matches}


def populations(units: dict[str, dict[str, Any]],
                values_fn: Callable[[dict[str, Any]], dict[str, tuple]]) -> dict[str, list[float]]:
    """{clave de values: valores no nulos de todas las unidades}."""
    out: dict[str, list[float]] = defaultdict(list)
    for n in units.values():
        for key, (value, _) in values_fn(n).items():
            if value is not None:
                out[key].append(value)
    return dict(out)


def official_only(mids: list[int], date_of: dict[int, str], end: str = fw.OFFICIAL_END) -> list[int]:
    """Partidos de la ventana oficial (fecha ≤ ``end``); sin fecha conocida quedan fuera."""
    return [m for m in mids if date_of.get(m) and date_of[m] <= end]


def signature(mids: list[int]) -> str:
    """Firma barata del conjunto de partidos (versión, cuántos y suma de ids)."""
    return f'v{REF_VERSION}:{len(mids)}:{sum(mids)}'


# ---------------------------------------------------------------- IO (bordes)
def season_map(cache: pathlib.Path = CACHE) -> dict[int, Any]:
    """{match_id: season_id} desde los calendarios v6 en caché."""
    out: dict[int, Any] = {}
    for path in sorted(cache.glob('v6_competitions_*_seasons_*_matches.json')):
        try:
            rows = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        for m in rows:
            out[m['match_id']] = (m.get('season') or {}).get('season_id')
    return out


def match_dates(cache: pathlib.Path = CACHE) -> dict[int, str]:
    """{match_id: fecha} desde los calendarios v6 en caché."""
    out: dict[int, str] = {}
    for path in sorted(cache.glob('v6_competitions_*_seasons_*_matches.json')):
        try:
            rows = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        for m in rows:
            out[m['match_id']] = m.get('match_date')
    return out


def an_match_ids(extract: pathlib.Path = EXTRACT) -> list[int]:
    """Partidos con extracto an_."""
    out = []
    for p in extract.glob('an_*.json'):
        try:
            out.append(int(p.stem.split('_', 1)[1]))
        except ValueError:
            continue
    return sorted(out)


def load_units(path: pathlib.Path = REF_PATH, build: bool = True) -> dict[str, dict[str, Any]]:
    """Unidades de referencia desde disco; si faltan o la firma no coincide, se recalculan y se guardan."""
    from analytics import a4_common, load_an, load_events, load_f360
    mids = official_only(an_match_ids(), match_dates())   # las conclusiones se comparan con la ventana oficial
    sig = signature(mids)
    try:
        doc = json.loads(path.read_text(encoding='utf-8'))
        if doc.get('firma') == sig:
            return doc['unidades']
    except (OSError, ValueError):
        pass
    if not build:
        return {}
    units = unit_counts(mids, lambda m: a4_common.cached_facts(load_an, load_events, load_f360, m),
                        season_map())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'firma': sig, 'descripcion': REF_LABEL, 'unidades': units},
                               ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return units


def units_for(ctx: Any) -> dict[str, dict[str, Any]]:
    """Unidades inyectadas en ``ctx.league_ref['a4_unidades']`` (tests) o las de disco (memoizadas)."""
    injected = (getattr(ctx, 'league_ref', None) or {}).get('a4_unidades')
    if injected is not None:
        return injected
    if 'units' not in _MEMO:
        _MEMO['units'] = load_units()
    return _MEMO['units']


def populations_for(ctx: Any, values_fn: Callable[[dict[str, Any]], dict[str, tuple]]) -> dict[str, list[float]]:
    """Poblaciones de referencia de un tema para el contexto."""
    return populations(units_for(ctx), values_fn)


def main() -> int:
    """CLI: recalcula (si hace falta) y resume las unidades de referencia."""
    units = load_units()
    print(f'{len(units)} unidades de referencia ({REF_LABEL}) → {REF_PATH}')
    return 0 if units else 1


if __name__ == '__main__':  # uso: cd pipeline && python -X utf8 -m analytics.a4_reference
    raise SystemExit(main())
