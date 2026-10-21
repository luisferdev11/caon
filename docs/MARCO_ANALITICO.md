# Marco analítico

Documento generado por `pipeline/framework.py` (`render_marco`). No editar a mano: cambia `DEFINITIONS` y vuelve a generarlo. La misma fuente alimenta `/api/framework`.

## Definiciones

### Sistema de coordenadas (`coord`)

Campo StatsBomb de 120×80 yardas; cada evento en el marco de ataque de su equipo (ataca hacia x=120). En pantalla el protagonista ataca de izquierda a derecha.

- **Fórmula:** rival: (120-x, 80-y) vía to_frame
- **Unidad:** yardas
- **Límites:** Los 360 vienen en el marco del equipo actor.
- **Fuente:** eventos

### Zona del campo (`zona`)

Rejilla de 6 columnas × 3 carriles (20 yd × 26.7 yd).

- **Fórmula:** zona = floor(x/20)·3 + floor(y/26.67)
- **Unidad:** zona 0–17
- **Límites:** Idéntica a la del simulador.
- **Fuente:** eventos

### Tercio (`tercio`)

Propio x<40, medio 40–80, final x≥80.

- **Fórmula:** umbral en x
- **Unidad:** tercio
- **Límites:** Marco propio.
- **Fuente:** eventos

### Posesión (secuencia ofensiva) (`posesion`)

Posesión de StatsBomb con al menos una acción con balón (pase, conducción, regate o tiro) del equipo poseedor; se ignoran las solo administrativas.

- **Fórmula:** possession id con ≥1 acción con balón
- **Unidad:** posesiones
- **Límites:** Aproximada desde eventos.
- **Fuente:** eventos

### Origen de la posesión (`origen`)

Robo en juego, portero, banda, tiro libre, córner, saque inicial u otro.

- **Fórmula:** tipo de reanudación + posesión previa
- **Unidad:** categoría
- **Límites:** Robo = posesión previa rival en juego.
- **Fuente:** eventos

### Salida limpia (`salida_limpia`)

Posesión en juego que nace en x<40 y llega a x≥60 sin perder el balón.

- **Fórmula:** inicio x<40 y max_x≥60
- **Unidad:** % de posesiones
- **Límites:** Solo juego abierto.
- **Fuente:** eventos

### Progresión limpia (`progresion_limpia`)

Posesión que nace en x<60 y llega a x≥80 sin perder el balón.

- **Fórmula:** inicio x<60 y max_x≥80
- **Unidad:** % de posesiones
- **Límites:** Solo juego abierto.
- **Fuente:** eventos

### Creación (`creacion`)

Posesión que entra al área rival o termina en tiro.

- **Fórmula:** entrada al área o tiro
- **Unidad:** % de posesiones
- **Límites:** Área: x≥102, 18≤y≤62.
- **Fuente:** eventos

### Acción progresiva (`prog`)

Pase o conducción completada (no la primera de un balón parado), desde x≥48, que acerca el balón a la portería ≥25% y ≥10 yd, o pase completado al área desde fuera.

- **Fórmula:** Δd(120,40) ≥ 25% y ≥ 10 yd
- **Unidad:** acciones/partido
- **Límites:** Solo acciones completadas.
- **Fuente:** eventos

### Dominio territorial (field tilt) (`field_tilt`)

Proporción de acciones con balón en el último tercio que son propias.

- **Fórmula:** propias_tercio_final / (propias + rivales)
- **Unidad:** %
- **Límites:** Igual al fieldTilt del simulador.
- **Fuente:** eventos

### Transición ofensiva (`transicion`)

Posesión nacida de un robo en juego; la fase de transición son sus primeros 10 s.

- **Fórmula:** origen=robo, t ≤ 10 s
- **Unidad:** posesiones
- **Límites:** Espejo: transición defensiva.
- **Fuente:** eventos

### Contraataque (`contraataque`)

Transición que nace en x<60 y termina en tiro en ≤15 s.

- **Fórmula:** robo x<60 → tiro ≤ 15 s
- **Unidad:** contraataques/partido
- **Límites:** Compatible con StatsBomb.
- **Fuente:** eventos

### Pérdida (`perdida`)

Fin de una posesión propia cuando la siguiente posesión no administrativa es rival.

- **Fórmula:** lossO en juego; lossX* con balón parado
- **Unidad:** pérdidas/partido
- **Límites:** Como en extract.
- **Fuente:** eventos

