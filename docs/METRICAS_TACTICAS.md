# Métricas tácticas y contratos de observación

Las fórmulas siguientes describen el código local. No constituyen una validación
externa de identidad táctica. `team-stats` contiene métricas suministradas por
StatsBomb: no afirmamos conocer sus fórmulas internas. Las métricas calculadas
localmente a partir de eventos son aproximaciones experimentales.

## Poblaciones y ausencia

- `n = len(coverage.processed_match_ids) = att.matches = dfn.matches`: partidos
  únicos de la selección equipo/entrenador/fechas con ambos equipos presentes en
  el extracto. Ataque y defensa se incorporan juntos. `coverage.excluded` explica
  cada exclusión. Un extracto incompleto se pone en cuarentena con `status: invalid`.
- `style_status.valid_matches` cuenta observaciones válidas **por métrica**, con
  claves StatsBomb, igual que `sources`. Puede ser menor que `n`. `unavailable`
  usa claves públicas de estilo. Un cero observado es un valor; ausencia es `null`
  o una clave de estilo omitida acompañada de su causa.
- Un partido procesado no garantiza observación de todas las métricas: por
  ejemplo, no tener remates impide calcular el ritmo hacia el primer tiro.
- El arquetipo sintético tiene una exposición configurada de 60 partidos y sus
  percentiles son manuales. No tiene contexto histórico real.
- `model.meta.schema_version = 2` añade cobertura y comparaciones; se conservan
  `att`, `dfn`, `style`, `raw`, `shape`, `map`, `temporal` y `personnel`.

## Inventario reproducible

En esta tabla, los conteos de estilo son por partido; los contextos acumulan los
numeradores y denominadores de la misma población antes de dividir. Coordenadas
StatsBomb: 120 × 80. Las distancias son unidades de esa cancha, aproximadamente
yardas; no son desplazamientos medidos por tracking.

