# ruff: noqa: UP045  (Python 3.9: Optional en lugar de X | None)
"""Explorador por equipo, temporada y DT desde team-stats de todos los partidos en caché (AC-12).

Unidad = (equipo, DT, temporada) y tenencia = (equipo, DT, ventana), solo partidos con un único DT
registrado. Cada métrica se encoge hacia el prior de la carrera previa del DT (sus partidos anteriores,
ponderados por partido) o hacia la liga si no tiene historia: (n·x̄ + n0·μ0)/(n + n0), con intervalo
central al 80% σ/√(n+n0) y banda de confianza. Los resúmenes de equipo y DT usan solo la ventana oficial
(si no la hay, se rotula la ventana usada). La identidad sale de ``labels.identity`` (mismas reglas que
la historia) sobre los percentiles de los valores encogidos. Los ids de métrica son los de DEFINITIONS.
Cada equipo, DT y tenencia enlaza las entidades del modelo con analítica de eventos/360 (``entidades``).
Uso: .venv/bin/python -X utf8 pipeline/explorer.py [--out ruta.json] [--model model/model.json]
"""
import argparse
import collections
import json
import math
import pathlib
import statistics
import unicodedata
from collections.abc import Callable
from typing import Any, Optional

import framework as fw
import labels
from analytics.replay import window_of
from build_model import STY as METRICS  # mismas métricas de estilo que el modelo
from framework import confidence

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data' / 'cache'
MODEL = ROOT / 'model' / 'model.json'
DEFAULT_OUT = ROOT / 'data' / 'out' / 'preview' / 'A6' / 'explorer.json'
VERSION = 'explorer.v3'
SHRINK_K = fw.SHRINK_N0
Z_CI = statistics.NormalDist().inv_cdf(0.5 + fw.CI_LEVEL / 2)   # 1.2816 para el 80%
SMALL_SAMPLE_N = {name: limit for limit, name in fw.CONFIDENCE_BANDS}['baja']  # "muestra chica": n < 12 (bajo 'media')
REF_MIN_MATCHES = 10               # equipo-temporada entra a la referencia de percentiles
DISPLAY_FIRST = ('xg', 'xga', 'posesion')   # las 3 que ve el modo Aficionado
IDENTITY_KEYS = ('build', 'defense', 'attack', 'offense_style', 'tags', 'map')
SEASON_IDENTITY_KEYS = ('build', 'defense', 'attack', 'tags')
SIG_DIGITS = 4                     # cifras significativas publicadas
SOURCE = 'team-stats'
Row = dict[str, Any]


