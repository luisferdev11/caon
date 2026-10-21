# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Referencia 360 de liga y de la muestra neutral, más el nivel del rival por temporada.

Resume cada (partido, equipo) de todos los extractos ``f360_<mid>`` en sumas y conteos por métrica de
``shape360_base.SPECS`` y agrega por ventana: media de liga (por registro), medias por equipo (para el
percentil; equipos con ≥5 partidos con 360) y media de la muestra neutral (data/out/neutral_sample.json).
IO solo en ``main`` / ``load_reference``:

    flock data/out/heavy.lock .venv/bin/python -X utf8 pipeline/analytics/shape360_ref.py
"""
from __future__ import annotations

import functools
import json
import pathlib
import sys
from collections import defaultdict
from collections.abc import Iterable, Sequence
from multiprocessing import Pool
from typing import Any, Optional

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from framework import rival_tier

from analytics import shape360_base as sb

ROOT = HERE.parents[1]
EXTRACT = ROOT / 'data' / 'extract'
CACHE = ROOT / 'data' / 'cache'
REF_PATH = EXTRACT / 'shape360_ref.json'
NEUTRAL_PATH = ROOT / 'data' / 'out' / 'neutral_sample.json'
REF_VERSION = 1
REF_MIN_TEAM_MATCHES = 5   # un equipo entra a la distribución del percentil con ≥5 partidos con 360
POOL_SIZE = 4
LEAGUE_FULL_MIN = 0.90     # se rotula "liga" solo con ≥90 % del calendario de la ventana con 360
COMPETITION_ID = 73

Summary = dict[str, list[float]]


def team_match_summary(f360: dict[str, Any], team: int) -> Summary:
    """{clave: [suma, n]} de las filas del equipo ``team`` (solo claves con n>0)."""
    by_table = {t: [r for r in sb.rows(f360, t) if r.get('team') == team] for t in sb.TABLES}
    out: Summary = {}
    for key, spec in sb.SPECS.items():
        vals = sb.values(by_table[spec.table], key)
        if vals:
            out[key] = [round(sum(vals), 4), len(vals)]
    return out


def _add(acc: dict[str, list[float]], summary: Summary) -> None:
    for key, (s, n) in summary.items():
        cur = acc.setdefault(key, [0.0, 0])
        cur[0] += s
        cur[1] += n


def _window_ref(items: Sequence[tuple[int, int, Summary]]) -> dict[str, Any]:
    pooled: dict[str, list[float]] = {}
    teams: dict[int, dict[str, list[float]]] = defaultdict(dict)
    matches: dict[int, set] = defaultdict(set)
    for mid, team, summ in items:
        _add(pooled, summ)
        _add(teams[team], summ)
        matches[team].add(mid)
    out = {}
    for key, (s, n) in pooled.items():
        means = sorted(round(t[key][0] / t[key][1], sb.ROUND) for tid, t in teams.items()
                       if key in t and len(matches[tid]) >= REF_MIN_TEAM_MATCHES)
        out[key] = {'liga': round(s / n, sb.ROUND), 'n': int(n), 'equipos': means, 'n_equipos': len(means)}
    return out


def summarize_league(items: Sequence[tuple[int, int, Summary]], windows: dict[int, str],
                     neutral_ids: Iterable[int]) -> dict[str, Any]:
    """Referencia por ventana (liga + medias por equipo), cobertura del calendario y muestra neutral."""
    by_w: dict[str, list[tuple[int, int, Summary]]] = defaultdict(list)
    for it in items:
        if it[0] in windows:
            by_w[windows[it[0]]].append(it)
    neutral = set(neutral_ids)
    pooled: dict[str, list[float]] = {}
    for mid, _team, summ in items:
        if mid in neutral:
            _add(pooled, summ)
    with_360 = {it[0] for it in items}
    cov: dict[str, dict[str, int]] = {}
    for mid, w in windows.items():
        c = cov.setdefault(w, {'con_360': 0, 'calendario': 0})
        c['calendario'] += 1
        c['con_360'] += int(mid in with_360)
    return {'ventanas': {w: _window_ref(its) for w, its in sorted(by_w.items())}, 'cobertura': cov,
            'neutral': {k: {'valor': round(s / n, sb.ROUND), 'n': int(n)} for k, (s, n) in pooled.items()}}


def league_complete(ref: dict[str, Any], window: str) -> bool:
    """¿El 360 cubre al menos LEAGUE_FULL_MIN del calendario de la ventana? Solo entonces se dice "liga"."""
    c = (ref.get('cobertura') or {}).get(window) or {}
    return bool(c.get('calendario')) and c['con_360'] / c['calendario'] >= LEAGUE_FULL_MIN


def season_tiers(stats: dict[Any, list[dict[str, Any]]], order: Sequence[Any]) -> dict[Any, dict[int, str]]:
    """{temporada: {equipo: nivel}} con framework.rival_tier: el equipo con <10 partidos usa la temporada previa."""
    out: dict[Any, dict[int, str]] = {}
    prev: Optional[list[dict[str, Any]]] = None
    for sid in order:
        rows = stats.get(sid) or []
        tiers = {r['team_id']: rival_tier(r['team_id'], rows, prev) for r in rows}
        out[sid] = {k: v for k, v in tiers.items() if v is not None}
        prev = rows if rows else prev
    return out


# ---------------------------------------------------------------- IO
def _read(path: pathlib.Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _summaries(path: pathlib.Path) -> list[tuple[int, int, Summary]]:
    f = _read(path)
    if not f:
        return []
    return [(f['mid'], t, team_match_summary(f, t)) for t in f.get('teams') or []]


def _calendar() -> tuple[dict[int, dict[str, Any]], dict[str, list[dict[str, Any]]], list[str]]:
    matches, stats, names = {}, {}, {}
    for p in sorted(CACHE.glob(f'v6_competitions_{COMPETITION_ID}_seasons_*_matches.json')):
        for m in _read(p) or []:
            matches[m['match_id']] = m
            names[str(m['season']['season_id'])] = m['season']['season_name']
    for sid in names:
        stats[sid] = _read(CACHE / f'v2_competitions_{COMPETITION_ID}_seasons_{sid}_team-stats.json') or []
    return matches, stats, sorted(names, key=lambda s: names[s])


def build_reference() -> dict[str, Any]:
    """Lee todos los f360, el calendario y la muestra neutral; devuelve la referencia completa."""
    from build_analysis import match_window
    matches, stats, order = _calendar()
    paths = sorted(EXTRACT.glob('f360_*.json'))
    with Pool(POOL_SIZE) as pool:
        items = [it for chunk in pool.imap_unordered(_summaries, paths, chunksize=8) for it in chunk]
    windows = {mid: match_window(m['match_date']) for mid, m in matches.items()}
    neutral = (_read(NEUTRAL_PATH) or {}).get('match_ids') or []
    ref = summarize_league(items, windows, neutral)
    tiers = season_tiers(stats, order)
    f_mids = {it[0] for it in items}
    ref.update(version=REF_VERSION, n_partidos=len(f_mids), n_neutral=len(set(neutral) & f_mids),
               niveles={sid: {str(k): v for k, v in t.items()} for sid, t in tiers.items()},
               temporada={str(mid): str(m['season']['season_id']) for mid, m in matches.items() if mid in f_mids})
    return ref


@functools.lru_cache(maxsize=1)
def load_reference() -> dict[str, Any]:
    """Referencia publicada en data/extract/shape360_ref.json ({} si no existe)."""
    return _read(REF_PATH) or {}


def main() -> None:
    ref = build_reference()
    REF_PATH.write_text(json.dumps(ref, ensure_ascii=False, allow_nan=False, separators=(',', ':')),
                        encoding='utf-8')
    print(json.dumps({'partidos': ref['n_partidos'], 'neutral': ref['n_neutral'],
                      'ventanas': {w: len(v) for w, v in ref['ventanas'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
