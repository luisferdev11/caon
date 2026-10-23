# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Auditoría de coherencia interna (AC-05).

Revisa: (1) etiquetas sin pares en conflicto, tarjeta defensiva = cuadrante del mapa, punto del mapa = motor y
toda identidad publicada (modelo, explorador, análisis, historia) igual a ``labels.identity`` de sus percentiles
y sin afirmar lo que los números no sostienen (``labels.claim_violations``); (2) todo registro de
métrica publicado bajo ``model/`` usa un ``id`` de ``framework.DEFINITIONS``; (3) el mismo ``id`` tiene el
mismo valor en todas las vistas (historia, tablero, Almada, explorador); (4) un único umbral por concepto.
Uso: ``.venv/bin/python -X utf8 pipeline/audit_coherence.py`` → ``data/out/audits/coherence.json``.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import sys
from collections.abc import Iterator
from typing import Any, Optional

import framework as fw
import labels

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'model'
PAYLOAD_DIRS = ('analysis', 'story', 'explorer', 'entities', 'kpis', 'replay')
PAYLOAD_FILES = ('explorer.json',)
STORY_PREFIX = 'story'
BADGE_KEYS = ('fuera_de_ventana', 'badge')
OUT = ROOT / 'data' / 'out' / 'audits' / 'coherence.json'
VALUE_TOL = 1e-6
FW_CONSTANTS = {k: v for k, v in vars(fw).items()
                if k.isupper() and isinstance(v, (int, float)) and not isinstance(v, bool)}
FW_X_THRESHOLDS = {k: v for k, v in FW_CONSTANTS.items() if k.endswith('_X')}


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
    """Payloads JSON publicados bajo los directorios conocidos de ``model/`` y los archivos sueltos conocidos."""
    paths = [root / f for f in PAYLOAD_FILES if (root / f).is_file()]
    for d in PAYLOAD_DIRS:
        paths += sorted((root / d).glob('**/*.json')) if (root / d).is_dir() else []
    out: dict[str, Any] = {}
    for p in paths:
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


IDENTITY_FIELDS = ('build', 'defense', 'attack', 'offense_style', 'tags', 'map')
IDENTITY_KEYS = ('identity', 'identidad')


def _published_identity_errors(eid: str, ident: dict[str, Any]) -> list[str]:
    dfn = (ident.get('map') or {}).get('dfn')
    if dfn and ident.get('defense') != dfn[2]:
        return ['{}: tarjeta defensiva "{}" ≠ cuadrante "{}"'.format(eid, ident.get('defense'), dfn[2])]
    return []


def check_identity(name: str, ident: dict[str, Any], style: Optional[dict[str, Any]]) -> list[str]:
    """Una identidad publicada: sin pares en conflicto, tarjeta = mapa y, con percentiles, igual al motor."""
    full = dict({'build': '', 'attack': '', 'tags': []}, **ident)
    errs = [f'{name}: conflicto {c}' for c in labels.conflicts(full)] if ident.get('map') else []
    errs += _published_identity_errors(name, ident)
    if not style:
        return errs
    fresh = labels.identity(style)
    stale = [k for k in IDENTITY_FIELDS if k in ident and ident[k] != fresh[k]]
    if stale:
        errs.append('{}: identidad publicada desactualizada en {} (regenerar con labels.identity)'.format(
            name, ', '.join(stale)))
    errs += [f'{name}: {v}' for v in labels.claim_violations(full, style)]
    return errs


def _map_point_errors(e: dict[str, Any]) -> list[str]:
    """El punto que dibuja el mapa (``entity.map``) es el del motor de etiquetas."""
    pts, drawn = labels.map_points(e.get('style') or {}), e.get('map') or {}
    return ['{}: punto del mapa {} {} ≠ motor {}'.format(e['id'], mk, drawn[mk], pts[mk])
            for mk in ('off', 'dfn') if mk in drawn and pts[mk] and list(drawn[mk] or [])[:2] != pts[mk]]


def check_labels(model: dict[str, Any]) -> list[str]:
    """0 pares en conflicto en todas las entidades y unidades del mapa; tarjeta defensiva = cuadrante."""
    errs = []
    for e in model.get('entities', []):
        style = e.get('style') or {}
        errs += ['{}: conflicto {}'.format(e['id'], c) for c in labels.conflicts(labels.identity(style))]
        if e.get('identity'):
            errs += check_identity(e['id'], e['identity'], style)
        errs += _map_point_errors(e)
    for u in (model.get('map') or {}).get('units', []):
        ident = u.get('identity') or (labels.identity(u['style']) if u.get('style') else None)
        if ident:
            errs += check_identity('{} {} {}'.format(u.get('team'), u.get('coach'), u.get('season')), ident,
                                   u.get('style'))
    return errs


