"""Automatic acceptance checks AC-01..AC-17 -> docs/ACEPTACION.md.

Each check is a small function ``check_acXX(ctx) -> (status, evidence)`` registered
in ``CHECKS``. Unknown or not-yet-built items return PENDING with a reason, never OK.
Later agents extend a check by editing its function; the registry order is fixed.
Usage: .venv/bin/python -X utf8 pipeline/acceptance.py [--no-http] [--no-run] [--baseline]
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
OK, FAIL, PENDING = 'ok', 'fail', 'pending'
SYMBOL = {OK: '✅', FAIL: '❌', PENDING: '⏳'}
BASE_URL = 'http://127.0.0.1:8010'
HTTP_TIMEOUT_S = 5
CMD_TIMEOUT_S = 600
MODEL_API_MAX_BYTES = 4 * 1024 * 1024
DANGEROUS_MAX_BYTES = 250 * 1024
JARDINE_N, JARDINE_EPI_N = 91, 38
EXTRACT_IGNORED_KEYS = ('names',)
Result = tuple[str, str]


class Context(NamedTuple):
    root: Path
    http: bool = True
    run: bool = True


class Check(NamedTuple):
    ac_id: str
    title: str
    fn: Callable[[Context], Result]


# ---------------------------------------------------------------- pure helpers
def extract_digest(payload: dict) -> str:
    """sha256 of the simulator-facing part of an mx_ extract (stable key order)."""
    kept = {k: v for k, v in payload.items() if k not in EXTRACT_IGNORED_KEYS}
    text = json.dumps(kept, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def md_sections(text: str) -> list[str]:
    """Headings (any level) of a markdown text, without the hashes."""
    return [m.group(1).strip() for m in re.finditer(r'^#+\s+(.+)$', text, re.MULTILINE)]


# (rule id, predicate over a label row, explanation)
_FAST, _SLOW = ('Dominio vertical', 'Contragolpe'), ('Posesión elaborada', 'Reactivo')
_PRESS, _WAIT = ('Presión alta', 'Bloque medio agresivo'), ('Bloque bajo', 'Línea alta, presión selectiva')
CONTRADICTION_RULES = [
    ('pase_corto_vs_muy_vertical', lambda r: r['build'] == 'Pase corto' and 'Muy vertical' in r['tags'],
     'Salida "Pase corto" junto a la etiqueta "Muy vertical"'),
    ('rapidos_vs_pausados', lambda r: 'Ataques rápidos' in r['tags'] and r['q_off'] in _SLOW,
     'Etiqueta "Ataques rápidos" con cuadrante ofensivo pausado'),
    ('ataques_pausados_vs_mapa_rapido', lambda r: 'Ataques pausados' in r['tags'] and r['q_off'] in _FAST,
     'Etiqueta "Ataques pausados" con cuadrante ofensivo rápido'),
    ('contragolpe_vs_posesion', lambda r: r['build'] == 'Contragolpe' and r['q_off'] == 'Posesión elaborada',
     'Salida "Contragolpe" en cuadrante "Posesión elaborada"'),
    ('cede_vs_domina', lambda r: 'Cede el balón' in r['tags'] and (r['map_off'] or [0, 0])[1] >= 50,
     '"Cede el balón" pero el mapa lo ubica dominando el balón'),
    ('dueno_vs_cede', lambda r: 'Dueño del balón' in r['tags'] and (r['map_off'] or [0, 100])[1] < 50,
     '"Dueño del balón" pero el mapa lo ubica cediendo el balón'),
    ('def_alto_vs_mapa_bajo', lambda r: r['def'].startswith('Alto') and (r['map_dfn'] or [100, 0])[0] < 50,
     'Tarjeta defensiva "Alto" con línea baja en el mapa'),
    ('def_profundo_vs_mapa_alto', lambda r: r['def'] == 'Profundo' and (r['map_dfn'] or [0, 0])[0] >= 50,
     'Tarjeta defensiva "Profundo" con línea alta en el mapa'),
    ('linea_alta_vs_mapa', lambda r: 'Línea muy alta' in r['tags'] and r['q_dfn'] in ('Bloque bajo', 'Bloque medio agresivo'),
     '"Línea muy alta" en cuadrante de línea baja'),
    ('bloque_bajo_vs_mapa', lambda r: 'Bloque bajo' in r['tags'] and r['q_dfn'] in ('Presión alta', 'Línea alta, presión selectiva'),
     'Etiqueta "Bloque bajo" en cuadrante de línea alta'),
    ('asfixiante_vs_espera', lambda r: 'Presión asfixiante' in r['tags'] and r['q_dfn'] in _WAIT,
     '"Presión asfixiante" en cuadrante que espera'),
    ('no_presiona_vs_presiona', lambda r: 'Corta con duelos, no presiona' in r['tags'] and r['q_dfn'] in _PRESS,
     '"No presiona" en cuadrante que presiona'),
    ('def_card_vs_quadrant', lambda r: r['def'] not in ('', 'Datos insuficientes') and r['q_dfn'] not in ('sin dato',)
     and _card_family(r['def']) != _quad_family(r['q_dfn']),
     'La tarjeta "Enfoque defensivo" y el cuadrante del mapa usan reglas distintas y no coinciden'),
]


def _card_family(card: str) -> str:
    if card.startswith('Alto') or card == 'Agresivo':
        return 'alta'
    return 'baja' if card == 'Profundo' else 'media'


def _quad_family(quad: str) -> str:
    if quad in ('Presión alta', 'Línea alta, presión selectiva'):
        return 'alta'
    return 'baja' if quad == 'Bloque bajo' else 'media'


def label_contradictions(row: dict) -> list[dict]:
    """Contradictions between the label outputs of one entity (fcLabels, tags, quadName)."""
    row = dict({'build': '', 'def': '', 'att': '', 'tags': [], 'q_off': 'sin dato', 'q_dfn': 'sin dato',
                'map_off': None, 'map_dfn': None}, **row)
    return [{'id': row['id'], 'rule': rid, 'detalle': text} for rid, pred, text in CONTRADICTION_RULES if pred(row)]


# ---------------------------------------------------------------- IO helpers
def load_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def http_get(ctx: Context, path: str) -> bytes | None:
    if not ctx.http:
        return None
    try:
        with urllib.request.urlopen(BASE_URL + path, timeout=HTTP_TIMEOUT_S) as resp:
            return resp.read()
    except Exception:  # noqa: BLE001 - server down or route missing => None
        return None


def run_cmd(ctx: Context, cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ctx.root), capture_output=True, text=True, check=False, timeout=CMD_TIMEOUT_S)
    return proc.returncode, (proc.stdout + proc.stderr)[-400:]


def entity(model: dict | None, eid: str) -> dict | None:
    for e in (model or {}).get('entities', []):
        if e.get('id') == eid:
            return e
    return None


# ---------------------------------------------------------------- baseline (AC-05 input, extract regression)
LABEL_JS = r"""
const fs = require('fs'), vm = require('vm');
const html = fs.readFileSync(process.argv[1] + '/frontend/index.html', 'utf8');
const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x => x[1]).join('\n');
const cut = (a, b) => js.slice(js.indexOf(a), js.indexOf(b, js.indexOf(a)));
const code = cut('  function fcLabels(', '  /* ---------- selector') + cut('  const MAPS = {', '  function renderMap(');
const M = JSON.parse(fs.readFileSync(process.argv[1] + '/model/model.json', 'utf8'));
const c = { M }; vm.createContext(c);
vm.runInContext(code + `\nthis.rows = M.entities.map(e => { const l = fcLabels(e.style || {}), m = e.map || {};
  return { id: e.id, kind: 'entidad', build: l.build, def: l.def, att: l.att, tags: tags(e.style || {}),
    q_off: quadName('off', m.off), q_dfn: quadName('dfn', m.dfn), map_off: m.off || null, map_dfn: m.dfn || null }; })
  .concat(M.map.units.map(u => ({ id: unitName(u), kind: 'unidad_mapa', build: '', def: '', att: '', tags: [],
    q_off: quadName('off', u.off), q_dfn: quadName('dfn', u.dfn), map_off: u.off || null, map_dfn: u.dfn || null })));`, c);
