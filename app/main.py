"""Servidor de Caon (Vestidor Táctico).

Sirve la página (frontend/) y una API pequeña de solo lectura sobre el modelo ya construido
(model/model.json). La simulación corre en el navegador con frontend/engine.js.

Arrancar:  uvicorn app.main:app --reload      →  http://127.0.0.1:8000
Documentación interactiva de la API:          →  http://127.0.0.1:8000/docs
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'frontend'
MODEL_PATH = ROOT / 'model' / 'model.json'

app = FastAPI(title='Caon · Vestidor Táctico', description='Estilos de juego de Liga MX y simulación de partidos con datos StatsBomb.')

_cache = {'mtime': None, 'model': None}


def load_model():
    """Lee model/model.json y lo vuelve a leer solo si cambió (tras correr el pipeline)."""
    if not MODEL_PATH.exists():
        raise HTTPException(503, 'No existe model/model.json. Corre: python pipeline/run.py build')
    mtime = MODEL_PATH.stat().st_mtime
    if _cache['mtime'] != mtime:
        _cache['model'] = json.loads(MODEL_PATH.read_text(encoding='utf-8'))
        _cache['mtime'] = mtime
    return _cache['model']


def team_summary(e):
    return {k: e.get(k) for k in ('id', 'label', 'team', 'coach', 'group', 'kind', 'n', 'd0', 'd1', 'official', 'formation')}


@app.get('/api/health')
def health():
    m = load_model()
    return {'ok': True, 'teams': len(m['entities']), 'built': m['meta'].get('built')}


@app.get('/api/model')
def model():
    """El modelo completo que usa la página (agregados, sin eventos crudos)."""
    return FileResponse(MODEL_PATH, media_type='application/json')


@app.get('/api/teams')
def teams():
    """Lista de equipos-entrenador disponibles."""
    return [team_summary(e) for e in load_model()['entities']]


@app.get('/api/teams/{team_id}')
def team(team_id: str):
    """Plan de juego, once tipo, lanzadores y posición en el mapa de un equipo-entrenador."""
    for e in load_model()['entities']:
        if e['id'] == team_id:
            out = team_summary(e)
            out.update(style=e.get('style') or {}, style_status=e.get('style_status'), shape=e.get('shape') or [],
                       roles=e.get('roles'), context=e.get('context'), temporal=e.get('temporal'),
                       context_comparisons=e.get('context_comparisons'), context_status=e.get('context_status'),
                       coverage=e.get('coverage'),
                       personnel=e.get('personnel'),
                       map=e.get('map'), note=e.get('note'))
            return out
    raise HTTPException(404, f'No existe el equipo {team_id}')


<<<<<<< HEAD
@app.get('/api/teams/{team_id}/context')
def context(team_id: str):
    """Contextos observados, cobertura y diferencias descriptivas."""
    data = team(team_id)
    return {key: data.get(key) for key in ('id', 'label', 'coverage', 'context', 'context_status', 'context_comparisons')}


@app.get('/api/teams/{team_id}/temporal')
def temporal(team_id: str):
    """Evolución cronológica agregada desde los resúmenes de partidos observados."""
    for e in load_model()['entities']:
        if e['id'] == team_id:
            return {'team': team_summary(e), 'temporal': e.get('temporal'),
                    'note': (e.get('temporal') or {}).get('note')}
    raise HTTPException(404, f'No existe el equipo {team_id}')


@app.get('/api/teams/{team_id}/personnel')
def personnel(team_id: str):
    """Participación observada, posiciones registradas y sustituciones."""
    for e in load_model()['entities']:
        if e['id'] == team_id:
            return {'team': team_summary(e), 'personnel': e.get('personnel')}
    raise HTTPException(404, f'No existe el equipo {team_id}')


@app.get('/api/teams/{team_id}/lineups')
def lineups(team_id: str):
    for e in load_model()['entities']:
        if e['id'] == team_id:
            personnel_data = e.get('personnel') or {}
            return {'team': team_summary(e),
                    'starting_lineups': personnel_data.get('starting_lineups', []),
                    'matches': personnel_data.get('matches', [])}
    raise HTTPException(404, f'No existe el equipo {team_id}')


@app.get('/api/teams/{team_id}/substitutions')
def substitutions(team_id: str):
    for e in load_model()['entities']:
        if e['id'] == team_id:
            personnel_data = e.get('personnel') or {}
            return {'team': team_summary(e),
                    'substitutions': personnel_data.get('substitutions', []),
                    'coverage': personnel_data.get('coverage', {})}
=======
@app.get('/api/teams/{team_id}/dangerous-plays')
def dangerous_plays(team_id: str):
    """Top de secuencias ofensivas rivales observadas en los partidos del equipo."""
    for e in load_model()['entities']:
        if e['id'] == team_id:
            return {
                'team': team_summary(e),
                'plays': e.get('dangerous_plays', []),
                'criterion': '100 × gol + 10 × xG + peligro de zona (min(max(x del remate − 80, 0), 40)); los goles siempre quedan por delante.',
                'limitations': 'Solo se incluyen posesiones rivales que terminan en remate y eventos registrados por StatsBomb. No se interpolan posiciones ni se usan datos 360 en este modelo.',
            }
>>>>>>> origin/main
    raise HTTPException(404, f'No existe el equipo {team_id}')


@app.get('/')
def index():
    return FileResponse(FRONTEND / 'index.html')


# engine.js y cualquier otro archivo estático del frontend
app.mount('/', StaticFiles(directory=FRONTEND), name='frontend')
