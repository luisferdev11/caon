# Framework metodológico de CAON

**Proyecto:** CAON · Trabajo Táctico
**Complemento para el jurado:** [Metodología, visualizaciones y resultados](metodologia_resultados.html)

Este documento especifica cómo se construyen las medidas de la aplicación y cómo se interpretan en fútbol. Se apoya en el registro de Método, los módulos analíticos y sus resultados. Las reglas son definiciones operativas del proyecto: explicitar su lógica permite repetir un cálculo, pero no demuestra por sí solo validez predictiva o causal.

## 1. Diseño del estudio y exploración de datos

Primero delimitamos la pregunta: describir cómo juega un equipo durante la etapa de un entrenador y relacionar ese comportamiento con sus resultados. Elegimos como caso principal al América de Jardine: 91 partidos entre el 1 de julio de 2023 y el 26 de mayo de 2025. La unidad de análisis combina equipo, entrenador y periodo; no pretende aislar el efecto personal del entrenador.

Exploramos calendarios, eventos, alineaciones, estadísticas por equipo y cuadros 360. Revisamos identificadores, fechas, equipos, tipos de acción, campos disponibles y cobertura. El calendario permitió seleccionar encuentros; los eventos reconstruir posesiones; las alineaciones reconocer participantes y cambios; las estadísticas resumir estilo; y el 360 describir jugadores visibles alrededor del balón. La disponibilidad se comprobó por fuente: que un partido exista en el calendario no garantiza que tenga todas esas capas.

Después organizamos las acciones en una cancha común, ordenamos las secuencias y separamos juego abierto, reanudaciones y contextos. Convertimos preguntas futbolísticas en reglas observables: alcanzar una zona conservando el balón, recuperar después de perder, permitir un tiro o mantener jugadores de resguardo. Establecimos coordenadas y tiempos explícitos para aplicar el mismo criterio a todos los casos.

Agregamos los hechos como tasas, promedios y distribuciones. Elegimos el denominador según la pregunta: posesiones elegibles para progresión, tiros sin penal para calidad de ocasión, pérdidas para reacción defensiva y partidos para frecuencia. Comparamos contra referencias compatibles y dividimos por localía, rival, marcador y momento del juego. Los valores ausentes permanecen sin dato; no se reemplazan por cero.

Construimos la aplicación separando cálculo y presentación. Los procesos Python preparan resúmenes y archivos JSON por entidad, partido e historia. FastAPI expone esos archivos mediante una API; las vistas HTML, CSS y JavaScript los convierten en tarjetas, tablas, canchas y gráficos. El registro de Método reúne las definiciones que consulta la interfaz. Los hallazgos narrativos enlazan métricas y evidencia, y el laboratorio utiliza un motor probabilístico para explorar estilos.

La cadena de evidencia es fuente → hecho calculado → resumen → interpretación. Una simulación es una salida generada. Cada hecho debe poder rastrearse por identificador, valor, unidad, base de cálculo, fuente y periodo. `null` representa ausencia de dato; cero representa una observación válida.

## 2. Datos obtenidos y finalidad

| Fuente | Qué obtuvimos | Para qué y cómo lo usamos |
|---|---|---|
| Calendarios StatsBomb | IDs, fechas, torneo, temporada, equipos y localía | Seleccionar encuentros y formar ventanas comparables. |
| Eventos StatsBomb | Acciones, ubicaciones, tiempos, posesiones, jugadores, remates, xG, OBV y presión | Ordenar secuencias y calcular progresión, pérdidas, recuperación, ocasiones y contexto. |
| Alineaciones | Participación, posición, formación e intervalos | Reconstruir minutos, once habitual, rotación y sustituciones. |
| Estadísticas por equipo (team-stats) | 14 señales de estilo por equipo-partido | Construir referencias, percentiles, mapas y etiquetas; se conservan las medidas del proveedor. |
| Cuadros 360 | Posiciones y región visible en instantes asociados a eventos | Calcular resguardo, bloque y relaciones espaciales con filtros de cobertura. |
| Open Data | 68 partidos del Barcelona de Guardiola, 2009–2011 | Perfil histórico de contraste en el laboratorio; calibración experimental desde eventos. |
| Configuración sintética | Perfil `arq_autobus`, formación 4-4-2 | Contraste de bloque bajo y contraataque para comprobar la respuesta del motor. No aporta partidos históricos observados. |

Ambos perfiles de contraste se comprobaron seleccionándolos en `/lab.html`, dentro de «Equipos de validación». Barcelona muestra plan, métricas y formación; verticalidad, saque largo y tiros tras robo alto quedan sin dato al no superar el criterio de calibración R²≥0.5. El arquetipo muestra «Contragolpe» y «Bloque bajo». Su campo interno `n=60` es configuración, no una muestra empírica. Ninguno forma parte de los 91 partidos de Jardine ni dispone de la misma ficha analítica completa que ese caso.

La población oficial comprende Apertura 2021–Clausura 2025, hasta el 30 de junio de 2025. El epílogo empieza el 1 de julio de 2025. La muestra del caso Jardine ocupa una parte de esa población. El explorador puede consultar temporadas adicionales y utiliza una referencia ampliada.

## 3. Construcción de la aplicación y flujo de cálculo

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


La extracción genera representaciones distintas según la tarea: `mx_` alimenta agregados y simulación, `an_` conserva hechos de posesión y `f360_` añade geometría visible. Los archivos ligeros permiten abrir el portal; el detalle se solicita por entidad o partido. Esta separación evita recalcular la historia al navegar.

El motor del laboratorio estima, por zona y fase, probabilidades de pasar, conducir, rematar y finalizar la posesión. Utiliza una rejilla de 18 zonas y distingue los primeros diez segundos tras robo del ataque establecido. El laboratorio de texto interpreta una jugada y la anima sobre formas del equipo; esa escena es generada, no vídeo ni seguimiento real de jugadores.

## 4. Objetos metodológicos

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

## 5. Geometría y constantes

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


Las distancias de eventos están en yardas; algunas estadísticas suministradas están en metros. No se mezclan directamente. Las fronteras espaciales y temporales permiten comparar acciones con un criterio constante; su elección no afirma que exista una frontera táctica universal exactamente en ese punto.

## 6. Diccionario técnico y explicación futbolística

Se documentan las 77 entradas de `/api/framework`. Cada ficha incluye la definición formal, fórmula, unidad, fuente, límites y la razón de usarla. Las 14 señales de estilo incluyen contrapresión, descrita una sola vez en el grupo de presión. La explicación futbolística justifica la operacionalización; no sustituye una validación externa.

### 6.1. Espacio, posesión y progresión

#### `coord` · Sistema de coordenadas

**Definición técnica.** Campo StatsBomb de 120×80 yardas; cada evento en el marco de ataque de su equipo (ataca hacia x=120). En pantalla el protagonista ataca de izquierda a derecha.

**Cálculo o campo.** `rival: (120-x, 80-y) vía to_frame`
**Unidad:** yardas. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Orientamos todas las acciones hacia la misma portería para que avanzar signifique lo mismo en ambos tiempos y para ambos equipos. Sin esta transformación, una recuperación alta podría parecer baja solo por el sentido de ataque.

**Alcance.** Los 360 vienen en el marco del equipo actor.

#### `zona` · Zona del campo

**Definición técnica.** Rejilla de 6 columnas × 3 carriles (20 yd × 26.7 yd).

**Cálculo o campo.** `zona = floor(x/20)·3 + floor(y/26.67)`
**Unidad:** zona 0–17. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Dividimos la cancha en 18 espacios para resumir rutas del balón y estimar transiciones del simulador. Sacrificamos precisión espacial a cambio de reunir suficientes acciones comparables en cada zona.

**Alcance.** Idéntica a la del simulador.

#### `tercio` · Tercio

