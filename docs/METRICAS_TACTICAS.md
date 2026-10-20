# Métricas tácticas del modelo

Este inventario describe las métricas que se calculan en
[`pipeline/extract.py`](../pipeline/extract.py) y se agregan en
[`pipeline/build_model.py`](../pipeline/build_model.py). Las métricas de
StatsBomb `team-stats` son observadas en la fuente; las demás son derivadas de
eventos y no deben interpretarse como mediciones oficiales del proveedor.

| Métrica | Fórmula implementada | Fuente | Unidad / rango | Estado y limitación |
|---|---|---|---|---|
| Posesión | `pases del equipo / (pases del equipo + pases rivales)` | Eventos `Pass` | Proporción 0–1; estilo en percentil | Derivada; usa pases como aproximación de posesión. |
| Verticalidad | `distancia hacia delante / distancia total` en pases y conducciones | `Pass`, `Carry`, `end_location` | Proporción aproximada 0–1 | Derivada; no es una clasificación oficial de pase progresivo. |
| Ritmo hacia portería | `avance positivo del tiro / segundos hasta el primer tiro` | Posesiones, `Shot`, timestamps | Yardas por segundo aproximadas | Derivada; solo posesiones con remate y excluye juego parado. |
| Presión | `Pressure / (1 - posesión)` | `Pressure`, pases | Acciones ajustadas por proporción rival | Derivada; no mide éxito ni duración de la presión. |
| PPDA aproximado | `pases rivales en zona propia / acciones defensivas seleccionadas` | `Pass`, `Interception`, `Duel`, `Foul Committed` | Razón; menor implica más presión | Derivada; la implementación se calibra en escala logarítmica contra team-stats. |
| Contrapresión | Conteo de presiones con `counterpress` | `Pressure.counterpress` | Conteo agregado | Observada como etiqueta de evento; no mide resultado de la acción. |
| Altura defensiva | `media de x` de acciones defensivas | Eventos defensivos con `location` | Coordenada StatsBomb 0–120 | Derivada; acciones registradas no equivalen a línea defensiva completa. |
| Tiros de transición | Tiro tras recuperación rival en la ventana definida | Posesiones, `play_pattern`, timestamps | Conteo | Derivada; depende del `possession` y de una ventana de 10 segundos. |
| xG | Suma de `shot.statsbomb_xg` | `Shot` | xG por partido o contexto | Observada desde StatsBomb; no se recalibra localmente. |
| xG concedido | Suma del xG de tiros del rival | `Shot` rival | xG por partido o contexto | Observada desde StatsBomb. |
| Progresión territorial | Diferencia de coordenadas entre eventos | `location`, `end_location` | Yardas | Derivada; no representa valor de posesión. |
| Estado del marcador | Marcador acumulado antes de cada evento de gol | `Shot.outcome`, `Own Goal For`, `index` | Ganando / empatando / perdiendo | Derivada cronológicamente; se conserva el tamaño de muestra. |
| Localía | Equipo local del metadato del partido | Endpoint de partidos StatsBomb | Local / visitante | Observada de metadatos; no se deduce de coordenadas. |

## Ausencia y normalización

Los valores no calculables se conservan como `null` en lugar de convertirse en
cero. Los percentiles de estilo se calculan contra referencias de liga
compatibles y se aplica el encogimiento documentado por `K_MATCHES` hacia la
media de liga. El contexto incluye minutos aproximados, posesiones y una marca
`sufficient_sample`; una diferencia entre contextos no implica causalidad.

Las métricas de estilo que no tienen `team-stats` suficiente pueden usar una
estimación derivada de eventos únicamente cuando existe una calibración con
`R² >= 0.5`. El origen queda registrado en `style_status.sources`; las métricas
restantes aparecen en `style_status.unavailable`.
