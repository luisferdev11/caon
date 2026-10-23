# Marco analítico

Documento generado por `pipeline/framework.py` (`render_marco`). No editar a mano: cambia `DEFINITIONS` (en `framework_defs.py`) y vuelve a generarlo. La misma fuente alimenta `/api/framework`.

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

### Posesión (secuencia ofensiva) (`secuencia`)

Posesión de StatsBomb con al menos una acción con balón (pase, conducción, regate o tiro) del equipo poseedor; se ignoran las solo administrativas.

- **Fórmula:** possession id con ≥1 acción con balón
- **Unidad:** posesiones
- **Límites:** Aproximada desde eventos. Se excluye un tiro hecho dentro de una posesión rival (1 de 2,241 tiros y menos de una milésima del xG en los 91 partidos de Jardine; se mide en rival_shots de cada an_). La jugada que reanuda (córner, tiro libre, saque de banda o de puerta, inicial) no cuenta como progresión.
- **Fuente:** eventos

### Origen de la posesión (`origen`)

Robo en juego, portero, banda, tiro libre, córner, saque inicial u otro.

- **Fórmula:** tipo de reanudación + posesión previa
- **Unidad:** categoría
- **Límites:** Robo = posesión previa rival en juego.
- **Fuente:** eventos

### Salida limpia (`salida_limpia`)

Posesión en juego que nace en x<40 y llega a x≥60 sin perder el balón.

- **Fórmula:** inicio x<40 y max_x≥60 (solo acciones completadas)
- **Unidad:** % de posesiones
- **Límites:** Solo juego abierto.
- **Fuente:** eventos

### Progresión limpia (`progresion_limpia`)

Posesión que nace en x<60 y llega a x≥80 sin perder el balón.

- **Fórmula:** inicio x<60 y max_x≥80 (solo acciones completadas)
- **Unidad:** % de posesiones
- **Límites:** Solo juego abierto.
- **Fuente:** eventos

### Creación (`creacion`)

Posesión que entra al área rival o termina en tiro.

- **Fórmula:** entrada al área o tiro
- **Unidad:** % de posesiones
- **Límites:** Área: x≥102, 18≤y≤62.
- **Fuente:** eventos

### Entradas al área (`entradas_area`)

Posesiones propias que llevan el balón al área rival (pase o conducción que termina dentro, o tiro).

- **Fórmula:** box_entry por posesión
- **Unidad:** por partido
- **Límites:** Área: x≥102, 18≤y≤62.
- **Fuente:** eventos

### Calidad de ocasión (npxG por tiro) (`npxg_por_tiro`)

xG promedio de los tiros propios sin contar penales.

- **Fórmula:** Σ xG sin penal / tiros sin penal
- **Unidad:** xG por tiro
- **Límites:** xG de StatsBomb.
- **Fuente:** eventos

### Tiros desde la zona de remate (`tiros_zona_remate`)

Porcentaje de tiros sin penal hechos desde la zona de remate (x≥102, 30≤y≤50).

- **Fórmula:** tiros en zona / tiros
- **Unidad:** % de tiros
- **Límites:** Zona central del área.
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

Pérdida en juego seguida de tiro rival en ≤15 s dentro de esa posesión rival.

- **Fórmula:** lossO → tiro rival ≤ 15 s
- **Unidad:** pérdidas/partido
- **Límites:** Asociación descriptiva, no causal.
- **Fuente:** eventos

### Pérdida letal (`perdida_letal`)

Pérdida costosa cuyo tiro rival en ≤15 s terminó en gol.

- **Fórmula:** lossO → gol rival ≤ 15 s
- **Unidad:** pérdidas (total ventana)
- **Límites:** Asociación descriptiva.
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

- **Fórmula:** pases rivales x<72 (su marco) / (intercepción+falta+entrada+regate superado) x≥48
- **Unidad:** pases
- **Límites:** Menor = más presión. Con el regate superado correlaciona r=0.98 con el PPDA de StatsBomb.
- **Fuente:** eventos

### Contrapresión (`contrapresion`)

Presiones marcadas como contrapresión por StatsBomb (en los 5 s siguientes a perder el balón).

- **Fórmula:** presiones con counterpress
- **Unidad:** presiones/partido
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** eventos

### Contrapresión efectiva (`contrapresion_efectiva`)

Tras una pérdida propia en juego, la posesión rival dura ≤5 s y acaba en robo propio.

