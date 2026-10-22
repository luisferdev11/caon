# Framework metodológico de CAON · versión 2

**Proyecto:** CAON · Trabajo Táctico<br>
**Fuente funcional:** `overnight/jardine-historia` en `4e44246`<br>
**Artefacto publicado:** 21 de octubre de 2026<br>
**Complemento visual:** [`metodologia_resultados.html`](metodologia_resultados.html)

Este documento describe el sistema que existe en esa versión. Se apoya en `pipeline/framework_defs.py`, el `MARCO_ANALITICO.md` generado, la vista Método, los contratos de `pipeline/analytics/`, los artefactos de `model/` y las rutas de `app/main.py`. Una cifra del artefacto publicado y una obtenida en una regeneración local se mantienen separadas.

---

## 1. Propósito y alcance

CAON describe cómo juega un **equipo durante una ventana atribuida a un entrenador**, cómo cambia según el contexto y qué resultados acompañan esas señales. Responde:

1. ¿Qué identidad con y sin balón aparece en eventos y estadísticas?
2. ¿Cómo se construyen, progresan y terminan las posesiones, y cómo se defiende tras pérdida?
3. ¿Cómo varían esas señales por rival, marcador, localía, minuto, torneo, jugadores y cambios?
4. ¿Qué historia descriptiva puede trazarse con evidencia desde el partido hasta una conclusión editorial?

La unidad de atribución es `equipo + entrenador + ventana`. CAON no aísla el efecto causal del entrenador. Plantel, rival, calendario, expulsiones, localía, competición y cobertura también influyen. “En partidos con X sumó Y” describe una asociación.

El replay, el simulador y el laboratorio son productos derivados. No son pronósticos ni reconstrucciones de un partido real.

## 2. Jerarquía de evidencia

| Nivel | Representa | Ejemplo | Uso |
|---|---|---|---|
| Fuente | dato recibido | evento, lineup, team-stat, frame 360 | evidencia primaria con cobertura |
| Hecho derivado | regla determinista | pérdida seguida de tiro | cálculo con fórmula y denominador |
| Resumen | agregación | media, tasa, percentil, IQR | comparación descriptiva |
| Interpretación | texto condicionado | “vive en campo rival” | requiere métricas y límites |
| Salida generada | simulación o dibujo | replay xG, jugada de texto | ilustración, nunca observación |

Cada afirmación debe conservar identificador, fuente, unidad, ventana y límites. `null` significa no disponible; cero es un valor observado.

## 3. Estado documentado

La rama añade diez commits después de `origin/main` (`98759e5`): línea base y pruebas doradas; portal y marco; analítica; integración de KPI e historias; correcciones de PPDA y balón parado; vistas de Historia, Almada y Partidos; ficha de DT, Método y explorador; y cierre visual `4e44246`.

| Componente | Estado en `4e44246` |
|---|---:|
| Entidades del modelo | 30 |
| Entidades con análisis, KPI y replay | 28 |
| Fichas de partido | 411 |
| Equipos / entrenadores del explorador | 19 / 102 |
| Filas del explorador | 3,602 |
| Métricas de estilo | 14 |
| Definiciones en Método | 77 |
| Historias | Jardine y Almada |
| Jardine oficial | 91 partidos, 2023-07-01 a 2025-05-26 |

`model.json` declara `schema_version=2`, `extract_version=2`, rejilla 6×3, transición de 10 s y bloques temporales de 8 partidos. Fue construido el `2026-10-21T18:50:24.71483-06:00`.

## 4. Fuentes y cobertura

| Fuente | Contenido y uso | Límite |
|---|---|---|
| Calendarios StatsBomb v6 | partido, fecha, temporada, equipos, localía y selección | catálogo no implica descarga |
| Eventos StatsBomb v8 | acciones, posesión, ubicación, jugador, tiro, xG, OBV y presión | no registra todo movimiento sin balón |
| Lineups StatsBomb v4 | titulares, suplentes, posiciones e intervalos | no explica ausencias |
| Team-stats | 14 métricas suministradas; estilo y referencia | algunas fórmulas son externas al repo |
| Frames 360 | jugadores/región visibles; bloque, vigilancias y packing | cobertura parcial; cotas inferiores |
| Open Data | Barcelona 2009–11 | otra liga, época y cobertura |
| Configuración sintética | `arq_autobus` para contraste | no es un equipo histórico |

