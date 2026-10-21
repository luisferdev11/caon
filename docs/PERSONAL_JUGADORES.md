# Participación y jugadores

El modelo de jugadores se construye en `pipeline/personnel.py` a partir de
los lineups y eventos StatsBomb almacenados en caché. No usa nombres como
identificador cuando existe `player_id`.

## Datos observados

Cada partido conserva, cuando está disponible:

- jugador, equipo e `player_id`;
- titularidad;
- intervalos registrados de posición;
- minuto de entrada y salida;
- minutos observados;
- sustitución, motivo y contraparte;
- estado del marcador y localía en cada sustitución;
- expulsiones observadas;
- jugadores simultáneamente en campo por intervalo.

Las posiciones (`Right Wing`, `Center Back`, etc.) son posiciones registradas
por StatsBomb. El sistema no las transforma en roles tácticos inferidos.
`Tactical Shift` cambia el segmento de posición, no la interpretación del
rol.

## Intervalos

Los intervalos se delimitan con `from`/`to` de las posiciones del lineup,
eventos de gol y el último timestamp de evento disponible. Un `to` nulo se
extiende hasta ese último timestamp observado; no se supone que el partido
termine exactamente en 90 minutos. Por eso `match_minutes_observed` es una
medida de cobertura y no una duración oficial si falta un evento final.

Los cambios de composición se validan contra los eventos de sustitución y
tarjetas. IDs duplicados, lineups incompletos, posiciones ausentes, intervalos
invertidos o sustituciones sin contraparte se conservan como warnings en
`personnel.coverage.warnings` o en el partido correspondiente.

## Métricas por intervalo

Cada intervalo incluye minutos, eventos, pases del equipo, pases rivales,
presiones, tiros, xG, directness y un `ppda_all_zone` descriptivo. Esta última
razón usa pases rivales frente a acciones defensivas observadas, sin aplicar
la delimitación territorial del PPDA agregado del modelo; no debe compararse
directamente con el PPDA contextual global.

Los intervalos también conservan `score_state` (`winning`, `drawing`,
`losing`) y `venue`. `sufficient_sample` se marca con 15 minutos como criterio
operativo de inspección, no como prueba estadística.

## Agregados

`personnel.players` resume partidos, titularidades, minutos y posiciones.
`starting_lineups` lista las combinaciones más frecuentes y
`combinations` lista parejas con apariciones iniciales y minutos compartidos.
Estos son conteos descriptivos: no identifican una alineación ideal ni un
jugador mejor.

## Cobertura conocida

La cobertura se genera dentro del modelo y contiene por fuente:

- partidos de entrada;
- partidos con y sin lineup;
- partidos con sustituciones;
- jugadores identificables;
- partidos con posiciones;
- partidos no disponibles;
- warnings agregados.

StatsBomb API y Open Data no ofrecen la misma cobertura. En particular, los
lineups Open Data existentes no siempre están completos y algunos partidos no
tienen un archivo de lineup válido; esos partidos permanecen en
`unavailable_matches` y no se rellenan con ceros.
