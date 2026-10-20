"""Validate structural invariants of the generated model.

This check intentionally treats missing analytical data as a warning rather
than fabricating values. Structural inconsistencies remain errors.
"""
import json
import math
import sys
from pathlib import Path

MODEL = Path(__file__).resolve().parents[1] / 'model' / 'model.json'


def _finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def validate(model):
    errors = []
    warnings = []
    entities = model.get('entities')
    if not isinstance(entities, list) or not entities:
        errors.append('model.entities no contiene entidades')
        return errors, warnings
    for entity in entities:
        identifier = entity.get('id', '<sin id>')
        n = entity.get('n')
        att_matches = (entity.get('att') or {}).get('matches')
        dfn_matches = (entity.get('dfn') or {}).get('matches')
        if not isinstance(n, int) or n < 0:
            errors.append(f'{identifier}: n no es un entero no negativo')
        for label, value in (('att.matches', att_matches), ('dfn.matches', dfn_matches)):
            if not isinstance(value, int) or value < 0:
                errors.append(f'{identifier}: {label} no es un entero no negativo')
        if isinstance(n, int) and isinstance(att_matches, int) and n != att_matches:
            errors.append(f'{identifier}: n={n} no coincide con att.matches={att_matches}')
        if isinstance(n, int) and isinstance(dfn_matches, int) and n != dfn_matches:
            errors.append(f'{identifier}: n={n} no coincide con dfn.matches={dfn_matches}')
        style = entity.get('style')
        status = entity.get('style_status') or {}
        if not isinstance(style, dict):
            errors.append(f'{identifier}: style no es un objeto')
        elif not style and n:
            warnings.append(f'{identifier}: estilo vacío con n={n}')
        unavailable = status.get('unavailable', {})
        if unavailable:
            warnings.append(f'{identifier}: métricas de estilo no disponibles: {", ".join(unavailable)}')
        context = entity.get('context')
        if entity.get('kind') == 'real' and not isinstance(context, dict):
            warnings.append(f'{identifier}: no contiene contexto score_state/venue')
        for key, value in entity.items():
            if isinstance(value, float) and not _finite(value):
                errors.append(f'{identifier}: valor no finito en {key}')
    return errors, warnings


def main():
    if not MODEL.exists():
        print(f'ERROR: no existe {MODEL}')
        return 1
    try:
        model = json.loads(MODEL.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f'ERROR: no se pudo leer model.json: {exc}')
        return 1
    errors, warnings = validate(model)
    print(f'entidades: {len(model.get("entities", []))}')
    print(f'advertencias: {len(warnings)}')
    print(f'errores: {len(errors)}')
    for message in warnings:
        print(f'WARN: {message}')
    for message in errors:
        print(f'ERROR: {message}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