process.stdout.write(JSON.stringify(c.rows));
"""


def frontend_label_rows(root: Path) -> list[dict]:
    """Evaluate the current inline label functions of frontend/index.html for every entity and map unit."""
    proc = subprocess.run(['node', '-e', LABEL_JS, str(root)], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def write_baseline(root: Path) -> None:
    out = root / 'data' / 'out' / 'baseline'
    rows = frontend_label_rows(root)
    found = [c for r in rows for c in label_contradictions(r)]
    dump = {'fuente': 'frontend/index.html fcLabels/tags/quadName', 'filas': rows, 'contradicciones': found}
    (out / 'label_contradictions.json').write_text(json.dumps(dump, ensure_ascii=False, allow_nan=False, indent=1), encoding='utf-8')
    hashes = {f.name: extract_digest(json.loads(f.read_text(encoding='utf-8')))
              for f in sorted((root / 'data' / 'extract').glob('mx_*.json'))}
    meta = {'clave': 'sha256 de todo el extracto salvo ' + ', '.join(EXTRACT_IGNORED_KEYS), 'n': len(hashes), 'hashes': hashes}
    (out / 'extract_chain_hashes.json').write_text(json.dumps(meta, ensure_ascii=False, allow_nan=False, indent=1), encoding='utf-8')
    print(f'{len(rows)} filas de etiquetas, {len(found)} contradicciones, {len(hashes)} extractos')


# ---------------------------------------------------------------- checks
def check_ac01(ctx: Context) -> Result:
    doc = ctx.root / 'docs' / 'VALIDACION_MODELOS.md'
    if not doc.exists():
        return FAIL, 'falta docs/VALIDACION_MODELOS.md'
    text = doc.read_text(encoding='utf-8')
    heads = md_sections(text)
    has_before = any(h.startswith('Antes') for h in heads)
    after = text.split('## Después', 1)[1] if '## Después' in text else ''
    has_after = bool(after.strip()) and SYMBOL[PENDING] not in after
    if has_before and has_after:
        return OK, 'secciones Antes y Después presentes'
    if has_before:
        return PENDING, 'sección Antes presente; Después pendiente (fin de noche)'
    return FAIL, 'sin sección Antes'


def check_ac02(ctx: Context) -> Result:
    if not ctx.run:
        return PENDING, 'comandos desactivados (--no-run)'
    rc, _out = run_cmd(ctx, ['node', '--test', 'pipeline/test_golden_engine.js'])
    drc, _ = run_cmd(ctx, ['git', 'diff', '--quiet', 'main', '--', 'frontend/engine.js'])
    ev = 'test_golden_engine.js {}; git diff main -- frontend/engine.js {}'.format(
        'pasa' if rc == 0 else 'FALLA', 'vacío' if drc == 0 else 'CON CAMBIOS')
    return (OK if rc == 0 and drc == 0 else FAIL), ev


def check_ac03(ctx: Context) -> Result:
    model = load_json(ctx.root / 'model' / 'model.json')
    j, epi = entity(model, 'ame_jardine'), entity(model, 'ame_jardine_epi')
    if j is None:
        return FAIL, 'ame_jardine ausente en model.json'
    ev = ['ame_jardine n={} official={}'.format(j.get('n'), j.get('official'))]
    ok = j.get('n') == JARDINE_N and j.get('official') is True
    ev.append('ame_jardine_epi n={}'.format((epi or {}).get('n')) if epi else 'ame_jardine_epi ausente')
    ok = ok and bool(epi) and epi.get('n') == JARDINE_EPI_N
    ev.append('pac_almada %s' % ('presente' if entity(model, 'pac_almada') else 'ausente'))
    return (OK if ok else FAIL), '; '.join(ev) + '; cobertura mx_/an_/f360_ por verificar'


def check_ac04(ctx: Context) -> Result:
    fw, doc = ctx.root / 'pipeline' / 'framework.py', ctx.root / 'docs' / 'MARCO_ANALITICO.md'
    if not fw.exists():
        return PENDING, 'pipeline/framework.py aún no existe (agente Framework)'
    api = http_get(ctx, '/api/framework')
    ev = 'framework.py existe; MARCO_ANALITICO.md {}; /api/framework {}'.format(
        'existe' if doc.exists() else 'falta', 'responde' if api else 'sin respuesta')
    return (OK if doc.exists() and api else PENDING), ev


def check_ac05(ctx: Context) -> Result:
    audit = ctx.root / 'pipeline' / 'audit_coherence.py'
    if audit.exists() and ctx.run:
        rc, out = run_cmd(ctx, [sys.executable, '-X', 'utf8', str(audit)])
        return (OK if rc == 0 else FAIL), f'audit_coherence.py rc={rc}: {out.strip()[-200:]}'
    base = load_json(ctx.root / 'data' / 'out' / 'baseline' / 'label_contradictions.json')
    if base is None:
        return PENDING, 'sin audit_coherence.py ni tabla base'
    return FAIL, f"línea base: {len(base.get('contradicciones', []))} contradicciones de etiquetas (audit_coherence.py pendiente)"


def _pending_files(ctx: Context, files: list[str], what: str) -> Result:
    missing = [f for f in files if not (ctx.root / f).exists()]
    if missing:
        return PENDING, 'pendiente: falta {}'.format(', '.join(missing))
    return PENDING, f'{what}: archivos presentes, verificación de contenido manual/por revisor'


def check_ac06(ctx: Context) -> Result:
    return _pending_files(ctx, ['model/story/jardine.json'], 'componentes del reto')


def check_ac07(ctx: Context) -> Result:
    return _pending_files(ctx, ['pipeline/frames360.py', 'pipeline/extract_360.py'], 'métricas 360')


def check_ac08(ctx: Context) -> Result:
    return _pending_files(ctx, ['pipeline/analytics/transitions.py'], 'tipología de pérdidas')


def check_ac09(ctx: Context) -> Result:
    body = http_get(ctx, '/api/entities/ame_jardine/analysis')
    if body is None:
        return _pending_files(ctx, ['pipeline/analytics/dangerous.py'], 'jugadas peligrosas')
    return (OK if len(body) <= DANGEROUS_MAX_BYTES else FAIL), f'payload análisis {len(body)} bytes (límite {DANGEROUS_MAX_BYTES})'


def check_ac10(ctx: Context) -> Result:
    return _pending_files(ctx, ['app/play_rules.py', 'app/openrouter.py', 'docs/NL_BENCHMARK.md'], 'jugadas por texto')


def check_ac11(ctx: Context) -> Result:
    hits = []
    for f in sorted((ctx.root / 'frontend').rglob('*')):
        if f.suffix in ('.js', '.html') and f.name != 'engine.js':
            n = f.read_text(encoding='utf-8', errors='replace').count('toFixed(3)')
            if n:
                hits.append(f'{f.name}×{n}')
    if hits:
        return FAIL, 'toFixed(3) en: ' + ', '.join(hits)
    return PENDING, '0 toFixed(3); escaneo DOM/consola pendiente (revisor R2)'


def check_ac12(ctx: Context) -> Result:
    teams, coaches = http_get(ctx, '/api/explorer/teams'), http_get(ctx, '/api/explorer/coaches')
    if teams and coaches:
        return PENDING, 'explorador responde; revisar prior/intervalo/confianza'
    return _pending_files(ctx, ['pipeline/explorer.py'], 'explorador')


def check_ac13(ctx: Context) -> Result:
    return _pending_files(ctx, ['frontend/js/router.js', 'frontend/views/match.js'], 'modo Aficionado/DT')


def check_ac14(ctx: Context) -> Result:
    return _pending_files(ctx, ['pipeline/analytics/replay.py'], 'repetición con xG')


def check_ac15(ctx: Context) -> Result:
    story = load_json(ctx.root / 'model' / 'story' / 'jardine.json')
    if story is None:
        return PENDING, 'model/story/jardine.json aún no existe'
    bad = [c for c in story.get('chapters', []) for h in c.get('findings', []) if h.get('window', 'oficial') != 'oficial'
           and not h.get('badge')]
    return (OK if not bad else FAIL), f'{len(bad)} hallazgos fuera de ventana sin insignia'


def _touched_py(ctx: Context) -> list[str]:
    _, diff = run_cmd(ctx, ['git', 'diff', '--name-only', 'main'])
    _, new = run_cmd(ctx, ['git', 'ls-files', '--others', '--exclude-standard'])
    names = set((diff + '\n' + new).split())
    return sorted(n for n in names if n.endswith('.py') and (ctx.root / n).exists())


def _quality_commands(ctx: Context) -> dict[str, list[str]]:
    py = sys.executable
    tests = sorted(str(p.relative_to(ctx.root)) for p in (ctx.root / 'pipeline').glob('test_*.js'))
    return {
        'unittest': [py, '-X', 'utf8', '-m', 'unittest', 'discover', '-s', 'pipeline', '-p', 'test_*.py'],
        'node --test': ['node', '--test'] + tests,
        'check_model': [py, '-X', 'utf8', 'pipeline/check_model.py'],
        'validate.js 100': ['node', 'pipeline/validate.js', '100'],
        'referee.js 3': ['node', 'pipeline/referee.js', '3'],
    }


def check_ac16(ctx: Context) -> Result:
    if not ctx.run:
        return PENDING, 'comandos desactivados (--no-run)'
    ev, ok = [], True
    for name, cmd in _quality_commands(ctx).items():
        rc, _ = run_cmd(ctx, cmd)
        ok = ok and rc == 0
        ev.append('{} {}'.format(name, 'OK' if rc == 0 else f'FALLA rc={rc}'))
    files = _touched_py(ctx)
    rc, _ = run_cmd(ctx, [str(ctx.root / '.venv' / 'bin' / 'ruff'), 'check'] + files) if files else (0, '')
    ok = ok and rc == 0
    ev.append(f"ruff ({len(files)} archivos) {'limpio' if rc == 0 else 'con errores'}")
    body = http_get(ctx, '/api/model')
    if body is None:
        ev.append('/api/model sin respuesta')
        return (PENDING if ok else FAIL), '; '.join(ev)
    ok = ok and len(body) <= MODEL_API_MAX_BYTES
    ev.append('/api/model %.1f MB' % (len(body) / 1e6))
    return (OK if ok else FAIL), '; '.join(ev)


def check_ac17(ctx: Context) -> Result:
    doc = (ctx.root / 'docs' / 'RESUMEN_NOCHE.md').exists()
    health = http_get(ctx, '/api/health')
    ev = 'RESUMEN_NOCHE.md {}; /api/health {}'.format('existe' if doc else 'falta', 'responde' if health else 'sin respuesta')
    return (OK if doc and health else PENDING), ev


CHECKS = [
    Check('AC-01', 'Validar modelos', check_ac01), Check('AC-02', 'La simulación no cambia', check_ac02),
    Check('AC-03', 'Datos completos del protagonista', check_ac03), Check('AC-04', 'Framework explícito', check_ac04),
    Check('AC-05', 'Coherencia interna', check_ac05), Check('AC-06', 'Componentes del reto', check_ac06),
    Check('AC-07', 'Uso de 360', check_ac07), Check('AC-08', 'Errores al perder', check_ac08),
    Check('AC-09', 'Jugadas peligrosas en contra', check_ac09), Check('AC-10', 'Jugadas por texto', check_ac10),
    Check('AC-11', 'UI limpia', check_ac11), Check('AC-12', 'Rendimiento por equipo y DT', check_ac12),
    Check('AC-13', 'Modo Aficionado / DT', check_ac13), Check('AC-14', 'Simulación interpretativa', check_ac14),
    Check('AC-15', 'Ventana oficial', check_ac15), Check('AC-16', 'Calidad', check_ac16),
    Check('AC-17', 'Entrega', check_ac17),
]


def run_check(check: Check, ctx: Context) -> dict:
    """Run one check; exceptions become FAIL with the error as evidence."""
    try:
        status, evidence = check.fn(ctx)
    except Exception as exc:  # noqa: BLE001 - a broken check must not hide the others
        status, evidence = FAIL, f'error en la verificación: {type(exc).__name__}: {exc}'
    return {'id': check.ac_id, 'title': check.title, 'status': status, 'evidence': evidence}


def render_markdown(rows: list[dict], stamp: str) -> str:
    lines = ['# Aceptación automática', '', f'Generado por `pipeline/acceptance.py` el {stamp}.',
             '✅ cumple · ❌ no cumple · ⏳ pendiente o requiere revisión manual (con motivo).', '',
             '| AC | Criterio | Estado | Evidencia |', '|---|---|---|---|']
    for r in rows:
        lines.append('| {} | {} | {} | {} |'.format(r['id'], r['title'], SYMBOL[r['status']], r['evidence'].replace('|', '\\|')))
    return '\n'.join(lines) + '\n'


def main(argv: list[str]) -> int:
    if '--baseline' in argv:
        write_baseline(ROOT)
        return 0
    ctx = Context(ROOT, http='--no-http' not in argv, run='--no-run' not in argv)
    rows = [run_check(c, ctx) for c in CHECKS]
    out = ROOT / 'docs' / 'ACEPTACION.md'
    out.write_text(render_markdown(rows, datetime.now().strftime('%Y-%m-%d %H:%M')), encoding='utf-8')
    for r in rows:
        print(SYMBOL[r['status']], r['id'], r['evidence'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
