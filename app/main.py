"""Servidor de CAON (Trabajo Táctico).

Sirve el portal (frontend/index.html), el laboratorio de simulación (frontend/lab.html) y una API de solo
lectura sobre el modelo construido en model/:
  model.json              modelo ligero que usa el simulador (≤ 4 MB)
  entities/<id>.json      detalle pesado por entidad (temporal, personal, contexto, cobertura)
  analysis/<id>.json      analítica por entidad (build_analysis.py)
  explorer.json           explorador de equipos y DT
  story/<nombre>.json     historia del portal
Los archivos se releen cuando cambia su fecha de modificación.

Arrancar:  uvicorn app.main:app --port 8010   →  http://127.0.0.1:8010
"""
import importlib.util
import json
import re
import unicodedata
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'frontend'
MODEL_DIR = ROOT / 'model'
FRAMEWORK_PATH = ROOT / 'pipeline' / 'framework.py'
SAFE_KEY = re.compile(r'^[A-Za-z0-9_\-]{1,80}$')
EXPLORER_KINDS = {'teams': ('equipos', 'teams'), 'coaches': ('entrenadores', 'coaches'),
                  'team': ('equipos', 'teams'), 'coach': ('entrenadores', 'coaches')}
EXPLORER_NAME_KEYS = ('key', 'id', 'team', 'coach')
EXPLORER_HEAVY_KEYS = ('temporadas', 'tenencias', 'entidades')   # solo en el detalle de cada ficha
EXPLORER_LIST_METRIC_KEYS = ('id', 'value', 'raw', 'ci', 'ref_pct', 'n', 'window')  # nombre y unidad salen del catálogo
SUMMARY_KEYS = ('id', 'label', 'team', 'coach', 'group', 'kind', 'n', 'd0', 'd1', 'official', 'formation')

app = FastAPI(title='CAON · Trabajo Táctico',
              description='Estilos de juego de Liga MX, historia de Jardine en América y simulación con datos StatsBomb.')

_cache = {}


def clear_cache():
    """Vacía la caché de archivos JSON (tests y recargas)."""
    _cache.clear()


def model_path():
    return MODEL_DIR / 'model.json'


