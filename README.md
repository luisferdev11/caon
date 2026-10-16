# Caon · Vestidor Táctico

Estilos de juego de entrenadores de la Liga MX medidos con datos de Hudl StatsBomb, y un simulador de partidos estilo FC que enfrenta esos estilos jugada a jugada. Proyecto para el Hackathon ISAC 2026 · Club América ("La historia de un entrenador a través de los datos").

Qué hace la app:
- **Plan de juego**: 14 métricas de cada equipo-entrenador en percentil contra la liga, con etiquetas tipo FC.
- **Mapa de estilos**: cada equipo-temporada de la liga en dos mapas (con y sin balón), trayectorias por temporada y estilos más parecidos.
- **Simular partido**: partido animado con 22 jugadores, faltas, tarjetas, córners, tiros libres y penales; modo resumen y partido completo.
- **Simulación rápida**: el mismo duelo 1,500 veces.

## Arrancar en 2 minutos

Necesitas Python 3.9+. No necesitas credenciales para usar la app: el modelo ya construido viene en `model/model.json`.

```bash
git clone https://github.com/luisferdev11/caon.git
cd caon
python3 -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abre http://127.0.0.1:8000. La API está documentada en http://127.0.0.1:8000/docs.

## Estructura

```
app/main.py          servidor (FastAPI): sirve la página y una API de solo lectura sobre el modelo
frontend/index.html  la página (HTML + JS sin framework)
frontend/engine.js   motor de simulación y animación (corre en el navegador y en Node)
model/model.json     modelo ya construido (solo agregados, sin eventos crudos)
pipeline/            descarga de datos y construcción del modelo
research/            exploraciones (prueba de concepto, agrupamiento, laboratorio de métricas)
docs/                documentación técnica completa
```

Cómo fluye todo:

```
StatsBomb API / Open Data → data/cache → pipeline/extract.py → data/extract → pipeline/build_model.py → model/model.json → app + frontend
```

### API

| Ruta | Qué devuelve |
|---|---|
| `GET /api/health` | Estado y número de equipos |
| `GET /api/teams` | Lista de equipos-entrenador |
| `GET /api/teams/{id}` | Plan de juego, once tipo, lanzadores y posición en el mapa |
| `GET /api/model` | El modelo completo que usa la página |

## Reconstruir el modelo (necesita credenciales de StatsBomb)

1. `cp .env.example .env` y llena `USER_STATSBOMB` y `PSWD_STATSBOMB`.
2. Corre el pipeline:

```bash
python pipeline/run.py download   # baja eventos, alineaciones y estadísticas (~2.7 GB, con caché)
python pipeline/run.py extract    # resume cada partido (~10 s)
python pipeline/run.py build      # construye model/model.json (~2 s)
python pipeline/run.py validate   # compara la simulación con los datos reales (requiere Node 18+)
python pipeline/run.py referee    # árbitro automático: revisa el reglamento (requiere Node 18+)
python pipeline/run.py all        # todo en orden
```

El servidor recarga el modelo solo cuando cambia; no hace falta reiniciarlo.

### Agregar un equipo o entrenador

Agrega una línea a `SPECIAL` en `pipeline/entities.py`:

```python
('pac_almada', 'Pachuca · Almada', 'Pachuca', 'Almada', '2022-01-01', '2025-06-30', 'Histórico'),
#  id           etiqueta            equipo en StatsBomb  entrenador  desde  hasta  grupo
```

y corre `python pipeline/run.py all`. Los entrenadores actuales de cada club se detectan solos. Más casos (entrenadores con pocos partidos, otras ligas, estilos configurados) en `docs/DOCUMENTACION.md`, sección 14.

## Cómo colaborar

- Trabaja en una rama (`git checkout -b mi-cambio`) y abre un pull request.
- Front: todo está en `frontend/index.html` (estilos, HTML y JS en un archivo) y `frontend/engine.js`.
- Back: `app/main.py` es un solo archivo; agrega rutas ahí.
- Datos y modelo: `pipeline/`. Si cambias el motor o el modelo, corre `validate` y `referee` antes de subir.
- Nunca subas `.env` ni la carpeta `data/` (ya están en `.gitignore`).

## Datos

- Liga MX: API de Hudl StatsBomb con las credenciales del hackathon. Ventana oficial del reto: Apertura 2021 – Clausura 2025; lo posterior aparece marcado en la app.
- Barcelona 2009–11: [StatsBomb Open Data](https://github.com/statsbomb/open-data) (licencia abierta con atribución).
- Las bases del hackathon permiten presentar resultados, no los datos: por eso el repo solo incluye el modelo agregado y no los eventos. Repo privado.

## Documentación

- `docs/DOCUMENTACION.md`: cómo funciona todo (fuentes, framework, modelo, estilo de cada entrenador, simulación, reglamento, validación, cómo extenderlo).
- `docs/como-funciona.html`: la misma explicación en una página visual.
