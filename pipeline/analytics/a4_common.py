# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Piezas comunes de los temas A4 (offense, defense, transitions, dangerous).

- Hechos por partido con caché en memoria (un partido se procesa una sola vez por proceso aunque lo pidan
  varios temas o varias entidades).
- Agrupación por ventana, registros de métrica del contrato (``framework.metric``) con percentil de
  referencia, tablas columnares compactas, nombres de jugadores (apodo de alineaciones si existe).
"""
from __future__ import annotations

import functools
import json
import math
import pathlib
from typing import Any, Callable, Optional  # noqa: UP035 - Python 3.9

import framework as fw

from analytics import CACHE, a4_facts

Facts = dict[str, Any]
Values = dict[str, tuple[Optional[float], int]]
FACTS_CACHE_SIZE = 2048
SOURCE_EVENTS = 'eventos'
ORIGIN_ES = {'regain_open': 'Robo en juego', 'gk': 'Saque de puerta', 'keeper': 'Portero en juego',
             'throw': 'Saque de banda', 'fk': 'Tiro libre', 'corner': 'Córner', 'kickoff': 'Saque inicial',
             'other': 'Otro'}


# ---------------------------------------------------------------- IO (bordes)
def _read_json(path: pathlib.Path) -> Optional[Any]:
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def load_lineups(mid: int) -> Optional[list[dict[str, Any]]]:
    """Alineaciones v4 en caché o None."""
    return _read_json(CACHE / f'v4_lineups_{mid}.json')


def load_team_stats(mid: int) -> Optional[list[dict[str, Any]]]:
    """team-stats v1 del partido en caché o None."""
    return _read_json(CACHE / f'v1_matches_{mid}_team-stats.json')


# ---------------------------------------------------------------- hechos por partido
@functools.lru_cache(maxsize=FACTS_CACHE_SIZE)
def cached_facts(load_an: Callable, load_events: Callable, load_f360: Callable, mid: int) -> Optional[dict]:
    an = load_an(mid)
    events = load_events(mid)
    if not an or not events:
        return None
    return a4_facts.match_facts(mid, an, events, load_f360(mid))


def match_facts(ctx: Any, mid: int) -> Optional[dict[int, Facts]]:
    """Hechos de los dos equipos del partido ``mid`` con los cargadores del contexto (memoizado)."""
    return cached_facts(ctx.load_an, ctx.load_events, ctx.load_f360, mid)


def window_facts(ctx: Any) -> dict[str, dict[str, Any]]:
    """{ventana: {'rows': partidos con datos, 'facts': [hechos propios por partido], 'agg': suma}}."""
    out: dict[str, dict[str, Any]] = {}
    for window in fw.WINDOWS:
        rows, facts = [], []
        for row in ctx.matches:
            if row.get('window') != window:
                continue
            mf = match_facts(ctx, row['id'])
            if mf and row.get('team_id') in mf:
                rows.append(row)
                facts.append(mf[row['team_id']])
        if rows:
            out[window] = {'rows': rows, 'facts': facts, 'agg': a4_facts.merge(facts)}
    return out


# ---------------------------------------------------------------- números
def ratio(num: float, den: float, scale: float = 1.0) -> Optional[float]:
    """num/den·scale, o None si el denominador es 0."""
    return scale * num / den if den else None


def pct_rank(value: Optional[float], population: list[float]) -> Optional[float]:
    """Percentil (0–100) de ``value`` en la población: % de valores menores + mitad de los empates."""
    if value is None or not population:
        return None
    below = sum(v < value for v in population)
    ties = sum(v == value for v in population)
    return round(100.0 * (below + 0.5 * ties) / len(population), 1)


def pearson(xs: list[float], ys: list[float]) -> Optional[float]:
    """Correlación de Pearson (None si hay < 3 pares o varianza nula)."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if not sx or not sy:
        return None
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy), 4)


def rnd(v: Optional[float], nd: int = 3) -> Optional[float]:
    return None if v is None else round(v, nd)


