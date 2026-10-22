"""Textos del marco analítico: glosario ``DEFINITIONS``, KPIs, supuestos, alcance y límites.

Solo texto (sin lógica). Los umbrales numéricos viven en ``framework.py``; ``test_framework_defs`` verifica
que las cifras citadas aquí coincidan con esas constantes. ``framework`` reexporta todo este módulo.
"""
from __future__ import annotations

EV, TS, F360 = 'eventos', 'team-stats', '360'


def _d(nombre: str, definicion: str, formula: str, unidad: str, limites: str, fuente: str) -> dict[str, str]:
    """Una definición del glosario."""
    return {'nombre': nombre, 'definicion': definicion, 'formula': formula, 'unidad': unidad,
            'limites': limites, 'fuente': fuente}


STYLE_NOTE = 'En etiquetas y mapa se usa su percentil frente a la liga (0–100).'
DEF_BASE: dict[str, dict[str, str]] = {
    'coord': _d('Sistema de coordenadas', 'Campo StatsBomb de 120×80 yardas; cada evento en el marco de ataque '
                'de su equipo (ataca hacia x=120). En pantalla el protagonista ataca de izquierda a derecha.',
                'rival: (120-x, 80-y) vía to_frame', 'yardas', 'Los 360 vienen en el marco del equipo actor.', EV),
    'zona': _d('Zona del campo', 'Rejilla de 6 columnas × 3 carriles (20 yd × 26.7 yd).',
               'zona = floor(x/20)·3 + floor(y/26.67)', 'zona 0–17', 'Idéntica a la del simulador.', EV),
    'tercio': _d('Tercio', 'Propio x<40, medio 40–80, final x≥80.', 'umbral en x', 'tercio', 'Marco propio.', EV),
    'secuencia': _d('Posesión (secuencia ofensiva)', 'Posesión de StatsBomb con al menos una acción con balón '
                    '(pase, conducción, regate o tiro) del equipo poseedor; se ignoran las solo administrativas.',
                    'possession id con ≥1 acción con balón', 'posesiones',
                    'Aproximada desde eventos. Se excluye un tiro hecho dentro de una posesión rival (1 de 2,241 tiros '
                    'y menos de una milésima del xG en los 91 partidos de Jardine; se mide en rival_shots de cada an_). La '
                    'jugada que reanuda (córner, tiro libre, saque de banda o de puerta, inicial) no cuenta como '
                    'progresión.', EV),
    'origen': _d('Origen de la posesión', 'Robo en juego, portero, banda, tiro libre, córner, saque inicial u otro.',
                 'tipo de reanudación + posesión previa', 'categoría', 'Robo = posesión previa rival en juego.', EV),
    'salida_limpia': _d('Salida limpia', 'Posesión en juego que nace en x<40 y llega a x≥60 sin perder el balón.',
                        'inicio x<40 y max_x≥60 (solo acciones completadas)', '% de posesiones',
                        'Solo juego abierto.', EV),
    'progresion_limpia': _d('Progresión limpia', 'Posesión que nace en x<60 y llega a x≥80 sin perder el balón.',
                            'inicio x<60 y max_x≥80 (solo acciones completadas)', '% de posesiones',
                            'Solo juego abierto.', EV),
    'creacion': _d('Creación', 'Posesión que entra al área rival o termina en tiro.', 'entrada al área o tiro',
                   '% de posesiones', 'Área: x≥102, 18≤y≤62.', EV),
    'entradas_area': _d('Entradas al área', 'Posesiones propias que llevan el balón al área rival (pase o '
                        'conducción que termina dentro, o tiro).', 'box_entry por posesión', 'por partido',
                        'Área: x≥102, 18≤y≤62.', EV),
    'npxg_por_tiro': _d('Calidad de ocasión (npxG por tiro)', 'xG promedio de los tiros propios sin contar penales.',
                        'Σ xG sin penal / tiros sin penal', 'xG por tiro', 'xG de StatsBomb.', EV),
    'tiros_zona_remate': _d('Tiros desde la zona de remate', 'Porcentaje de tiros sin penal hechos desde la zona '
                            'de remate (x≥102, 30≤y≤50).', 'tiros en zona / tiros', '% de tiros',
                            'Zona central del área.', EV),
    'prog': _d('Acción progresiva', 'Pase o conducción completada (no la primera de un balón parado), desde x≥48, '
               'que acerca el balón a la portería ≥25% y ≥10 yd, o pase completado al área desde fuera.',
               'Δd(120,40) ≥ 25% y ≥ 10 yd', 'acciones/partido', 'Solo acciones completadas.', EV),
    'field_tilt': _d('Dominio territorial (field tilt)', 'Proporción de acciones con balón en el último tercio '
                     'que son propias.', 'propias_tercio_final / (propias + rivales)', '%',
                     'Igual al fieldTilt del simulador.', EV),
    'transicion': _d('Transición ofensiva', 'Posesión nacida de un robo en juego; la fase de transición son sus '
                     'primeros 10 s.', 'origen=robo, t ≤ 10 s', 'posesiones', 'Espejo: transición defensiva.', EV),
    'contraataque': _d('Contraataque', 'Transición que nace en x<60 y termina en tiro en ≤15 s.',
                       'robo x<60 → tiro ≤ 15 s', 'contraataques/partido', 'Compatible con StatsBomb.', EV),
    'perdida': _d('Pérdida', 'Fin de una posesión propia cuando la siguiente posesión no administrativa es rival.',
                  'lossO en juego; lossX* con balón parado', 'pérdidas/partido', 'Como en extract.', EV),
    'perdida_costosa': _d('Pérdida costosa', 'Pérdida en juego seguida de tiro rival en ≤15 s dentro de esa '
                          'posesión rival.', 'lossO → tiro rival ≤ 15 s', 'pérdidas/partido',
                          'Asociación descriptiva, no causal.', EV),
    'perdida_letal': _d('Pérdida letal', 'Pérdida costosa cuyo tiro rival en ≤15 s terminó en gol.',
                        'lossO → gol rival ≤ 15 s', 'pérdidas (total ventana)', 'Asociación descriptiva.', EV),
    'tipo_error': _d('Tipo de error', 'No forzado (pase fallado con xPass≥0.80 sin presión); bajo presión; decisión '
                     'arriesgada (pase adelante con xPass<0.50); duelo perdido; aislado (360: 0 compañeros ≤10 yd).',
                     'reglas en orden', 'categoría', '360 solo ve jugadores visibles.', EV),
    'fase_presion': _d('Fase de presión', 'Por ubicación del balón rival en nuestro marco: alta x≥80, bloque medio '
                       '40–80, bajo x<40.', 'presiones+acciones def. / acciones rivales en la banda', 'por acción',
                       'Marco propio.', EV),
    'ppda': _d('PPDA', 'Pases rivales permitidos por acción defensiva propia en campo de presión.',
               'pases rivales x<72 (su marco) / (intercepción+falta+entrada+regate superado) x≥48', 'pases',
               'Menor = más presión. Con el regate superado correlaciona r=0.98 con el PPDA de StatsBomb.', EV),
    'contrapresion': _d('Contrapresión', 'Presiones marcadas como contrapresión por StatsBomb (en los 5 s '
                        'siguientes a perder el balón).', 'presiones con counterpress', 'presiones/partido',
                        STYLE_NOTE, EV),
    'contrapresion_efectiva': _d('Contrapresión efectiva', 'Tras una pérdida propia en juego, la posesión rival '
                                 'dura ≤5 s y acaba en robo propio.', 'pérdidas recuperadas ≤ 5 s / pérdidas',
                                 '% de pérdidas', 'Solo pérdidas en juego.', EV),
    'rec_campo_rival': _d('Robos en campo rival', 'Recuperaciones en juego con x≥60.', 'robo x ≥ 60', 'robos/partido',
                          'Igual al simulador.', EV),
    'rec_alta': _d('Robos altos', 'Recuperaciones en juego con x≥80.', 'robo x ≥ 80', 'robos/partido',
                   'Igual a high_press_shots de extract.', EV),
    'jugada_peligrosa_concedida': _d('Jugada peligrosa concedida', 'Posesión rival con al menos un tiro; orden: gol, '
                                     'xG de la posesión, OBV máximo, fecha.', 'xG_pos = 1-Π(1-xg)', 'jugadas',
                                     'Etiquetas: penal, balón parado, transición, ataque establecido.', EV),
    'xg_concedido': _d('xG concedido', 'Suma de xG de los tiros rivales (por tipo de jugada).', 'Σ xG rival',
                       'xG por partido', 'Sin penales salvo que se indique.', EV),
    'minutos_jugador': _d('Minutos de un jugador', 'Minutos jugados por un futbolista y su parte de los minutos del equipo '
                          'en la ventana (alineaciones y cambios).', 'minutos del jugador / minutos del equipo',
                          '% de los minutos del equipo', 'Descriptivo: no distingue lesiones ni suspensiones.', EV),
    'formacion': _d('Formación inicial', 'Esquema con el que el equipo inicia el partido, según la alineación '
                    'registrada.', 'partidos con la formación / partidos', '% de los partidos',
                    'La formación registrada no describe el comportamiento durante el juego.', EV),
    'puntos': _d('Puntos por partido', 'Puntos reales del partido: victoria 3, empate 1, derrota 0 (la tanda de '
                'penales no cuenta).', 'Σ puntos / partidos', 'puntos por partido', 'Resultado en tiempo regular.', EV),
    'xg_dif': _d('Diferencia de xG', 'xG sin penales a favor menos xG sin penales en contra, por partido.',
                 'xg − xga', 'xG por partido', 'Usa el xG de team-stats; ver xg y xga.', TS),
    'salida_portero': _d('Salida larga del portero (eventos)', 'Porcentaje de saques de puerta largos y de pases '
                         'largos del portero en juego, contados desde los eventos (largo = 35 yd o más).',
                         'saques o pases largos / saques o pases del portero', '% de acciones',
                         'Distinta de saque_largo (team-stats, proporción del portero).', EV),
    'xg_origen': _d('xG por origen de la jugada', 'xG sin penales por partido de las posesiones que nacen en cada '
                    'origen: robo, portero, banda, tiro libre, córner u otro.', 'Σ xG de posesiones de ese origen / '
                    'partidos', 'xG por partido', 'Desde eventos; no suma exactamente el xG de team-stats.', EV),
    'rec_tiro': _d('Posesiones con tiro tras recuperación', 'Posesiones que terminan en tiro en los 15 s '
                   'siguientes a una recuperación en campo rival (x≥60) o alta (x≥80).',
                   'posesiones con tiro ≤15 s tras robo / partidos', 'posesiones por partido',
                   'Distinta de presion_alta_tiros (team-stats).', EV),
    'x_media_tiros_concedidos': _d('Distancia de los tiros concedidos', 'x media de los tiros rivales vista desde '
                                   'nuestra portería (x=0); menor = más cerca de nuestro arco.', 'media x (marco '
                                   'del protagonista)', 'yardas', 'Marco del protagonista.', EV),
    'bp_peligro': _d('Balón parado de peligro', 'Todos los córners; tiros libres con reanudación en x≥80; saques de '
                     'banda con x≥90 (solo análisis).', 'is_danger_sp', 'jugadas', 'Zonas: área, remate, área chica.', EV),
    'bp_ofensivo': _d('Balón parado a favor', 'xG generado en posesiones nacidas de un balón parado de peligro.',
                      'Σ xG_pos (bp_peligro propio)', 'xG por partido', 'Incluye segundas jugadas de la posesión.', EV),
    'bp_defensivo': _d('Balón parado en contra', 'xG concedido en posesiones rivales nacidas de un balón parado de '
                       'peligro.', 'Σ xG_pos (bp_peligro rival)', 'xG por partido', 'Marcaje inferido con 360.', EV),
    'bp_diferencial': _d('Diferencial de balón parado', 'xG a favor menos xG en contra en balón parado de peligro.',
                         'bp_ofensivo − bp_defensivo', 'xG por partido', 'KPI 7.', EV),
}
DEF_CONTEXT: dict[str, dict[str, str]] = {
    'rival_tier': _d('Nivel del rival', 'Rango del rival por diferencia de xG por partido en su temporada: 1–6 alto, '
                     '7–12 medio, 13–18 bajo (temporada previa si tiene <10 partidos).', 'rango team_season_xgd_pg',
                     'categoría', 'Circular: el rival también jugó contra nosotros.', TS),
    'minuto': _d('Tramo de minuto', '0–15, 16–30, 31–45+, 46–60, 61–75, 76–90+ y prórroga; sin tanda de penales.',
                 'minute_bin', 'tramo', 'El añadido cuenta en el último tramo.', EV),
    'marcador': _d('Marcador', 'Estado del marcador antes de cada acción, visto por el equipo protagonista.',
                   'ganando / empatando / perdiendo', 'categoría', 'Se excluyen autogoles no registrados.', EV),
    'obv': _d('OBV', 'Valor añadido por acción (On-Ball Value) de StatsBomb.', 'Σ obv_total_net',
              'goles esperados', 'Validado contra team_match_obv.', EV),
    'ventana': _d('Ventana', 'Oficial (≤2025-06-30, Ap2021–Cl2025), epílogo o temprano. Las conclusiones solo usan '
                  'la oficial.', 'fecha ≤ 2025-06-30', 'categoría',
                  'Lo demás lleva la insignia "Fuera de ventana". Los percentiles de las conclusiones comparan '
                  'contra equipos-temporada de la ventana oficial; solo el explorador usa la referencia ampliada '
                  '(y lo dice).', EV),
    'encogimiento': _d('Encogimiento hacia el prior', 'Promedio corregido por muestra chica hacia la carrera previa '
                       'del DT o la liga; intervalo del 80%.', '(n·x̄ + 8·μ0)/(n+8)', 'según métrica',
                       'Confianza: <5 muy baja, 5–11 baja, 12–24 media, ≥25 alta.', TS),
    'consistencia': _d('Consistencia', 'Qué tanto se repite el rendimiento entre partidos: dispersión entre partidos '
                       'y banda de ruido por remuestreo (bootstrap, 80%).', 'IQR entre partidos; bootstrap 80%',
                       'según métrica', 'Descriptivo; no implica estabilidad causal.', EV),
    'xpts': _d('Puntos esperados (xPts)', 'Puntos promedio si cada posesión con tiro se repitiera: 20,000 sorteos '
               'por partido con la probabilidad de gol de cada posesión.', '3·P(G) + P(E)', 'puntos por partido',
               'Penales con su xG; autogoles fijos.', EV),
    'resultado_sorpresivo': _d('Resultado sorpresivo', 'Partido cuyo resultado real tenía menos de 20% de '
                               'probabilidad en la repetición con xG.', 'P(resultado real) < 0.20', 'partidos',
                               'Interpretativo, no pronóstico.', EV),
    'xi_base': _d('XI base', 'Los jugadores con más minutos en la ventana, por posición.', 'share de minutos',
                  'jugadores', 'Roles en español; posiciones de StatsBomb.', EV),
    'rotacion': _d('Rotación', 'Cambios promedio en el XI titular respecto del partido anterior.',
                   'Δ XI entre partidos consecutivos', 'jugadores por partido', 'Incluye bajas no observadas.', EV),
    'cambios': _d('Momento de los cambios', 'Minuto medio de cada sustitución y su reparto por marcador.',
                  'minuto de Substitution', 'minuto', 'Se excluyen cambios por lesión no marcados.', EV),
    'impacto_cambio': _d('Impacto descriptivo del cambio', 'Δ xG, OBV y field tilt en los 15 min posteriores contra '
                         'los 15 previos (±2 min excluidos, mismo marcador).', 'después − antes', 'según métrica',
                         'Descriptivo, nunca "efecto".', EV),
}
DEF_STYLE: dict[str, dict[str, str]] = {
    'posesion': _d('Posesión del balón', 'Porcentaje de la posesión del partido (team_match_possession).',
                   'team_match_possession', '% del balón', STYLE_NOTE, TS),
    'verticalidad': _d('Verticalidad', 'Proporción del avance del balón que va directo hacia la portería rival '
                       '(team_match_directness).', 'team_match_directness', 'proporción', STYLE_NOTE, TS),
    'ritmo': _d('Velocidad del ataque', 'Velocidad media con la que el balón avanza hacia la portería rival '
                '(team_match_pace_towards_goal).', 'team_match_pace_towards_goal', 'm/s', STYLE_NOTE, TS),
    'linea': _d('Altura de la defensa', 'Distancia media de las acciones defensivas a la propia portería '
                '(team_match_defensive_distance).', 'team_match_defensive_distance', 'm', STYLE_NOTE, TS),
    'volumen_presion': _d('Volumen de presión', 'Presiones por partido ajustadas por la posesión rival '
                          '(team_match_pressures_adj).', 'team_match_pressures_adj', 'presiones/partido',
                          STYLE_NOTE, TS),
    'presion': _d('PPDA de team-stats (pases del rival por acción defensiva)', 'PPDA de StatsBomb por partido; para el '
                  'percentil se invierte: un percentil alto es un PPDA bajo (el rival hace pocos pases antes de que '
                  'el equipo actúe).', 'team_match_ppda', 'pases por acción defensiva (menos = más presión)', STYLE_NOTE, TS),
    'saque_largo': _d('Saque largo del portero', 'Proporción de pases largos del portero '
                      '(team_match_gk_long_pass_ratio).', 'team_match_gk_long_pass_ratio', 'proporción',
                      STYLE_NOTE, TS),
    'centros': _d('Centros al área', 'Centros al área por partido (team_match_crosses_into_box).',
                  'team_match_crosses_into_box', 'centros/partido', STYLE_NOTE, TS),
    'contragolpe': _d('Tiros al contragolpe', 'Tiros tras contraataque por partido '
                      '(team_match_counter_attacking_shots).', 'team_match_counter_attacking_shots',
                      'tiros/partido', STYLE_NOTE, TS),
    'presion_alta_tiros': _d('Tiros tras robo alto', 'Tiros en los segundos siguientes a un robo alto '
                             '(team_match_high_press_shots).', 'team_match_high_press_shots', 'tiros/partido',
                             STYLE_NOTE, TS),
    'xg': _d('xG a favor', 'Goles esperados sin penales por partido (team_match_np_xg).', 'team_match_np_xg',
             'xG por partido', STYLE_NOTE, TS),
    'xga': _d('xG en contra', 'Goles esperados sin penales concedidos por partido (team_match_np_xg_conceded); '
              'para el percentil se invierte (menor = más sólido).', 'team_match_np_xg_conceded', 'xG por partido',
              STYLE_NOTE, TS),
    'bp_xg': _d('xG a balón parado', 'Goles esperados de jugadas a balón parado por partido (team_match_sp_xg).',
                'team_match_sp_xg', 'xG por partido', STYLE_NOTE, TS),
    'vel_ataque': _d('Velocidad del ataque (eje del mapa)', 'Eje x del mapa ofensivo: media de los percentiles de '
                     'velocidad hacia portería y tiros al contragolpe.', 'round((ritmo + contragolpe) / 2)',
                     'percentil 0–100', 'Señal compuesta; la tarjeta ofensiva sale del cuadrante.', TS),
    'intensidad_presion': _d('Intensidad de presión (eje del mapa)', 'Eje y del mapa defensivo: media de los '
                             'percentiles de volumen de presión, PPDA invertido (alto = deja pocos pases por '
                             'acción defensiva) y contrapresión.', 'round((volumen_presion + presion + '
                             'contrapresion) / 3)', 'percentil 0–100',
                             'Señal compuesta: si volumen y PPDA discrepan, manda el perfil de presión.', TS),
    'perfil_presion': _d('Perfil de presión (regla de coherencia)', 'Volumen, PPDA y contrapresión nunca cuentan '
                         'historias opuestas. Si el volumen es ≥65 y el PPDA invertido ≤45 (con contrapresión '
                         '<75), el equipo "presiona mucho, deja jugar" y la tarjeta es "Línea alta: presiona mucho, '
                         'deja jugar" o "Línea baja: presiona mucho, deja jugar". Si el volumen es ≤45 y el PPDA '
                         'invertido ≥65, la presión es selectiva: "Línea alta, presión selectiva" o "Línea baja, '
                         'presión selectiva". Ese nombre sustituye al del cuadrante; los nombres de cuadrante solo hablan de la '
                         'altura de la línea y de la intensidad combinada, nunca del volumen. "Presión asfixiante" exige las '
                         'tres señales altas y "Espera al rival" las tres bajas con línea baja.',
                         'sin_robo: vol≥65, ppda≤45, cp<75 · selectiva: vol≤45, ppda≥65 · asfixiante: vol≥75, '
                         'ppda≥60, cp≥50 · espera: vol≤30, ppda≤40, cp≤50, línea≤40', 'categoría',
                         'Cada etiqueta declara lo que afirma sobre los percentiles; la auditoría rechaza las que '
                         'no se sostienen.', TS),
}
LB ='Cota inferior: solo jugadores visibles en la toma.'
DEF_360: dict[str, dict[str, str]] = {
    'vigilancias': _d('Vigilancias (defensa de resguardo)', 'Al robo rival tras nuestra pérdida: jugadores propios '
                      'visibles por detrás del balón.', 'conteo en el cuadro 360 del robo', 'jugadores', LB, F360),
    'vigilancias_bajas': _d('Pérdidas con pocas vigilancias', 'Porcentaje de pérdidas en juego con 2 o menos '
                            'jugadores propios visibles detrás del balón al robo rival.', 'vigilancias ≤ 2',
                            '% de pérdidas', LB, F360),
    'altura_linea': _d('Altura de la línea', 'x media de los 3 jugadores de campo más retrasados visibles.',
                       'media x de los 3 más profundos', 'yardas', 'Cuadros con ≥70% de la región visible.', F360),
    'bloque_360': _d('Forma del bloque', 'Con el rival en posesión establecida: altura de la última línea, largo, '
                     'ancho y área (envolvente convexa) del bloque, por zona del balón.', 'convex hull, extremos x/y',
                     'yardas / yd²', 'Región de 25 yd detrás, 10 delante y ±25 a lo ancho del balón; ≥7 visibles.',
                     F360),
    'rompe_lineas': _d('Pases que rompen líneas', 'Pases propios completados hacia adelante que superan rivales '
                       'visibles (packing, cota inferior) o marcados line_breaking_pass.', 'rivales con x0<x<x1',
                       'rivales superados por pase', LB, F360),
    'presion_360': _d('Presión coordinada', 'En cada presión propia: compañeros a ≤10 yd del balón y opciones '
                      'libres del rival (≤15 yd del balón y a >3 yd de cualquier defensor).', 'conteos en el cuadro',
                      'jugadores', LB, F360),
    'corner_def': _d('Organización en córner rival', 'Defensores en área y área chica, emparejamiento (atacantes con '
                     'un defensor a ≤1.5 yd) y tipo de marca inferido: zonal, mixta o al hombre.',
                     'índice de emparejamiento', 'categoría', 'Tipo de marca inferido; tentativo.', F360),
    'contexto_error': _d('Contexto del error', 'En la última acción antes de perder: apoyos a ≤10 yd, rivales a '
                         '≤5 yd, distancia al defensor más cercano, xPass y presión.', 'conteos en el cuadro',
                         'jugadores', LB, F360),
    'forma_cambio': _d('Forma antes y después del cambio', 'Δ altura de línea, ancho, largo y compacidad en 15 min '
                       'antes contra 15 min después de cada sustitución (±2 min excluidos, mismo marcador).',
                       'después − antes', 'yardas', 'Descriptivo; solo forma del equipo.', F360),
}
DEFINITIONS: dict[str, dict[str, str]] = {**DEF_BASE, **DEF_CONTEXT, **DEF_STYLE, **DEF_360}