La ventana oficial termina el `2025-06-30` (Apertura 2021–Clausura 2025). El epílogo empieza el `2025-07-01`. El explorador usa también temporadas posteriores y rotula su referencia como ampliada.

El artefacto oficial de Jardine tiene 91 partidos con eventos y 2,488 pérdidas con vigilancias 360 válidas de 4,285 enlazadas. Esto describe el artefacto versionado; un clon puede no tener los datos crudos para reconstruirlo.

## 5. Pipeline y publicación

```text
API / Open Data → data/cache
  → extract.py                 mx_: simulador y agregados
  → extract_analysis.py        an_: posesiones y hechos
  → extract_360.py             f360_: hechos 360
  → shape360_ref + a4_reference
  → build_model.py             model.json + entities/
  → check_model.py + targets.py
  → build_analysis.py          analysis/ + replay/ + matches/ + explorer + xg_grid
  → kpis.py                    kpis/
  → story.py                   story/jardine.json + story/almada.json
  → audit_coherence.py         valores, IDs, textos y ventanas
  → FastAPI + portal
```

`run.py analysis` ejecuta desde referencias hasta auditoría sin repetir extracción. `run.py build` incluye extracción. Presupuestos: análisis por entidad ≤400 KB, ficha de partido ≤60 KB y `model.json` ≤4 MB. La UI consume artefactos; no recalcula métricas.

## 6. Objetos metodológicos

| ID | Objeto | Identidad | Riesgo |
|---|---|---|---|
| O01 | Entidad | equipo+DT+intervalo+ventana | entidades se solapan |
| O02 | Partido | `match_id` | catálogo no implica datos |
| O03 | Equipo-partido | partido visto desde un equipo | dos observaciones por partido |
| O04 | Evento | acción ordenada por periodo/tiempo | no es tiempo efectivo |
| O05 | Posesión | ID con acción del poseedor | aproximación del proveedor |
| O06 | Secuencia | posesión+origen+fase+desenlace | reanudación no es progresión |
| O07 | Ventana | oficial, epílogo o temprana | solo oficial sostiene conclusión |
| O08 | Referencia | equipo-temporada, n≥10 | explorador usa población ampliada |
| O09 | Pérdida | siguiente posesión útil es rival | tiro posterior es asociación |
| O10 | Transición | robo; fase ≤10 s | contraataque añade tiro≤15 s |
| O11 | Contexto | localía, rival, marcador, minuto, torneo | muestra desigual |
| O12 | Jugador | ID+intervalos+posición | minutos no son rendimiento |
| O13 | Frame 360 | jugadores visibles | no equivale a 22 jugadores |
| O14 | Hecho | valor+n+unidad+fuente+ventana | contrato obligatorio |
| O15 | KPI | hecho+referencia+terciles propios | no mide causalidad |
| O16 | Hallazgo | texto+evidencia resoluble | no inventa valores |
| O17 | Replay | 20,000 sorteos de posesiones con tiro | no pronóstico |
| O18 | Etiqueta | regla sobre percentiles | resume señales |
| O19 | Simulación | cadena probabilística de estilos | salida generada |

## 7. Geometría y constantes

El campo mide 120×80 yardas y el protagonista ataca hacia `x=120`. La rejilla tiene 6×3 zonas: `floor(x/20)·3+floor(y/26.67)`.

| Regla | Valor |
|---|---:|
| Tercio propio / final | x<40 / x≥80 |
| Área / zona de remate | x≥102, y 18–62 / y 30–50 |
| Área chica | x≥114 |
| Transición / desenlace | 10 s / 15 s |
| Contrapresión | 5 s |
| Recuperación rival / alta | x≥60 / x≥80 |
| PPDA defensa / pase rival | x≥48 / x<72 |
| Progresiva | x≥48; reducción≥25% y ≥10 yd |
| Falta / banda peligrosa | x≥80 / x≥90 |
| Pase largo | ≥35 yd |
| Sustitución | ±15 min; hueco ±2 min |
| Prior / intervalo | 8 partidos / 80% |
| Resultado sorpresivo | p<20% |
| Semáforo KPI | P33/P67; mínimo 12 partidos |
| Replay | 20,000 sorteos; semilla `match_id` |

## 8. Glosario completo de Método

