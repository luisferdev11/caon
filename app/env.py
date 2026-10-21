# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Lector mínimo de .env (sin dependencias). Nunca imprime valores."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

ENV_PATH = Path(__file__).resolve().parents[1] / '.env'


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    """Devuelve las parejas CLAVE=valor del archivo; {} si no existe."""
    if not Path(path).exists():
        return {}
    out = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, val = line.split('=', 1)
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def get(key: str, default: Optional[str] = None) -> Optional[str]:
    """Variable de entorno del proceso o, si falta, de .env; vacío cuenta como ausente."""
    val = os.environ.get(key) or load_env().get(key)
    return val or default