- **Fórmula:** pérdidas recuperadas ≤ 5 s / pérdidas
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

### xG concedido (`xg_concedido`)

Suma de xG de los tiros rivales (por tipo de jugada).

- **Fórmula:** Σ xG rival
- **Unidad:** xG por partido
- **Límites:** Sin penales salvo que se indique.
- **Fuente:** eventos

### Minutos de un jugador (`minutos_jugador`)

Minutos jugados por un futbolista y su parte de los minutos del equipo en la ventana (alineaciones y cambios).

- **Fórmula:** minutos del jugador / minutos del equipo
- **Unidad:** % de los minutos del equipo
- **Límites:** Descriptivo: no distingue lesiones ni suspensiones.
- **Fuente:** eventos

### Formación inicial (`formacion`)

Esquema con el que el equipo inicia el partido, según la alineación registrada.

- **Fórmula:** partidos con la formación / partidos
- **Unidad:** % de los partidos
- **Límites:** La formación registrada no describe el comportamiento durante el juego.
- **Fuente:** eventos

### Puntos por partido (`puntos`)

Puntos reales del partido: victoria 3, empate 1, derrota 0 (la tanda de penales no cuenta).

- **Fórmula:** Σ puntos / partidos
- **Unidad:** puntos por partido
- **Límites:** Resultado en tiempo regular.
- **Fuente:** eventos

### Diferencia de xG (`xg_dif`)

xG sin penales a favor menos xG sin penales en contra, por partido.

- **Fórmula:** xg − xga
- **Unidad:** xG por partido
- **Límites:** Usa el xG de team-stats; ver xg y xga.
- **Fuente:** team-stats

### Salida larga del portero (eventos) (`salida_portero`)

Porcentaje de saques de puerta largos y de pases largos del portero en juego, contados desde los eventos (largo = 35 yd o más).

- **Fórmula:** saques o pases largos / saques o pases del portero
- **Unidad:** % de acciones
- **Límites:** Distinta de saque_largo (team-stats, proporción del portero).
- **Fuente:** eventos

### xG por origen de la jugada (`xg_origen`)

xG sin penales por partido de las posesiones que nacen en cada origen: robo, portero, banda, tiro libre, córner u otro.

- **Fórmula:** Σ xG de posesiones de ese origen / partidos
- **Unidad:** xG por partido
- **Límites:** Desde eventos; no suma exactamente el xG de team-stats.
- **Fuente:** eventos

### Posesiones con tiro tras recuperación (`rec_tiro`)

Posesiones que terminan en tiro en los 15 s siguientes a una recuperación en campo rival (x≥60) o alta (x≥80).

- **Fórmula:** posesiones con tiro ≤15 s tras robo / partidos
- **Unidad:** posesiones por partido
- **Límites:** Distinta de presion_alta_tiros (team-stats).
- **Fuente:** eventos

### Distancia de los tiros concedidos (`x_media_tiros_concedidos`)

x media de los tiros rivales vista desde nuestra portería (x=0); menor = más cerca de nuestro arco.

- **Fórmula:** media x (marco del protagonista)
- **Unidad:** yardas
- **Límites:** Marco del protagonista.
- **Fuente:** eventos

### Balón parado de peligro (`bp_peligro`)

Todos los córners; tiros libres con reanudación en x≥80; saques de banda con x≥90 (solo análisis).

- **Fórmula:** is_danger_sp
- **Unidad:** jugadas
- **Límites:** Zonas: área, remate, área chica.
- **Fuente:** eventos

### Balón parado a favor (`bp_ofensivo`)

xG generado en posesiones nacidas de un balón parado de peligro.

- **Fórmula:** Σ xG_pos (bp_peligro propio)
- **Unidad:** xG por partido
- **Límites:** Incluye segundas jugadas de la posesión.
- **Fuente:** eventos

### Balón parado en contra (`bp_defensivo`)

xG concedido en posesiones rivales nacidas de un balón parado de peligro.

- **Fórmula:** Σ xG_pos (bp_peligro rival)
- **Unidad:** xG por partido
- **Límites:** Marcaje inferido con 360.
- **Fuente:** eventos

### Diferencial de balón parado (`bp_diferencial`)

xG a favor menos xG en contra en balón parado de peligro.

