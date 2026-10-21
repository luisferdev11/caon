# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Agregados 360 por entidad (AC-07, AC-08, KPI 6), por ventana.

Por partido junta el extracto ``f360_<mid>`` (extract_360), los eventos v8 (marcador, cambios, nombres) y la
pérdida canónica de ``an_<mid>``. Publica: métricas escalares con el contrato del framework (vigilancias,
contexto del error, altura de línea, bloque, rompe-líneas, presión coordinada, córner) con referencia de
rivales en los mismos partidos, muestra neutral y liga (shape360_ref); el KPI de vigilancias con semáforo;
la tipología del error; el bloque por zona/marcador/minuto/rival; la forma ante los cambios; la organización
en córner; las fotos de las jugadas más peligrosas y la cordura de orientación. Todo conteo de jugadores es
una cota inferior (solo visibles en la toma).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from typing import Any, Optional

from framework import KPI_TRAFFIC_PCT, PITCH_X, PITCH_Y, REC_CAMPO_RIVAL_X

from analytics import EntityContext, register
from analytics import shape360_base as sb
from analytics import shape360_errors as se
from analytics import shape360_groups as sg
from analytics import shape360_match as sm
from analytics import shape360_ref as sr
from analytics.shape360_base import SPECS, mean

SNAPSHOTS_TOP = 5          # jugadas peligrosas por lado y ventana
KPI_MIN_FRAMES = 5         # cuadros válidos mínimos para que un partido entre al semáforo del KPI
REF_MIN_TEAMS = 10         # percentil solo contra ≥10 equipos con 360 en la ventana
NEUTRAL_MIN_MATCHES = 10   # la muestra neutral se publica con ≥10 partidos con 360
POINTS = {'G': 3, 'E': 1, 'P': 0}
CODE_SWAP = {0: 1, 1: 0, 2: 3, 3: 2, 4: 4}   # códigos de compact_points vistos desde el otro equipo
SANITY_MIN_X = REC_CAMPO_RIVAL_X              # en nuestro marco, el rival que saca de meta está en x > 60
NOTE = ('Conteos 360 = jugadores visibles (cota inferior). Referencias: rivales observados en los mismos partidos, '
        'muestra neutral y liga (solo si el 360 cubre ≥90% del calendario de la ventana).')
LEGEND = {'0': 'protagonista', '1': 'rival', '2': 'portero protagonista', '3': 'portero rival', '4': 'actor'}

Bundle = dict[str, Any]


# ---------------------------------------------------------------- paquete por partido
def _points(score: Optional[Sequence[Any]]) -> Optional[int]:
    if not score or score[0] is None or score[1] is None:
        return None
    return POINTS['G'] if score[0] > score[1] else (POINTS['E'] if score[0] == score[1] else POINTS['P'])


def _shot_info(events: Optional[Sequence[dict[str, Any]]], ids: set) -> dict[str, dict[str, Any]]:
    return {e['id']: {'minuto': e.get('minute'), 'jugador': (e.get('player') or {}).get('name')}
            for e in events or [] if e.get('id') in ids}


def bundle(m: dict[str, Any], f360: dict[str, Any], events: Optional[Sequence[dict[str, Any]]],
           an: Optional[dict[str, Any]], ref: dict[str, Any]) -> Bundle:
    """Paquete de un partido visto por el equipo de la entidad (filas propias y del rival)."""
    team = m['team_id']
    opp = next((t for t in f360.get('teams') or [] if t != team), None)
    own: dict[str, list] = {t: [] for t in sb.TABLES}
    other: dict[str, list] = {t: [] for t in sb.TABLES}
    for t in sb.TABLES:
        for r in sb.rows(f360, t):
            (own if r.get('team') == team else other)[t].append(r)
    loss_ids = {r['eid'] for r in own['perdidas'] + other['perdidas']}
    poss_of = {e['id']: e.get('possession') for e in events or [] if e.get('id') in loss_ids}
    index = se.an_loss_index(an)
    own['perdidas'] = se.join_an(own['perdidas'], poss_of, index)
    other['perdidas'] = se.join_an(other['perdidas'], poss_of, index)
    season = (ref.get('temporada') or {}).get(str(m['id']))
    snaps = f360.get('snapshots') or []
    return {'mid': m['id'], 'team': team, 'opp_id': opp, 'date': m.get('date'), 'opponent': m.get('opponent'),
            'points': _points(m.get('score')), 'tier': ((ref.get('niveles') or {}).get(season) or {}).get(str(opp)),
            'mctx': sm.match_context(events, team), 'own': own, 'opp': other,
            'snapshots': snaps, 'shots': _shot_info(events, {s.get('eid') for s in snaps})}