**Definición técnica.** Propio x<40, medio 40–80, final x≥80.

**Cálculo o campo.** `umbral en x`
**Unidad:** tercio. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Dividimos el largo del campo en tres partes iguales para distinguir salida, circulación y ataque cerca del arco. Son límites operativos repetibles; cruzarlos no demuestra por sí solo que se haya superado una línea defensiva.

**Alcance.** Marco propio.

#### `secuencia` · Posesión (secuencia ofensiva)

**Definición técnica.** Posesión de StatsBomb con al menos una acción con balón (pase, conducción, regate o tiro) del equipo poseedor; se ignoran las solo administrativas.

**Cálculo o campo.** `possession id con ≥1 acción con balón`
**Unidad:** posesiones. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Agrupamos las acciones de una misma posesión para estudiar una jugada completa. Exigimos actividad con balón porque una interrupción administrativa no representa un ataque; el identificador del proveedor aproxima la continuidad del juego.

**Alcance.** Aproximada desde eventos. Se excluye un tiro hecho dentro de una posesión rival (1 de 2,241 tiros y menos de una milésima del xG en los 91 partidos de Jardine; se mide en rival_shots de cada an_). La jugada que reanuda (córner, tiro libre, saque de banda o de puerta, inicial) no cuenta como progresión.

#### `origen` · Origen de la posesión

**Definición técnica.** Robo en juego, portero, banda, tiro libre, córner, saque inicial u otro.

**Cálculo o campo.** `tipo de reanudación + posesión previa`
**Unidad:** categoría. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Clasificamos cómo empieza cada posesión para distinguir atacar después de recuperar de atacar tras una reanudación. Así comparamos situaciones con organizaciones defensivas iniciales diferentes.

**Alcance.** Robo = posesión previa rival en juego.

#### `salida_limpia` · Salida limpia

**Definición técnica.** Posesión en juego que nace en x<40 y llega a x≥60 sin perder el balón.

**Cálculo o campo.** `inicio x<40 y max_x≥60 (solo acciones completadas)`
**Unidad:** % de posesiones. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Buscamos posesiones que salgan del tercio propio y alcancen la mitad del campo conservando el balón. Llegar mediante una acción completada permite medir avance efectivo y evita dar por buena una entrega interceptada.

**Alcance.** Solo juego abierto.

#### `progresion_limpia` · Progresión limpia

**Definición técnica.** Posesión que nace en x<60 y llega a x≥80 sin perder el balón.

**Cálculo o campo.** `inicio x<60 y max_x≥80 (solo acciones completadas)`
**Unidad:** % de posesiones. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Contamos cuántas posesiones nacidas en campo propio alcanzan el último tercio sin perderse. El denominador incluye solo las que podían hacer ese recorrido, por lo que una recuperación ya cerca del arco no cuenta como progresión desde atrás.

**Alcance.** Solo juego abierto.

#### `creacion` · Creación

**Definición técnica.** Posesión que entra al área rival o termina en tiro.

**Cálculo o campo.** `entrada al área o tiro`
**Unidad:** % de posesiones. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Una posesión crea acceso ofensivo cuando entra al área o termina en tiro. La regla capta una amenaza concreta, aunque no garantiza una ocasión clara ni un remate de calidad.

**Alcance.** Área: x≥102, 18≤y≤62.

#### `entradas_area` · Entradas al área

**Definición técnica.** Posesiones propias que llevan el balón al área rival (pase o conducción que termina dentro, o tiro).

**Cálculo o campo.** `box_entry por posesión`
**Unidad:** por partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Contamos posesiones que llevan el balón al área mediante pase, conducción o tiro, no cada toque dentro de ella. Esto evita inflar la medida por varios contactos en una misma llegada.

**Alcance.** Área: x≥102, 18≤y≤62.

#### `prog` · Acción progresiva

**Definición técnica.** Pase o conducción completada (no la primera de un balón parado), desde x≥48, que acerca el balón a la portería ≥25% y ≥10 yd, o pase completado al área desde fuera.

**Cálculo o campo.** `Δd(120,40) ≥ 25% y ≥ 10 yd`
**Unidad:** acciones/partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Reconocemos acciones completadas que acercan sustancialmente el balón al arco. La reducción relativa y la distancia mínima evitan etiquetar como progresivo un avance pequeño; el pase al área desde fuera reconoce un acceso ofensivo especialmente relevante.

**Alcance.** Solo acciones completadas.

#### `field_tilt` · Dominio territorial (field tilt)

**Definición técnica.** Proporción de acciones con balón en el último tercio que son propias.

**Cálculo o campo.** `propias_tercio_final / (propias + rivales)`
**Unidad:** %. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Comparamos la actividad de ambos equipos cerca de la portería contraria. Un 60% significa que seis de cada diez acciones de ambos en sus respectivos últimos tercios fueron del protagonista; no que tuvo el balón el 60% del tiempo.

**Alcance.** Igual al fieldTilt del simulador.

#### `xg_origen` · xG por origen de la jugada

**Definición técnica.** xG sin penales por partido de las posesiones que nacen en cada origen: robo, portero, banda, tiro libre, córner u otro.

**Cálculo o campo.** `Σ xG de posesiones de ese origen / partidos`
**Unidad:** xG por partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Sumamos la calidad de los remates según cómo nació la jugada y la dividimos por partidos. Permite ver si el peligro procede de robos, salida del portero o reanudaciones sin confundir volumen con goles finalmente marcados.

**Alcance.** Desde eventos; no suma exactamente el xG de team-stats.

### 6.2. Ocasiones, transiciones y pérdidas

#### `npxg_por_tiro` · Calidad de ocasión (npxG por tiro)

**Definición técnica.** xG promedio de los tiros propios sin contar penales.

**Cálculo o campo.** `Σ xG sin penal / tiros sin penal`
**Unidad:** xG por tiro. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Dividimos la calidad estimada acumulada de las ocasiones entre los remates sin penal. Así distinguimos tirar mucho de elegir buenas posiciones; excluimos penales por ser una situación especial de alta probabilidad.

**Alcance.** xG de StatsBomb.

#### `tiros_zona_remate` · Tiros desde la zona de remate

**Definición técnica.** Porcentaje de tiros sin penal hechos desde la zona de remate (x≥102, 30≤y≤50).

**Cálculo o campo.** `tiros en zona / tiros`
**Unidad:** % de tiros. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Medimos la proporción de tiros desde el centro del área, una zona próxima al arco. La geometría identifica el lugar del remate; el xG añade información de dificultad que la zona por sí sola no contiene.

**Alcance.** Zona central del área.

#### `transicion` · Transición ofensiva

**Definición técnica.** Posesión nacida de un robo en juego; la fase de transición son sus primeros 10 s.

**Cálculo o campo.** `origen=robo, t ≤ 10 s`
**Unidad:** posesiones. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Separamos los primeros segundos después de un robo porque el rival puede estar reorganizándose. Diez segundos es la frontera operativa del proyecto, no una duración universal de todas las transiciones.

**Alcance.** Espejo: transición defensiva.

#### `contraataque` · Contraataque

**Definición técnica.** Transición que nace en x<60 y termina en tiro en ≤15 s.

**Cálculo o campo.** `robo x<60 → tiro ≤ 15 s`
**Unidad:** contraataques/partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Exigimos recuperar en campo propio y rematar dentro de quince segundos para reconocer un ataque rápido con desenlace. Una recuperación alta con tiro pertenece a otro indicador, aunque también pueda aprovechar desorden rival.

**Alcance.** Compatible con StatsBomb.

#### `perdida` · Pérdida

**Definición técnica.** Fin de una posesión propia cuando la siguiente posesión no administrativa es rival.