Estas son las 77 definiciones de `/api/framework`. La redacción normativa vive en `framework_defs.py` y genera `MARCO_ANALITICO.md`.

### 8.1 Espacio, posesión y progresión

| ID | Definición / fórmula | Unidad y fuente | Límite |
|---|---|---|---|
| `coord` | marco 120×80; rival `(120-x,80-y)` | yd · eventos | 360 usa marco del actor |
| `zona` | rejilla 6×3 | 0–17 · eventos | igual al simulador |
| `tercio` | propio<40, medio40–80, final≥80 | categoría · eventos | marco protagonista |
| `secuencia` | posesión con acción ofensiva | posesiones · eventos | sin administrativas |
| `origen` | robo, portero, banda, falta, córner, inicio, otro | categoría · eventos | robo exige posesión rival previa |
| `salida_limpia` | x<40→x≥60, completadas | % · eventos | juego abierto |
| `progresion_limpia` | x<60→x≥80 | % · eventos | juego abierto |
| `creacion` | entra al área o tira | % · eventos | área x≥102 |
| `entradas_area` | pase/conducción al área o tiro | por partido · eventos | por posesión |
| `prog` | reduce distancia ≥25% y ≥10 yd, o pase al área | acciones/partido · eventos | completada; no reinicio BP |
| `field_tilt` | acciones propias / total en último tercio | % · eventos | no posesión total |
| `xg_origen` | npxG por origen / partidos | xG/partido · eventos | puede diferir de team-stats |

### 8.2 Ocasiones, transiciones y pérdidas

| ID | Definición / fórmula | Unidad y fuente | Límite |
|---|---|---|---|
| `npxg_por_tiro` | ΣnpxG/tiros | xG/tiro · eventos | sin penales |
| `tiros_zona_remate` | tiros x≥102,y30–50 / tiros | % · eventos | zona central |
| `transicion` | posesión nacida de robo; primeros 10 s | posesiones · eventos | espejo defensivo |
| `contraataque` | robo x<60→tiro≤15 s | por partido · eventos | regla local |
| `perdida` | siguiente posesión útil es rival | por partido · eventos | distingue juego/BP |
| `perdida_costosa` | pérdida→tiro rival≤15 s | por partido o % · eventos | asociación |
| `perdida_letal` | pérdida costosa→gol | total · eventos | muestra pequeña |
| `tipo_error` | no forzado, presión, arriesgada, duelo, aislado, otro | categoría · eventos/360 | reglas ordenadas |
| `rec_tiro` | tiro≤15 s tras robo x≥60/80 | posesiones/partido · eventos | no team-stat |
| `jugada_peligrosa_concedida` | posesión rival con tiro; orden gol,xG,OBV,fecha | jugadas · eventos | `1-Π(1-xg)` |
| `xg_concedido` | ΣxG rival por tipo | xG/partido · eventos | sin penal salvo aviso |
| `x_media_tiros_concedidos` | x media desde arco propio | yd · eventos | menor=más cerca |

### 8.3 Presión y defensa

| ID | Definición / fórmula | Unidad y fuente | Límite |
|---|---|---|---|
| `fase_presion` | acciones defensivas según altura del balón | acción · eventos | alta/media/baja |
| `ppda` | pases rivales x<72 / defensas x≥48 | pases/acción · eventos | menor=más presión |
| `contrapresion` | presión `counterpress`≤5 s | por partido · eventos | señal base |
| `contrapresion_efectiva` | rival dura≤5 s y acaba en recuperación | % pérdidas · eventos | juego abierto |
| `rec_campo_rival` | robo x≥60 | robos/partido · eventos | regla local |
| `rec_alta` | robo x≥80 | robos/partido · eventos | no tiro posterior |

### 8.4 Jugadores, contexto y resultados

