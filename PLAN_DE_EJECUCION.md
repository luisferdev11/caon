# PLAN DE EJECUCIÓN · Caon "La historia de André Jardine"

> Documento para retomar el trabajo en una sesión nueva.
> **Ejecutor:** Sonnet. **Advisor:** Opus, que revisa en cada puerta de control (G).
> Estado al 2026-10-21 17:00 (America/Mexico_City). Rama `overnight/jardine-historia`. Último commit: `f28fc74` (G1). **La Ola 2 está completa en disco pero SIN commit.**

---

## 0. Cómo usar este documento

### Roles
- **Ejecutor (Sonnet):** sigue las tareas `T-xx` en orden, marca `[x]` al terminar cada una y anota la evidencia (comando + resultado resumido) en `data/out/bitacora.md`. No inventa alcance nuevo.
- **Advisor (Opus):** en cada puerta de control (G1.5, G2, G3, G4, G5) revisa:
  - la evidencia;
  - el diff (`git diff --stat` + muestreo de archivos);
  - los criterios AC de la sección 5.

  Aprueba o devuelve con correcciones concretas. También resuelve las decisiones abiertas (sección 7) cuando el ejecutor lo pida.

### Reglas para ahorrar tokens (obligatorias)
La sesión anterior gastó demasiado con un workflow multi-agente, así que esta vez:
1. **No usar la herramienta Workflow ni lanzar más de 1 subagente a la vez.** Trabajar en una sola sesión secuencial.
2. **No leer archivos grandes completos.**
   - `model/*.json`, `data/cache/*` y los transcripts: usar `python -c`, `jq`, `head`, `grep -n`, o `Read` con `offset`/`limit`.
   - `frontend/lab.html` (1,059 líneas): leer solo el rango necesario.
3. **Capturas de pantalla solo en las puertas G3 y G4**, a lo más 1 por vista y por modo.
4. **Salida de las pruebas:** correrlas con `2>&1 | tail -20`.
5. **Antes de leer un archivo de requests** (`data/out/requests/*.md`), revisar si la tarea ya lo resume aquí.

### Marcado
- `[ ]` pendiente · `[x]` hecho · `[~]` parcial (explicar en una línea) · `[!]` bloqueado (explicar y pedir decisión al advisor).

---

## 1. Contexto

### 1.1 El reto (ITAM Sports Analytics · "La historia de un entrenador a través de los datos")
- **Qué pide:** con eventos y 360 de StatsBomb (Liga MX, **ventana oficial Apertura 2021 – Clausura 2025**), explicar cómo juega el equipo de un entrenador:
  - fase ofensiva: construcción, progresión, ocasiones;
  - fase defensiva: presión, organización, transiciones;
  - consistencia y variabilidad, y ajustes por contexto (rival, marcador, localía, momento);
  - uso de jugadores: roles, alineaciones, sustituciones;
  - balón parado ofensivo y defensivo;
  - evidencia cuantitativa: xG, OBV, pases progresivos, PPDA, field tilt y métricas propias;
  - un **framework explícito y con coherencia interna**.
- **Simulación:** opcional, solo para interpretar, no para predecir.
- **Criterios de evaluación (25% cada uno):** innovación, comunicación a un público no técnico, accionabilidad (KPIs), metodología y visualización.
- **Entregables:** reporte HTML (lo hace el equipo, no este plan), video de ≤5 min y 10 diapositivas si son finalistas.

### 1.2 Decisiones del usuario (no se discuten)
| Tema | Decisión |
|---|---|
| Protagonista | **América · Jardine**, Ap23–Cl25: **91 partidos**, todos con eventos y 360 |
| Epílogo | Jardine Ap25–Cl26 (38 partidos), **siempre rotulado "Fuera de ventana oficial"** |
| Capítulo final | **"¿Qué cambia con Almada?"**: Pachuca·Almada (Cl22–Cl25, 139 partidos, dentro de ventana) contra sus primeros 10 partidos en el América (2026/27, evidencia temprana) |
| Comparativos | América·Solari, América·Ortiz (antes de Jardine), San Luis·Jardine, Santos·Almada → "¿Jardine o el club?" |
| Explorador | Todos los equipos y DTs, con **prior de la carrera del DT** (encogimiento K=8 hacia su historia previa o hacia la liga), intervalos al 80% e indicador de confianza |
| Portal | Primero la historia y después el explorador. Lleva un **modo Aficionado** (estilo Google, lo esencial y lo divertido) y un **modo DT/Pro** (todo el detalle), una ficha por partido real y una ficha por DT |
| Jugadas por texto | Parser propio en español + LLM opcional vía **OpenRouter**. Solo modelos baratos que **no** sean de Anthropic. El crédito de la key es **de $3 en total** |
| Simulación | `frontend/engine.js` **no se modifica** (lo garantiza la prueba dorada) |
| Git | Commits locales en `overnight/jardine-historia`, **sin push** |
| Servidor | http://127.0.0.1:8010. **El puerto 8000 es de otro proyecto (superestela): no tocarlo** |
| Trabajo descartado | El trabajo del PR #1 queda descartado; solo se aplican sus lecciones (ver 1.5) |

### 1.3 Documentos de referencia (leer solo la sección que se necesite)
- Plan aprobado original: `~/.claude-percepthor/plans/es-que-actualmente-jardine-twinkly-cat.md`.
- Diseño técnico detallado (definiciones, contratos, métricas 360, KPIs, story, API, UI): `data/out/DISENO_DETALLADO.md`.
- Bitácora de las puertas de control: `data/out/bitacora.md`.
- Cobertura de datos: `data/out/coverage.md`.
- Peticiones entre agentes (pendientes para el integrador): `data/out/requests/A1.md` … `A9.md`. **Ya están resumidas en la tarea T-03.**
- Evidencia TDD: `data/out/tdd/*.log`.
- Notas de 360: `data/out/notes_360.md`.
- Handoff del workflow: `data/out/HANDOFF.md`.

### 1.4 Qué está hecho

#### G0 · commit `472bcc2` · verde
- Línea base validada: `docs/VALIDACION_MODELOS.md` (sección "Antes").
- **Prueba dorada del motor:** `pipeline/make_golden.js`, `pipeline/test_golden_engine.js` y `pipeline/fixtures/golden_*.json`.
- `pipeline/acceptance.py` genera `docs/ACEPTACION.md`.
- Hashes de extractos en `data/out/baseline/extract_chain_hashes.json`.
- Tabla de contradicciones de etiquetas en `data/out/baseline/label_contradictions.json`.

#### Ola 1 + G1 · commit `f28fc74` · verde
- Resultados del gate: 187 pruebas Python y 25 de Node pasan; prueba dorada OK; `validate.js` 0 errores; árbitro 0 infracciones.
- **Entidades:** `ame_jardine` (n=91, oficial), `ame_jardine_epi`, `pac_almada`, `ame_ortiz`, `ame_solari`, `slp_jardine`, `san_almada`. En total hay 30 entidades.
- **Descargas:** completas, incluida **toda la liga** (P5: 2,525 y P6: 507 partidos con eventos, lineups y 360; 0 fallas). Están en `data/cache`.
- **Framework:**
  - `pipeline/framework.py` + `framework_defs.py` (registro `DEFINITIONS`);
  - `sequences.py` (posesiones);
  - `extract_analysis.py` (`an_<mid>.json`, versión 4);
  - `labels.py` (motor de etiquetas `identity()`);
  - `audit_coherence.py`;
  - `docs/MARCO_ANALITICO.md`.