**Cálculo o campo.** `lossO en juego; lossX* con balón parado`
**Unidad:** pérdidas/partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Detectamos el paso de una posesión propia a otra rival con juego. Esto ofrece una regla estable para estudiar qué ocurre después de dejar de tener el balón, manteniendo aparte las reanudaciones.

**Alcance.** Como en extract.

#### `perdida_costosa` · Pérdida costosa

**Definición técnica.** Pérdida en juego seguida de tiro rival en ≤15 s dentro de esa posesión rival.

**Cálculo o campo.** `lossO → tiro rival ≤ 15 s`
**Unidad:** pérdidas/partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Marcamos las pérdidas en juego que preceden a un tiro rival en la misma posesión y dentro de quince segundos. El plazo concentra el análisis en el riesgo inmediato; no prueba que toda la responsabilidad corresponda al jugador que perdió.

**Alcance.** Asociación descriptiva, no causal.

#### `perdida_letal` · Pérdida letal

**Definición técnica.** Pérdida costosa cuyo tiro rival en ≤15 s terminó en gol.

**Cálculo o campo.** `lossO → gol rival ≤ 15 s`
**Unidad:** pérdidas (total ventana). **Fuente:** eventos.

**Sentido futbolístico y construcción.** Dentro de las pérdidas costosas distinguimos las que acabaron en gol. Es útil para localizar episodios decisivos, pero el resultado también depende del remate y del portero, y suele haber pocos casos.

**Alcance.** Asociación descriptiva.

#### `tipo_error` · Tipo de error

**Definición técnica.** No forzado (pase fallado con xPass≥0.80 sin presión); bajo presión; decisión arriesgada (pase adelante con xPass<0.50); duelo perdido; aislado (360: 0 compañeros ≤10 yd).

**Cálculo o campo.** `reglas en orden`
**Unidad:** categoría. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Usamos presión, dificultad del pase, dirección, duelo y apoyos visibles para clasificar el contexto de la pérdida. Las reglas se aplican en orden para evitar contar una acción en varias clases; la etiqueta describe señales observables, no la intención del jugador.

**Alcance.** 360 solo ve jugadores visibles.

#### `rec_tiro` · Posesiones con tiro tras recuperación

**Definición técnica.** Posesiones que terminan en tiro en los 15 s siguientes a una recuperación en campo rival (x≥60) o alta (x≥80).

**Cálculo o campo.** `posesiones con tiro ≤15 s tras robo / partidos`
**Unidad:** posesiones por partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Unimos el lugar del robo con un remate posterior cercano en el tiempo. Así distinguimos recuperar arriba de convertir esa recuperación en una ocasión; son preguntas diferentes.

**Alcance.** Distinta de presion_alta_tiros (team-stats).

#### `jugada_peligrosa_concedida` · Jugada peligrosa concedida

**Definición técnica.** Posesión rival con al menos un tiro; orden: gol, xG de la posesión, OBV máximo, fecha.

**Cálculo o campo.** `xG_pos = 1-Π(1-xg)`
**Unidad:** jugadas. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Seleccionamos posesiones rivales que incluyen tiro y las ordenamos para revisar episodios concretos. Combinar probabilidades de una misma posesión evita tratar dos remates consecutivos como dos goles seguros posibles en esa secuencia.

**Alcance.** Etiquetas: penal, balón parado, transición, ataque establecido.

#### `xg_concedido` · xG concedido

**Definición técnica.** Suma de xG de los tiros rivales (por tipo de jugada).

**Cálculo o campo.** `Σ xG rival`
**Unidad:** xG por partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Sumamos la calidad estimada de las ocasiones rivales para describir el peligro permitido. Permite analizar la defensa aunque el rival falle; no mide por sí solo todas las acciones defensivas previas.

**Alcance.** Sin penales salvo que se indique.

#### `x_media_tiros_concedidos` · Distancia de los tiros concedidos

**Definición técnica.** x media de los tiros rivales vista desde nuestra portería (x=0); menor = más cerca de nuestro arco.

**Cálculo o campo.** `media x (marco del protagonista)`
**Unidad:** yardas. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Miramos a qué altura del campo remata el rival respecto de nuestra portería. Una coordenada menor indica remates más cercanos en el eje longitudinal; no equivale a la distancia euclídea al centro del arco.

**Alcance.** Marco del protagonista.

### 6.3. Presión y defensa

#### `fase_presion` · Fase de presión

**Definición técnica.** Por ubicación del balón rival en nuestro marco: alta x≥80, bloque medio 40–80, bajo x<40.

**Cálculo o campo.** `presiones+acciones def. / acciones rivales en la banda`
**Unidad:** por acción. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Agrupamos la actividad defensiva según dónde está el balón rival. Esto permite distinguir presionar arriba de defender cerca del área y relacionar las acciones defensivas con la actividad rival disponible en cada zona.

**Alcance.** Marco propio.

#### `ppda` · PPDA

**Definición técnica.** Pases rivales permitidos por acción defensiva propia en campo de presión.

**Cálculo o campo.** `pases rivales x<72 (su marco) / (intercepción+falta+entrada+regate superado) x≥48`
**Unidad:** pases. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Contamos cuántos pases permite el equipo antes de una acción defensiva en la zona de presión. Un valor bajo indica intervenciones más frecuentes respecto a la circulación rival; no demuestra por sí solo recuperaciones ni coordinación colectiva.

**Alcance.** Menor = más presión. Con el regate superado correlaciona r=0.98 con el PPDA de StatsBomb.

#### `contrapresion` · Contrapresión

**Definición técnica.** Presiones marcadas como contrapresión por StatsBomb (en los 5 s siguientes a perder el balón).

**Cálculo o campo.** `presiones con counterpress`
**Unidad:** presiones/partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Contamos las presiones que el proveedor marca inmediatamente después de perder. Mide la actividad de reacción; recuperar realmente dentro de ese plazo se estudia con contrapresión efectiva.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `contrapresion_efectiva` · Contrapresión efectiva

**Definición técnica.** Tras una pérdida propia en juego, la posesión rival dura ≤5 s y acaba en robo propio.

**Cálculo o campo.** `pérdidas recuperadas ≤ 5 s / pérdidas`
**Unidad:** % de pérdidas. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Comprobamos si el equipo vuelve a recuperar en cinco segundos tras perder en juego. Dividir por las pérdidas permite comparar equipos con distintas oportunidades de reaccionar; es un resultado observado, no una demostración de intención táctica.

**Alcance.** Solo pérdidas en juego.

#### `rec_campo_rival` · Robos en campo rival

**Definición técnica.** Recuperaciones en juego con x≥60.

**Cálculo o campo.** `robo x ≥ 60`
**Unidad:** robos/partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Situamos el robo más allá de medio campo para saber cuántas posesiones empiezan cerca del rival. El conteo no exige remate posterior y por eso se diferencia de las ocasiones tras recuperación.

**Alcance.** Igual al simulador.

#### `rec_alta` · Robos altos

**Definición técnica.** Recuperaciones en juego con x≥80.

**Cálculo o campo.** `robo x ≥ 80`
**Unidad:** robos/partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Exigimos que el robo ocurra en el último tercio. Es una definición más exigente de altura que recuperar en campo rival; por sí sola no informa del éxito de la jugada siguiente.

**Alcance.** Conteo de recuperaciones altas; no equivale a tiros tras robo alto del proveedor.

### 6.4. Jugadores, contexto y resultados

#### `minutos_jugador` · Minutos de un jugador

**Definición técnica.** Minutos jugados por un futbolista y su parte de los minutos del equipo en la ventana (alineaciones y cambios).

**Cálculo o campo.** `minutos del jugador / minutos del equipo`
**Unidad:** % de los minutos del equipo. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Relacionamos el tiempo jugado de cada futbolista con los minutos del equipo para reconocer continuidad y núcleo de participación. El tiempo disponible no explica lesiones, sanciones ni el nivel de rendimiento individual.

