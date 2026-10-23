# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Contexto y consistencia por ventana: rendimiento y estilo según rival, localía, fase, marcador y minuto.

Dimensiones de partido (localía, nivel del rival, fase regular/liguilla) con métricas por partido: puntos,
xG y xG en contra (team-stats, sin penales), diferencia, field tilt (posesiones ``an_``) y estilo
(team-stats). Dimensiones de posesión (marcador visto por el protagonista, tramo de minuto) con tasas: xG
a favor y en contra por 90 minutos vividos en ese estado y field tilt. Cada grupo lleva banda del 80 % por
bootstrap sobre partidos y la diferencia contra el resto de partidos; ``supera_ruido`` si la banda de la
diferencia no incluye 0. Consistencia: % de partidos "a su manera" (≥3 de 5 rasgos dentro de su IQR) con
percentil frente a los equipo-temporada de la liga. Descriptivo: no controla plantilla ni calendario.
"""
from __future__ import annotations

import zlib
from collections import defaultdict
from typing import Any, Optional

import framework as fw
import numpy as np

from analytics import register
from analytics.context_io import STYLE_COLS, load_league, style_values

BOOT_DRAWS = fw.BOOT_DRAWS
PCT = 100.0
MIN_S = 60.0
PER_90 = 90.0
REGULAR_STAGES = fw.REGULAR_STAGES
MATCH_METRICS = ('puntos', 'xg', 'xga', 'xg_dif', 'field_tilt', 'posesion', 'verticalidad', 'ritmo', 'linea',
                 'volumen_presion', 'presion')
POSS_METRICS = ('xg_90', 'xga_90', 'field_tilt')
METRIC_META = {   # id del framework, unidad y fuente
    'puntos': ('puntos', 'puntos por partido', 'eventos'), 'xg': ('xg', 'xG sin penales por partido', 'team-stats'),
    'xga': ('xga', 'xG sin penales concedido por partido', 'team-stats'),
    'xg_dif': ('xg_dif', 'xG − xG en contra por partido', 'team-stats'),
    'field_tilt': ('field_tilt', '% de acciones en el último tercio', 'eventos'),
    'xg_90': ('xg', 'xG sin penales por 90 min en ese estado', 'eventos'),
    'xga_90': ('xg_concedido', 'xG sin penales concedido por 90 min en ese estado', 'eventos'),
    **{k: (k, fw.DEFINITIONS[k]['unidad'], 'team-stats') for k in
       ('posesion', 'verticalidad', 'ritmo', 'linea', 'volumen_presion', 'presion')},
}
MATCH_DIMS = (('localia', 'venue'), ('rival', 'rival_tier'), ('fase', 'fase'))
POSS_DIMS = ('marcador', 'minuto')
FLIP_STATE = {'ganando': 'perdiendo', 'perdiendo': 'ganando', 'empatando': 'empatando'}
CONSISTENCY_KEYS = ('xg', 'xga', 'posesion', 'presion', 'verticalidad')
CONSISTENCY_MIN_INSIDE = fw.CONSISTENCY_MIN_INSIDE
CONSISTENCY_MIN_MATCHES = fw.CONSISTENCY_MIN_MATCHES
IQR_Q = (0.25, 0.75)
COMPARISON_TARGETS = ('ame_jardine',)
FINDINGS_TOP = fw.FINDINGS_TOP
MIN_GROUP_MATCHES = fw.CONFIDENCE_BANDS[0][0]   # <5 partidos (confianza "muy baja"): nunca "supera el ruido"
NOTE = ('Descriptivo: diferencias contra el resto de partidos de la misma ventana con banda bootstrap del 80 %; '
        'no controla plantilla, calendario ni rival. Nivel del rival por xG diferencial de su temporada (circular).')


# ---------------------------------------------------------------- remuestreo
def seed_for(ctx: Any, window: str) -> int:
    """Semilla reproducible por entidad y ventana para todos los remuestreos."""
    return zlib.crc32(f'{getattr(ctx, "entity_id", "")}:{window}'.encode())


def _quantiles(samples: np.ndarray) -> list[float]:
    lo, hi = np.quantile(samples, [(1 - fw.CI_LEVEL) / 2, 1 - (1 - fw.CI_LEVEL) / 2])
    return [round(float(lo), fw.ROUND_DIGITS), round(float(hi), fw.ROUND_DIGITS)]


def band80(values: list[float], seed: int) -> Optional[list[float]]:
    """Banda bootstrap (nivel CI_LEVEL) de la media remuestreando partidos; None sin datos."""
    if not values:
        return None
    return ratio_band80(values, [1.0] * len(values), seed)


def _boot_ratios(num: np.ndarray, den: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    idx = rng.integers(0, len(num), size=(BOOT_DRAWS, len(num)))
    dens = den[idx].sum(axis=1)
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(dens > 0, num[idx].sum(axis=1) / np.where(dens > 0, dens, 1.0), np.nan)


def ratio_band80(num: list[float], den: list[float], seed: int) -> Optional[list[float]]:
    """Banda bootstrap de Σnum/Σden remuestreando partidos (razón agrupada); None si Σden = 0."""
    a, b = np.asarray(num, dtype=float), np.asarray(den, dtype=float)
    if not len(a) or b.sum() <= 0:
        return None
    r = _boot_ratios(a, b, np.random.default_rng(seed))
    return _quantiles(r[~np.isnan(r)])


def _ratio(num: list[float], den: list[float]) -> float:
    return float(sum(num) / sum(den))


def group_stat(num_g: list[float], den_g: list[float], num_r: list[float], den_r: list[float],
               seed: int) -> Optional[dict[str, Any]]:
    """Valor del grupo (Σnum/Σden), su banda 80 %, y diferencia contra el resto con su banda y ``supera_ruido``."""
    if not num_g or sum(den_g) <= 0:
        return None
    rng = np.random.default_rng(seed)
    g = _boot_ratios(np.asarray(num_g, float), np.asarray(den_g, float), rng)
    out = {'valor': round(_ratio(num_g, den_g), fw.ROUND_DIGITS), 'n': len(num_g),
           'banda80': _quantiles(g[~np.isnan(g)]), 'confianza': fw.confidence(len(num_g))}
    if not num_r or sum(den_r) <= 0:
        return dict(out, resto=None, dif=None, banda_dif=None, supera_ruido=False)
    r = _boot_ratios(np.asarray(num_r, float), np.asarray(den_r, float), rng)
    d = g - r
    band = _quantiles(d[~np.isnan(d)])
    return dict(out, resto=round(_ratio(num_r, den_r), fw.ROUND_DIGITS),
                dif=round(_ratio(num_g, den_g) - _ratio(num_r, den_r), fw.ROUND_DIGITS), banda_dif=band,
                supera_ruido=bool((band[0] > 0 or band[1] < 0) and min(len(num_g), len(num_r)) >= MIN_GROUP_MATCHES))


# ---------------------------------------------------------------- un partido
def _points(score: Optional[list]) -> Optional[float]:
    if not score or score[0] is None or score[1] is None:
        return None
    return 3.0 if score[0] > score[1] else (1.0 if score[0] == score[1] else 0.0)


def _durations(poss: list[dict]) -> list[float]:
    """Segundos de reloj de cada posesión: hasta el inicio de la siguiente del mismo periodo (o su fin)."""
    out = []
    for i, p in enumerate(poss):
        nxt = poss[i + 1] if i + 1 < len(poss) else None
        end = nxt['t0'] if nxt is not None and nxt.get('period') == p.get('period') else p['t1']
        out.append(max(0.0, float(end) - float(p['t0'])))
    return out


def poss_groups(an: dict, team_id: int) -> dict[str, dict[str, dict[str, float]]]:
    """Minutos, xG a favor/en contra y acciones en último tercio por marcador (visto por ``team_id``) y minuto."""
    poss = [p for p in an.get('possessions') or [] if p.get('period', 1) < fw.SHOOTOUT_PERIOD]
    out: dict[str, dict[str, dict[str, float]]] = {'marcador': {}, 'minuto': {}}
    for p, dur in zip(poss, _durations(poss)):
        own = p.get('team') == team_id
        state = p.get('score_state') if own else FLIP_STATE.get(p.get('score_state'))
        for dim, key in (('marcador', state), ('minuto', p.get('minute_bin'))):
            if key is None:
                continue
            acc = out[dim].setdefault(key, {'min': 0.0, 'xg_f': 0.0, 'xg_c': 0.0, 'f3_own': 0, 'f3_opp': 0})
            acc['min'] += dur / MIN_S
            acc['xg_f' if own else 'xg_c'] += float(p.get('xg') or 0.0)
            acc['f3_own' if own else 'f3_opp'] += int(p.get('n_final_third') or 0)
    return out


def match_record(row: dict, an: Optional[dict], ts: Optional[dict], tier: Optional[str],
                 fase: Optional[str]) -> dict[str, Any]:
    """Un partido: dimensiones y pares (numerador, denominador) por métrica; None si falta el dato (pura)."""
    team = row['team_id']
    st = style_values(ts)
    vals: dict[str, Optional[tuple]] = {k: (st[k], 1.0) if st.get(k) is not None else None
                                        for k in MATCH_METRICS if k in STYLE_COLS}
    pts = _points(row.get('score'))
    vals['puntos'] = (pts, 1.0) if pts is not None else None
    vals['xg_dif'] = (st['xg'] - st['xga'], 1.0) if st['xg'] is not None and st['xga'] is not None else None
    poss = poss_groups(an, team) if an else None
    f3o = sum(p.get('n_final_third') or 0 for p in (an or {}).get('possessions') or [] if p.get('team') == team)
    f3a = sum(p.get('n_final_third') or 0 for p in (an or {}).get('possessions') or [] if p.get('team') != team)
    vals['field_tilt'] = (PCT * f3o, float(f3o + f3a)) if an and f3o + f3a else None
    return {'id': row['id'], 'venue': row.get('venue'), 'rival_tier': tier, 'fase': fase, 'vals': vals,
            'poss': poss, 'style': st}


# ---------------------------------------------------------------- dimensiones
def _pairs(recs: list[dict], key: str) -> tuple[list[float], list[float]]:
    got = [r['vals'][key] for r in recs if r['vals'].get(key) is not None]
    return [p[0] for p in got], [p[1] for p in got]


def split(records: list[dict], dim: str, seed: int = 0) -> dict[str, Any]:
    """Métricas por grupo de una dimensión de partido contra el resto de partidos."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get(dim) is not None:
            groups[r[dim]].append(r)
    if not groups:
        return {'grupos': None, 'motivo': f'sin dato de {dim} en los partidos'}
    out: dict[str, dict[str, Any]] = {}
    for i, (g, recs) in enumerate(sorted(groups.items())):
        rest = [r for k, rs in groups.items() if k != g for r in rs]
        out[g] = {}
        for j, key in enumerate(MATCH_METRICS):
            stat = group_stat(*_pairs(recs, key), *_pairs(rest, key), seed + 31 * i + j)
            if stat is not None:
                out[g][key] = stat
    return {'grupos': out, 'partidos': {g: len(rs) for g, rs in sorted(groups.items())}}


