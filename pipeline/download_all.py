"""Plan de descarga por prioridad (P1..P6) y corrida reanudable por tramos.

P1 Pachuca·Almada + faltantes de Jardine/Almada-América · P2 San Luis·Jardine ·
P3 muestra neutral 360 (40 partidos 281/317 sin América ni Pachuca, semilla fija) ·
P4 Santos·Almada + 360 faltante de partidos con eventos ya cacheados ·
P5 resto de la liga en ventana oficial (108, 235, 281, 317) · P6 temporadas 318 y 351.

Uso: python pipeline/download_all.py --priorities 1,2 --max-seconds 480
"""
import argparse
import json
import pathlib
import random
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from download_360 import ALL_KINDS, PATHS, cache_name, jobs_for_match, run_jobs

NEUTRAL_N = 40
NEUTRAL_SEED = 20260721
NEUTRAL_SEASONS = (281, 317)
NEUTRAL_EXCLUDE = ('América', 'Pachuca')
OFFICIAL_SEASONS = (108, 235, 281, 317)
LATE_SEASONS = (318, 351)
P1_ENTITIES = ('pac_almada', 'ame_jardine', 'ame_jardine_epi', 'ame_almada')
P2_ENTITIES = ('slp_jardine',)
P4_ENTITIES = ('san_almada',)
PROGRESS_EVERY = 25
STUB_MAX_BYTES = 4096


def _teams(m: dict) -> tuple:
    return m['home_team']['home_team_name'], m['away_team']['away_team_name']


def _sid(m: dict) -> int:
    return m['season']['season_id']


def neutral_sample(ms: list, n: int, seed: int) -> list:
    """Ids ordenados de n partidos (281/317) sin América ni Pachuca, con semilla fija."""
    pool = sorted(m['match_id'] for m in ms if _sid(m) in NEUTRAL_SEASONS
                  and not set(_teams(m)) & set(NEUTRAL_EXCLUDE))
    return sorted(random.Random(seed).sample(pool, min(n, len(pool))))


def _entity_mids(ents: list, ids: tuple) -> list:
    return sorted({x['mid'] for e in ents if e['id'] in ids for x in e['matches']})


def build_plan(ents: list, ms: list, cached_events: set, seed: int = NEUTRAL_SEED,
               neutral_n: int = NEUTRAL_N) -> list:
    """Lista ordenada [(prioridad, match_id, kinds)] sin partidos repetidos."""
    seen: set = set()
    plan = []

    def add(p: int, mids: list, kinds: tuple = ALL_KINDS) -> None:
        for mid in mids:
            if mid not in seen:
                seen.add(mid)
                plan.append((p, mid, kinds))
    add(1, _entity_mids(ents, P1_ENTITIES))
    add(2, _entity_mids(ents, P2_ENTITIES))
    add(3, neutral_sample(ms, neutral_n, seed), ('360',))
    add(4, _entity_mids(ents, P4_ENTITIES))
    add(4, sorted(cached_events), ('360',))
    add(5, sorted(m['match_id'] for m in ms if _sid(m) in OFFICIAL_SEASONS))
    add(6, sorted(m['match_id'] for m in ms if _sid(m) in LATE_SEASONS))
    return plan


def plan_jobs(plan: list, by_id: dict) -> list:
    """[(prioridad, ruta API)] para el plan; 360 solo donde está disponible."""
    return [(p, path) for p, mid, kinds in plan if mid in by_id for path in jobs_for_match(by_id[mid], kinds)]


def _write(path: pathlib.Path, obj: object) -> None:
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=1), encoding='utf-8')
    tmp.replace(path)


def _merge_failures(path: pathlib.Path, new: list, done: set) -> list:
    """Mantiene fallas previas no resueltas y agrega las nuevas (sin duplicar rutas)."""
    old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    by = {f['path']: f for f in old if f['path'] not in done}
    for f in new:
        by[f['path']] = dict(f, at=time.strftime('%Y-%m-%dT%H:%M:%S'))
    return sorted(by.values(), key=lambda f: f['path'])


def _progress_writer(path: pathlib.Path, priority: int):
    """Callback que guarda el avance cada PROGRESS_EVERY trabajos terminados."""
    def cb(s: dict) -> None:
        if (s['ok'] + len(s['failures'])) % PROGRESS_EVERY == 0:
            _write(path, {'priority': priority, 'running': True, 'total': s['total'], 'cached': s['cached'],
                          'ok': s['ok'], 'failures': len(s['failures']), 'updated': time.strftime('%Y-%m-%dT%H:%M:%S')})
    return cb


def coverage_by_priority(jobs: list, cache: pathlib.Path) -> dict:
    """{prioridad: {total, cached}} según los archivos presentes en la caché."""
    out: dict = {}
    for p, path in jobs:
        d = out.setdefault(str(p), {'total': 0, 'cached': 0})
        d['total'] += 1
        d['cached'] += (cache / cache_name(path)).exists()
    return out