# KPIs de identidad (plan §6): id del registro, nombre, métricas de apoyo y si "mejor" es alto o bajo.
KPIS = (
    {'id': 'field_tilt', 'nombre': 'Dominio territorial', 'apoyo': (), 'mejor': 'alto'},
    {'id': 'progresion_limpia', 'nombre': 'Progresión limpia', 'apoyo': (), 'mejor': 'alto'},
    {'id': 'npxg_por_tiro', 'nombre': 'Calidad de ocasión', 'apoyo': ('tiros_zona_remate',), 'mejor': 'alto'},
    {'id': 'contrapresion_efectiva', 'nombre': 'Contrapresión efectiva', 'apoyo': (), 'mejor': 'alto'},
    {'id': 'perdida_costosa', 'nombre': 'Pérdidas costosas por partido', 'apoyo': ('tipo_error',), 'mejor': 'bajo'},
    {'id': 'vigilancias', 'nombre': 'Vigilancias 360', 'apoyo': ('vigilancias_bajas',), 'mejor': 'alto'},
    {'id': 'bp_diferencial', 'nombre': 'Diferencial de balón parado', 'apoyo': ('bp_ofensivo', 'bp_defensivo'),
     'mejor': 'alto'},
)

ASSUMPTIONS = (
    'La posesión se aproxima con el identificador de posesión de StatsBomb; no se mide el tiempo de balón en juego.',
    'Los cuadros 360 solo muestran a los jugadores visibles en la toma de televisión: los conteos son cotas inferiores.',
    'Los eventos no registran desmarques sin balón; lo que no toca el balón solo se ve en 360.',
    'La población de referencia 360 son los rivales observados en los mismos partidos, no toda la liga.',
    'Los tipos de marca en balón parado (zonal, mixto, al hombre) se infieren de posiciones; son tentativos.',
    'El nivel del rival es circular: su diferencia de xG incluye el partido contra nosotros.',
    'La región de forma 360 es una ventana alrededor del balón (la toma ve ~22% del campo), no el ancho completo.',
)
SCOPE = (
    'Ventana oficial: Apertura 2021 a Clausura 2025 (hasta 2025-06-30). Las conclusiones solo usan esa ventana.',
    'Epílogo (2025-07-01 en adelante) y muestras tempranas se muestran con la insignia "Fuera de ventana".',
    'Muestras chicas se encogen hacia la carrera previa del DT o la liga (n0 = 8) y llevan intervalo del 80%.',
)
LIMITS = (
    'Las asociaciones son descriptivas, no causales: "en partidos con X sumó Y" no significa que X cause Y.',
    'El simulador es un duelo de estilos dentro del modelo, no un pronóstico.',
    'Sin 360, las métricas de forma (línea, bloque, vigilancias) se marcan como no disponibles, nunca se imputan.',
    'Semáforos de KPIs sobre los terciles propios del DT (P33/P67): comparan al equipo consigo mismo.',
)