# ---------------------------------------------------------------- métricas escalares
def _ref_block(key: str, opp_rows: list[dict[str, Any]], ref: dict[str, Any], window: str) -> dict[str, Any]:
    out: dict[str, Any] = {'rivales': mean(sb.values(opp_rows, key))}
    league = ((ref.get('ventanas') or {}).get(window) or {}).get(key) or {}
    if league:
        out['liga' if sr.league_complete(ref, window) else 'partidos_con_360'] = league.get('liga')
    neutral = (ref.get('neutral') or {}).get(key)
    if neutral and (ref.get('n_neutral') or 0) >= NEUTRAL_MIN_MATCHES:
        out['neutral'] = neutral['valor']
    return out


def _ref_pct(key: str, value: Optional[float], ref: dict[str, Any], window: str) -> dict[str, Any]:
    league = ((ref.get('ventanas') or {}).get(window) or {}).get(key) or {}
    teams = league.get('equipos') or []
    if len(teams) < REF_MIN_TEAMS and not sr.league_complete(ref, window):
        return {}
    return {'ref_pct': sb.percentile(value, teams)}


def ref_summary(ref: dict[str, Any], window: str) -> dict[str, Any]:
    """Población de referencia de la ventana (una vez por ventana, no por métrica)."""
    league = ((ref.get('ventanas') or {}).get(window) or {}).get('vig_media') or {}
    return {'poblacion_percentil': '{} equipos con ≥{} partidos con 360 en la ventana'.format(
                league.get('n_equipos', 0), sr.REF_MIN_TEAM_MATCHES),
            'liga_completa': sr.league_complete(ref, window),
            'cobertura_calendario': (ref.get('cobertura') or {}).get(window),
            'neutral_partidos': ref.get('n_neutral')}


def match_series(bundles: Sequence[Bundle], key: str) -> list[tuple[Bundle, float, int]]:
    """[(partido, media, n)] de la métrica ``key`` en los partidos con registros válidos."""
    out = []
    for b in bundles:
        vals = sb.values(b['own'][SPECS[key].table], key)
        if vals:
            out.append((b, sum(vals) / len(vals), len(vals)))
    return out


def metric_records(bundles: Sequence[Bundle], window: str, entity: str, ref: dict[str, Any]) -> dict[str, Any]:
    """Un registro del contrato por métrica escalar de shape360_base.SPECS."""
    out = {}
    for key, spec in SPECS.items():
        own = [r for b in bundles for r in b['own'][spec.table]]
        opp = [r for b in bundles for r in b['opp'][spec.table]]
        vals = sb.values(own, key)
        series = match_series(bundles, key)
        value = mean(vals)
        out[key] = sb.record(key, value, len(vals), window, entity=entity, n_partidos=len(series),
                             coverage={'n_valid': len(vals), 'n_linked': sb.n_linked(own, key)},
                             ref=_ref_block(key, opp, ref, window), ci=sb.ci80([s[1] for s in series], value),
                             **_ref_pct(key, value, ref, window))
    return out


