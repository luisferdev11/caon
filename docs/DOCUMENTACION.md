# Vestidor Táctico · Documentación técnica

Cómo funciona todo: de dónde salen los datos, cómo se consumen y transforman, cómo se obtiene el estilo de juego de cada entrenador, cómo se simulan los partidos y cómo agregar equipos o entrenadores nuevos.

Demo publicada: https://claude.ai/artifact/5BFGG5xVxLiNJAoHytdXiT · Local: `uvicorn app.main:app --reload`.

---

## 0. Resumen en un párrafo

Descargamos eventos de Hudl StatsBomb (Liga MX por API y el Barcelona 2009–11 de StatsBomb Open Data). Cada partido se resume en conteos por equipo: en qué zona de la cancha y en qué fase (transición o ataque establecido) ocurre cada acción con balón, y cómo termina (pase a otra zona, tiro, falta recibida, córner, pérdida…). Agregando esos conteos por **equipo + entrenador + periodo** obtenemos una huella de su estilo. Con ella hacemos tres cosas: (1) el **plan de juego** en percentiles contra la liga, (2) un **mapa de estilos** donde cada equipo-temporada se ubica y se compara, y (3) un **motor de simulación** que enfrenta dos huellas en una cadena de Markov por zonas y lo anima jugada a jugada con 22 jugadores, respetando el reglamento. Todo se calibró contra partidos reales y un árbitro automático revisó 1.9 millones de situaciones sin infracciones.

---

## 1. Arquitectura

```
StatsBomb API (Liga MX) ─┐                                    ┌─ Plan de juego (percentiles)
                         ├─> data/cache ─> extract.py ─> data/extract ─> build_model.py ─> model/model.json ─┼─ Mapa de estilos
StatsBomb Open Data ─────┘   (crudo)      (etapa 1)      (por partido)    (etapa 2)        (agregado)          └─ engine.js: simular + coreografiar ─> index.html
                                                                                                               ↑
                                                                         validate.js · referee.js (calibración y reglamento)
```

| Archivo | Qué hace |
|---|---|
| `pipeline/statsbomb.py` | Cliente de la API (usuario y contraseña de `.env`, autenticación básica) con caché en `data/cache/`. |
| `pipeline/entities.py` | Define las entidades equipo-entrenador-periodo y sus partidos. |
| `pipeline/download.py`, `download_lineups.py`, `download_opendata.py` | Descarga eventos, alineaciones, estadísticas por partido y Open Data. |
| `pipeline/extract.py` | **Etapa 1.** Resume cada partido en conteos (un JSON por partido en `data/extract/`). |
| `pipeline/build_model.py` | **Etapa 2.** Agrega por entidad, calcula estilo, calibra métricas, construye arquetipo y mapa → `model/model.json` (ligero) + `model/entities/<id>.json` (detalle). |
| `pipeline/model_split.py` | Divide el modelo: lo que usa el simulador queda en `model.json`; temporal, personal, contexto, cobertura y crudos van a `model/entities/<id>.json`. Define la ventana de cada entidad y el alcance de la referencia de liga (`CAON_LEAGUE_SCOPE`). |
| `pipeline/build_analysis.py` | **Etapa 3.** Corre los módulos de `pipeline/analytics/` por entidad → `model/analysis/<id>.json` (≤ 400 KB c/u), `model/explorer.json`, `model/xg_grid.json`, y la auditoría de coherencia si existe. |
| `pipeline/framework.py` | Marco analítico: constantes con nombre y registro `DEFINITIONS` (lo sirve `/api/framework`). |
| `frontend/engine.js` | Motor: parámetros, cruce, simulación, coreografía. El mismo archivo corre en el navegador y en Node. |
| `frontend/index.html`, `frontend/lab.html` | Portal (historia, explorador, partidos) y laboratorio de simulación. |
| `pipeline/validate.js`, `targets.py` | Validación contra estadísticas reales. |
| `pipeline/referee.js` | Árbitro automático (reglamento). |
| `pipeline/metric_lab.py`, `clusters.py` | Laboratorio de métricas y exploración de agrupamiento. |

---

## 2. Fuentes de datos