| ID | Definición / fórmula | Unidad y fuente | Límite |
|---|---|---|---|
| `minutos_jugador` | minutos/minutos equipo | % · lineup/eventos | no explica ausencia |
| `formacion` | inicios con esquema/partidos | % · lineup | no forma dinámica |
| `puntos` | `(3V+E)/partidos` | pts/partido · eventos | tiempo regular |
| `xg_dif` | npxG−npxGA | xG/partido · team-stats | fuente agregada |
| `salida_portero` | saques/pases GK ≥35 yd | % · eventos | distinta de `saque_largo` |
| `rival_tier` | rango xGD: 1–6,7–12,13–18 | categoría · team-stats | circular; previa si n<10 |
| `minuto` | siete tramos+prórroga | categoría · eventos | añadido en último tramo |
| `marcador` | ganando/empatando/perdiendo antes de acción | categoría · eventos | perspectiva protagonista |
| `obv` | Σ`obv_total_net` | goles esperados · eventos | validado contra team-match |
| `ventana` | oficial/epílogo/temprana | categoría · fecha | conclusión solo oficial |
| `encogimiento` | `(n·x̄+8·μ0)/(n+8)` | según métrica · team-stats | prior carrera/liga |
| `consistencia` | IQR+bootstrap 80% | según métrica · eventos | descriptivo |
| `xpts` | `3P(V)+P(E)` | pts/partido · eventos | replay, no pronóstico |
| `resultado_sorpresivo` | p(resultado real)<0.20 | partidos · eventos | interpretativo |
| `xi_base` | más minutos por posición | jugadores · lineup | no XI universal |
| `rotacion` | ΔXI entre partidos | jugadores/partido · lineup | incluye bajas |
| `cambios` | minuto medio y marcador | minuto · eventos | lesión si está marcada |
| `impacto_cambio` | después−antes en xG,OBV,field tilt | según métrica · eventos | descriptivo; mismo marcador |

### 8.5 Balón parado

| ID | Definición / fórmula | Unidad y fuente | Límite |
|---|---|---|---|
| `bp_peligro` | córner; falta x≥80; banda x≥90 | jugadas · eventos | regla analítica |
| `bp_ofensivo` | xG propio en posesión BP | xG/partido · eventos | incluye segunda jugada |
| `bp_defensivo` | xG rival en posesión BP | xG/partido · eventos | marca requiere 360 |
| `bp_diferencial` | ofensivo−defensivo | xG/partido · eventos | KPI 7 |

### 8.6 Catorce métricas de estilo

| ID | Team-stat | Unidad | Percentil alto |
|---|---|---|---|
| `posesion` | possession | % | más balón |
| `verticalidad` | directness | proporción | más directo |
| `ritmo` | pace_towards_goal | m/s | más rápido |
| `linea` | defensive_distance | m | más adelantado |
| `volumen_presion` | pressures_adj | por partido | más volumen |
| `presion` | ppda | pases/acción | PPDA más bajo |
| `contrapresion` | counterpressures | por partido | más contrapresión |
| `saque_largo` | gk_long_pass_ratio | proporción | más largo |
| `centros` | crosses_into_box | por partido | más centros |
| `contragolpe` | counter_attacking_shots | por partido | más tiros de contra |
| `presion_alta_tiros` | high_press_shots | por partido | más tiros tras robo |
| `xg` | np_xg | xG/partido | más generación |
| `xga` | np_xg_conceded | xG/partido | menos concesión |
| `bp_xg` | sp_xg | xG/partido | más peligro BP |

Las conversiones locales de `verticalidad`, `saque_largo` y `presion_alta_tiros` quedan no disponibles si `R²<0.5`; no se imputan.

### 8.7 Identidad

| ID | Fórmula | Salida |
|---|---|---|
| `vel_ataque` | `(ritmo+contragolpe)/2` | percentil |
| `intensidad_presion` | `(volumen+PPDA invertido+contrapresión)/3` | percentil |
| `perfil_presion` | coherencia de las tres señales | categoría |

Mapa ofensivo: velocidad×posesión. Defensivo: línea×intensidad. Extremo≥80 o≤20; equilibrado si ambos ejes están a menos de 9 puntos de 50.

- `asfixiante`: volumen≥75, PPDA invertido≥60, contrapresión≥50.
- `sin_robo`: volumen≥65, PPDA invertido≤45, contrapresión<75.
- `selectiva`: volumen≤45 y PPDA invertido≥65.
- `espera`: volumen≤30, PPDA invertido≤40, contrapresión≤50, línea≤40.

### 8.8 Métricas 360