- **360:** `frames360.py` + `extract_360.py` producen **1,749 archivos `f360_*.json`**.
- **Modelo aligerado:** `model/model.json` pesa 1.2 MB y el resto vive en `model/entities/<id>.json`. Rutas nuevas en `app/main.py`.
- **Explorador, repetición y rejilla de xG:** `pipeline/explorer.py`, `pipeline/analytics/replay.py`, `pipeline/xg_grid.py`.
- **Portal (shell):** `frontend/index.html` (router por hash, interruptor Aficionado/DT), `frontend/js/*`, `frontend/views/*`. El laboratorio original se movió a `frontend/lab.html`.
- **Laboratorio de lenguaje natural:**
  - `app/nlplay.py`, `play_schema.py`, `play_rules.py`, `openrouter.py`, `env.py`;
  - `frontend/views/playlab.js`;
  - `docs/NL_BENCHMARK.md`;
  - ≥30 frases etiquetadas.

#### Ola 2 · en disco, **sin commit** (88 archivos cambiados)
Todos los agentes reportaron "done".

| Agente | Entregó | Pendientes que reporta |
|---|---|---|
| A2 (cierre del framework) | Regla exclusiva de etiquetas de presión (volumen, PPDA y contrapresión ya no se contradicen); `CONFLICTS` extendido; `an_` v4 | `audit_coherence` marca **52 errores** sobre el `model.json` actual. Son esperados y desaparecen al reconstruir (T-04) |
| A6 (cierre del explorador) | Repetición con xG, explorador v2 (etiqueta, identidad, métricas con intervalo, temporadas y tenencias), rejilla de xG v2 | Hay que publicarlos con `build_analysis` |
| A8 (sistema de diseño) | `frontend/css/tokens.css`, `components.css`, `pitch.css`, `js/theme.js`; colores fijos (protagonista dorado, rival azul, liga gris); explorador arreglado en el frontend | `pipeline/test_design_system.js` prohíbe colores literales en `frontend/views/` |
| A3 (análisis 360) | `analytics/shape360*.py` con vigilancias, tipología de errores, bloque, rompe-líneas, presión coordinada, cambios, córner y fotos de jugada; referencia de liga en `data/extract/shape360_ref.json` | Falta que el integrador corra `shape360_ref` antes de `build_analysis` |
| A4 (ofensiva, defensa, peligrosas) | `analytics/{offense,defense,transitions,dangerous,dangerous_detail}.py`, capa `a4_facts`, referencia `a4_reference` | Borró `pipeline/dangerous.py`, pero falta registrarlo con `git rm` |
| A5 (balón parado, contexto, uso) | `analytics/{setpieces,context,context_club,context_io,usage,usage_subs}.py`, banda bootstrap, "¿Jardine o el club?" | Al terminar reportó 471 pruebas Python en verde |

**El integrador 2 (A7b) no llegó a ejecutarse:** no existen `pipeline/kpis.py`, `pipeline/story.py` ni `model/story/`. Por eso `model/analysis/*` y `model/explorer.json` siguen siendo las versiones de G1 y **el servidor en 8010 muestra el explorador vacío**.

### 1.5 Discrepancias encontradas (histórico completo)

**A. Del repo original (revisión inicial)**
1. Las etiquetas se contradecían:
   - "Muy vertical" (directness, P81) contra "Posesión elaborada / ataque pausado" (ritmo);
   - la tarjeta defensiva decía "Equilibrado" y el mapa "Línea alta, presión selectiva";
   - "Corta con duelos, no presiona" aparecía con PPDA en P94.
   - → Lo atendió A2 con `labels.identity()`. **Falta verificar tras reconstruir.**
2. "Recuperación alta" tenía tres umbrales: simulador x≥60, `high_press_shots` x≥80 y PPDA x≥48. → Ahora son conceptos con nombres distintos en el framework (`rec_campo_rival`, `rec_alta`, `ppda`). **Hay que verificar que la UI use el nombre correcto.**
3. La transición y el ritmo se definían distinto en `extract`, `contextual`, `temporal` y `personnel`. → Se unificó en `framework` (10 s para la transición, 15 s nombrado como contragolpe).
4. `model.json` estaba desactualizado: Jardine tenía n=70. → Corregido: 91 en ventana y 38 en el epílogo.
5. La UI mostraba datos crudos: `toFixed(3)`, "unknown", palabras en inglés (Directness, losing, nombres de posiciones) y códigos de advertencia sin traducir. → Lo atendió `fmt.js`. **Se verifica en G3.**
6. No se usaban 360, OBV, pases progresivos ni field tilt. → Ya están en los módulos de la Ola 2; falta publicarlos.
7. El balón parado solo aparecía como un percentil. → Ahora existe el módulo `setpieces`; falta mostrarlo en la UI.
8. Los heatmaps simulados se presentaban como si fueran reales. → En el laboratorio se rotulan "simulado"; la historia usa mapas reales.
9. "Gana 49%" se leía como pronóstico. → Se rotula "Duelo de estilos en el modelo (no es un pronóstico)".
10. El merge del PR #2 había borrado el PR #1, cuyo trabajo quedó descartado. `DOCUMENTACION.md` todavía citaba el endpoint eliminado. → Pendiente de revisar en T-10.

**B. Lecciones del PR #1 descartado (aplicar en las jugadas peligrosas)**
- Ordenar por gol, luego xG de la posesión, luego OBV. No ordenar por zona.
- Invertir bien las coordenadas entre equipos.
- Filtrar o etiquetar penales y balón parado.
- No exponer datos crudos de eventos.
- Usar el formato "Hecho observado / Interpretación".

**C. Discrepancias de estilo visual (reportadas por el usuario el 2026-10-21)**
1. El portal nuevo tenía un tema claro genérico y el laboratorio conserva la identidad original oscura (azul marino, Barlow Condensed, acentos dorado y azul, cancha verde a rayas). → Lo atendió A8 con `tokens.css` y `components.css`. **Se verifica en G3.**
2. En el laboratorio de jugadas el América salía **azul** y el rival **naranja**, mientras que en el simulador el protagonista es **dorado** y el rival azul. → Quedan fijos: protagonista dorado, rival azul, liga gris. **Se verifica en G3.**
3. El laboratorio de jugadas usaba controles nativos sin estilo y una cancha pálida distinta. → Hay componentes compartidos y un solo `pitch.js`. **Se verifica.**
4. En el explorador ninguna tarjeta mostraba el nombre del equipo o DT; todas decían "Sin métricas publicadas todavía" y "Confianza sin calcular". → El frontend ya está arreglado y **falta publicar `model/explorer.json` v2 (T-04)**.

**D. Coherencia del estilo de juego (detectada en la revisión del 2026-10-21)**
1. América·Jardine tenía la etiqueta "Línea alta, presión selectiva" con volumen de presión en P71 y PPDA en P18. → A2 definió una regla exclusiva. **Hay que verificarla con el modelo reconstruido** (T-05).
2. El control "Pases rivales por acción defensiva (PPDA)" muestra un percentil **invertido**: "P18" parece un PPDA bajo, que sería bueno. → Renombrarlo (T-03.4).
3. `lab.html` conserva los nombres estáticos de cuadrantes (`MAPS.dfn.q.br = 'Línea alta, presión selectiva'`, eje "Espera/Presiona"). → Debe leerlos de `identity.regions` o de `/api/framework` (T-03.5).