| Nombre y concepto | Fórmula implementada / campos | Unidad y rango | Ausencia / normalización / limitación |
|---|---|---|---|
| Posesión aproximada, participación en circulación | `Pass propios / (Pass propios + rivales)`; `m.passes`, `m.opp_passes` | 0–1 | Denominador 0 → null. No mide tiempo efectivo de posesión. Contexto: `possession_proxy`. |
| Distribución de acciones | `(Pass+Carry+Dribble+Shot propios) / (propios+rivales)` | 0–1 | Sin acciones → null. Excluye eventos administrativos. Contexto: `action_share`. |
| Verticalidad global | `sum(max(dx,0)) / sum(hypot(dx,dy))` de pases y conducciones en posesiones sin BP peligroso | 0–1 | Distancia total 0 → null. `m.dir_fwd/dir_tot`; no representa valor ni éxito del avance. |
| Verticalidad contextual de pases | Igual cociente, únicamente `Pass.location/end_location` | 0–1 | Geometría ausente → null, nunca se rellena con (0,0). Se etiqueta como pases para distinguirla de la global. |
| Frecuencia de avance | Pases con `end_x > start_x` / pases | 0–1 | Denominador 0 o geometría incompleta → null. No equivale a pase progresivo según otra taxonomía. |
| Ritmo global hacia portería | Media por posesión con tiro de `max(x_primer_tiro-x_primera_acción,0) / max(t_tiro-t_acción,0.5)` | Unidades de cancha/s, ≥0 | `pace2_sum/pace2_n`. Sin tiros → null. Hereda exclusión de BP peligroso; la cota histórica de 0.5 s se conserva y documenta. |
| Ritmo contextual | Media del avance positivo/tiempo hasta primer tiro, dentro del mismo estado | Unidades de cancha/s, ≥0 | Tiempo ≤0 → null; no aplica la cota global. Experimental, no intercambiable con el estilo calibrado. |
| Altura de acciones defensivas | Media de `location.x` para Pressure, Duel, Interception, Ball Recovery, Block, Clearance, Foul Committed | 0–120 | `def_x/def_n`; sin localizaciones → null. No es la posición geométrica de la línea defensiva. |
| Volumen de presión ajustado | `Pressure / (1-posesión_proxy)` | Conteo ajustado ≥0 por partido | Sin exposición rival → null. Se eliminó el suelo artificial de 0.2 para que sea el mismo ajuste que la calibración contra team-stats. No mide eficacia. |
| PPDA aproximado | Pases rivales iniciados en `x<72` / (Interception + Foul Committed + Duel de tipo Tackle en `x>=48`) | Pases por acción defensiva, ≥0 | Sin acciones defensivas → null. Los duelos aéreos no cuentan. En calibración se usa log(PPDA); PPDA=0 no tiene log y se excluye, sin pseudoconteos. Menor PPDA genera mayor percentil de presión. |
| Contrapresión | Número de `Pressure` con `counterpress=true` | Conteo ≥0 | Cero si hubo observación y ningún evento; ausencia si no hubo muestra. La etiqueta del proveedor no prueba éxito ni causalidad. |
| Saque largo | Pases del portero de longitud ≥32 / pases del portero | 0–1 | `gk_long/gk_passes`; denominador 0 → null. Incluye pases del portero, no solo saques de meta. |
| Centros al área | `Pass.cross` y destino `x>=102`, `18<=y<=62` | Conteo ≥0 | `crosses_box`; selección geométrica local. Estilo por partido. |
| Contragolpe de estilo | Una posesión tras cambio de dueño, Regular Play/From Counter, inicio x<60, primer tiro no penal en ≤15 s | Conteo de posesiones ≥0 | `counter_shots2`; no equivale a todos los tiros de transición. El nombre del proveedor es una referencia de calibración, no igualdad de definiciones. |
| Tiros tras robo alto | Tiros no penales en posesión tras cambio de dueño, primera acción x>=80 | Conteo ≥0 | `high_press_shots`; sin ventana temporal adicional. Heurística de recuperación, no prueba de presión previa. |
| Tiros de transición contextual | Cada tiro no penal en ≤10 s desde inicio de posesión recuperada en Regular Play/From Counter; mismo periodo | Conteo ≥0 | No confundir con la heurística de 15 s de estilo. Cuenta tiros, no posesiones con tiro. |
| xG global a favor / concedido | Suma `Shot.statsbomb_xg` no penal propio/rival | xG ≥0 por partido | Procede del modelo xG del proveedor. No recalculamos probabilidades. |
| xG contextual a favor / concedido | Suma xG de todos los tiros, incluidos penales, asignada al estado **antes** del tiro | xG ≥0 | Si falta algún xG, el total y sus tasas son null, con contador de ausencias. Un contexto no observado no es xG=0. |
| xG a balón parado de estilo | xG no penal con patrón From Corner/From Free Kick/From Throw In | xG ≥0 | `m.sp_xg`. Distinto del BP peligroso del motor: córner o falta con primera acción x>=80. |
| Recuperaciones contextuales | Eventos Ball Recovery | Conteo ≥0 | Cuenta eventos registrados, no todas las recuperaciones de posesión ni éxito posterior. |
| Pérdidas contextuales | Dispossessed + Miscontrol | Conteo ≥0 | No incluye todas las pérdidas por pase; la interfaz usa el nombre concreto para no exagerar cobertura. |
| Exposición con expulsiones | Segundos posteriores a Red Card/Second Yellow de cualquier equipo | Segundos ≥0 | Persiste entre periodos. No ajusta por inferioridad, rival o torneo; advierte un posible factor de confusión. |

## Marcador, reloj y localía

`pipeline/contextual.py` reutiliza las ideas de `research/poc.py`, no su ejecución:
se elimina el filtro de disponibilidad 360 y el equipo fijo América. No se consultan
ni se requieren archivos 360. Se reutilizan las definiciones de balón parado y
PPDA del pipeline.

Se ordena por periodo e índice, preservando la secuencia del proveedor cuando los
timestamps coinciden. Un gol pertenece al estado previo; se actualiza el marcador
para las acciones posteriores y el intervalo que comienza después del gol.
`Own Goal For` cuenta una vez; `Own Goal Against` se usa solo si no tiene pareja.
Se excluye la tanda (periodo 5), se incluyen prórrogas (3/4). Con índices ausentes o
duplicados, o marcador final incompatible con metadatos, el estado se registra en
`unknown` y no se presentan inferencias ganando/empatando/perdiendo.

Los intervalos se miden con el timestamp relativo al periodo. No se atraviesan
medios tiempos ni se descartan pausas mayores de 30 s. Se informa tiempo de reloj
observado, **no tiempo de balón en juego**. Si falta un límite de periodo o un
intervalo no puede medirse, se marcan `clock_incomplete` y las tasas /90 son null.
La localía usa exclusivamente los IDs home/away de los metadatos, tanto Liga MX
como Open Data. Sin metadatos: `venue.unknown`.