| ID | Definición | Unidad / límite |
|---|---|---|
| `vigilancias` | propios visibles detrás del balón al robo | jugadores; cota inferior |
| `vigilancias_bajas` | pérdidas con ≤2 vigilancias | % pérdidas |
| `altura_linea` | media x de 3 más retrasados | yd; visibilidad≥70% |
| `bloque_360` | altura, largo, ancho y envolvente | yd/yd²; ≥7 visibles |
| `rompe_lineas` | rivales visibles superados por pase | jugadores; cota inferior |
| `presion_360` | apoyos≤10 yd y opciones libres | jugadores; cota inferior |
| `corner_def` | emparejamiento≤1.5 yd y tipo de marca | inferido |
| `contexto_error` | apoyos, rivales, defensor, xPass, presión | conteos/distancia |
| `forma_cambio` | Δ forma antes/después del cambio | yd; descriptivo |

## 9. Siete KPIs

`ref_pct` compara con la referencia oficial; el semáforo usa P33/P67 de los propios partidos. Verde significa tramo favorable para ese KPI, no éxito causal.

| # | KPI | Jardine oficial | Referencia | Base |
|---:|---|---:|---:|---|
| 1 | Field tilt | 59.792% | P98.6 | 40,763 acciones |
| 2 | Progresión limpia | 36.833% | P97.2 | 4,762 posesiones |
| 3 | npxG por tiro | 0.1153 | P98.6 | 1,196 tiros |
| 4 | Contrapresión efectiva | 13.419% | P45.8 | 4,695 pérdidas |
| 5 | Pérdidas costosas | 2.758/partido | P66.7 favorable | 91 partidos |
| 6 | Vigilancias | 4.55 visibles | P33 | 2,488 válidas |
| 7 | Diferencial BP | +0.0676 xG/partido | sin percentil | 0.3470−0.2794 |

En verde de calidad de ocasión sumó 2.53 puntos/partido frente a 1.13 en rojo (`n=30/30`), una asociación descriptiva.

## 10. Contexto y muestras pequeñas

El contexto desglosa por localía, nivel rival, marcador previo, tramo de minuto, torneo, fase, ventana y etapa del club. Cada hecho conserva numerador, denominador, partidos y advertencias; “resto” excluye el estrato observado.

El explorador encoge con `n0=8` e intervalo 80%. Confianza: muy baja `<5`, baja `5–11`, media `12–24`, alta `≥25`; menos de 12 es muestra chica.

## 11. Replay de xG

Por partido se agrupan tiros por posesión y se usa `1-Π(1-xG)`. Hay 20,000 sorteos con semilla `match_id`, penales con su xG, autogoles fijos y tandas excluidas. `xPts=3P(V)+P(E)`. Resultado sorpresivo: probabilidad real <20%. Es interpretación de ocasiones, no pronóstico.

## 12. Resultados versionados: Jardine

### Población e identidad

- `ame_jardine`: 91 partidos oficiales, 2023-07-01 a 2025-05-26; formación modal 4-2-3-1.
- Con balón: **Posesión con pase vertical**, ataque **Por dentro**, cuadrante **Posesión elaborada**.
- Sin balón: **Línea alta: presiona mucho, deja jugar**.
- Etiquetas: Directo pero paciente, Muy sólido atrás, Dueño del balón, Línea muy alta.
- Presión: volumen P67, PPDA invertido P8, contrapresión P44, intensidad P40.

Percentiles: posesión 81, verticalidad 93, ritmo 31, línea 81, volumen 67, PPDA 8, contrapresión 44, saque largo 68, centros 28, contra 62, robo alto 78, xG 96, solidez 88 y BP 69.

### Historia publicada

`story/jardine.json` contiene 12 capítulos y 46 hallazgos:

1. Portada: 1.93 puntos y 1.83 xPts por partido.
2. Identidad: etiquetas con y sin balón.
3. Con balón: salida 46.5%, progresión 36.8%, 0.12 npxG/tiro, OBV 1.98, field tilt 59.8%.
4. Sin balón: presión, 18.5 robos rivales, 0.87 xGA y bloque 360.
5. Transiciones: 51.6 pérdidas/partido, coste por tipo y tercio.
6. Dolor: 10.7 posesiones rivales con tiro/partido y Top-N.
7. Balón parado: 0.35 xG a favor, 0.28 en contra, +0.07.
8. Contexto: localía, rival, marcador, minuto, liguilla y entrenador/club.
9. Jugadores: núcleo, roles, formaciones y cambios.
10. Mereció ganar: 176 puntos contra 166.79 esperados; +9.21.
11. KPI: 4 de 7 sobre referencia y 1 debajo de la mayoría.
12. Epílogo: 1.68 puntos y 1.70 xPts, fuera de ventana.