**E. Problemas técnicos reportados por la Ola 2 (pendientes, ver T-03)**
- `build_model.map_point` no usa `labels.map_points`, así que los puntos del mapa no coinciden con las etiquetas. Esto causa los 52 errores de coherencia.
- `acceptance.py` y `test_acceptance.py` tienen los nombres de cuadrantes escritos a mano.
- **Presupuesto de tamaño:**
  - el análisis de `pac_almada` llega a ~420 KB, por encima del límite de 400 KB, y `enforce_budget` borraría `replay` (~234 KB). Hay que mover la repetición a un archivo por partido;
  - `/api/explorer/{teams|coaches}` pesa ~1 MB cada uno. Hay que quitar `temporadas` y `tenencias` de las rutas de lista.
- Ninguna ruta sirve `model/xg_grid.json`, que necesita el laboratorio de jugadas.
- `build_analysis` todavía envuelve la repetición en el adaptador `replay_ctx`. Hay que quitarlo y pasar `entity_id`, el equipo y la ventana de cada partido.
- `analytics.build_all` itera sobre el dict del registro; si un tópico registra otro durante la corrida, falla. Hay que iterar sobre `list(...)`.
- Cada tópico vuelve a cargar los eventos v8 (~10 s por 100 partidos). Conviene una caché en el contexto.
- Faltan ids en `DEFINITIONS`: `puntos`, `xg_dif` y los que pidió A4 (salida desde eventos, xG por origen, posesiones con tiro tras recuperación). También hay constantes sueltas que deberían vivir en `framework`: `REPLAY_DRAWS`, `DESERVED_P`, `BALANCE_PTS`, `BIG_CHANCE_XG`, `EPILOGUE_END`, `REF_MIN_MATCHES` y las de A5 (`SHORT_CORNER_YD`, `BOOT_DRAWS`, `REGULAR_STAGES`, `CONSISTENCY_MIN_INSIDE`…; la lista completa está en `requests/A5.md`).
- **Problemas en `sequences.py`** (reportados por A4):
  - `box_entry` cuenta pases fallados;
  - `_is_prog` cuenta la primera acción de un balón parado;
  - se descartan los tiros que ocurren dentro de una posesión rival (<1% del xG);
  - `lossO` incluye pérdidas seguidas de córner.
- **xG de posesión contra `np_xg` de team-stats:** la tolerancia de 0.01 por partido solo se cumple en ~20–25% de los partidos, porque usan versiones distintas de xG (r=0.994, diferencia media 0.057). El criterio debe pasar a r≥0.99 con la diferencia media documentada (decisión del advisor).
- **Muestra neutral 360:** 36 de los 40 partidos tienen frames pero no eventos v8 (P3 solo bajó 360). Hay que bajar sus eventos o retirar la referencia neutral.
- Faltan dos archivos 360: `4038856` (`ame_jardine_epi`) y `4063616` (`ame_almada`).
- La población de referencia de percentiles incluye equipos-temporada 2025/26 (epílogo). Para las conclusiones debe usarse solo la ventana oficial.
- Falta evidencia TDD explícita de `test_fmt.js` y `test_nlplay.py`. `test_a5_real` es una prueba de caracterización.
- `pipeline/build_model.py` tiene 44 errores de ruff (43 venían de antes).
- `model/entities` pesa **29 MB** y está versionado en git (por `personnel`). Es una decisión abierta (sección 7).

---

## 2. Reglas de ingeniería (siempre)
- **Python 3.9:** usar `.venv/bin/python -X utf8`. No se permite `X | Y`, `match` ni `dict | dict`. Node 22.
- **TDD:** escribir el test, verlo en ROJO (guardar la salida en `data/out/tdd/<tarea>.log`), implementar, verlo en VERDE y guardar esa salida también. Las fixtures sintéticas van en `pipeline/fixtures/`.
- **Clean code:**
  - funciones puras para el cálculo; la E/S solo en los bordes;
  - archivos de 400 líneas o menos y funciones de unas 40 o menos;
  - constantes en `framework.py`;
  - type hints y docstrings breves;
  - `.venv/bin/ruff check <archivos tocados>` limpio.
- **Congelados, no editar nunca:** `frontend/engine.js`, `pipeline/extract.py`, `pipeline/validate.js`, `pipeline/referee.js`. En `lab.html` el JavaScript de simulación queda **igual, carácter por carácter**; solo puede cambiar la presentación (CSS, textos, etiquetas).
- **Procesos pesados** con `flock data/out/heavy.lock <cmd>`, y como máximo `Pool(4)`.
- **JSON:** `ensure_ascii=False, allow_nan=False`. Lo ausente es `null` y lleva su motivo.
- **Contrato de métrica:** `{"id", "value", "n", "unit", "ref_pct"?, "ci"?, "source": "eventos|team-stats|360", "window": "oficial|epilogo|temprano", "coverage"?}`. El `id` debe existir en `DEFINITIONS`.
- **Textos de la UI en español (es-MX)** y siempre a través de `frontend/js/fmt.js`. Nada de colores literales en `frontend/views/` (`test_design_system.js` lo prohíbe).
- **Secretos:** nunca imprimir `.env`. OpenRouter: ≤10 llamadas de prueba por sesión.
- **Commits:** mensaje en español, `"<Gate>: <resumen>"`, terminado en `Co-Authored-By: <modelo> <noreply@anthropic.com>`. Nunca hacer push.
- **Reinicio del servidor** (solo el de 8010):
  ```bash
  kill $(ss -ltnp | grep ':8010 ' | grep -o 'pid=[0-9]*' | cut -d= -f2)
  cd /home/pillofon/Documents/personal/proyectos2026/caon && setsid nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010 > data/out/uvicorn.log 2>&1 < /dev/null &
  curl -s 127.0.0.1:8010/api/health
  ```

### Comando de verificación estándar (se usa en todas las puertas de control)
```bash
cd /home/pillofon/Documents/personal/proyectos2026/caon
flock data/out/heavy.lock .venv/bin/python -X utf8 -m unittest discover -s pipeline -p "test_*.py" 2>&1 | tail -5
node --test pipeline/test_*.js 2>&1 | tail -8
git diff main -- frontend/engine.js pipeline/extract.py pipeline/validate.js pipeline/referee.js | wc -l   # debe ser 0
.venv/bin/ruff check $(git diff --name-only HEAD -- '*.py'; git ls-files -o --exclude-standard -- '*.py') 2>&1 | tail -3
.venv/bin/python -X utf8 pipeline/check_model.py 2>&1 | tail -3
node pipeline/validate.js 100 2>&1 | tail -4 && node pipeline/referee.js 2 2>&1 | tail -3
.venv/bin/python -X utf8 pipeline/audit_coherence.py 2>&1 | tail -5
.venv/bin/python -X utf8 pipeline/acceptance.py 2>&1 | tail -5     # → docs/ACEPTACION.md
```

---

