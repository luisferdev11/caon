# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Repetición con xG de partidos reales (AC-14) y datos de la ficha de partido.

Cada posesión con tiros es un ensayo de Bernoulli con p = 1 - Π(1 - xg) sobre sus tiros sin penal; los
penales se sortean aparte (etiquetados) y los autogoles cuentan como goles fijos. Con 20,000 sorteos
sembrados por el id del partido se estima P(G/E/P), los puntos esperados (xPts), si el resultado real fue
sorpresivo y el veredicto "¿mereció ganar?". Es interpretación de lo que pasó, no un pronóstico.
Contexto: ``EntityContext`` del registro, o dict ``{'team_id', 'matches': [{'meta', 'events'}]}``.
"""
from __future__ import annotations

import collections
import pathlib
import sys
from collections.abc import Iterable
from typing import Any, Optional

import numpy as np

if __name__ == '__main__':  # ejecutado como script: pipeline/ en sys.path
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import framework as fw

from analytics.match_xg import (
    field_tilt,
    is_goal,
    match_card,
    shot_xg,
    sides,
    team_chances,
    team_shots,
)

REPLAY_DRAWS = 20000           # sorteos por partido
DESERVED_P = 0.50              # "mereció ganar / perder" si esa probabilidad es ≥ 0.50
BALANCE_PTS = 1.0              # |puntos − xPts| ≤ 1 → resultado acorde a las ocasiones
EPILOGUE_END = getattr(fw, 'EPILOGUE_END', '2026-06-30')  # fin del epílogo (= build_analysis.EPILOGUE_END)
APERTURA_FIRST_MONTH = 7       # julio–diciembre = Apertura; enero–junio = Clausura
POINTS = {'G': 3, 'E': 1, 'P': 0}
NOTE = ('Repetición con el xG de los tiros reales: interpretación, no pronóstico. Penales con su xG, '
        'autogoles como goles fijos, tanda de penales excluida.')
VERDICT_TITLES = {'merecio_ganar': 'Mereció ganar', 'parejo': 'Partido parejo', 'merecio_perder': 'Mereció perder'}
BALANCE_TEXTS = {'por_encima': 'Sacó más puntos de lo que generó.', 'acorde': 'El resultado fue acorde a las ocasiones.',
                 'por_debajo': 'Mereció más puntos de los que sacó.'}
TEXTOS = {'veredicto': VERDICT_TITLES, 'balance': BALANCE_TEXTS,
          'resultado': {'G': 'Ganó', 'E': 'Empató', 'P': 'Perdió'}}


def window_of(date: Optional[str]) -> Optional[str]:
    """Ventana por fecha: oficial (≤ OFFICIAL_END), epilogo (temporada 2025/26) o temprano (después)."""
    if not date:
        return None
    day = str(date)[:10]
    if day <= fw.OFFICIAL_END:
        return 'oficial'
    return 'epilogo' if day <= EPILOGUE_END else 'temprano'


def tournament_of(date: Optional[str]) -> Optional[str]:
    """Torneo de Liga MX por fecha: 'Ap2023' (jul–dic) o 'Cl2024' (ene–jun); liguilla incluida."""
    if not date:
        return None
    year, month = int(date[:4]), int(date[5:7])
    return f"{'Ap' if month >= APERTURA_FIRST_MONTH else 'Cl'}{year}"


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


def _actual(gf: int, ga: int) -> str:
    return 'G' if gf > ga else ('E' if gf == ga else 'P')


def match_replay(events: list[dict[str, Any]], meta: dict[str, Any], team_id: int,
                 draws: int = REPLAY_DRAWS) -> dict[str, Any]:
    """Repetición de un partido desde la óptica de team_id."""
    rival, gf, ga, venue = sides(meta, team_id)
    own, opp = team_chances(events, team_id), team_chances(events, rival)
    sim = simulate_result(own['open'] + own['pens'], opp['open'] + opp['pens'],
                          own['own_goals'], opp['own_goals'], draws=draws, seed=int(meta['match_id']))
    actual = _actual(gf, ga)
    p_actual = {'G': sim['p_win'], 'E': sim['p_draw'], 'P': sim['p_loss']}[actual]
    xg_f = sum(shot_xg(e) for e in team_shots(events, team_id))
    xg_c = sum(shot_xg(e) for e in team_shots(events, rival))
    tilt = field_tilt(events, team_id)
    return {
        'match_id': meta['match_id'], 'actual': actual, 'points': POINTS[actual], 'localia': venue,
        'p': {'G': round(sim['p_win'], 4), 'E': round(sim['p_draw'], 4), 'P': round(sim['p_loss'], 4)},
        'xpts': round(3 * sim['p_win'] + sim['p_draw'], 3), 'p_actual': round(p_actual, 4),
        'sorpresivo': p_actual < fw.SURPRISE_P,
        'xg': {'propio': round(xg_f, 3), 'rival': round(xg_c, 3)},
        'penales_xg': {'propio': round(sum(own['pens']), 3), 'rival': round(sum(opp['pens']), 3)},
        'autogoles_a_favor': own['own_goals'],
        'dominio': {'xg_share': round(xg_f / (xg_f + xg_c), 4) if xg_f + xg_c > 0 else None,
                    'field_tilt': None if tilt is None else round(tilt, 4)},
    }


def verdict(rep: dict[str, Any]) -> dict[str, Any]:
    """¿Mereció ganar? según P(G/E/P) de la repetición, y balance puntos reales contra xPts (títulos en TEXTOS)."""
    p = rep['p']
    kind = 'merecio_ganar' if p['G'] >= DESERVED_P else ('merecio_perder' if p['P'] >= DESERVED_P else 'parejo')
    diff = rep['points'] - rep['xpts']
    balance = 'por_encima' if diff > BALANCE_PTS else ('por_debajo' if diff < -BALANCE_PTS else 'acorde')
    pct = {k: round(100 * v) for k, v in p.items()}
    text = (f"Con estas ocasiones ganaba {pct['G']} de cada 100 veces, empataba {pct['E']} "
            f"y perdía {pct['P']}.")
    return {'veredicto': kind, 'texto': text, 'balance': balance}


def _side_name(m: dict[str, Any], meta: dict[str, Any], venue: str, own: bool) -> Optional[str]:
    side = ('home' if venue == 'local' else 'away') if own else ('away' if venue == 'local' else 'home')
    return meta.get(f'{side}_name') or meta.get(side)


def replay_row(m: dict[str, Any], team_id: int, draws: int = REPLAY_DRAWS,
               team: Optional[str] = None, entity: Optional[str] = None) -> dict[str, Any]:
    """Fila completa de un partido: repetición, fecha, ventana, torneo, equipos y ficha con veredicto."""
    meta, events = m['meta'], m['events']
    rep = match_replay(events, meta, team_id, draws=draws)
    fecha = m.get('date') or meta.get('date')
    rep.update({'fecha': fecha, 'window': m.get('window') or window_of(fecha), 'torneo': tournament_of(fecha),
                'equipo': team or _side_name(m, meta, rep['localia'], own=True),
                'rival': m.get('opponent') or _side_name(m, meta, rep['localia'], own=False), 'entity': entity})
    rep['ficha'] = dict(match_card(events, meta, team_id), merecio=verdict(rep))
    rep['veredicto'] = rep['ficha']['merecio']['veredicto']
    return rep


def _mean_of(rows: list[dict[str, Any]], key: str) -> Optional[float]:
    vals = [r['dominio'][key] for r in rows if (r.get('dominio') or {}).get(key) is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Puntos reales contra xPts de un conjunto de partidos (ventana única o 'mixta') y dominio medio."""
    n, pts = len(rows), sum(r['points'] for r in rows)
    xpts = sum(r['xpts'] for r in rows)
    wins = {r.get('window') for r in rows}
    return {'n': n, 'puntos': pts, 'xpts': round(xpts, 2), 'diferencia': round(pts - xpts, 2),
            'puntos_por_partido': round(pts / n, 2) if n else None,
            'xpts_por_partido': round(xpts / n, 2) if n else None,
            'sorpresivos': sum(1 for r in rows if r['sorpresivo']),
            'dominio': {'xg_share': _mean_of(rows, 'xg_share'), 'field_tilt': _mean_of(rows, 'field_tilt')},
            'window': (wins.pop() if len(wins) == 1 else 'mixta') if rows else None}


