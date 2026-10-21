# ruff: noqa: UP045  (Python 3.9: Optional en lugar de X | None)
"""Explorador por equipo, temporada y DT desde team-stats de todos los partidos en caché (AC-12).

Unidad = (equipo, DT, temporada), solo partidos con un único DT registrado. Cada métrica se
encoge hacia el prior de la carrera del DT (sus otros clubes, ponderado por partidos) o hacia la
liga si no tiene historia: (n·x̄ + K·μ0)/(n + K). Intervalo al 80% σ/√(n+K) y banda de confianza.
Uso: .venv/bin/python -X utf8 pipeline/explorer.py [--out ruta.json]
"""
import argparse
import collections
import json
import math
import pathlib
import statistics
from typing import Any, Optional

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data' / 'cache'
DEFAULT_OUT = ROOT / 'data' / 'out' / 'preview' / 'A6' / 'explorer.json'

from framework import OFFICIAL_END as WINDOW_END
from framework import SHRINK_N0 as SHRINK_K
from framework import confidence

Z80 = 1.2816                       # cuantil normal para intervalo central al 80% (framework.CI_LEVEL)
WINDOW_START = '2021-07-01'        # inicio de la ventana oficial Ap2021–Cl2025
UNITS = {'posesion': 'proporción', 'verticalidad': 'proporción', 'ritmo': 'm/s', 'linea': 'm',
         'presion': 'pases por acción', 'saque_largo': 'proporción', 'xg': 'xG por partido',
         'xga': 'xG por partido', 'bp_xg': 'xG por partido'}
SMALL_SAMPLE_N = 12                # "muestra chica" por debajo de confianza media
REF_MIN_MATCHES = 10               # equipo-temporada entra a la referencia de percentiles

try:  # mismas definiciones de estilo que el modelo (no se edita build_model.py)
    from build_model import STY as METRICS
except Exception:  # noqa: BLE001 - build_model trae dependencias pesadas; copia fiel de STY
    METRICS = [
        ('posesion', 'team_match_possession', False, 'Posesión'),
        ('verticalidad', 'team_match_directness', False, 'Verticalidad'),
        ('ritmo', 'team_match_pace_towards_goal', False, 'Velocidad hacia portería'),
        ('linea', 'team_match_defensive_distance', False, 'Altura de línea defensiva'),
        ('volumen_presion', 'team_match_pressures_adj', False, 'Volumen de presión'),
        ('presion', 'team_match_ppda', True, 'Pases rivales por acción defensiva (PPDA)'),
        ('contrapresion', 'team_match_counterpressures', False, 'Contrapresión'),
        ('saque_largo', 'team_match_gk_long_pass_ratio', False, 'Saque largo del portero'),
        ('centros', 'team_match_crosses_into_box', False, 'Centros al área'),
        ('contragolpe', 'team_match_counter_attacking_shots', False, 'Tiros al contragolpe'),
        ('presion_alta_tiros', 'team_match_high_press_shots', False, 'Tiros tras robo alto'),
        ('xg', 'team_match_np_xg', False, 'xG a favor'),
        ('xga', 'team_match_np_xg_conceded', True, 'Solidez (xG en contra)'),
        ('bp_xg', 'team_match_sp_xg', False, 'Peligro a balón parado'),
    ]


