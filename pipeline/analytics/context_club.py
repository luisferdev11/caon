# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""¿Jardine o el club? Compara el estilo del América de Jardine con el América previo (Solari, Ortiz) y con
el San Luis del mismo Jardine, con team-stats por partido de la ventana oficial (funciones puras).

Por métrica: diferencia protagonista − otro con banda bootstrap del 80 % (``context.group_stat``) y
percentil de cada equipo frente a los equipo-temporada de la liga. Lectura: "rasgo de Jardine" si el América
de Jardine se parece más a su San Luis que al América previo y ambas diferencias con el América previo superan
el ruido; "rasgo del club" si se parece más al América previo y la diferencia con su San Luis supera el ruido;
si no, "sin señal clara". Descriptivo: plantillas y rivales distintos.
"""
from __future__ import annotations

from statistics import fmean
from typing import Any, Optional

import framework as fw

from analytics.context import CONSISTENCY_MIN_MATCHES, PCT, group_stat
from analytics.context_io import STYLE_COLS

COMPARISONS = {'ame_jardine': {'club_previo': ('ame_solari', 'ame_ortiz'), 'mismo_dt': ('slp_jardine',)}}
CLUB_KEYS = ('posesion', 'verticalidad', 'ritmo', 'linea', 'volumen_presion', 'presion', 'xg', 'xga')
INVERTED = {'presion', 'xga'}        # menor valor = más presión / más solidez → percentil invertido
WINDOW = 'oficial'
SEED = 20260721
NOTE = ('Comparación descriptiva con team-stats de la ventana oficial: plantillas, rivales y épocas distintas; '
        'no aísla el efecto del entrenador.')
TEXTS = {
    'rasgo de Jardine': '{n}: el América de Jardine se parece más a su San Luis que al América previo; '
                        'apunta a un rasgo del entrenador.',
    'rasgo del club': '{n}: el América de Jardine se parece más al América previo que a su San Luis; '
                      'apunta a un rasgo del club o de la plantilla.',
    'sin señal clara': '{n}: sin señal clara; las diferencias no superan el ruido o apuntan a ambos lados.',
}


def profile(rows: list[dict], team_stats: dict, keys: tuple, cols: dict) -> dict[str, list[float]]:
    """{métrica: valores por partido} de los partidos de la ventana oficial con team-stats."""
    out: dict[str, list[float]] = {k: [] for k in keys}
    for r in rows:
        if r.get('window') != WINDOW:
            continue
        st = team_stats.get((r['id'], r['team_id'])) or {}
        for k in keys:
            v = st.get(cols[k])
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k].append(float(v))
    return out


def league_reference(units: dict[Any, list[dict]], keys: tuple) -> dict[str, list[float]]:
    """Medias de cada equipo-temporada con ≥CONSISTENCY_MIN_MATCHES partidos, ordenadas, por métrica."""
    ref: dict[str, list[float]] = {}
    for k in keys:
        means = []
        for rows in units.values():
            vals = [r[k] for r in rows if r.get(k) is not None]
            if len(vals) >= CONSISTENCY_MIN_MATCHES:
                means.append(fmean(vals))
        ref[k] = sorted(means)
    return ref


def percentile(ref: list[float], value: Optional[float], inverted: bool) -> Optional[int]:
    """Percentil de ``value`` en la referencia (invertido si menos es más)."""
    if value is None or not ref:
        return None
    p = PCT * sum(1 for x in ref if x < value) / len(ref)
    return round(PCT - p if inverted else p)


def compare(target: dict[str, list[float]], other: dict[str, list[float]], keys: tuple) -> dict[str, Any]:
    """Protagonista − otro por métrica con banda bootstrap de la diferencia."""
    out = {}
    for i, k in enumerate(keys):
        s = group_stat(target[k], [1.0] * len(target[k]), other[k], [1.0] * len(other[k]), SEED + i)
        if s is not None and s.get('resto') is not None:
            out[k] = {'protagonista': s['valor'], 'otro': s['resto'], 'dif': s['dif'], 'banda_dif': s['banda_dif'],
                      'supera_ruido': s['supera_ruido']}
    return out


def verdict(target_pct: float, club_pcts: list[float], coach_pct: float, club_noise: list[bool],
            coach_noise: bool) -> str:
    """Lectura por métrica a partir de percentiles y de qué diferencias superan el ruido."""
    d_club = fmean(abs(target_pct - c) for c in club_pcts)
    d_coach = abs(target_pct - coach_pct)
    if d_coach < d_club and all(club_noise):
        return 'rasgo de Jardine'
    if d_club < d_coach and coach_noise:
        return 'rasgo del club'
    return 'sin señal clara'


def _traits(entity: str, groups: dict[str, tuple], profiles: dict[str, dict], pairs: dict[str, dict],
            ref: dict[str, list[float]], keys: tuple) -> list[dict[str, Any]]:
    out = []
    for k in keys:
        pct = {e: percentile(ref[k], fmean(v[k]) if v[k] else None, k in INVERTED) for e, v in profiles.items()}
        others = groups['club_previo'] + groups['mismo_dt']
        if any(pct[e] is None for e in (entity, *others)) or any(k not in pairs[e] for e in others):
            continue
        coach = groups['mismo_dt'][0]
        lectura = verdict(pct[entity], [pct[e] for e in groups['club_previo']], pct[coach],
                          [pairs[e][k]['supera_ruido'] for e in groups['club_previo']], pairs[coach][k]['supera_ruido'])
        name = fw.DEFINITIONS.get(k, {}).get('nombre', k)
        out.append({'metrica': k, 'id': k, 'nombre': name, 'pct': pct, 'lectura': lectura,
                    'texto': TEXTS[lectura].format(n=name)})
    return out


def club_or_coach(entity: str, league: dict[str, Any], keys: tuple = CLUB_KEYS,
                  cols: Optional[dict] = None) -> dict[str, Any]:
    """Payload "¿Jardine o el club?" del protagonista ``entity`` (None con motivo si falta una entidad)."""
    cols = cols or STYLE_COLS
    groups = COMPARISONS[entity]
    ids = (entity, *groups['club_previo'], *groups['mismo_dt'])
    profiles = {e: profile(league['entity_rows'](e), league['team_stats'], keys, cols) for e in ids}
    empty = [e for e, p in profiles.items() if not any(p.values())]
    base = {'window': WINDOW, 'source': 'team-stats', 'nota': NOTE,
            'n': {e: max((len(v) for v in p.values()), default=0) for e, p in profiles.items()}}
    if empty:
        return dict(base, pares=[], rasgos=None, motivo='faltan partidos con team-stats de: ' + ', '.join(empty))
    pairs = {e: compare(profiles[entity], profiles[e], keys) for e in ids[1:]}
    ref = league_reference(league['league_units'], keys)
    return dict(base, pares=[{'otro': e, 'grupo': 'mismo_dt' if e in groups['mismo_dt'] else 'club_previo',
                              'n_otro': base['n'][e], 'metricas': pairs[e]} for e in ids[1:]],
                rasgos=_traits(entity, groups, profiles, pairs, ref, keys))
