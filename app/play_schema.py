# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Esquema play.v1: una jugada descrita en texto, normalizada a pasos sobre la cancha.

Coordenadas StatsBomb 120x80, el equipo protagonista ataca hacia x=120 (izquierda→derecha).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

StepType = Literal['pass', 'carry', 'dribble', 'cross', 'shot', 'header', 'recovery', 'loss', 'clearance']
Restart = Literal['open', 'goal_kick', 'corner', 'free_kick', 'throw_in', 'kickoff', 'recovery']
Outcome = Literal['gol', 'atajada', 'fuera', 'poste', 'bloqueado']

# Zonas con nombre → punto representativo (x, y) en el marco del atacante.
ZONES = {
    'campo_propio': (24.0, 40.0),
    'medio': (60.0, 40.0),
    'zona_alta': (86.0, 40.0),
    'banda_izq': (78.0, 7.0),
    'banda_der': (78.0, 73.0),
    'borde_area': (98.0, 40.0),
    'area': (106.0, 40.0),
    'punto_penal': (108.0, 40.0),
    'area_chica': (115.0, 40.0),
    'primer_palo': (114.0, 34.0),
    'segundo_palo': (114.0, 47.0),
}
ZoneId = Literal['campo_propio', 'medio', 'zona_alta', 'banda_izq', 'banda_der', 'borde_area',
                 'area', 'punto_penal', 'area_chica', 'primer_palo', 'segundo_palo']


class Actor(BaseModel):
    """Quién ejecuta: dorsal, nombre (de la forma del equipo) o posición."""
    model_config = ConfigDict(extra='ignore')
    num: Optional[int] = None
    name: Optional[str] = None
    pos: Optional[str] = None


class Start(BaseModel):
    model_config = ConfigDict(extra='ignore')
    restart: Restart = 'open'
    zone: Optional[ZoneId] = None


class Step(BaseModel):
    """Un paso: dónde ocurre/termina (`zone`), quién lo hace y, si es el final, el desenlace."""
    model_config = ConfigDict(extra='ignore')
    type: StepType
    actor: Actor = Field(default_factory=Actor)
    receiver: Optional[Actor] = None
    zone: Optional[ZoneId] = None
    height: Optional[Literal['raso', 'alto']] = None
    outcome: Optional[Outcome] = None


class Play(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    schema_id: Literal['play.v1'] = 'play.v1'
    team: Optional[str] = None
    start: Start = Field(default_factory=Start)
    steps: list[Step] = Field(min_length=1, max_length=12)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)
    source: Literal['rules', 'llm'] = 'rules'


def json_schema() -> dict:
    """Esquema JSON compacto que se manda al LLM."""
    return Play.model_json_schema()