**Alcance.** Descriptivo: no distingue lesiones ni suspensiones.

#### `formacion` · Formación inicial

**Definición técnica.** Esquema con el que el equipo inicia el partido, según la alineación registrada.

**Cálculo o campo.** `partidos con la formación / partidos`
**Unidad:** % de los partidos. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Contamos los esquemas iniciales registrados para describir la estructura de partida más habitual. Un 4-2-3-1 puede transformarse con o sin balón; las posiciones y el 360 estudian otras facetas de esa organización.

**Alcance.** La formación registrada no describe el comportamiento durante el juego.

#### `puntos` · Puntos por partido

**Definición técnica.** Puntos reales del partido: victoria 3, empate 1, derrota 0 (la tanda de penales no cuenta).

**Cálculo o campo.** `Σ puntos / partidos`
**Unidad:** puntos por partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Asignamos tres puntos a la victoria, uno al empate y cero a la derrota para resumir resultados por partido. La media permite comparar ventanas de distinta duración sin sumar títulos ni adjudicar puntos por una tanda.

**Alcance.** Resultado en tiempo regular.

#### `xg_dif` · Diferencia de xG

**Definición técnica.** xG sin penales a favor menos xG sin penales en contra, por partido.

**Cálculo o campo.** `xg − xga`
**Unidad:** xG por partido. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Restamos el peligro concedido al generado para describir el balance de ocasiones. Un valor positivo muestra ventaja en calidad acumulada, aunque el marcador real pueda ser desfavorable.

**Alcance.** Usa el xG de team-stats; ver xg y xga.

#### `salida_portero` · Salida larga del portero (eventos)

**Definición técnica.** Porcentaje de saques de puerta largos y de pases largos del portero en juego, contados desde los eventos (largo = 35 yd o más).

**Cálculo o campo.** `saques o pases largos / saques o pases del portero`
**Unidad:** % de acciones. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Identificamos entregas largas del portero desde eventos para explorar cuánto recurre a superar distancia desde el inicio. Usamos un umbral explícito y mantenemos esta medida separada de la proporción suministrada en team-stats.

**Alcance.** Distinta de saque_largo (team-stats, proporción del portero).

#### `rival_tier` · Nivel del rival

**Definición técnica.** Rango del rival por diferencia de xG por partido en su temporada: 1–6 alto, 7–12 medio, 13–18 bajo (temporada previa si tiene <10 partidos).

**Cálculo o campo.** `rango team_season_xgd_pg`
**Unidad:** categoría. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Ordenamos a los rivales por su balance de ocasiones en la temporada y formamos tres niveles. El criterio contextualiza la dificultad, pero incluye encuentros contra el propio protagonista y no es una clasificación independiente de él.

**Alcance.** Circular: el rival también jugó contra nosotros.

#### `minuto` · Tramo de minuto

**Definición técnica.** 0–15, 16–30, 31–45+, 46–60, 61–75, 76–90+ y prórroga; sin tanda de penales.

**Cálculo o campo.** `minute_bin`
**Unidad:** tramo. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Agrupamos acciones en tramos del partido para ver cuándo aparecen los patrones. El añadido se incorpora al tramo final de cada tiempo; los tramos pueden contener distinta cantidad de juego y no son una tasa por minuto efectivo.

**Alcance.** El añadido cuenta en el último tramo.

#### `marcador` · Marcador

**Definición técnica.** Estado del marcador antes de cada acción, visto por el equipo protagonista.

**Cálculo o campo.** `ganando / empatando / perdiendo`
**Unidad:** categoría. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Tomamos el resultado justo antes de la acción para distinguir comportamientos cuando se gana, empata o pierde. Evitamos que el gol que cierra la jugada cambie retrospectivamente el contexto de su inicio.

**Alcance.** Se excluyen autogoles no registrados.

#### `obv` · OBV

**Definición técnica.** Valor añadido por acción (On-Ball Value) de StatsBomb.

**Cálculo o campo.** `Σ obv_total_net`
**Unidad:** goles esperados. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Agregamos el valor que el proveedor asigna a las acciones con balón para estudiar aportaciones anteriores al remate. El proyecto utiliza esos valores; no entrena aquí el modelo de valoración ni interpreta la suma como goles reales.

**Alcance.** Validado contra team_match_obv.

#### `ventana` · Ventana

**Definición técnica.** Oficial (≤2025-06-30, Ap2021–Cl2025), epílogo o temprano. Las conclusiones solo usan la oficial.

**Cálculo o campo.** `fecha ≤ 2025-06-30`
**Unidad:** categoría. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Separamos periodos temporales para mantener una población de estudio coherente. Las observaciones posteriores o tempranas sirven como contexto y no se mezclan con la conclusión principal.

**Alcance.** Lo demás lleva la insignia "Fuera de ventana". Los percentiles de las conclusiones comparan contra equipos-temporada de la ventana oficial; solo el explorador usa la referencia ampliada (y lo dice).

#### `encogimiento` · Encogimiento hacia el prior

**Definición técnica.** Promedio corregido por muestra chica hacia la carrera previa del DT o la liga; intervalo del 80%.

**Cálculo o campo.** `(n·x̄ + 8·μ0)/(n+8)`
**Unidad:** según métrica. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Acercamos los promedios con pocos partidos a una referencia previa para no exagerar un debut atípico. Ocho partidos equivalentes determinan el peso de esa referencia; al crecer la muestra domina cada vez más lo observado.

**Alcance.** Confianza: <5 muy baja, 5–11 baja, 12–24 media, ≥25 alta.

#### `consistencia` · Consistencia

**Definición técnica.** Qué tanto se repite el rendimiento entre partidos: dispersión entre partidos y banda de ruido por remuestreo (bootstrap, 80%).

**Cálculo o campo.** `IQR entre partidos; bootstrap 80%`
**Unidad:** según métrica. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Miramos cuánto varía la medida entre partidos y cuánto cambia su resumen al remuestrear. Una dispersión pequeña describe regularidad observada, sin prometer que se repita frente a cualquier rival.

**Alcance.** Descriptivo; no implica estabilidad causal.

#### `xpts` · Puntos esperados (xPts)

**Definición técnica.** Puntos promedio si cada posesión con tiro se repitiera: 20,000 sorteos por partido con la probabilidad de gol de cada posesión.

**Cálculo o campo.** `3·P(G) + P(E)`
**Unidad:** puntos por partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Repetimos probabilísticamente las ocasiones del partido para traducirlas a puntos medios: tres por victoria y uno por empate. Conservamos los tiros observados, por lo que el resultado interpreta ese partido y no anticipa uno futuro.

**Alcance.** Penales con su xG; autogoles fijos.

#### `resultado_sorpresivo` · Resultado sorpresivo

**Definición técnica.** Partido cuyo resultado real tenía menos de 20% de probabilidad en la repetición con xG.

**Cálculo o campo.** `P(resultado real) < 0.20`
**Unidad:** partidos. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Señalamos resultados reales poco frecuentes en la repetición de sus ocasiones. El corte del 20% facilita revisar casos llamativos; no invalida el marcador ni certifica que alguien mereciera ganar.

**Alcance.** Interpretativo, no pronóstico.

#### `xi_base` · XI base

**Definición técnica.** Los jugadores con más minutos en la ventana, por posición.

**Cálculo o campo.** `share de minutos`
**Unidad:** jugadores. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Seleccionamos a los jugadores de mayor participación por posición para representar una estructura habitual. Es un resumen del periodo y puede combinar futbolistas que no coincidieron siempre en el mismo once.

**Alcance.** Roles en español; posiciones de StatsBomb.

#### `rotacion` · Rotación

**Definición técnica.** Cambios promedio en el XI titular respecto del partido anterior.