### 2.1 StatsBomb API (Liga MX)
- Acceso: `https://data.statsbomb.com/api/...` con `USER_STATSBOMB` / `PSWD_STATSBOMB` del `.env` (HTTP Basic). Cada respuesta se guarda en `data/cache/<ruta>.json`; si ya existe no se vuelve a pedir.
- Competición 73 (Liga MX), temporadas 108 (2021/22), 235 (2022/23), 281 (2023/24), 317 (2024/25), 318 (2025/26), 351 (2026/27). **Ventana oficial del reto: 108–317** (Apertura 2021–Clausura 2025); lo posterior se marca "fuera de ventana oficial".

| Endpoint | Uso |
|---|---|
| `v4/competitions` | Lista de competiciones/temporadas. |
| `v6/competitions/73/seasons/{s}/matches` | Partidos, equipos, **entrenadores (managers)**, fechas, fase (Liguilla). |
| `v8/events/{match}` | Eventos con ubicación, posesión, patrón de juego, xG, OBV. Base de todo el modelo. |
| `v4/lineups/{match}` | Apodos y dorsales de los jugadores. |
| `v1/matches/{match}/team-stats` | +150 métricas por equipo y partido (posesión, PPDA, altura defensiva…). Base del plan de juego. |
| `v2/competitions/73/seasons/{s}/team-stats` | Estadísticas por temporada (exploración). |
| `v2/360-frames/{match}` | Exploración (prueba de concepto); no se usa en la demo final porque solo ve ~13 de 22 jugadores. |

Volumen descargado: 1,799 partidos con estadísticas, 568 con eventos completos (2.7 GB en caché).

### 2.2 StatsBomb Open Data (Barcelona 2009–11)
`https://raw.githubusercontent.com/statsbomb/open-data/master/data/` · La Liga (competición 11) temporadas 21 (2009/10) y 22 (2010/11): 68 partidos del Barcelona con eventos y alineaciones (`data/opendata/`). Licencia abierta con atribución. No trae estadísticas agregadas, por eso su estilo se calcula desde eventos (sección 7.5).

### 2.3 Uso de datos
Las bases dicen que los datos solo se usan para la competencia y se pueden presentar resultados, no datos. Por eso `model.json` contiene **agregados** y secuencias compactas seleccionadas (conteos, tasas por zona, percentiles, posiciones medias ); no se exponen los eventos crudos completos. `data/` y `.env` están en `.gitignore`.

---

## 3. Entidades: equipo + entrenador + periodo

`entities.py` define cada entidad como (equipo StatsBomb, texto del entrenador, desde, hasta, grupo):
- **Especiales** (lista `SPECIAL`): América de Jardine (tricampeonato, Apertura 2023→Apertura 2025), América de Almada, Chivas de Paunović, Gago y Milito, Atlas de Cocca (bicampeonato, jul-2021→jun-2022).
- **Entrenador actual de cada equipo**: el último entrenador que aparece en la temporada 2026/27; su tramo continuo hacia atrás (hasta que aparece otro DT) define el periodo.
- Partidos de una entidad = partidos del equipo cuyo campo `managers` contiene el entrenador dentro del periodo.
- Validación: Barcelona 2009–11 (Open Data) y el arquetipo "Autobús y contra" (configurado).

Total: 24 entidades. La identidad del entrenador sale del dato `managers` del partido, no de una lista manual.

---

## 4. Framework analítico (definiciones)

Todas las métricas, mapas y simulaciones salen de estos objetos:

| Concepto | Definición |
|---|---|
| Posesión | Eventos con el mismo `possession` id de StatsBomb. StatsBomb abre una posesión nueva en cada reanudación, aunque la reanude el mismo equipo. |
| Acción con balón | `Pass`, `Carry`, `Dribble` o `Shot` del equipo en posesión, con ubicación. |
| Zonas | Rejilla de 6 (largo) × 3 (ancho) sobre la cancha de 120×80 yardas, **siempre en la orientación del equipo que ataca** (x=120 es la portería rival). |
| Recuperación | Posesión de juego abierto (`Regular Play` o `From Counter`) que sigue a una posesión del rival. |
| Fase de transición (T) | Acciones de los primeros **10 s** de una posesión que empezó con recuperación. Todo lo demás es **ataque establecido (E)**. |
| Balón parado peligroso | Posesión `From Corner`, o `From Free Kick` cuya primera acción está en x ≥ 80. |
| Posesión administrativa | Posesión sin balón en juego (solo falta, tarjeta, lesión); se salta para saber cómo sigue el juego. |
| Supuestos | Se excluyen tandas de penales; los penales se modelan aparte; 10 yardas = 10 unidades (StatsBomb mide en yardas). |

