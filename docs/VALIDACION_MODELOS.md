# Validación de los modelos

Este documento valida el modelo y el simulador tal como están en la rama `overnight/jardine-historia` al inicio de la noche (sección **Antes**) y, al cierre, tras los cambios de la noche (sección **Después**, la escribe el agente de cierre). Todas las cifras salen de archivos en `data/out/baseline/` generados el 21 de octubre de 2026 a partir de `model/model.json` (construido el 2026-10-21 03:05 UTC).

## Antes

### 1. Estado de las pruebas

| Prueba | Resultado | Tiempo | Evidencia |
|---|---|---|---|
| `unittest discover` (Python) | ✅ 29 pruebas, todas pasan | 0.9 s | `data/out/baseline/unittest.txt` |
| `node --test test_validate.js test_frontend.js` | ✅ 6 de 6 pasan | 0.1 s | `data/out/baseline/node_tests.txt` |
| `check_model.py` | ✅ 24 entidades, 0 errores, 1 advertencia | 0.9 s | `data/out/baseline/check_model.txt` |
| `validate.js 100` | ✅ 25 evaluadas, 25 correctas, 0 errores | 1.0 s | `data/out/baseline/validate_100.txt`, `validate_100.json` |
| `referee.js 3` | ✅ 72 partidos simulados, 575,758 revisiones, 0 infracciones | 3.5 s | `data/out/baseline/referee_3.txt` |
| Prueba dorada nueva `test_golden_engine.js` | ✅ 2 de 2 pasan | <1 s | `data/out/tdd/A0.log` |

La única advertencia de `check_model` es que Barcelona 2009–11 (datos abiertos) no tiene verticalidad, saque largo ni tiros tras robo alto: esas métricas se muestran como no disponibles, no como cero.

### 2. Prueba dorada del simulador (AC-02)

El simulador (`frontend/engine.js`) queda congelado. Para demostrarlo durante toda la noche se creó una prueba dorada:

- **Fixture recortada** `pipeline/fixtures/golden_model.json` (179 KB): `meta`, `league`, `map` y 4 entidades (Jardine, Cocca, Guardiola y el arquetipo "autobús") sin los bloques que el motor no lee (`personnel`, `temporal`, `context`, `context_comparisons`, `coverage`, `style_status`, `context_status`, `raw`). **Prueba de identidad:** con 5 semillas, el modelo recortado y el completo (19.6 MB) producen exactamente los mismos hashes de todas las salidas (`make_golden.js strip` aborta si no coinciden).
- **Huellas** `pipeline/fixtures/golden_engine.json`: sha256 de `simulate` con registro completo para 25 semillas en 4 cruces (Jardine–Cocca, Cocca–autobús, Guardiola–Jardine, Jardine–liga promedio), `simulateMany` con N=300, y `choreograph` para 5 semillas (fotogramas, balón, narración, avisos, tiempos muertos, fases, jugadas destacadas, momentum, tarjetas, expulsados) más `playersAt`/`ballAt` en 50 instantes.
- **La prueba sí detecta cambios:** sobre una copia temporal de `engine.js` fuera del repositorio, cambiar `V_PASS` de 21 a 22 (constante solo visual) rompe la huella de `choreograph`. Cambiar `TURN_TIME` de 1.0 a 1.01 rompe las cuatro huellas de `simulate`, la de `simulateMany` y la de `choreograph`. Las copias se borraron después (evidencia en `data/out/tdd/A0.log`).

Aclaración importante: si en la noche se agregan partidos de Pachuca, San Luis o Santos, cambia `model.league` y por lo tanto cambian las cifras simuladas **aunque el código del motor no cambie**. La prueba dorada usa la fixture congelada justamente para separar "el código es idéntico" de "los datos cambiaron".

### 3. Datos reales contra simulados (`validate.js`, 100 partidos por cruce)

Cada entidad se simula contra la liga promedio. "Real" es el promedio por partido de los partidos reales de esa entidad; "sim" es el promedio de 100 partidos simulados. El xG real es sin penales (npxG) y los tiros reales son sin penales. Barcelona y el arquetipo no tienen línea "real" comparable en Liga MX.