### Pérdida costosa (`perdida_costosa`)

Pérdida en juego seguida de tiro rival en ≤15 s dentro de esa posesión rival; "letal" si fue gol.

- **Fórmula:** lossO → tiro rival ≤ 15 s
- **Unidad:** pérdidas/partido
- **Límites:** Asociación descriptiva, no causal.
- **Fuente:** eventos

### Tipo de error (`tipo_error`)

No forzado (pase fallado con xPass≥0.80 sin presión); bajo presión; decisión arriesgada (pase adelante con xPass<0.50); duelo perdido; aislado (360: 0 compañeros ≤10 yd).

- **Fórmula:** reglas en orden
- **Unidad:** categoría
- **Límites:** 360 solo ve jugadores visibles.
- **Fuente:** eventos

### Fase de presión (`fase_presion`)

Por ubicación del balón rival en nuestro marco: alta x≥80, bloque medio 40–80, bajo x<40.

- **Fórmula:** presiones+acciones def. / acciones rivales en la banda
- **Unidad:** por acción
- **Límites:** Marco propio.
- **Fuente:** eventos

### PPDA (`ppda`)

Pases rivales permitidos por acción defensiva propia en campo de presión.

- **Fórmula:** pases rivales x<72 (su marco) / (intercepción+falta+entrada) x≥48
- **Unidad:** pases
- **Límites:** Menor = más presión.
- **Fuente:** eventos

### Contrapresión (`contrapresion`)

Presión marcada counterpress; recuperación por contrapresión: tras nuestra pérdida, la posesión rival dura ≤5 s y acaba en robo propio.

- **Fórmula:** rival ≤ 5 s → robo
- **Unidad:** % de pérdidas
- **Límites:** Solo pérdidas en juego.
- **Fuente:** eventos

### Robos en campo rival (`rec_campo_rival`)

Recuperaciones en juego con x≥60.

- **Fórmula:** robo x ≥ 60
- **Unidad:** robos/partido
- **Límites:** Igual al simulador.
- **Fuente:** eventos

### Robos altos (`rec_alta`)

Recuperaciones en juego con x≥80.

- **Fórmula:** robo x ≥ 80
- **Unidad:** robos/partido
- **Límites:** Igual a high_press_shots de extract.
- **Fuente:** eventos

### Jugada peligrosa concedida (`jugada_peligrosa_concedida`)

Posesión rival con al menos un tiro; orden: gol, xG de la posesión, OBV máximo, fecha.

- **Fórmula:** xG_pos = 1-Π(1-xg)
- **Unidad:** jugadas
- **Límites:** Etiquetas: penal, balón parado, transición, ataque establecido.
- **Fuente:** eventos

### Balón parado de peligro (`bp_peligro`)

Todos los córners; tiros libres con reanudación en x≥80; saques de banda con x≥90 (solo análisis).

- **Fórmula:** is_danger_sp
- **Unidad:** jugadas
- **Límites:** Zonas: área, remate, área chica.
- **Fuente:** eventos

### Nivel del rival (`rival_tier`)

Rango del rival por diferencia de xG por partido en su temporada: 1–6 alto, 7–12 medio, 13–18 bajo (temporada previa si tiene <10 partidos).

- **Fórmula:** rango team_season_xgd_pg
- **Unidad:** categoría
- **Límites:** Circular: el rival también jugó contra nosotros.
- **Fuente:** team-stats

### Tramo de minuto (`minuto`)

0–15, 16–30, 31–45+, 46–60, 61–75, 76–90+ y prórroga; sin tanda de penales.

- **Fórmula:** minute_bin
- **Unidad:** tramo
- **Límites:** El añadido cuenta en el último tramo.
- **Fuente:** eventos

### Marcador (`marcador`)

Estado del marcador antes de cada acción, visto por el equipo protagonista.

- **Fórmula:** ganando / empatando / perdiendo
- **Unidad:** categoría
- **Límites:** Se excluyen autogoles no registrados.
- **Fuente:** eventos

### OBV (`obv`)

Valor añadido por acción (On-Ball Value) de StatsBomb.

- **Fórmula:** Σ obv_total_net
- **Unidad:** goles esperados
- **Límites:** Validado contra team_match_obv.
- **Fuente:** eventos

### Ventana (`ventana`)

Oficial (≤2025-06-30, Ap2021–Cl2025), epílogo o temprano. Las conclusiones solo usan la oficial.

