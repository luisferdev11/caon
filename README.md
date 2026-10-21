# Caon · Vestidor Táctico

Estilos de juego de entrenadores de la Liga MX medidos con datos de Hudl StatsBomb, y un simulador de partidos estilo FC que enfrenta esos estilos jugada a jugada. Proyecto para el Hackathon ISAC 2026 · Club América ("La historia de un entrenador a través de los datos").

Qué hace la app:
- **Plan de juego**: 14 métricas de cada equipo-entrenador en percentil contra la liga, con etiquetas tipo FC.
- **Contexto táctico**: comparación descriptiva por estado del marcador y localía, conservando minutos, posesiones y advertencias de muestra.
- **Mapa de estilos**: cada equipo-temporada de la liga en dos mapas (con y sin balón), trayectorias por temporada y estilos más parecidos.
- **Simular partido**: partido animado con 22 jugadores, faltas, tarjetas, córners, tiros libres y penales; modo resumen y partido completo.
- **Laboratorio táctico**: describe una jugada en español, conviértela en acciones estructuradas y reproduce una representación sobre la cancha.
- **Jugadas peligrosas**: Top 5 de posesiones rivales que terminaron en remate contra el equipo seleccionado, priorizando goles y mostrando únicamente eventos observados de StatsBomb.
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
frontend/index.html  la página (HTML + JS sin framework, incluido el laboratorio táctico)
frontend/engine.js   motor de simulación y animación (corre en el navegador y en Node)
model/model.json     modelo ya construido (solo agregados, sin eventos crudos)
pipeline/            descarga de datos y construcción del modelo
pipeline/dangerous.py extracción compacta de secuencias ofensivas rivales peligrosas
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
<<<<<<< HEAD
| `GET /api/teams/{id}` | Plan de juego, contexto, evolución temporal, once tipo, lanzadores y posición en el mapa |
| `GET /api/teams/{id}/temporal` | Periodos cronológicos, cobertura, métricas y contexto temporal |
| `GET /api/teams/{id}/personnel` | Jugadores, intervalos, posiciones observadas y sustituciones |
| `GET /api/teams/{id}/lineups` | Alineaciones iniciales y partidos con participación |
| `GET /api/teams/{id}/substitutions` | Sustituciones observadas y cobertura |
=======
| `GET /api/teams/{id}` | Plan de juego, once tipo, lanzadores y posición en el mapa |
| `GET /api/teams/{id}/dangerous-plays` | Top 5 de jugadas ofensivas rivales observadas contra el equipo |
>>>>>>> origin/main
| `GET /api/model` | El modelo completo que usa la página |

## Reconstruir el modelo (necesita credenciales de StatsBomb)

1. `cp .env.example .env` y llena `USER_STATSBOMB` y `PSWD_STATSBOMB`.
2. Corre el pipeline:

```bash
python pipeline/run.py download   # baja eventos, alineaciones y estadísticas (~2.7 GB, con caché)
python pipeline/run.py extract    # resume cada partido (~10 s)
python pipeline/run.py build      # construye y valida model/model.json (incluye jugadores y contextos)
python pipeline/check_model.py    # comprueba invariantes del modelo generado
python pipeline/run.py validate   # compara la simulación con los datos reales (requiere Node 18+)
python pipeline/run.py referee    # árbitro automático: revisa el reglamento (requiere Node 18+)
python pipeline/run.py all        # todo en orden
```

El análisis temporal se agrupa en bloques cronológicos de ocho partidos y
fusiona una cola menor de cinco partidos. Conserva ausencias como `null`,
expone la cobertura por métrica y no interpreta una variación como causalidad.
La interfaz muestra la evolución de las métricas disponibles junto con las
fechas y el número de partidos de cada periodo.

El servidor recarga el modelo solo cuando cambia; no hace falta reiniciarlo.

La participación de jugadores se deriva de lineups y eventos reales. Conserva
IDs, posiciones registradas, intervalos, minutos observados, sustituciones,
estado del marcador y warnings de cobertura. No infiere roles tácticos
complejos ni atribuye causalidad a los cambios de composición. Consulta
`docs/PERSONAL_JUGADORES.md` para las definiciones y limitaciones.

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

- [Informe de esta entrega y próximos pasos](docs/INFORME_CORRECCION_PRIORITARIA.md): cambios, pruebas, limitaciones y guía para continuar en equipo.
- `docs/DOCUMENTACION.md`: cómo funciona todo (fuentes, framework, modelo, estilo de cada entrenador, simulación, reglamento, validación, cómo extenderlo).
- `docs/como-funciona.html`: la misma explicación en una página visual.

## Correcciones de datos y contexto (schema 2)

`n` cuenta IDs de partidos procesados junto con ambos agregados. La cobertura de
estilo se conserva por separado para cada métrica. Los estilos incompletos no se
rellenan. Ganando/empatando/perdiendo y local/visitante incluyen exposición,
tasas, diferencias y advertencias. API adicional: `/api/teams/{id}/context`.
Las definiciones y limitaciones están en [METRICAS_TACTICAS.md](docs/METRICAS_TACTICAS.md).

Regeneración con datos ya descargados (no modifica los archivos de origen):

```powershell
python -X utf8 pipeline/run.py extract
python -X utf8 pipeline/run.py build
python -X utf8 pipeline/check_model.py
python -X utf8 -m unittest discover -s pipeline -p "test_*.py"
node --test pipeline/test_validate.js pipeline/test_frontend.js
node pipeline/validate.js 100
node pipeline/referee.js 3
```

La extracción actualiza automáticamente extractos de versiones anteriores.
Para forzar un recálculo de la misma versión: `python -X utf8 pipeline/extract.py --force`.
Cada construcción válida respalda el artefacto anterior en
`model/model.json.pre-build-<fecha-UTC>.gz` y verifica que se pueda recuperar.
Normalmente publica con reemplazo atómico; si el espacio solo alcanza para
reescribir el archivo, conserva el respaldo y restaura el original ante error.
Si ni siquiera alcanza, conserva el modelo original y, cuando es posible,
el resultado validado en `model/model.json.pending.gz`.
Dejar espacio libre suficiente evita ese modo de recuperación.

En este equipo el alias `python` y el entorno `.venv` inicial no eran utilizables
para toda la suite. El intérprete probado fue:

```powershell
$caonPython = 'C:\Users\eddym\AppData\Local\Programs\Python\Python313\python.exe'
& $caonPython -X utf8 pipeline/run.py extract
& $caonPython -X utf8 pipeline/run.py build
& $caonPython -X utf8 pipeline/check_model.py
& $caonPython -X utf8 -m unittest discover -s pipeline -p 'test_*.py'
```

Las pruebas HTTP requieren `httpx` además de las dependencias de ejecución.
Si se usa el sandbox de Windows, `TestClient` puede necesitar ejecución fuera
del aislamiento para abrir su socket interno. No necesita contactar un servidor externo.
