# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Especificación única de las métricas 360 escalares (tabla f360, id del framework, alcance, unidad y
valor por registro) y utilidades compartidas por la entidad y por la referencia de liga.

Cada métrica es la media de un valor por registro válido (las proporciones son medias de 0/100), así la
entidad, los rivales de los mismos partidos, la muestra neutral y la liga se calculan con la misma regla.
"""
from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from typing import Any, Callable, NamedTuple, Optional  # noqa: UP035 - Python 3.9

from framework import CI_LEVEL, VIG_LOW_MAX, confidence, metric

SOURCE = '360'
ROUND = 2
LOWER_BOUND = 'jugadores visibles (cota inferior)'
NO_360 = 'sin partidos con 360 en esta ventana'
NO_VALID = 'sin cuadros 360 que pasen la puerta de visibilidad'
TABLES = ('perdidas', 'bloque', 'salida', 'rompe', 'presion', 'corner_def', 'saque_meta')
PCT = 100.0
Z_CI = statistics.NormalDist().inv_cdf(0.5 + CI_LEVEL / 2)   # 1.2816 para el 80 %

Row = dict[str, Any]


class Spec(NamedTuple):
    """Una métrica 360: de qué tabla sale, con qué id/alcance se publica y cómo vale cada registro."""
    table: str
    metric_id: str
    scope: str
    unit: str
    value: Callable[[Row], Optional[float]]
    linked: str = ''      # columna que marca "con cuadro enlazado" ('' = toda fila tiene cuadro)


def _when(flag: str, col: str) -> Callable[[Row], Optional[float]]:
    return lambda r: r.get(col) if r.get(flag) and r.get(col) is not None else None


def _ind(flag: str, test: Callable[[Row], bool]) -> Callable[[Row], Optional[float]]:
    return lambda r: (PCT if test(r) else 0.0) if r.get(flag) else None


def _costly(r: Row) -> bool:
    return bool(r.get('costly', r.get('shot15')))


def _pairing(r: Row) -> Optional[float]:
    return r['pairing'] * PCT if r.get('valid') and r.get('pairing') is not None else None


_YD_OWN = 'yardas desde la portería propia'
SPECS: dict[str, Spec] = {
    'vig_media': Spec('perdidas', 'vigilancias', 'media', LOWER_BOUND, _when('vig_valid', 'vig_gs'), 'vig_linked'),
    'vig_pct_max2': Spec('perdidas', 'vigilancias_bajas', 'pct_max2', f'% de pérdidas con ≤{VIG_LOW_MAX} vigilancias',
                         _ind('vig_valid', lambda r: (r.get('vig_gs') or 0) <= VIG_LOW_MAX), 'vig_linked'),
    'vig_centrales': Spec('perdidas', 'vigilancias', 'centrales', 'jugadores visibles centrales (cota inferior)',
                          _when('vig_valid', 'vig_central'), 'vig_linked'),
    'error_costosa': Spec('perdidas', 'perdida_costosa', '360_contexto_valido', '% de pérdidas',
                          _ind('err_valid', _costly), 'err_linked'),
    'err_apoyos': Spec('perdidas', 'contexto_error', 'apoyos_10yd', 'compañeros a ≤10 yd (cota inferior)',
                       _when('err_valid', 'tm10'), 'err_linked'),
    'err_rivales': Spec('perdidas', 'contexto_error', 'rivales_5yd', 'rivales a ≤5 yd (cota inferior)',
                        _when('err_valid', 'op5'), 'err_linked'),
    'err_distancia': Spec('perdidas', 'contexto_error', 'distancia_rival', 'yardas al rival visible más cercano',
                          _when('err_valid', 'nearest'), 'err_linked'),
    'err_aislado': Spec('perdidas', 'contexto_error', 'pct_aislado', '% de pérdidas sin compañero a ≤10 yd',
                        _ind('err_valid', lambda r: bool(r.get('isolated'))), 'err_linked'),
    'altura_con_balon': Spec('salida', 'altura_linea', 'con_balon', _YD_OWN, _when('valid', 'height')),
    'altura_sin_balon': Spec('bloque', 'altura_linea', 'sin_balon', _YD_OWN, _when('valid', 'last_line')),
    'bloque_largo': Spec('bloque', 'bloque_360', 'largo', 'yardas (visibles)', _when('valid', 'length')),
    'bloque_ancho': Spec('bloque', 'bloque_360', 'ancho', 'yardas (visibles)', _when('valid', 'width')),
    'bloque_area': Spec('bloque', 'bloque_360', 'area', 'yd² (área convexa de visibles)',
                        _when('valid', 'hull_area')),
    'bloque_entre': Spec('bloque', 'bloque_360', 'entre_balon_y_porteria', LOWER_BOUND, _when('valid', 'between')),
    'rompe_pct': Spec('rompe', 'rompe_lineas', 'pct', '% de pases adelante completados',
                      _ind('valid', lambda r: bool(r.get('lbp')))),
    'rompe_superados': Spec('rompe', 'rompe_lineas', 'superados', 'rivales superados por pase (cota inferior)',
                            _when('valid', 'bypassed')),
    'presion_apoyo': Spec('presion', 'presion_360', 'apoyo', 'compañeros a ≤10 yd del balón (cota inferior)',
                          _when('valid', 'support')),
    'presion_libres': Spec('presion', 'presion_360', 'opciones_libres', 'opciones libres del rival (cota inferior)',
                           _when('valid', 'free_options')),
    'presion_contra': Spec('presion', 'presion_360', 'pct_contrapresion', '% de presiones',
                           _ind('valid', lambda r: bool(r.get('counterpress')))),
    'corner_area': Spec('corner_def', 'corner_def', 'def_area', LOWER_BOUND, _when('valid', 'def_box')),
    'corner_area_chica': Spec('corner_def', 'corner_def', 'def_area_chica', LOWER_BOUND, _when('valid', 'def_six')),
    'corner_emparejamiento': Spec('corner_def', 'corner_def', 'emparejamiento',
                                  '% de atacantes en el área con marca a ≤1.5 yd', _pairing),
}


def rows(f360: dict[str, Any], table: str) -> list[Row]:
    """Tabla en columnas → lista de dicts."""
    tab = (f360.get('tables') or {}).get(table) or {}
    cols = tab.get('cols') or []
    return [dict(zip(cols, r)) for r in tab.get('rows') or []]


def values(recs: Sequence[Row], key: str) -> list[float]:
    """Valores por registro válido de la métrica ``key``."""
    fn = SPECS[key].value
    return [float(v) for v in (fn(r) for r in recs) if v is not None]


def n_linked(recs: Sequence[Row], key: str) -> int:
    """Registros con cuadro 360 enlazado para la métrica ``key``."""
    col = SPECS[key].linked
    return sum(1 for r in recs if r.get(col)) if col else len(recs)


def mean(vals: Sequence[float]) -> Optional[float]:
    return round(statistics.fmean(vals), ROUND) if vals else None


def pct(num: int, den: int) -> Optional[float]:
    return round(PCT * num / den, ROUND) if den else None


def percentile(value: Optional[float], dist: Sequence[float]) -> Optional[int]:
    """Percentil por rango medio: % de la distribución por debajo + la mitad de los empates."""
    if value is None or not dist:
        return None
    below = sum(1 for d in dist if d < value)
    ties = sum(1 for d in dist if d == value)
    return round(PCT * (below + 0.5 * ties) / len(dist))


def quantile(vals: Sequence[float], q: float) -> Optional[float]:
    """Cuantil con interpolación lineal (tipo 7, como numpy por defecto)."""
    if not vals:
        return None
    s = sorted(vals)
    pos = q * (len(s) - 1)
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (pos - lo), ROUND)


def ci80(match_means: Sequence[float], center: Optional[float] = None) -> Optional[list[float]]:
    """Intervalo del 80 % con la dispersión entre partidos, centrado en ``center`` (o la media de partidos)."""
    if len(match_means) < 2:
        return None
    m = statistics.fmean(match_means) if center is None else center
    half = Z_CI * statistics.stdev(match_means) / math.sqrt(len(match_means))
    return [round(m - half, ROUND), round(m + half, ROUND)]


def record(key: str, value: Optional[float], n: int, window: str, *, entity: str, n_partidos: int,
           **extra: Any) -> dict[str, Any]:
    """Registro del contrato para la métrica ``key`` (id del framework + alcance); null lleva motivo.

    La confianza se calcula con el número de partidos con registros válidos, no con los cuadros.
    """
    spec = SPECS[key]
    motivo = NO_360 if n_partidos == 0 else NO_VALID
    val = round(value, ROUND) if value is not None else None
    return metric(spec.metric_id, val, n, spec.unit, SOURCE, window, motivo, scope=spec.scope, entity=entity,
                  n_partidos=n_partidos, confidence=confidence(n_partidos), **extra)