def _poss_pairs(per_match: list[dict[str, float]], key: str) -> tuple[list[float], list[float]]:
    if key == 'field_tilt':
        pairs = [(PCT * m['f3_own'], float(m['f3_own'] + m['f3_opp'])) for m in per_match]
    else:
        side = 'xg_f' if key == 'xg_90' else 'xg_c'
        pairs = [(m[side] * PER_90, m['min']) for m in per_match]
    pairs = [p for p in pairs if p[1] > 0]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def _sum_states(states: dict[str, dict[str, float]], skip: str) -> dict[str, float]:
    tot = {'min': 0.0, 'xg_f': 0.0, 'xg_c': 0.0, 'f3_own': 0.0, 'f3_opp': 0.0}
    for k, v in states.items():
        if k != skip:
            for f in tot:
                tot[f] += v[f]
    return tot


def poss_split(records: list[dict], dim: str, seed: int = 0) -> dict[str, Any]:
    """Tasas por estado (marcador o tramo de minuto) contra el resto del tiempo de los mismos partidos."""
    states = [r['poss'][dim] for r in records if r.get('poss')]
    names = sorted({k for s in states for k in s})
    if not names:
        return {'grupos': None, 'motivo': 'sin extractos de posesión (an_)'}
    out: dict[str, dict[str, Any]] = {}
    for i, g in enumerate(names):
        mine = [s[g] for s in states if g in s]
        rest = [_sum_states(s, g) for s in states]
        out[g] = {'minutos': round(sum(m['min'] for m in mine), 1)}
        for j, key in enumerate(POSS_METRICS):
            stat = group_stat(*_poss_pairs(mine, key), *_poss_pairs(rest, key), seed + 31 * i + j)
            if stat is not None:
                out[g][key] = stat
    return {'grupos': out, 'nota': 'xG por 90 minutos de reloj vividos en ese estado; field tilt del tramo.'}