**Cálculo o campo.** `Δ XI entre partidos consecutivos`
**Unidad:** jugadores por partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Comparamos titulares entre partidos consecutivos para medir cuánto cambia la alineación. La variación observada combina decisiones y disponibilidad; no equivale automáticamente a una política voluntaria de rotación.

**Alcance.** Incluye bajas no observadas.

#### `cambios` · Momento de los cambios

**Definición técnica.** Minuto medio de cada sustitución y su reparto por marcador.

**Cálculo o campo.** `minuto de Substitution`
**Unidad:** minuto. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Resumimos cuándo se hacen las sustituciones y con qué marcador. Esto describe la gestión del partido sin poder conocer todas las razones médicas o tácticas de cada cambio.

**Alcance.** Se excluyen cambios por lesión no marcados.

#### `impacto_cambio` · Impacto descriptivo del cambio

**Definición técnica.** Δ xG, OBV y field tilt en los 15 min posteriores contra los 15 previos (±2 min excluidos, mismo marcador).

**Cálculo o campo.** `después − antes`
**Unidad:** según métrica. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Comparamos ventanas cercanas antes y después de sustituir, dejando un margen de dos minutos y conservando el marcador. Así reducimos mezclas evidentes de contexto, pero siguen cambiando el rival, el tiempo y otros factores: la diferencia no identifica un efecto causal.

**Alcance.** Descriptivo, nunca "efecto".

### 6.5. Balón parado

#### `bp_peligro` · Balón parado de peligro

**Definición técnica.** Todos los córners; tiros libres con reanudación en x≥80; saques de banda con x≥90 (solo análisis).

**Cálculo o campo.** `is_danger_sp`
**Unidad:** jugadas. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Seleccionamos córners y reanudaciones suficientemente cercanas al arco para estudiar balón parado ofensivo relevante. Los umbrales de faltas y bandas hacen la selección reproducible; una reanudación fuera de ellos no es necesariamente inofensiva.

**Alcance.** Zonas: área, remate, área chica.

#### `bp_ofensivo` · Balón parado a favor

**Definición técnica.** xG generado en posesiones nacidas de un balón parado de peligro.

**Cálculo o campo.** `Σ [1−Π(1−xG_tiro)] de posesiones propias de balón parado de peligro / partidos válidos; sin penales`
**Unidad:** xG por partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Combinamos los tiros sin penal de cada posesión para estimar su probabilidad de producir al menos un gol, y sumamos esas probabilidades por partido. Mantener la posesión permite incluir segundas jugadas, aunque el remate ya no sea el primer contacto, sin sumar sin límite los tiros sucesivos de la misma posesión.

**Alcance.** Incluye segundas jugadas de la posesión.

#### `bp_defensivo` · Balón parado en contra

**Definición técnica.** xG concedido en posesiones rivales nacidas de un balón parado de peligro.

**Cálculo o campo.** `Σ [1−Π(1−xG_tiro)] de posesiones rivales de balón parado de peligro / partidos válidos; sin penales`
**Unidad:** xG por partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Aplicamos al rival el mismo filtro de reanudaciones para medir el peligro concedido de forma comparable. La suma informa sobre ocasiones; identificar el tipo de marcaje requiere posiciones visibles y sigue siendo inferencial.

**Alcance.** Marcaje inferido con 360.

#### `bp_diferencial` · Diferencial de balón parado

**Definición técnica.** xG a favor menos xG en contra en balón parado de peligro.

**Cálculo o campo.** `bp_ofensivo − bp_defensivo`
**Unidad:** xG por partido. **Fuente:** eventos.

**Sentido futbolístico y construcción.** Restamos el peligro concedido al generado en esas reanudaciones. Un saldo positivo resume ventaja en ocasiones de balón parado, no una diferencia garantizada de goles.

**Alcance.** KPI 7.

### 6.6. Estilo suministrado

Estas medidas se toman de estadísticas por equipo-partido; el proyecto no vuelve a entrenar los modelos del proveedor. La señal de contrapresión completa las catorce: para estilo se usa `team_match_counterpressures`, mientras la ficha `contrapresion` del glosario explica el conteo desde eventos marcados `counterpress`. Se conserva la procedencia de cada uso. Los percentiles de PPDA y xG concedido se invierten para que valores altos indiquen menos pases permitidos y menos peligro concedido, respectivamente.

#### `posesion` · Posesión del balón

**Definición técnica.** Porcentaje de la posesión del partido (team_match_possession).

**Cálculo o campo.** `team_match_possession`
**Unidad:** % del balón. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Usamos la proporción de posesión suministrada para describir cuánto balón tiene el equipo. Su percentil muestra dónde se sitúa frente a la referencia, pero tener más balón no implica atacar mejor.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `verticalidad` · Verticalidad

**Definición técnica.** Proporción del avance del balón que va directo hacia la portería rival (team_match_directness).

**Cálculo o campo.** `team_match_directness`
**Unidad:** proporción. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Usamos la medida del proveedor sobre avance directo hacia el arco. Describe la dirección del juego; un equipo puede avanzar de manera directa pero hacerlo lentamente, por lo que la interpretamos junto al ritmo.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `ritmo` · Velocidad del ataque

**Definición técnica.** Velocidad media con la que el balón avanza hacia la portería rival (team_match_pace_towards_goal).

**Cálculo o campo.** `team_match_pace_towards_goal`
**Unidad:** m/s. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Usamos la velocidad de avance hacia portería para distinguir ataques pausados de ataques rápidos. No es la velocidad física de los jugadores ni implica jugar al contragolpe en todas las posesiones.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `linea` · Altura de la defensa

**Definición técnica.** Distancia media de las acciones defensivas a la propia portería (team_match_defensive_distance).

**Cálculo o campo.** `team_match_defensive_distance`
**Unidad:** m. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Tomamos la distancia de las acciones defensivas al arco propio como señal de altura defensiva. Refleja dónde actúa el equipo; la ubicación de sus últimos defensores se estudia aparte con cuadros 360.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `volumen_presion` · Volumen de presión

**Definición técnica.** Presiones por partido ajustadas por la posesión rival (team_match_pressures_adj).

**Cálculo o campo.** `team_match_pressures_adj`
**Unidad:** presiones/partido. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Usamos presiones ajustadas por posesión rival para aproximar cuánto interviene el equipo cuando puede presionar. Lo combinamos con PPDA y contrapresión porque mucho volumen no garantiza impedir la circulación.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `presion` · PPDA de team-stats (pases del rival por acción defensiva)

**Definición técnica.** PPDA de StatsBomb por partido; para el percentil se invierte: un percentil alto es un PPDA bajo (el rival hace pocos pases antes de que el equipo actúe).

**Cálculo o campo.** `team_match_ppda`
**Unidad:** pases por acción defensiva (menos = más presión). **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Transformamos el PPDA suministrado a una escala en la que un percentil alto significa permitir menos pases por intervención. Invertir el orden facilita leerlo con otras señales defensivas sin cambiar la magnitud original.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `saque_largo` · Saque largo del portero

**Definición técnica.** Proporción de pases largos del portero (team_match_gk_long_pass_ratio).

**Cálculo o campo.** `team_match_gk_long_pass_ratio`
**Unidad:** proporción. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Usamos la proporción suministrada de pases largos del portero para caracterizar su preferencia por envío largo. Es un indicador de elección, no de precisión ni de éxito del receptor.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `centros` · Centros al área

**Definición técnica.** Centros al área por partido (team_match_crosses_into_box).

**Cálculo o campo.** `team_match_crosses_into_box`
**Unidad:** centros/partido. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Contamos los centros al área por partido informados por el proveedor para describir la vía de ataque. Un valor alto indica frecuencia de uso; la calidad de las ocasiones requiere mirar los remates generados.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `contragolpe` · Tiros al contragolpe

**Definición técnica.** Tiros tras contraataque por partido (team_match_counter_attacking_shots).