## 3. Lo que falta (resumen)
| Etapa | Contenido | Estado |
|---|---|---|
| **G1.5** | Verificar la Ola 2 y hacer su commit | ⏳ |
| **Integración** | Peticiones pendientes, reconstrucción, KPIs, historia, rutas, coherencia | ⏳ (A7b no corrió) |
| **G2** | Puerta de control | ⏳ |
| **Ola 3 (UI)** | Historia de Jardine, pestaña Almada, partidos, ficha de partido, ficha de DT, explorador con datos, método | ⏳ (hoy story, almada, match y coach son stubs de 5 líneas) |
| **G3** | Puerta de control con capturas | ⏳ |
| **Auditorías** | Coherencia, aficionado + diseño, táctico, regresión → correcciones | ⏳ |
| **G4** | Puerta de control | ⏳ |
| **Cierre (G5)** | Reconstrucción final, aceptación, `RESUMEN_NOCHE.md`, servidor | ⏳ |

---

## 4. Plan paso a paso

### ETAPA G1.5 · Asegurar la Ola 2

**T-01 · Verificar que la Ola 2 está en verde**
- [x] Correr el comando de verificación estándar (sección 2). `audit_coherence` puede marcar los ~52 errores esperados; eso no bloquea aquí. *(473 unittest OK, 52 node OK, frozen diff 0, check_model 0 err, validate 0 err, referee 0 infracciones, audit 52 etiquetas esperados.)*
- [x] Si alguna prueba falla, corregirla. Si la corrección toma más de 30 min, mover el módulo a `data/out/quarantine/` y registrarlo. *(Solo 2 I001 de ruff en `replay.py` y `xg_grid.py`, corregidos con `--fix`.)*
- [x] Revisar con `ls data/out/tdd/` que exista evidencia TDD de A2, A3w2, A4, A5, A6 y A8. *(Las 6 existen.)*
- **Aceptación:**
  - unittest y node en verde (0 fallos, 0 errores);
  - diff de los archivos congelados = 0;
  - `ruff` limpio en los archivos nuevos o tocados (la deuda previa de `build_model.py` se permite).

**T-02 · Commit G1.5**
- [x] `git rm pipeline/dangerous.py`.
- [x] `git add` de `pipeline/ app/ frontend/ docs/` (sin `data/`, `.env` ni respaldos `model/*.gz`).
- [x] Commit `G1.5: Ola 2 — 360, ofensiva/defensa/peligrosas, balón parado/contexto/uso, sistema de diseño, explorador v2`.
- [x] Agregar una entrada en `data/out/bitacora.md`. *(hash en la bitácora)*
- **Aceptación:** `git status --short` sin cambios de código pendientes. → **Revisión del advisor (rápida).**

### ETAPA Integración (rol A7b)

**T-03 · Atender las peticiones pendientes del integrador** (una subtarea por punto, cada una con TDD)
- [x] **T-03.1** `pipeline/run.py`: el paso `build` debe ejecutar en orden: *(`run.py`: `extract`=3 scripts, `analysis`=pasos 4–9 con `check_model` y `targets` entre `build_model` y `build_analysis`, `build`=ambos; los módulos `-m` corren desde `pipeline/`. Hasta T-06/T-07 `kpis.py` y `story.py` no existen, así que T-04 corre los pasos sueltos.)*
  1. `extract.py` (incremental)
  2. `extract_analysis.py`
  3. `extract_360.py`
  4. `python -m analytics.shape360_ref`
  5. `python -m analytics.a4_reference`
  6. `build_model.py`
  7. `build_analysis.py`
  8. `kpis.py`
  9. `story.py`

  Agregar el paso `analysis` (de 4 a 9) para no repetir `extract`. Test: el orden de `STEPS` es exactamente ese.
- [x] **T-03.2** `build_model.map_point` debe usar `labels.map_points()`, y `entity.identity` debe regenerarse con `labels.identity()`. Test: para cada entidad, el cuadrante de la tarjeta es igual al del mapa. *(`build_model.map_point` delega en `labels.map_points`; las identidades ya se regeneraban con `labels.identity`.)*
- [x] **T-03.3** `acceptance.py` y `test_acceptance.py` deben usar `labels.QUADRANTS` y `labels.DFN_QUALIFIED`, no nombres escritos a mano. *(`acceptance.py` deriva `_FAST/_SLOW/_PRESS/_WAIT/LINE_HIGH/LINE_LOW` de `labels`; `LABEL_JS` recibe los nombres desde Python.)*
- [x] **T-03.4** Renombrar la etiqueta del control `presion` en `style_labels` (y en `lab.html`, que solo es presentación) a **"Presión por PPDA (alto = deja pocos pases)"**. Revisar con el advisor el texto final. *(texto PROVISIONAL: «Presión por PPDA (alto = deja pocos pases)» en `labels.PPDA_LABEL`; Jardine P18 = su PPDA medio 20.2 es alto, el percentil está invertido. El advisor lo aprueba en T-05.)*
- [x] **T-03.5** `lab.html` (solo presentación): los nombres de cuadrantes y de ejes (`MAPS`) deben leerse de `identity.regions` o de `/api/framework` (`etiquetas.cuadrantes`). El JavaScript de simulación queda igual. *(`/api/framework` ahora trae `etiquetas`; `lab.html` lee `ETIQ` de ahí; el polo «Bloque bajo» del eje X pasó a «Línea baja».)*
- [x] **T-03.6** **Presupuesto de tamaño:** *(`build_analysis.publish_replay/split_replay`; `/api/explorer/{teams|coaches}` sin `temporadas/tenencias/entidades` y con métricas mínimas; nuevo `/api/explorer/catalog`; fichas de partido solo de entidades narrativas, la primera conserva la ficha. Los tests de tamaño con datos reales se corren en T-04: `pipeline/test_budget.py`.)*
  - la repetición se escribe por entidad en `model/replay/<id>.json` y la ficha de cada partido en `model/matches/<match_id>.json`, usando `replay.split_cards()`;
  - `model/analysis/<id>.json` solo guarda el resumen de la repetición;
  - `/api/explorer/{teams|coaches}` deja de devolver `temporadas` y `tenencias`; el detalle (`/api/explorer/team/{key}`, `/api/explorer/coach/{key}`) sí las devuelve.

  Tests de tamaño: análisis ≤400 KB, listas ≤300 KB, partido ≤60 KB.
