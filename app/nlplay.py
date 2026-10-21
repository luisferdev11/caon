# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Router del laboratorio de jugadas: POST /api/play/parse y GET /api/play/capabilities."""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import env, openrouter
from app.play_rules import MAX_INPUT, PlayParseError, parse_rules

router = APIRouter()
log = logging.getLogger('caon.nlplay')
AUTO_LLM_BELOW = 0.6  # confianza de reglas bajo la cual auto consulta al LLM


class ParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    team: Optional[str] = None
    opponent: Optional[str] = None
    mode: Literal['auto', 'rules', 'llm'] = 'auto'


def api_key() -> Optional[str]:
    return env.get('OPENROUTER_API_KEY')


def model_id() -> str:
    return env.get('OPENROUTER_MODEL') or openrouter.DEFAULT_MODEL


def team_shape(team: Optional[str]) -> list[dict]:
    """Forma (once tipo) del equipo-entrenador desde el modelo; [] si no hay."""
    if not team:
        return []
    try:
        from app.main import load_model  # import tardío: main incluye este router
        ent = next((e for e in load_model()['entities'] if e.get('id') == team), None)
    except Exception:  # noqa: BLE001 - sin modelo: el parser funciona sin nombres
        return []
    return [{k: p.get(k) for k in ('name', 'num', 'pos')} for p in (ent or {}).get('shape') or []]


def _try_llm(text: str, shape: list[dict], warnings: list[str]) -> Optional[dict]:
    """Play del LLM como dict, o None (y un aviso) ante cualquier falla."""
    key = api_key()
    if not key:
        warnings.append('llm_sin_key')
        return None
    try:
        names = [p['name'] for p in shape if p.get('name')]
        play, _usage = openrouter.parse_llm(text, key, model_id(), names)
        return play.model_dump()
    except openrouter.LLMError as exc:
        log.warning('LLM falló (%s); se usan reglas', exc)
        warnings.append('llm_fallo')
        return None


def parse_play(req: dict, shape: list[dict]) -> dict:
    """Modo rules: solo reglas. llm: LLM y respaldo a reglas. auto: reglas primero y LLM solo si
    las reglas no entienden o dudan (el benchmark mostró reglas más exactas). Devuelve play.v1 + warnings.
    """
    text, mode, warnings = req['text'][:MAX_INPUT], req.get('mode') or 'auto', []
    if len(req['text']) > MAX_INPUT:
        warnings.append('texto_recortado_500')
    rules, err = None, None
    if mode != 'llm':
        try:
            rules = parse_rules(text, shape, req.get('team')).model_dump()
        except PlayParseError as exc:
            err = exc
    need_llm = mode == 'llm' or (mode == 'auto' and (rules is None or rules['confidence'] < AUTO_LLM_BELOW))
    llm = _try_llm(text, shape, warnings) if need_llm else None
    if llm is not None:
        return dict(llm, team=req.get('team'), warnings=warnings)
    if rules is None and err is None:
        rules = parse_rules(text, shape, req.get('team')).model_dump()
    if rules is None:
        raise err
    return dict(rules, warnings=warnings)


@router.post('/api/play/parse')
def parse_endpoint(body: ParseRequest):
    """Texto en español → jugada play.v1 (source: rules|llm) con supuestos y avisos."""
    try:
        return parse_play(body.model_dump(), team_shape(body.team))
    except PlayParseError as exc:
        raise HTTPException(422, {'mensaje': str(exc), 'sugerencias': exc.suggestions})


@router.get('/api/play/capabilities')
def capabilities():
    """Si hay LLM disponible (sin revelar la key) y qué modelo se usa."""
    has = bool(api_key())
    return {'llm': has, 'model': model_id() if has else None}