**Cálculo o campo.** `team_match_counter_attacking_shots`
**Unidad:** tiros/partido. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Usamos los tiros de contraataque del proveedor como señal de amenaza rápida. La clasificación del proveedor se conserva separada de la regla local de recuperación y tiro dentro de quince segundos.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `presion_alta_tiros` · Tiros tras robo alto

**Definición técnica.** Tiros en los segundos siguientes a un robo alto (team_match_high_press_shots).

**Cálculo o campo.** `team_match_high_press_shots`
**Unidad:** tiros/partido. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Usamos los remates tras robo alto del proveedor para describir peligro generado desde la recuperación avanzada. No es un conteo de todos los robos altos ni sustituye la definición local de posesiones con tiro tras recuperación.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `xg` · xG a favor

**Definición técnica.** Goles esperados sin penales por partido (team_match_np_xg).

**Cálculo o campo.** `team_match_np_xg`
**Unidad:** xG por partido. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Tomamos los goles esperados sin penal del proveedor por partido para describir creación de ocasiones. El valor suma calidad estimada, de modo que varias ocasiones pueden superar un gol esperado sin que haya ocurrido un gol.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `xga` · xG en contra

**Definición técnica.** Goles esperados sin penales concedidos por partido (team_match_np_xg_conceded); para el percentil se invierte (menor = más sólido).

**Cálculo o campo.** `team_match_np_xg_conceded`
**Unidad:** xG por partido. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Tomamos el peligro sin penal permitido al rival y ordenamos su percentil en sentido favorable: menos concesión equivale a mayor solidez. El resultado depende también de la calidad de los oponentes.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

#### `bp_xg` · xG a balón parado

**Definición técnica.** Goles esperados de jugadas a balón parado por partido (team_match_sp_xg).

**Cálculo o campo.** `team_match_sp_xg`
**Unidad:** xG por partido. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Usamos el xG de balón parado suministrado como rasgo general de estilo. No lo sustituimos por el filtro local de reanudaciones de peligro, porque las poblaciones y clasificaciones pueden diferir.

**Alcance.** En etiquetas y mapa se usa su percentil frente a la liga (0–100).

### 6.7. Identidad

#### `vel_ataque` · Velocidad del ataque (eje del mapa)

**Definición técnica.** Eje x del mapa ofensivo: media de los percentiles de velocidad hacia portería y tiros al contragolpe.

**Cálculo o campo.** `round((ritmo + contragolpe) / 2)`
**Unidad:** percentil 0–100. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Combinamos los percentiles de ritmo y remates de contraataque para colocar al equipo en un mapa de ataque. El promedio es un eje descriptivo de estilo, no una velocidad física medida.

**Alcance.** Señal compuesta; la tarjeta ofensiva sale del cuadrante.

#### `intensidad_presion` · Intensidad de presión (eje del mapa)

**Definición técnica.** Eje y del mapa defensivo: media de los percentiles de volumen de presión, PPDA invertido (alto = deja pocos pases por acción defensiva) y contrapresión.

**Cálculo o campo.** `round((volumen_presion + presion + contrapresion) / 3)`
**Unidad:** percentil 0–100. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Promediamos volumen, PPDA orientado favorablemente y contrapresión para resumir tres señales complementarias. El promedio puede ocultar desacuerdos, por eso la etiqueta defensiva también consulta el perfil de presión.

**Alcance.** Señal compuesta: si volumen y PPDA discrepan, manda el perfil de presión.

#### `perfil_presion` · Perfil de presión (regla de coherencia)

**Definición técnica.** Volumen, PPDA y contrapresión nunca cuentan historias opuestas. Si el volumen es ≥65 y el PPDA invertido ≤45 (con contrapresión <75), el equipo "presiona mucho, deja jugar" y la tarjeta es "Línea alta: presiona mucho, deja jugar" o "Línea baja: presiona mucho, deja jugar". Si el volumen es ≤45 y el PPDA invertido ≥65, la presión es selectiva: "Línea alta, presión selectiva" o "Línea baja, presión selectiva". Ese nombre sustituye al del cuadrante; los nombres de cuadrante solo hablan de la altura de la línea y de la intensidad combinada, nunca del volumen. "Presión asfixiante" exige las tres señales altas y "Espera al rival" las tres bajas con línea baja.

**Cálculo o campo.** `sin_robo: vol≥65, ppda≤45, cp<75 · selectiva: vol≤45, ppda≥65 · asfixiante: vol≥75, ppda≥60, cp≥50 · espera: vol≤30, ppda≤40, cp≤50, línea≤40`
**Unidad:** categoría. **Fuente:** team-stats.

**Sentido futbolístico y construcción.** Comprobamos que las señales defensivas sostengan el texto de la etiqueta. Por ejemplo, mucho volumen con PPDA poco favorable se describe como presionar mucho y dejar jugar; evita llamar asfixiante a una presión solo por su frecuencia.

**Alcance.** Cada etiqueta declara lo que afirma sobre los percentiles; la auditoría rechaza las que no se sostienen.

### 6.8. Geometría visible 360

#### `vigilancias` · Vigilancias (defensa de resguardo)

**Definición técnica.** Al robo rival tras nuestra pérdida: jugadores propios visibles por detrás del balón.

**Cálculo o campo.** `conteo en el cuadro 360 del robo`
**Unidad:** jugadores. **Fuente:** 360.

**Sentido futbolístico y construcción.** Contamos compañeros visibles detrás del balón cuando el rival recupera para aproximar la protección ante la transición. Estar detrás aporta cobertura potencial, pero la cámara puede ocultar jugadores y el conteo no describe sus duelos ni distancias.

**Alcance.** Cota inferior: solo jugadores visibles en la toma.

#### `vigilancias_bajas` · Pérdidas con pocas vigilancias

**Definición técnica.** Porcentaje de pérdidas en juego con 2 o menos jugadores propios visibles detrás del balón al robo rival.

**Cálculo o campo.** `vigilancias ≤ 2`
**Unidad:** % de pérdidas. **Fuente:** 360.

**Sentido futbolístico y construcción.** Marcamos las pérdidas con dos o menos jugadores visibles de resguardo para localizar episodios de exposición. La proporción usa observaciones válidas con cobertura; un jugador fuera de cámara no debe interpretarse automáticamente como ausente.

**Alcance.** Cota inferior: solo jugadores visibles en la toma.

#### `altura_linea` · Altura de la línea

**Definición técnica.** x media de los 3 jugadores de campo más retrasados visibles.

**Cálculo o campo.** `media x de los 3 más profundos`
**Unidad:** yardas. **Fuente:** 360.

**Sentido futbolístico y construcción.** Promediamos los tres jugadores de campo visibles más retrasados para estimar la última línea. Usar varios jugadores reduce la influencia de una posición aislada; el filtro de visibilidad no convierte la toma en seguimiento completo.

**Alcance.** Cuadros con ≥70% de la región visible.

#### `bloque_360` · Forma del bloque

**Definición técnica.** Con el rival en posesión establecida: altura de la última línea, largo, ancho y área (envolvente convexa) del bloque, por zona del balón.

**Cálculo o campo.** `convex hull, extremos x/y`
**Unidad:** yardas / yd². **Fuente:** 360.

**Sentido futbolístico y construcción.** Medimos extensión y forma del grupo visible alrededor del balón durante posesión rival establecida. La región de interés y el mínimo de jugadores hacen más comparables las tomas, pero solo describen la parte del bloque observada.

**Alcance.** Región de 25 yd detrás, 10 delante y ±25 a lo ancho del balón; ≥7 visibles.

#### `rompe_lineas` · Pases que rompen líneas

**Definición técnica.** Pases propios completados hacia adelante que superan rivales visibles (packing, cota inferior) o marcados line_breaking_pass.