def _style_of(holder: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Percentiles de estilo de quien publica la identidad: ``style`` o métricas con ``clave`` y ``ref_pct``."""
    if isinstance(holder.get('style'), dict):
        return holder['style']
    recs = holder.get('metrics') or holder.get('metricas') or []
    pairs = recs.items() if isinstance(recs, dict) else ((r.get('clave'), r) for r in recs if isinstance(r, dict))
    style = {k: r['ref_pct'] for k, r in pairs
             if k and isinstance(r, dict) and isinstance(r.get('ref_pct'), (int, float))}
    return style or None


def _identity_holders(obj: Any, path: str = '') -> Iterator[tuple]:
    if isinstance(obj, dict):
        for key in IDENTITY_KEYS:
            if isinstance(obj.get(key), dict):
                yield path, obj, obj[key]
        for k, v in obj.items():
            if k not in IDENTITY_KEYS:
                yield from _identity_holders(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _identity_holders(v, f'{path}[{i}]')


def check_payload_identities(payloads: dict[str, Any]) -> list[str]:
    """Identidades dentro de los payloads (explorador, análisis, historia) contra sus propios percentiles."""
    errs = []
    for name, doc in payloads.items():
        for path, holder, ident in _identity_holders(doc):
            who = holder.get('key') or holder.get('id') or holder.get('label') or path
            errs += check_identity(f'{name} {who}', ident, _style_of(holder))
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
    """Un umbral por concepto: ningún módulo redefine una constante de framework con OTRO valor."""
    files = paths if paths is not None else _code_files()
    errs = []
    for p in files:
        for name, val in _assigned_constants(p).items():
            if name in FW_CONSTANTS and val != FW_CONSTANTS[name]:
                errs.append(f'{p.name}: redefine {name}={val} (framework: {FW_CONSTANTS[name]})')
    if fw.REC_CAMPO_RIVAL_X == fw.REC_ALTA_X:
        errs.append('framework: rec_campo_rival y rec_alta comparten umbral')
    return errs


def threshold_warnings(paths: Optional[list[pathlib.Path]] = None) -> list[str]:
    """Avisos: copia local de una constante de framework (mismo valor) o alias probable de un umbral en x."""
    files = paths if paths is not None else _code_files()
    warns = []
    for p in files:
        for name, val in _assigned_constants(p).items():
            if name in FW_CONSTANTS:
                warns.append(f'{p.name}: copia local de {name} (importarla de framework)')
                continue
            twins = sorted(k for k, v in FW_X_THRESHOLDS.items() if name.endswith('_X') and v == val)
            if twins:
                warns.append('{}: {}={} parece alias de {}'.format(p.name, name, val, ', '.join(twins)))
    return warns


def window_badge_warnings(payloads: dict[str, Any]) -> list[str]:
    """AC-15: en la historia, todo registro fuera de la ventana oficial lleva insignia (``fuera_de_ventana``)."""
    warns = []
    for name, doc in payloads.items():
        if not name.startswith(STORY_PREFIX):
            continue
        for rec in _records(doc):
            if rec.get('window') != 'oficial' and not any(rec.get(k) for k in BADGE_KEYS):
                warns.append('{}: {} en ventana {} sin insignia'.format(name, rec.get('id'), rec.get('window')))
    return warns


USER_TEXT_BANNED = re.compile(r'\b(unknown|undefined|None|NaN|nan|null|Directness|losing|winning|Possession|Pressing)\b'
                              r'|proporción 0–1|team-stats')
STORY_TEXT_KEYS = ('titulo', 'hecho', 'interpretacion', 'accion')


def _story_findings(doc: Any) -> Iterator[dict[str, Any]]:
    for ch in (doc or {}).get('capitulos') or []:
        yield from ch.get('hallazgos') or []


def check_window_flags(payloads: dict[str, Any]) -> list[str]:
    """Todo payload publicado declara su ventana (historia, KPIs, repetición, analítica y explorador)."""
    errs = []
    for name, doc in payloads.items():
        if name.startswith(STORY_PREFIX + '/'):
            if not doc.get('ventana'):
                errs.append(f'{name}: sin ventana')
            errs += [f"{name}: hallazgo {f.get('id')} sin ventana" for f in _story_findings(doc) if not f.get('window')]
        elif name.startswith('kpis/'):
            for w, rows in (doc.get('kpis') or {}).items():
                if w not in fw.WINDOWS or any(not r.get('window') for r in rows):
                    errs.append(f'{name}: KPIs con ventana inválida o ausente ({w})')
        elif name.startswith('replay/'):
            errs += [f"{name}: partido {r.get('match_id')} sin ventana" for r in doc.get('partidos') or [] if not r.get('window')]
        elif name.startswith('analysis/'):
            if not (doc.get('meta') or {}).get('windows'):
                errs.append(f'{name}: meta sin ventanas')
            errs += [f'{name}: tema {k} sin ventana' for k, v in doc.items()
                     if k != 'meta' and not (isinstance(v, dict) and any(x in v for x in ('ventanas', 'por_ventana', 'motivo', 'error')))]
        elif name == 'explorer.json':
            for key in ('equipos', 'entrenadores'):
                errs += [f"{name}: {key} «{i.get('label') or i.get('key')}» sin ventana" for i in doc.get(key) or [] if not i.get('window')]
    return errs


def check_user_text(payloads: dict[str, Any]) -> list[str]:
    """Sin inglés, «unknown», NaN ni unidades técnicas en los textos que lee la persona usuaria."""
    errs = []

    def scan(name: str, field: str, text: Any) -> None:
        found = dict.fromkeys(m.group(0) for m in USER_TEXT_BANNED.finditer(text)) if isinstance(text, str) else {}
        errs.extend(f'{name}: {field}: «{tok}»' for tok in found)
    for name, doc in payloads.items():
        if name.startswith(STORY_PREFIX + '/'):
            for ch in doc.get('capitulos') or []:
                for k in ('conclusion', 'curioso'):
                    scan(name, f"capítulo {ch.get('orden')} {k}", (ch.get('aficionado') or {}).get(k))
            for f in _story_findings(doc):
                for k in STORY_TEXT_KEYS:
                    scan(name, f"{f.get('id')}.{k}", f.get(k))
        elif name == 'explorer.json':
            for m in doc.get('metricas') or []:
                for k in ('nombre', 'unit'):
                    scan(name, f"métrica {m.get('id')}.{k}", m.get(k))
    return errs


def _code_files() -> list[pathlib.Path]:
    pipe = ROOT / 'pipeline'
    files = [p for p in pipe.glob('*.py') if p.name not in ('framework.py',) and not p.name.startswith('test_')]
    return files + sorted((pipe / 'analytics').glob('*.py')) + sorted((ROOT / 'app').glob('*.py'))


def run(model_dir: pathlib.Path = MODEL_DIR) -> dict[str, Any]:
    """Corre todas las revisiones; ``ok`` depende solo de los errores, los avisos se reportan aparte."""
    model_path = model_dir / 'model.json'
    model = json.loads(model_path.read_text(encoding='utf-8')) if model_path.exists() else {}
    payloads = load_payloads(model_dir)
    checks = {'etiquetas': check_labels(model), 'etiquetas_vistas': check_payload_identities(payloads),
              'ids_metricas': check_metric_ids(payloads),
              'mismo_valor': check_same_values(payloads), 'umbrales': check_thresholds(),
              'ventana': check_window_flags(payloads), 'texto_usuario': check_user_text(payloads)}
    warns = {'umbrales': threshold_warnings(), 'insignia_ventana': window_badge_warnings(payloads)}
    return {'ok': not any(checks.values()), 'payloads': len(payloads),
            'errores': {k: v[:200] for k, v in checks.items()}, 'conteo': {k: len(v) for k, v in checks.items()},
            'avisos': {k: v[:200] for k, v in warns.items()},
            'conteo_avisos': {k: len(v) for k, v in warns.items()}}


def main() -> int:
    """CLI: escribe el reporte y sale con 1 si hay errores."""
    rep = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, ensure_ascii=False, allow_nan=False, indent=1), encoding='utf-8')
    print('coherencia:', 'OK' if rep['ok'] else 'ERRORES', rep['conteo'], 'avisos', rep['conteo_avisos'],
          'payloads', rep['payloads'])
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