**Desenlace de cada acción** en zona *z* y fase *f* (lo que alimenta la cadena):

| Desenlace | Cuándo |
|---|---|
| `move z→w` | La siguiente acción de la misma posesión ocurre en la zona *w* (pase o conducción; se guarda cuántas fueron conducciones). |
| `shot` | Tiro en juego abierto (con su xG). |
| `spC` / `spF` | La siguiente posesión es del mismo equipo y es córner / falta peligrosa. |
| `pen` | La siguiente posesión es un penal a favor. |
| `keepF` | Le hacen falta lejos del área: tiro libre a favor. |
| `keepT` | El rival la saca por la banda: saque de banda a favor. |
| `lossO` | Pierde en juego: la siguiente posesión es del rival en juego abierto. |
| `lossXT` / `lossXG` / `lossXF` | Pierde con balón muerto: saque de banda / de meta / tiro libre (falta propia o fuera de juego) del rival. |

Para cada pérdida y cada reanudación se guarda también **dónde arranca la siguiente posesión** (matrices `lto*`), en la orientación del equipo que la recibe.

---

## 5. Descarga

```bash
cd pipeline
python3 -I download.py           # eventos de los partidos de las entidades + team-stats de toda la liga
python3 -I download_lineups.py   # alineaciones (apodos, dorsales) y Open Data
python3 -I download_opendata.py  # Barcelona 2009–11
```
Paralelo (8 hilos), con reintentos y caché: volver a correrlo solo baja lo que falta.

---

## 6. Etapa 1 · `extract.py` (un resumen por partido)

Por cada partido y equipo produce `data/extract/<fuente>_<id>.json` con:
- **Cadena** por fase (2) y zona (18): `n` (acciones), `shot`, `xg`, `spC`, `spF`, `pen`, `keepF`, `keepT`, `lossO`, `lossXT`, `lossXG`, `lossXF`; matrices `mv` (18×18 por fase) y `mvC` (conducciones); matrices de reinicio `ltoO`, `ltoXT`, `ltoXG`, `ltoXF`, `ltoKF`, `ltoKT`; tiempo entre acciones por fase (`dt`).
- **Balón parado**: córners (cortos, técnica abierta/cerrada/recta, zona de caída: corto, primer palo, área chica, segundo palo, punto penal, borde), remates y cabezazos tras córner, faltas peligrosas directas o centradas con su xG, penales (convertidos, lado izquierdo/centro/derecho).
- **Disciplina**: faltas cometidas, amarillas, segundas amarillas, rojas, tarjetas por protestar.
- **Lanzadores**: quién cobra córners, faltas y penales y quién remata balón parado (id de jugador).
- **Actores**: cuántas acciones hace cada puesto en cada zona (para saber quién toca el balón dónde).
- **Posiciones medias** de cada puesto con y sin balón; **alineación inicial** con dorsales.
- **Métricas propias** para calibrar contra StatsBomb (posesión por pases, PPDA, altura defensiva, presiones, contrapresiones, centros al área, tiros al contragolpe, velocidad hacia portería, xG…).

Corre en ~8 s para 510 partidos (8 procesos). `--force` recalcula todo.

---

## 7. Etapa 2 · `build_model.py` (el modelo)

### 7.1 Agregación
Para cada entidad se suman los resúmenes de sus partidos:
- `att`: lo que hace el equipo con el balón (sus propios conteos).
- `dfn`: lo que le hacen sus rivales (los conteos del rival en esos partidos). Así una misma estructura describe ataque y defensa.
- `league`: suma de todos los equipos en todos los partidos procesados (884 actuaciones equipo-partido) = el comportamiento promedio de la liga.

### 7.2 Once tipo y quién toca el balón
- Formación más usada; dentro de ella, el conjunto de 11 puestos más repetido.
- Un jugador distinto por puesto: el titular más frecuente (con su dorsal y apodo de la alineación).
- Posición media con balón y sin balón de cada puesto (de sus eventos).
- Matriz `actors[zona][puesto]`: proporción de acciones que hace cada puesto en cada zona (los puestos fuera del once se asignan al puesto más cercano).
- `roles`: cobrador de córners, de faltas y de penales, y rematadores de balón parado, elegidos como el jugador del once que más lo hizo en los datos (p. ej. Barcelona: Xavi córners y faltas, Messi penales).

### 7.3 Plan de juego (percentiles)
Catorce controles con métricas de `team-stats` de StatsBomb (promedio por partido de la entidad):