| Entidad | n | Goles a favor real / sim | Goles en contra real / sim | xG a favor real (npxG) / sim | xG en contra real (npxG) / sim | Tiros real / sim | Posesión real / sim |
|---|---|---|---|---|---|---|---|
| Liga promedio | 890 | 1.33 / 1.28 | 1.38 / 1.08 | 1.13 / 1.16 | 1.13 / 1.19 | 13.23 / 13.1 | 50% / 50% |
| América · Jardine (Tricampeonato) | 70 | 1.76 / 1.56 | 0.89 / 1.11 | 1.48 / 1.44 | 0.86 / 1.10 | 13.13 / 12.2 | 54% / 53% |
| América · Almada | 10 | 2.20 / 1.35 | 1.10 / 1.17 | 1.47 / 1.40 | 1.20 / 1.14 | 19.20 / 15.3 | 56% / 53% |
| Chivas · Paunović | 42 | 1.29 / 1.18 | 1.17 / 1.06 | 0.97 / 1.14 | 1.02 / 1.03 | 12.64 / 12.7 | 48% / 47% |
| Chivas · Gago | 32 | 1.22 / 1.48 | 0.91 / 1.15 | 1.08 / 1.21 | 0.90 / 1.11 | 12.97 / 12.6 | 53% / 52% |
| Chivas · Milito | 51 | 1.69 / 1.58 | 1.18 / 1.04 | 1.54 / 1.54 | 0.85 / 1.04 | 15.65 / 14.8 | 57% / 54% |
| Atlas · Cocca (Bicampeonato) | 46 | 1.20 / 1.06 | 0.83 / 1.12 | 0.90 / 1.11 | 0.90 / 1.02 | 11.94 / 12.6 | 49% / 50% |
| Atlante · Miguel Herrera | 12 | 1.08 / 1.06 | 1.58 / 1.36 | 1.14 / 1.25 | 1.15 / 1.30 | 14.50 / 13.2 | 44% / 47% |
| Atlas · Hernán Crespo | 11 | 1.36 / 1.22 | 1.46 / 1.67 | 1.22 / 1.26 | 1.31 / 1.48 | 12.64 / 11.8 | 52% / 49% |
| San Luis · Diego Mejía | 11 | 1.27 / 1.32 | 1.82 / 1.17 | 1.14 / 1.16 | 1.26 / 1.26 | 12.46 / 12.1 | 53% / 52% |
| Cruz Azul · Joel Huiqui | 18 | 1.94 / 1.26 | 1.56 / 1.30 | 1.43 / 1.41 | 1.08 / 1.18 | 17.94 / 15.6 | 53% / 53% |
| Juárez · Gustavo Lema | 5 | 1.00 / 1.43 | 1.40 / 1.53 | 1.05 / 1.35 | 1.41 / 1.37 | 10.00 / 11.8 | 49% / 50% |
| León · Javier Gandolfi | 17 | 1.47 / 1.34 | 1.24 / 1.24 | 1.20 / 1.26 | 1.02 / 1.21 | 14.65 / 13.1 | 53% / 52% |
| Monterrey · Matías Almeyda | 10 | 1.70 / 1.26 | 1.50 / 1.15 | 1.35 / 1.21 | 1.36 / 1.08 | 16.70 / 14.1 | 55% / 53% |
| Necaxa · Juan Reynoso | 4 | 1.50 / 1.42 | 3.00 / 1.61 | 1.58 / 1.35 | 1.80 / 1.59 | 15.00 / 13.0 | 46% / 50% |
| Pachuca · Benjamín Mora | 11 | 1.64 / 1.37 | 1.27 / 1.29 | 1.36 / 1.30 | 1.37 / 1.28 | 15.73 / 13.2 | 48% / 49% |
| Puebla · Gerardo Espinoza | 12 | 1.00 / 1.05 | 1.08 / 1.39 | 0.78 / 1.04 | 1.21 / 1.28 | 12.75 / 12.6 | 43% / 47% |
| Pumas · Esteban Solari | 12 | 1.58 / 1.13 | 1.67 / 1.49 | 0.99 / 1.18 | 1.18 / 1.32 | 11.75 / 12.2 | 47% / 49% |
| Querétaro · Esteban González | 27 | 1.15 / 1.31 | 1.07 / 1.35 | 1.28 / 1.35 | 1.23 / 1.32 | 13.48 / 13.0 | 39% / 41% |
| Santos · Renato Paiva | 11 | 1.00 / 1.27 | 1.46 / 1.52 | 1.40 / 1.32 | 1.31 / 1.29 | 14.54 / 13.3 | 50% / 48% |
| Tigres · Víctor Vucetich | 7 | 1.00 / 1.42 | 0.71 / 1.24 | 1.21 / 1.30 | 1.17 / 1.23 | 14.71 / 13.3 | 50% / 50% |
| Tijuana · Sebastián Abreu | 48 | 1.35 / 1.44 | 1.25 / 1.52 | 0.98 / 1.29 | 1.22 / 1.34 | 11.73 / 11.6 | 47% / 48% |
| Toluca · Antonio Mohamed | 76 | 1.90 / 1.78 | 1.12 / 0.99 | 1.60 / 1.66 | 0.90 / 0.99 | 16.36 / 15.5 | 55% / 54% |
| Barcelona 2009–11 (Guardiola) | 68 | s/d / 1.68 | s/d / 0.73 | s/d / 1.74 | s/d / 0.81 | s/d / 14.5 | s/d / 68% |
| Autobús y contra (arquetipo tipo Atlético) | 60 | s/d / 1.33 | s/d / 0.81 | s/d / 1.46 | s/d / 0.89 | s/d / 13.5 | s/d / 43% |