def _finite(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def shrink(n: int, xbar: Optional[float], mu0: float, k: int = SHRINK_K) -> float:
    """Encogimiento (n·x̄ + k·μ0)/(n + k)."""
    if not n or xbar is None:
        return mu0
    return (n * xbar + k * mu0) / (n + k)


def interval80(value: float, sd: float, n: int, k: int = SHRINK_K) -> list:
    """Intervalo central 80%: value ± z·σ/√(n+k)."""
    half = Z80 * sd / math.sqrt(n + k)
    return [value - half, value + half]


def window_of(date: str) -> str:
    """Ventana del framework: 'oficial' (Ap2021–Cl2025), 'epilogo' (después) o 'temprano' (antes)."""
    if date > WINDOW_END:
        return 'epilogo'
    return 'oficial' if date >= WINDOW_START else 'temprano'


def percentile(ref: list, v: float, inverted: bool) -> int:
    """Percentil de v en la referencia ordenada (invertido si menos es mejor)."""
    p = 100 * sum(1 for x in ref if x < v) / len(ref)
    return round(100 - p if inverted else p)


def match_coach(side: dict) -> Optional[str]:
    """Nombre del DT si el partido tiene exactamente uno registrado."""
    mgrs = side.get('managers') or []
    if len(mgrs) != 1:
        return None
    return mgrs[0].get('nickname') or mgrs[0].get('name')


def _mean(rows: list, col: str) -> Optional[float]:
    vals = [r['stats'][col] for r in rows if _finite(r['stats'].get(col))]
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


def _metric_records(rows: list, prior: dict, league_sd: dict, ref: dict, metrics: list, window: str) -> dict:
    out = {}
    for key, col, inv, _label in metrics:
        vals = [r['stats'][col] for r in rows if _finite(r['stats'].get(col))]
        if not vals or prior.get(col) is None:
            out[key] = {'id': key, 'value': None, 'n': len(vals), 'motivo': 'sin_dato_en_team_stats'}
            continue
        v = shrink(len(vals), sum(vals) / len(vals), prior[col])
        lo, hi = interval80(v, league_sd[col], len(vals))
        rec = {'id': key, 'value': round(v, 4), 'bruto': round(sum(vals) / len(vals), 4), 'n': len(vals),
               'unit': UNITS.get(key, 'por partido'),
               'ci': [round(lo, 4), round(hi, 4)], 'source': 'team-stats', 'window': window}
        if ref.get(col):
            rec['ref_pct'] = percentile(ref[col], v, inv)
        out[key] = rec
    return out


def _league_refs(rows: list, cols: list):
    league = {c: _mean(rows, c) for c in cols}
    sd = {}
    for c in cols:
        vals = [r['stats'][c] for r in rows if _finite(r['stats'].get(c))]
        sd[c] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    grp = collections.defaultdict(list)
    for r in rows:
        grp[(r['team'], r['season_id'])].append(r)
    ref = {c: sorted(m for m in (_mean(g, c) for g in grp.values() if len(g) >= REF_MIN_MATCHES) if m is not None)
           for c in cols}
    return league, sd, ref


def _window(rows: list) -> str:
    wins = {window_of(r['date']) for r in rows}
    if wins == {'oficial'}:
        return 'oficial'
    return 'epilogo' if 'epilogo' in wins else 'temprano'


def _unit(rows: list, prior: dict, src: str, refs, metrics: list) -> dict:
    _league, sd, ref = refs
    first = rows[0]
    n = len(rows)
    return {'team': first['team'], 'coach': first['coach'], 'season_id': first['season_id'],
            'temporada': first['season_name'], 'n': n, 'confianza': confidence(n),
            'muestra_chica': n < SMALL_SAMPLE_N, 'ventana': _window(rows), 'prior': src,
            'desde': min(r['date'] for r in rows), 'hasta': max(r['date'] for r in rows),
            'metricas': _metric_records(rows, prior, sd, ref, metrics, _window(rows))}


def build_payload(rows: list, metrics: Optional[list] = None) -> dict:
    """Índices de equipos y DTs, línea de tiempo por equipo y carrera por DT."""
    metrics = metrics or METRICS
    cols = [m[1] for m in metrics]
    refs = _league_refs(rows, cols)
    by_unit = collections.defaultdict(list)
    by_tenure = collections.defaultdict(list)
    for r in rows:
        if r['coach']:
            by_unit[(r['team'], r['coach'], r['season_id'])].append(r)
            by_tenure[(r['team'], r['coach'], window_of(r['date']))].append(r)
    timeline = collections.defaultdict(list)
    career = collections.defaultdict(list)
    for (team, coach, _sid), urows in sorted(by_unit.items(), key=lambda kv: min(r['date'] for r in kv[1])):
        prior, src = career_prior(rows, coach, min(r['date'] for r in urows), refs[0], cols)
        timeline[team].append(_unit(urows, prior, src, refs, metrics))
    for (_team, coach, _win), trows in sorted(by_tenure.items(), key=lambda kv: min(r['date'] for r in kv[1])):
        prior, src = career_prior(rows, coach, min(r['date'] for r in trows), refs[0], cols)
        career[coach].append(_unit(trows, prior, src, refs, metrics))
    teams = [{'team': t, 'n': sum(u['n'] for u in us), 'unidades': len(us),
              'entrenadores': sorted({u['coach'] for u in us})} for t, us in sorted(timeline.items())]
    coaches = []
    for c, ts in sorted(career.items()):
        n = sum(t['n'] for t in ts)
        coaches.append({'coach': c, 'n': n, 'confianza': confidence(n), 'muestra_chica': n < SMALL_SAMPLE_N,
                        'clubes': [t['team'] for t in ts]})
    return {'version': 'explorer.v1', 'equipos': teams, 'entrenadores': coaches,
            'linea_tiempo': dict(timeline), 'carrera': dict(career),
            'metodo': {'k': SHRINK_K, 'intervalo': '80%', 'fuente': 'team-stats StatsBomb por partido',
                       'bandas': {'muy baja': '<5', 'baja': '5–11', 'media': '12–24', 'alta': '≥25'},
                       'nota': 'Identidad (labels.identity) pendiente: aún no existe pipeline/labels.py.'}}


def _read(path: pathlib.Path) -> Any:
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode('utf-8'))
    except UnicodeDecodeError:
        return json.loads(raw.decode('cp1252'))


def load_rows(cache: pathlib.Path = CACHE) -> list:
    """Une partidos (DT, fecha) con team-stats por partido; agrega team_match_pressures_adj."""
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    out = pathlib.Path(ap.parse_args().out)
    rows = load_rows()
    payload = build_payload(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(f"{len(rows)} filas, {len(payload['equipos'])} equipos, {len(payload['entrenadores'])} DTs → {out}")


if __name__ == '__main__':
    main()