def by_tournament(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resumen por torneo (Apertura/Clausura), en orden cronológico."""
    groups: dict[Optional[str], list] = collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: r.get('fecha') or ''):
        groups[r.get('torneo')].append(r)
    return [dict(summarize(g), torneo=t) for t, g in groups.items()]


def window_records(summary: dict[str, Any], window: str, entity: Optional[str]) -> list[dict[str, Any]]:
    """Registros del contrato para una ventana: xPts por partido y proporción de resultados sorpresivos."""
    n = summary['n']
    extra = {} if entity is None else {'entity': entity}
    share = summary['sorpresivos'] / n if n else None
    return [fw.metric('xpts', summary['xpts_por_partido'], n, 'puntos por partido', 'eventos', window,
                      puntos_por_partido=summary['puntos_por_partido'], **extra),
            fw.metric('resultado_sorpresivo', share, n, 'proporción de partidos', 'eventos', window,
                      conteo=summary['sorpresivos'], **extra)]


def by_window(rows: list[dict[str, Any]], entity: Optional[str] = None) -> dict[str, Any]:
    """Resumen por ventana con sus registros de métrica; las conclusiones solo usan 'oficial'."""
    groups: dict[str, list] = collections.defaultdict(list)
    for r in rows:
        groups[r.get('window') or 'sin_fecha'].append(r)
    out = {}
    for w, g in groups.items():
        summ = summarize(g)
        if w in fw.WINDOWS:
            summ['metricas'] = window_records(summ, w, entity)
        out[w] = summ
    return out


def meta_from_events(events: list[dict[str, Any]], team: str, match_id: int) -> Optional[dict[str, Any]]:
    """Ids y marcador (goles de tiro + autogoles, sin tanda) desde los eventos; el equipo como local."""
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
        return sum(1 for e in team_shots(events, tid) if is_goal(e)) + team_chances(events, tid)['own_goals']
    return {'match_id': match_id, 'home_id': own, 'away_id': rival,
            'home_score': goals(own), 'away_score': goals(rival)}


def meta_from_row(m: dict[str, Any], events: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Metadatos desde la fila del calendario (team_id, venue, score) y el id rival visto en los eventos."""
    team_id, score = m.get('team_id'), m.get('score') or [None, None]
    rivals = {(e.get('team') or {}).get('id') for e in events} - {None, team_id}
    if team_id is None or len(rivals) != 1 or None in score or m.get('venue') not in ('local', 'visita'):
        return None
    rival = rivals.pop()
    home = m['venue'] == 'local'
    return {'match_id': m['id'], 'home_id': team_id if home else rival, 'away_id': rival if home else team_id,
            'home_score': score[0] if home else score[1], 'away_score': score[1] if home else score[0]}


def _context_matches(ctx: Any) -> tuple:
    """Adapta EntityContext del registro → (team_id, [{'meta', 'events', 'date', 'window', 'opponent'}])."""
    team_id, out = None, []
    for m in ctx.matches:
        events = ctx.load_events(m['id']) or []
        meta = (meta_from_row(m, events) or meta_from_events(events, ctx.team, m['id'])) if events else None
        if meta is None:
            continue
        team_id = m.get('team_id') or meta['home_id']
        out.append({'meta': meta, 'events': events, 'window': m.get('window'), 'date': m.get('date'),
                    'opponent': m.get('opponent')})
    return team_id, out


def _unpack(ctx: Any) -> tuple:
    """(team_id, partidos, sorteos, equipo, entidad, partidos del calendario) para dict o EntityContext."""
    if isinstance(ctx, dict):
        matches = list(ctx.get('matches', []))
        return (ctx['team_id'], matches, int(ctx.get('draws', REPLAY_DRAWS)), ctx.get('team'),
                ctx.get('entity_id'), len(matches))
    team_id, matches = _context_matches(ctx)
    return team_id, matches, REPLAY_DRAWS, ctx.team, ctx.entity_id, len(ctx.matches)


def build(ctx: Any) -> dict[str, Any]:
    """Repeticiones por partido + resumen global (con cobertura), por torneo y por ventana."""
    team_id, matches, draws, team, entity, total = _unpack(ctx)
    rows = [replay_row(m, team_id, draws, team=team, entity=entity) for m in matches if m.get('events')]
    resumen = dict(summarize(rows), nota=NOTE, sorteos=draws, semilla='id del partido',
                   cobertura={'partidos': total, 'con_eventos': len(rows)})
    return {'resumen': resumen, 'por_torneo': by_tournament(rows), 'por_ventana': by_window(rows, entity),
            'partidos': rows, 'textos': TEXTOS}


def split_cards(payload: dict[str, Any]) -> tuple:
    """(payload sin fichas, {match_id: fila completa con ficha y textos}) para servir /api/matches/{id} aparte."""
    light = dict(payload, partidos=[{k: v for k, v in r.items() if k != 'ficha'} for r in payload['partidos']])
    cards = {r['match_id']: dict(r, textos=payload.get('textos', TEXTOS)) for r in payload['partidos']}
    return light, cards


def _coached_by(side: dict, coach: str) -> bool:
    mgrs = side.get('managers') or []
    return not coach or (len(mgrs) == 1 and any(coach in (mgrs[0].get(k) or '') for k in ('name', 'nickname')))


def _calendar(cache: pathlib.Path) -> Iterable[dict[str, Any]]:
    import json
    for mf in sorted(cache.glob('v6_competitions_73_seasons_*_matches.json')):
        yield from json.loads(mf.read_text(encoding='utf-8'))


def load_matches(team: str, since: str, until: str, coach: str = '',
                 cache: Optional[pathlib.Path] = None) -> tuple:
    """IO: partidos de `team` (con DT único `coach`) en [since, until] con eventos v8 → (team_id, matches)."""
    import json
    cache = pathlib.Path(cache or fw_root() / 'data' / 'cache')
    team_id, out = None, []
    for m in _calendar(cache):
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
                'home_name': h['home_team_name'], 'away_name': a['away_team_name']}
        out.append({'meta': meta, 'events': json.loads(ev.read_text(encoding='utf-8'))})
    return team_id, sorted(out, key=lambda m: m['meta']['date'])


def fw_root() -> pathlib.Path:
    """Raíz del repositorio."""
    return pathlib.Path(__file__).resolve().parents[2]


def main() -> None:
    """CLI de vista previa: --team América --coach Jardine --since 2023-07-01 --until 2025-06-30 --out ruta."""
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument('--team', default='América')
    ap.add_argument('--since', default='2023-07-01')
    ap.add_argument('--until', default=fw.OFFICIAL_END)
    ap.add_argument('--coach', default='Jardine')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    team_id, matches = load_matches(args.team, args.since, args.until, args.coach)
    out = build({'team_id': team_id, 'matches': matches, 'team': args.team})
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(json.dumps(out['resumen'], ensure_ascii=False))


def _register() -> None:
    try:
        from analytics import register
    except ImportError:
        return
    register('replay', build)


_register()

if __name__ == '__main__':
    main()