def read_json(path):
    """JSON cacheado por mtime; None si el archivo no existe."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    hit = _cache.get(path)
    if hit is None or hit[0] != mtime:
        hit = (mtime, json.loads(path.read_text(encoding='utf-8')))
        _cache[path] = hit
    return hit[1]


def safe_key(key, what):
    """Valida identificadores usados como nombre de archivo (evita rutas arbitrarias)."""
    if not SAFE_KEY.match(key or ''):
        raise HTTPException(404, f'No existe {what} «{key}»')
    return key


def load_model():
    """Modelo ligero (model/model.json)."""
    model = read_json(model_path())
    if model is None:
        raise HTTPException(503, 'No existe model/model.json. Corre: python pipeline/run.py build')
    return model


def team_summary(e):
    return {k: e.get(k) for k in SUMMARY_KEYS}


def find_entity(team_id):
    """Entidad completa: la ligera de model.json + su detalle en model/entities/<id>.json."""
    for e in load_model()['entities']:
        if e.get('id') == team_id:
            detail = read_json(MODEL_DIR / 'entities' / f'{safe_key(team_id, "el equipo")}.json') or {}
            out = dict(detail)
            out.update(e)
            return out
    raise HTTPException(404, f'No existe el equipo {team_id}')


@app.get('/api/health')
def health():
    m = load_model()
    return {'ok': True, 'teams': len(m['entities']), 'built': m['meta'].get('built')}


@app.get('/api/model')
def model():
    """El modelo ligero que usa el simulador (agregados, sin eventos crudos)."""
    load_model()
    return FileResponse(model_path(), media_type='application/json')


@app.get('/api/teams')
def teams():
    """Lista de equipos-entrenador disponibles."""
    return [team_summary(e) for e in load_model()['entities']]


@app.get('/api/teams/{team_id}')
def team(team_id: str):
    """Plan de juego, once tipo, lanzadores, contexto y posición en el mapa de un equipo-entrenador."""
    e = find_entity(team_id)
    out = team_summary(e)
    out.update(style=e.get('style') or {}, style_status=e.get('style_status'), shape=e.get('shape') or [],
               roles=e.get('roles'), context=e.get('context'), temporal=e.get('temporal'),
               context_comparisons=e.get('context_comparisons'), context_status=e.get('context_status'),
               coverage=e.get('coverage'), personnel=e.get('personnel'), map=e.get('map'), note=e.get('note'),
               window=e.get('window'), identity=e.get('identity'))
    return out


@app.get('/api/teams/{team_id}/context')
def context(team_id: str):
    """Contextos observados, cobertura y diferencias descriptivas."""
    data = team(team_id)
    return {key: data.get(key) for key in ('id', 'label', 'coverage', 'context', 'context_status', 'context_comparisons')}


@app.get('/api/teams/{team_id}/temporal')
def temporal(team_id: str):
    """Evolución cronológica agregada desde los resúmenes de partidos observados."""
    e = find_entity(team_id)
    return {'team': team_summary(e), 'temporal': e.get('temporal'), 'note': (e.get('temporal') or {}).get('note')}


@app.get('/api/teams/{team_id}/personnel')
def personnel(team_id: str):
    """Participación observada, posiciones registradas y sustituciones."""
    e = find_entity(team_id)
    return {'team': team_summary(e), 'personnel': e.get('personnel')}


@app.get('/api/teams/{team_id}/lineups')
def lineups(team_id: str):
    e = find_entity(team_id)
    data = e.get('personnel') or {}
    return {'team': team_summary(e), 'starting_lineups': data.get('starting_lineups', []), 'matches': data.get('matches', [])}


@app.get('/api/teams/{team_id}/substitutions')
def substitutions(team_id: str):
    e = find_entity(team_id)
    data = e.get('personnel') or {}
    return {'team': team_summary(e), 'substitutions': data.get('substitutions', []), 'coverage': data.get('coverage', {})}


# ---------------------------------------------------------------- portal
def framework_module():
    """pipeline/framework.py (se carga por ruta para no tocar sys.path)."""
    spec = importlib.util.spec_from_file_location('caon_framework', FRAMEWORK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_framework():
    """DEFINITIONS de pipeline/framework.py."""
    return framework_module().DEFINITIONS


@app.get('/api/framework')
def framework():
    """Marco analítico: definiciones, KPIs, nombres de etiquetas, umbrales, supuestos, alcance y límites."""
    try:
        return framework_module().framework_payload()
    except Exception as exc:
        raise HTTPException(503, f'El marco analítico no está disponible: {type(exc).__name__}') from exc


def analysis_for(entity_id):
    return read_json(MODEL_DIR / 'analysis' / f'{safe_key(entity_id, "la entidad")}.json')


@app.get('/api/entities')
def entities():
    """Entidades con su ventana (oficial, epílogo, temprano) y si ya tienen analítica."""
    out = []
    for e in load_model()['entities']:
        row = team_summary(e)
        row.update(window=e.get('window'), identity=e.get('identity'),
                   has_analysis=(MODEL_DIR / 'analysis' / f"{e.get('id')}.json").exists())
        out.append(row)
    return out


@app.get('/api/entities/{entity_id}/analysis')
def entity_analysis(entity_id: str):
    """Analítica por entidad (model/analysis/<id>.json)."""
    data = analysis_for(entity_id)
    if data is None:
        raise HTTPException(404, f'No existe analítica para la entidad {entity_id}')
    return data


def explorer_items(kind):
    data = read_json(MODEL_DIR / 'explorer.json')
    if data is None:
        raise HTTPException(404, 'El explorador todavía no está construido')
    for name in EXPLORER_KINDS[kind]:
        if data.get(name):
            return data[name]
    return []


def slug(text):
    """'André Jardine' → 'andre-jardine' (claves de URL del explorador)."""
    plain = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', plain).strip('-')


def explorer_match(item, key):
    names = [item.get(k) for k in EXPLORER_NAME_KEYS if item.get(k) is not None]
    return key in names or slug(key) in {slug(n) for n in names}


def explorer_summary(item):
    """Versión ligera de una ficha para las listas: sin temporadas/tenencias y con métricas mínimas."""
    out = {k: v for k, v in item.items() if k not in EXPLORER_HEAVY_KEYS}
    if isinstance(out.get('metrics'), dict):
        out['metrics'] = {m: {k: r[k] for k in EXPLORER_LIST_METRIC_KEYS if k in r} if isinstance(r, dict) else r
                          for m, r in out['metrics'].items()}
    return out


@app.get('/api/explorer/catalog')
def explorer_catalog():
    """Catálogo de métricas (nombre, unidad en lenguaje llano, orientación) y método del explorador."""
    data = read_json(MODEL_DIR / 'explorer.json')
    if data is None:
        raise HTTPException(404, 'El explorador todavía no está construido')
    return {'version': data.get('version'), 'metricas': data.get('metricas', []), 'metodo': data.get('metodo', {})}


@app.get('/api/explorer/{kind}')
def explorer_list(kind: str):
    """Unidades del explorador: equipos (teams) o entrenadores (coaches), sin el detalle pesado."""
    if kind not in ('teams', 'coaches'):
        raise HTTPException(404, f'No existe la sección del explorador «{kind}»; use teams o coaches')
    items = explorer_items(kind)
    return [explorer_summary(x) for x in items] if isinstance(items, list) else items


@app.get('/api/explorer/{kind}/{key}')
def explorer_item(kind: str, key: str):
    """Ficha de un equipo (team) o entrenador (coach) del explorador."""
    if kind not in ('team', 'coach'):
        raise HTTPException(404, f'No existe la sección del explorador «{kind}»; use team o coach')
    items = explorer_items(kind)
    if isinstance(items, dict):
        found = items.get(key)
    else:
        found = next((x for x in items if explorer_match(x, key)), None)
    if found is None:
        raise HTTPException(404, f'No existe «{key}» en el explorador')
    return found


MATCH_ROW_KEYS = ('match_id', 'fecha', 'torneo', 'window', 'equipo', 'rival', 'localia', 'actual', 'points', 'xpts', 'p',
                  'p_actual', 'sorpresivo', 'veredicto', 'xg', 'marcador')


@app.get('/api/kpis/{entity_id}')
def kpis(entity_id: str):
    """Los 7 KPIs de una entidad por ventana (valor, percentil, IQR, semáforo y frase descriptiva)."""
    data = read_json(MODEL_DIR / 'kpis' / f'{safe_key(entity_id, "la entidad")}.json')
    if data is None:
        raise HTTPException(404, f'No existen KPIs para la entidad {entity_id}')
    return data


@app.get('/api/entities/{entity_id}/matches')
def entity_matches(entity_id: str):
    """Partidos reales de una entidad con su resultado, xPts y veredicto (sin la ficha completa)."""
    data = read_json(MODEL_DIR / 'replay' / f'{safe_key(entity_id, "la entidad")}.json')
    if data is None:
        data = (analysis_for(entity_id) or {}).get('replay') or {}
    rows = data.get('partidos') or data.get('matches')
    if not rows:
        raise HTTPException(404, f'No existe la lista de partidos para la entidad {entity_id}')
    light = sorted(({k: r.get(k) for k in MATCH_ROW_KEYS if k in r} for r in rows), key=lambda r: r.get('fecha') or '')
    return {'entity': entity_id, 'n': len(light), 'partidos': light}


@app.get('/api/xg_grid')
def xg_grid():
    """Rejilla y coeficientes del modelo de xG (distancia, ángulo, cabeza) para interpretar jugadas."""
    data = read_json(MODEL_DIR / 'xg_grid.json')
    if data is None:
        raise HTTPException(404, 'La rejilla de xG todavía no está construida')
    return data


@app.get('/api/story/{name}')
def story(name: str):
    """Capítulos de la historia del portal (jardine, almada)."""
    data = read_json(MODEL_DIR / 'story' / f'{safe_key(name, "la historia")}.json')
    if data is None:
        raise HTTPException(404, f'No existe la historia «{name}»')
    return data


@app.get('/api/replay/{entity_id}')
def replay(entity_id: str):
    """Repetición con xG de los partidos reales de una entidad (¿mereció ganar?)."""
    data = read_json(MODEL_DIR / 'replay' / f'{safe_key(entity_id, "la entidad")}.json')
    if data is None:
        data = (analysis_for(entity_id) or {}).get('replay')
    if data is None:
        raise HTTPException(404, f'No existe repetición con xG para {entity_id}')
    return data


def find_match(match_id):
    """Busca la ficha del partido en model/matches/<id>.json o en la repetición de cada entidad."""
    card = read_json(MODEL_DIR / 'matches' / f'{match_id}.json')
    if card is not None:
        return card
    for e in load_model()['entities']:
        rep = (analysis_for(e.get('id', '')) or {}).get('replay') or {}
        rows = rep.get('partidos') or rep.get('matches') or []
        for row in rows:
            if row.get('match_id') == match_id:
                return row
    return None


@app.get('/api/matches/{match_id}')
def match(match_id: int):
    """Ficha de un partido real: marcador, xG acumulado, ¿mereció ganar?."""
    card = find_match(match_id)
    if card is None:
        raise HTTPException(404, f'No existe el partido {match_id}')
    return card


try:
    from app.nlplay import router as nlplay_router
    app.include_router(nlplay_router)
except ImportError:  # el laboratorio de jugadas por texto es opcional
    nlplay_router = None


@app.get('/')
def index():
    return FileResponse(FRONTEND / 'index.html')


@app.get('/lab.html')
def lab():
    path = FRONTEND / 'lab.html'
    if not path.exists():
        raise HTTPException(404, 'No existe el laboratorio (frontend/lab.html)')
    return FileResponse(path)


for _sub in ('js', 'views', 'css'):
    app.mount(f'/{_sub}', StaticFiles(directory=FRONTEND / _sub, check_dir=False), name=f'frontend-{_sub}')
# engine.js y cualquier otro archivo estático del frontend
app.mount('/', StaticFiles(directory=FRONTEND), name='frontend')