- **Fórmula:** fecha ≤ 2025-06-30
- **Unidad:** categoría
- **Límites:** Lo demás lleva la insignia "Fuera de ventana".
- **Fuente:** eventos

### Encogimiento hacia el prior (`encogimiento`)

Promedio corregido por muestra chica hacia la carrera previa del DT o la liga; intervalo del 80%.

- **Fórmula:** (n·x̄ + 8·μ0)/(n+8)
- **Unidad:** según métrica
- **Límites:** Confianza: <5 muy baja, 5–11 baja, 12–24 media, ≥25 alta.
- **Fuente:** team-stats

### Vigilancias (defensa de resguardo) (`vigilancias`)

Al robo rival tras nuestra pérdida: jugadores propios visibles por detrás del balón.

- **Fórmula:** conteo en el cuadro 360 del robo
- **Unidad:** jugadores
- **Límites:** Cota inferior: solo jugadores visibles.
- **Fuente:** 360

### Altura de la línea (`altura_linea`)

x media de los 3 jugadores de campo más retrasados visibles.

- **Fórmula:** media x de los 3 más profundos
- **Unidad:** yardas
- **Límites:** Cuadros con ≥70% de la región visible.
- **Fuente:** 360

## Supuestos

- La posesión se aproxima con el identificador de posesión de StatsBomb; no se mide el tiempo de balón en juego.
- Los cuadros 360 solo muestran a los jugadores visibles en la toma de televisión: los conteos son cotas inferiores.
- Los eventos no registran desmarques sin balón; lo que no toca el balón solo se ve en 360.
- La población de referencia 360 son los rivales observados en los mismos partidos, no toda la liga.
- Los tipos de marca en balón parado (zonal, mixto, al hombre) se infieren de posiciones; son tentativos.
- El nivel del rival es circular: su diferencia de xG incluye el partido contra nosotros.

## Alcance

- Ventana oficial: Apertura 2021 a Clausura 2025 (hasta 2025-06-30). Las conclusiones solo usan esa ventana.
- Epílogo (2025-07-01 en adelante) y muestras tempranas se muestran con la insignia "Fuera de ventana".
- Muestras chicas se encogen hacia la carrera previa del DT o la liga (n0 = 8) y llevan intervalo del 80%.

## Límites

- Las asociaciones son descriptivas, no causales: "en partidos con X sumó Y" no significa que X cause Y.
- El simulador es un duelo de estilos dentro del modelo, no un pronóstico.
- Sin 360, las métricas de forma (línea, bloque, vigilancias) se marcan como no disponibles, nunca se imputan.

## Umbrales con nombre

| Constante | Valor |
|---|---|
| `PITCH_X` | 120.0 |
| `PITCH_Y` | 80.0 |
| `ZONE_NX` | 6 |
| `ZONE_NY` | 3 |
| `ZONE_DX` | 20.0 |
| `ZONE_DY` | 26.666666666666668 |
| `THIRD_OWN_MAX_X` | 40.0 |
| `THIRD_FINAL_MIN_X` | 80.0 |
| `BOX_MIN_X` | 102.0 |
| `SIX_YARD_MIN_X` | 114.0 |
| `TRANSITION_PHASE_S` | 10.0 |
| `OUTCOME_WINDOW_S` | 15.0 |
| `COUNTERPRESS_WINDOW_S` | 5.0 |
| `PACE_FLOOR_S` | 0.5 |
| `REC_CAMPO_RIVAL_X` | 60.0 |
| `REC_ALTA_X` | 80.0 |
| `PPDA_DEF_MIN_X` | 48.0 |
| `PPDA_OPP_MAX_X` | 72.0 |
| `PROG_MIN_START_X` | 48.0 |
| `PROG_MIN_REDUCTION` | 0.25 |
| `PROG_MIN_YARDS` | 10.0 |
| `DANGER_FK_MIN_X` | 80.0 |
| `DANGER_THROW_MIN_X` | 90.0 |
| `XPASS_EASY` | 0.8 |
| `XPASS_RISKY` | 0.5 |
| `PRESSURE_RADIUS_YD` | 3.0 |
| `ISOLATION_RADIUS_YD` | 10.0 |
| `TIER_SIZE` | 6 |
| `TIER_MIN_MATCHES` | 10 |
| `SHRINK_N0` | 8 |
| `CI_LEVEL` | 0.8 |