| Control | Métrica StatsBomb |
|---|---|
| Posesión | `possession` |
| Verticalidad | `directness` |
| Velocidad hacia portería | `pace_towards_goal` |
| Altura de línea defensiva | `defensive_distance` |
| Volumen de presión | `pressures / (1 − posesión)` (presiones por posesión rival) |
| Acciones defensivas por pase rival | `ppda` (invertido) |
| Contrapresión | `counterpressures` |
| Saque largo del portero | `gk_long_pass_ratio` |
| Centros al área | `crosses_into_box` |
| Tiros al contragolpe | `counter_attacking_shots` |
| Tiros tras robo alto | `high_press_shots` |
| xG a favor / solidez | `np_xg` / `np_xg_conceded` (invertido) |
| Peligro a balón parado | `sp_xg` |

- **Encogimiento**: valor = (n·media del equipo + 8·media de la liga)/(n + 8). Un entrenador con 3 partidos queda cerca de la media; uno con 70 casi no se mueve.
- **Percentil** contra la distribución de todos los equipo-temporada de la liga con ≥10 partidos (2021–2026). 50 = equipo típico.
- **Volumen de presión y PPDA van separados** porque miden cosas distintas: el Atlas de Cocca tiene PPDA en P94 (muchas acciones defensivas por pase rival) pero volumen de presión P19 (no presiona: corta con duelos en bloque medio).

### 7.4 Etiquetas tipo FC
Reglas sobre los percentiles: construcción (pase corto / equilibrado / contragolpe / juego directo), enfoque defensivo (agresivo / alto / alto con presión situacional / profundo / bloque medio que va al duelo / equilibrado), ataque (por bandas / por dentro / mixto) y rasgos ("Dueño del balón", "Presión asfixiante" solo si coinciden presión y PPDA, "Corta con duelos, no presiona", etc.).

### 7.5 Equipos sin estadísticas agregadas (Barcelona): calibración
Para cada control definimos una versión propia calculada desde eventos y la ajustamos con una regresión lineal contra la métrica de StatsBomb en 884 actuaciones de Liga MX. Solo se usan las que replican bien (R² ≥ 0.5):

| Control | R² | Control | R² |
|---|---|---|---|
| Posesión | 1.00 | Centros al área | 0.91 |
| Volumen de presión | 1.00 | PPDA | 0.89 |
| xG a favor / en contra | 0.99 | Contrapresión | 0.88 |
| Tiros al contragolpe | 0.73 | Velocidad hacia portería | 0.62 |
| Altura de línea | 0.59 | Peligro a balón parado | 0.52 |
| Saque largo portero | 0.11 (no se usa) | Verticalidad | 0.01 (no se usa) |
| Tiros tras robo alto | 0.14 (no se usa) | | |

Definiciones que replican StatsBomb: *tiros al contragolpe* = recuperación en campo propio y tiro en ≤15 s; *velocidad hacia portería* = en posesiones que terminan en tiro, avance hacia portería entre segundos. Resultado Barcelona: posesión P100, volumen de presión P97, PPDA P95, contrapresión P80, velocidad hacia portería P2.

### 7.6 Arquetipo configurado ("Autobús y contra")
Sirve para comprobar que el motor responde a una configuración. Se construye desde la liga multiplicando tasas por fase y columna de la cancha: en ataque establecido pierde más el balón y tira menos; en transición avanza con sesgo vertical (×1.7 por columna) y pierde menos; defendiendo, sus rivales circulan cómodos atrás pero pierden mucho más y rematan peor cerca del área (tiros ×0.65, xG ×0.75). No tiene bonificación de definición: su peligro sale de cómo ataca.

### 7.7 Mapa de estilos
Para cada equipo-entrenador-temporada de la liga con ≥8 partidos (159 puntos) y para cada entidad:
- **Con balón**: x = ritmo de ataque = media de percentiles (velocidad hacia portería, tiros al contragolpe); y = posesión. Cuadrantes: posesión elaborada, dominio vertical, contragolpe, reactivo.
- **Sin balón**: x = altura de línea; y = intensidad de presión = media (volumen de presión, contrapresión). Cuadrantes: presión alta, línea alta con presión selectiva, bloque medio agresivo, bloque bajo.
- **Trayectoria**: puntos por temporada del mismo entrenador en el mismo club.
- **Estilos más parecidos**: los 3 equipo-temporada más cercanos en las 4 coordenadas, sin contar al propio entrenador.