def findings(dims: dict[str, dict[str, Any]], top: int) -> list[dict[str, Any]]:
    """Diferencias contra el resto que superan el ruido, ordenadas por tamaño relativo a su banda."""
    out = []
    for dim, block in dims.items():
        for g, metrics in (block.get('grupos') or {}).items():
            for key, s in metrics.items():
                if isinstance(s, dict) and s.get('supera_ruido'):
                    width = max(s['banda_dif'][1] - s['banda_dif'][0], 1e-9)
                    out.append({'dimension': dim, 'grupo': g, 'metrica': key, 'valor': s['valor'],
                                'resto': s['resto'], 'dif': s['dif'], 'banda_dif': s['banda_dif'], 'n': s['n'],
                                'confianza': s['confianza'],
                                '_peso': abs(s['dif']) / width})
    out.sort(key=lambda d: -d['_peso'])
    return [{k: v for k, v in d.items() if k != '_peso'} for d in out[:top]]


# ---------------------------------------------------------------- general y consistencia
def _record(key: str, value: Optional[float], n: int, window: str, entity: str, **extra: Any) -> dict[str, Any]:
    mid, unit, source = METRIC_META[key]
    return fw.metric(mid, value, n, unit, source, window, entity=entity, scope=f'contexto:{key}', **extra)