- [x] **T-03.7** Ruta nueva `GET /api/xg_grid` que sirve `model/xg_grid.json`. Conectarla en `frontend/views/playlab.js` (la fórmula está en `requests/A6.md`). Test con TestClient. *(`/api/xg_grid` + `gridXG` en `playlab.js`, probado contra `xg_grid.xg_at`.)*
- [x] **T-03.8** `build_analysis`: quitar el adaptador `replay_ctx` y pasar `entity_id`, el equipo y la ventana de cada partido. *(`replay.build` ya aceptaba `EntityContext`; se borraron `replay_ctx` y `replay_meta`.)*
- [x] **T-03.9** `analytics/__init__.build_all` debe iterar sobre `list(REGISTRY.items())`. Agregar una caché de eventos v8 por partido en `EntityContext`, con LRU acotada. Test: registrar un tópico durante la corrida no falla. *(LRU de 100 partidos por contexto, vaciada al terminar cada entidad; un partido parseado pesa ~18 MB. Vigilar RAM en T-04.)*
- [x] **T-03.10** `framework_defs`: agregar los ids `puntos`, `xg_dif` y los que pidió A4 (salida desde eventos, xG por origen, posesiones con tiro tras recuperación). Mover a `framework.py` las constantes listadas en la sección 1.5 E y actualizar sus imports. *(5 ids nuevos: `puntos`, `xg_dif`, `salida_portero`, `xg_origen`, `rec_tiro`; 24 constantes movidas a `framework.py`; `REF_MIN_MATCHES` unificado en 10 (A4 usaba 5); `MARCO_ANALITICO.md` regenerado.)*
- [x] **T-03.11** `sequences.py`, con TDD, un test por bug: *((a) y (d) ya estaban corregidos y con prueba desde A2; hechos (b) con `RESTARTS` y (c) por exclusión medida: 1 de 2,241 tiros, xG 0.007 de 216.8 = 0.003 % en Jardine, publicado en `rival_shots` de cada `an_`; `extract_analysis.VERSION` = 5.)*
  - (a) `box_entry` solo con acciones completadas;
  - (b) `_is_prog` excluye la primera acción de un balón parado;
  - (c) los tiros dentro de una posesión rival se cuentan en una posesión propia de "remate tras pérdida rival", o se documenta su exclusión (decide el advisor);
  - (d) separar `lossO` de "pérdida seguida de córner" (`lossXF`).

  Subir `extract_analysis.VERSION` y regenerar `an_` en T-04.
- [x] **T-03.12** Referencia de percentiles para las conclusiones: usar solo equipos-temporada de la ventana oficial (`window == 'oficial'`). Dejar la referencia ampliada solo para el explorador, rotulada. *(`build_model` y `a4_reference` usan solo la ventana oficial; `shape360_ref` ya era por ventana; el explorador conserva la referencia ampliada y la rotula en `metodo.referencia`.)*
- [x] **T-03.13** **Muestra neutral:** bajar los eventos v8 de los 36 partidos de `data/out/neutral_sample.json` que no los tienen (`download_all.py` con un modo `--ids`). Si falla, retirar la referencia neutral y documentarlo. *(los 36 faltantes ya bajaron: `download_all.py --ids @data/out/neutral_sample.json`, 72 archivos, 0 fallas.)*
- [x] **T-03.14** Bajar los 360 faltantes `4038856` y `4063616`. Si no existen en la API, documentarlo en la cobertura. *(`4038856` y `4063616` tienen `match_status_360 = 'unscheduled'`: la API no los tiene; documentado en `data/out/coverage.md`.)*
- **Aceptación de T-03:** cada subtarea con su test en verde y su entrada TDD; `ruff` limpio. ✅ *(517 unittest y 54 node en verde; TDD en `data/out/tdd/T-03.*`.)*

**T-04 · Reconstrucción completa**
- [x] Correr `flock data/out/heavy.lock .venv/bin/python -X utf8 pipeline/run.py build`. Tiempo estimado: varios minutos; vigilar la RAM con `Pool(4)`. *(22 min; RAM ≤ 7.9 GB usados de 13.8; terminó en el error esperado de `kpis.py` inexistente, todo lo anterior publicado.)*
- [x] Revisar: `model/model.json` ≤4 MB; `model/analysis/*.json` ≤400 KB y sin tópicos nulos por presupuesto; existen `model/explorer.json` v2 y `model/xg_grid.json` v2. *(Toluca perdía `dangerous`: ahora `enforce_budget` recorta los Top-N antes de anular; `test_budget.py` en verde.)*
- [x] `check_model` 0 errores; `validate.js 100` 0 errores; `referee.js 2` 0 infracciones; prueba dorada OK.
- [x] Anotar en `docs/VALIDACION_MODELOS.md` la sección "Después (G2)": entidades y su n, simulado contra real por entidad, y la deriva respecto a G1 (por la liga de referencia ampliada; existe el flag `LEAGUE_SCOPE`).
- **Aceptación:** **`audit_coherence.py` con 0 errores** (los 52 desaparecen); el AC-05 de `acceptance.py` en ✅. ✅ *(0 errores en 87 payloads.)*

**T-05 · Verificar la coherencia del estilo de juego en datos reales**
- [x] Imprimir `labels.identity()` de `ame_jardine`, `ame_jardine_epi`, `pac_almada`, `ame_almada` y `atl_cocca` (`python -c`). Para cada uno: construcción, enfoque defensivo, ataque, tags, cuadrantes con y sin balón, y los percentiles de evidencia.
- [x] Revisar a mano que no se contradigan con los percentiles: volumen P71 + PPDA P18 no puede decir "presión selectiva" sin explicación; "Directo pero paciente" debe salir de verticalidad ≥70 y ritmo ≤40.
- **Aceptación:** tabla en `data/out/estilo_check.md`; **el advisor la revisa y aprueba los textos.** ✅ *(aprobada con cambios de texto aplicados: PPDA «Pases que permite al rival (PPDA · alto = permite pocos)», «deja jugar al rival», cuadrante «Línea alta, sin asfixiar». Jardine hoy: PPDA P8, no P18.)*

**T-06 · KPIs** (`pipeline/kpis.py` + `pipeline/test_kpis.py`, TDD)
Los 7 KPIs, con definiciones en `DEFINITIONS`:
1. Dominio territorial: field tilt.
2. Progresión limpia (%).
3. Calidad de ocasión: npxG por tiro y % de tiros desde la zona de remate.
4. Contrapresión efectiva: % de pérdidas en juego recuperadas en ≤5 s.
5. Pérdidas costosas por partido, por tercio y por tipo.
6. Vigilancias 360: media de jugadores visibles detrás del balón y % de pérdidas con ≤2.
7. Diferencial de balón parado: xG a favor − xG en contra, por partido.

- [x] Para cada KPI y cada entidad con datos: valor en la ventana, percentil de referencia (solo oficial), IQR entre partidos, semáforo en los P33/P67 propios y la frase descriptiva "en partidos en verde sumó X pts/partido contra Y en rojo (n)".
- [x] Salida: `model/kpis.json`, o `kpis` dentro de `model/analysis/<id>.json` (decisión del integrador, documentada).
- **Aceptación:** tests con fixture sintética de valores conocidos; los 7 KPIs presentes y sin NaN para `ame_jardine`; mismo `id` y mismo valor que en `model/analysis` (el test de coherencia lo verifica). ✅ *(salida en `model/kpis/<id>.json` por entidad, servida en `/api/kpis/{id}`; el valor se copia de `analysis` y la auditoría `mismo_valor` lo ata. Semáforo solo con ≥12 partidos.)*

**T-07 · Historia** (`pipeline/story.py` + `pipeline/test_story.py`, TDD)
- [x] Generar `model/story/jardine.json` con estos capítulos:
  1. Portada (4 KPIs).
  2. Identidad.
  3. Con balón (salida → progresión → creación).
  4. Sin balón (presión → bloque 360).
  5. Transiciones y pérdidas (tipología 360).
  6. Lo que más dolió (jugadas peligrosas en contra).
  7. Balón parado (ofensivo y defensivo).
  8. Consistencia y contexto (rival, marcador, localía, minuto, liguilla; "¿Jardine o el club?").
  9. Jugadores y cambios.
  10. ¿Mereció ganar? (repetición con xG).
  11. Tablero de KPIs.
  12. Epílogo (fuera de ventana).
