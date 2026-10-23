# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""KPIs de identidad (plan §6): 7 indicadores por entidad y ventana → ``model/kpis/<id>.json``.

Cada KPI copia su registro de ``model/analysis/<id>.json`` (mismo id, valor, n y percentil: la auditoría los ata)
y agrega, con la serie por partido, el IQR, el semáforo en los terciles propios (P33/P67 de ``framework``) y una frase
descriptiva «en partidos en verde sumó X pts/partido contra Y en rojo (n)». Es una asociación, no una causa.
Los puntos por partido salen de ``model/replay/<id>.json``.

    .venv/bin/python -X utf8 pipeline/kpis.py [id ...]
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
from typing import Any, Optional

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import framework as fw

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL = ROOT / 'model'
VERSION = 'kpis.v1'
ROUND = fw.ROUND_DIGITS
COPIED = ('id', 'value', 'n', 'unit', 'source', 'window', 'entity', 'ref_pct', 'ci', 'coverage', 'confidence',
          'scope', 'ref', 'motivo')
# id del KPI -> dónde está su registro, su serie por partido y su apoyo dentro de analysis[tema]['ventanas'][ventana]
SPECS = {
    'field_tilt': {'rec': ('offense', 'dominio', 'field_tilt'), 'serie': ('offense', 'field_tilt'), 'apoyo': {}},
    'progresion_limpia': {'rec': ('offense', 'progresion', 'progresion_limpia'),
                          'serie': ('offense', 'progresion_limpia'), 'apoyo': {}},
    'npxg_por_tiro': {'rec': ('offense', 'ocasiones', 'npxg_por_tiro'), 'serie': ('offense', 'npxg_tiro'),
                      'apoyo': {'tiros_zona_remate': ('offense', 'ocasiones', 'tiros_zona_remate')}},
    'contrapresion_efectiva': {'rec': ('transitions', 'contrapresion_efectiva'),
                               'serie': ('transitions', 'contrapresion_efectiva'), 'apoyo': {}},
    'perdida_costosa': {'rec': ('transitions', 'perdidas', 'costosas_por_partido'),
                        'serie': ('transitions', 'costosas_partido'),
                        'apoyo': {'por_tipo': ('transitions', 'perdidas', 'por_tipo'),
                                  'por_tercio': ('transitions', 'perdidas', 'por_tercio')}},
    'vigilancias': {'rec': ('shape360', 'kpi'), 'serie': None,   # valor y serie (por_partido) de shape360
                    'apoyo': {'vigilancias_bajas': ('shape360', 'metricas', 'vig_pct_max2')}},
    'bp_diferencial': {'rec': ('setpieces', 'diferencial'), 'serie': None,
                       'apoyo': {'bp_ofensivo': ('setpieces', 'ofensivo', 'xg_bp'),
                                 'bp_defensivo': ('setpieces', 'defensivo', 'xg_bp')}},
}


# ---------------------------------------------------------------- puro
def quantile(vals: list[float], q: float) -> Optional[float]:
    """Cuantil con interpolación lineal (tipo 7) y 4 decimales (la escala de xG pide más que 2)."""
    if not vals:
        return None
    s = sorted(vals)
    pos = q * (len(s) - 1)
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (pos - lo), ROUND)


def _mean(vals: list[float]) -> Optional[float]:
    return round(sum(vals) / len(vals), 2) if vals else None


def _band(items: list[tuple], points: dict) -> dict[str, Any]:
    return {'n': len(items), 'pts_partido': _mean([points[m] for m, _ in items if points.get(m) is not None])}


def traffic_light(series: list[tuple], points: dict, mejor: str) -> dict[str, Any]:
    """IQR, umbrales P33/P67 propios, semáforo (verde = lo mejor según ``mejor``) y frase descriptiva."""
    vals = [v for _, v in series]
    out: dict[str, Any] = {'n_partidos': len(series), 'iqr': [quantile(vals, 0.25), quantile(vals, 0.75)],
                           'umbrales': None, 'semaforo': None, 'frase': None,
                           'por_partido': [[m, round(v, ROUND)] for m, v in series]}
    if not series:
        out['motivo'] = 'sin serie por partido'
        return out
    if len(series) < fw.KPI_MIN_MATCHES:
        out['motivo'] = f'muestra chica (n={len(series)}<{fw.KPI_MIN_MATCHES}): sin semáforo'
        return out
    p33, p67 = (quantile(vals, p / 100) for p in fw.KPI_TRAFFIC_PCT)
    hi = [s for s in series if s[1] >= p67]
    lo = [s for s in series if s[1] <= p33]
    green, red = (hi, [s for s in lo if s not in hi]) if mejor == 'alto' else (lo, [s for s in hi if s not in lo])
    amber = [s for s in series if s not in green and s not in red]
    bands = {'verde': _band(green, points), 'ambar': _band(amber, points), 'rojo': _band(red, points)}
    out.update(umbrales={'p33': p33, 'p67': p67}, semaforo=bands)
    if bands['verde']['pts_partido'] is not None and bands['rojo']['pts_partido'] is not None:
        out['frase'] = 'En partidos en verde sumó {} pts/partido vs {} en rojo (n={}/{}); descriptivo.'.format(
            bands['verde']['pts_partido'], bands['rojo']['pts_partido'], len(green), len(red))
    return out