def general(records: list[dict], window: str, entity: str, seed: int) -> dict[str, Any]:
    """Media por partido (o razón agrupada) de cada métrica con banda bootstrap del 80 %."""
    out = {}
    for j, key in enumerate(MATCH_METRICS):
        num, den = _pairs(records, key)
        value = _ratio(num, den) if num and sum(den) > 0 else None
        extra = {'ci': ratio_band80(num, den, seed + j)} if value is not None else {}
        out[key] = _record(key, value, len(num), window, entity, **extra)
    return out


def _consistency_index(rows: list[dict]) -> Optional[tuple[float, int, dict[str, float]]]:
    full = [r for r in rows if all(r.get(k) is not None for k in CONSISTENCY_KEYS)]
    if len(full) < CONSISTENCY_MIN_MATCHES:
        return None
    qs = {k: np.quantile([r[k] for r in full], IQR_Q) for k in CONSISTENCY_KEYS}
    inside = [sum(qs[k][0] <= r[k] <= qs[k][1] for k in CONSISTENCY_KEYS) >= CONSISTENCY_MIN_INSIDE for r in full]
    return PCT * sum(inside) / len(full), len(full), {k: float(q[1] - q[0]) for k, q in qs.items()}


def consistency(own: list[dict], league: dict[Any, list[dict]], window: str, entity: str) -> dict[str, Any]:
    """Índice de consistencia (``consistencia``) con percentil y dispersión relativa frente a la liga."""
    res = _consistency_index(own)
    unit = f'% de partidos con ≥{CONSISTENCY_MIN_INSIDE} de {len(CONSISTENCY_KEYS)} rasgos dentro de su IQR'
    if res is None:
        return fw.metric('consistencia', None, len(own), unit, 'team-stats', window, entity=entity,
                         motivo=f'menos de {CONSISTENCY_MIN_MATCHES} partidos con team-stats completos')
    value, n, iqr = res
    refs = [x for x in (_consistency_index(rows) for rows in league.values()) if x is not None]
    extra: dict[str, Any] = {'dispersion': {}}
    if refs:
        extra['ref_pct'] = round(PCT * sum(1 for r in refs if r[0] < value) / len(refs))
        extra['ref_n'] = len(refs)
    for k in CONSISTENCY_KEYS:
        med = float(np.median([r[2][k] for r in refs])) if refs else None
        extra['dispersion'][k] = {'iqr': round(iqr[k], fw.ROUND_DIGITS),
                                  'iqr_liga_mediana': None if med is None else round(med, fw.ROUND_DIGITS),
                                  'relativa': round(iqr[k] / med, 2) if med else None}
    return fw.metric('consistencia', value, n, unit, 'team-stats', window, entity=entity, scope='contexto',
                     **extra)