- [x] Generar `model/story/almada.json`: identidad en el Pachuca contra la base de Jardine; primeros partidos en el América con valores crudos y encogidos, con intervalos; "qué ya cambió" y "qué vigilar".
- [x] Cada hallazgo es `{id, titulo, hecho, interpretacion, evidencia:[{id, value, n, ci, window}], accion, modo:'aficionado'|'dt'|'ambos', window}`:
  - `titulo` es el hallazgo mismo;
  - `hecho` se llena con una plantilla a partir de los registros de métrica;
  - `interpretacion` es una plantilla condicional que no puede contradecir los números.
- [x] Las conclusiones usan solo `window == 'oficial'`; el epílogo y lo temprano van marcados.
- **Aceptación:**
  - un test por capítulo: al menos 1 hallazgo, con evidencia existente en `analysis/kpis`;
  - test de no contradicción: si la métrica está por debajo de P50, la plantilla no usa "alto/más que la mayoría";
  - test de ventana: ningún hallazgo de los capítulos 1–11 tiene evidencia fuera de la ventana oficial;
  - cobertura del AC-06 (cada componente del reto tiene al menos 1 hallazgo). ✅ *(44 hallazgos en 12 capítulos, 24 componentes cubiertos; módulos `story_text/ch_a–d/almada`; `almada.json` con 2 capítulos y 5 hallazgos.)*

**T-08 · Rutas y contratos de la API**
- [x] `/api/story/{jardine|almada}`, `/api/entities/{id}/analysis`, `/api/entities/{id}/matches`, `/api/matches/{id}`, `/api/replay/{id}`, `/api/kpis/{id}` (si los KPIs van aparte), `/api/xg_grid`, `/api/framework`.
- [x] Errores 404 con mensaje en español.
- [x] Tests con TestClient en `pipeline/test_api.py`.
- **Aceptación:** todas las rutas devuelven 200 con datos reales; los tamaños cumplen T-03.6. ✅ *(`/api/kpis/{id}` y `/api/entities/{id}/matches` nuevas; `test_api.py` prueba todas las rutas con datos reales.)*

**T-09 · Extender `audit_coherence.py` y `acceptance.py`**
- [x] En `audit_coherence.py` (TDD):
  - mismo `id` de métrica → mismo valor en story, analysis, kpis y explorer;
  - todos los payloads llevan bandera de ventana;
  - no hay palabras en inglés ni "unknown" en textos de usuario (lista de tokens prohibidos);
  - no hay conflictos de etiquetas;
  - la tarjeta defensiva es igual al cuadrante del mapa.
- [x] En `acceptance.py`: checks reales para AC-03…AC-15. Los campos que sugirió A3 son `cordura.aprobado`, la cobertura `n_valid`, `cambios.validos` y `errores.tipos/zonas/jugadores`.
- **Aceptación:** `audit_coherence` 0 errores; `docs/ACEPTACION.md` regenerado. ✅ *(la auditoría suma `ventana` y `texto_usuario`; AC-03, 06, 07, 09, 10, 12, 14, 15 son checks reales en `acceptance_checks.py`.)*

**T-10 · Documentación técnica**
- [x] `docs/DOCUMENTACION.md` y `README.md`: estructura nueva, pipeline (`run.py build|analysis`), rutas, sistema de diseño; sin referencias al endpoint eliminado del PR #1.
- [x] `docs/MARCO_ANALITICO.md`: regenerado desde `DEFINITIONS`.

**T-11 · Puerta de control G2**
- [x] Comando de verificación estándar, todo en verde.
- [x] Commit `G2: integración — KPIs, historia, rutas, coherencia`.
- [x] Reiniciar el servidor en 8010 y verificar que `/api/story/jardine`, `/api/explorer/teams` y `/api/entities/ame_jardine/analysis` devuelvan 200.
- [x] Bitácora.
- → **Revisión del advisor (profunda):** coherencia, textos de la historia y las decisiones de T-03.11 y T-05.
  - ✅ *Revisión hecha: aprobada con 9 correcciones aplicadas en el commit G2.1.*

### ETAPA Ola 3 · Interfaz (antes de empezar, cargar el skill `dataviz`)
Reglas de interfaz para toda la etapa:
- usar `tokens.css`, `components.css`, `js/pitch.js` y `js/charts.js`;
- protagonista dorado, rival azul, liga gris, fuera de ventana con tono apagado o trama;
- el protagonista siempre ataca de izquierda a derecha, y el texto al pie lo dice;
- títulos que dicen el hallazgo; cada gráfica con unidad, n y ventana;
- tooltip "¿Cómo se mide?" con el id del framework;
- modo Aficionado: ≤3 números por tarjeta, 1 conclusión, 1 visual y 1 dato curioso por capítulo;
- modo DT: todo, con n, intervalos y cobertura;
- "Hecho observado / Interpretación";
- todo pasa por `fmt.js`;
- móvil a 390 px sin scroll horizontal.

**T-12 · Vista Historia** (`frontend/views/story.js` + helpers `story_*.js`)
- [x] Los 12 capítulos desde `/api/story/jardine` y `/api/entities/ame_jardine/analysis`.
- [x] **Visuales:**
  - mapa de tiros real;
  - rejilla de calor 6×3;
  - gráfica de puntos contra la liga;
  - barras con intervalo;
  - lista de jugadas peligrosas con su dibujo en cancha ("Hecho / Interpretación");
  - zonas de caída y de remate en balón parado;
  - vigilancias y bloque 360, rotulados "jugadores visibles (cota inferior)";
  - tipología de pérdidas;
  - contexto en múltiplos pequeños;
  - resumen de "¿mereció ganar?";
  - tablero de KPIs con semáforo;
  - epílogo con la insignia "Fuera de ventana oficial".
- [x] Tests en `pipeline/test_views.js`: se renderiza con un payload fixture; en modo Aficionado hay ≤3 números por tarjeta; no hay colores literales.
- **Aceptación:** AC-06 visible (los 12 capítulos), AC-08 visible, AC-13 y AC-15. ✅ *(`views/story.js`, `story_visuals.js`, `story_plays.js`; QA en navegador sin errores en ambos modos; AC-08 ✅.)*

**T-13 · Vista Almada** (`frontend/views/almada.js`)
- [x] Huella en el Pachuca contra la base de Jardine; primeros 10 partidos en el América, crudos contra encogidos, con intervalo y confianza; "qué ya cambió / qué vigilar"; insignia de evidencia temprana.
- **Aceptación:** sin conclusiones fuertes sobre datos con n<12 (confianza baja visible). ✅ *(`views/almada.js`: aviso de evidencia temprana, crudo/ajustado/intervalo/valor del Pachuca.)*

**T-14 · Partidos y ficha de partido** (`frontend/views/match.js`)
- [x] `#partidos`: lista filtrable por entidad, temporada y resultado; por defecto Jardine.
- [x] `#partido/<id>`, estilo Google:
  - marcador, momentos clave, xG acumulado por minuto, "¿mereció ganar?" (P de ganar/empatar/perder, xPts contra puntos) y 3 datos curiosos;
  - el modo DT agrega posesión, field tilt, OBV y mapa de tiros.