**Cálculo o campo.** `rivales con x0<x<x1`
**Unidad:** rivales superados por pase. **Fuente:** 360.

**Sentido futbolístico y construcción.** Contamos rivales visibles entre el inicio y el final de un pase hacia delante, o consultamos la marca del proveedor. Aproxima cuántos oponentes deja atrás el balón, sin reconstruir todas las líneas tácticas ni los movimientos fuera de cámara.

**Alcance.** Cota inferior: solo jugadores visibles en la toma.

#### `presion_360` · Presión coordinada

**Definición técnica.** En cada presión propia: compañeros a ≤10 yd del balón y opciones libres del rival (≤15 yd del balón y a >3 yd de cualquier defensor).

**Cálculo o campo.** `conteos en el cuadro`
**Unidad:** jugadores. **Fuente:** 360.

**Sentido futbolístico y construcción.** Contamos apoyos próximos a quien presiona y opciones rivales libres cercanas al balón. Esto añade contexto de coordinación a la presión individual; una opción geométricamente libre no garantiza que el pase sea viable.

**Alcance.** Cota inferior: solo jugadores visibles en la toma.

#### `corner_def` · Organización en córner rival

**Definición técnica.** Defensores en área y área chica, emparejamiento (atacantes con un defensor a ≤1.5 yd) y tipo de marca inferido: zonal, mixta o al hombre.

**Cálculo o campo.** `índice de emparejamiento`
**Unidad:** categoría. **Fuente:** 360.

**Sentido futbolístico y construcción.** Relacionamos distancias entre atacantes y defensores para inferir organización en córner. La proximidad sugiere emparejamiento, pero una foto no prueba la instrucción de marcar al hombre, en zona o de forma mixta.

**Alcance.** Tipo de marca inferido; tentativo.

#### `contexto_error` · Contexto del error

**Definición técnica.** En la última acción antes de perder: apoyos a ≤10 yd, rivales a ≤5 yd, distancia al defensor más cercano, xPass y presión.

**Cálculo o campo.** `conteos en el cuadro`
**Unidad:** jugadores. **Fuente:** 360.

**Sentido futbolístico y construcción.** Observamos apoyos, oponentes cercanos, dificultad del pase y presión en la última acción antes de perder. Sirve para interpretar la exigencia de la situación sin convertir una pérdida en juicio automático sobre el futbolista.

**Alcance.** Cota inferior: solo jugadores visibles en la toma.

#### `forma_cambio` · Forma antes y después del cambio

**Definición técnica.** Δ altura de línea, ancho, largo y compacidad en 15 min antes contra 15 min después de cada sustitución (±2 min excluidos, mismo marcador).

**Cálculo o campo.** `después − antes`
**Unidad:** yardas. **Fuente:** 360.

**Sentido futbolístico y construcción.** Comparamos la geometría visible antes y después de una sustitución con ventanas y marcador equivalentes. Describe si cambió la forma observada; no atribuye toda la variación al jugador entrante.

**Alcance.** Descriptivo; solo forma del equipo.

### Aclaraciones de implementación

- En balón parado, `analytics/setpieces.py` acumula `p['xg']` de las posesiones elegibles y promedia por partido. `sequences.py` construye ese campo como `1−Π(1−xG)` de los tiros sin penal: es la probabilidad combinada por posesión, no la suma simple de todos sus tiros. Por ejemplo, dos tiros de 0.20 y 0.30 producen 0.44, frente a 0.50 al sumarlos. El modelo combina las oportunidades con esa regla; no demuestra independencia real entre remates. Las tablas de remates por zona sí pueden sumar xG de tiros y por eso deben conservar su etiqueta.
- `prog` excluye la primera acción de una reanudación. El avance general exige inicio x≥48, reducción de distancia al arco ≥25% y ≥10 yd; también reconoce el pase completado al área desde fuera. Un intento no completado no cuenta como progresión lograda.
- El PPDA calculado desde eventos usa pases rivales en x<72 de su marco y acciones defensivas propias en x≥48 del propio. Incluye intercepción, falta, entrada y regate superado. El PPDA suministrado conserva su propia fuente; la correlación r=0.98 citada en Método es una comprobación interna de concordancia, no una equivalencia de todas las observaciones.
- Para el bloque 360 se exige cobertura suficiente de la región de interés (≥70%) y al menos siete jugadores visibles. La región comprende 25 yd detrás, 10 delante y ±25 de ancho alrededor del balón. La última línea utiliza tres jugadores de campo visibles retrasados; no se añaden jugadores fuera de cámara.
- En tipología de error, `frames360.classify_error` aplica esta prioridad: duelo perdido → presión marcada o rival presionando → pase fácil fallado (xPass≥0.80) → pase arriesgado hacia delante (xPass<0.50) → otro. Si el caso quedó como «otro» y el 360 muestra cero apoyos a ≤10 yd, los módulos analíticos lo reclasifican como «aislado». La cobertura disponible limita la clasificación.

## 7. Referencias, agregación e incertidumbre

Para estilo, los valores por equipo-partido se agregan en unidades equipo-temporada. La referencia oficial exige al menos diez partidos válidos por métrica. Un percentil es una posición relativa, no un porcentaje de posesiones ni probabilidad de victoria. El explorador incorpora temporadas adicionales y declara esa referencia ampliada.

Las tasas agrupadas usan suma de numeradores / suma de denominadores. Un promedio de tasas por partido da el mismo peso a cada encuentro y puede diferir. Así, el KPI de dominio territorial es 59.792%, mientras el resumen de replay informa 59.48%; se conservan sus agregaciones y no se intercambian.

Las referencias 360 dependen de los partidos con cobertura. El resultado incluye comparadores de rivales observados, agregado etiquetado como liga cuando su cobertura es completa y referencia neutral cuando hay muestra suficiente. Para vigilancias aparecen 4.48, 4.61 y 4.63 respectivamente; el P33 se interpreta dentro de esa referencia 360, no como ranking de todos los equipos posibles.

El explorador aplica `(n·x̄+8·μ0)/(n+8)`: `n` es el número de partidos, `x̄` la media observada y `μ0` la carrera previa del entrenador o la liga. Informa intervalos del 80%. Las bandas de muestra son <5 muy baja, 5–11 baja, 12–24 media y ≥25 alta. Son criterios operativos de tamaño, no garantías estadísticas. IQR es el intervalo entre los percentiles 25 y 75; bootstrap remuestrea partidos para describir la variabilidad del resumen.

## 8. Los siete KPI: contrato, cálculo y lectura

En las tasas de eventos, se suman numeradores y denominadores antes de dividir. Dominio territorial: acciones propias en último tercio / acciones de ambos en sus respectivos últimos tercios. Progresión: posesiones elegibles que alcanzan x≥80 / posesiones en juego que empiezan en x<60. Calidad: suma de xG sin penal / tiros sin penal. Contrapresión efectiva: pérdidas que terminan en recuperación propia dentro de cinco segundos / pérdidas en juego. Las proporciones se multiplican por cien cuando la unidad es porcentaje. Pérdidas costosas se divide por partidos válidos; vigilancias promedia conteos visibles válidos; balón parado aplica la fórmula por posesión descrita en sus fichas.

KPI significa indicador clave. Los cinco primeros usan eventos; el sexto usa 360; el séptimo resume balón parado desde posesiones. `n` cambia de significado según la medida y se informa con su unidad. `ref_pct` conserva el orden original; `pct_bueno` lo invierte cuando menos es favorable. En pérdidas costosas, P33.3 original equivale a 66.7 en orientación favorable.