# ---------------------------------------------------------------- payload
def tier_and_phase(row: dict, league: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """(nivel del rival, fase regular|liguilla) desde el calendario y las estadísticas de temporada."""
    cal = league['calendar'].get(row['id'])
    if not cal:
        return None, None
    fase = 'regular' if cal.get('stage') in REGULAR_STAGES else 'liguilla'
    opp = next((t for t in cal.get('teams') or [] if t != row['team_id']), None)
    order = list(league['season_order'])
    sid = cal.get('season_id')
    prev = order[order.index(sid) - 1] if sid in order and order.index(sid) > 0 else None
    rows = league['season_stats'].get(sid) or []
    tier = fw.rival_tier(opp, rows, league['season_stats'].get(prev)) if opp is not None and rows else None
    return tier, fase


def _metric_meta() -> dict[str, dict[str, Optional[str]]]:
    return {k: {'id': v[0], 'unidad': v[1], 'fuente': v[2]} for k, v in METRIC_META.items()}


def window_payload(records: list[dict], window: str, entity: str, seed: int,
                   league_units: dict[Any, list[dict]]) -> dict[str, Any]:
    """Contexto completo de una ventana a partir de los registros por partido."""
    dims = {name: split(records, key, seed) for name, key in MATCH_DIMS}
    dims.update({name: poss_split(records, name, seed) for name in POSS_DIMS})
    return {'n_partidos': len(records),
            'cobertura': {'team_stats': sum(r['style']['xg'] is not None for r in records),
                          'an': sum(r['poss'] is not None for r in records)},
            'general': general(records, window, entity, seed),
            'dimensiones': dims,
            'consistencia': consistency([r['style'] for r in records], league_units, window, entity),
            'hallazgos': findings(dims, FINDINGS_TOP), 'metricas': _metric_meta(), 'nota': NOTE}


def build(ctx: Any) -> dict[str, Any]:
    """Contrato analytics: contexto por ventana (+ "¿Jardine o el club?" para el protagonista)."""
    league = (getattr(ctx, 'league_ref', None) or {}).get('context')
    if league is None:
        league = load_league()
    entity = getattr(ctx, 'entity_id', '')
    wins: dict[str, Any] = {}
    for window in fw.WINDOWS:
        rows = [r for r in ctx.matches if r.get('window') == window]
        if not rows:
            continue
        recs = [match_record(r, ctx.load_an(r['id']), league['team_stats'].get((r['id'], r['team_id'])),
                             *tier_and_phase(r, league)) for r in rows]
        wins[window] = window_payload(recs, window, entity, seed_for(ctx, window), league['league_units'])
    out: dict[str, Any] = {'ventanas': wins}
    if entity in COMPARISON_TARGETS and 'entity_rows' in league:
        from analytics.context_club import club_or_coach
        out['jardine_o_club'] = club_or_coach(entity, league)
    return out


register('context', build)