- **Aceptación:** AC-13 (la ficha incluye "¿mereció ganar?"); cada ficha ≤60 KB. ✅ *(`views/match.js`; pendiente: el mapa de tiros y el OBV del modo DT, porque la ficha aún no trae los tiros: se agrega en una iteración posterior.)*

**T-15 · Ficha de DT** (`frontend/views/coach.js`)
- [x] `#dt/<key>`: 5 rasgos en palabras sencillas (de `labels.identity` y del explorador), línea de tiempo de su carrera por club y KPIs con confianza.
- **Aceptación:** funciona para Jardine, Almada y al menos 3 DTs actuales con muestra chica (confianza visible). ✅ *(`views/coach.js`; QA en navegador sin errores con Jardine, Almada y un DT de 1 partido.)*

**T-16 · Explorador y Método** (`frontend/views/explorer.js`, `method.js`)
- [x] Explorador con los datos v2 reales:
  - pestañas por equipo y por DT;
  - valores encogidos con intervalo al 80%, insignia de confianza, marca de muestra chica e insignia de fuera de ventana;
  - unidades en lenguaje llano (no "proporción 0–1 en team-stats"; la unidad sale del catálogo `metricas`).
- [x] Método: glosario con ids, supuestos, alcance y límites.
- **Aceptación:** AC-12; ninguna tarjeta vacía. ✅ *(Método ahora trae alcance, límites, supuestos, los 7 KPIs y los umbrales en DT; `/api/framework` publica el payload completo; las tarjetas del explorador apilan valor, intervalo 80 % y bruto.)*

**T-17 · Laboratorio**
- [x] Revisar que `#laboratorio` y `lab.html` compartan el sistema de diseño, y que el laboratorio de jugadas use `pitch.js` y los colores fijos (protagonista dorado). *(el QA de navegador de `#laboratorio` y `lab.html` pasa sin errores; la revisión visual fina queda para G3.)*
- [ ] Probar 5 frases de ejemplo en modo reglas y 1 en modo auto con LLM (≤3 llamadas). *(pendiente: se hace en G3 con capturas; el crédito de OpenRouter es de $3.)*
- [x] El panel de interpretación usa `/api/xg_grid`. *(T-03.7)*
- **Aceptación:** AC-10; golden OK.

**T-18 · Puerta de control G3**
- [ ] Comando de verificación estándar.
- [ ] **Capturas** con `/snap/bin/chromium --headless=new`. Solo puede escribir bajo `$HOME`: usar `$HOME/snap/chromium/common/caon/<vista>_<modo>_<ancho>.png`.
  - Rutas: `#historia`, `#almada`, `#partidos`, una `#partido/<id>`, una `#dt/<key>`, `#explorador`, `#laboratorio`, `#metodo`, y `/lab.html`.
  - Anchos 1440 y 390 px; los dos modos solo en `#historia`.
- [ ] Revisar las capturas y corregir: errores de consola, scroll horizontal, inconsistencias visuales.
- [ ] Commit `G3: interfaz — historia, Almada, partidos, DT, explorador`.
- [ ] Reiniciar el servidor.
- → **Revisión del advisor** (con 3–4 capturas clave).

### ETAPA Auditorías (secuenciales, sin workflow; cada una deja `data/out/audits/<R>.md`)

**T-19 · R1 Coherencia** (AC-04, AC-05, AC-15)
- [ ] Correr `audit_coherence` y `acceptance`.
- [ ] Rastrear a mano 25 números visibles de la historia hasta su id del framework y su fuente.
- [ ] Buscar contradicciones entre secciones: etiquetas, cuadrantes, textos, KPIs y explorador.

**T-20 · R2 Aficionado + diseño** (AC-11, AC-13)
- [ ] Con las capturas de G3, responder: ¿alguien que no vio los partidos entiende cómo juega el América de Jardine?
- [ ] Revisar: jerga, más de 2 decimales, inglés, códigos crudos, gráficas sin título, unidad, n o ventana, tablas-muro, y la consistencia visual entre todas las rutas y `lab.html`.

**T-21 · R3 Táctico** (AC-06, AC-14)
- [ ] Verosimilitud futbolística: formación; línea alta contra PPDA contra bloque 360; si las afirmaciones de salida coinciden con los datos.
- [ ] Terminología: salida, vigilancias, basculación, bloque medio, segundo palo.
- [ ] KPIs accionables; marcaje en balón parado con cautela; cambios como asociación y no efecto; simulación como interpretación.

**T-22 · R4 Regresión** (AC-02, AC-10, AC-16, AC-17)
- [ ] Suite completa, golden, `validate.js 100`, `referee.js 3`.
- [ ] Prueba de humo de **todas** las rutas, con tamaños.
- [ ] Verificar que ningún secreto aparezca en respuestas ni logs, que exista la evidencia TDD y que el diff de `engine.js` esté vacío.

**T-23 · Correcciones**
- [ ] Juntar los hallazgos de R1–R4 y corregir en orden bloqueante → mayor → menor (TDD en los cambios de lógica).
- [ ] Hacer como máximo 2 rondas.
- **Aceptación:** 0 hallazgos bloqueantes ni mayores abiertos; los menores se documentan si quedan.

**T-24 · Puerta de control G4**
- [ ] Comando de verificación estándar.
- [ ] Commit `G4: auditorías y correcciones`.
- [ ] Reiniciar el servidor.
- → **Revisión del advisor.**

### ETAPA Cierre (G5)

**T-25 · Reconstrucción final y aceptación**
- [ ] Correr `flock … pipeline/run.py build` y la verificación estándar completa. Debe salir `docs/ACEPTACION.md` con los **17 AC en ✅, o justificados con ⏳ o ❌ y su motivo**.

**T-26 · `docs/RESUMEN_NOCHE.md`** (en español, para el equipo)
- [ ] Qué se hizo; qué falló o quedó pendiente (con evidencia).
- [ ] Cobertura de datos.
- [ ] Tablero de aceptación.
- [ ] Decisiones abiertas, con el default aplicado.
- [ ] **Borrador de 10 hallazgos clave de Jardine:** cada uno con número, n, ventana y advertencia, tomados de `model/story/jardine.json`, sin inventar números.
- [ ] Esqueleto del guion del video (5 min) y de las 10 diapositivas.
- [ ] Cómo correr todo.

**T-27 · Commit G5 y servidor**
- [ ] Commit `G5: cierre`.
- [ ] Reiniciar el servidor en 8010; `/api/health` y `/` devuelven 200.
- [ ] Actualizar `data/out/HANDOFF.md`.
- → **Aprobación final del advisor.**

---

## 5. Criterios de aceptación (los verifica el advisor)
`pipeline/acceptance.py` los calcula y escribe `docs/ACEPTACION.md`. Estado conocido al cierre de la Ola 2: AC-02 ✅ (G1) · AC-03 casi completo (faltan los 360 de T-03.14) · AC-05 ❌ (52 errores, se resuelve en T-04) · el resto ⏳.