def _finite(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def shrink(n: int, xbar: Optional[float], mu0: float, k: int = SHRINK_K) -> float:
    """Encogimiento (n·x̄ + k·μ0)/(n + k) (framework.shrink); sin datos devuelve μ0."""
    if not n or xbar is None:
        return mu0
    return fw.shrink(xbar, n, mu0, k)


def interval80(value: float, sd: float, n: int, k: int = SHRINK_K) -> list:
    """Intervalo central al nivel framework.CI_LEVEL: value ± z·σ/√(n+k)."""
    half = Z_CI * sd / math.sqrt(n + k)
    return [value - half, value + half]


def percentile(ref: list, v: float, inverted: bool) -> int:
    """Percentil de v en la referencia ordenada (invertido si menos es mejor)."""
    p = 100 * sum(1 for x in ref if x < v) / len(ref)
    return round(100 - p if inverted else p)


def slug(text: str) -> str:
    """'André Jardine' → 'andre-jardine' (misma regla que las claves de URL de la API)."""
    plain = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode().lower()
    return '-'.join(''.join(c if c.isalnum() else ' ' for c in plain).split())


def match_coach(side: dict) -> Optional[str]:
    """Nombre del DT si el partido tiene exactamente uno registrado."""
    mgrs = side.get('managers') or []
    if len(mgrs) != 1:
        return None
    return mgrs[0].get('nickname') or mgrs[0].get('name')


def sig(v: float, digits: int = SIG_DIGITS) -> float:
    """Redondeo a ``digits`` cifras significativas (269.32 → 269.3; 0.50712 → 0.5071)."""
    if v == 0:
        return 0.0
    return round(v, digits - 1 - math.floor(math.log10(abs(v))))


def unit_of(key: str) -> str:
    """Unidad publicada de la métrica: la del glosario DEFINITIONS (una sola fuente de verdad)."""
    return (fw.DEFINITIONS.get(key) or {}).get('unidad', 'por partido')


# ---------------------------------------------------------------- referencias y prior
def _values(rows: list, col: str) -> list:
    return [r['stats'][col] for r in rows if _finite(r['stats'].get(col))]


def _mean(rows: list, col: str) -> Optional[float]:
    vals = _values(rows, col)
    return sum(vals) / len(vals) if vals else None


def career_prior(rows: list, coach: str, before: str, league: dict, cols: list):
    """Prior μ0 por métrica: carrera previa del DT (partidos antes de `before`, ponderada) o liga."""
    prev = [r for r in rows if r['coach'] == coach and r['date'] < before]
    if not prev:
        return {c: league[c] for c in cols}, 'liga'
    prior = {}
    for c in cols:
        m = _mean(prev, c)
        prior[c] = league[c] if m is None else m
    return prior, 'carrera'


def league_refs(rows: list, cols: list) -> tuple:
    """(media de liga, σ entre partidos, referencia ordenada de equipo-temporada con ≥10 partidos)."""
    league = {c: _mean(rows, c) for c in cols}
    sd = {}
    for c in cols:
        vals = _values(rows, c)
        sd[c] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    grp = collections.defaultdict(list)
    for r in rows:
        grp[(r['team'], r['season_id'])].append(r)
    ref = {c: sorted(m for m in (_mean(g, c) for g in grp.values() if len(g) >= REF_MIN_MATCHES) if m is not None)
           for c in cols}
    return league, sd, ref


# ---------------------------------------------------------------- registros e identidad
def _ordered(metrics: list) -> list:
    first = [m for k in DISPLAY_FIRST for m in metrics if m[0] == k]
    return first + [m for m in metrics if m not in first]


def metric_record(vals: list, mu0: Optional[float], sd: float, ref: list, metric: tuple, window: str,
                  compact: bool = False) -> dict:
    """Registro de métrica encogido (contrato del framework) o nulo con motivo.

    ``compact``: para unidades anidadas, sin id/nombre/unidad/fuente/ventana (el id es la clave del dict, la
    unidad viene del catálogo y la fuente y la ventana de la unidad).
    """
    key, _col, inv, label = metric
    rec = {'n': len(vals)} if compact else {'id': key, 'nombre': label, 'unit': unit_of(key), 'n': len(vals),
                                            'source': SOURCE, 'window': window}
    if not vals or mu0 is None:
        return dict(rec, value=None, motivo='sin dato en team-stats para estos partidos')
    raw = sum(vals) / len(vals)
    v = shrink(len(vals), raw, mu0)
    lo, hi = interval80(v, sd, len(vals))
    rec.update({'value': sig(v), 'raw': sig(raw), 'prior_value': sig(mu0), 'ci': [sig(lo), sig(hi)]})
    if ref:
        rec['ref_pct'] = percentile(ref, v, inv)
    return rec


def identity_of(records: dict, keys: tuple = IDENTITY_KEYS) -> dict:
    """Identidad (labels.identity) desde los percentiles de los valores encogidos."""
    style = {k: r['ref_pct'] for k, r in records.items() if r.get('ref_pct') is not None}
    ident = labels.identity(style)
    return {k: ident.get(k) for k in keys}


def window_label(rows: list) -> str:
    """Ventana de una unidad: la única de sus partidos o, si se mezclan, la más frecuente."""
    counts = collections.Counter(window_of(r['date']) for r in rows)
    return counts.most_common(1)[0][0]


def unit(rows: list, prior: dict, src: str, refs: tuple, metrics: list, nested: bool = False) -> dict:
    """Unidad del explorador con métricas por id, identidad y confianza.

    Resumen (``nested=False``): registros completos del contrato. Temporada o tenencia (``nested=True``):
    registros compactos, identidad corta y ``source`` a nivel de unidad.
    """
    _league, sd, ref = refs
    n, window = len(rows), window_label(rows)
    recs = {m[0]: metric_record(_values(rows, m[1]), prior.get(m[1]), sd[m[1]], ref[m[1]], m, window, nested)
            for m in _ordered(metrics)}
    out = {'n': n, 'confidence': confidence(n), 'small_sample': n < SMALL_SAMPLE_N, 'window': window,
           'prior': src, 'desde': min(r['date'] for r in rows), 'hasta': max(r['date'] for r in rows),
           'identity': identity_of(recs, SEASON_IDENTITY_KEYS if nested else IDENTITY_KEYS), 'metrics': recs}
    if nested:
        out['source'] = SOURCE
    return out


# ---------------------------------------------------------------- equipos y DTs
def _summary_rows(rows: list) -> list:
    official = [r for r in rows if window_of(r['date']) == 'oficial']
    return official or rows


def _by(rows: list, keyf: Callable[[Row], Any]) -> dict:
    out = collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: r['date']):
        out[keyf(r)].append(r)
    return out


