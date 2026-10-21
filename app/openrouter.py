# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Llamada servidor→OpenRouter para convertir texto en play.v1. La key nunca se registra ni se devuelve."""
from __future__ import annotations

import json
import re
import urllib.request
from collections.abc import Callable
from typing import Optional

from pydantic import ValidationError

from app.play_schema import ZONES, Play

URL = 'https://openrouter.ai/api/v1/chat/completions'
DEFAULT_MODEL = 'mistralai/mistral-small-3.2-24b-instruct'  # elegido en docs/NL_BENCHMARK.md
TIMEOUT_S = 10
MAX_INPUT = 500
MAX_TOKENS = 700

SYSTEM = (
    'Convierte una jugada de fútbol descrita en español a JSON play.v1. Responde SOLO el objeto JSON. '
    'Formato: {"start":{"restart":"open|goal_kick|corner|free_kick|throw_in|kickoff|recovery"},'
    '"steps":[{"type":"pass|carry|dribble|cross|shot|header|recovery|loss|clearance",'
    '"actor":{"num":int|null,"name":str|null,"pos":str|null},"receiver":{...}|null,'
    '"zone":"' + '|'.join(ZONES) + '"|null,"height":"raso|alto"|null,'
    '"outcome":"gol|atajada|fuera|poste|bloqueado"|null}],"assumptions":[str],"confidence":0-1}. '
    'zone = dónde termina el paso (para remates: desde dónde se remata). Una "pared" son dos pases. '
    '"Tiro libre directo" es un shot con restart free_kick. "Córner al primer palo" es un cross. '
    'Escribe en assumptions todo lo que supongas.'
)
FEW_SHOT_USER = 'el 10 centra al segundo palo y el 9 cabecea: gol'
FEW_SHOT_ASSISTANT = json.dumps({
    'start': {'restart': 'open'}, 'assumptions': [], 'confidence': 0.9,
    'steps': [{'type': 'cross', 'actor': {'num': 10}, 'zone': 'segundo_palo', 'height': 'alto'},
              {'type': 'header', 'actor': {'num': 9}, 'zone': 'segundo_palo', 'outcome': 'gol'}]},
    ensure_ascii=False)


class LLMError(RuntimeError):
    """Cualquier falla del LLM (red, tiempo, JSON o esquema). El mensaje nunca incluye la key."""


def http_post(url: str, headers: dict, body: dict, timeout: float) -> dict:
    """POST JSON con urllib (sin dependencias extra)."""
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def build_body(text: str, model: str, names: Optional[list] = None) -> dict:
    user = text[:MAX_INPUT]
    if names:
        user += '\n(Jugadores: ' + ', '.join(names[:11]) + ')'
    return {
        'model': model, 'temperature': 0, 'max_tokens': MAX_TOKENS,
        'response_format': {'type': 'json_object'}, 'usage': {'include': True},
        'messages': [{'role': 'system', 'content': SYSTEM},
                     {'role': 'user', 'content': FEW_SHOT_USER},
                     {'role': 'assistant', 'content': FEW_SHOT_ASSISTANT},
                     {'role': 'user', 'content': user}],
    }


def extract_json(content: str) -> dict:
    """Primer objeto JSON del texto (tolera cercas ```json)."""
    m = re.search(r'\{.*\}', content or '', re.DOTALL)
    if not m:
        raise LLMError('respuesta sin JSON')
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise LLMError('JSON inválido') from exc


def parse_llm(text: str, key: str, model: str, names: Optional[list] = None,
              post: Optional[Callable] = None) -> tuple[Play, dict]:
    """Texto → (Play validado, usage). Lanza LLMError ante cualquier falla."""
    post = post or http_post
    headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
               'X-Title': 'Caon laboratorio de jugadas'}
    try:
        data = post(URL, headers, build_body(text, model, names), TIMEOUT_S)
        content = data['choices'][0]['message']['content']
    except LLMError:
        raise
    except Exception:  # noqa: BLE001 - red, timeout, HTTP, forma inesperada
        raise LLMError('falla de red o respuesta inesperada') from None
    raw = extract_json(content)
    try:
        play = Play.model_validate(dict(raw, source='llm', schema_id='play.v1'))
    except (ValidationError, TypeError) as exc:
        raise LLMError('esquema inválido') from exc
    return play, data.get('usage') or {}