| ID | Objetivo | Criterio verificable | Cómo se verifica |
|---|---|---|---|
| AC-01 | Validar modelos | `docs/VALIDACION_MODELOS.md` con "Antes" y "Después": tests, `validate.js` real contra simulado, R² de calibración, árbitro con 0 infracciones, cobertura | Leer el documento; los números coinciden con las salidas |
| AC-02 | La simulación no cambia | `test_golden_engine.js` pasa; `git diff main -- frontend/engine.js` vacío; el JS de simulación de `lab.html` es idéntico al de `index.html` de `main` | `node --test pipeline/test_golden_engine.js`; diff |
| AC-03 | Datos del protagonista | `ame_jardine` n=91 y oficial; `ame_jardine_epi` n=38; 100% de Jardine con `mx_`, `an_` y `f360_`; `pac_almada` ≥90% con eventos | `python -c` sobre `model/model.json` y `data/extract` |
| AC-04 | Framework explícito | `/api/framework` y `docs/MARCO_ANALITICO.md` salen del mismo `DEFINITIONS`; cada métrica publicada tiene un `id` registrado | test + `audit_coherence` |
| AC-05 | Coherencia interna | 0 conflictos de etiquetas; mismo id → mismo valor en todas las secciones; tarjeta defensiva = cuadrante del mapa; un umbral por concepto | `audit_coherence.py` con 0 errores + `estilo_check.md` aprobado |
| AC-06 | Componentes del reto | Al menos 1 hallazgo con evidencia en: construcción, progresión, ocasiones, presión, organización defensiva, transiciones, identidad y consistencia, contexto (rival, marcador, localía, minuto), roles, alineaciones, sustituciones, balón parado ofensivo y defensivo, xG, OBV, progresivos, PPDA, field tilt y métricas propias | test de `story` + revisión R3 |
| AC-07 | Uso de 360 | Vigilancias, contexto del error, bloque, rompe-líneas, forma ante cambios y organización en córner, todas con cobertura; test de cordura de la inversión de coordenadas aprobado | payload `shape360` + test |
| AC-08 | Errores al perder | Tipología (no forzado, bajo presión, decisión arriesgada, duelo perdido, aislado) con tasa de pérdida costosa por tipo, zona y jugador, **visible en la UI** | payload + captura de la Historia, capítulo 5 |
| AC-09 | Jugadas peligrosas en contra | Top 10 por entidad, ordenado por gol → xG de la posesión → OBV; etiquetas de penal y balón parado; tiros concedidos con x media <25 en el marco del protagonista; "Hecho / Interpretación"; ≤250 KB | test de `dangerous` + tamaño |
| AC-10 | Jugadas por texto | Reglas ≥90% de acierto en ≥30 frases; benchmark con ≥3 modelos no-Anthropic; respaldo a reglas probado; la key nunca se expone; 5 frases se animan | `test_nlplay.py` + `docs/NL_BENCHMARK.md` + R4 |
| AC-11 | UI limpia | 0 `toFixed(3)`; DOM sin inglés ni "unknown"; cada gráfica con título-hallazgo, unidad, n y ventana; 0 errores de consola en todas las rutas, 1440/390 px y ambos modos; **un solo sistema de diseño** (sin colores literales en las vistas; protagonista dorado, rival azul) | `grep`, `test_design_system.js`, capturas + R2 |
| AC-12 | Rendimiento por equipo y por DT | Explorador con todos los equipos y DTs: prior, intervalo, confianza y marca de muestra chica; ninguna tarjeta vacía | captura + `/api/explorer/*` |
| AC-13 | Modo Aficionado / DT | El interruptor cambia el detalle en todas las vistas; Aficionado ≤3 números por tarjeta; la ficha de partido tiene "¿mereció ganar?" | `test_views.js` + capturas |
| AC-14 | Simulación interpretativa | Hay repetición con xG de partidos reales (xPts contra puntos); el duelo de estilos dice "no es pronóstico" | payload de repetición + `lab.html` |
| AC-15 | Ventana oficial | Las conclusiones solo usan `window=oficial`; lo demás lleva la insignia "Fuera de ventana" | test sobre `model/story/*.json` |
| AC-16 | Calidad | Suite en verde; `ruff` limpio en los archivos tocados; `check_model` 0 errores; `validate` y `referee` OK; `/api/model` ≤4 MB | comando estándar |
| AC-17 | Entrega | Existe `docs/RESUMEN_NOCHE.md`; servidor en 8010 responde 200; commits G1.5–G5 en la rama | `git log` + `curl` |

---

## 6. Datos y artefactos (referencia rápida)
- **Caché:** `data/cache/` (~3,600 partidos con eventos, lineups, team-stats y 360). **Extractos** en `data/extract/`: `mx_*` (cadena), `an_*` (posesiones v4), `f360_*` (360) y `shape360_ref.json`.
- **Modelo:**
  - `model/model.json` (1.2 MB, lo que usa el simulador + `identity`);
  - `model/entities/<id>.json` (29 MB en total);
  - `model/analysis/<id>.json`;
  - `model/explorer.json`, `model/xg_grid.json`;
  - `model/story/` (por crear).
- **API** (`app/main.py`): `/api/health`, `/api/model`, `/api/teams…` (heredadas), `/api/framework`, `/api/entities`, `/api/entities/{id}/analysis`, `/api/explorer/*`, `/api/replay/{id}`, `/api/matches/{id}`, `/api/story/{name}`, `/api/play/parse`, `/api/play/capabilities`.
- **Frontend:**
  - `index.html`, el portal; rutas `#historia`, `#almada`, `#partidos`, `#partido/<id>`, `#dt/<key>`, `#explorador`, `#equipo/<key>`, `#laboratorio`, `#metodo`;
  - `lab.html`, el simulador original;
  - `css/{tokens,components,pitch,portal}.css`;
  - `js/{api,fmt,pitch,charts,cards,explorer_data,glossary,qa,router,theme}.js`;
  - `views/*.js`. Hoy **story, almada, match y coach son stubs**.

## 7. Decisiones abiertas (el advisor las resuelve; si no lo hace, se aplica el default)
1. **Liga de referencia del simulador:** ampliada (default, si `validate` se sostiene) o el conjunto original (flag `LEAGUE_SCOPE`).
2. **Base del tier del rival:** xGD de la misma temporada (default) o de la anterior.
3. **Umbrales:** saque de banda peligroso con x≥90; exclusión de progresivos con x<48 (defaults).
4. **Semáforos de KPIs:** terciles propios (default) o percentiles de liga.
5. **xG de posesión contra `np_xg`:** cambiar el criterio a r≥0.99 con la diferencia media documentada (default).
6. **Tiros dentro de una posesión rival** (T-03.11c): excluirlos y documentarlo (default).
7. **`model/entities` (29 MB) en git:** mantenerlo (default) o generarlo y agregarlo a `.gitignore`.
8. **Texto de la etiqueta PPDA** (T-03.4).

## 8. Riesgos
| Riesgo | Mitigación |
|---|---|
| Gasto de tokens | Una sola sesión secuencial y lecturas acotadas. El advisor solo revisa en las puertas de control |
| La reconstrucción tarda o se queda sin RAM | `Pool(4)`, `flock` y correr `run.py analysis` sin `extract` |
| Inversión de coordenadas | Una sola función `framework.to_frame` + tests de cordura |
| Deriva de la simulación | La prueba dorada demuestra que el código no cambió; la deriva por datos se reporta en VALIDACION |
| Presupuesto de tamaño | T-03.6 con tests de tamaño |
| Crédito de OpenRouter ($3) | El modo reglas es el default en las pruebas; ≤10 llamadas por sesión |