Replay oficial: 12 resultados sorpresivos, 61.75% del xG total y 59.48% de field tilt.

### Lecturas con límite

- Local: 2.27 puntos/partido contra 1.61 en el resto; no controla rival.
- Rival débil: field tilt 70.2% contra 56.1%; tier circular.
- Perdiendo: field tilt 74.1% contra 57.4%; respuesta, no intención.
- Liguilla: 1.06 xG/partido contra 1.61; muestras/rivales distintos.
- 45% de inicios en 4-2-3-1 y cinco formaciones; registro no forma dinámica.
- 4.6 cambios/partido; primero cerca del 57; asociación descriptiva.

## 13. Trazabilidad de interfaz

| Vista | Artefactos | Contenido |
|---|---|---|
| Historia | story+analysis+glossary | 12 capítulos y evidencia |
| Almada | story/almada+entidades | etapa previa y muestra temprana |
| Partidos | matches+replay+xg_grid | xG, xPts, momentos, veredicto |
| Entrenador | entity+analysis+kpis | identidad, contexto, jugadores |
| Explorador | explorer.v3 | 19 equipos, 102 DTs, intervalos |
| Laboratorio | model+parser | simulación/jugada generada |
| Método | `/api/framework` | 77 definiciones y umbrales |

Método muestra definición, unidad y límites; en modo DT añade fórmula, fuente y umbrales. `#metodo/{id}` enfoca una definición.

## 14. Limitaciones y reproducibilidad local

### Límites del diseño

1. No identifica causalidad del entrenador.
2. Posesión no es tiempo efectivo.
3. Eventos no ven desmarques; 360 ve parte del campo.
4. Tier rival es circular.
5. Etiquetas condensan heterogeneidad.
6. Semáforo usa terciles propios.
7. Replay y simulador no pronostican.
8. Team-stats y eventos pueden tener fórmulas distintas.

### Verificación en esta PC

Había 493 `mx_*` y 68 `od_*`, pero faltaban `an_*` y `f360_*`. `run.py extract` creó 493 `an_*`; no creó `f360_*` por falta de frames. El análisis local produjo 7 unidades A4 y 30 entidades, pero no reprodujo el 360 oficial.

La historia local quedó en 12 capítulos y 44 hallazgos, sin `contexto_rival`. La auditoría reportó 105 faltantes `n`, `unit`, `source` en el recorrido KPI; valores, etiquetas, umbrales, ventanas y textos no mostraron errores. Esto no sustituye el resultado versionado: identifica que el pipeline no cierra en verde con la caché de esta PC.

### Acción recomendada

- recuperar cobertura de eventos y 360 del artefacto oficial;
- ejecutar `run.py build` sin bloqueos de OneDrive;
- resolver el contrato KPI de `audit_coherence.py`;
- exigir auditoría verde antes de publicar;
- guardar manifiesto de IDs y hashes por versión.

## 15. Reproducción

```powershell
python -X utf8 pipeline/run.py extract
python -X utf8 pipeline/run.py analysis
python -X utf8 pipeline/check_model.py
python -X utf8 -m unittest discover -s pipeline -p 'test_*.py'
node --test pipeline/test_*.js
node pipeline/validate.js 100
node pipeline/referee.js 3
python -m uvicorn app.main:app --port 8010
```

Aceptación: extracción válida → referencias no vacías → modelo válido → análisis dentro de presupuesto → 7 KPI → historias con evidencia → auditoría → pruebas → HTTP y revisión visual.

## 16. Fuentes de este documento

- `frontend/views/method.js`; `pipeline/framework.py`; `pipeline/framework_defs.py`.
- `docs/MARCO_ANALITICO.md`; `pipeline/analytics/*.py`.
- `pipeline/kpis.py`; `pipeline/story*.py`; `pipeline/audit_coherence.py`.
- `model/model.json`; `model/analysis/ame_jardine.json`; `model/kpis/ame_jardine.json`.
- `model/story/{jardine,almada}.json`; `model/explorer.json`; `app/main.py`.

Las secciones 3, 9 y 12 corresponden a `4e44246`. La sección 14 distingue la ejecución local posterior para no confundir resultado publicado con reproducibilidad.
