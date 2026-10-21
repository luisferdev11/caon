"""Etapa 3: analítica por entidad → model/analysis/<id>.json, más explorer.json y xg_grid.json.

Descubre los módulos registrados en pipeline/analytics/ (cada uno expone build(ctx) -> dict y se
registra con analytics.register), arma el contexto de cada entidad (partidos con ventana, rival, marcador)
y escribe un archivo por entidad con presupuesto de tamaño. Al final corre audit_coherence.py si existe.

    python pipeline/build_analysis.py            # todas las entidades con datos
    python pipeline/build_analysis.py ame_jardine pac_almada
"""
from __future__ import annotations

import importlib
import json
import pathlib
import subprocess
import sys
from collections.abc import Callable, Iterable

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
MODEL_DIR = ROOT / 'model'
EXTRACT = ROOT / 'data' / 'extract'
CACHE = ROOT / 'data' / 'cache'
ANALYSIS_LIMIT_BYTES = 400 * 1024
EPILOGUE_END = '2026-06-30'
NARRATIVE_IDS = ('ame_jardine', 'ame_jardine_epi', 'ame_almada', 'pac_almada', 'ame_solari', 'ame_ortiz',
                 'slp_jardine', 'san_almada')
GLOBAL_BUILDERS = (('explorer.py', 'explorer.json'), ('xg_grid.py', 'xg_grid.json'))
AUDIT_SCRIPT = HERE / 'audit_coherence.py'
try:
    from framework import OFFICIAL_END
except ImportError:  # el marco es de otro agente; mismo valor documentado
    OFFICIAL_END = '2025-06-30'


def match_window(date: str) -> str:
    """oficial (≤2025-06-30), epilogo (temporada 2025/26) o temprano (después)."""
    if date <= OFFICIAL_END:
        return 'oficial'
    return 'epilogo' if date <= EPILOGUE_END else 'temprano'


def context_matches(entity_matches: Iterable[dict], sb_by_id: dict) -> list[dict]:
    """[{id, date, window, venue, opponent, score [propio, rival], team_id}] desde el calendario StatsBomb."""
    rows = []
    for x in entity_matches:
        m = sb_by_id.get(x['mid'])
        if m is None:
            continue
        side, other = (x['side'], 'away' if x['side'] == 'home' else 'home')
        rows.append({'id': x['mid'], 'date': x['date'], 'window': match_window(x['date']),
                     'venue': 'local' if side == 'home' else 'visita',
                     'opponent': m[other + '_team'][other + '_team_name'],
                     'score': [m.get(side + '_score'), m.get(other + '_score')],
                     'team_id': m[side + '_team'][side + '_team_id']})
    return rows


def replay_meta(m: dict) -> dict:
    """Metadatos que espera analytics.replay a partir de un partido del calendario."""
    return {'match_id': m['match_id'], 'date': m.get('match_date'),
            'home_id': m['home_team']['home_team_id'], 'away_id': m['away_team']['away_team_id'],
            'home_name': m['home_team']['home_team_name'], 'away_name': m['away_team']['away_team_name'],
            'home_score': m.get('home_score'), 'away_score': m.get('away_score')}


def entities_to_build(entities: Iterable[dict], has_data: Callable[[dict], bool]) -> list[str]:
    """Entidades narrativas y de comparación siempre; las demás reales si ya tienen datos descargados."""
    return [e['id'] for e in entities
            if e.get('kind') == 'real' and (e['id'] in NARRATIVE_IDS or has_data(e))]


def index_by_model_id(entities: Iterable[dict], display_fn: Callable[[dict], tuple]) -> dict[str, dict]:
    """{id del modelo: entidad}; build_model renombra las entidades actuales con display()."""
    out = {}
    for e in entities:
        mid_, label, coach = display_fn(e)
        out[mid_] = dict(e, id=mid_, label=label, coach=coach)
    return out