- **Fórmula:** bp_ofensivo − bp_defensivo
- **Unidad:** xG por partido
- **Límites:** KPI 7.
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
- **Límites:** Lo demás lleva la insignia "Fuera de ventana". Los percentiles de las conclusiones comparan contra equipos-temporada de la ventana oficial; solo el explorador usa la referencia ampliada (y lo dice).
- **Fuente:** eventos

### Encogimiento hacia el prior (`encogimiento`)

Promedio corregido por muestra chica hacia la carrera previa del DT o la liga; intervalo del 80%.

- **Fórmula:** (n·x̄ + 8·μ0)/(n+8)
- **Unidad:** según métrica
- **Límites:** Confianza: <5 muy baja, 5–11 baja, 12–24 media, ≥25 alta.
- **Fuente:** team-stats

### Consistencia (`consistencia`)

Qué tanto se repite el rendimiento entre partidos: dispersión entre partidos y banda de ruido por remuestreo (bootstrap, 80%).

- **Fórmula:** IQR entre partidos; bootstrap 80%
- **Unidad:** según métrica
- **Límites:** Descriptivo; no implica estabilidad causal.
- **Fuente:** eventos

### Puntos esperados (xPts) (`xpts`)

Puntos promedio si cada posesión con tiro se repitiera: 20,000 sorteos por partido con la probabilidad de gol de cada posesión.

- **Fórmula:** 3·P(G) + P(E)
- **Unidad:** puntos por partido
- **Límites:** Penales con su xG; autogoles fijos.
- **Fuente:** eventos

### Resultado sorpresivo (`resultado_sorpresivo`)

Partido cuyo resultado real tenía menos de 20% de probabilidad en la repetición con xG.

- **Fórmula:** P(resultado real) < 0.20
- **Unidad:** partidos
- **Límites:** Interpretativo, no pronóstico.
- **Fuente:** eventos

### XI base (`xi_base`)

Los jugadores con más minutos en la ventana, por posición.

- **Fórmula:** share de minutos
- **Unidad:** jugadores
- **Límites:** Roles en español; posiciones de StatsBomb.
- **Fuente:** eventos

### Rotación (`rotacion`)

Cambios promedio en el XI titular respecto del partido anterior.

- **Fórmula:** Δ XI entre partidos consecutivos
- **Unidad:** jugadores por partido
- **Límites:** Incluye bajas no observadas.
- **Fuente:** eventos

### Momento de los cambios (`cambios`)

Minuto medio de cada sustitución y su reparto por marcador.

- **Fórmula:** minuto de Substitution
- **Unidad:** minuto
- **Límites:** Se excluyen cambios por lesión no marcados.
- **Fuente:** eventos

### Impacto descriptivo del cambio (`impacto_cambio`)

Δ xG, OBV y field tilt en los 15 min posteriores contra los 15 previos (±2 min excluidos, mismo marcador).

- **Fórmula:** después − antes
- **Unidad:** según métrica
- **Límites:** Descriptivo, nunca "efecto".
- **Fuente:** eventos

### Posesión del balón (`posesion`)

Porcentaje de la posesión del partido (team_match_possession).

- **Fórmula:** team_match_possession
- **Unidad:** % del balón
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### Verticalidad (`verticalidad`)

Proporción del avance del balón que va directo hacia la portería rival (team_match_directness).

- **Fórmula:** team_match_directness
- **Unidad:** proporción
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### Velocidad del ataque (`ritmo`)

Velocidad media con la que el balón avanza hacia la portería rival (team_match_pace_towards_goal).

- **Fórmula:** team_match_pace_towards_goal
- **Unidad:** m/s
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### Altura de la defensa (`linea`)

Distancia media de las acciones defensivas a la propia portería (team_match_defensive_distance).

- **Fórmula:** team_match_defensive_distance
- **Unidad:** m
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### Volumen de presión (`volumen_presion`)

Presiones por partido ajustadas por la posesión rival (team_match_pressures_adj).

- **Fórmula:** team_match_pressures_adj
- **Unidad:** presiones/partido
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### PPDA de team-stats (pases del rival por acción defensiva) (`presion`)

PPDA de StatsBomb por partido; para el percentil se invierte: un percentil alto es un PPDA bajo (el rival hace pocos pases antes de que el equipo actúe).

- **Fórmula:** team_match_ppda
- **Unidad:** pases por acción defensiva (menos = más presión)
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### Saque largo del portero (`saque_largo`)

Proporción de pases largos del portero (team_match_gk_long_pass_ratio).