def _dig(node: Any, path: tuple) -> Any:
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
    return node


def _series_from_block(block: Any, col: str) -> list[tuple]:
    """[(match_id, valor)] desde un bloque {cols, rows}; omite valores ausentes."""
    if not isinstance(block, dict) or col not in (block.get('cols') or []):
        return []
    i = block['cols'].index(col)
    return [(r[0], r[i]) for r in block.get('rows') or [] if r[i] is not None]


def _null(kpi_id: str, number: int, name: str, mejor: str, window: str, entity: str, reason: str) -> dict[str, Any]:
    return {'id': kpi_id, 'kpi': number, 'nombre': name, 'mejor': mejor, 'value': None, 'window': window,
            'entity': entity, 'motivo': reason}


def _pct_bueno(ref_pct: Optional[float], mejor: str) -> Optional[float]:
    if ref_pct is None:
        return None
    return ref_pct if mejor == 'alto' else round(100 - ref_pct, 1)


def _series_of(spec: dict, win: dict, record: dict) -> list[tuple]:
    if spec['serie'] is not None:
        topic, col = spec['serie']
        return _series_from_block((win.get(topic) or {}).get('serie'), col)
    return [(m, v) for m, v in record.get('por_partido') or []]   # vigilancias y balón parado publican su serie


def _window_topics(analysis: dict, window: str) -> dict[str, dict]:
    return {t: ((analysis.get(t) or {}).get('ventanas') or {}).get(window) or {} for t in
            ('offense', 'defense', 'transitions', 'shape360', 'setpieces')}


def build_kpi(kpi: dict, number: int, win: dict, points: dict, window: str, entity: str) -> dict[str, Any]:
    """Un KPI: registro copiado + apoyo + IQR y semáforo."""
    spec, mejor = SPECS[kpi['id']], kpi['mejor']
    record = _dig(win, spec['rec'])
    if not isinstance(record, dict) or record.get('value') is None:
        why = (record or {}).get('motivo') if isinstance(record, dict) else None
        return _null(kpi['id'], number, kpi['nombre'], mejor, window, entity, why or 'sin dato en esta ventana')
    series = _series_of(spec, win, record)
    out = {k: record[k] for k in COPIED if k in record}
    out.update(kpi=number, nombre=kpi['nombre'], mejor=mejor, pct_bueno=_pct_bueno(record.get('ref_pct'), mejor),
               apoyo={name: _dig(win, path) for name, path in spec['apoyo'].items()})
    out.update(traffic_light(series, points, mejor))
    return out


def build_entity(analysis: dict, points: dict, entity: str) -> dict[str, Any]:
    """KPIs por ventana presente en la analítica de la entidad."""
    windows = [w for w in fw.WINDOWS if any(((analysis.get(t) or {}).get('ventanas') or {}).get(w)
                                            for t in ('offense', 'transitions', 'setpieces', 'shape360'))]
    kpis = {w: [build_kpi(k, i, _window_topics(analysis, w), points, w, entity) for i, k in enumerate(fw.KPIS, 1)]
            for w in windows}
    return {'version': VERSION, 'entity': entity, 'label': (analysis.get('meta') or {}).get('label', entity),
            'kpis': kpis, 'nota': 'Semáforo en los terciles propios de la entidad; puntos por partido descriptivos, '
                                  'no causales.'}


# ---------------------------------------------------------------- IO
def _read(path: pathlib.Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def points_by_match(replay: Optional[dict]) -> dict[int, int]:
    """{match_id: puntos reales} desde model/replay/<id>.json."""
    return {r['match_id']: r['points'] for r in (replay or {}).get('partidos') or [] if r.get('points') is not None}


def main(argv: list[str]) -> int:
    from model_split import dump_json
    (MODEL / 'kpis').mkdir(parents=True, exist_ok=True)
    ids = argv or sorted(p.stem for p in (MODEL / 'analysis').glob('*.json'))
    for eid in ids:
        analysis = _read(MODEL / 'analysis' / f'{eid}.json')
        if analysis is None:
            print('  sin analysis', eid, flush=True)
            continue
        doc = build_entity(analysis, points_by_match(_read(MODEL / 'replay' / f'{eid}.json')), eid)
        dump_json(doc, MODEL / 'kpis' / f'{eid}.json')
        print(f"  {eid:20s} {', '.join(f'{w}: {len(v)}' for w, v in doc['kpis'].items())}", flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