# ---------------------------------------------------------------- registros
class Recorder:
    """Fabrica registros de métrica de una entidad y ventana, con percentil frente a la referencia."""

    def __init__(self, entity: str, window: str, pops: Optional[dict[str, list[float]]] = None) -> None:
        self.entity, self.window, self.pops = entity, window, pops or {}

    def __call__(self, mid: str, value: Optional[float], n: int, unit: str, scope: Optional[str] = None,
                 ref_key: Optional[str] = None, source: str = SOURCE_EVENTS, **extra: Any) -> dict[str, Any]:
        rec = fw.metric(mid, value, n, unit, source, self.window, motivo=None if n else 'sin datos en la ventana',
                        entity=self.entity, **extra)
        if scope:
            rec['scope'] = scope
        pop = self.pops.get(ref_key) if ref_key else None
        if pop and rec['value'] is not None:
            rec['ref_pct'] = pct_rank(rec['value'], pop)
            rec['ref_n'] = len(pop)
        return rec

    def from_values(self, vals: Values, key: str, mid: str, unit: str, scope: Optional[str] = None,
                    **extra: Any) -> dict[str, Any]:
        """Registro de la clave ``key`` de ``values()`` (percentil con la misma clave)."""
        value, n = vals[key]
        return self(mid, value, n, unit, scope=scope, ref_key=key, **extra)


def reference_note(pops: dict[str, list[float]]) -> dict[str, Any]:
    """Descripción única de la población de referencia de un tema (en vez de repetirla en cada registro)."""
    from analytics import a4_reference
    return {'descripcion': a4_reference.REF_LABEL, 'min_partidos': a4_reference.REF_MIN_MATCHES,
            'unidades': max((len(v) for v in pops.values()), default=0),
            'ref_pct': '% de equipos-temporada con valor menor (empates a la mitad)'}


def series(rows: list[dict[str, Any]], facts: list[Facts], values_fn: Callable[[dict], Values],
           keys: tuple[str, ...]) -> dict[str, Any]:
    """Serie por partido (tabla columnar) de algunas claves de ``values_fn`` para KPIs y consistencia."""
    out = []
    for row, f in zip(rows, facts):
        vals = values_fn(f['n'])
        out.append([row['id'], row.get('date')] + [rnd(vals[k][0], 4) for k in keys])
    return {'cols': ['match_id', 'fecha', *keys], 'rows': out}


def compact_shots(shots: list[list[Any]]) -> dict[str, Any]:
    """Tiros como tabla columnar (x, y, xg, gol, penal) para no inflar el payload."""
    return {'cols': ['x', 'y', 'xg', 'goal', 'penal'], 'rows': shots}


# ---------------------------------------------------------------- jugadores
def player_names(rows: list[dict[str, Any]], pids: set[int],
                 lineups_fn: Callable[[int], Optional[list[dict[str, Any]]]] = load_lineups) -> dict[int, str]:
    """Apodo (o nombre) de cada jugador pedido, leyendo alineaciones hasta encontrarlos todos."""
    out: dict[int, str] = {}
    for row in rows:
        if pids <= set(out):
            break
        for team in lineups_fn(row['id']) or []:
            for p in team.get('lineup') or []:
                if p.get('player_id') in pids and p['player_id'] not in out:
                    out[p['player_id']] = p.get('player_nickname') or p.get('player_name') or ''
    return out


def top_players(counts: dict[Any, Any], rows: list[dict[str, Any]], key: Callable[[Any], tuple], limit: int,
                lineups_fn: Callable[[int], Optional[list[dict[str, Any]]]] = load_lineups) -> list[dict[str, Any]]:
    """Los ``limit`` jugadores con mayor ``key`` y su nombre; ``counts`` = {player_id: conteo o dict}."""
    ranked = sorted(((pid, v) for pid, v in counts.items() if pid is not None), key=lambda kv: (key(kv[1]), kv[0]))[:limit]
    names = player_names(rows, {pid for pid, _ in ranked}, lineups_fn)
    out = []
    for pid, v in ranked:
        item = dict(v) if isinstance(v, dict) else {'n': v}
        out.append(dict(item, player_id=pid, jugador=names.get(pid) or f'Jugador {pid}'))
    return out