- **Fórmula:** team_match_gk_long_pass_ratio
- **Unidad:** proporción
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### Centros al área (`centros`)

Centros al área por partido (team_match_crosses_into_box).

- **Fórmula:** team_match_crosses_into_box
- **Unidad:** centros/partido
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### Tiros al contragolpe (`contragolpe`)

Tiros tras contraataque por partido (team_match_counter_attacking_shots).

- **Fórmula:** team_match_counter_attacking_shots
- **Unidad:** tiros/partido
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### Tiros tras robo alto (`presion_alta_tiros`)

Tiros en los segundos siguientes a un robo alto (team_match_high_press_shots).

- **Fórmula:** team_match_high_press_shots
- **Unidad:** tiros/partido
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### xG a favor (`xg`)

Goles esperados sin penales por partido (team_match_np_xg).

- **Fórmula:** team_match_np_xg
- **Unidad:** xG por partido
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### xG en contra (`xga`)

Goles esperados sin penales concedidos por partido (team_match_np_xg_conceded); para el percentil se invierte (menor = más sólido).

- **Fórmula:** team_match_np_xg_conceded
- **Unidad:** xG por partido
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### xG a balón parado (`bp_xg`)

Goles esperados de jugadas a balón parado por partido (team_match_sp_xg).

- **Fórmula:** team_match_sp_xg
- **Unidad:** xG por partido
- **Límites:** En etiquetas y mapa se usa su percentil frente a la liga (0–100).
- **Fuente:** team-stats

### Velocidad del ataque (eje del mapa) (`vel_ataque`)

Eje x del mapa ofensivo: media de los percentiles de velocidad hacia portería y tiros al contragolpe.

- **Fórmula:** round((ritmo + contragolpe) / 2)
- **Unidad:** percentil 0–100
- **Límites:** Señal compuesta; la tarjeta ofensiva sale del cuadrante.
- **Fuente:** team-stats

### Intensidad de presión (eje del mapa) (`intensidad_presion`)

Eje y del mapa defensivo: media de los percentiles de volumen de presión, PPDA invertido (alto = deja pocos pases por acción defensiva) y contrapresión.

- **Fórmula:** round((volumen_presion + presion + contrapresion) / 3)
- **Unidad:** percentil 0–100
- **Límites:** Señal compuesta: si volumen y PPDA discrepan, manda el perfil de presión.
- **Fuente:** team-stats

### Perfil de presión (regla de coherencia) (`perfil_presion`)

Volumen, PPDA y contrapresión nunca cuentan historias opuestas. Si el volumen es ≥65 y el PPDA invertido ≤45 (con contrapresión <75), el equipo "presiona mucho, deja jugar" y la tarjeta es "Línea alta: presiona mucho, deja jugar" o "Línea baja: presiona mucho, deja jugar". Si el volumen es ≤45 y el PPDA invertido ≥65, la presión es selectiva: "Línea alta, presión selectiva" o "Línea baja, presión selectiva". Ese nombre sustituye al del cuadrante; los nombres de cuadrante solo hablan de la altura de la línea y de la intensidad combinada, nunca del volumen. "Presión asfixiante" exige las tres señales altas y "Espera al rival" las tres bajas con línea baja.

- **Fórmula:** sin_robo: vol≥65, ppda≤45, cp<75 · selectiva: vol≤45, ppda≥65 · asfixiante: vol≥75, ppda≥60, cp≥50 · espera: vol≤30, ppda≤40, cp≤50, línea≤40
- **Unidad:** categoría
- **Límites:** Cada etiqueta declara lo que afirma sobre los percentiles; la auditoría rechaza las que no se sostienen.
- **Fuente:** team-stats

### Vigilancias (defensa de resguardo) (`vigilancias`)

Al robo rival tras nuestra pérdida: jugadores propios visibles por detrás del balón.

- **Fórmula:** conteo en el cuadro 360 del robo
- **Unidad:** jugadores
- **Límites:** Cota inferior: solo jugadores visibles en la toma.
- **Fuente:** 360

### Pérdidas con pocas vigilancias (`vigilancias_bajas`)

Porcentaje de pérdidas en juego con 2 o menos jugadores propios visibles detrás del balón al robo rival.

- **Fórmula:** vigilancias ≤ 2
- **Unidad:** % de pérdidas
- **Límites:** Cota inferior: solo jugadores visibles en la toma.
- **Fuente:** 360