Lectura: la posesión se reproduce casi exacta (diferencia media 1.5 puntos, máxima 3.9). Los goles tienen una diferencia media de 0.24 por partido, y la máxima (0.85) está en América · Almada, que solo tiene 10 partidos. **No hay prueba estadística de ajuste**: las diferencias son descriptivas, y en entidades con menos de 12 partidos el ruido domina. En Jardine el modelo es más conservador que la realidad: 1.56 goles simulados contra 1.76 reales a favor, y 1.11 contra 0.89 en contra.

### 4. Calibración de las métricas de estilo (R²)

Para cada partido de Liga MX se compara la métrica calculada desde los eventos con la métrica oficial de StatsBomb (`team-stats`) mediante un ajuste lineal (PPDA en logaritmo). Si R² < 0.5, la métrica no se considera calibrada.

| Métrica de estilo | Métrica StatsBomb | R² | Estado |
|---|---|---|---|
| Posesión | `team_match_possession` | 1.00 | ✅ alta |
| Verticalidad | `team_match_directness` | 0.01 | ❌ R² < 0.5: la métrica se reporta como no calibrada |
| Velocidad hacia portería | `team_match_pace_towards_goal` | 0.62 | ⚠️ moderada |
| Altura de línea defensiva | `team_match_defensive_distance` | 0.59 | ⚠️ moderada |
| Volumen de presión | `team_match_pressures_adj` | 1.00 | ✅ alta |
| PPDA | `team_match_ppda` | 0.89 | ✅ alta |
| Contrapresión | `team_match_counterpressures` | 0.88 | ✅ alta |
| Saque largo del portero | `team_match_gk_long_pass_ratio` | 0.11 | ❌ R² < 0.5: la métrica se reporta como no calibrada |
| Centros al área | `team_match_crosses_into_box` | 0.91 | ✅ alta |
| Tiros al contragolpe | `team_match_counter_attacking_shots` | 0.73 | ⚠️ moderada |
| Tiros tras robo alto | `team_match_high_press_shots` | 0.14 | ❌ R² < 0.5: la métrica se reporta como no calibrada |
| xG a favor (sin penales) | `team_match_np_xg` | 0.99 | ✅ alta |
| xG en contra (sin penales) | `team_match_np_xg_conceded` | 0.99 | ✅ alta |
| xG a balón parado | `team_match_sp_xg` | 0.52 | ⚠️ moderada |

Tres métricas no pasan la calibración: verticalidad (R² 0.01), saque largo del portero (0.11) y tiros tras robo alto (0.14). Las tres alimentan etiquetas visibles ("Muy vertical", "Portero en largo", "Roba y remata"), así que hoy esas etiquetas descansan en métricas que no coinciden con StatsBomb.

### 5. Árbitro automático (`referee.js 3`)

24 cruces × 3 partidos = 72 partidos simulados con coreografía completa. Todas las reglas revisadas:

