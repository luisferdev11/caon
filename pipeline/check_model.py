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
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate(model):
    errors = []
    warnings = []
    def walk(value, path='model'):
        if isinstance(value, dict):
            for key, child in value.items(): walk(child, f'{path}.{key}')
        elif isinstance(value, list):
            for index, child in enumerate(value): walk(child, f'{path}[{index}]')
        elif isinstance(value, float) and not math.isfinite(value):
            errors.append(f'{path}: valor no finito')
        elif isinstance(value, str) and any(marker in value for marker in ('\ufffd', 'Ã©', 'Ã¡', 'Ã³', 'Ã±', 'Ã¼', 'Ã­', 'Ã£', 'Ã§', 'Â·', 'â€')):
            errors.append(f'{path}: posible corrupción de codificación')
    walk(model)
    entities = model.get('entities')
    if not isinstance(entities, list) or not entities:
        errors.append('model.entities no contiene entidades')
        return errors, warnings
    for entity in entities:
        if not isinstance(entity, dict):
            errors.append('entidad no es un objeto')
            continue
        identifier = entity.get('id', '<sin id>')
        n = entity.get('n')
        coverage = entity.get('coverage')
        if coverage:
            processed = coverage.get('processed_match_ids', [])
            if len(processed) != len(set(processed)) or len(processed) != n:
                errors.append(f'{identifier}: IDs procesados no coinciden con n o están duplicados')
            if len(processed) + len(coverage.get('excluded', [])) != coverage.get('requested_matches'):
                errors.append(f'{identifier}: cobertura de partidos no cuadra')
        if n == 0:
            warnings.append(f'{identifier}: sin partidos procesados; no simular')
        att_matches = entity['att'].get('matches') if isinstance(entity.get('att'), dict) else None
        dfn_matches = entity['dfn'].get('matches') if isinstance(entity.get('dfn'), dict) else None
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
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
        if isinstance(style, dict):
            for key, value in style.items():
                if value is not None and (not _finite(value) or not 0 <= value <= 100):
                    errors.append(f'{identifier}: percentil inválido en {key}')
        unavailable = status.get('unavailable', {})
        if unavailable:
            warnings.append(f'{identifier}: métricas de estilo no disponibles: {", ".join(unavailable)}')
        context = entity.get('context')
        if isinstance(context, dict):
            for dimension, buckets in context.items():
                for key, bucket in buckets.items():
                    if not isinstance(bucket, dict):
                        errors.append(f'{identifier}: contexto inválido {dimension}.{key}'); continue
                    matches = bucket.get('matches')
                    if matches is not None and (not isinstance(matches, int) or matches < 0 or (isinstance(n, int) and matches > n)):
                        errors.append(f'{identifier}: partidos contextuales inválidos {dimension}.{key}')
                    for metric in ('seconds', 'possessions', 'xg', 'xga', 'ppda'):
                        value = bucket.get(metric)
                        if value is not None and (not _finite(value) or value < 0):
                            errors.append(f'{identifier}: métrica contextual inválida {dimension}.{key}.{metric}')
            if context.get('score_state') and context.get('venue'):
                for metric in ('seconds', 'actions', 'passes', 'shots'):
                    totals = [sum(b.get(metric) or 0 for b in context[d].values()) for d in ('score_state', 'venue')]
                    if abs(totals[0] - totals[1]) > .1:
                        errors.append(f'{identifier}: particiones contextuales no conservan {metric}')
        if entity.get('kind') == 'real' and not isinstance(context, dict):
            warnings.append(f'{identifier}: no contiene contexto score_state/venue')
        temporal = entity.get('temporal')
        if entity.get('kind') == 'real':
            if not isinstance(temporal, dict):
                warnings.append(f'{identifier}: no contiene análisis temporal')
            else:
                matches = temporal.get('matches') or []
                periods = temporal.get('periods') or []
                match_ids = [row.get('match_id') for row in matches]
                if len(match_ids) != len(set(match_ids)):
                    errors.append(f'{identifier}: partidos temporales duplicados')
                dates = [row.get('date') for row in matches]
                if any(not isinstance(date, str) or not date for date in dates):
                    errors.append(f'{identifier}: partido temporal sin fecha válida')
                if all(isinstance(date, str) for date in dates) and dates != sorted(dates):
                    errors.append(f'{identifier}: partidos temporales fuera de orden')
                if not isinstance(temporal.get('coverage'), dict):
                    errors.append(f'{identifier}: cobertura temporal ausente')
                if temporal.get('coverage', {}).get('observed_matches') != len(matches):
                    errors.append(f'{identifier}: cobertura temporal inconsistente')
                if sum(period.get('matches', 0) for period in periods) != len(matches):
                    errors.append(f'{identifier}: periodos no cubren los partidos temporales')
            personnel = entity.get('personnel')
            if not isinstance(personnel, dict):
                warnings.append(f'{identifier}: no contiene participación de jugadores')
            else:
                coverage = personnel.get('coverage') or {}
                if coverage.get('input_matches') != (entity.get('coverage') or {}).get('requested_matches', entity.get('n')):
                    errors.append(f'{identifier}: cobertura de jugadores no coincide con n')
                match_ids = [row.get('match_id') for row in personnel.get('matches', [])]
                if len(match_ids) != len(set(match_ids)):
                    errors.append(f'{identifier}: partidos de jugadores duplicados')
                for match in personnel.get('matches', []):
                    for interval in match.get('intervals', []):
                        player_ids = [player.get('player_id') for player in interval.get('players', [])]
                        if len(player_ids) != len(set(player_ids)):
                            errors.append(f'{identifier}: jugadores duplicados en intervalo {match.get("match_id")}')
                        for player in interval.get('players', []):
                            if player.get('player_id') is None:
                                errors.append(f'{identifier}: intervalo sin player_id')
                for player in personnel.get('players', []):
                    if player.get('player_id') is None:
                        errors.append(f'{identifier}: agregado de jugador sin player_id')
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
