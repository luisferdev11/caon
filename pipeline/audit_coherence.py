# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Auditoría de coherencia interna (AC-05).

Revisa: (1) etiquetas sin pares en conflicto y tarjeta defensiva = cuadrante del mapa; (2) todo registro de
métrica publicado bajo ``model/`` usa un ``id`` de ``framework.DEFINITIONS``; (3) el mismo ``id`` tiene el
mismo valor en todas las vistas (historia, tablero, Almada, explorador); (4) un único umbral por concepto.
Uso: ``.venv/bin/python -X utf8 pipeline/audit_coherence.py`` → ``data/out/audits/coherence.json``.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys
from collections.abc import Iterator
from typing import Any, Optional

import framework as fw
import labels

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'model'
PAYLOAD_DIRS = ('analysis', 'story', 'explorer', 'entities', 'kpis', 'replay')
OUT = ROOT / 'data' / 'out' / 'audits' / 'coherence.json'
VALUE_TOL = 1e-6
FW_CONSTANTS = {k: v for k, v in vars(fw).items() if k.isupper() and isinstance(v, (int, float))}


def _records(obj: Any) -> Iterator[dict[str, Any]]:
    """Todos los registros de métrica (dict con id, value y window) dentro de un payload."""
    if isinstance(obj, dict):
        if {'id', 'value', 'window'} <= set(obj):
            yield obj
        for v in obj.values():
            yield from _records(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _records(v)


def load_payloads(root: pathlib.Path = MODEL_DIR) -> dict[str, Any]:
    """Payloads JSON publicados bajo los directorios conocidos de ``model/``."""
    out: dict[str, Any] = {}
    for d in PAYLOAD_DIRS:
        for p in sorted((root / d).glob('**/*.json')) if (root / d).is_dir() else []:
            try:
                out[str(p.relative_to(root))] = json.loads(p.read_text(encoding='utf-8'))
            except ValueError as exc:
                out[str(p.relative_to(root))] = {'_error': str(exc)}
    return out


def check_metric_ids(payloads: dict[str, Any]) -> list[str]:
    """Cada registro publicado cumple el contrato y su id existe en DEFINITIONS."""
    errs = []
    for name, doc in payloads.items():
        for rec in _records(doc):
            errs += [f'{name}: {e}' for e in fw.check_metric_record(rec)]
    return errs


def check_same_values(payloads: dict[str, Any]) -> list[str]:
    """Mismo (entidad, id, ventana, alcance) → mismo valor en todas las vistas."""
    seen: dict[tuple, tuple] = {}
    errs = []
    for name, doc in payloads.items():
        for rec in _records(doc):
            if rec.get('entity') is None or not isinstance(rec.get('value'), (int, float)):
                continue
            key = (rec['entity'], rec['id'], rec['window'], rec.get('scope'))
            if key not in seen:
                seen[key] = (rec['value'], name)
            elif abs(seen[key][0] - rec['value']) > VALUE_TOL:
                errs.append('{} {}: {} en {} vs {} en {}'.format(
                    key[0], key[1], seen[key][0], seen[key][1], rec['value'], name))
    return errs


def _published_identity_errors(eid: str, ident: dict[str, Any]) -> list[str]:
    dfn = (ident.get('map') or {}).get('dfn')
    if dfn and ident.get('defense') != dfn[2]:
        return ['{}: tarjeta defensiva "{}" ≠ cuadrante "{}"'.format(eid, ident.get('defense'), dfn[2])]
    return []


def check_labels(model: dict[str, Any]) -> list[str]:
    """0 pares en conflicto en todas las entidades y unidades del mapa; tarjeta defensiva = cuadrante."""
    errs = []
    for e in model.get('entities', []):
        ident = labels.identity(e.get('style') or {})
        errs += ['{}: conflicto {}'.format(e['id'], c) for c in labels.conflicts(ident)]
        if e.get('identity'):
            errs += _published_identity_errors(e['id'], e['identity'])
            errs += ['{}: conflicto publicado {}'.format(e['id'], c) for c in labels.conflicts(
                dict({'build': '', 'attack': '', 'tags': []}, **e['identity'])) if e['identity'].get('map')]
    for u in (model.get('map') or {}).get('units', []):
        ident = u.get('identity') or (labels.identity(u['style']) if u.get('style') else None)
        if ident:
            name = '{} {} {}'.format(u.get('team'), u.get('coach'), u.get('season'))
            errs += [f'{name}: conflicto {c}' for c in labels.conflicts(ident)]
            errs += _published_identity_errors(name, ident)
    return errs


def _assigned_constants(path: pathlib.Path) -> dict[str, Any]:
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except (OSError, SyntaxError):
        return {}
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = node.value.value
    return out


def check_thresholds(paths: Optional[list[pathlib.Path]] = None) -> list[str]:
    """Un umbral por concepto: ningún módulo redefine con literal una constante de framework."""
    files = paths if paths is not None else _code_files()
    errs = []
    for p in files:
        for name, val in _assigned_constants(p).items():
            if name in FW_CONSTANTS:
                errs.append(f'{p.name}: redefine {name}={val} (framework: {FW_CONSTANTS[name]})')
    if fw.REC_CAMPO_RIVAL_X == fw.REC_ALTA_X:
        errs.append('framework: rec_campo_rival y rec_alta comparten umbral')
    return errs


def _code_files() -> list[pathlib.Path]:
    pipe = ROOT / 'pipeline'
    files = [p for p in pipe.glob('*.py') if p.name not in ('framework.py',) and not p.name.startswith('test_')]
    return files + sorted((pipe / 'analytics').glob('*.py')) + sorted((ROOT / 'app').glob('*.py'))


def run(model_dir: pathlib.Path = MODEL_DIR) -> dict[str, Any]:
    """Corre todas las revisiones y devuelve el reporte."""
    model_path = model_dir / 'model.json'
    model = json.loads(model_path.read_text(encoding='utf-8')) if model_path.exists() else {}
    payloads = load_payloads(model_dir)
    checks = {'etiquetas': check_labels(model), 'ids_metricas': check_metric_ids(payloads),
              'mismo_valor': check_same_values(payloads), 'umbrales': check_thresholds()}
    return {'ok': not any(checks.values()), 'payloads': len(payloads),
            'errores': {k: v[:200] for k, v in checks.items()}, 'conteo': {k: len(v) for k, v in checks.items()}}


def main() -> int:
    """CLI: escribe el reporte y sale con 1 si hay errores."""
    rep = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, ensure_ascii=False, allow_nan=False, indent=1), encoding='utf-8')
    print('coherencia:', 'OK' if rep['ok'] else 'ERRORES', rep['conteo'], 'payloads', rep['payloads'])
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