# ---------------------------------------------------------------- KPI 6
def _band(items: Sequence[tuple[Bundle, float, int]]) -> dict[str, Any]:
    pts = [b['points'] for b, _, _ in items if b['points'] is not None]
    return {'n': len(items), 'pts_partido': mean(pts)}


def kpi_vigilancias(bundles: Sequence[Bundle], record: dict[str, Any], window: str) -> dict[str, Any]:
    """KPI 6: vigilancias medias con IQR entre partidos, semáforo en sus P33/P67 y puntos por banda."""
    series = [s for s in match_series(bundles, 'vig_media') if s[2] >= KPI_MIN_FRAMES]
    per = [s[1] for s in series]
    lo_q, hi_q = (p / 100.0 for p in KPI_TRAFFIC_PCT)
    p33, p67 = sb.quantile(per, lo_q), sb.quantile(per, hi_q)
    green = [s for s in series if p67 is not None and s[1] >= p67]
    red = [s for s in series if p33 is not None and s[1] <= p33]
    amber = [s for s in series if s not in green and s not in red]
    bands = {'verde': _band(green), 'ambar': _band(amber), 'rojo': _band(red)}
    phrase = None
    if green and red:
        phrase = 'En partidos en verde sumó {} pts/partido vs {} en rojo (n={}/{}); descriptivo.'.format(
            bands['verde']['pts_partido'], bands['rojo']['pts_partido'], len(green), len(red))
    keep = ('id', 'value', 'n', 'unit', 'source', 'window', 'scope', 'entity', 'coverage', 'ref', 'ref_pct',
            'confidence', 'motivo')
    return dict({k: record[k] for k in keep if k in record}, kpi=6, nombre='Vigilancias 360', mejor='alto',
                n_partidos=len(series), iqr=[sb.quantile(per, 0.25), sb.quantile(per, 0.75)],
                umbrales={'rojo_max': p33, 'verde_min': p67}, semaforo=bands, frase=phrase,
                por_partido=[[b['mid'], round(v, sb.ROUND)] for b, v, _ in series])


# ---------------------------------------------------------------- córner, fotos y cordura
def _marks(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(r.get('marking') or 'sin_dato' for r in rows if r.get('valid')))


def corners(bundles: Sequence[Bundle]) -> dict[str, Any]:
    """Tipo de marca inferido en córner rival (con la distribución de los rivales como referencia)."""
    own = [r for b in bundles for r in b['own']['corner_def']]
    opp = [r for b in bundles for r in b['opp']['corner_def']]
    return {'n': sum(1 for r in own if r.get('valid')), 'marcaje': _marks(own), 'ref_marcaje': _marks(opp),
            'nota': 'Marca inferida por emparejamiento (≤1.5 yd) y libres en el área chica; tentativa.'}


def _flip(pts: Optional[list]) -> Optional[list]:
    if not pts:
        return pts
    return [[round(PITCH_X - p[0], 1), round(PITCH_Y - p[1], 1), CODE_SWAP.get(p[2], p[2])] for p in pts]


