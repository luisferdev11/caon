"""Modelo ligero: model/model.json solo con lo que usan el simulador y el laboratorio.

Los campos pesados de cada entidad (temporal, personal, contexto, cobertura, crudos) se mueven a
model/entities/<id>.json; la API los vuelve a unir con merge_entity().
"""
from __future__ import annotations

import copy
import json
import os
import pathlib
from collections.abc import Iterable

SLIM_KEYS = ('id', 'label', 'team', 'coach', 'group', 'kind', 'd0', 'd1', 'n', 'official', 'formation',
             'style', 'style_status', 'shape', 'actors', 'roles', 'att', 'dfn', 'map', 'note')
DETAIL_KEYS = ('temporal', 'personnel', 'context', 'context_comparisons', 'context_status', 'coverage', 'raw')
NON_LEAGUE_KINDS = ('opendata', 'synthetic')
GROUP_EPILOGUE = 'Epílogo'
GROUP_COMPARISON = 'Comparación'
LEAGUE_SCOPES = ('all', 'legacy')
LEAGUE_SCOPE_ENV = 'CAON_LEAGUE_SCOPE'
DEFAULT_LEAGUE_SCOPE = 'all'


def window_of(entity: dict) -> str | None:
    """Ventana: oficial (≤2025-06-30), epilogo (2025/26), temprano (resto de Liga MX); None si no es Liga MX real."""
    if entity.get('kind') in NON_LEAGUE_KINDS:
        return None
    if entity.get('official'):
        return 'oficial'
    if entity.get('group') == GROUP_EPILOGUE:
        return 'epilogo'
    return 'temprano'


def slim_entity(entity: dict, identity: dict | None = None) -> dict:
    """Solo las llaves que necesita el simulador, más la ventana y la identidad (si existe)."""
    out = {k: copy.deepcopy(entity[k]) for k in SLIM_KEYS if k in entity}
    out['window'] = window_of(entity)
    if identity is not None:
        out['identity'] = identity
    return out


def detail_entity(entity: dict) -> dict:
    """Campos pesados de una entidad, con su id."""
    out = {'id': entity.get('id')}
    out.update({k: entity[k] for k in DETAIL_KEYS if k in entity})
    return out


def split_model(model: dict, identities: dict[str, dict] | None = None) -> tuple[dict, dict[str, dict]]:
    """(modelo ligero, {id: detalle}). No modifica la entrada."""
    identities = identities or {}
    slim = {k: v for k, v in model.items() if k != 'entities'}
    slim['entities'] = [slim_entity(e, identities.get(e.get('id'))) for e in model.get('entities', [])]
    details = {e.get('id'): detail_entity(e) for e in model.get('entities', [])}
    return slim, details


def merge_entity(slim: dict, detail: dict | None) -> dict:
    """Entidad completa = ligera + detalle (el detalle no pisa llaves ligeras)."""
    out = dict(detail or {})
    out.update(slim)
    return out


def dump_json(obj, path: pathlib.Path) -> None:
    """Escritura atómica en UTF-8, sin NaN."""
    data = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(data, encoding='utf-8')
    tmp.replace(path)


def write_split(model: dict, out_dir: pathlib.Path, identities: dict[str, dict] | None = None) -> dict:
    """Escribe out_dir/entities/<id>.json y regresa el modelo ligero (model.json lo publica quien llama)."""
    slim, details = split_model(model, identities)
    ent_dir = out_dir / 'entities'
    ent_dir.mkdir(parents=True, exist_ok=True)
    for eid, detail in details.items():
        dump_json(detail, ent_dir / f'{eid}.json')
    return slim


def league_scope() -> str:
    """Alcance de la referencia de liga: 'all' (todas las entidades) o 'legacy' (conjunto previo)."""
    return os.environ.get(LEAGUE_SCOPE_ENV, DEFAULT_LEAGUE_SCOPE)


def league_match_ids(entities: Iterable[dict], scope: str) -> list:
    """Partidos que alimentan model.league. 'legacy' omite los que solo aportan entidades de Comparación."""
    if scope not in LEAGUE_SCOPES:
        raise ValueError(f'LEAGUE_SCOPE inválido: {scope}; use uno de {LEAGUE_SCOPES}')
    ents = list(entities)
    if scope == 'legacy':
        ents = [e for e in ents if e.get('group') != GROUP_COMPARISON]
    return sorted({x['mid'] for e in ents for x in e['matches']})
