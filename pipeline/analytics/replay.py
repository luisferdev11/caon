"""Repetición con xG de partidos reales (AC-14) y datos de la ficha de partido.

Cada posesión con tiros es un ensayo de Bernoulli con p = 1 - Π(1 - xg) sobre sus
tiros sin penal; los penales se sortean aparte (etiquetados) y los autogoles cuentan
como goles fijos. Con 20,000 sorteos sembrados por el id del partido se estima
P(G/E/P), los puntos esperados (xPts) y si el resultado real fue sorpresivo.
Es interpretación de lo que pasó, no un pronóstico.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np

REPLAY_DRAWS = 20000           # sorteos por partido
SURPRISE_P = 0.20              # "resultado sorpresivo" si P(resultado real) < 0.20
BIG_CHANCE_XG = 0.30           # "gran ocasión": tiro con xG >= 0.30
FINAL_THIRD_X = 80.0           # último tercio (marco propio de ataque)
SHOOTOUT_PERIOD = 5            # tanda de penales: excluida
ON_BALL = ('Pass', 'Carry', 'Dribble', 'Shot')
POINTS = {'G': 3, 'E': 1, 'P': 0}


def _tname(ev: dict[str, Any]) -> str:
    return (ev.get('type') or {}).get('name', '')


def _team(ev: dict[str, Any]) -> Optional[int]:  # noqa: UP045 (Python 3.9)
    return (ev.get('team') or {}).get('id')


def _in_play(ev: dict[str, Any]) -> bool:
    return ev.get('period', 1) != SHOOTOUT_PERIOD


def _is_penalty(ev: dict[str, Any]) -> bool:
    return ((ev.get('shot') or {}).get('type') or {}).get('name') == 'Penalty'


def _xg(ev: dict[str, Any]) -> float:
    return float((ev.get('shot') or {}).get('statsbomb_xg') or 0.0)


def _is_goal(ev: dict[str, Any]) -> bool:
    return ((ev.get('shot') or {}).get('outcome') or {}).get('name') == 'Goal'


def team_shots(events: list[dict[str, Any]], team_id: int) -> list[dict[str, Any]]:
    """Tiros del equipo en juego (sin tanda de penales)."""
    return [e for e in events if _tname(e) == 'Shot' and _team(e) == team_id and _in_play(e)]


def team_chances(events: list[dict[str, Any]], team_id: int) -> dict[str, Any]:
    """Probabilidades de gol por posesión (sin penal), penales aparte y autogoles fijos."""
    by_poss: dict[Any, float] = {}
    pens: list[float] = []
    for e in team_shots(events, team_id):
        if _is_penalty(e):
            pens.append(_xg(e))
            continue
        key = (e.get('period'), e.get('possession'))
        by_poss[key] = 1.0 - (1.0 - by_poss.get(key, 0.0)) * (1.0 - _xg(e))
    own = sum(1 for e in events if _tname(e) == 'Own Goal For' and _team(e) == team_id and _in_play(e))
    return {'open': list(by_poss.values()), 'pens': pens, 'own_goals': own}


def _draw_goals(rng: np.random.Generator, probs: list[float], fixed: int, draws: int) -> np.ndarray:
    if not probs:
        return np.full(draws, fixed, dtype=np.int64)
    p = np.asarray(probs, dtype=float)
    return (rng.random((draws, p.size)) < p).sum(axis=1) + fixed


def simulate_result(probs_a: list[float], probs_b: list[float], fixed_a: int, fixed_b: int,
                    draws: int = REPLAY_DRAWS, seed: int = 0) -> dict[str, float]:
    """P(ganar/empatar/perder) del equipo A con sorteos Poisson-binomiales sembrados."""
    rng = np.random.default_rng(seed)
    ga = _draw_goals(rng, probs_a, fixed_a, draws)
    gb = _draw_goals(rng, probs_b, fixed_b, draws)
    return {'p_win': float(np.mean(ga > gb)), 'p_draw': float(np.mean(ga == gb)),
            'p_loss': float(np.mean(ga < gb))}


def field_tilt(events: list[dict[str, Any]], team_id: int) -> Optional[float]:  # noqa: UP045 (Python 3.9)
    """Acciones con balón propias en último tercio ÷ (propias + rival)."""
    own = riv = 0
    for e in events:
        loc = e.get('location')
        if _tname(e) in ON_BALL and loc and loc[0] >= FINAL_THIRD_X and _in_play(e):
            if _team(e) == team_id:
                own += 1
            else:
                riv += 1
    return own / (own + riv) if own + riv else None


def _sides(meta: dict[str, Any], team_id: int):
    home = meta['home_id'] == team_id
    rival = meta['away_id'] if home else meta['home_id']
    gf, ga = (meta['home_score'], meta['away_score']) if home else (meta['away_score'], meta['home_score'])
    return rival, gf, ga


def _round(v: Optional[float], nd: int = 4) -> Optional[float]:  # noqa: UP045
    return None if v is None else round(v, nd)


def _actual(gf: int, ga: int) -> str:
    return 'G' if gf > ga else ('E' if gf == ga else 'P')


def match_replay(events: list[dict[str, Any]], meta: dict[str, Any], team_id: int,
                 draws: int = REPLAY_DRAWS) -> dict[str, Any]:
    """Repetición de un partido desde la óptica de team_id."""
    rival, gf, ga = _sides(meta, team_id)
    own, opp = team_chances(events, team_id), team_chances(events, rival)
    sim = simulate_result(own['open'] + own['pens'], opp['open'] + opp['pens'],
                          own['own_goals'], opp['own_goals'], draws=draws, seed=int(meta['match_id']))
    actual = _actual(gf, ga)
    p_actual = {'G': sim['p_win'], 'E': sim['p_draw'], 'P': sim['p_loss']}[actual]
    xg_f = sum(_xg(e) for e in team_shots(events, team_id))
    xg_c = sum(_xg(e) for e in team_shots(events, rival))
    return {
        'match_id': meta['match_id'], 'actual': actual, 'points': POINTS[actual],
        'p': {'G': round(sim['p_win'], 4), 'E': round(sim['p_draw'], 4), 'P': round(sim['p_loss'], 4)},
        'xpts': round(3 * sim['p_win'] + sim['p_draw'], 3), 'p_actual': round(p_actual, 4),
        'sorpresivo': p_actual < SURPRISE_P,
        'xg': {'propio': round(xg_f, 3), 'rival': round(xg_c, 3)},
        'penales_xg': {'propio': round(sum(own['pens']), 3), 'rival': round(sum(opp['pens']), 3)},
        'autogoles_a_favor': own['own_goals'],
        'dominio': {'xg_share': round(xg_f / (xg_f + xg_c), 4) if xg_f + xg_c > 0 else None,
                    'field_tilt': _round(field_tilt(events, team_id))},
        'sorteos': draws, 'semilla': int(meta['match_id']),
    }


def meta_from_events(events: list[dict[str, Any]], team: str, match_id: int) -> Optional[dict[str, Any]]:  # noqa: UP045
    """Ids y marcador (goles de tiro + autogoles, sin tanda) a partir de los eventos; equipo como local."""
    ids = {}
    for e in events:
        t = e.get('team') or {}
        if t.get('id') is not None:
            ids[t.get('name')] = t['id']
    if team not in ids or len(ids) != 2:
        return None
    own = ids[team]
    rival = next(i for n, i in ids.items() if n != team)

    def goals(tid: int) -> int:
        return sum(1 for e in team_shots(events, tid) if _is_goal(e)) + team_chances(events, tid)['own_goals']
    return {'match_id': match_id, 'home_id': own, 'away_id': rival,
            'home_score': goals(own), 'away_score': goals(rival)}


def _context_matches(ctx: Any) -> tuple:
    """Adapta EntityContext del registro → (team_id, [{'meta', 'events', 'window'}])."""
    team_id, out = None, []
    for m in ctx.matches:
        events = ctx.load_events(m['id']) or []
        meta = meta_from_events(events, ctx.team, m['id'])
        if meta is None:
            continue
        team_id = meta['home_id']
        out.append({'meta': meta, 'events': events, 'window': m.get('window'), 'date': m.get('date')})
    return team_id, out


def build(ctx: Any) -> dict[str, Any]:
    """Repeticiones + resumen. ctx: EntityContext del registro, o dict {'team_id', 'matches': [{'meta', 'events'}]}."""
    if isinstance(ctx, dict):
        team_id, matches, draws = ctx['team_id'], ctx.get('matches', []), int(ctx.get('draws', REPLAY_DRAWS))
    else:
        (team_id, matches), draws = _context_matches(ctx), REPLAY_DRAWS
    rows = []
    for m in matches:
        rep = match_replay(m['events'], m['meta'], team_id, draws=draws)
        rep['ficha'] = match_card(m['events'], m['meta'], team_id)
        rep['window'], rep['fecha'] = m.get('window'), m.get('date')
        rows.append(rep)
    pts = sum(r['points'] for r in rows)
    xpts = sum(r['xpts'] for r in rows)
    return {'resumen': {'n': len(rows), 'puntos': pts, 'xpts': round(xpts, 2),
                        'diferencia': round(pts - xpts, 2),
                        'sorpresivos': sum(1 for r in rows if r['sorpresivo']),
                        'nota': 'Repetición con el xG de los tiros reales: interpretación, no pronóstico.'},
            'partidos': rows}


def _moments(events: list[dict[str, Any]], team_id: int, rival: int) -> list[dict[str, Any]]:
    out = []
    for side, tid in (('propio', team_id), ('rival', rival)):
        for e in team_shots(events, tid):
            goal, xg = _is_goal(e), _xg(e)
            if goal or xg >= BIG_CHANCE_XG:
                out.append({'minuto': int(e.get('minute', 0)), 'equipo': side,
                            'tipo': 'gol' if goal else 'gran_ocasion', 'xg': round(xg, 2),
                            'jugador': (e.get('player') or {}).get('name'), 'penal': _is_penalty(e)})
    for e in events:
        if _tname(e) == 'Own Goal For' and _in_play(e):
            out.append({'minuto': int(e.get('minute', 0)), 'tipo': 'autogol', 'xg': None, 'jugador': None,
                        'equipo': 'propio' if _team(e) == team_id else 'rival', 'penal': False})
    return sorted(out, key=lambda m: m['minuto'])


def xg_timeline(events: list[dict[str, Any]], team_id: int, rival: int) -> list[dict[str, Any]]:
    """xG acumulado por minuto con un punto en cada minuto con tiro (más 0 y el final)."""
    shots = sorted(team_shots(events, team_id) + team_shots(events, rival), key=lambda e: e.get('minute', 0))
    acc = {'propio': 0.0, 'rival': 0.0}
    points = [{'minuto': 0, 'propio': 0.0, 'rival': 0.0}]
    for e in shots:
        acc['propio' if _team(e) == team_id else 'rival'] += _xg(e)
        row = {'minuto': int(e.get('minute', 0)), 'propio': round(acc['propio'], 2), 'rival': round(acc['rival'], 2)}
        if points[-1]['minuto'] == row['minuto']:
            points[-1] = row
        else:
            points.append(row)
    return points


def fun_facts(events: list[dict[str, Any]], team_id: int, rival: int) -> list[str]:
    """Tres datos curiosos calculados del partido (texto es-MX)."""
    own, opp = team_shots(events, team_id), team_shots(events, rival)
    best = max(own + opp, key=_xg, default=None)
    facts = [f'Tiros: {len(own)} propios contra {len(opp)} del rival.']
    if best is not None:
        quien = 'propia' if _team(best) == team_id else 'del rival'
        facts.append(f"La ocasión más clara ({quien}) fue al minuto {best.get('minute', 0)}, "
                     f'con {round(100 * _xg(best))}% de probabilidad de gol.')
    else:
        facts.append('Ningún equipo remató en todo el partido.')
    tilt = field_tilt(events, team_id)
    facts.append('Sin datos de territorio.' if tilt is None else
                 f'De cada 100 acciones en un último tercio, {round(100 * tilt)} fueron propias.')
    return facts


def match_card(events: list[dict[str, Any]], meta: dict[str, Any], team_id: int) -> dict[str, Any]:
    """Datos de la ficha de partido: marcador, momentos clave, xG acumulado y 3 datos curiosos."""
    rival, gf, ga = _sides(meta, team_id)
    return {'match_id': meta['match_id'], 'marcador': {'propio': gf, 'rival': ga},
            'momentos': _moments(events, team_id, rival),
            'xg_acumulado': xg_timeline(events, team_id, rival),
            'datos_curiosos': fun_facts(events, team_id, rival)}


def _coached_by(side: dict, coach: str) -> bool:
    mgrs = side.get('managers') or []
    return not coach or (len(mgrs) == 1 and any(coach in (mgrs[0].get(k) or '') for k in ('name', 'nickname')))


def load_matches(team: str, since: str, until: str, coach: str = '',
                 cache: Optional[Any] = None) -> tuple:  # noqa: UP045
    """IO: partidos de `team` (con DT único `coach`) en [since, until] con eventos v8 → (team_id, matches)."""
    import json
    import pathlib
    cache = pathlib.Path(cache or pathlib.Path(__file__).resolve().parents[2] / 'data' / 'cache')
    team_id, out = None, []
    for mf in sorted(cache.glob('v6_competitions_73_seasons_*_matches.json')):
        for m in json.loads(mf.read_text(encoding='utf-8')):
            h, a = m['home_team'], m['away_team']
            if team not in (h['home_team_name'], a['away_team_name']) or not since <= m['match_date'] <= until:
                continue
            ev = cache / f"v8_events_{m['match_id']}.json"
            own_side = h if h['home_team_name'] == team else a
            if not ev.exists() or not _coached_by(own_side, coach):
                continue
            team_id = h['home_team_id'] if h['home_team_name'] == team else a['away_team_id']
            meta = {'match_id': m['match_id'], 'date': m['match_date'], 'home_id': h['home_team_id'],
                    'away_id': a['away_team_id'], 'home_score': m['home_score'], 'away_score': m['away_score'],
                    'home': h['home_team_name'], 'away': a['away_team_name']}
            out.append({'meta': meta, 'events': json.loads(ev.read_text(encoding='utf-8'))})
    return team_id, sorted(out, key=lambda m: m['meta']['date'])


def main() -> None:
    """CLI: --team América --since 2023-07-01 --until 2025-06-30 --out ruta.json."""
    import argparse
    import json
    import pathlib
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from framework import OFFICIAL_END
    ap = argparse.ArgumentParser()
    ap.add_argument('--team', default='América')
    ap.add_argument('--since', default='2023-07-01')
    ap.add_argument('--until', default='2025-06-30')
    ap.add_argument('--coach', default='Jardine')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    team_id, matches = load_matches(args.team, args.since, args.until, args.coach)
    out = build({'team_id': team_id, 'matches': matches})
    for row, m in zip(out['partidos'], matches):
        row['fecha'], row['local'], row['visita'] = m['meta']['date'], m['meta']['home'], m['meta']['away']
        row['window'] = 'oficial' if m['meta']['date'] <= OFFICIAL_END else 'epilogo'
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(json.dumps(out['resumen'], ensure_ascii=False))


def _register() -> None:
    try:
        from analytics import register  # type: ignore
    except ImportError:
        return
    register('replay', build)


_register()

if __name__ == '__main__':
    main()