### Altura de la línea (`altura_linea`)

x media de los 3 jugadores de campo más retrasados visibles.

- **Fórmula:** media x de los 3 más profundos
- **Unidad:** yardas
- **Límites:** Cuadros con ≥70% de la región visible.
- **Fuente:** 360

### Forma del bloque (`bloque_360`)

Con el rival en posesión establecida: altura de la última línea, largo, ancho y área (envolvente convexa) del bloque, por zona del balón.

- **Fórmula:** convex hull, extremos x/y
- **Unidad:** yardas / yd²
- **Límites:** Región de 25 yd detrás, 10 delante y ±25 a lo ancho del balón; ≥7 visibles.
- **Fuente:** 360

### Pases que rompen líneas (`rompe_lineas`)

Pases propios completados hacia adelante que superan rivales visibles (packing, cota inferior) o marcados line_breaking_pass.

- **Fórmula:** rivales con x0<x<x1
- **Unidad:** rivales superados por pase
- **Límites:** Cota inferior: solo jugadores visibles en la toma.
- **Fuente:** 360

### Presión coordinada (`presion_360`)

En cada presión propia: compañeros a ≤10 yd del balón y opciones libres del rival (≤15 yd del balón y a >3 yd de cualquier defensor).

- **Fórmula:** conteos en el cuadro
- **Unidad:** jugadores
- **Límites:** Cota inferior: solo jugadores visibles en la toma.
- **Fuente:** 360

### Organización en córner rival (`corner_def`)

Defensores en área y área chica, emparejamiento (atacantes con un defensor a ≤1.5 yd) y tipo de marca inferido: zonal, mixta o al hombre.

- **Fórmula:** índice de emparejamiento
- **Unidad:** categoría
- **Límites:** Tipo de marca inferido; tentativo.
- **Fuente:** 360

### Contexto del error (`contexto_error`)

En la última acción antes de perder: apoyos a ≤10 yd, rivales a ≤5 yd, distancia al defensor más cercano, xPass y presión.

- **Fórmula:** conteos en el cuadro
- **Unidad:** jugadores
- **Límites:** Cota inferior: solo jugadores visibles en la toma.
- **Fuente:** 360

### Forma antes y después del cambio (`forma_cambio`)

Δ altura de línea, ancho, largo y compacidad en 15 min antes contra 15 min después de cada sustitución (±2 min excluidos, mismo marcador).

- **Fórmula:** después − antes
- **Unidad:** yardas
- **Límites:** Descriptivo; solo forma del equipo.
- **Fuente:** 360

## KPIs de identidad

Cada KPI lleva semáforo en los terciles propios del DT (P33/P67) y la frase descriptiva "en partidos en verde sumó X pts/partido".

| # | KPI | Métrica (`id`) | Apoyo | Mejor |
|---|---|---|---|---|
| 1 | Dominio territorial | `field_tilt` | — | alto |
| 2 | Progresión limpia | `progresion_limpia` | — | alto |
| 3 | Calidad de ocasión | `npxg_por_tiro` | `tiros_zona_remate` | alto |
| 4 | Contrapresión efectiva | `contrapresion_efectiva` | — | alto |
| 5 | Pérdidas costosas por partido | `perdida_costosa` | `tipo_error` | bajo |
| 6 | Vigilancias 360 | `vigilancias` | `vigilancias_bajas` | alto |
| 7 | Diferencial de balón parado | `bp_diferencial` | `bp_ofensivo`, `bp_defensivo` | alto |

## Motor de etiquetas

Una sola función (`labels.identity`) produce tarjetas, etiquetas y puntos del mapa: la tarjeta "Enfoque defensivo" es el cuadrante del mapa defensivo. Extremos: percentil ≥80 o ≤20; centro "Equilibrado" si ambos ejes están a menos de 9 puntos de 50.

- **Mapa ofensivo:** x = Velocidad del ataque, y = Posesión.
- **Mapa defensivo:** x = Altura de línea, y = Intensidad de presión (media de volumen de presión, PPDA invertido y contrapresión).
- **Regla combinada:** "Directo pero paciente" (verticalidad alta con ritmo bajo; sustituye a las dos etiquetas sueltas).
- **Presión selectiva:** "Presión selectiva: pocas presiones, pero corta pronto el pase rival (PPDA bajo)".

