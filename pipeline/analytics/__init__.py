# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Registro de módulos analíticos por tema.

Contrato: cada módulo ``pipeline/analytics/<tema>.py`` expone ``build(ctx) -> dict`` y se registra con
``register('<tema>', build)``. ``build_all(ctx)`` corre todos los registrados y devuelve ``{tema: payload}``.
Los cargadores leen los extractos de cada partido (``an_<mid>``, ``f360_<mid>``) y los eventos v8 en caché.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Callable, Optional  # noqa: UP035 - Python 3.9: sin "X | Y"

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXTRACT = ROOT / 'data' / 'extract'
CACHE = ROOT / 'data' / 'cache'

BuildFn = Callable[['EntityContext'], dict[str, Any]]
_REGISTRY: dict[str, BuildFn] = {}


def _read_json(path: pathlib.Path) -> Optional[Any]:
    """Lee JSON; devuelve None si el archivo no existe o está corrupto."""
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def load_an(mid: int) -> Optional[dict[str, Any]]:
    """Extracto de análisis por partido (posesiones y eventos ligeros) o None."""
    return _read_json(EXTRACT / f'an_{mid}.json')


def load_f360(mid: int) -> Optional[dict[str, Any]]:
    """Extracto 360 por partido o None."""
    return _read_json(EXTRACT / f'f360_{mid}.json')


def load_events(mid: int) -> Optional[list[dict[str, Any]]]:
    """Eventos StatsBomb v8 en caché o None."""
    return _read_json(CACHE / f'v8_events_{mid}.json')


@dataclass
class EntityContext:
    """Todo lo que un módulo analítico necesita saber de una entidad (equipo + DT + ventana).

    ``matches``: [{id, date, season, window, venue, opponent, score}]. Los cargadores se pueden sustituir
    en tests por funciones que lean fixtures.
    """
    entity_id: str
    label: str
    team: str
    coach: str
    matches: list[dict[str, Any]] = field(default_factory=list)
    load_an: Callable[[int], Optional[dict[str, Any]]] = load_an
    load_f360: Callable[[int], Optional[dict[str, Any]]] = load_f360
    load_events: Callable[[int], Optional[list[dict[str, Any]]]] = load_events
    league_ref: dict[str, Any] = field(default_factory=dict)

    def match_ids(self, window: Optional[str] = None) -> list[int]:
        """Ids de partido, opcionalmente filtrados por ventana (oficial|epilogo|temprano)."""
        return [m['id'] for m in self.matches if window is None or m.get('window') == window]


def register(topic: str, build_fn: BuildFn) -> BuildFn:
    """Registra ``build_fn`` bajo ``topic``; falla si el tema ya existe con otra función."""
    prev = _REGISTRY.get(topic)
    if prev is not None and prev is not build_fn:
        raise ValueError(f'tema analítico duplicado: {topic}')
    _REGISTRY[topic] = build_fn
    return build_fn


def topics() -> list[str]:
    """Temas registrados, en orden de registro."""
    return list(_REGISTRY)


def build_all(ctx: EntityContext, only: Optional[list[str]] = None) -> dict[str, Any]:
    """Corre cada módulo registrado sobre ``ctx``; un fallo queda como {'error': ...} sin tumbar al resto."""
    out: dict[str, Any] = {}
    for topic, fn in _REGISTRY.items():
        if only is not None and topic not in only:
            continue
        try:
            out[topic] = fn(ctx)
        except Exception as exc:  # noqa: BLE001 - se reporta por tema
            out[topic] = {'error': f'{type(exc).__name__}: {exc}'}
    return out


def _clear_registry_for_tests() -> None:
    """Solo para tests: vacía el registro."""
    _REGISTRY.clear()