### 7.8 Salida: `model/` dividido
- `model/model.json` (≤ 4 MB, lo descarga el simulador vía `/api/model`): `meta` (etiquetas, calibración, K, `league_scope`), `league` (conteos de la liga), `map.units` (puntos del mapa) y `entities[]` con `id`, `label`, `team`, `coach`, `group`, `kind` (real/opendata/synthetic), `n`, fechas, `official`, `window`, `formation`, `style` (percentiles), `style_status`, `shape`, `actors`, `roles`, `att`, `dfn`, `map`, `note` e `identity` (cuando existe el motor de etiquetas).
- `model/entities/<id>.json`: `temporal`, `personnel`, `context`, `context_comparisons`, `context_status`, `coverage`, `raw`. Las rutas `/api/teams/{id}`, `/context`, `/temporal`, `/personnel`, `/lineups` y `/substitutions` los unen al vuelo.
- `model/analysis/<id>.json`: analítica por entidad (un tema por módulo registrado en `pipeline/analytics/`, p. ej. `replay`), con `meta.windows` (partidos por ventana) y `meta.advertencias` si algún tema se omitió por tamaño.
- `model/explorer.json`, `model/xg_grid.json`, `model/story/<nombre>.json`.

**Ventana** (`window`): `oficial` si todos los partidos son ≤ 2025-06-30 (Ap2021–Cl2025); `epilogo` para Jardine 2025/26 (`ame_jardine_epi`); `temprano` para el resto de Liga MX (p. ej. Almada en América); `null` para Open Data y arquetipos. `ame_jardine` (91 partidos) es oficial; `ame_jardine_epi` (38) no.

**Referencia de liga**: `model.league` suma todos los partidos de todas las entidades. Al agregar las entidades de *Comparación* (Pachuca, Santos y San Luis de Almada/Jardine, América de Solari/Ortiz) esa referencia cambia y la simulación puede derivar aunque `engine.js` no cambie. `CAON_LEAGUE_SCOPE=legacy python pipeline/run.py build` restaura el conjunto anterior (excluye los partidos que solo aportan esas entidades).

### 7.9 API
`/api/health`, `/api/model`, `/api/teams[/{id}[/context|temporal|personnel|lineups|substitutions]]`, `/api/framework`, `/api/entities`, `/api/entities/{id}/analysis`, `/api/explorer/{teams|coaches}`, `/api/explorer/{team|coach}/{clave}`, `/api/story/{nombre}`, `/api/replay/{id}`, `/api/matches/{id}` y, si está instalado, el laboratorio de jugadas por texto (`/api/play/*`). Los errores 404 llevan mensaje en español; los archivos se releen cuando cambia su fecha. Las jugadas peligrosas en contra se reconstruirán con implementación propia en `pipeline/analytics/` (el módulo anterior `dangerous.py` venía de un trabajo descartado y no se usa).

---

## 8. Cómo encontramos el estilo de un entrenador

1. **Sus partidos**: el dato `managers` de cada partido dice quién dirigió. Una entidad junta solo esos partidos (y el periodo que elijamos: p. ej. el tricampeonato).
2. **Tres lentes complementarias**:
   - *Plan de juego*: dónde está contra la liga en 14 dimensiones (percentiles con encogimiento).
   - *Mapa de estilos*: en qué familia cae, cómo evolucionó por temporada (Jardine: de esperar en 23/24 a presionar en 24/25) y a quién se parece.
   - *Huella de cadena*: cómo se mueve el balón zona a zona, cuánto dura su posesión, cómo transita, dónde tira, dónde recupera y cómo cobra el balón parado. Es la parte que el motor usa para jugar "como él".
3. **Lo que no es estilo**: el modelo mezcla estilo y calidad (un equipo mejor tira más). Por eso el plan de juego separa métricas de forma (posesión, presión, altura) de las de rendimiento (xG), y el mapa usa solo métricas de forma.
4. **Agrupamiento**: probamos k-means sobre equipo-temporadas (ofensivo y defensivo por separado). La separación es débil (silhouette 0.15 y 0.23): los estilos de la Liga MX son un continuo, no cajas. Por eso el producto usa un mapa con ejes y cuadrantes con nombre en lugar de "N estilos" cerrados. El primer eje defensivo (intensidad sin balón) explica 55% de la variación y es la diferencia más clara entre entrenadores.

---

## 9. Motor de simulación (`engine.js · simulate`)