def entity_coverage(ents: list, by_id: dict, cache: pathlib.Path, ext: pathlib.Path) -> list:
    """Filas de cobertura por entidad: partidos, eventos, lineups, 360 (disp./bajado) y mx_."""
    def has(kind: str, mid: int) -> bool:
        return (cache / cache_name(PATHS[kind].format(mid))).exists()
    rows = []
    for e in ents:
        mids = [x['mid'] for x in e['matches']]
        rows.append({'id': e['id'], 'label': e['label'], 'matches': len(mids),
                     'events': sum(has('events', m) for m in mids), 'lineups': sum(has('lineups', m) for m in mids),
                     'avail360': sum(by_id.get(m, {}).get('match_status_360') == 'available' for m in mids),
                     'f360': sum(has('360', m) for m in mids), 'mx': sum((ext / f'mx_{m}.json').exists() for m in mids)})
    return rows


def _pct(a: int, n: int) -> str:
    return f'{a} ({round(100 * a / n) if n else 0}%)'


def coverage_markdown(rows: list, stamp: str) -> str:
    """Tabla Markdown de cobertura por entidad."""
    out = [f'# Cobertura de datos por entidad ({stamp})', '',
           '360 = archivos bajados / partidos con 360 disponible en StatsBomb.', '',
           '| id | entidad | partidos | eventos | lineups | 360 | mx_ |', '|---|---|---|---|---|---|---|']
    for r in rows:
        n = r['matches']
        out.append(f"| {r['id']} | {r['label']} | {n} | {_pct(r['events'], n)} | {_pct(r['lineups'], n)} | "
                   f"{r['f360']}/{r['avail360']} | {_pct(r['mx'], n)} |")
    return '\n'.join(out) + '\n'


def stale_stubs(ext: pathlib.Path, cache: pathlib.Path) -> list:
    """mx_ inválidos cuyo evento o lineup falta en caché (extract los saltaría para siempre)."""
    out = []
    for f in sorted(ext.glob('mx_*.json')):
        if f.stat().st_size > STUB_MAX_BYTES:
            continue
        d = json.loads(f.read_text(encoding='utf-8'))
        mid = f.stem.split('_')[1]
        missing = not all((cache / cache_name(PATHS[k].format(mid))).exists() for k in ('events', 'lineups'))
        if d.get('status') == 'invalid' and missing:
            out.append(f)
    return out


def main(argv: tuple = ()) -> int:
    from entities import build_entities
    from statsbomb import CACHE, DATA, get
    ap = argparse.ArgumentParser()
    ap.add_argument('--priorities', default='1,2,3,4,5,6')
    ap.add_argument('--max-seconds', type=float, default=0.0)
    ap.add_argument('--coverage', action='store_true', help='solo escribe data/out/coverage.md')
    ap.add_argument('--clean-stubs', action='store_true', help='borra mx_ inválidos por caché faltante')
    args = ap.parse_args(list(argv) or None)
    out = DATA / 'out'
    if args.clean_stubs:
        for f in stale_stubs(DATA / 'extract', CACHE):
            print('borrando stub', f.name)
            f.unlink()
        return 0
    ents, ms = build_entities()
    if args.coverage:
        rows = entity_coverage(ents, {m['match_id']: m for m in ms}, CACHE, DATA / 'extract')
        (out / 'coverage.md').write_text(coverage_markdown(rows, time.strftime('%Y-%m-%d %H:%M')), encoding='utf-8')
        return 0
    cached_ev = {m['match_id'] for m in ms if (CACHE / cache_name(PATHS['events'].format(m['match_id']))).exists()}
    plan = build_plan(ents, ms, cached_ev)
    _write(out / 'neutral_sample.json', {'seed': NEUTRAL_SEED, 'seasons': list(NEUTRAL_SEASONS),
                                         'match_ids': neutral_sample(ms, NEUTRAL_N, NEUTRAL_SEED)})
    jobs = plan_jobs(plan, {m['match_id']: m for m in ms})
    wanted = {int(x) for x in args.priorities.split(',')}
    deadline = time.time() + args.max_seconds if args.max_seconds else 0.0
    for p in sorted(wanted):
        paths = [path for q, path in jobs if q == p]
        progress = _progress_writer(out / 'download_progress.json', p)
        st = run_jobs(paths, get, CACHE, on_progress=progress, deadline=deadline)
        done = {path for path in paths if (CACHE / cache_name(path)).exists()}
        _write(out / 'download_failures.json', _merge_failures(out / 'download_failures.json', st['failures'], done))
        print(f"P{p}: total={st['total']} cached={st['cached']} ok={st['ok']} fail={len(st['failures'])} "
              f"skipped={st['skipped_deadline']}", flush=True)
    _write(out / 'download_progress.json', {'running': False, 'updated': time.strftime('%Y-%m-%dT%H:%M:%S'),
                                            'by_priority': coverage_by_priority(jobs, CACHE)})
    return 0


if __name__ == '__main__':
    sys.exit(main())