| Cuadrante ofensivo | | Cuadrante defensivo | |
|---|---|---|---|
| tl | Posesión elaborada | tl | Bloque medio agresivo |
| tr | Dominio vertical | tr | Presión alta |
| bl | Reactivo | bl | Bloque bajo |
| br | Contragolpe | br | Línea alta, sin asfixiar |

### Regla de presión

Volumen, PPDA y contrapresión nunca cuentan historias opuestas. Si el volumen es ≥65 y el PPDA invertido ≤45 (con contrapresión <75), el equipo "presiona mucho, deja jugar" y la tarjeta es "Línea alta: presiona mucho, deja jugar" o "Línea baja: presiona mucho, deja jugar". Si el volumen es ≤45 y el PPDA invertido ≥65, la presión es selectiva: "Línea alta, presión selectiva" o "Línea baja, presión selectiva". Ese nombre sustituye al del cuadrante; los nombres de cuadrante solo hablan de la altura de la línea y de la intensidad combinada, nunca del volumen. "Presión asfixiante" exige las tres señales altas y "Espera al rival" las tres bajas con línea baja.

| Perfil | Texto | Afirma (percentiles) |
|---|---|---|
| `asfixiante` | Presión asfixiante | volumen_presion 75–100, presion 60–100, contrapresion 50–100, intensidad_presion 62–100 |
| `sin_robo` | Presiona mucho, pero deja jugar al rival (PPDA alto) | volumen_presion 65–100, presion 0–45, contrapresion 0–74 |
| `selectiva` | Presión selectiva: pocas presiones, pero corta pronto el pase rival (PPDA bajo) | volumen_presion 0–45, presion 65–100 |
| `espera` | Espera al rival | volumen_presion 0–30, presion 0–40, contrapresion 0–50, linea 0–40, intensidad_presion 0–40 |

| Línea | Perfil | Tarjeta y nombre en el mapa |
|---|---|---|
| alta | `sin_robo` | Línea alta: presiona mucho, deja jugar |
| baja | `sin_robo` | Línea baja: presiona mucho, deja jugar |
| alta | `selectiva` | Línea alta, presión selectiva |
| baja | `selectiva` | Línea baja, presión selectiva |

Pares excluyentes (nunca aparecen juntos; incluye los deducidos de afirmaciones disjuntas):