def _size(obj) -> int:
    return len(json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8'))


def enforce_budget(payload: dict, limit: int = ANALYSIS_LIMIT_BYTES) -> tuple[dict, list[str]]:
    """Si el archivo excede el límite, reemplaza los temas más pesados por null con motivo."""
    out, warnings = dict(payload), []
    while _size(out) > limit:
        topics = [k for k in out if k != 'meta' and not (isinstance(out[k], dict) and 'motivo' in out[k])]
        if not topics:
            break
        big = max(topics, key=lambda k: _size(out[k]))
        warnings.append(f'{big}: {_size(out[big])} bytes omitidos por presupuesto')
        out[big] = {'valor': None, 'motivo': f'excede el presupuesto de {limit // 1024} KB por entidad'}
    return out, warnings


# ---------------------------------------------------------------- IO
def discover() -> list[str]:
    """Importa cada pipeline/analytics/<tema>.py (se registran solos) y devuelve los temas."""
    import analytics
    for path in sorted((HERE / 'analytics').glob('*.py')):
        if path.stem != '__init__':
            importlib.import_module(f'analytics.{path.stem}')
    return analytics.topics()


def read_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def has_data(entity: dict) -> bool:
    return any((EXTRACT / f"an_{x['mid']}.json").exists() for x in entity.get('matches', []))


def replay_ctx(rows: list[dict], sb_by_id: dict) -> dict:
    """Contexto de analytics.replay; los eventos se leen de uno en uno (generador)."""
    def gen():
        for r in rows:
            events = read_json(CACHE / f"v8_events_{r['id']}.json")
            if events:
                yield {'meta': replay_meta(sb_by_id[r['id']]), 'events': events}
    team_id = rows[0]['team_id'] if rows else None
    return {'team_id': team_id, 'matches': gen()}


def build_entity(entity: dict, slim: dict, sb_by_id: dict, topics: list[str]) -> dict:
    """Payload completo de una entidad (sin presupuesto aplicado)."""
    import analytics
    rows = context_matches(entity['matches'], sb_by_id)
    ctx = analytics.EntityContext(entity_id=entity['id'], label=slim.get('label', entity['id']),
                                  team=entity['team'], coach=slim.get('coach') or entity.get('coach_key', ''),
                                  matches=rows)
    payload = {'meta': {'id': entity['id'], 'label': ctx.label, 'window': slim.get('window'), 'n': len(rows),
                        'windows': {w: sum(1 for r in rows if r['window'] == w) for w in ('oficial', 'epilogo', 'temprano')}}}
    for topic in topics:
        topic_ctx = replay_ctx(rows, sb_by_id) if topic == 'replay' else ctx
        payload.update(analytics.build_all(topic_ctx, only=[topic]))
    return payload


def run_script(script: pathlib.Path, *args: str) -> int:
    if not script.exists():
        print('  (no existe)', script.name, flush=True)
        return 0
    return subprocess.run([sys.executable, '-X', 'utf8', str(script), *args], check=False).returncode


def main(argv: list[str]) -> int:
    from build_model import display
    from entities import build_entities
    from model_split import dump_json
    model = read_json(MODEL_DIR / 'model.json') or {}
    slim_by_id = {e['id']: e for e in model.get('entities', [])}
    ents, ms = build_entities()
    sb_by_id = {m['match_id']: m for m in ms}
    by_id = index_by_model_id(ents, display)
    for eid, e in by_id.items():
        e['kind'] = slim_by_id.get(eid, {}).get('kind', 'real')
    wanted = argv or entities_to_build(by_id.values(), has_data)
    topics = discover()
    print('temas analíticos:', ', '.join(topics) or '(ninguno)', flush=True)
    (MODEL_DIR / 'analysis').mkdir(parents=True, exist_ok=True)
    for eid in wanted:
        payload, warnings = enforce_budget(build_entity(by_id[eid], slim_by_id.get(eid, {}), sb_by_id, topics))
        payload['meta']['advertencias'] = warnings
        dump_json(payload, MODEL_DIR / 'analysis' / f'{eid}.json')
        print(f'  {eid:20s} {_size(payload) // 1024} KB', *warnings, flush=True)
    status = 0
    for script, out in GLOBAL_BUILDERS:
        status |= run_script(HERE / script, '--out', str(MODEL_DIR / out))
    status |= run_script(AUDIT_SCRIPT)
    return status


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