| Indicador | Resultado | Base de cálculo | Referencia favorable |
|---|---:|---|---:|
| Dominio territorial | 59.792 % | 40,763 acciones en último tercio | 98.6 |
| Progresión limpia | 36.8333 % | 4,762 posesiones elegibles | 97.2 |
| Calidad de ocasión | 0.1153 xG/tiro | 1,196 tiros sin penal | 98.6 |
| Contrapresión efectiva | 13.4185 % | 4,695 pérdidas en juego | 45.8 |
| Pérdidas costosas por partido | 2.7582 por partido | 91 partidos | 66.7 |
| Vigilancias 360 | 4.55 jugadores visibles | 2,488 observaciones 360 válidas de 4,285 enlazadas | 33 |
| Diferencial de balón parado | 0.0676 xG/partido | 91 partidos | No disponible |

El semáforo compara partidos del equipo consigo mismo: cortes P33/P67, mínimo doce partidos. Verde es el tramo favorable al indicador; rojo, el desfavorable. No son categorías de victoria/derrota. Los empates de valor pueden dejar grupos desiguales: en pérdidas costosas hay 42 partidos verdes, ninguno ámbar y 49 rojos, sin imputar puntos al grupo vacío.

| KPI | Corte P33 | Corte P67 | Partidos verde / ámbar / rojo | Puntos/partido verde / ámbar / rojo |
|---|---:|---:|---|---|
| Dominio territorial | 54.7871 | 69.2948 | 30 / 31 / 30 | 1.73 / 1.94 / 2.13 |
| Progresión limpia | 32.0528 | 42.931 | 30 / 31 / 30 | 1.8 / 2.03 / 1.97 |
| Calidad de ocasión | 0.0846 | 0.1213 | 30 / 31 / 30 | 2.53 / 2.13 / 1.13 |
| Contrapresión efectiva | 11.2207 | 16.0 | 31 / 30 / 30 | 1.61 / 1.93 / 2.27 |
| Pérdidas costosas por partido | 2.0 | 3.0 | 42 / 0 / 49 | 2.17 / s/d / 1.73 |
| Vigilancias 360 | 4.27 | 4.626 | 30 / 30 / 31 | 1.87 / 1.83 / 2.1 |
| Diferencial de balón parado | -0.091 | 0.1847 | 30 / 31 / 30 | 2.23 / 1.81 / 1.77 |

La calidad de ocasión se asocia con 2.53 puntos/partido en verde y 1.13 en rojo (30 partidos por grupo). El dominio territorial presenta 1.73 frente a 2.13. Mostrar ambos evita seleccionar solo relaciones favorables: más dominio no implica automáticamente más puntos y el contexto puede invertir una asociación.

El balance de balón parado es 0.3470−0.2794=+0.0676 xG/partido; intervalo del 80% [0.0070, 0.1279]. No tiene percentil disponible. Los valores en xG se muestran en su escala original y no se convierten artificialmente en porcentajes.

## 9. Contexto y muestras pequeñas

El contexto desglosa por localía, nivel rival, marcador previo, tramo de minuto, torneo, fase, ventana y etapa del club. Cada hecho conserva numerador, denominador, partidos y advertencias; “resto” excluye el estrato observado.

El explorador encoge con `n0=8` e intervalo 80%. Confianza: muy baja `<5`, baja `5–11`, media `12–24`, alta `≥25`; menos de 12 es muestra chica.

## 10. Replay de xG

Por partido se agrupan tiros por posesión y se usa `1-Π(1-xG)`. Hay 20,000 sorteos con semilla `match_id`, penales con su xG, autogoles fijos y tandas excluidas. `xPts=3P(V)+P(E)`. Resultado sorpresivo: probabilidad real <20%. Es interpretación de ocasiones, no pronóstico.

## 11. Resultados: América de Jardine

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
11. KPI: dominio, progresión, calidad de ocasión y pérdidas costosas destacan en orientación favorable; vigilancias requiere su referencia 360.
12. Epílogo: 1.68 puntos y 1.70 xPts, fuera de ventana.

Replay oficial: 12 resultados sorpresivos, 61.75% del xG total y 59.48% de field tilt.

### Lecturas con límite

- Local: 2.27 puntos/partido contra 1.61 en el resto; no controla rival.
- Rival débil: field tilt 70.2% contra 56.1%; tier circular.
- Perdiendo: field tilt 74.1% contra 57.4%; respuesta, no intención.
- Liguilla: 1.06 xG/partido contra 1.61; muestras/rivales distintos.
- 45% de inicios en 4-2-3-1 y cinco formaciones; registro no forma dinámica.
- 4.6 cambios/partido; primero cerca del 57; asociación descriptiva.

## 12. Trazabilidad de interfaz

| Vista | Artefactos | Contenido |
|---|---|---|
| Historia | story+analysis+glossary | 12 capítulos y evidencia |
| Almada | story/almada+entidades | etapa previa y muestra temprana |
| Partidos | matches+replay+xg_grid | xG, xPts, momentos, veredicto |
| Entrenador | entity+analysis+kpis | identidad, contexto, jugadores |
| Explorador | explorer.json | 19 equipos, 102 DTs, intervalos |
| Laboratorio | model+parser | simulación/jugada generada |
| Método | `/api/framework` | 77 definiciones y umbrales |

Método muestra definición, unidad y límites; en modo DT añade fórmula, fuente y umbrales. `#metodo/{id}` enfoca una definición.

## 13. Alcance de las conclusiones

Los resultados describen asociaciones y no identifican causalidad del entrenador. Los eventos no contienen todos los movimientos sin balón y el 360 ofrece visibilidad parcial. El nivel rival incluye partidos contra el protagonista; las etiquetas condensan comportamientos heterogéneos. Las diferencias entre estadísticas suministradas y cálculos desde eventos se conservan con su fuente y denominador. El replay interpreta ocasiones observadas y el simulador explora duelos hipotéticos.

## 14. Ejecución y comprobación del producto

Se inició FastAPI con los datos analíticos disponibles y se consultaron `/api/health`, `/api/teams`, `/api/framework`, `/api/kpis/ame_jardine`, `/api/replay/ame_jardine` y `/api/story/jardine`. Se verificaron siete KPI, 77 definiciones, 91 partidos con eventos y una historia con doce capítulos. En el laboratorio se seleccionaron Barcelona y el arquetipo y se comprobaron sus tarjetas y métricas visibles. Esta comprobación ejecuta la aplicación y sus salidas disponibles; no equivale a una nueva descarga ni a recalcular todas las fuentes.

Para servir los resultados existentes: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8011`.

Para recalcular con las fuentes completas: extracción → referencias → modelo → análisis → KPI → historias → auditoría, mediante `python -X utf8 pipeline/run.py build`. `python -X utf8 pipeline/run.py analysis` utiliza los extractos ya disponibles. Los módulos de auditoría comprueban referencias, valores, etiquetas y ventanas; no sustituyen una validación externa de las interpretaciones futbolísticas.

## 15. Fuentes internas y trazabilidad

| Contenido | Fuente consultada |
|---|---|
| Definiciones y umbrales | `pipeline/framework.py`, `pipeline/framework_defs.py`, `frontend/views/method.js` |
| Preparación | `pipeline/extract.py`, `pipeline/extract_analysis.py`, `pipeline/extract_360.py`, `pipeline/build_model.py` |
| Cálculo temático | `pipeline/analytics/`, `pipeline/build_analysis.py`, `pipeline/kpis.py` |
| Relato y evidencia | `pipeline/story*.py`, `pipeline/audit_coherence.py` |
| Resultados del caso | `model/analysis/ame_jardine.json`, `model/kpis/ame_jardine.json`, `model/replay/ame_jardine.json`, `model/story/jardine.json` |
| Perfiles de contraste | `model/model.json`, `frontend/lab.html` |
| Presentación y servicio | `app/main.py`, `frontend/views/`, `frontend/js/` |

Las cifras del HTML proceden de estos resultados; las fichas de este framework explican cómo leerlas y reconstruir su significado.