| Regla | Revisiones | Faltas |
|---|---|---|
| Las reanudaciones (saque inicial, de meta, de banda, tiro libre) se juegan con un pase | 6752 | 0 |
| Saque inicial: cada equipo en su campo | 6918 | 0 |
| Saque inicial: el rival fuera del círculo central | 3463 | 0 |
| Saque de meta: el balón se patea desde dentro del área | 1901 | 0 |
| Saque de meta: los rivales fuera del área | 20704 | 0 |
| Tiro libre: los rivales a 10 yardas del balón | 22078 | 0 |
| Córner: el balón en la esquina | 657 | 0 |
| Córner: los rivales a 10 yardas | 7121 | 0 |
| Saque de banda: el balón sale desde la línea | 2864 | 0 |
| Un expulsado no vuelve a tocar el balón | 126515 | 0 |
| Nadie recibe un pase en fuera de juego | 58562 | 0 |
| Quien reanuda no se la pasa a sí mismo | 58562 | 0 |
| Nadie recibe tarjeta después de ser expulsado | 429 | 0 |
| La segunda amarilla llega solo tras una primera | 393 | 0 |
| Ningún jugador corre más rápido que un humano (≤ 9.5 yd/s) | 148189 | 0 |
| La crónica y el marcador coinciden | 72 | 0 |
| Tras un gol saca el equipo que lo recibió | 173 | 0 |
| El segundo tiempo lo saca el equipo que no sacó el primero | 72 | 0 |
| El portero solo usa las manos dentro de su área | 804 | 0 |
| Durante pases y conducciones el balón está dentro del campo | 108767 | 0 |
| Penal: el portero sobre la línea de gol | 37 | 0 |
| Penal: los demás fuera del área y del arco | 725 | 0 |

### 6. Cobertura de datos por entidad

| Entidad | Partidos (n) | Ventana oficial | Fechas | Tipo |
|---|---|---|---|---|
| América · Jardine (Tricampeonato) | 70 | sí | 2023-07-01 → 2024-12-16 | real |
| América · Almada | 10 | no | 2026-07-19 → 2026-10-11 | real |
| Chivas · Paunović | 42 | sí | 2023-01-08 → 2023-12-04 | real |
| Chivas · Gago | 32 | sí | 2024-01-14 → 2024-10-06 | real |
| Chivas · Milito | 51 | no | 2025-07-20 → 2026-10-11 | real |
| Atlas · Cocca (Bicampeonato) | 46 | sí | 2021-07-25 → 2022-05-30 | real |
| Atlante · Miguel Herrera | 12 | no | 2026-07-17 → 2026-10-17 | real |
| Atlas · Hernán Crespo | 11 | no | 2026-07-26 → 2026-10-17 | real |
| San Luis · Diego Mejía | 11 | no | 2026-07-18 → 2026-10-11 | real |
| Cruz Azul · Joel Huiqui | 18 | no | 2026-04-27 → 2026-10-12 | real |
| Juárez · Gustavo Lema | 5 | no | 2026-09-05 → 2026-10-10 | real |
| León · Javier Gandolfi | 17 | no | 2026-03-22 → 2026-10-10 | real |
| Monterrey · Matías Almeyda | 10 | no | 2026-07-19 → 2026-10-11 | real |
| Necaxa · Juan Reynoso | 4 | no | 2026-09-19 → 2026-10-17 | real |
| Pachuca · Benjamín Mora | 11 | no | 2026-07-18 → 2026-10-11 | real |
| Puebla · Gerardo Espinoza | 12 | no | 2026-07-18 → 2026-10-17 | real |
| Pumas · Esteban Solari | 12 | no | 2026-07-18 → 2026-10-17 | real |
| Querétaro · Esteban González | 27 | no | 2026-01-11 → 2026-10-10 | real |
| Santos · Renato Paiva | 11 | no | 2026-07-19 → 2026-10-11 | real |
| Tigres · Víctor Vucetich | 7 | no | 2026-08-22 → 2026-10-10 | real |
| Tijuana · Sebastián Abreu | 48 | no | 2025-07-12 → 2026-10-17 | real |
| Toluca · Antonio Mohamed | 76 | no | 2025-01-11 → 2026-10-10 | real |
| Barcelona 2009–11 (Guardiola) | 68 | no | 2009-08-29 → 2011-05-21 | datos abiertos |
| Autobús y contra (arquetipo tipo Atlético) | 60 | no | — → — | sintético |