- Pase corto ↔ Posesión con pase vertical
- Pase corto ↔ Contragolpe
- Pase corto ↔ Juego directo
- Pase corto ↔ Reactivo
- Pase corto ↔ Equilibrado
- Pase corto ↔ Directo pero paciente
- Pase corto ↔ Cede el balón
- Pase corto ↔ Muy vertical
- Posesión con pase vertical ↔ Contragolpe
- Posesión con pase vertical ↔ Juego directo
- Posesión con pase vertical ↔ Reactivo
- Posesión con pase vertical ↔ Equilibrado
- Posesión con pase vertical ↔ Cede el balón
- Posesión con pase vertical ↔ Elabora en corto
- Contragolpe ↔ Dueño del balón
- Juego directo ↔ Posesión elaborada
- Juego directo ↔ Dominio vertical
- Juego directo ↔ Dueño del balón
- Juego directo ↔ Sale jugando desde el portero
- Por bandas ↔ Por dentro
- Por bandas ↔ Mixto
- Por bandas ↔ Evita el centro
- Por dentro ↔ Mixto
- Por dentro ↔ Centrador
- Mixto ↔ Centrador
- Mixto ↔ Evita el centro
- Posesión elaborada ↔ Dominio vertical
- Posesión elaborada ↔ Reactivo
- Posesión elaborada ↔ Contragolpe
- Posesión elaborada ↔ Cede el balón
- Dominio vertical ↔ Reactivo
- Dominio vertical ↔ Contragolpe
- Dominio vertical ↔ Cede el balón
- Reactivo ↔ Contragolpe
- Reactivo ↔ Dueño del balón
- Equilibrado ↔ Dueño del balón
- Equilibrado ↔ Cede el balón
- Bloque medio agresivo ↔ Presión alta
- Bloque medio agresivo ↔ Bloque bajo
- Bloque medio agresivo ↔ Línea alta, sin asfixiar
- Bloque medio agresivo ↔ Línea alta: presiona mucho, deja jugar
- Bloque medio agresivo ↔ Línea alta, presión selectiva
- Bloque medio agresivo ↔ Espera al rival
- Bloque medio agresivo ↔ Línea muy alta
- Presión alta ↔ Bloque bajo
- Presión alta ↔ Línea alta, sin asfixiar
- Presión alta ↔ Línea baja: presiona mucho, deja jugar
- Presión alta ↔ Línea baja, presión selectiva
- Presión alta ↔ Espera al rival
- Presión alta ↔ Línea muy baja
- Bloque bajo ↔ Línea alta, sin asfixiar
- Bloque bajo ↔ Línea alta: presiona mucho, deja jugar
- Bloque bajo ↔ Línea alta, presión selectiva
- Bloque bajo ↔ Presión asfixiante
- Bloque bajo ↔ Línea muy alta
- Línea alta, sin asfixiar ↔ Línea baja: presiona mucho, deja jugar
- Línea alta, sin asfixiar ↔ Línea baja, presión selectiva
- Línea alta, sin asfixiar ↔ Presión asfixiante
- Línea alta, sin asfixiar ↔ Espera al rival
- Línea alta, sin asfixiar ↔ Línea muy baja
- Equilibrado ↔ Presión asfixiante
- Equilibrado ↔ Espera al rival
- Equilibrado ↔ Línea muy alta
- Equilibrado ↔ Línea muy baja
- Línea alta: presiona mucho, deja jugar ↔ Línea baja: presiona mucho, deja jugar
- Línea alta: presiona mucho, deja jugar ↔ Línea alta, presión selectiva
- Línea alta: presiona mucho, deja jugar ↔ Línea baja, presión selectiva
- Línea alta: presiona mucho, deja jugar ↔ Presión asfixiante
- Línea alta: presiona mucho, deja jugar ↔ Espera al rival
- Línea alta: presiona mucho, deja jugar ↔ Línea muy baja
- Línea baja: presiona mucho, deja jugar ↔ Línea alta, presión selectiva
- Línea baja: presiona mucho, deja jugar ↔ Línea baja, presión selectiva
- Línea baja: presiona mucho, deja jugar ↔ Presión asfixiante
- Línea baja: presiona mucho, deja jugar ↔ Espera al rival
- Línea baja: presiona mucho, deja jugar ↔ Línea muy alta
- Línea alta, presión selectiva ↔ Línea baja, presión selectiva
- Línea alta, presión selectiva ↔ Presión asfixiante
- Línea alta, presión selectiva ↔ Espera al rival
- Línea alta, presión selectiva ↔ Línea muy baja
- Línea baja, presión selectiva ↔ Presión asfixiante
- Línea baja, presión selectiva ↔ Espera al rival
- Línea baja, presión selectiva ↔ Línea muy alta
- Directo pero paciente ↔ Elabora en corto
- Directo pero paciente ↔ Ataques rápidos
- Presión asfixiante ↔ Espera al rival
- Espera al rival ↔ Línea muy alta
- Dueño del balón ↔ Cede el balón
- Línea muy alta ↔ Línea muy baja
- Muy vertical ↔ Elabora en corto
- Ataques rápidos ↔ Ataques pausados
- Centrador ↔ Evita el centro
- Muy sólido atrás ↔ Concede mucho
- Portero en largo ↔ Sale jugando desde el portero
- Contragolpe ↔ Ataques pausados
- Posesión elaborada ↔ Ataques rápidos
- Presión asfixiante ↔ Presión selectiva: pocas presiones, pero corta pronto el pase rival (PPDA bajo)
- Presión asfixiante ↔ Presiona mucho, pero deja jugar al rival (PPDA alto)
- Línea muy baja ↔ Bloque medio agresivo
- Línea alta: presiona mucho, deja jugar ↔ Roba y remata
- Línea baja: presiona mucho, deja jugar ↔ Roba y remata

## Supuestos

- La posesión se aproxima con el identificador de posesión de StatsBomb; no se mide el tiempo de balón en juego.
- Los cuadros 360 solo muestran a los jugadores visibles en la toma de televisión: los conteos son cotas inferiores.
- Los eventos no registran desmarques sin balón; lo que no toca el balón solo se ve en 360.
- La población de referencia 360 son los rivales observados en los mismos partidos, no toda la liga.
- Los tipos de marca en balón parado (zonal, mixto, al hombre) se infieren de posiciones; son tentativos.
- El nivel del rival es circular: su diferencia de xG incluye el partido contra nosotros.
- La región de forma 360 es una ventana alrededor del balón (la toma ve ~22% del campo), no el ancho completo.

