# Framework metodológico de CAON

Versión documental: 21 de octubre de 2026 · Rama de trabajo: feat/docHTML · Base: 429c4ec.

Este documento fija el significado de los objetos, métricas y límites de la narrativa de CAON, Vestidor Táctico. «CoachDNA», usado en el encargo, se trata aquí como referencia conceptual a este proyecto; no se identificó un segundo pipeline con ese nombre. Es una reconstrucción del sistema construido y de sus ramas disponibles, no una especificación de funciones futuras ya realizadas. El resumen para presentación es [metodologia_resultados.html](metodologia_resultados.html).

## 1. Estado auditado y regla de evidencia

El checkout está en la webapp inicial. La versión analítica más desarrollada existe en fix/model y la línea de jugadas en feat/game_description/origin/main. Ninguna de esas ramas se integró para producir esta documentación. No se ejecutaron descargas, reconstrucciones del modelo ni correcciones de cálculos. Las referencias origin/* son las guardadas localmente; no se consultó el servidor remoto.

| Rama o referencia | Commit auditado | Contenido |
| --- | --- | --- |
| feat/docHTML / main local | 429c4ec | Checkout documentado; webapp base. |
| origin/main | d6db8e8 | Referencia remota almacenada; merge de jugadas. |
| feat/game_description / origin/feat/game_description | e6f37b6 | Firmas, secuencias peligrosas y parser de texto. |
| fix/model / origin/fix/model | 820e749 | Correcciones, contextos, temporal y personal; sin jugadas. |
| Tag fase-2-estabilidad-temporal | 763d415 | Análisis temporal antes de la corrección prioritaria. |


Los prefijos de procedencia usados en fichas son **B=429c4ec** (base actual), **F=820e749** (fix/model), **P=e6f37b6** (jugadas), **H=ecdf05e** (firmas), **C=f334f92** (contexto inicial), **T=763d415** (temporal). Un archivo indicado como F puede no existir en este checkout. Para leerlo: `git show 820e749:pipeline/contextual.py`; no se ofrece como enlace local inexistente. Los IDs Oxx, Mxx, Axx, Vxx e Ixx enlazan conceptualmente objetos, métricas, supuestos, visualizaciones e incidencias en ambos documentos.

Se inspeccionaron Git status/branch/log --all/diff/show/blame, los archivos versionados de pipeline, research, app, frontend y docs, los modelos de las cuatro refs anteriores, los 561 extractos locales y sus versiones, seis catálogos MX y dos Open Data, inventarios de cachés, los 70 archivos de eventos del caso Jardine (247.271 registros de ambos equipos), sus 70 team-stats y los respaldos locales. No se leyeron secretos de .env. No se afirma haber leído individualmente los 493 archivos de eventos MX completos ni reejecutado el pipeline de otras ramas.

Jerarquía para resolver contradicciones: (1) artefacto identificado por commit/hash y datos locales para el resultado específico; (2) código de esa misma versión para la definición; (3) pruebas y reportes de esa versión para el alcance de verificación; (4) documentación histórica como antecedente, no evidencia suficiente si contradice lo anterior. Cuando datos y fórmula del proveedor no coinciden, se conservan ambos y se declara la diferencia.

### Cuatro niveles de afirmación

| Nivel | Significado | Ejemplo y regla |
| --- | --- | --- |
| Dato suministrado | Registro o estimación recibida de fuente primaria | Evento Shot, location, player_id, lineup, shot.statsbomb_xg o team_match_ppda. El xG ya es una estimación del proveedor; no un hecho físico observado. |
| Métrica derivada | Transformación local con fórmula, población y denominador | PPDA territorial, directness de Pass+Carry, suma de xG. No se llama métrica oficial de StatsBomb. |
| Resumen descriptivo | Agregación de observaciones o métricas | Media de partido, bloque temporal, frecuencia de titulares, top 5 seleccionado. Debe declarar exposición y versión. |
| Interpretación | Lectura condicionada por los datos | «En esta muestra se observa mayor proporción de pases propios al ir perdiendo». No implica intención ni causalidad del entrenador. |

Una escena simulada o desde descripción constituye una **salida generada**, identificada además de los cuatro niveles. No puede usarse como observación del partido real. No se presenta como consolidado ningún elemento sin objeto, fuente y supuesto verificables; se etiqueta experimental o pendiente.

## 2. Pregunta de análisis y alcance de inferencia

¿Cómo describen los datos de eventos y estadísticas suministradas las diferencias entre equipos durante una etapa de entrenador, su variación según marcador y localía, su evolución cronológica y la participación registrada de jugadores? ¿Qué enfrentamientos ilustrativos genera una cadena probabilística a partir de esos conteos?

La unidad de atribución es el **equipo en una ventana con entrenador registrado**, no el entrenador aislado. Rival, calendario, plantel, torneo, expulsiones, cobertura y selección pueden explicar diferencias. No se estima causalidad ni se pretende identificar intención táctica. Una diferencia descriptiva no constituye una prueba de significancia, estabilidad o capacidad predictiva.

## 3. Cómo evolucionó el proyecto

### Fase 1. Investigación ya incluida en la primera entrega

**Evidencia:** 429c4ec · 15 oct 2026.

**Problema:** Explorar diferencias entre entrenadores y comprobar datos 360.

**Archivos:** research/poc.py, dl.py, sliders.py, metric_lab.py, clusters.py y clusters.csv; docs/DOCUMENTACION.md ``7–8.

**Método y cambios:** Proxies por marcador, simulación Bernoulli de tiros (5.000 repeticiones), variantes de ritmo/directness, KMeans y PCA. El primer commit importa estos experimentos juntos: Git no fecha su ejecución individual.

**Resultado y estado:** Experimental. No hay salidas locales data/out ni frames 360 en el inventario actual. El CSV conserva 160 filas de agrupaciones; los índices de silhouette citados por documentación son un reporte histórico, sin log de ejecución conservado.

### Fase 2. Webapp y cadena por zonas

**Evidencia:** 429c4ec · 15 oct 2026.

**Problema:** Explicar enfrentamientos de estilos con datos agregados.

**Archivos:** pipeline/extract.py, build_model.py, entities.py; frontend/engine.js e index.html; app/main.py.

**Método y cambios:** 18 zonas, fases E/T, 14 métricas de estilo, once representativo, mapas con ejes manuales, simulación y árbitro. K=8.

**Resultado y estado:** Activo en main local y feat/docHTML. El primer modelo registra 24 entidades; league.matches=884 son observaciones equipo-partido.

### Fase 3. Firmas de jugadas y ampliación de ventana

**Evidencia:** ecdf05e · 17 oct 2026.

**Problema:** Resumir formas recurrentes de iniciar y terminar ataques.

**Archivos:** pipeline/extract.py::classify_open; build_model.py::signature_plays; frontend/index.html::signaturePlays.

**Método y cambios:** Añade plays_open [conteo,xG,goles], balón parado detallado y etiquetas inicio|carril|definición. Amplía Jardine hasta junio de 2026.

**Resultado y estado:** Solo en la línea de jugadas. Clasificación geométrica y nombres de denominadores presentan problemas; no se consolida como taxonomía táctica.

### Fase 4. Secuencias rivales y descripción de jugadas

**Evidencia:** e6f37b6 · 19 oct 2026; merge d6db8e8 en origin/main.

**Problema:** Mostrar ocasiones peligrosas observadas y dibujar una jugada escrita.

**Archivos:** pipeline/dangerous.py; app/main.py::dangerous_plays; frontend/index.html::drawDangerous, parseNL, nlPositions.

**Método y cambios:** Top 5 de posesiones rivales con tiro; puntuación gol+xG+zona; parser local por expresiones regulares y posiciones configuradas.

**Resultado y estado:** Disponible en origin/main, ausente en main local y fix/model. El modelo de esa rama conserva n=0 y 129 partidos agregados para Jardine. El dibujo desde texto es ilustración, no una jugada recuperada del proveedor.

### Fase 5. Retorno de la línea de trabajo y contexto inicial

**Evidencia:** ddc1571 (checkpoint) y f334f92 · 19 oct 2026.

**Problema:** Recuperar consistencia de conteos, estilo ausente y lectura contextual.

**Archivos:** pipeline/extract.py, build_model.py, check_model.py, test_metrics.py; docs/METRICAS_TACTICAS.md.

**Método y cambios:** El checkpoint ddc1571 elimina dangerous.py y las vistas de jugadas. f334f92 parte de la base 429c4ec, cambia n a att.matches, añade origen del estilo y contexto inicial por marcador/localía.

**Resultado y estado:** Corrección activa en fix/model; contexto inicial reemplazado en 820e749. No se infiere una decisión de producto de un checkpoint ni una integración entre ramas que Git no muestra.

### Fase 6. Bloques cronológicos

**Evidencia:** 763d415 · 20 oct 2026; tag fase-2-estabilidad-temporal; 1924e17 cierre sin diff.

**Problema:** Describir variación del equipo a lo largo de su muestra.

**Archivos:** pipeline/temporal.py, test_temporal.py; API /temporal; frontend::renderTemporal.

**Método y cambios:** Bloques de 8 partidos; cola menor de 5 se fusiona; medias por partido y dispersión entre bloques.

**Resultado y estado:** Activo en fix/model. El nombre del tag no demuestra estabilidad estadística. 820e749 reutiliza el resumen contextual corregido y elimina doble conteo de matches.

### Fase 7. Participación de jugadores

**Evidencia:** 1ee7667 · checkpoint 20 oct 2026; incorporado a 820e749.

**Problema:** Reconstruir titulares, minutos, sustituciones y jugadores simultáneos.

**Archivos:** pipeline/personnel.py, test_personnel.py; docs/PERSONAL_JUGADORES.md; API y vista de jugadores.

**Método y cambios:** Intervalos de posiciones del lineup, eventos de sustitución, combinaciones y métricas dentro de intervalos.

**Resultado y estado:** Activo en fix/model. Conserva un reloj y PPDA propios: no equivale al contexto global. La integración aparece primero en checkpoint, no en un commit autónomo de rama pública.

### Fase 8. Corrección prioritaria y contratos de datos

**Evidencia:** 820e749 · 20 oct 2026.

**Problema:** Distinguir ausencia, corregir contextos y publicar un modelo verificable.

**Archivos:** metric_utils.py, contextual.py, extract.py, build_model.py, targets.py, check_model.py, tests; informes y context_view.js.

**Método y cambios:** IDs procesados, cobertura por métrica, null, calibración protegida, tiempo por periodo, marcador posterior al gol, cuarentena y publicación respaldada/atómica.

**Resultado y estado:** Última versión analítica disponible en fix/model. Modelo schema_version=2, 445 partidos MX distintos y 68 Open Data. No integra dangerous.py.


El grafo no describe una única secuencia lineal de funcionalidades. fix/model y la línea fusionada en origin/main comparten la base 429c4ec y divergen. 1924e17 es un cierre sin cambios de archivos. Los checkpoints 71482eb y def5adc importan árboles de trabajo; 89ffd25 añade DOCUMENTACION_TECNICA_COMPLETA.txt, también conservado en P. Los checkpoints de inicio/fin sin cambios metodológicos propios no se cuentan como fases científicas. No se deduce por el mensaje de un commit que una hipótesis haya sido validada.

## 4. Fuentes de datos y cobertura real

| ID | Fuente | Endpoint o archivo de origen | Contenido/uso | Cobertura constatada | Limitación |
| --- | --- | --- | --- | --- | --- |
| D01 | Partidos Liga MX | v6/competitions/73/seasons/{sid}/matches | Fechas, equipos/IDs, managers, localía, resultado, estado disponible. | 6 catálogos; 1.854 registros, 1.801 available; fechas disponibles 2021-07-23–2026-10-17. | No confundir el calendario programado hasta noviembre con datos ya disponibles. |
| D02 | Eventos Liga MX | v8/events/{match_id} | Acciones, posesiones, localizaciones, timestamps, jugadores, tiros/xG, sustituciones. | 493 archivos en caché; F incorpora 445 partidos distintos (208 con fecha≤2025-06-30). | Disponibilidad del catálogo no implica descarga completa de la liga. Eventos de acceso autenticado. |
| D03 | Lineups Liga MX | v4/lineups/{match_id} | Identidades, dorsales, posiciones e intervalos/razones cuando presentes. | 493 archivos locales; Jardine F 70/70 con lineup. | Sin from/to/ID no se reconstruye participación con certeza; lista incluye suplentes. |
| D04 | Team-stats por partido | v1/matches/{match_id}/team-stats | Métricas suministradas, raw y referencia de estilo/targets. | 1.801 archivos; F referencia 108 equipo-temporadas por métrica; Jardine 70 valores válidos por cada métrica. | Fórmulas internas no especificadas en repo; no equivalencia automática con proxies locales. |
| D05 | Open Data Barcelona | data/matches/11/{21,22}.json; events/{id}.json; lineups/{id}.json en repositorio StatsBomb Open Data | Barcelona La Liga 2009/10 y 2010/11 como comparación de otra liga/época. | 2 catálogos;68 eventos y 68 lineups;68 partidos en B/F. | Solo muestra disponible y descargada, no todos los partidos de dos temporadas; estilo estimado por calibración MX. |
| D06 | 360 | Exploración research/dl.py/poc.py: v2/360-frames/{match_id} | freeze_frame de jugadores visibles; pruebas tipo packing y detrás del balón. | 0 archivos v2_360-frames en caché actual; catálogos anuncian disponibilidad histórica. | Sin cobertura 360 observada local ni integración al modelo. No convertir disponibilidad anunciada en datos realmente usados. |
| D07 | Team-stats por temporada | research/sliders.py/poc.py: v2/competitions/73/seasons/{sid}/team-stats | Referencia y fuerza de rival en experimentos. | 0 respuestas locales con ese prefijo; existe código de consulta. | No se afirma que el experimento pueda reproducirse offline en este checkout. |
| D08 | Player-stats | Sin descarga ni consumidor de endpoint dedicado encontrado | El módulo de jugadores deriva lineups+events. | 0 archivos player-stats locales y ningún módulo dedicado de consulta hallado. | Participación no equivale a un modelo de rendimiento individual. |
| D09 | Modelo/targets derivados | model/model.json; pipeline/targets.json en cada commit | Conteos, estilos, muestras, anclas y salidas analíticas. | B 479.280 bytes; F 19.568.283 bytes; P 874.520 bytes. | Cada artefacto pertenece a una versión; league es selección de entidades, targets toda referencia disponible. |
| D10 | Arquetipo configurado | build_model.py::ATLETI/synth | Multiplicadores manuales y posiciones configuradas. | 1 entidad synthetic; exposición configurada 60. | No datos de un equipo histórico real. |


| Temporada / ID | Registros de catálogo | Available | Fechas de catálogo (incluye programados) |
| --- | --- | --- | --- |
| 2021/22 ·108 | 342 | 342 | 2021-07-23 → 2022-05-30 |
| 2022/23 ·235 | 342 | 342 | 2022-07-02 → 2023-05-29 |
| 2023/24 ·281 | 340 | 340 | 2023-07-01 → 2024-05-27 |
| 2024/25 ·317 | 340 | 340 | 2024-07-05 → 2025-05-26 |
| 2025/26 ·318 | 337 | 337 | 2025-07-12 → 2026-05-25 |
| 2026/27 ·351 | 153 | 100 | 2026-07-17 → 2026-11-23 |


Los cuatro catálogos de la ventana del reto suman 1.364 partidos available. En F, la selección del motor contiene 445 IDs MX únicos entre 2021-07-25 y 2026-10-17; 208 tienen fecha hasta 2025-06-30. league.matches=890 es dos observaciones por partido; B conserva 884, compatible con 442 partidos completos, pero no exporta sus IDs y por eso esa cifra se expresa como implicación del acumulador, no como lista reconstruida. La suma n de entidades no es un número de partidos distintos: las entidades se solapan. Se identifican 642 player_id únicos entre entidades MX de F, incluidos suplentes sin minutos.

Los 561 extractos locales se distribuyen en 445 MX versión 2, 48 MX heredados sin versión y 68 Open Data versión 2. Son archivos locales ignorados por Git, posteriores al modelo B: no prueban que B se haya construido con esos extractos. Ninguno de esos 561 está marcado invalid. Los 48 antiguos no pertenecen a los 445 IDs seleccionados en F. No hay salidas data/out del PoC en el inventario revisado.

Los catálogos anuncian cobertura 360, pero hay cero archivos de frames locales; no se utiliza 360 en B, F ni dangerous de P. La documentación antigua afirma que se exploró, y research contiene la lógica. Ese antecedente no permite medir ahora la cobertura efectiva ni sostener la cifra aproximada de jugadores visibles como resultado auditado.

## 5. Pipeline y contratos de integración

Flujo ejecutado en B: StatsBomb/API y Open Data → caché de respuestas → entities selecciona equipo/DT/fechas → extract genera conteos por partido → build_model suma att propio y dfn rival, construye estilo/anclas/mapa → targets prepara referencias → FastAPI sirve JSON y frontend → motor local simula/coreografía.

F añade orden/validación de reloj y marcador → contextual → extract_version 2 → cobertura de IDs y estilo por métrica → temporal y personnel → modelo schema_version 2 validado → API/vistas de contexto, bloques y jugadores. Personnel vuelve a cargar events+lineups, no deriva sus intervalos de las matrices del simulador. P añade plays_open y dangerous desde eventos rivales y un parser de texto del frontend. Son líneas alternativas, no un único artefacto integrado.

La API B tiene GET /api/health, /api/model, /api/teams y /api/teams/{id}; sirve frontend en /. F añade /context, /temporal, /personnel, /lineups y /substitutions bajo /api/teams/{id}. P añade /dangerous-plays. El servidor temporal Node usado para probar la interfaz en esta sesión no forma parte del producto FastAPI ni de la metodología versionada. Los dos documentos se abren como archivos locales; no requieren endpoints nuevos.

## 6. Fichas de objetos

### O01. Entidad equipo–entrenador–ventana

- **Fuente (D01):** Catálogos de partidos; managers; entities.py::SPECIAL/build_entities.
- **Definición:** ID ASCII de producto, equipo por nombre exacto, entrenador por substring y fechas inclusivas. Actual se determina con el último manager disponible de temporada 351 y tramo retrospectivo continuo. No es una estimación del efecto individual del entrenador.
- **Implementación:** B/F: entities.py, build_model.py::display/ascii_id.
- **Métricas/objetos derivados:** style, raw, att, dfn, map, temporal/personnel (F).
- **Visualizaciones consumidoras:** Plan, selección, mapa, contextos y caso de estudio.
- **Limitaciones:** Nombres y fechas pueden variar por rama. Etiqueta Tricampeonato no define por sí sola los partidos incluidos.

### O02. Partido y observación equipo-partido

- **Fuente (D01/D02/D03/D04):** StatsBomb v6 matches, v8 events, v4 lineups y v1 team-stats.
- **Definición:** match_id, fecha, dos equipos e IDs, home/away, marcador final home_score/away_score, temporada/estado disponible. Un partido genera dos observaciones equipo-partido; la misma observación puede pertenecer a distintas entidades. Cobertura válida requiere ambos equipos en el extracto.
- **Implementación:** B/F: download.py, entities.py, extract.py; F: build_model.py::entity_from_matches.
- **Métricas/objetos derivados:** n, att.matches, dfn.matches; coverage; métricas por partido.
- **Visualizaciones consumidoras:** Chips y todas las agregaciones.
- **Limitaciones:** league es la selección de partidos descargados para entidades, no todos los partidos de la liga; targets y referencia de estilo usan una población mayor.

### O03. Evento

- **Fuente (D02/D05):** Respuesta events de StatsBomb.
- **Definición:** Registro discreto con id/index, period, timestamp, minute/second, type, team, possession/possession_team y campos de acción. location, player, position, end_location y xG son condicionales; no se inventan cuando faltan.
- **Implementación:** B/F: extract.py; F: contextual.py::ordered_events.
- **Métricas/objetos derivados:** Conteos, xG, zonas, geometría y contexto.
- **Visualizaciones consumidoras:** Todos los análisis basados en eventos.
- **Limitaciones:** Una localización es la del evento, no la de todos los jugadores en ese instante.

### O04. Reloj, duración y marcador

- **Fuente (D01/D02/D05):** period, timestamp, índices y goles del proveedor; metadatos.
- **Definición:** F contexto ordena por (period,index,timestamp); periodos 1–4, sin tanda 5. Calcula intervalos entre eventos del mismo periodo con timestamp relativo; gol se cuenta en estado previo y el intervalo siguiente en estado actualizado. Own Goal For y Own Goal Against emparejados no se duplican.
- **Implementación:** F: contextual.py::period_seconds/score_timeline/extract_context. B extracción y F personnel usan minute*60+second+fracción; el simulador fija 95 min.
- **Métricas/objetos derivados:** Segundos por contexto, tasas /90, score_state.
- **Visualizaciones consumidoras:** Contextos y bloques.
- **Limitaciones:** Son segundos de reloj observados con pausas; sin límites Half Start/Half End o reloj inválido, /90=null. Relojes de personnel y cadena no son equivalentes al contextual.

### O05. Posesión StatsBomb

- **Fuente (D02/D05):** possession y possession_team de events.
- **Definición:** Se utiliza el ID del proveedor, no se reconstruye un nuevo dueño con cada acción. Cadena B/F agrupa por possession; contexto F por (period,possession). Acciones elegibles propias: Pass, Carry, Dribble y Shot con location. Posesiones administrativas sin balón se saltan para determinar la siguiente reanudación; el marcador puede cambiar dentro de una posesión.
- **Implementación:** B/F: extract.py::process/_process, first_onball, is_admin; F: contextual.py.
- **Métricas/objetos derivados:** poss de la cadena; possessions e inicios contextuales; matrices y fase.
- **Visualizaciones consumidoras:** Simulación, contextos y temporal.
- **Limitaciones:** poss del motor excluye BP peligroso y posesiones sin acción no penal. Contexto cuenta cada posesión con acción propia en cada estado visitado: los conteos por marcador no son aditivos.

### O06. Acción, secuencia y prefijo de cadena

- **Fuente (D02/D05):** Eventos agrupados por posesión O05.
- **Definición:** Acción con balón es un evento elegible. Para el motor, secuencia es el prefijo de acciones hasta el primer tiro no penal o el fin observado; una transición de zona une orígenes de acciones consecutivas, no necesariamente extremos de un pase completado. La última acción sin siguiente posesión se retira del denominador. No existe una subsecuencia universal de progresión independiente de posesión.
- **Implementación:** B/F: extract.py, bucle acts y break tras Shot. P: dangerous.py.
- **Métricas/objetos derivados:** n[phase][zone], mv/mvC, shot, xg y desenlaces.
- **Visualizaciones consumidoras:** Motor y cancha.
- **Limitaciones:** La secuencia peligrosa de P conserva eventos de la posesión y selecciona su último tiro; puede incluir acciones posteriores a ese tiro y no es el prefijo del motor.

### O07. Zona y orientación

- **Fuente (D02/D05):** location/end_location en cancha StatsBomb 120×80.
- **Definición:** z=floor(clamp(x,0,119.999)/20)*3+floor(clamp(y,0,79.999)/(80/3)). 6 columnas por 3 carriles; ataque de cada equipo hacia x=120. Motor refleja z con (5-col)*3+(2-row) para cambiar equipo.
- **Implementación:** B/F: extract.py::zone; engine.js::mirrorZ.
- **Métricas/objetos derivados:** Matrices, mapas de calor, objetivos y actores.
- **Visualizaciones consumidoras:** Cancha, mapas simulados.
- **Limitaciones:** Unidades de cancha, aproximadamente yardas; no tracking métrico. P dangerousSummary usa cuatro franjas y/20 y mezcla orientaciones de eventos defensivos: no es la misma rejilla.

### O08. Recuperación y pérdida

- **Fuente (D02/D05):** Cambio de possession_team, play_pattern; Ball Recovery, Dispossessed, Miscontrol.
- **Definición:** Cadena: recuperación inferida si posesión previa tiene otro dueño y nueva es Regular Play/From Counter. Contexto: previa elegible del mismo periodo. Recuperación contextual es conteo de Ball Recovery; pérdidas contextuales son Dispossessed+Miscontrol. En cadena lossO/lossXT/lossXG/lossXF se deducen del dueño/patrón de la siguiente posesión no administrativa; keepT/keepF conservan dueño.
- **Implementación:** B/F: extract.py; F: contextual.py.
- **Métricas/objetos derivados:** poss_regain, losses, recoveries, lto*.
- **Visualizaciones consumidoras:** Contextos y simulación.
- **Limitaciones:** Evento de recuperación, recuperación inferida y pérdida de cadena son objetos distintos. Ball Recovery no aplica filtro recovery_failure en el contador. No hay índice universal de pérdida o recuperación exitosa.

### O09. Transición

- **Fuente (D02/D05):** O05/O08 y tiempo.
- **Definición:** Fase T del motor: acciones a ≤10 s desde primer evento de posesión recuperada; después E, sin condición de progresión ni finalización obligatoria. Tiro contextual: cada Shot no penal a 0–10 s en posesión recuperada del mismo periodo. Contragolpe de estilo/temporal: primer tiro no penal, inicio de primera acción x<60 y ≤15 s (tiempo con suelo 0.5 s).
- **Implementación:** B/F: extract.py::T_WINDOW/counter_shots 2; F: contextual.py.
- **Métricas/objetos derivados:** shot[1], transition_shots, counter_shots 2/poss.
- **Visualizaciones consumidoras:** Simulación y contextos/temporal según variante.
- **Limitaciones:** No existe una definición única ejecutada en todos los módulos. Definición documental preferente para nueva narrativa de transición: contexto 10 s, siempre identificada; no se migra el cálculo histórico.

### O10. Presión, contrapresión y PPDA

- **Fuente (D02/D04/D05):** Pressure; counterpress; Pass, Interception, Foul Committed y Duel.Tackle.
- **Definición:** Pressure es evento registrado; contrapresión usa la etiqueta counterpress del proveedor. No se agrupan episodios de presión ni se calcula duración/éxito. PPDA aproximado territorial usa pases rivales x<72 sobre Interception+Foul Committed+Duel.Tackle propios x>=48. No incluye Pressure en su denominador.
- **Implementación:** B/F: extract.py; F: contextual.py::defensive_action, metric_utils.py.
- **Métricas/objetos derivados:** Volumen ajustado, PPDA, presión/pase rival, altura de acciones.
- **Visualizaciones consumidoras:** Plan, mapas, contexto y temporal.
- **Limitaciones:** Presión alta inferida con x>=80 no requiere un Pressure previo. PPDA all zone de personnel utiliza otro conjunto de eventos; no es comparable.

### O11. Tiro, xG y balón parado

- **Fuente (D02/D04/D05):** Shot, shot.statsbomb_xg, shot.type/outcome, play_pattern.
- **Definición:** xG es valor estimado por el proveedor; su suma local es métrica derivada. Global m.np_xg excluye penales; contexto/personnel incluyen todos los tiros. BP peligroso del motor: From Corner o From Free Kick con primera acción x>=80, sin posesión con penal; m.sp_xg incluye córner, falta y banda.
- **Implementación:** B/F: extract.py::is_sp; F: contextual.py/personnel.py.
- **Métricas/objetos derivados:** shot, xg, np_xg, sp_xg, pens y atributos de lanzamientos.
- **Visualizaciones consumidoras:** Plan y motor; contextos/tiros de secuencias.
- **Limitaciones:** No son los mismos denominadores: cadena corta al primer tiro, estilo cuenta xG no penal de todos los eventos, P selecciona último tiro. xG no equivale a gol observado ni a un modelo entrenado por CAON.

### O12. Jugador, posición y participación

- **Fuente (D02/D03/D05):** player_id y lineup[].positions; Starting XI; Substitution.
- **Definición:** Identidad por player_id, nombre solo presentación. F toma segmentos registrados from/to y razones; si falta fin usa máximo minute/second de eventos. Suma duración de segmentos válidos; titular si algún start_reason=Starting XI; aparición si minutos>0. Sustitución requiere IDs de salida/entrada y tiempo.
- **Implementación:** F: personnel.py::_registered_segments/build_match_personnel/_substitutions.
- **Métricas/objetos derivados:** Minutos, apariciones, titularidades, posiciones y sustituciones.
- **Visualizaciones consumidoras:** Vista y endpoints personnel/lineups/substitutions.
- **Limitaciones:** Posición registrada no es rol táctico inferido; frecuencias de posiciones cuentan segmentos, no partidos únicos. Identificados incluye suplentes sin minutos. Segmentos invertidos se omiten con aviso.

### O13. Alineación inicial, composición simultánea y once representativo

- **Fuente (D02/D03/D05):** Lineups y Starting XI; acciones con position.
- **Definición:** Starting lineup F: conjunto de titulares por razones de inicio, ordenado por ID para frecuencia. Composición: jugadores activos en intervalos [inicio,fin) de posiciones, cortados también por tiros/Own Goal For y fusionados si conjunto y estado coinciden. Shape B/F: formación modal, conjunto modal de puestos, titular más frecuente por puesto sin repetir jugador; anclas medias por puesto con/sin posesión.
- **Implementación:** B/F: build_model.py::build_shape; F: personnel.py::_composition_intervals/_pairs.
- **Métricas/objetos derivados:** shape/actors, starting_lineups (top 10), pares (top 20), shared_minutes.
- **Visualizaciones consumidoras:** Cancha representativa y vista de jugadores.
- **Limitaciones:** Shape puede no haber coincidido como once real. Anclas por puesto agrupan jugadores y eventos; no media temporal de posiciones. Composición no garantiza 11 activos ni corrige automáticamente expulsiones por todas las vías.

### O14. Contexto

- **Fuente (D01/D02/D05):** Marcador previo y metadatos de localía.
- **Definición:** Dos particiones independientes: score_state winning/drawing/losing/unknown y venue home/away/unknown. Son marginales, no un cruce marcador×localía. Índices inválidos o goles incompatibles llevan marcador a unknown; localía desconocida se conserva.
- **Implementación:** F: contextual.py y build_model.py::Acc.
- **Métricas/objetos derivados:** Conteos acumulados, razones de sumas, /90, /100 posesiones y diferencias.
- **Visualizaciones consumidoras:** ContextView y contexto por bloque temporal.
- **Limitaciones:** No estima efectos ajustados por rival, torneo o expulsiones. Las muestras de los estados se solapan a nivel de partido.

### O15. Bloque temporal y serie

- **Fuente (D01/D02/D09):** Extractos por partido y metadatos.
- **Definición:** Orden por fecha y match_id, deduplicación por ID. Bloques consecutivos de 8; último con <5 se agrega al anterior; primer bloque corto se conserva insuficiente. Media aritmética de valores válidos de partido; cobertura por métrica. Serie resume medias de bloque, stdev muestral, min/max y diferencias entre valores disponibles.
- **Implementación:** F/T: temporal.py::_period_rows/aggregate_period/build_temporal.
- **Métricas/objetos derivados:** 9 métricas temporales, observaciones y contextos sumados por bloque.
- **Visualizaciones consumidoras:** Tabla temporal (no gráfico de línea en el frontend actual).
- **Limitaciones:** Bloques tienen duración calendario y tamaño variables; no pondera medias de bloque por partidos en series.mean. Omitir null antes de diferencias puede conectar bloques no adyacentes.

### O16. Secuencia peligrosa observada

- **Fuente (D02):** Eventos rivales de una posesión en P.
- **Definición:** Candidata: posesión del rival con al menos Shot rival; elige último tiro. Conserva tipos ACTION_TYPES de ambos equipos, defensa solo Pressure/Duel/Interception/Ball Recovery/Clearance/Block. Score=100*gol+10*xG+clamp(x_tiro-80,0,40); orden descendente (gol,score,xG,fecha,minuto); top 5 por entidad.
- **Implementación:** P: dangerous.py::dangerous_for_match/dangerous_for_entity.
- **Métricas/objetos derivados:** danger_score; progression=x_último_tiro−x_primera_acción rival; duration=max(0,t_tiro−t_primer_evento); contexto defensivo.
- **Visualizaciones consumidoras:** P: Top 5, cancha de eventos y resumen descriptivo.
- **Limitaciones:** No exige entrada al área, avance mínimo ni transición; no hay score por esos componentes. Selección retrospectiva favorece goles; no estima todas las amenazas. Sin datos 360; no está en esta rama ni en F.

### O17. Firma táctica experimental

- **Fuente (D02):** Posesiones no BP peligroso; plays_open en H/P.
- **Definición:** Etiqueta inicio|carril|definición. Inicio regular con x>=60 se llama robo_alto sin exigir recuperación. Carril depende de primera acción x>=80 y rejilla. Definición usa último Pass y comparaciones de columna. Conteo es por posesión, incluyendo posesiones sin tiro.
- **Implementación:** H/P: extract.py::classify_open; frontend::signaturePlays.
- **Métricas/objetos derivados:** Frecuencia, share, lift, xG/posesión; prioridad n*sqrt(lift).
- **Visualizaciones consumidoras:** P: firmas de jugadas y balón parado.
- **Limitaciones:** Etiquetas centro/profundo usan columnas 0 y 2 (x<20 y 40≤x<60), no carriles ni área. xg_per_shot del helper divide por posesiones. Taxonomía excluida de metodología consolidada.

### O18. Modelo, estilo y mapa

- **Fuente (D02/D04/D05/D09/D10):** Extractos, team-stats y referencia de liga.
- **Definición:** Artefacto JSON con meta, league, entities y map.units. Estilo contiene percentiles; raw son medias sin encogimiento, no eventos crudos. F registra schema/extract_version=2, cobertura y fuentes. Unidad de referencia de estilo: equipo-temporada; punto de mapa: equipo-entrenador-temporada.
- **Implementación:** B/F: build_model.py::STY/style_from_means/map_point.
- **Métricas/objetos derivados:** 14 percentiles, mapa 4D y distancias.
- **Visualizaciones consumidoras:** B/F: barras, mapas y vecinos.
- **Limitaciones:** Las fórmulas internas de métricas team-stats son del proveedor y no están especificadas en el repositorio. Una aproximación local con igual nombre no se declara equivalente.

### O19. Partido simulado, coreografía y jugada escrita

- **Fuente (D09/D10 + entrada textual de usuario en P):** Conteos att/dfn/league; shape/actors; descripción libre en P.
- **Definición:** Estado probabilístico: dueño, zona, fase y reloj; ataque y defensa combinados en escala logit, destinos desde atacante. Coreografía transforma log simulado en posiciones interpoladas mediante reglas. Parser P reconoce palabras con regex y usa coordenadas prefijadas.
- **Implementación:** B/F: engine.js::rates/matchup/simulate/choreograph; P: frontend::parseNL/nlPositions.
- **Métricas/objetos derivados:** Promedios Monte Carlo, goles simulados, posesión por tiempo simulado, posesiones largas y mapas.
- **Visualizaciones consumidoras:** Partido animado, resumen, estadísticas, Monte Carlo; jugada de texto solo P.
- **Limitaciones:** Los agregados observados son fuente, los eventos/movimientos generados no son observaciones. Simulador no incorpora política táctica por marcador ni modifica tasas por localía; tiene efectos heurísticos por rojas.


## 7. Catálogo formal de métricas

Notación: P=pases propios, P_rival=pases rivales, A=acciones elegibles, dx=end_x−start_x, dy=end_y−start_y, Δt=diferencia temporal bajo el reloj de cada módulo. Σ y medias se aplican únicamente a la población declarada. Los sufijos /90, /100 y percentil son transformaciones diferentes. La fórmula interna exacta de **team_match_directness, team_match_pace_towards_goal, team_match_defensive_distance, team_match_ppda** y otros campos suministrados **no está publicada en este repositorio**: se documenta su consumo y media, no se inventa una fórmula del proveedor.

| ID | Métrica | Objeto | Fórmula local o transformación | Unidad | Implementación/fuente | Interpretación y limitación | Supuestos A |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M01 | Posesión aproximada por pases | O03/O05 | P/(P+P_rival) | Proporción 0–1 | B/F: my_metrics/event_metrics; F contexto y temporal. | Circulación relativa; no tiempo de control. F denominador 0→null; B usa max(den,1). | 01/05/28 |
| M02 | Participación de acciones | O03/O14 | A/(A+A_rival), A=Pass+Carry+Dribble+Shot | Proporción 0–1 | F: contextual.py::summarize_bucket | No es posesión medida por reloj. | 09/28 |
| M03 | Directness de eventos global | O05/O06/O07 | Σ max(dx,0) / Σ sqrt(dx²+dy²), Pass y Carry en posesiones sin BP peligroso | 0–1 | B/F: extract.py m.dir_fwd/dir_tot; F temporal. | No es directness de team-stats: R²=0,01 en el modelo F. Incluye pases no completados; mide dirección, no valor generado. | 06/11/20/28 |
| M04 | Directness de pases contextual/intervalo | O03/O14/O13 | Σ max(dx,0) / Σ hypot(dx,dy), solo Pass en contexto o intervalo | 0–1 | F: contextual.py, personnel.py::_event_metrics | Contexto incluye BP y penales como población de eventos; personnel omite geometría ausente sin invalidar todo el cociente. No comparar directamente con M03 ni con raw.verticalidad. | 19/29/34 |
| M05 | Frecuencia de pase hacia delante | O03/O07 | N(Pass con end_x>start_x) / N(Pass) | 0–1 | F: contextual.py; experimental poc.py usa dx>10 | No existe clasificación oficial de pase progresivo consolidada. El umbral del experimento es distinto. | 19/29/42 |
| M06 | Ritmo global hacia primer tiro | O05/O11 | Media de max(x_primer_tiro−x_primera_acción,0) / max(Δt,0,5), posesiones con tiro sin BP peligroso | Unidades de cancha/s | B/F: extract.py pace2_sum/pace2_n; temporal.py | Sesgo hacia posesiones con tiro; suelo 0,5 s. No velocidad de cada jugador. | 08/12/18/20 |
| M07 | Ritmo contextual | O05/O14 | Media del avance positivo al primer tiro no penal / Δt, Δt>0; misma categoría de marcador al inicio y tiro | Unidades de cancha/s | F: contextual.py::extract_context/summarize_bucket | Sin suelo 0,5 s. Comprueba categoría al inicio/final, no todos los estados intermedios. No equivale a M06 ni a ritmo suministrado. | 09/20/29 |
| M08 | PPDA territorial aproximado | O03/O07/O10 | N(Pass rival con x<72) / [N(Interception)+N(Foul Committed)+N(Duel.Tackle)] propios con x>=48 | Pases/acción defensiva | B/F: extract.py; F: contextual.py y temporal.py | Denominador sin Pressure. F sin denominador→null; B pseudoconteos solo en conversión de my_metrics. Contexto es razón de sumas; temporal media de razones de partido. | 16/17/28 |
| M09 | PPDA all zone de composición | O13/O10 | N(Pass rival) / N(Pressure+Duel+Interception+Ball Recovery+Foul Committed propios) | Pases/acción seleccionada, sin zona | F: personnel.py::_event_metrics, ppda_all_zone | Incluye Pressure y todos los Duel; excluye filtro territorial. Denominador 0→null. Debe llamarse razón descriptiva de acciones en todo el campo, no PPDA oficial. | 16/34 |
| M10 | Altura de acciones defensivas | O03/O07/O10 | Σ x de Pressure/Duel/Interception/Ball Recovery/Block/Clearance/Foul Committed / N con location | Coordenada x 0–120 | B/F: extract.py def_x/def_n; event_metrics | Representa dónde se registran acciones, no la geometría de una línea de cuatro ni altura de todo el equipo. | 06/28 |
| M11 | Volumen de presión ajustado | O10/O05 | N(Pressure)/(1−posesión) | Conteo ajustado/partido | B/F: build_model.py a partir de team-stats; eventos usan M01 | B eventos protege exposición con max(1−p,0,2); F elimina suelo. No son presiones por posesión rival individual. Sin exposición en F→null. | 18/28 |
| M12 | Presiones por pase rival | O10 | N(Pressure) / N(Pass rival) | Acciones/pase | F: temporal.py::match_metrics | Distinto ajuste de M11; cero eventos es cero solo con muestra. | 28/33 |
| M13 | Contrapresiones | O10 | N(Pressure con counterpress=true) | Conteo/partido o contexto | B/F: extract.py; F contextual.py | Etiqueta primaria del proveedor agregada localmente; no detección propia de episodio ni éxito. | 28 |
| M14 | Contragolpe de estilo | O08/O09/O11 | N(posesiones recuperadas Regular Play/From Counter, primera acción x<60, primer tiro no penal a ≤15 s) | Posesiones con tiro/partido | B/F: extract.py counter_shots2 | No exige avance mínimo; cuenta una por posesión aunque haya rebotes. No es la fase de 10 s. | 13/14 |
| M15 | Transición temporal heredada | O09/O15 | counter_shots2 / poss del motor por partido; luego media de partidos del bloque | Fracción de posesiones | F: temporal.py transition_shots_per_possession | Numerador M14 (15 s); denominador sin BP peligroso. No usar el rótulo genérico tiros de transición de 10 s. | 14/32/33 |
| M16 | Tiros contextuales de transición de 10 s | O09/O14 | N(Shot no penal a 0≤t_tiro−t_inicio_posesión≤10 s tras cambio de dueño del mismo periodo) | Tiros; /90; /100 posesiones | F: contextual.py | Cuenta todos los tiros elegibles. No requiere x<60; distintas reglas de recuperación que la cadena. | 09/13 |
| M17 | Tiros tras recuperación alta de estilo | O08/O07 | N(Shot no penal en posesión recuperada con primera acción x>=80) | Conteo/partido | B/F: extract.py high_press_shots | Sin ventana de tiempo ni Pressure obligatorio. No es éxito de presión alta. R²=0,14; estimación para Barcelona omitida. | 15 |
| M18 | xG y xGA global no penal | O11 | Σ shot.statsbomb_xg propio/rival para Shot.type≠Penalty; media por partido | xG/partido | B/F: extract.py m.np_xg/m.np_xga; team-stats para estilo | Suma de probabilidades del proveedor, no probabilidad de ganar. temporal.xg usa este total, no solo tiros del prefijo. | 07/28 |
| M19 | Tiros/xG del prefijo de cadena | O06/O11 | Σ shot[phase][zone] y Σ xg[phase][zone] hasta primer tiro no penal por posesión no BP peligroso | Conteo y xG acumulados | B/F: extract.py; temporal.shots=Σ shot | No incluye todos los rebotes ni BP; temporal.shots no tiene exactamente la misma población que temporal.xg. | 12/20 |
| M20 | Tiros y xG contextual/intervalo | O11/O14/O13 | N(Shot); Σ shot.statsbomb_xg, incluidos penales | Conteo y xG | F: contextual.py; personnel.py | Contexto anula total/tasas si algún xG falta; personnel suma solo finitos y puede subestimar sin aviso. No comparar con M18 sin separar penales. | 07/29/34 |
| M21 | xG a balón parado de estilo | O11 | Σ xG no penal con From Corner/From Free Kick/From Throw In | xG/partido | B/F: extract.py m.sp_xg y team-stats | Incluye bandas/faltas alejadas; no igual a sp_xg del motor restringido por is_sp. | 20 |
| M22 | Saque largo del portero | O03/O11 | N(Pass de Goalkeeper con length>=32)/N(Pass de Goalkeeper) | 0–1 | B/F: extract.py gk_long/gk_passes | Todos los pases del portero, no solo saque de meta. Calibración de eventos R²=0,11; omitida en Barcelona. | 19/28 |
| M23 | Centros al área | O03/O07 | N(Pass.cross con end_x>=102 y 18<=end_y<=62) | Conteo/partido | B/F: extract.py crosses_box | Geometría local; no da calidad del centro. | 19 |
| M24 | Recuperaciones y pérdidas contextuales | O08 | N(Ball Recovery); N(Dispossessed)+N(Miscontrol) | Conteos, /90 y /100 posesiones | F: contextual.py | No todas las recuperaciones/cambios de posesión; pérdidas excluyen pases fallidos. | 28 |
| M25 | Exposición y tasas | O04/O14 | min=seconds/60; tasa90=conteo*5400/seconds; tasa100=conteo*100/possessions | Minutos; conteo/90; conteo/100 | F: contextual.py::summarize_bucket | Reloj con pausas; clock_incomplete anula /90. xGA/100 usa posesiones propias, no del rival. | 09/29/31 |
| M26 | Diferencias de contexto | O14 | Δ=A−B; relativa=Δ/abs(B), B≠0 | Unidad original y proporción | F: contextual.py::comparisons | Solo winning−drawing, losing−drawing y home−away; sin prueba estadística ni ajuste de confusores. | 30/31 |
| M27 | Media, dispersión y cambio temporal | O15 | bloque=Σ valores válidos/n_válidos; series.mean=media de bloques; stdev=sqrt(Σ(v−media)²/(b−1)); Δ_i=v_i−v_(i−1) | Unidad de cada métrica | F/T: temporal.py | Bloque suficiente por ≥5 partidos aunque cobertura métrica sea menor; no es prueba de estabilidad. Media de razones ≠ razón de sumas. | 32/33 |
| M28 | Minutos, apariciones y titularidades | O12 | minutos=Σ max(fin_segmento−inicio,0)/60; partidos=Σ I(minutos>0); titularidades=Σ I(start_reason=Starting XI) | Minutos y conteos | F: personnel.py | Sin unir intervalos superpuestos; reloj minuto global puede solaparse entre mitades. Los minutos incluyen agregado según datos del proveedor. | 10/35 |
| M29 | Alineaciones y pares | O13 | Frecuencia del conjunto de titulares; minutos compartidos=Σ duración de intervalos con ambos; titularidades conjuntas=Σ I(ambos titulares) | Partidos/minutos | F: personnel.py::_pairs/build_personnel | Frecuencia de conjunto no considera orden/formación. Shared_minutes suma duración ya redondeada a 0,001 min. No identifica sinergia causal. | 10/36 |
| M30 | Sustituciones | O12/O04 | N(Substitution propia con ambos IDs y tiempo verificable) | Conteo; tiempo de reloj | F: personnel.py::_substitutions | Estado previo calculado con reloj propio y gol anterior al momento; acciones simultáneas y autogol sin pareja no tienen el contrato de contextual.py. | 10/35 |
| M31 | Puntuación de peligro | O16 | 100*I(gol)+10*xG+min(max(x_tiro−80,0),40) | Puntos arbitrarios | P: dangerous.py::_score | Todos los goles ordenan primero. Dentro de goles la zona puede dominar al xG; la leyenda gol>xG>zona del frontend no describe el orden real. No es probabilidad. | 38 |
| M32 | Progresión/duración de secuencia peligrosa | O16 | progression=x_último_tiro−x_primera_acción rival; duration=max(0,t_último_tiro−t_primer_evento) | Unidades de cancha y segundos | P: dangerous.py | Avance neto puede ser negativo; no suma avance total. Primer evento puede ser administrativo; timestamp relativo puede fallar al cruzar periodos. | 38 |
| M33 | Firmas experimentales | O17 | share=n_firma/Σ n; lift=share_equipo/share_liga; frecuencia10=10*n/partidos; xG_por_posesión=ΣxG/n | Proporción; razón; conteo/10 partidos; xG | H/P: signature_plays y signaturePlays | Helper histórico llama xg_per_shot a xG/posesión; frontend xg10=10*ΣxG/n. Lift sin base usa share en helper y null en frontend. No consolidado. | 39 |
| M34 | Percentil de estilo | O18/O01 | v_s=(n_m*v+8*μ_liga)/(n_m+8); p=round(100*#(ref<v_s)/#ref); invertido=round(100−p) | Percentil 0–100 | B/F: build_model.py::style_from_means/pct | B n=len(filas), F n_m por métrica. μ_liga pondera partidos; ref pondera equipos-temporada. raw guarda media v sin encogimiento. | 24/26 |
| M35 | Calibración desde eventos | O18/O03 | ŷ=a+b*x por mínimos cuadrados; R²=corr(x,y)²; PPDA ajusta log y retorna exp(ŷ) | Escala suministrada estimada | B/F: build_model.py; F: metric_utils.py::fit_calibration | F exige ≥3 pares, variación, finitud, R²>=0,5 y predicción>=0. Ajuste en muestra; no validación externa. | 27 |
| M36 | Mapa y semejanza | O18 | off=[round((P_ritmo+P_contra)/2),P_posesión]; dfn=[P_altura,round((P_volumen+P_contrapresión)/2)]; d=√Σ(v_j−u_j)² en 4 ejes | Coordenadas percentiles y distancia | B/F: build_model.py::map_point; frontend::similar | No es PCA ni clustering. Top 3 excluye trayectoria propia; igual peso para los cuatro ejes, con correlaciones y redondeo. | 25/49 |
| M37 | Tasa de desenlace y cruce simulado | O19/O06 | p=(c+K*L_n/L_m*p_L)/(n+K*L_n/L_m); logit(p_AD)=logit(p_A)+logit(p_D)−logit(p_L) | Probabilidad condicional | B/F: engine.js::rates/matchup | K=8; límites numéricos y normalización adicionales. Destinos de movimiento parten del atacante; no modelo aprendido de enfrentamientos fuera de muestra. | 26/44 |
| M38 | xG por tiro simulado y Monte Carlo | O19/O11 | xG_AD=clamp(xG_A*xG_D/xG_L,0,005,0,9); métricas=Σ simulación/N; W/N,D/N,L/N | Probabilidad por tiro; medias y proporciones | B/F: engine.js::matchup/simulateMany | Penales y BP tienen límites propios. La simulación incluye penales; referencia np_xg/np_shots los excluye. N=1500 en UI; semilla fija. | 43/45/47 |
| M39 | Posesión y firmas simuladas | O19 | posesión=time_equipo/Σ time; longitud=acciones/posesiones; largas=N(possActs>=10)/posesiones; shareT=shotsT/shots; robo_alto=regainsHigh/regains | Proporciones y acciones/posesión | B/F: engine.js::simulate/simulateMany | Posesión es tiempo simulado, no proxy M01. Robo alto simulado usa col>=3 (x>=60); no M17 (x>=80). | 43/47 |
| M40 | Exploraciones de clustering y tiros Bernoulli | O18/O11 | KMeans sobre StandardScaler; k=argmax silhouette para k∈{3,4,5,6}; PCA(2); en poc: goles=Σ Bernoulli(xG_tiro), xPts=(3W+D)/5000 | Clusters/componentes; puntos esperados experimentales | research/clusters.py y poc.py | Sin validación externa ni integración al mapa. El CSV solo conserva etiquetas; no centroides, coeficientes ni silhouette. No usar como resultados consolidados. | 40/42 |
| M41 | Dominio, momentum y mapas simulados | O19/O07 | fieldTilt=acciones propias en col>=4 / acciones de ambos en col>=4; momentum_min=0,02*(Pass+Carry con destino col>=4)+ΣxG_tiros del minuto; UI promedia minutos m−1,m,m+1; heat_z=conteo_z/Σconteos | Proporción; índice arbitrario; proporción por zona | B/F: engine.js::simulate/choreograph y frontend::drawMomentum/heatHTML | Momentum suma xG y un peso configurado de 0,02 por avance al tercio final. No es presión ni dominio observado; visual usa96 bins y suelo0,15 en escala. | 06/43/47/53/54 |

### Las 14 dimensiones del estilo suministrado

| Clave pública | Campo suministrado/transformación | Dirección del percentil |
| --- | --- | --- |
| posesion | team_match_possession | Directo |
| verticalidad | team_match_directness | Directo |
| ritmo | team_match_pace_towards_goal | Directo |
| linea | team_match_defensive_distance | Directo |
| volumen_presion | team_match_pressures / (1−team_match_possession) | Directo; transformación local del campo |
| presion | team_match_ppda | Invertido: menor razón→mayor percentil |
| contrapresion | team_match_counterpressures | Directo |
| saque_largo | team_match_gk_long_pass_ratio | Directo |
| centros | team_match_crosses_into_box | Directo |
| contragolpe | team_match_counter_attacking_shots | Directo |
| presion_alta_tiros | team_match_high_press_shots | Directo |
| xg | team_match_np_xg | Directo |
| xga | team_match_np_xg_conceded | Invertido |
| bp_xg | team_match_sp_xg | Directo |


### Balón parado, disciplina y probabilidades auxiliares

Conteos derivados: corners, corners_short, corner_shots, corner_xg, corner_headers; fk, fk_direct, fk_direct_xg, fk_cross_shots/xg; pens, pens_scored y pen_place; fouls, yellow, second_yellow, red, bb_yellow/red. Tasas descriptivas de la vista P: córners/partidos; cortos/córners; remates/córners; cabeza/remates; directas/faltas; penales convertidos/pens. Técnica y destino favoritos son argmax de los conteos; cuota = máximo/Σconteos. No se interpreta una cuota sin denominador. Lanzadores se eligen por frecuencia dentro del shape y, si no se encuentra uno, por fallback de A37.

Matriz mv[phase][z][w] cuenta saltos entre orígenes consecutivos; mvC marca cuando la acción precedente era Carry/Dribble. Cada fila se normaliza tras encogimiento para muestrear destino. Matrices lto* registran desde zona de desenlace hacia primera acción posterior observada; su distribución se normaliza por fila o queda null si no hay masa. n es el denominador de desenlaces (incluye las acciones conservadas del prefijo), no número de posesiones. La conservación se establece dentro de estos objetos, no entre todos los contadores con nombres parecidos.

## 8. Supuestos metodológicos

Las razones de esta tabla son justificaciones operativas identificables en el código o su efecto; cuando un valor es heurístico no se presenta como una elección validada empíricamente. El inventario reúne criterios que modifican inclusión, población, fórmula, exposición, modelo o lectura. Coordenadas de decoración y tamaños tipográficos no son umbrales analíticos; las reglas espaciales y velocidades generadas de la coreografía se declaran como configuración, sin convertir cada offset de dibujo en una medición.

| ID | Nombre | Definición/valor | Dónde se implementa | Razón | Impacto | Limitación |
| --- | --- | --- | --- | --- | --- | --- |
| A01 | Competición y temporadas | 73; 108/235/281/317/318/351 | B/F statsbomb.py::SEASONS_ALL | Selección configurada. | Fija universo de catálogos. | No cobertura universal de Liga MX ni actualidad en vivo. |
| A02 | Ventana del reto | 2021/22–2024/25; corte 2025-06-30 | B/F statsbomb.py; build_model.py official | Regla del proyecto, consignada en código. | Marca entidad fuera de ventana si fecha máxima supera corte. | official es booleano por entidad y solo mira máximo; no filtra referencia de percentiles ni league. |
| A03 | Ventanas de entidades | SPECIAL: Jardine 2023-07-01 a 2024-12-31 en B/F; hasta 2026-06-30 en H/P | entities.py::SPECIAL | Selección editorial de etapa. | 70 partidos en B/F vs 129 agregados históricos P. | No son poblaciones intercambiables. Para otros DT, fechas explícitas en tabla anexa. |
| A04 | DT actual | Último manager con partido available en temporada 351; tramo retrospectivo hasta distinto manager | entities.py::build_entities | Regla de selección disponible. | Define entidades Actual según snapshot local. | No confirma cargos reales a la fecha de lectura; sin managers no se añade. |
| A05 | Disponibilidad e inclusión | match_status=available; dos equipos; ID único procesado en F | entities.py; F build_model.py::entity_from_matches | Evitar observaciones parciales o duplicadas. | F n=len(IDs)=att.matches=dfn.matches. | Metadatos disponibles no aseguran eventos descargados. B n proviene de team-stats. |
| A06 | Espacio | 120×80; rejilla 6×3; límites 119,999 y 79,999 | extract.py::zone | Discretización manual. | 18 estados espaciales; conserva índice en borde. | Pierde detalle dentro de celda. |
| A07 | Periodos | 1–4 incluidos; tanda 5 excluida | B/F extract.py; F contextual.py::ordered_events | Analizar partido/prórroga, no tanda. | Afecta goles, tiros y exposición. | P dangerous.py y F personnel.py no filtran explícitamente periodos. |
| A08 | Reloj de cadena | minute*60+second+fracción de timestamp | extract.py::ts | Implementación histórica. | Diferencias temporales de transición/ritmo. | No reloj acumulativo que sume añadido previo; puede retroceder al reiniciar mitad. |
| A09 | Reloj contextual | Timestamp relativo por periodo; fallback offsets 0/2700/5400/6300; solo intervalos dentro del periodo | F contextual.py::period_seconds/extract_context | Evitar descanso y añadido solapado. | No descarta pausas largas; exige Half Start/Half End. | No tiempo efectivo; marcador unknown ante índices ausentes/duplicados o incompatibilidad final. |
| A10 | Final de participación | Máximo minute*60+second+fracción de todos los eventos | F personnel.py::_match_end | Cerrar segmentos to ausente con fin observado. | Duración reconstruida de jugadores. | No filtra tanda; no concatena periodos; huecos/solapamientos de añadido pueden afectar intervalos. |
| A11 | Posesión e interrupción | ID StatsBomb; contexto añade period; ADMIN se salta solo al buscar siguiente posesión | extract.py::is_admin, process; F contextual.py | Reutilizar fuente y evitar desenlaces administrativos. | Reanudaciones del mismo equipo pueden enlazarse como move/keep. | Regain de cadena mira posesión previa directa, contexto previa con acciones y mismo periodo. |
| A12 | Acciones elegibles y cierre | Pass/Carry/Dribble/Shot con location y dueño; sin Shot penal; break al primer tiro | extract.py::acts | Construir cadena discreta. | No todos los eventos forman una acción del motor. | Último tiro o rebotes no necesariamente incluidos; última acción sin sucesor se retira de n. |
| A13 | Transición de fase | ≤10 s desde primer evento de posesión recuperada | extract.py::T_WINDOW; engine.js::T_WINDOW | Ventana heurística. | T→E al vencer reloj. | Sin criterio de avance; cadena no comprueba explícitamente mismo periodo al inferir regain. |
| A14 | Contragolpe | Inicio x<60; primer tiro ≤15 s; Δt con suelo 0,5 s | extract.py::counter_shots 2 | Heurística seleccionada del laboratorio. | Una posesión contada; usa métrica temporal heredada. | Distinto de transición de 10 s y del contador de todos los tiros. |
| A15 | Robo alto | Primera acción x>=80 tras regain, sin límite al tiro | extract.py::high_press_shots | Heurística territorial. | Cuenta todos los tiros elegibles de esa posesión. | No prueba presión; firma experimental y simulador usan x>=60. |
| A16 | PPDA territorial | Pases rival x<72; defensa x>=48; Interception/Foul Committed/Duel.Tackle | extract.py; F contextual.py::defensive_action | Zona complementaria en orientación propia/rival. | Pases por acción defensiva. | Pressure y duelos aéreos quedan fuera. F personnel usa otra definición. |
| A17 | PPDA logarítmico histórico | B: log(max(P_rival,1)/max(D,1)); objetivo log(max(y,0,5)); F: razón válida >0 y log sin pseudoconteos | B build_model.py::my_metrics; F metric_utils.py | Protección original; F conserva ausencia. | Diferencias en observaciones cero/denominador vacío. | No recalcular histórico como si fuera F. |
| A18 | Presión y ritmo | B presión: suelo 0,2 de exposición rival; F sin suelo; ritmo global: suelo 0,5 s | build_model.py; metric_utils.py; extract.py | Protecciones históricas no justificadas externamente. | Cambia magnitudes extremas; velocidad no infinita. | No son constantes físicas ni umbrales validados. |
| A19 | Pase portero/centro | Longitud>=32; cross con end_x>=102 y 18<=end_y<=62 | extract.py | Umbrales manuales de acción. | Fija conteos locales de saque largo y centro. | No definición oficial del proveedor. |
| A20 | BP peligroso | From Corner o From Free Kick cuya primera acción tiene x>=80; posesión con penal excluida | extract.py::is_sp | Separar proceso de BP del motor. | Excluye estas posesiones de directness y cadena abierta. | No excluye todas las reanudaciones; m.sp_xg usa además bandas. |
| A21 | Córner corto y destinos | Corto length<15; reflejar y si origen y>40; x>=114 y y<36/<=44/>44; luego x>=102 y y>50; resto borde | extract.py::corner_target | Clases geométricas configuradas. | Seis categorías y técnica Inswinging/Outswinging/Straight. | Límites discretos; corto depende de longitud, no intención. |
| A22 | Penal y disciplina observada | Lado y<38,5 / 38,5–41,5 / y>41,5; Yellow/Second Yellow/Red y Bad Behaviour separados | extract.py | Codificación de lanzamientos y tarjetas. | Tasas por falta, lado y conversión. | Expulsiones pueden registrarse por vías distintas; personnel disciplinary_events solo Bad Behaviour. |
| A23 | Tiempo medio entre acciones | Solo 0<=Δt<=30 s; tau=ΣΔt/max(N,1) | extract.py; build_model.py::Acc.to | Evitar pausas largas en tau del motor. | Calibra duración de acciones simuladas. | Filtro de 30 s se mantiene aquí; ya se eliminó para exposición contextual F. |
| A24 | Referencia del percentil | ≥10 partidos válidos por métrica y equipo-temporada | B/F build_model.py::ref | Mínimo descriptivo configurado. | F:108 referencias por cada una de 14 métricas. | Incluye temporadas fuera de ventana oficial; sin fundamento de potencia estadística. |
| A25 | Mapa de estilos | ≥8 partidos por equipo-entrenador-temporada; ambos puntos calculables | build_model.py::units | Mínimo manual de presentación. | B/F:159 unidades. | Distinto del mínimo 10 de referencia de percentil. Trayectoria puede usar toda etapa coach-club más allá de ventana SPECIAL. |
| A26 | Encogimiento | K_MATCHES=8; media liga pondera partidos, percentil pondera equipo-temporada | build_model.py; engine.js::rates | Regularización manual hacia liga. | Reduce extremos en muestras pequeñas. | No intervalo de confianza; no valida identidad táctica. Estilo y motor encogen objetos distintos. |
| A27 | Calibración | F: ≥3 pares, variación x/y, finitud, R²>=0,5, predicciones finitas>=0 | F metric_utils.py::fit_calibration; build_model.py::from_events | Contrato técnico y puerta heurística. | Habilita estimación solo cuando pasa; PPDA en log. | R² en muestra; no prueba transporte entre ligas o épocas. |
| A28 | Null y cero | F ratio exige num/den finitos y den>0; contador ausente en m no vacío se trata como cero observado | F metric_utils.py::event_metrics/ratio | Conservar ausencia en razones. | m vacío→{}; contexto sin partidos→conteos null. | Convención de counters heredados no certifica cobertura de cada campo. Temporal/personnel aún tienen defaults propios. |
| A29 | Geometría/xG ausente | Contexto: falta cualquier xG→total y tasas null; pase sin geometría→directness/rate null; falta ubicación PPDA→null | F contextual.py::summarize_bucket | Evitar sumas parciales aparentes completas. | Conserva missing_*; clock_incomplete anula /90. | Personnel no propaga estas mismas ausencias. |
| A30 | Muestra contextual | ≥5 partidos Y ≥5400 s Y ≥30 posesiones por bucket | F contextual.py::summarize_bucket | Regla de suficiencia descriptiva. | Compara solo si ambos contextos la cumplen; aún exporta valor con marca. | No significancia estadística; estados no independientes por partido. C versión previa: solo ≥5 posesiones. |
| A31 | Tasas y diferencias | /90 usa 5400 s; /100 usa posesiones propias; Δ relativa divide abs(B), B=0→null | F contextual.py | Exposición explícita. | Evita comparar solo totales. | No ajuste por expulsión/rival; xGA/100 no usa posesiones del rival. |
| A32 | Bloques temporales | Tamaño 8; mínimo 5; cola<5 se fusiona con previo; posible bloque de hasta 12 | F/T temporal.py::_period_rows | Reducir fragmentos muy pequeños. | 70→8 bloques de 8+1 de 6. | No meses/torneos fijos; si primer bloque es corto se conserva como insuficiente. |
| A33 | Agregación temporal | Media de métricas válidas por partido; 6 decimales; stdev muestral si ≥2 bloques; diferencias tras omitir null | F/T temporal.py | Resumen descriptivo. | Registra valid_matches y missing_matches. | sufficient_sample mira partidos del bloque, no válidos por métrica; series.mean no pondera tamaño. |
| A34 | Muestra de composición | MIN_SAMPLE_MINUTES=15; segmentación [inicio,fin) | F personnel.py | Umbral descriptivo del intervalo. | Marca sufficient_sample por duración. | No exige volumen de eventos ni rival comparable; no valida PPDA. |
| A35 | Participación faltante | Sin from se omite; to ausente→match_end; fin<inicio se omite con aviso; IDs faltantes se excluyen | F personnel.py::_registered_segments/_lineup_intervals | No inventar entradas. | Datos faltantes quedan en warnings. | Minutos=0 también para jugador sin segmentos; no equivale siempre a cero minutos confirmado. |
| A36 | Rankings de jugadores | Top 10 conjuntos iniciales; top 20 pares por minutos compartidos; frontend top 12 jugadores y primeras 8 sustituciones | F personnel.py::build_personnel; frontend::renderPersonnel | Límites de presentación. | Orden jugadores por minutos, titularidades y nombre. | Primeras 8 sustituciones no son top por impacto; truncamiento no cobertura total. |
| A37 | Once y roles | Formación/puestos modales; asignación única por mayor frecuencia; rematadores hasta 4; fallback al más adelantado/central cercano a(70,40) | build_model.py::build_shape/roles_for | Armar una representación animable. | Media con/sin por puesto; actores normalizados por zona. | Requiere ambas medias; portero penalizado 10^6 al reasignar puestos; no once real simultáneo. |
| A38 | Peligro y selección | Top 5; último tiro; score 100 gol+10 xG+clamp(x−80,0,40); xG ausente→0 | P dangerous.py | Priorización editorial. | Favor explícito a goles y localización. | Sesgo de selección/resultado; no umbral mínimo xG ni entrada al área. No consolida tasa de amenaza. |
| A39 | Firmas y patrones | H/P inicio alto x>=60; carril solo si inicio x>=80; último pase con columna 0/2; ranking n*sqrt(lift) | H/P classify_open/signaturePlays | Heurísticas sin validación. | Clasifica incluso posesiones sin tiro. | Columnas 0/2 no son bandas ni área; revisar antes de inferencias tácticas. |
| A40 | KMeans/PCA exploratorios | ≥8 partidos; dropna; StandardScaler; k=3..6; n_init=20 evaluación y 50 final; random_state=0; PCA 2 | research/clusters.py | Búsqueda heurística reproducible en código. | Clusters CSV, componentes impresos. | No modelos serializados ni resultados fuera de muestra; resultados del docs antiguo no se verificaron de nuevo. |
| A41 | Laboratorio de métricas | path>10; net>0; end_x>=80; ventanas contra x<60/15, x<40/20, sin zona/12, x<60/20, x<80/10 | research/metric_lab.py | Comparar alternativas contra team-stats. | Variantes p1…p5,d1…d6,c1…c5. | Condición inicial if ...: pass no filtra; no usar variantes como política consolidada. |
| A42 | PoC de investigación | América ID 1229, disponibilidad 360, periodos<=4; pace exploratorio; pase largo>32; pase adelante dx>10; medias pos con >300 eventos; 5000 Bernoulli; rival top 6 | research/poc.py; sliders.py | Exploración selectiva, no producto. | Contexto y xPts experimentales; sliders ≥10 partidos. | Sesgo de selección 360; salidas no presentes; sliders usa ruta absoluta antigua, dl importa sb inexistente. |
| A43 | Horizonte simulado | T_TOTAL=95*60; HALF=T_TOTAL/2; TURN_TIME=1; SHOT_TIME=1,6; SP_DELIVERY=3; PEN_XG=0,78 | engine.js constantes | Reloj y mecánica configurados. | Tiempo muerto calibrado con liga: mínimo 3s; pesos banda 0,55/meta 1/falta 0,75/BP 1,3/gol 2/penal 2,5/tarjeta 0,6. | No duraciones observadas de cada partido ni añadido reglamentario modelado. |
| A44 | Cruce y límites numéricos | logit con p∈[0,0001;0,999]; suma desenlaces<=0,97; xG abierto∈[0,005;0,9] | engine.js::comb/matchup | Evitar degeneración numérica y dejar movimientos. | Ataque+defensa−liga; destinos mezclados 50/50 al perder. | Son regularizaciones configuradas, no estimadas fuera de muestra. |
| A45 | Límites de balón parado simulado | Corto 0–0,8; remate córner 0,02–0,9; xG córner 0,02–0,5; directa 0–0,9 y xG 0,01–0,3; remate centro FK 0,01–0,9 y xG 0,02–0,5; penal conversión 0,4–0,97 | engine.js::rates/matchup | Estabilizar tasas raras. | pen_sp<=0,1 en rates y<=0,15 cruce; sp_after_shot<=0,6; corner_again=0,24. | Límites manuales; no probabilidades observadas sin transformación. |
| A46 | Disciplina simulada | RED_SHOT=0,2; RED_LOSS=0,15 por diferencia de expulsados; amonestado×0,35 faltas; yellow/foul 0–0,6; red/foul 0–0,1 | engine.js constantes/rates/foul | Respuesta heurística a inferioridad. | En penal pR=min(0,3,4*pR+0,06); pY=min(0,9,1,5*pY). | No ajuste causal estimado; no sustituciones tácticas dinámicas del entrenador. |
| A47 | Muestras y semillas simuladas | UI N=1500 seed 7; validate usa seed 11; árbitro s*7919+13; posesión larga>=10 acciones; robo alto col>=3 | frontend::runQuick; engine.js; validate/referee.js | Reproducibilidad y etiquetas configuradas. | N no es cantidad de partidos reales. | Repetición Monte Carlo no reduce sesgo del modelo. |
| A48 | Coreografía | V_RUN 7,6/V_JOG 4,2/V_GK 5,5/V_CARRY 6,2/V_PASS 21/V_SHOT 34; TEN 10,3; segundo defensor volumen>=62 | engine.js::choreograph | Animación plausible/reglas. | Radio 7+11*vol/100; alcance 40+70*(0,5*linea+0,5*vol)/100; bloque 0,22+0,28*linea/100. | Todos los desplazamientos sin evento e interpolaciones son generados; offsets de colocación y tolerancias gráficas no son métricas empíricas. |
| A49 | Etiquetas del frontend | Reglas sobre percentiles; orden prioritario; mapa centro si \|x−50\|<9 e \|y−50\|<9; vecinos 3 | frontend::fcLabels/tags/quadName/similar | Narrativa editorial del producto. | Reglas completas transcritas en anexo; B ausente→50 en fcLabels, F añade estado insuficiente. | P≥80 no significa eficacia ni certeza; etiquetas como letal exceden lo medido. |
| A50 | Arquetipo sintético | 60 pseudo-partidos; 4-4-2; style manual; multiplicadores ATLETI; forward_bias T=1,7; tope desenlaces 0,95 | build_model.py::ATLETI/synth | Contraste configurado de respuesta del motor. | Repondera conteos de liga por columna/fase; xG y BP multiplicados. | No representa datos del Atlético ni valida tácticas reales. |
| A51 | Persistencia y validación | F schema=2/extract_version=2; allow_nan=False; UTF-8; respaldo gzip; check_model antes de publicar | F build_model.py::publish_model, check_model.py; extract.py::process | Consistencia técnica. | Cuarentena de extractos inválidos; calibración sin pares no se inventa. | Un JSON válido no garantiza validez táctica; las pruebas no cubren todas las definiciones. |
| A52 | Disponibilidad local vs remota | Refs existentes al 21 oct 2026; sin fetch, descarga ni reconstrucción | Auditoría Git y filesystem | Preservar estado solicitado y datos. | Distingue main local 429c4ec de origin/main d6db8e8. | No afirma que las refs remotas guardadas sean la última versión del servidor GitHub. |

| A53 | Selección de highlights simulados | Inicio [0,6]s; gol o xG>=0,08 o penal; máximo22s previos; previo penal5s/BP3s; posterior gol9s/otro3,5s; roja de−2 a+5s | engine.js::choreograph highlights | Selección editorial de momentos generados. | Recuperación retrocede3s, reanudación2s; ventanas solapadas se fusionan. | No selección de partidos reales ni todas las posesiones con tiro. |
| A54 | Dominio y resúmenes de simulación | Momentum peso0,02 por pase/conducción al tercio final;96 bins; media de 3 minutos; escala mínimo0,15; marcador agrupa goles>=5 como 5; top 6 scores; lectura parejo si \|ΔxG\|<0,15 | engine.js::choreograph/simulateMany; frontend::drawMomentum/runQuick | Reglas gráficas/editoriales configuradas. | Afecta dominio dibujado, selección de marcadores y frase automática. | No umbral de significancia ni marcador exacto para valores>=5. |

### Ventanas SPECIAL y referencia de etapa

| ID | Equipo / entrenador | Desde | Hasta en B/F |
| --- | --- | --- | --- |
| ame_jardine | América / Jardine | 2023-07-01 | 2024-12-31 |
| ame_almada | América / Almada | 2026-07-01 | 2099-01-01 |
| gdl_paunovic | Guadalajara / Paunovic | 2023-01-01 | 2023-12-31 |
| gdl_gago | Guadalajara / Gago | 2024-01-01 | 2024-12-31 |
| gdl_milito | Guadalajara / Milito | 2025-07-01 | 2099-01-01 |
| atl_cocca | Atlas / Cocca | 2021-07-01 | 2022-06-30 |


P amplía únicamente la ventana especial de Jardine hasta 2026-06-30 en este historial. d0/d1 publicados son mínimo/máximo observado de selección, no necesariamente límites configurados. Las entidades Actual detectadas se extienden hasta 2099 como centinela, no pronóstico de permanencia.

### Reglas editoriales FC completas de B

Construcción en orden: posesión≥80→Pase corto; si posesión≥65 y ritmo≤55→Pase corto; si (contra≥65 o ritmo≥65) y posesión≤50→Contragolpe; si saque_largo≥70 y posesión≤45→Juego directo; resto Equilibrado. Defensa en orden: línea≥70 y volumen≥65→Agresivo; línea≥60→Alto (situacional si volumen≤40); línea≤35→Profundo; volumen≥75→Presión intensa; PPDA invertido≥75→Bloque medio, va al duelo; resto Equilibrado. Ataque: centros≥67→Por bandas, ≤33→Por dentro, resto Mixto; sin centros en B→Mixto.

Tags en orden: volumen≥75 y (PPDA invertido ausente o≥60)→Presión asfixiante; si PPDA invertido≥80 y volumen≤40→Corta con duelos; si volumen≤25 y línea≤30→Espera al rival. Además extremos≥80/≤20 para posesión, línea, verticalidad, ritmo, centros y xGA invertido; solo≥80 para contragolpe, robo alto y BP; saque largo≥85/≤15. Se ordenan por distancia a 50 y se muestran 4. Son reglas editoriales. «Letal», «asfixiante» o «no presiona» no se toman como conclusiones científicas. La ausencia que B reemplaza por 50 no es una observación de equilibrio. F hereda reglas, con manejo de ausencia mejorado.

### Arquetipo completo como configuración

| Componente | Parámetros |
| --- | --- |
| Ataque E | lossO por columna=[1.9,1.9,1.6,1.45,1.35,1.25]; tiro=[1,1,1,0.5,0.5,0.55]; forward_bias=1; xg=1; lossX=1.3 |
| Ataque T | lossO=[1.1,1.1,1,0.95,0.95,0.95]; tiro=1 en todas; forward_bias=1.7; xg=1; lossX=1 |
| Defensa E | lossO=[0.55,0.6,0.9,1.15,1.45,1.45]; tiro=[1,1,1,0.8,0.65,0.65]; xg=0.75; lossX=1; forward_bias=1 |
| Defensa T | lossO=[1,1,1.1,1.3,1.45,1.45]; tiro=[1,1,1,0.7,0.6,0.6]; xg=0.75; lossX=1; forward_bias=1 |
| BP | Ataque shots=1,xg=1.1; defensa shots=0.72,xg=0.85 |
| Percentiles manuales | posesión 6, verticalidad 95, ritmo 93, línea 8, volumen 22, PPDA invertido 35, contra-presión 15, saque 88, centros 55, contra 97, robo alto 20, xG 70, xGA invertido 97, BP 92 |
| Actores | Pesos exp(−distancia/11); penalización portero 0.15 fuera de primera columna; normalización por zona. Shape 4-4-2 con 11 coordenadas configuradas en ATLETI. |


## 9. Decisiones de estandarización

Estas son decisiones **documentales**. La definición preferente orienta nuevas narrativas y propuestas; no significa que todas las implementaciones ya la cumplan. Las variantes históricas se conservan con nombre y origen propios.

| Concepto | Definición antigua/variante | Definición documental actual | Motivo | Archivo histórico y vigente |
| --- | --- | --- | --- | --- |
| PPDA | B leyenda acciones por pase; C contexto todos los Duel; personnel todo el campo. | Pases por acción defensiva territorial aproximada (M08) para análisis local; team-stats sigue identificado como suministrado; M09 separado. | Evitar inversión y mezcla de población. | 429c4ec:frontend/index.html; f334f92:extract.py; 820e749:contextual.py/personnel.py. |
| Transición | C: posesión From Counter con tiro; legado estilo 15s+x<60; fase 10s. | M16, tiros contextuales 10s, como definición narrativa de nuevas comparaciones; fase T y contragolpe 15s nombrados por separado. | Cuentan unidades y ventanas diferentes; no migrar cifras. | f334f92:extract.py; 820e749:contextual.py/temporal.py; B/F:engine.js. |
| Directness/verticalidad | Un mismo rótulo para team-stats, Pass+Carry y soloPass. | M03 directness de eventos; M04 directness de pases; raw.verticalidad suministrada con fórmula interna no disponible. | Calibración R²0,01 no sostiene equivalencia. | B/F:build_model.py; F:contextual.py/personnel.py. |
| Ritmo | Global suelo 0,5s; contextual exige Δt>0. | Especificar global hasta primer tiro vs contextual, sin unificar numéricamente. | Distinta población y tratamiento de tiempo. | B/F:extract.py; F:contextual.py. |
| Reloj y marcador | C descartaba pausas>30s y atribuía intervalo postgol al estado previo; personnel conserva reloj global. | Contrato de contexto F por periodo y marcador posterior al gol para exposición; reloj personnel se mantiene como variante pendiente. | Tiempo observado, sin descanso entre mitades ni tiempo efectivo supuesto. | f334f92:extract.py; 820e749:contextual.py/personnel.py. |
| Posesión y secuencia | ID único de proveedor; prefijo al primer tiro; P selecciona último tiro; contexto cuenta estados visitados. | Definir O05/O06/O16 por separado; no llamar secuencia peligrosa a toda posesión. | Evitar equivalencia falsa y suma de posesiones por estado. | B/F:extract.py; F:contextual.py; P:dangerous.py. |
| Ausencia | B pseudodenominadores y estilo 50; F null y causa, con excepciones en temporal/personal. | Ausencia=sin dato; cero=observación de ausencia de evento, cuando cobertura lo permite. | Evitar promedios o etiquetas fabricados. | 429c4ec:build_model.py/frontend; 820e749:metric_utils.py/contextual.py. |
| n y cobertura | B/P n=len(team-stats), motor usa extractos; P Jardine 0/129. | Contrato F n=IDs únicos=att.matches=dfn.matches; muestra de estilo independiente por métrica. | Evidencia de población, sin reasignar 129 partidos al caso 70. | e6f37b6:model/model.json; f334f92/820e749:build_model.py. |
| Peligro y firmas | UI gol>xG>zona; clasificación de columnas como patrones. | Puntaje ponderado exacto M31; firmas O17 exclusivamente experimentales. | No presentar taxonomía o amenaza validada. | ecdf05e:classify_open; e6f37b6:dangerous.py/frontend. |
| xG y tiros | Estilo team-stats, temporal eventos y tiros de prefijo; simulación total vs targets no penal. | Etiquetar suministrado/no penal, eventos/no penal, prefijo y total simulado, respectivamente. | Diferencias demostradas aun en los mismos 70 IDs; evitar restas incompatibles. | 820e749:model/validate.js; cache local Jardine 70. |


## 10. Auditoría de coherencia y pendientes de código

No existe coherencia numérica completa entre todos los módulos por los motivos siguientes. Se limita el alcance de cada resultado en vez de cambiar cálculos para acomodar la narrativa. Las propuestas son trabajo posterior.

### CRÍTICOS · I01 · Conteo y ventana incompatibles en origin/main/P

**Dónde/evidencia:** P model ame_jardine: n=0, att.matches=dfn.matches=129, style={}; d1=2026-05-11. B/F:70/70 y d1=2024-12-16.

**Impacto:** El problema exacto sí es reproducible leyendo e6f37b6:model/model.json; el informe F decía que no se reprodujo en su línea de trabajo. No se atribuye sin prueba una causa de codificación concreta.

**Corrección propuesta, no ejecutada:** Separar ventana/número de filas de team-stats y partidos realmente procesados; portar coverage/contratos F a la rama que se integre, conservando IDs y pruebas.

### CRÍTICOS · I02 · Mezcla de orientaciones en cancha peligrosa

**Dónde/evidencia:** P frontend::drawDangerous dibuja sin reflejar acciones analizado/rival. Cada equipo usa orientación propia.

**Impacto:** Puntos defensivos no son una configuración espacial coherente frente al ataque rival. Puede aparentar una relación espacial que no existe.

**Corrección propuesta, no ejecutada:** Normalizar toda coordenada al marco del rival antes de dibujar y probar con posesión mixta. Mantener historial observado, sin interpolar 22 jugadores.

### IMPORTANTES · I03 · Tres objetos llamados transición

**Dónde/evidencia:** B/F cadena 10s, estilo/temporal 15s+x<60, contexto F 10s cuenta cada tiro; C contexto From Counter contaba posesiones.

**Impacto:** Métricas con nombre parecido no son equivalentes; recuperaciones y punto de inicio también difieren.

**Corrección propuesta, no ejecutada:** Adoptar narrativa de tiro contextual 10s para nuevas comparaciones; renombrar legado y migrar cálculos solo con acuerdo y prueba de sensibilidad.

### IMPORTANTES · I04 · Tres PPDA y agregaciones diferentes

**Dónde/evidencia:** B/F: team-stats suministrado; territorial local; F personnel ppda_all_zone. C contexto incluía cualquier Duel; F lo restringe a Tackle.

**Impacto:** No se comparan magnitudes ni percentiles directamente. La media temporal de PPDA por partido difiere de razón contextual de sumas.

**Corrección propuesta, no ejecutada:** Nombre oficial documental PPDA territorial aproximado; conservar etiqueta all_zone explícita y plantear uso de función compartida si se busca equivalencia.

### IMPORTANTES · I05 · Directness y ritmo comparten rótulos

**Dónde/evidencia:** Estilo raw.verticalidad viene de team-stats; global local Pass+Carry sin BP; contexto/personnel solo Pass. Ritmo global suelo 0,5 vs contextual Δt>0.

**Impacto:** R² de directness 0,01 rechaza equivalencia desde eventos; los rótulos pueden inducir inferencia falsa.

**Corrección propuesta, no ejecutada:** Indicar fuente, población y unidad en cada vista; diferenciar directness_eventos, directness_pases y directness_proveedor sin cambiar código en esta tarea.

### IMPORTANTES · I06 · Reloj/estado de personnel no reutiliza contextual

**Dónde/evidencia:** F personnel usa max(minute*60+second), no filtra period 5; _states_at procesa goles con t<momento, y al cortar en t_gol conserva estado previo para intervalo siguiente hasta otra frontera. No usa Own Goal Against sin pareja.

**Impacto:** Tiempo añadido, eventos simultáneos o autogoles pueden producir exposición/estado distinto a contexto. Es un riesgo verificable en lógica, sin cuantificar aquí cuántos resultados reales afecta.

**Corrección propuesta, no ejecutada:** Unificar reloj acumulado por periodos y estado posterior al gol; comprobar intervalos/titulares contra metadatos y añadido con fixtures específicos.

### IMPORTANTES · I07 · Firmas experimentales con geometría/nombre incorrectos

**Dónde/evidencia:** H/P classify_open compara columna 0 y 2 para centro/profundo, sin área; llama robo_alto a Regular Play x>=60 sin regain. xg_per_shot divide por posesiones.

**Impacto:** Etiquetas no respaldan intención, banda o profundidad.

**Corrección propuesta, no ejecutada:** Revisar taxonomía y denominadores; publicar únicamente como clasificador experimental hasta corregir y validar.

### IMPORTANTES · I08 · Ranking peligro: leyenda y población

**Dónde/evidencia:** P UI dice gol>xG>zona; score mezcla 10*xG+zona. Top 5 incluye fechas 2025/2026 para entidad etiquetada Tricampeonato.

**Impacto:** Orden dentro de goles puede estar dominado por zona; no representa todas las amenazas ni ventana 70 de F.

**Corrección propuesta, no ejecutada:** Mostrar fórmula ponderada exacta; decidir ventana explícita; mantener ejemplos históricos fuera del caso 70.

### IMPORTANTES · I09 · Tiros y xG no siempre comparten población

**Dónde/evidencia:** Temporal.shots usa prefijo no BP; temporal.xg incluye todos los tiros no penales; contexto/personnel/simulador incluyen penales; targets np_* no.

**Impacto:** Tiros/xG comparados como si fueran equivalentes generan ratios o validaciones inválidas.

**Corrección propuesta, no ejecutada:** Etiquetar poblaciones; conservar la corrección F que evita restar simulación total−referencia no penal; ampliar salidas por tipo si se necesita comparabilidad.

### IMPORTANTES · I10 · Ausencia no uniforme

**Dónde/evidencia:** B fcLabels ausente→50; B razones con max; F contexto propaga xG faltante, personnel omite sin aviso y temporal usa varios defaults 0.

**Impacto:** Un cero o etiqueta equilibrada puede esconder falta de observación.

**Corrección propuesta, no ejecutada:** Usar null+causa+exposición consistentemente; no aplicar retrospectivamente F a B ni sobrestimar cobertura de personal.

### IMPORTANTES · I11 · Referencia liga, modelo y ventana distintas

**Dónde/evidencia:** F style referencia 108 equipo-temporadas y targets 1801 partidos; league deriva 445 seleccionados; official no filtra esos universos.

**Impacto:** Percentiles y simulación no son estrictamente análisis de la ventana oficial del reto.

**Corrección propuesta, no ejecutada:** Explicitar poblaciones; definir una construcción oficial restringida si el jurado la requiere y comparar sensibilidad.

### MENORES · I12 · Carriles y texto estático desactualizados

**Dónde/evidencia:** P dangerSummary divide y/20 en 4 franjas; cadena 6×3. F frontend conserva texto 884 actuaciones aunque league.matches=890. B etiqueta PPDA invierte palabras (acciones por pase).

**Impacto:** Lectura documental confusa y cifras obsoletas.

**Corrección propuesta, no ejecutada:** Unificar nombre de zona, derivar cobertura de meta y decir pases por acción defensiva.

### MENORES · I13 · Portabilidad de research y reproducción

**Dónde/evidencia:** research/dl.py importa sb inexistente; sliders.py escribe a ruta absoluta antigua; metric_lab if ...:pass no filtra.

**Impacto:** Experimentos no ejecutables directamente como pipeline consolidado.

**Corrección propuesta, no ejecutada:** Reparar rutas/filtros y guardar salidas/versiones si se retoman; no incorporarlos al resultado principal.

### MENORES · I14 · Cobertura de bloque y series

**Dónde/evidencia:** F temporal.sufficient_sample usa total del bloque, no válidos por métrica; diferencias eliminan null antes de restar.

**Impacto:** Una serie puede conectar bloques separados o anunciar suficiencia con pocos valores de una métrica.

**Corrección propuesta, no ejecutada:** Añadir suficiencia por métrica e índices de bloque a diferencias.

### MENORES · I15 · Advertencias de jugadores y reproducibilidad

**Dónde/evidencia:** Jardine F contiene aviso de segmento invertido para Igor Lichnovsky; identificados 55 incluye suplentes sin minutos.

**Impacto:** No todos los intervalos están libres de advertencias; no llamarlos 55 participantes efectivos.

**Corrección propuesta, no ejecutada:** Conservar aviso en UI/documentos y distinguir identificados de jugadores con minutos.

### IMPORTANTES · I16 · xG de team-stats y eventos no idéntico aun con mismos 70 IDs

**Dónde/evidencia:** Cache local de Jardine: team-stats Σnp_xg=103.451162; eventos Shot no penal ΣxG=107.352638; temporal sigue eventos.

**Impacto:** La media raw.xg=1,478 suministrada y media de eventos≈1,5336 no son la misma serie. No se atribuye la diferencia a una causa del proveedor sin evidencia adicional.

**Corrección propuesta, no ejecutada:** Conciliar partido por partido los campos del proveedor y documentar versión/filtros. Mientras tanto presentar ambos resultados con procedencia, sin intercambiarlos.


### MENORES · I17 · Marcadores frecuentes agrupan goleadas sin distinguirlas

**Dónde/evidencia:** B/F engine.simulateMany guarda Math.min(goles,5) para cada equipo y frontend muestra clave como marcador.

**Impacto:** Un5–0 puede reunir5–0,6–0 y más. No es una distribución exacta de marcadores.

**Corrección propuesta, no ejecutada:** Mostrar categoría5+ o conservar marcadores enteros antes de calcular frecuencias.

## 11. Visualizaciones y matriz de trazabilidad

Cada entrada relaciona pregunta, objetos, métricas, supuestos y transformación. B/F/P indican dónde está implementada; V17 es una visualización nueva de este documento, no una capacidad de la aplicación.

| ID | Nombre | Estado / consumidor | Pregunta | Entrada, métrica y supuestos | Transformación/visual | Lectura válida | Lectura inválida |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V01 | Selección y cobertura | B/F · chips | ¿Qué equipo-etapa y muestra se comparan? | O01/O02; n,d0,d1,formation,official; A01–05 | Texto/chips de metadatos; aviso de muestra pequeña n<8. | Identificar población de cada selección. | Leer Actual como confirmación externa de cargo o n como número universal de eventos. |
| V02 | Plan y etiquetas FC | B/F · renderPlan/fcLabels/tags | ¿Dónde se sitúa cada media respecto a la referencia? | O18; M34/M35; A24–28/A49 | 14 barras percentiles y etiquetas por reglas; s/d si falta métrica. | Comparación descriptiva de medias encogidas. | P93 significa 93% de eficacia, o etiqueta prueba intención del DT. |
| V03 | Vista táctica con/sin balón | B/F · drawTactical | ¿Cómo se distribuyen anclas de eventos por puesto? | O13; shape y actors; A37 | Cancha y dorsales; medias por puesto separadas por dueño de posesión. | Representación de ubicación de acciones registradas. | Posiciones simultáneas reales de los 22 jugadores o bloque sin balón medido. |
| V04 | Mapa con balón | B/F · renderMap(off) | ¿Qué perfiles se aproximan en ritmo/posesión? | O18; M36; A24–26 | SVG de ejes manuales: promedio P_ritmo/P_contra vs P_posesión; cuadrantes. | Semejanza en esas dimensiones. | Mapa PCA, clustering o cercanía táctica completa. |
| V05 | Mapa sin balón, trayectoria y vecinos | B/F · renderMap(dfn)/similar | ¿Cómo cambian coordenadas de etapa-temporada y quién está cerca? | O18/O01; M36; A25/A49 | P_altura vs media P_volumen/P_contrapresión; línea de temporadas, top 3 por distancia 4D. | Trayectoria descriptiva de esos agregados; 159 unidades B/F. | Efecto del entrenador o continuidad exacta de la ventana SPECIAL: trayectoria usa todo coach-club. |
| V06 | Partido animado y resumen | B/F · renderFrame; engine.choreograph | ¿Qué choque de tasas genera el modelo? | O19; M37–39; A43–48/A53 | Canvas de jugadores/ballAt interpolados desde log simulado; resumen de posesiones con remate. | Ejemplo generado por modelo y semilla. | Reconstrucción de partido real o tracking observado. |
| V07 | Dominio por minuto, crónica y estadísticas | B/F · drawMomentum/renderLive/buildCum | ¿Cómo evoluciona la simulación seleccionada? | O19; M39/M41; A43/A47/A54 | Momentum por minuto:0,02 por pase/conducción al tercio final más xG de tiros; suavizado de 3 minutos; barras acumuladas y log. | Dominio definido por actividad del motor. | Momentum emocional/táctico observado o datos del calendario real. |
| V08 | Simulación rápida, marcadores y mapas | B/F · runQuick/heatHTML | ¿Qué distribución genera el mismo duelo con N=1500? | O19/O07; M38/M39; A43–48 | Medias de partidos simulados, W/D/L, marcadores frecuentes; mapas 6×3 de tiros/xG y recuperaciones. | Sensibilidad del generador a los parámetros del duelo. | Pronóstico calibrado o intervalos de confianza del resultado real. |
| V09 | Contexto por marcador/localía | F · context_view.js::render | ¿Cómo difieren circulación, peligro y presión entre contextos observados? | O14/O04/O05; M01/02/04/07/08/16/20/24–26; A09/A28–31 | Tarjetas de exposición y tabla de métricas/diferencias; null=s/d, advertencias de muestra. | Diferencia marginal descriptiva con exposición informada. | Cambio causado por DT/localía o comparar /90 con media por partido sin aviso. |
| V10 | Evolución temporal | T/F · renderTemporal | ¿Cómo varían las medias por bloques consecutivos? | O15; M01/03/06/08/12/15/18/19/27; A32/A33 | Tabla por bloques, cobertura y texto de contextos. El frontend no dibuja una serie de línea. | Variación descriptiva, sin clasificación estable/inestable. | Prueba estadística de identidad estable; transición de 15s tratada como 10s. |
| V11 | Jugadores y alineación inicial | F · renderPersonnel | ¿Quién aparece, inicia y acumula minutos registrados? | O12/O13; M28–30; A10/A34–36 | Tabla top 12 jugadores, conjunto inicial más frecuente, primeras 8 sustituciones y cobertura. | Participación y sustituciones registradas, con advertencias. | Rendimiento individual, rol táctico causal, o shape como once inicial modal de personas. |
| V12 | Firmas ofensivas y BP detallado | H/P · signaturePlays/setPieceHTML | ¿Qué etiquetas de posesión y lanzamientos son frecuentes? | O17/O11; M33; A20–22/A39 | Cards de firma con share/lift/xG10 y tablas de lanzadores/destinos/técnica. | Describir el clasificador implementado, con sus errores geométricos. | Taxonomía validada o xG10 como xG por diez tiros. Solo experimental. |
| V13 | Top 5 rival observado | P · renderDangerous/drawDangerous | ¿Cuáles de las posesiones rivales con tiro obtienen mayor score? | O16; M31/32; A38 | Lista, flechas/puntos de eventos, contexto defensivo y resumen del top 5. | Ejemplos seleccionados de ocasiones concedidas. | Frecuencia de todas las amenazas, defensa completa, zona común6×3 o score ordenado primero por xG dentro de goles. |
| V14 | Jugada desde descripción | P · parseNL/nlPositions/drawNL | ¿Cómo ilustrar una descripción de ataque? | O19; reglas de parser y coordenadas fijas; A48 | Regex→lista de acciones→cancha y narrativa animadas; fallback posesión estructurada. | Ilustración pedagógica generada a partir del texto. | Recuperación semántica de partido real, modelo de lenguaje entrenado o evidencia StatsBomb. |
| V15 | Clustering/PCA y exploración 360 | research · salida consola/CSV; doc histórico | ¿Hay agrupaciones separables o campos espaciales útiles? | O18/O03; M40; A40–42 | KMeans ofensivo/defensivo, PCA2, conteos visibles tipo packing; salidas parciales. | Ensayos de factibilidad, con cobertura limitada. | Clusters de la UI, tracking continuo o cobertura 360 en modelo actual. |
| V16 | Diagramas documentales previos | docs/como-funciona.html y DOCUMENTACION.md | ¿Cómo funcionaba la primera entrega? | O05/O07/O18/O19; B | Cancha por zonas, flujo, fórmulas, tablas de validación y ejemplos editoriales. | Explicación histórica contrastada con código. | Sus números/etiquetas como validación actual; usa fuentes web externas para tipografía. |
| V17 | Gráfico temporal de esta documentación | Nuevo HTML documental, datos F | ¿Cómo cambió el PPDA aproximado de Jardine entre bloques? | O15/O10; M08/M27; A32/A33; F entities[ame_jardine].temporal.periods | SVG estático accesible de nueve medias de partido, con tabla completa. | Variación de medias de bloque en la muestra especificada. | Visualización ya implementada en la app o cambio causal por entrenador. |

La trazabilidad de fuentes se resuelve por Oxx→Dxx y ruta/commit en ficha, Mxx→fórmula, Axx→regla. En particular: PPDA temporal V10→O15/O10→D02→M08→A16/A32/A33→F temporal.py, cuyo origen es m.opp_passes_own 60/m.ppda_den. El contexto de ese bloque vuelve a contextual.py::summarize_bucket; la media de partido del bloque no se reemplaza por la razón de sumas contextual.

## 12. Resultados auditados y caso de estudio: América de André Jardine

### R01. Cobertura y población

B:24 entidades (22 MX,1 Open Data,1 sintética), 159 unidades de mapa y league.matches 884. F:24 entidades,159 unidades y league.matches 890/445 partidos. P:24 entidades,147 puntos de mapa y league.matches 986; **sus conteos n no deben sumarse como partidos**. F tiene 70 IDs únicos solicitados/procesados de Jardine, sin exclusiones, entre 2023-07-01 y 2024-12-16;34 locales y 36 visitantes. Formación representativa 4-2-3-1. Fuente: modelos identificados abajo, O01/O02/O18, A03/A05.

### R02. Estilo suministrado y discrepancia de xG

Jardine B y F tienen raw posesión 0,535, directness suministrado 0,875, ritmo 2,634, PPDA suministrado 15,025, npxG 1,478 y npxGA 0,862 (medias redondeadas por partido). F percentiles: posesión 74, verticalidad 81, ritmo 31, línea 59, volumen 58, PPDA invertido 10, contrapresión 30, saque 61, centros 31, contra 58, robo alto 60, xG 93, xGA invertido 88 y BP 64. B difiere en línea 60, saque 60 y contra 59: no se mezclan esos puntos con F.

Datos de origen revisados: los 70 team-stats de Jardine suman np_xg=103,45116167 y 919 tiros no penales; los 70 archivos events suman xG no penal=107,3526380086 y 919 tiros no penales (periodos 1–4). Media de eventos=1,533609; temporal.xg sigue esta última (tolerancia de redondeo). Por tanto no se atribuye a Jardine una única media xG intercambiable entre fuentes. I16 registra una conciliación pendiente; se desconoce aquí la razón del proveedor para la diferencia. O11/M18/M34, A05/A27/A28.

### R03. Contexto F: razones de sumas y exposición observada

| Contexto | Partidos con exposición | Minutos reloj | Posesiones visitadas | Proxy por pases | Directness pases | PPDA aprox. | xG total/90 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| score_state/winning | 48 | 2320.04 | 2249 | 48.41% | 0.4689 | 20.048 | 1.4552 |
| score_state/drawing | 70 | 3762.83 | 3887 | 54.11% | 0.4319 | 20.585 | 1.3754 |
| score_state/losing | 31 | 1025.79 | 1101 | 62.82% | 0.4126 | 14.533 | 1.8384 |
| venue/home | 34 | 3443.95 | 3465 | 54.07% | 0.4316 | 19.643 | 1.6159 |
| venue/away | 36 | 3664.71 | 3772 | 52.94% | 0.4479 | 19.343 | 1.3295 |


Fuente exacta: F model.entities[id=ame_jardine].context. Todos estos buckets cumplen A30; unknown tiene cero exposición y valores analíticos null. Las mismas 70 observaciones de partido pueden aparecer en varios estados. En esta muestra, el proxy por pases es 62,82% perdiendo y 54,11% empatando; la diferencia es+8,70 puntos porcentuales. PPDA territorial es 14,533 perdiendo y 20,585 empatando. Es una descripción por marcador, no evidencia de una orden de presión ni efecto causal del DT. En localía, xG total/90 es 1,6159 en casa y 1,3295 fuera; sin ajuste por rivales/calendario. Objetos O04/O14, M01/M04/M08/M20/M25/M26; A09/A16/A29–31.

### R04. Nueve bloques cronológicos F

| Bloque | Fechas | Partidos | Directness Pass+Carry | Media PPDA de partido | Media xG no penal eventos |
| --- | --- | --- | --- | --- | --- |
| 1 | 2023-07-01 → 2023-09-21 | 8 | 0.457811 | 14.773995 | 1.738289 |
| 2 | 2023-09-24 → 2023-11-05 | 8 | 0.451331 | 25.376612 | 2.155508 |
| 3 | 2023-11-12 → 2024-01-14 | 8 | 0.485464 | 23.478146 | 1.289341 |
| 4 | 2024-01-21 → 2024-02-25 | 8 | 0.471415 | 21.252167 | 1.499504 |
| 5 | 2024-03-03 → 2024-04-27 | 8 | 0.463611 | 23.558800 | 2.013926 |
| 6 | 2024-05-09 → 2024-07-13 | 8 | 0.475101 | 22.956284 | 1.152397 |
| 7 | 2024-07-18 → 2024-09-30 | 8 | 0.479598 | 18.034018 | 1.131147 |
| 8 | 2024-10-06 → 2024-11-22 | 8 | 0.473573 | 14.382129 | 1.728647 |
| 9 | 2024-11-28 → 2024-12-16 | 6 | 0.540917 | 34.630511 | 0.947093 |


Fuente: F temporal.periods. Cada bloque contiene 8 partidos salvo el último 6. Se observa variación de medias PPDA entre 14,382129 y 34,630511. El último bloque no demuestra cambio decidido por entrenador ni es comparable por ratio de sumas con PPDA contextual. La diferencia entre directness de pases contextual y de Pass+Carry temporal es deliberadamente visible. O15, M03/M08/M18/M27, A32/A33. V17 dibuja únicamente esos nueve PPDA.

### R05. Jugadores y sustituciones F

70/70 partidos con lineup y sustituciones;55 jugadores identificados, de los cuales 46 tienen minutos>0;1.470 registros jugador-partido identificables (incluyen suplentes);317 sustituciones. Advertencia conservada: un intervalo invertido de Igor Lichnovsky. No se interpreta 55 como jugadores utilizados efectivamente.

| player_id | Jugador | Partidos con minutos | Titularidades | Minutos registrados |
| --- | --- | --- | --- | --- |
| 33098 | Luis Malagón | 64 | 64 | 6180.955 |
| 47467 | Álvaro Fidalgo | 63 | 56 | 5512.122 |
| 6357 | Jonathan dos Santos | 64 | 52 | 4484.819 |
| 30458 | Alejandro Zendejas | 61 | 48 | 4442.491 |
| 26400 | Henry Martín | 59 | 47 | 4361.773 |
| 33126 | Israel Reyes | 49 | 40 | 3927.373 |


Conjunto inicial más frecuente: Malagón, Layún, Lichnovsky, Valdés, Martín, Fuentes, Zendejas, Quiñones, Cáceres, Fidalgo y dos Santos, en 4 partidos. Es diferente del shape representativo de puestos. Par con mayor tiempo compartido exportado: Malagón–Fidalgo,5162,405 min y 53 titularidades conjuntas; son sumas descriptivas bajo reloj personnel, sujetas a I06. O12/O13, M28–30, A10/A34–37. No se afirma efecto en rendimiento.

### R06. Jugadas peligrosas P: evidencia histórica, no integración al caso 70

| ID partido:posesión | Fecha | Rival | xG último tiro | Score | Progresión | Duración s | Compatibilidad con caso 70 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3919036:21 | 2024-03-03 | Atlas | 0.9269 | 147.369 | 11.7 | 3.01 | Dentro por fecha; muestra P distinta |
| 3917858:162 | 2023-12-10 | Atlético San Luis | 0.6092 | 143.592 | -2.5 | 2.61 | Dentro por fecha; muestra P distinta |
| 3889669:48 | 2023-08-21 | Atlas | 0.5697 | 142.197 | 108.0 | 19.54 | Dentro por fecha; muestra P distinta |
| 4004103:134 | 2025-09-14 | Guadalajara | 0.5576 | 140.476 | 27.6 | 28.54 | Fuera de la ventana del caso 70 |
| 4038871:41 | 2026-03-01 | Tigres UANL | 0.5913 | 139.713 | -6.2 | 6.71 | Fuera de la ventana del caso 70 |


Fuente: P model.entities[id=ame_jardine].dangerous_plays; todos los cinco son goles (sesgo explícito del ranking). El conjunto proviene de la ventana ampliada 129; dos ejemplos son posteriores a 2024. No se utilizan para cuantificar frecuencia de amenaza del tricampeonato 70 ni para completar artificialmente F. Una progresión negativa es posible porque M32 usa avance neto. O16, M31/M32, A38; I01/I02/I08.

### R07. Calibración y verificaciones registradas

F meta.calibration conserva R²: directness 0,01; saque largo 0,11; tiros tras robo alto 0,14. Las tres se omiten en Barcelona (11 dimensiones disponibles); no se rellenan con percentil 50. Jardine obtiene 14 dimensiones por team-stats, no por esas calibraciones. El propio valor R² no valida tácticas ni transferencia entre épocas.

En B, pipeline/referee_report.txt registra 1.916.547 comprobaciones y 0 infracciones en 240 partidos simulados; validation_table.md conserva tablas históricas con poblaciones/tipos de tiros no plenamente comparables. En F, validation_summary.json y validation_report.txt registran 25 casos correctos aN=100,0 advertencias y 0 errores; referee_current_report.txt registra 575.758 comprobaciones,0 infracciones en 72 partidos. El informe F documenta 29 pruebas Python y 6 JavaScript y su contexto de ejecución. Se inspeccionaron los tests (reloj, marcador, autogoles, n/IDs, ausencias, calibración, backup, UTF-8, API, temporal, personal, frontend y validación); **esas suites no se reejecutaron como parte de esta entrega documental**. No se convierte un reporte histórico en un test ejecutado hoy. La validación F comprueba estructura/rangos/WDL; no exige tolerancia estadística frente a los datos reales. Pasar no valida identidad táctica ni precisión predictiva.

## 13. Alcance del framework

Permite describir ubicaciones de eventos, posesiones del proveedor observadas, circulación y avance aproximados, tiros/xG, presiones registradas, recuperaciones y pérdidas acotadas, contextos marginales de marcador/localía, evolución por bloques, participación registrada, conjuntos iniciales y simultáneos bajo los límites de su reloj. También permite explicar cómo se construyen estilos percentiles y resultados simulados. Las salidas avanzadas solo se atribuyen a la rama que las contiene.

## 14. Fuera de alcance

No captura tracking continuo, comportamiento de jugadores sin evento, estructura completa sin balón, distancias reales entre líneas, espacios libres, amplitud exacta de todo el equipo, sincronización completa de 22 jugadores ni intención táctica. No estima causalidad del entrenador, efectos ajustados de localía/rival/plantel, significancia temporal, detección validada de patrones, OBV, xT, VAEP o rendimiento individual aprendido. No hay cobertura 360 incorporada, modelo de lenguaje para recuperar jugadas ni predictor deportivo validado. Cruces de liga/época y arquetipos son hipotéticos.

## 15. Evidencia reproducible y archivos históricos

| Referencia | Commit | Bytes exactos de model/model.json | SHA-256 |
| --- | --- | --- | --- |
| main | 429c4ec | 479280 | df86d3f310f5a5b6366460700f21450dae1ccc22a0c8f969ccf994e90c215a7f |
| origin/main | d6db8e8 | 874520 | 028dca81de5f2665102ba8316bd19d5f72f3c7e6992fb7df0885390f3419dfcd |
| fix/model | 820e749 | 19568283 | 1ca33302d26468e6ffe98d9ffd0ad16aa1afeae087d46235a041391a3db8f826 |
| feat/game_description | e6f37b6 | 874520 | 028dca81de5f2665102ba8316bd19d5f72f3c7e6992fb7df0885390f3419dfcd |


B meta.built=2026-10-15 está fijado como literal en código, por lo que no prueba cuándo se ejecutó una construcción. F meta.built=2026-10-21T 03:05:18.227255+00:00 y schema/extract_version 2. P conserva el literal 2026-10-15 pese a cambios posteriores. Siempre preferir commit/hash.

Respaldos locales: model.json.pre-fix-20261019 es idéntico a B (SHA-256 de B). Los tres .pre-build-20261021T024941265709Z.gz, T 025608303019Z.gz y T 030520491440Z.gz descomprimen a 16.835.671 bytes idénticos, SHA-2560de583f2dfb9eeabb0b9fe29342f5eb23d1fb4b56c4ced47148b438101025bc2; contienen 70 partidos Jardine y temporal/personal/contexto sin schema 2. Son respaldo de trabajo, no una publicación ni una fase diferente por cada timestamp. No se modificaron.

Versiones contrastadas: 429c4ec y def5adc (árbol base y research); 89ffd25:DOCUMENTACION_TECNICA_COMPLETA.txt; ecdf05e:extract.py/build_model.py/entities.py/frontend; e6f37b6:dangerous.py/app/frontend/model y texto técnico; d6db8e8:model; ddc1571 (eliminación en checkpoint); f334f92:extract/build/check_model/test_metrics/docs; 763d415:temporal/test_temporal/app/frontend/model; 1924e17; 1ee7667:personnel/test_personnel/docs/model; 820e749:contextual/metric_utils/build/extract/temporal/personnel/targets/check_model, API, vistas, todos los test_* y reportes. Git blame confirmó origen inicial de pseudodenominadores y calibración, y 820e749 para contratos contextuales. Git diff confirmó la ampliación de ventana y las divergencias entre ramas.

Comandos de lectura para auditar sin cambiar la rama:

```bash
git status --short --branch
git branch -a
git log --oneline --decorate --graph --all
git diff main origin/main -- pipeline/entities.py pipeline/statsbomb.py
git diff main fix/model --stat
git show e6f37b6:model/model.json
git show 820e749:pipeline/contextual.py
git show 763d415:pipeline/temporal.py
git show 1ee7667:pipeline/personnel.py
git blame -L 205,222 820e749 -- pipeline/contextual.py
git grep -n -i -E 'PPDA|transition|directness|verticality|possession|pressure|dangerous|zone|high pressure' 820e749 -- pipeline frontend research docs
```

Las comprobaciones documentales (HTML, navegación, responsive, enlaces, UTF-8 y sintaxis si hay JS) se reportan en la entrega. Estas operaciones no alteran arquitectura, cálculos, datos ni ramas auditadas. Los resultados se conservan como R01–R07 con procedencia; cualquier nueva conclusión debe repetir este contrato de objeto+fuente+supuesto.

## 16. Comprobación de esta entrega documental

Se validó la estructura explícita de HTML con un parser local de etiquetas y un DOM lxml: cierres y atributos, IDs únicos, destinos de navegación y aria-labelledby, enlaces locales existentes, summary inicial en cada details, captions y número de columnas de tablas, UTF-8 estricto y ausencia de indicadores de corrupción. El HTML contiene 16 secciones y no requiere JavaScript, imágenes remotas ni hojas externas. node --check no aplica porque no incluye scripts.

Se comprobaron delimitadores CSS y reglas responsive a 1100/850/560 px, contenedores minmax(0,1fr) y desplazamiento horizontal limitado a tablas/figuras. Estas son comprobaciones estáticas: la revisión visual en escritorio/móvil y la apertura por doble clic no pudieron verificarse en el navegador integrado porque su política bloqueó el protocolo file://. No se afirma que esa revisión visual se haya realizado. La navegación usa anclas nativas con destinos existentes.