def _season_units(rows: list, all_rows: list, refs: tuple, metrics: list, cols: list) -> list:
    out = []
    for (team, coach, _sid), urows in _by(rows, lambda r: (r['team'], r['coach'], r['season_id'])).items():
        prior, src = career_prior(all_rows, coach, urows[0]['date'], refs[0], cols)
        label = f"{team} · {coach} · {urows[0]['season_name']}"
        out.append(dict(unit(urows, prior, src, refs, metrics, nested=True), key=slug(label),
                        label=label, team=team, coach=coach, season_id=urows[0]['season_id'],
                        temporada=urows[0]['season_name']))
    return out


def team_items(rows: list, refs: tuple, metrics: list, cols: list) -> list:
    """Un resumen por equipo (prior = liga) con sus temporadas por DT encogidas a la carrera previa."""
    items = []
    for team, trows in sorted(_by(rows, lambda r: r['team']).items()):
        seasons = _season_units(trows, rows, refs, metrics, cols)
        base = unit(_summary_rows(trows), refs[0], 'liga', refs, metrics)
        items.append(dict(base, key=slug(team), label=team, team=team, n_total=len(trows), unidades=len(seasons),
                          entrenadores=sorted({r['coach'] for r in trows}), temporadas=seasons))
    return items


def coach_items(rows: list, refs: tuple, metrics: list, cols: list) -> list:
    """Un resumen por DT (prior = liga), su carrera por temporada y sus tenencias (equipo, ventana)."""
    items = []
    for coach, crows in sorted(_by(rows, lambda r: r['coach']).items()):
        tenures = []
        for (team, _win), trows in _by(crows, lambda r: (r['team'], window_of(r['date']))).items():
            prior, src = career_prior(rows, coach, trows[0]['date'], refs[0], cols)
            tenures.append(dict(unit(trows, prior, src, refs, metrics, nested=True), team=team,
                                coach=coach, label=f'{team} · {coach}'))
        seasons = _season_units(crows, rows, refs, metrics, cols)
        base = unit(_summary_rows(crows), refs[0], 'liga', refs, metrics)
        items.append(dict(base, key=slug(coach), label=coach, coach=coach, n_total=len(crows),
                          unidades=len(seasons), clubes=list(dict.fromkeys(t['team'] for t in tenures)),
                          tenencias=tenures, temporadas=seasons))
    return items


def _method() -> dict:
    return {'k': SHRINK_K, 'intervalo': f'{round(100 * fw.CI_LEVEL)}%',
            'fuente': 'team-stats StatsBomb por partido (solo partidos con un único DT registrado)',
            'resumen': 'Resúmenes de equipo y DT con la ventana oficial; prior = liga.',
            'unidades': 'Temporadas y tenencias encogidas hacia la carrera previa del DT o la liga; sus '
                        'métricas son compactas (unidad en el catálogo, fuente y ventana en la unidad).',
            'bandas': {'muy baja': '<5', 'baja': '5–11', 'media': '12–24', 'alta': '≥25'},
            'muestra_chica': f'menos de {SMALL_SAMPLE_N} partidos',
            'identidad': 'labels.identity sobre percentiles de valores encogidos.',
            'entidades': 'Entidades del modelo con analítica de eventos y 360 (/api/entities/{id}/analysis).'}


