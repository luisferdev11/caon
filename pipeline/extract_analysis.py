# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Etapa de análisis: escribe ``data/extract/an_<mid>.json`` (posesiones + eventos ligeros) por partido.

Uso: ``flock data/out/heavy.lock .venv/bin/python -X utf8 pipeline/extract_analysis.py [--force]``.
Procesa todo ``data/cache/v8_events_<mid>.json``; salta los que ya están al día (misma versión y más nuevos).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from multiprocessing import Pool
from typing import Any, Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))   # run.py arranca con -I
import sequences

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data' / 'cache'
OUT = ROOT / 'data' / 'extract'
VERSION = 5  # 2: alcance solo completadas; 3: sin tanda de penales; 4: tipo de pérdida como extract; 5: n_prog sin la jugada de reanudación y rival_shots
WORKERS = 4


def _event_ids(cache: pathlib.Path) -> list[int]:
    return sorted(int(p.stem.rsplit('_', 1)[1]) for p in cache.glob('v8_events_*.json'))


def _up_to_date(src: pathlib.Path, dst: pathlib.Path) -> bool:
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        return False
    try:
        return json.loads(dst.read_text(encoding='utf-8')).get('version') == VERSION
    except ValueError:
        return False


def pending_ids(cache: pathlib.Path, out: pathlib.Path, force: bool) -> list[int]:
    """Partidos con eventos v8 cuyo an_<mid>.json falta, es viejo o de otra versión (todos con ``force``)."""
    return [m for m in _event_ids(cache)
            if force or not _up_to_date(cache / f'v8_events_{m}.json', out / f'an_{m}.json')]


def metadata_index(cache: pathlib.Path) -> dict[int, dict[str, Any]]:
    """Metadatos de partido (local/visitante, marcador) desde los listados de temporada en caché."""
    out: dict[int, dict[str, Any]] = {}
    for path in cache.glob('v6_competitions_73_seasons_*_matches.json'):
        for match in json.loads(path.read_text(encoding='utf-8')):
            out[match['match_id']] = match
    return out


def process_one(mid: int, cache: pathlib.Path, out: pathlib.Path, metadata: Optional[dict[str, Any]]) -> str:
    """Construye y escribe an_<mid>.json; devuelve 'ok' o el motivo del fallo."""
    try:
        events = json.loads((cache / f'v8_events_{mid}.json').read_text(encoding='utf-8'))
        doc = sequences.build_possessions(events, metadata or {})
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return f'{type(exc).__name__}: {exc}'
    meta = metadata or {}
    doc = dict(version=VERSION, match_id=mid, status='ok',
               home=(meta.get('home_team') or {}).get('home_team_id'),
               away=(meta.get('away_team') or {}).get('away_team_id'), **doc)
    tmp = out / f'an_{mid}.json.tmp'
    tmp.write_text(json.dumps(doc, ensure_ascii=False, allow_nan=False, separators=(',', ':')), encoding='utf-8')
    tmp.replace(out / f'an_{mid}.json')
    return 'ok'


def _job(args: tuple) -> tuple:
    mid, meta = args
    return mid, process_one(mid, CACHE, OUT, meta)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI: procesa los partidos pendientes con Pool(4)."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--force', action='store_true', help='reprocesa todo')
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    todo = pending_ids(CACHE, OUT, args.force)
    meta = metadata_index(CACHE)
    with Pool(WORKERS) as pool:
        results = pool.map(_job, [(m, meta.get(m)) for m in todo], chunksize=4)
    bad = [(m, s) for m, s in results if s != 'ok']
    print(f'an_*: {len(results) - len(bad)} procesados, {len(bad)} fallos, {len(_event_ids(CACHE)) - len(todo)} al día')
    for m, s in bad[:20]:
        print('  fallo', m, s)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