## Alcance

- Ventana oficial: Apertura 2021 a Clausura 2025 (hasta 2025-06-30). Las conclusiones solo usan esa ventana.
- Epílogo (2025-07-01 en adelante) y muestras tempranas se muestran con la insignia "Fuera de ventana".
- Muestras chicas se encogen hacia la carrera previa del DT o la liga (n0 = 8) y llevan intervalo del 80%.

## Límites

- Las asociaciones son descriptivas, no causales: "en partidos con X sumó Y" no significa que X cause Y.
- El simulador es un duelo de estilos dentro del modelo, no un pronóstico.
- Sin 360, las métricas de forma (línea, bloque, vigilancias) se marcan como no disponibles, nunca se imputan.
- Semáforos de KPIs sobre los terciles propios del DT (P33/P67): comparan al equipo consigo mismo.

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
| `BOX_Y` | [18.0, 62.0] |
| `SHOOTING_ZONE_Y` | [30.0, 50.0] |
| `SIX_YARD_MIN_X` | 114.0 |
| `GOAL` | [120.0, 40.0] |
| `TRANSITION_PHASE_S` | 10.0 |
| `OUTCOME_WINDOW_S` | 15.0 |
| `COUNTERPRESS_WINDOW_S` | 5.0 |
| `PACE_FLOOR_S` | 0.5 |
| `SHOOTOUT_PERIOD` | 5 |
| `SUB_WINDOW_MIN` | 15 |
| `SUB_GAP_MIN` | 2 |
| `REC_CAMPO_RIVAL_X` | 60.0 |
| `REC_ALTA_X` | 80.0 |
| `PPDA_DEF_MIN_X` | 48.0 |
| `PPDA_OPP_MAX_X` | 72.0 |
| `SALIDA_LIMPIA` | [40.0, 60.0] |
| `PROGRESION_LIMPIA` | [60.0, 80.0] |
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
| `SURPRISE_P` | 0.2 |
| `KPI_TRAFFIC_PCT` | [33, 67] |
| `KPI_MIN_MATCHES` | 12 |
| `VIG_LOW_MAX` | 2 |
| `GRID_STEP_YD` | 2.0 |
| `MIN_ROI_VISIBLE` | 0.7 |
| `MIN_SHAPE_PLAYERS` | 7 |
| `DEEP_LINE_N` | 3 |
| `ROI_BACK_YD` | 25.0 |
| `ROI_FRONT_YD` | 10.0 |
| `ROI_HALF_WIDTH_YD` | 25.0 |
| `ERROR_OPP_RADIUS_YD` | 5.0 |
| `PRESS_SUPPORT_RADIUS_YD` | 10.0 |
| `FREE_OPTION_RADIUS_YD` | 15.0 |
| `FREE_OPTION_MARGIN_YD` | 3.0 |
| `PAIRING_RADIUS_YD` | 1.5 |
| `REPLAY_DRAWS` | 20000 |
| `DESERVED_P` | 0.5 |
| `BALANCE_PTS` | 1.0 |
| `BIG_CHANCE_XG` | 0.3 |
| `REF_MIN_MATCHES` | 10 |
| `LONG_PASS_YD` | 35.0 |
| `DANGEROUS_TOP_N` | 10 |
| `DANGEROUS_MAX_ACTIONS` | 15 |
| `DANGEROUS_PAYLOAD_MAX_BYTES` | 250000 |
| `PROGRESSORS_TOP` | 8 |
| `LOSS_PLAYERS_TOP` | 10 |
| `SHORT_CORNER_YD` | 15.0 |
| `CONTACT_SCAN_EVENTS` | 8 |
| `SETPIECES_TOP_N` | 5 |
| `BOOT_DRAWS` | 1000 |
| `CONSISTENCY_MIN_INSIDE` | 3 |
| `CONSISTENCY_MIN_MATCHES` | 10 |
| `FINDINGS_TOP` | 12 |
| `XI_SIZE` | 11 |
| `SQUAD_TOP` | 25 |
| `HALFTIME_MINUTE` | 45 |
| `STORY_BALANCE_PPP` | 0.15 |
| `CORE_MINUTES_PCT` | 60 |
| `STORY_PCT_SHIFT` | 20 |
| `ROUND_DIGITS` | 4 |
