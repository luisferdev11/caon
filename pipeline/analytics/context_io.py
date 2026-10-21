# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""IO de ``analytics.context``: team-stats por partido de la liga, calendario (fase y temporada), estadísticas
de temporada (nivel del rival) y partidos de otras entidades para "¿Jardine o el club?". Solo lectura.
"""
from __future__ import annotations

import functools
import json
import pathlib
from collections import defaultdict
from typing import Any, Callable, Optional  # noqa: UP035 - Python 3.9

import numpy as np

# explorer importa analytics.replay: al cargar este módulo (no dentro de build) el registro queda completo
from explorer import load_rows

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / 'data' / 'cache'
COMPETITION_ID = 73
STYLE_COLS = {'xg': 'team_match_np_xg', 'xga': 'team_match_np_xg_conceded', 'posesion': 'team_match_possession',
              'verticalidad': 'team_match_directness', 'ritmo': 'team_match_pace_towards_goal',
              'linea': 'team_match_defensive_distance', 'volumen_presion': 'team_match_pressures_adj',
              'presion': 'team_match_ppda'}                      # = build_model.STY (mismas columnas)


def style_values(ts: Optional[dict]) -> dict[str, Optional[float]]:
    """Métricas de estilo y xG de una fila team-stats (None si falta o no es finito)."""
    out = {}
    for key, col in STYLE_COLS.items():
        v = (ts or {}).get(col)
        out[key] = float(v) if isinstance(v, (int, float)) and np.isfinite(v) else None
    return out


def _read(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _calendar() -> tuple[dict[int, dict[str, Any]], dict[Any, list[dict]], list[Any]]:
    cal, names = {}, {}
    for path in sorted(CACHE.glob(f'v6_competitions_{COMPETITION_ID}_seasons_*_matches.json')):
        for m in _read(path) or []:
            sid = m['season']['season_id']
            names[sid] = m['season']['season_name']
            cal[m['match_id']] = {'stage': (m.get('competition_stage') or {}).get('name'), 'season_id': sid,
                                  'teams': [m['home_team']['home_team_id'], m['away_team']['away_team_id']]}
    order = sorted(names, key=lambda s: names[s])
    stats = {sid: _read(CACHE / f'v2_competitions_{COMPETITION_ID}_seasons_{sid}_team-stats.json') or []
             for sid in order}
    return cal, stats, order


def _entity_rows_loader() -> Callable[[str], list[dict]]:
    """Partidos de otra entidad (mismo formato que ctx.matches), para las comparaciones."""
    @functools.cache
    def load(eid: str) -> tuple:
        from build_analysis import context_matches, index_by_model_id
        from build_model import display
        from entities import build_entities
        ents, ms = build_entities()
        by_id = index_by_model_id(ents, display)
        if eid not in by_id:
            return ()
        return tuple(context_matches(by_id[eid]['matches'], {m['match_id']: m for m in ms}))
    return lambda eid: list(load(eid))


@functools.lru_cache(maxsize=1)
def load_league() -> dict[str, Any]:
    """Team-stats por partido de toda la liga, calendario (fase, temporada) y estadísticas de temporada."""
    rows = load_rows()
    units: dict[Any, list[dict]] = defaultdict(list)
    for r in rows:
        units[(r['team'], r['season_id'])].append(style_values(r['stats']))
    cal, stats, order = _calendar()
    return {'team_stats': {(r['match_id'], r['stats']['team_id']): r['stats'] for r in rows},
            'league_units': dict(units), 'calendar': cal, 'season_stats': stats, 'season_order': order,
            'entity_rows': _entity_rows_loader()}