def _snap(b: Bundle, s: dict[str, Any], flip: bool) -> dict[str, Any]:
    item = {k: s.get(k) for k in ('eid', 'period', 'xg', 'goal', 'pattern')}
    item.update(b['shots'].get(s.get('eid')) or {'minuto': int((s.get('t') or 0) // 60), 'jugador': None})
    item.update(mid=b['mid'], fecha=b.get('date'), rival=b.get('opponent'),
                ff=_flip(s.get('ff')) if flip else s.get('ff'),
                kp_pts=_flip(s.get('kp_pts')) if flip else s.get('kp_pts'))
    return item


def jugadas(bundles: Sequence[Bundle]) -> dict[str, Any]:
    """Fotos de los tiros más peligrosos (sin penales), ordenadas por gol y luego xG.

    Concedidas: el protagonista defiende la portería IZQUIERDA (x=0). A favor: ataca de izquierda a derecha.
    Códigos de punto: ver ``leyenda`` (0 siempre es el protagonista)."""
    conc, fav = [], []
    for b in bundles:
        for s in b['snapshots']:
            if s.get('penalty'):
                continue
            if s.get('shooter_team') != b['team'] and s.get('team') == b['team']:
                conc.append(_snap(b, s, flip=False))
            elif s.get('shooter_team') == b['team']:
                fav.append(_snap(b, s, flip=True))

    def key(d: dict[str, Any]) -> tuple:
        return (not d.get('goal'), -(d.get('xg') or 0.0))
    return {'concedidas': sorted(conc, key=key)[:SNAPSHOTS_TOP], 'a_favor': sorted(fav, key=key)[:SNAPSHOTS_TOP],
            'leyenda': LEGEND}


def sanity(bundles: Sequence[Bundle]) -> dict[str, Any]:
    """Cordura de la inversión: en nuestro marco, el rival que saca de meta debe estar en x > 60."""
    xs = [r['kick_mean_x'] for b in bundles for r in b['own']['saque_meta']
          if r.get('valid') and r.get('kick_mean_x') is not None]
    value = mean(xs)
    return {'x_media_rival_saque_meta': value, 'n': len(xs), 'umbral_x': SANITY_MIN_X,
            'aprobado': None if value is None else value > SANITY_MIN_X}


# ---------------------------------------------------------------- ventana y entidad
def _errors(bundles: Sequence[Bundle], window: str) -> dict[str, Any]:
    names: dict[int, str] = {}
    for b in bundles:
        names.update((b['mctx'] or {}).get('names') or {})
    own = [r for b in bundles for r in b['own']['perdidas']]
    opp = [r for b in bundles for r in b['opp']['perdidas']]
    return se.taxonomy(own, opp, names, window)


def window_payload(bundles: Sequence[Bundle], matches: Sequence[dict[str, Any]], window: str, entity: str,
                   ref: dict[str, Any]) -> dict[str, Any]:
    """Todos los agregados 360 de una ventana."""
    have = {b['mid'] for b in bundles}
    metrics = metric_records(bundles, window, entity, ref)
    base = sg.baselines(bundles)
    return {'partidos': {'con_360': len(bundles), 'total': len(matches),
                         'con_eventos': sum(1 for b in bundles if b['mctx'] is not None),
                         'sin_360': [m['id'] for m in matches if m['id'] not in have]},
            'referencia': ref_summary(ref, window), 'metricas': metrics, 'kpi': kpi_vigilancias(bundles, metrics['vig_media'], window),
            'errores': _errors(bundles, window), 'bloque': sg.block_groups(bundles),
            'cambios': sg.sub_summary([x for b in bundles for x in sg.sub_moments(b, base)], window),
            'corners': corners(bundles), 'jugadas': jugadas(bundles), 'cordura': sanity(bundles)}


def _reference(ctx: EntityContext) -> dict[str, Any]:
    return ctx.league_ref['shape360'] if 'shape360' in ctx.league_ref else sr.load_reference()


def build(ctx: EntityContext) -> dict[str, Any]:
    """Agregados 360 por ventana de la entidad."""
    ref = _reference(ctx)
    by_window: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in ctx.matches:
        by_window[m.get('window') or 'oficial'].append(m)
    out = {}
    for w, ms in by_window.items():
        bundles = []
        for m in ms:
            f = ctx.load_f360(m['id']) if m.get('team_id') is not None else None
            if f is not None:
                bundles.append(bundle(m, f, ctx.load_events(m['id']), ctx.load_an(m['id']), ref))
        out[w] = window_payload(bundles, ms, w, ctx.entity_id, ref)
    return {'ventanas': out, 'nota': NOTE, 'referencia': {'partidos_360': ref.get('n_partidos'),
                                                          'cobertura': ref.get('cobertura')}}


register('shape360', build)