La "ventana oficial" es hasta el 30 de junio de 2025 (Apertura 2021 a Clausura 2025). De las 22 entidades reales, solo 4 están en ventana (Jardine, Paunović, Gago y Cocca). El resto son de la temporada en curso, con entre 4 y 27 partidos: **muestra chica** para casi todos los equipos actuales.

### 7. Problemas conocidos (con evidencia)

1. **Jardine está incompleto y desactualizado.** `ame_jardine` tiene n=70, del 2023-07-01 al 2024-12-16. Faltan el Clausura 2025 y el resto del ciclo: el periodo oficial completo son 91 partidos (Ap23 23, Cl24 23, Ap24 24, Cl25 21), más 38 de epílogo (2025-07-01 a 2026-06-30). Hay unos 47 partidos con eventos ya descargados pero sin extracto `mx_`. Además, Jardine ya no es el DT de América: hoy se presenta como "actual" junto a Almada.
2. **Almada tiene 10 partidos.** Cualquier conclusión sobre su América es de muy baja confianza sin un prior (su carrera en Pachuca) y sin intervalos.
3. **Etiquetas que se contradicen.** Al evaluar las funciones actuales del frontend (`fcLabels`, `tags`, `quadName` de `frontend/index.html`) sobre las 24 entidades y las 159 unidades del mapa, salen 8 contradicciones (`data/out/baseline/label_contradictions.json`):
   - Jardine aparece a la vez con salida **"Pase corto"** y la etiqueta **"Muy vertical"**. Esa etiqueta viene de la verticalidad, que no está calibrada (R² 0.01).
   - En 7 entidades (Jardine, Atlante·Herrera, San Luis·Mejía, Juárez·Lema, Puebla·Espinoza, Pumas·Solari, Santos·Paiva), la tarjeta "Enfoque defensivo" dice "Equilibrado" mientras el mapa las pone en un cuadrante extremo. Por ejemplo, Jardine sale en "Línea alta, presión selectiva" y Santos·Paiva en "Bloque bajo". La tarjeta (`fcLabels`) y el mapa (`quadName`) usan reglas distintas sobre datos distintos.
4. **Un mismo nombre con definiciones distintas.** "Robo alto" tiene tres umbrales: el simulador usa x ≥ 60 ("Robos en campo rival"), `high_press_shots` usa x ≥ 80 y la PPDA usa x ≥ 48. El "balón parado peligroso" usa x ≥ 80 para faltas. El marco analítico de la noche les pondrá nombres distintos.
5. **Mapas de calor simulados presentados como reales.** En `frontend/index.html`, líneas 1109–1112, "De dónde tira …" y "Dónde recupera …" se calculan con `simulateMany` (partidos del modelo), pero el título no dice "simulado".
6. **Decimales crudos.** En `frontend/index.html`, línea 755, se formatea con `toFixed(3)`.
7. **La documentación cita código descartado.** `docs/DOCUMENTACION.md` (líneas 31, 205–218) describe `pipeline/dangerous.py`, `dangerous_plays` en el modelo y la ruta `GET /api/teams/{id}/dangerous-plays`. Esa ruta no existe en `app/main.py` y `pipeline/dangerous.py` es un huérfano del PR #1 descartado. Se reemplaza por una implementación propia.
8. **Código heredado en `research/dl.py`.** Importa `from sb import *`, pero `research/sb.py` no existe: el script ya no corre. Es material de exploración, no forma parte de la cadena.
9. **`/api/model` pesa 19.6 MB.** El límite de AC-16 es 4 MB. Unos 2 MB por entidad son `personnel` y unos 450 KB son `temporal`, y el simulador no necesita ninguno de los dos (lo demuestra la fixture dorada).

### 8. Línea base para regresión

- `data/out/baseline/extract_chain_hashes.json`: sha256 de cada uno de los 442 extractos `data/extract/mx_*.json` (todo salvo `names`), para detectar si `extract` cambia sin querer.
- `data/out/baseline/timings.jsonl`: código de salida y duración de cada paso.
- `docs/ACEPTACION.md`: tabla automática AC-01..AC-17 (`pipeline/acceptance.py`).

## Después

⏳ Pendiente: la escribe el agente de cierre con las mismas pruebas tras la reconstrucción final.