def build_payload(rows: list, metrics: Optional[list] = None) -> dict:
    """Payload del explorador: equipos y DTs (resumen oficial + detalle), catálogo de métricas y método."""
    metrics = metrics or METRICS
    cols = [m[1] for m in metrics]
    rows = [r for r in rows if r['coach']]
    refs = league_refs(rows, cols)
    catalog = [{'id': k, 'nombre': lab, 'unit': unit_of(k), 'menos_es_mejor': inv, 'columna': col,
                'fuente': SOURCE} for k, col, inv, lab in _ordered(metrics)]
    return {'version': VERSION, 'equipos': team_items(rows, refs, metrics, cols),
            'entrenadores': coach_items(rows, refs, metrics, cols), 'metricas': catalog, 'metodo': _method()}


# ---------------------------------------------------------------- enlace a entidades del modelo
def entity_coach(entity: dict, rows: list) -> Optional[str]:
    """DT con más partidos del equipo de la entidad dentro de [d0, d1]; None si no hay partidos."""
    d0, d1 = entity.get('d0') or '', entity.get('d1') or '9999'
    counts = collections.Counter(r['coach'] for r in rows
                                 if r['team'] == entity.get('team') and d0 <= r['date'] <= d1 and r['coach'])
    return counts.most_common(1)[0][0] if counts else None


def _overlaps(unit_: dict, entity: dict) -> bool:
    return unit_['desde'] <= (entity.get('d1') or '9999') and (entity.get('d0') or '') <= unit_['hasta']


def link_entities(payload: dict, entities: list, rows: list) -> dict:
    """Agrega ``entidades`` [{id, label, window}] a equipos, DTs y tenencias (mismo equipo y DT)."""
    linked = []
    for e in entities:
        coach = entity_coach(e, rows)
        if coach is not None:
            linked.append((e, coach, {'id': e['id'], 'label': e.get('label', e['id']), 'window': e.get('window')}))
    for t in payload['equipos']:
        t['entidades'] = [ref for e, _c, ref in linked if e['team'] == t['team']]
    for c in payload['entrenadores']:
        c['entidades'] = [ref for _e, coach, ref in linked if coach == c['coach']]
        for ten in c['tenencias']:
            ten['entidades'] = [ref for e, coach, ref in linked
                                if coach == c['coach'] and e['team'] == ten['team'] and _overlaps(ten, e)]
    return payload


# ---------------------------------------------------------------- IO
def _read(path: pathlib.Path) -> Any:
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode('utf-8'))
    except UnicodeDecodeError:
        return json.loads(raw.decode('cp1252'))


def load_rows(cache: pathlib.Path = CACHE) -> list:
    """IO: une partidos (DT, fecha) con team-stats por partido; agrega team_match_pressures_adj."""
    rows = []
    for mf in sorted(cache.glob('v6_competitions_73_seasons_*_matches.json')):
        for m in _read(mf):
            ts = cache / f"v1_matches_{m['match_id']}_team-stats.json"
            if not ts.exists():
                continue
            coaches = {m['home_team']['home_team_name']: match_coach(m['home_team']),
                       m['away_team']['away_team_name']: match_coach(m['away_team'])}
            for r in _read(ts):
                pr, po = r.get('team_match_pressures'), r.get('team_match_possession')
                if _finite(pr) and _finite(po) and 0 <= po < 1:
                    r['team_match_pressures_adj'] = pr / (1 - po)
                rows.append({'match_id': m['match_id'], 'date': m['match_date'], 'season_id': m['season']['season_id'],
                             'season_name': m['season']['season_name'], 'team': r['team_name'],
                             'coach': coaches.get(r['team_name']), 'stats': r})
    return rows


def load_entities(path: pathlib.Path = MODEL) -> list:
    """IO: entidades reales de Liga MX del modelo (id, label, team, d0, d1, window); [] si no hay modelo."""
    try:
        model = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    return [e for e in model.get('entities', []) if e.get('kind') == 'real' and e.get('team')]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    ap.add_argument('--model', default=str(MODEL))
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    rows = load_rows()
    payload = link_entities(build_payload(rows), load_entities(pathlib.Path(args.model)), rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    out.write_text(text, encoding='utf-8')
    print(f"{len(rows)} filas, {len(payload['equipos'])} equipos, {len(payload['entrenadores'])} DTs, "
          f"{len(text.encode('utf-8')) // 1024} KB → {out}")


if __name__ == '__main__':
    main()
