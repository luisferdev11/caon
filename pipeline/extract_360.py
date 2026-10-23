# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Extracción 360 por partido → data/extract/f360_<mid>.json (registros por evento, ambos equipos).

Une cada frame 360 con su evento v8 por id (``event['id'] == frame['event_uuid']``) y calcula, para
cada equipo X en su propio marco (ver frames360.view), tablas columnares compactas:
perdidas (contexto del error + vigilancias en la recuperación rival), bloque (pases rivales en
ataque establecido), salida (altura de línea con balón x<60), rompe (pases adelante completados),
presion, corner_def, saque_meta (cordura de orientación) y fotos de jugadas peligrosas (tiros).
Uso: flock data/out/heavy.lock .venv/bin/python -X utf8 pipeline/extract_360.py [--force]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys
import time
from collections.abc import Iterable, Sequence
from multiprocessing import Pool
from typing import Any, Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import frames360 as f3
from extract import ADMIN, ts
from framework import (
    OUTCOME_WINDOW_S,
    SALIDA_LIMPIA,
    TRANSITION_PHASE_S,
    to_frame,
    zone,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data' / 'cache'
OUT = ROOT / 'data' / 'extract'
SUMMARY = ROOT / 'data' / 'out' / 'f360_coverage.json'
VERSION = 1
POOL_SIZE = 4
OPEN_PATTERNS = {'Regular Play', 'From Counter'}   # = DISENO "origen regain_open"
BUILDUP_MAX_X = SALIDA_LIMPIA[1]                   # salida: pases propios con x < 60
LOSS_TYPES = {'Pass': 'pase', 'Carry': 'conduccion', 'Dribble': 'duelo', 'Dispossessed': 'duelo',
              'Miscontrol': 'duelo', 'Clearance': 'despeje', 'Ball Receipt*': 'control', 'Shot': 'tiro'}
REGAIN_TYPES = {'Ball Recovery', 'Interception', 'Pass', 'Carry', 'Ball Receipt*', 'Duel', 'Clearance',
                'Block', 'Goal Keeper', 'Dribble', 'Shot', 'Miscontrol'}

LOSS_COLS = ('team', 'player', 'eid', 'rid', 'period', 't', 'x', 'y', 'kind', 'xpass', 'up', 'fwd',
             'shot15', 'goal15', 'tipo', 'err_linked', 'err_valid', 'tm10', 'op5', 'op3', 'nearest',
             'isolated', 'vig_linked', 'vig_valid', 'vig_gs', 'vig_central', 'vig_ahead', 'vig_sup')
TABLE_COLS = {
    'perdidas': LOSS_COLS,
    'bloque': ('team', 'eid', 'period', 't', 'bx', 'by', 'zone', 'n_vis', 'last_line', 'length', 'width',
               'hull_area', 'between', 'valid'),
    'salida': ('team', 'eid', 'period', 't', 'bx', 'n_vis', 'height', 'valid'),
    'rompe': ('team', 'eid', 'period', 't', 'x0', 'x1', 'lbp', 'bypassed', 'valid'),
    'presion': ('team', 'eid', 'period', 't', 'x', 'y', 'counterpress', 'support', 'free_options', 'valid'),
    'corner_def': ('team', 'eid', 'period', 't', 'def_box', 'def_six', 'att_box', 'near_post', 'far_post',
                   'pairing', 'unpaired_six', 'marking', 'valid'),
    'saque_meta': ('team', 'eid', 'period', 't', 'kick_mean_x', 'def_mean_x', 'n_kick', 'n_def', 'valid'),
}


# ---------------------------------------------------------------- helpers de eventos
def tname(e: dict[str, Any]) -> str:
    return e['type']['name']


def pass_type(e: dict[str, Any]) -> Optional[str]:
    return ((e.get('pass') or {}).get('type') or {}).get('name')


def possessions(events: Sequence[dict[str, Any]]) -> list[tuple[int, list[dict[str, Any]]]]:
    """Agrupa por id de posesión StatsBomb, en orden de índice."""
    groups: dict[int, list[dict[str, Any]]] = collections.OrderedDict()
    for e in sorted(events, key=lambda e: e.get('index', 0)):
        groups.setdefault(e.get('possession', 0), []).append(e)
    return [(k, v) for k, v in groups.items()]


def is_admin(pe: Sequence[dict[str, Any]]) -> bool:
    return all(tname(e) in ADMIN for e in pe)


def poss_team(pe: Sequence[dict[str, Any]]) -> Optional[int]:
    return (pe[0].get('possession_team') or {}).get('id') if pe else None


def rpt(loc: Sequence[float]) -> tuple[float, float]:
    """Punto redondeado a 0.1 yd (precisión de StatsBomb)."""
    return (round(loc[0], 1), round(loc[1], 1))


def base(team: int, e: dict[str, Any]) -> list[Any]:
    return [team, e['id'], e.get('period'), round(ts(e), 1)]


def _rows(cols: Sequence[str], recs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return {'cols': list(cols), 'rows': [[r.get(c) for c in cols] for r in recs]}


def rows_as_dicts(table: dict[str, Any]) -> list[dict[str, Any]]:
    """Tabla columnar → lista de dicts (para análisis y tests)."""
    return [dict(zip(table['cols'], r)) for r in table['rows']]


# ---------------------------------------------------------------- pérdidas
def _last_onball(pe: Sequence[dict[str, Any]], team: int) -> Optional[dict[str, Any]]:
    for e in reversed(pe):
        if e['team']['id'] != team or tname(e) not in LOSS_TYPES or 'location' not in e:
            continue
        if tname(e) == 'Ball Receipt*' and 'outcome' in (e.get('ball_receipt') or {}):
            continue
        return e
    return None


def _first_regain(qe: Sequence[dict[str, Any]], team: int) -> Optional[dict[str, Any]]:
    return next((e for e in qe if e['team']['id'] == team and tname(e) in REGAIN_TYPES
                 and 'location' in e), None)


def find_losses(events: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pérdidas en juego: la siguiente posesión no administrativa es rival y en juego abierto."""
    poss = [pe for _, pe in possessions(events)]
    out = []
    for i, pe in enumerate(poss):
        team = poss_team(pe)
        nxt = next((q for q in poss[i + 1:] if not is_admin(q)), None)
        if team is None or nxt is None or poss_team(nxt) == team:
            continue
        if nxt[0]['play_pattern']['name'] not in OPEN_PATTERNS:
            continue
        err = _last_onball(pe, team)
        regain = _first_regain(nxt, poss_team(nxt))
        if err is None or regain is None or tname(err) == 'Shot':
            continue
        out.append({'team': team, 'err': err, 'regain': regain, 'rival': nxt})
    return out


def loss_kind(err: dict[str, Any]) -> str:
    """Tipo de acción que perdió el balón (un regate completado cuenta como conducción)."""
    if tname(err) == 'Dribble' and ((err.get('dribble') or {}).get('outcome') or {}).get('name') == 'Complete':
        return 'conduccion'
    return LOSS_TYPES[tname(err)]


def _shot_after(rival: Sequence[dict[str, Any]], t0: float) -> tuple[bool, bool]:
    shots = [e for e in rival if tname(e) == 'Shot' and ts(e) - t0 <= OUTCOME_WINDOW_S]
    goal = any((e['shot'].get('outcome') or {}).get('name') == 'Goal' for e in shots)
    return bool(shots), goal


def loss_record(loss: dict[str, Any], frames: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Registro de una pérdida: datos del evento + contexto 360 del error y vigilancias."""
    err, reg, team = loss['err'], loss['regain'], loss['team']
    p = err.get('pass') or {}
    fwd = bool(p.get('end_location')) and p['end_location'][0] > err['location'][0]
    shot, goal = _shot_after(loss['rival'], ts(reg))
    r: dict[str, Any] = {'team': team, 'player': (err.get('player') or {}).get('id'), 'eid': err['id'],
                         'rid': reg['id'], 'period': err.get('period'), 't': round(ts(err), 1),
                         'x': err['location'][0], 'y': err['location'][1], 'kind': loss_kind(err),
                         'xpass': p.get('pass_success_probability'), 'up': bool(err.get('under_pressure')),
                         'fwd': fwd, 'shot15': shot, 'goal15': goal, 'err_linked': err['id'] in frames,
                         'vig_linked': reg['id'] in frames}
    if r['err_linked']:
        c = f3.error_context(f3.view(frames[err['id']], True), tuple(err['location']))
        r.update(err_valid=c['valid'], tm10=c['teammates_near'], op5=c['opps_near'],
                 op3=c['opps_pressing'], nearest=c['nearest_opp'], isolated=c['isolated'])
    if r['vig_linked']:
        g = f3.rest_defense(f3.view(frames[reg['id']], False), tuple(to_frame(reg['location'], True)))
        r.update(vig_valid=g['valid'], vig_gs=g['own_goal_side'], vig_central=g['own_central'],
                 vig_ahead=g['opp_ahead'], vig_sup=g['superiority'])
    if r['kind'] == 'pase' and 'outcome' not in p and tname(err) == 'Pass':
        r['kind'] = 'pase_completo'  # el pase llegó; la pérdida vino después (p. ej. control rival)
    r['tipo'] = f3.classify_error(r['kind'], r['xpass'], r['up'], fwd, r.get('op3'))
    return r


# ---------------------------------------------------------------- tablas por evento
def _other(teams: Sequence[int], team: int) -> Optional[int]:
    return next((t for t in teams if t != team), None)


def _poss_start(events: Sequence[dict[str, Any]]) -> dict[int, float]:
    return {k: ts(pe[0]) for k, pe in possessions(events)}


def event_tables(events: Sequence[dict[str, Any]], frames: dict[str, dict[str, Any]],
                 teams: Sequence[int]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, collections.Counter]]:
    """Recorre eventos enlazados y llena las tablas por evento; cuenta candidatos por tabla/equipo."""
    tabs: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    cand: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    start = _poss_start(events)
    for e in events:
        if 'location' not in e or 'team' not in e:
            continue
        team, rival = e['team']['id'], _other(teams, e['team']['id'])
        for name, team_x, rec in _event_records(e, team, rival, frames, start):
            cand[name][str(team_x)] += 1
            if rec is not None:
                tabs[name].append(rec)
    return tabs, cand


def _event_records(e: dict[str, Any], team: int, rival: Optional[int], frames: dict[str, dict[str, Any]],
                   start: dict[int, float]) -> list[tuple[str, int, Optional[dict[str, Any]]]]:
    """(tabla, equipo X, registro o None si no hay frame) para un evento."""
    out: list[tuple[str, int, Optional[dict[str, Any]]]] = []
    fr = frames.get(e['id'])
    kind, ptype, loc = tname(e), pass_type(e), e['location']
    head = dict(zip(('team', 'eid', 'period', 't'), base(team, e)))
    if kind == 'Pass' and ptype is None:
        out += _pass_records(e, head, rival, fr, start)
    if kind == 'Pass' and ptype in ('Corner', 'Goal Kick') and rival is not None:
        rec = None
        if fr is not None:
            v = f3.view(fr, False)
            rec = dict(head, team=rival)
            if ptype == 'Corner':
                rec.update(f3.corner_organization(v, tuple(to_frame(loc, True))))
            else:
                kick = v['opp'] + v['opp_gk']
                rec.update(kick_mean_x=f3.rnd(f3.mean_x(kick)), def_mean_x=f3.rnd(f3.mean_x(v['own'])),
                           n_kick=len(kick), n_def=len(v['own']), valid=bool(kick))
        out.append(('corner_def' if ptype == 'Corner' else 'saque_meta', rival, rec))
    if kind == 'Pressure':
        rec = None
        if fr is not None:
            rec = dict(head, x=loc[0], y=loc[1], counterpress=bool(e.get('counterpress')))
            rec.update(f3.coordinated_pressure(f3.view(fr, True), tuple(loc)))
        out.append(('presion', team, rec))
    return out


def _pass_records(e: dict[str, Any], head: dict[str, Any], rival: Optional[int],
                  fr: Optional[dict[str, Any]], start: dict[int, float]) -> list[tuple[str, int, Any]]:
    """Pases de juego abierto: salida (x<60), rompe-líneas (adelante, completado) y bloque rival."""
    out: list[tuple[str, int, Any]] = []
    loc, p, team = e['location'], e.get('pass') or {}, head['team']
    v = f3.view(fr, True) if fr is not None else None
    if loc[0] < BUILDUP_MAX_X:
        rec = dict(head, bx=loc[0], **f3.line_height(v, tuple(loc))) if v else None
        if rec:
            rec['height'] = f3.rnd(rec['height'])
        out.append(('salida', team, rec))
    end = p.get('end_location')
    if end and 'outcome' not in p and end[0] > loc[0]:
        rec = dict(head, x0=loc[0], x1=end[0], lbp=fr.get('line_breaking_pass'),
                   **f3.packing(v, tuple(loc), tuple(end))) if v else None
        out.append(('rompe', team, rec))
    established = ts(e) - start.get(e.get('possession', 0), ts(e)) >= TRANSITION_PHASE_S
    if rival is not None and established and e['play_pattern']['name'] == 'Regular Play':
        rec = None
        if fr is not None:
            ball = rpt(to_frame(loc, True))
            rec = dict(head, team=rival, bx=ball[0], by=ball[1], zone=zone(ball),
                       **f3.block_shape(f3.view(fr, False), ball))
        out.append(('bloque', rival, rec))
    return out


# ---------------------------------------------------------------- fotos de jugadas peligrosas
def _shot_ff(shot: dict[str, Any]) -> list[list[float]]:
    """freeze_frame v8 del tiro (marco del tirador) → marco del defensor, códigos de compact_points."""
    pts = []
    for p in (shot.get('shot') or {}).get('freeze_frame') or []:
        x, y = to_frame(p['location'], True)
        gk = (p.get('position') or {}).get('name') == 'Goalkeeper'
        code = (f3.CODE_OPP_GK if gk else f3.CODE_OPP) if p.get('teammate') else \
            (f3.CODE_OWN_GK if gk else f3.CODE_OWN)
        pts.append([round(x, 1), round(y, 1), code])
    x, y = to_frame(shot['location'], True)
    return pts + [[round(x, 1), round(y, 1), f3.CODE_ACTOR]]


def snapshots(events: Sequence[dict[str, Any]], frames: dict[str, dict[str, Any]],
              teams: Sequence[int]) -> list[dict[str, Any]]:
    """Por tiro: foto del pase clave (360) y freeze_frame del tiro, en el marco del equipo que defiende."""
    out = []
    for e in events:
        if tname(e) != 'Shot':
            continue
        s, kp = e['shot'], e['shot'].get('key_pass_id')
        out.append({'team': _other(teams, e['team']['id']), 'shooter_team': e['team']['id'], 'eid': e['id'],
                    'period': e.get('period'), 't': round(ts(e), 1), 'xg': s.get('statsbomb_xg'),
                    'goal': (s.get('outcome') or {}).get('name') == 'Goal',
                    'penalty': (s.get('type') or {}).get('name') == 'Penalty',
                    'pattern': e['play_pattern']['name'], 'kp': kp,
                    'kp_pts': f3.compact_points(f3.view(frames[kp], False)) if kp in frames else None,
                    'ff': _shot_ff(e)})
    return out


# ---------------------------------------------------------------- partido
def _coverage(tabs: dict[str, list[dict[str, Any]]], cand: dict[str, collections.Counter],
              teams: Sequence[int]) -> dict[str, dict[str, dict[str, int]]]:
    cov: dict[str, dict[str, dict[str, int]]] = {}
    for name in TABLE_COLS:
        cov[name] = {}
        for t in teams:
            rows = [r for r in tabs.get(name, []) if r['team'] == t]
            c = {'candidates': cand.get(name, {}).get(str(t), len(rows)), 'rows': len(rows),
                 'valid': sum(1 for r in rows if r.get('valid'))}
            if name == 'perdidas':
                c = {'rows': len(rows), **{k: sum(1 for r in rows if r.get(k)) for k in
                                          ('err_linked', 'err_valid', 'vig_linked', 'vig_valid')}}
            cov[name][str(t)] = c
    return cov


def extract_match(mid: int, events: Sequence[dict[str, Any]], frames_list: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Función pura: eventos v8 + frames 360 de un partido → payload f360."""
    frames = {f['event_uuid']: f for f in frames_list}
    ids = {e['id'] for e in events}
    teams = sorted({e['team']['id'] for e in events if 'team' in e})
    tabs, cand = event_tables(events, frames, teams)
    tabs['perdidas'] = [loss_record(x, frames) for x in find_losses(events)]
    return {'mid': mid, 'version': VERSION, 'teams': teams, 'n_frames': len(frames),
            'n_linked': sum(1 for k in frames if k in ids),
            'tables': {n: _rows(c, tabs.get(n, [])) for n, c in TABLE_COLS.items()},
            'snapshots': snapshots(events, frames, teams), 'coverage': _coverage(tabs, cand, teams)}


def is_up_to_date(out: pathlib.Path, sources: Sequence[pathlib.Path]) -> bool:
    """True si la salida existe, tiene la versión actual y es más nueva que sus fuentes."""
    if not out.exists() or any(out.stat().st_mtime < s.stat().st_mtime for s in sources):
        return False
    try:
        return json.loads(out.read_text(encoding='utf-8')).get('version') == VERSION
    except (OSError, ValueError):
        return False


def process(args: tuple[int, bool]) -> dict[str, Any]:
    """IO de un partido (para el Pool): lee caché, extrae y escribe f360_<mid>.json."""
    mid, force = args
    src = [CACHE / f'v8_events_{mid}.json', CACHE / f'v2_360-frames_{mid}.json']
    out = OUT / f'f360_{mid}.json'
    if not force and is_up_to_date(out, src):
        return {'mid': mid, 'status': 'skip'}
    try:
        ev, fr = (json.loads(p.read_text(encoding='utf-8')) for p in src)
        res = extract_match(mid, ev, fr)
    except (KeyError, TypeError, ValueError, OSError, IndexError) as exc:
        return {'mid': mid, 'status': 'error', 'reason': f'{type(exc).__name__}: {exc}'}
    out.write_text(json.dumps(res, ensure_ascii=False, allow_nan=False, separators=(',', ':')),
                   encoding='utf-8')
    return {'mid': mid, 'status': 'ok', 'n_frames': res['n_frames'], 'n_linked': res['n_linked']}


def jobs() -> list[int]:
    """Partidos con eventos v8 y frames 360 en caché."""
    mids = [int(p.stem.rsplit('_', 1)[1]) for p in CACHE.glob('v2_360-frames_*.json')]
    return sorted(m for m in mids if (CACHE / f'v8_events_{m}.json').exists())


def main(argv: Sequence[str]) -> None:
    force = '--force' in argv
    mids, t0, res = jobs(), time.time(), []
    with Pool(POOL_SIZE) as pool:
        for k, r in enumerate(pool.imap_unordered(process, [(m, force) for m in mids], chunksize=2)):
            res.append(r)
            if k % 50 == 0:
                print(k, len(mids), flush=True)
    stat = collections.Counter(r['status'] for r in res)
    summary = {'version': VERSION, 'matches': len(mids), 'status': dict(stat),
               'seconds': round(time.time() - t0, 1), 'errors': [r for r in res if r['status'] == 'error']}
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=1), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False)[:2000])


if __name__ == '__main__':
    main(sys.argv[1:])