### 9.1 Parámetros de un equipo (`rates`)
Para cada fase y zona, la probabilidad de cada desenlace = (conteo del equipo + K·tasa de la liga·acciones de liga por partido) / (acciones del equipo + mismo término). Con K = 8 pseudo-partidos. Igual para el destino de cada pase (fila de 18 zonas), la proporción de conducciones, dónde arranca la siguiente posesión, el xG por tiro, el tiempo por acción y todas las tasas de balón parado y tarjetas.

### 9.2 El cruce A vs D
Cuando A ataca a D, cada probabilidad combina el ataque de A, la defensa de D (lo que sus rivales lograban contra él) y la liga:

**logit p = logit p_A + logit p_D − logit p_liga**

Si A tira el doble que la liga en una zona y D concede la mitad, el resultado queda cerca de la liga; si ambos empujan en la misma dirección, se acumula. El xG por tiro se combina como cociente (xG_A × xG_D / xG_liga). El destino de los pases y la proporción de conducciones salen del atacante (es su forma de jugar).

### 9.3 El partido
Estado: equipo con balón, zona, fase, reloj. En cada acción se sortea un desenlace con las probabilidades del cruce; un `move` consume el tiempo medio por acción del equipo; una pérdida en juego da la posesión al rival en la zona sorteada de `ltoO` y empieza su fase de transición (10 s). Las reanudaciones consumen tiempo muerto: una unidad común (29.7 s) × un peso por tipo (banda 0.55, meta 1.0, falta 0.75, balón parado 1.3, gol 2.0, penal 2.5, tarjeta 0.6). La unidad se calibra para que un partido de liga dure ~95 min de reloj con el número real de acciones.

**Reglas dentro del simulador**: una reanudación no puede ser un tiro, conducción ni balón parado inmediato (el primer toque es un pase); tras un gol saca quien lo recibió; el segundo tiempo lo saca el otro equipo.

### 9.4 Faltas, tarjetas, balón parado y penales
- **Falta**: el infractor se elige entre los jugadores del rival según quién suele estar en esa zona (raíz de su proporción de acciones), excluyendo al portero y a los expulsados. Un amonestado comete ×0.35 faltas (se cuida, como en la realidad).
- **Tarjeta**: amarilla y roja directa con la tasa por falta del equipo infractor; en faltas de penal, más probable. Segunda amarilla = roja. Tarjetas por protestar como proceso de Poisson con la tasa del equipo.
- **Expulsión**: el equipo con uno menos pierde fuerza en escala logit (tiros −0.2 y pérdidas +0.15 por jugador de diferencia).
- **Córner**: corto o al área (tasa del equipo), técnica (abierto/cerrado/recto), zona de caída, remate (combinado ataque-defensa), cabezazo, xG; si no hay remate, despeje (a veces a otro córner) y transición del rival.
- **Falta peligrosa**: directa (tasa del equipo, xG combinado) o centrada (remate combinado).
- **Penal**: surge de una falta en el área (o en un balón parado); conversión del equipo, lado (izquierda/centro/derecha) de sus datos y estirada del portero coherente con el resultado.

### 9.5 Simulación rápida
`simulateMany` repite el duelo 1,500 veces (≈1 s en el navegador) y promedia: ganar/empatar/perder, goles, xG, tiros, posesión, acciones por posesión, % de posesiones largas, % de tiros al contragolpe, robos en campo rival, córners, faltas, tarjetas y mapas de zonas de tiro y de recuperación. Cada partido usa una semilla: el mismo número de partido da siempre el mismo partido.

---

## 10. Coreografía (`engine.js · choreograph`)