Cada contexto tiene partidos observados, segundos/minutos, posesiones con acción
propia, inicios de posesión y conteos. Una posesión que atraviesa estados se cuenta
en cada estado visitado; esos conteos no se deben sumar para obtener el total.
Los conteos de acciones y segundos sí deben conservarse entre las particiones
score_state y venue, incluyendo unknown. `check_model.py` comprueba esa invariante.

Tasas: `conteo * 5400 / segundos` y `conteo * 100 / posesiones propias`. xG concedido
por 100 posesiones propias expresa exposición propia, no xG por posesión rival;
la comparación principal usa /90. Umbral descriptivo de muestra: ≥5 partidos,
≥90 minutos y ≥30 posesiones en **cada** contexto. Es una regla de presentación,
no una prueba de potencia estadística. Diferencia relativa: `(A-B)/abs(B)`; B=0
produce null. No se atribuye una diferencia automáticamente a una decisión táctica.

## Referencias y calibración del estilo

1. Referencia: medias de equipos-temporada de Liga MX, cada métrica con al menos
   diez observaciones finitas. Se registra su población en `meta.style_reference`.
2. Para una entidad se usan filas team-stats de sus partidos realmente procesados;
   si faltan, se puede usar la estimación lineal de eventos, con su cobertura propia.
3. Regresión partido a partido en Liga MX: `y = a + b*x`; PPDA en escala logarítmica.
   Sin ≥3 pares válidos, varianza o finitud se rechaza la calibración. R²<0.5 se
   conserva como diagnóstico pero no habilita imputación. Predicciones negativas
   o no finitas se omiten. R² es en muestra, no validación fuera de muestra.
4. Encogimiento: `(n_métrica * media_entidad + 8 * media_liga_partido)/(n_métrica+8)`.
   La media de liga pondera partidos; los percentiles ponderan equipos-temporada.
   Son ponderaciones distintas, explícitas, que se mantienen por compatibilidad.
5. Percentil: `100 * count(referencia < valor)/len(referencia)`; invertido para PPDA
   y xGA. Empates usan comparación estricta. Una referencia ausente no se inventa.

Los periodos equipo-entrenador y las temporadas de referencia tienen longitudes
variables; el percentil es descriptivo respecto a esa referencia, no un ranking
ajustado por calendario. Barcelona se proyecta desde otra competición y época:
la compatibilidad de escala no demuestra transportabilidad. Los conteos globales
de estilo conservan la escala por partido del proveedor; las comparaciones
contextuales usan exposición /90 para evitar comparar solo conteos absolutos.

## Análisis temporal existente

Se conservan los bloques cronológicos de ocho partidos y la fusión del último
bloque si tiene menos de cinco. `temporal.matches`, `periods`, `series`, `coverage`
y el análisis de jugadores se mantienen. Los resúmenes contextuales temporales
usan la misma función de tasas; ya no incrementan partidos en estados sin exposición
ni cuentan dos veces `matches` cuando el extracto ya lo proporciona.

La métrica temporal histórica `transition_shots_per_possession` usa
`counter_shots2/poss` (posesiones con contragolpe de 15 s / posesiones del motor).
Se conserva por compatibilidad y no debe interpretarse como la nueva métrica de
tiros de transición de 10 s. La dispersión temporal es descriptiva.

## Validación y codificación

`validate.js` distingue datos inválidos, errores de simulación y métricas no
disponibles. NaN/infinito, rangos imposibles y W+D+L≠N son errores con salida 1.
null/undefined analíticos son advertencias; se imprime NA y se continúa. Las
referencias npxG/tiros sin penal no se restan de xG/tiros totales del simulador.
Las diferencias cuantificadas se limitan a goles y posesión, con la limitación
adicional de que el rival de la simulación es la liga, no el calendario observado.

Los JSON generados usan UTF-8, `ensure_ascii=False`, `allow_nan=False`. Se leen
cachés heredadas CP1252 solo como compatibilidad cuando fallan bytes UTF-8, sin
reescribirlas. Ya no se usa la codificación predeterminada de Windows en targets ni en los descargadores de Open Data/lineups; las respuestas JSON nuevas se decodifican explícitamente como UTF-8.
El validador recorre estructuras anidadas para detectar no finitos y señales de
mojibake; no intenta reconstruir arbitrariamente caracteres perdidos.