Convierte cada evento simulado en movimiento. No cambia el resultado.
- **Receptor de un pase**: jugador del once ponderado por cuánto toca el balón en esa zona (dato) y por su cercanía; nunca en fuera de juego; recibe en un punto que puede alcanzar.
- **Bloque**: con balón, cada jugador va a su posición media con balón desplazada según dónde está la pelota; sin balón, a su posición sin balón con un desplazamiento según la altura de línea del equipo. En transición los atacantes rompen hacia adelante (sin pasar la línea del fuera de juego).
- **Presión**: el defensor más cercano presiona si la pelota está dentro de su alcance (depende de altura de línea y volumen de presión); los equipos de presión alta mandan un segundo hombre.
- **Física**: velocidad máxima 7.6 yd/s al correr, 4.2 al trotar, 5.5 el portero, 6.2 conduciendo; pase a 21 yd/s, tiro a 34 yd/s. Por eso un equipo que pierde arriba queda desordenado y el contragolpe se ve.
- **Reanudaciones**: saque inicial (todos en su campo, rival fuera del círculo), saque de meta (balón en el área chica, centrales abiertos, rival fuera del área y alto si presiona), saque de banda (desde la línea), tiro libre (rivales a 10 yardas; barrera de 2–4 a 10 yardas en la línea al centro de la portería), córner (rematadores del equipo en el área, uno o dos rivales arriba para la contra, centro con curva según técnica), penal (todos fuera del área y del arco, portero en la línea).
- **Tarjetas**: se muestran sobre el jugador; el expulsado camina fuera y desaparece; su equipo juega con 10.
- **Momentos destacados**: abre con el saque inicial y muestra cada jugada desde que empieza la posesión hasta el remate.

---

## 11. Reglamento: árbitro automático (`referee.js`)

Simula 240 partidos entre 24 cruces distintos y revisa cada situación: 1,916,547 revisiones, **0 infracciones**.

Reglas revisadas: reanudaciones con pase · saque inicial en campo propio y rival fuera del círculo · saque de meta desde el área y rivales fuera · tiro libre y córner con rivales a 10 yardas · córner desde la esquina · penal con portero en la línea y los demás fuera del área y del arco · saque de banda desde la línea · nadie recibe en fuera de juego · quien reanuda no se la pasa a sí mismo · un expulsado no vuelve a jugar ni recibe tarjetas · la segunda amarilla requiere una primera · velocidad humana (≤9.5 yd/s) · marcador = crónica · saque tras gol y del segundo tiempo · portero con las manos solo en su área · balón dentro del campo en pases y conducciones.

```bash
node pipeline/referee.js 10   # 10 partidos por cruce
```

---

## 12. Validación

Liga promedio contra liga promedio (2,000 partidos) contra la realidad (por equipo y partido):

| Métrica | Simulado | Real Liga MX |
|---|---|---|
| Tiros (sin penales) | 12.5 | 13.2 |
| xG sin penales | 1.06 | 1.13 |
| Goles | 1.25 | 1.33 |
| Posesión | 50% | 50% |
| Empates | 28% | 27% |
| Acciones por posesión | 8.0 | 8.0 |
| Faltas | 13.2 | 13.1 |
| Amarillas (por faltas) | 1.51 | 1.50 |
| Rojas | 0.10 | 0.12–0.16 |
| Córners | 4.3 | 4.9 |
| Tiros libres peligrosos | 2.0 | 2.3 |
| Penales | 0.23 | 0.21 |

Firmas de estilo contra la liga promedio (1,000 partidos): Barcelona 68% de posesión y 13.9 acciones por posesión; el arquetipo 43% y 37% de sus tiros al contragolpe; Atlas de Cocca 6.6 acciones por posesión; Jardine y Milito 9.6. Cada equipo de Liga MX reproduce sus tiros, xG y posesión reales (p. ej. Toluca: 15.0 tiros contra 16.4 y 55% de posesión contra 55%). Tablas completas en `pipeline/validation_table.md`.

```bash
node pipeline/validate.js 800        # cada entidad contra la liga, frente a sus datos reales
```

---

## 13. Interfaz (`index.html`)

1. **Enfrentamiento**: local y visitante (24 entidades en tres grupos), con chips de partidos, periodo, formación y avisos (muestra pequeña, fuera de ventana oficial, Open Data, configurado).
2. **Plan de juego**: tarjetas FC, 14 controles con los dos equipos sobre la misma barra, vista táctica con/sin balón con dorsales.
3. **Mapa de estilos**: dos mapas, trayectorias, detalle al pasar el cursor y estilos más parecidos.
4. **Simular partido**: cancha animada con indicador de posesión y fase, halo y nombre del poseedor, líneas de pase y tiro, avisos (robos, faltas, tarjetas, córners, goles), barra de dominio por minuto (clic para saltar), modos resumen y completo, velocidades, crónica y estadísticas en vivo.
5. **Simulación rápida**: 1,500 partidos con barras, marcadores frecuentes, lecturas automáticas y mapas de zonas.

---

## 14. Cómo agregar equipos y entrenadores nuevos

### 14.1 Un entrenador de Liga MX que ya aparece en los datos
1. En `pipeline/entities.py` agrega una línea a `SPECIAL`:
   ```python
   ('pac_almada', 'Pachuca · Almada', 'Pachuca', 'Almada', '2022-01-01', '2025-06-30', 'Histórico'),
   ```
   (id, etiqueta, nombre del equipo como en StatsBomb, texto que aparece en `managers`, desde, hasta, grupo).
2. Descarga lo que falte y reconstruye:
   ```bash
   cd pipeline
   python3 -I download.py && python3 -I download_lineups.py
   python3 -I extract.py          # solo procesa partidos nuevos
   python3 -I build_model.py
   python3 -I targets.py && node validate.js 600 pac && node referee.js 3
   ```
3. Arranca el servidor (`uvicorn app.main:app --reload`): el nuevo equipo aparece en el selector, en el mapa y se puede simular.

Los **entrenadores actuales** se detectan solos: si cambia el DT de un club, basta con volver a correr la descarga y los dos pasos de construcción.

### 14.2 Un entrenador recién llegado (pocos partidos)
El encogimiento con K = 8 lo acerca a la media mientras tenga pocos partidos y lo marca "Muestra pequeña". Opciones para darle más forma desde el inicio:
- crear también su entidad con su club anterior (p. ej. Almada en Pachuca, 138 partidos) y comparar ambas en el mapa;
- usar su club anterior como "previo": sustituir en `rates` la liga por los conteos de su etapa anterior en el término de encogimiento (cambio de una línea), para que sus primeros partidos se mezclen con su estilo conocido y no con la media.

### 14.3 Un equipo de otra competición o temporada
- **Con la API**: la competición debe estar en `v4/competitions`. Agrega sus temporadas en `pipeline/statsbomb.py` (`SEASONS_ALL`) y sus entidades. Si no tiene `team-stats`, el estilo se calcula como el del Barcelona (métricas propias calibradas, sección 7.5).
- **Con Open Data**: copia `download_opendata.py` cambiando competición/temporada/equipo; `extract.py` ya procesa la fuente `od`; crea la entidad como el Barcelona en `build_model.py` (`entity_from_matches('od', ids, 'Nombre del equipo')`).
- Advertencia: la línea base de la simulación es la Liga MX. Un equipo de otra liga se mide contra los rivales de su liga, así que cruzarlo es una comparación hipotética (se indica en la interfaz).

### 14.4 Un estilo configurado (sin datos)
Copia el diccionario `ATLETI` de `build_model.py`, cambia multiplicadores por fase y columna (pérdidas, tiros, sesgo vertical, xG, balón parado), su once (posiciones con y sin balón) y sus percentiles de estilo. Valida que la firma salga como esperas con `validate.js` (posesión, acciones por posesión, tiros al contragolpe) y que no supere a los equipos reales en fuerza sin quererlo.

### 14.5 Actualizar con jornadas nuevas
`download.py` + `download_lineups.py` + `extract.py` + `build_model.py`. Todo es incremental salvo la etapa 2, que tarda ~2 s.

---

## 15. Limitaciones

- No hay tracking: las posiciones de los jugadores sin balón son una reconstrucción (posiciones medias + reglas), no lo que pasó.
- El 360 ve ~13 de 22 jugadores por evento; se exploró y se dejó fuera de la demo.
- La cadena es de primer orden por zona y fase: no recuerda la jugada completa más allá de la fase de transición.
- El modelo mezcla estilo y calidad del plantel; la simulación explica cómo chocan dos estilos, no predice resultados (las bases lo piden así).
- Barcelona se mide contra La Liga y el arquetipo es configurado: sirven para validar, no son parte del análisis de Liga MX.
- Verticalidad, saque largo del portero y tiros tras robo alto no se replican desde eventos (R² bajo); para Barcelona se muestran como "s/d".
- Los córners simulados quedan un poco por debajo de los reales (4.3 contra 4.9).

---

## 16. Glosario

**xG**: probabilidad de que un tiro sea gol (modelo de StatsBomb). **PPDA**: pases del rival en su 60% de cancha por cada acción defensiva propia ahí. **Percentil**: porcentaje de equipo-temporadas de la liga por debajo. **Encogimiento**: mezcla del dato del equipo con la media de la liga según el tamaño de muestra. **Logit**: escala log(p/(1−p)) donde se suman efectos de ataque y defensa. **Cadena de Markov**: el siguiente estado depende solo del actual (zona y fase). **Transición**: primeros 10 s tras recuperar el balón en juego.
