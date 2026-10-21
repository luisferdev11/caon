# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Marco analítico canónico: constantes con nombre, registro DEFINITIONS y helpers geométricos.

Es la única fuente de umbrales. ``/api/framework`` y ``docs/MARCO_ANALITICO.md`` se generan de
``DEFINITIONS``. Coordenadas StatsBomb 120×80 yd; cada evento en el marco de ataque de su equipo (x→120).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Optional

# --- Geometría -------------------------------------------------------------------------------------
PITCH_X = 120.0
PITCH_Y = 80.0
ZONE_NX = 6
ZONE_NY = 3
ZONE_DX = PITCH_X / ZONE_NX  # 20 yd
ZONE_DY = PITCH_Y / ZONE_NY
THIRD_OWN_MAX_X = 40.0
THIRD_FINAL_MIN_X = 80.0
BOX_MIN_X = 102.0
BOX_Y = (18.0, 62.0)
SHOOTING_ZONE_Y = (30.0, 50.0)
SIX_YARD_MIN_X = 114.0
GOAL = (120.0, 40.0)

# --- Tiempos ---------------------------------------------------------------------------------------
TRANSITION_PHASE_S = 10.0   # == extract.T_WINDOW (fase de transición)
OUTCOME_WINDOW_S = 15.0     # contraataque y pérdida costosa (compatible StatsBomb)
COUNTERPRESS_WINDOW_S = 5.0
PACE_FLOOR_S = 0.5          # piso de duración entre acciones para el ritmo

# --- Umbrales con nombre (uno por concepto) --------------------------------------------------------
REC_CAMPO_RIVAL_X = 60.0    # = simulador "Robos en campo rival" (colOf(z) >= 3)
REC_ALTA_X = 80.0           # = extract high_press_shots
PPDA_DEF_MIN_X = 48.0       # acciones defensivas propias contadas desde x >= 48
PPDA_OPP_MAX_X = 72.0       # pases rivales contados en x < 72 (su marco)
SALIDA_LIMPIA = (40.0, 60.0)
PROGRESION_LIMPIA = (60.0, 80.0)
PROG_MIN_START_X = 48.0
PROG_MIN_REDUCTION = 0.25
PROG_MIN_YARDS = 10.0
DANGER_FK_MIN_X = 80.0
DANGER_THROW_MIN_X = 90.0
XPASS_EASY = 0.80
XPASS_RISKY = 0.50
PRESSURE_RADIUS_YD = 3.0
ISOLATION_RADIUS_YD = 10.0
TIER_SIZE = 6
TIER_MIN_MATCHES = 10
SHRINK_N0 = 8
CI_LEVEL = 0.80
CONFIDENCE_BANDS = ((5, 'muy baja'), (12, 'baja'), (25, 'media'))  # n < límite → etiqueta; si no 'alta'
OFFICIAL_END = '2025-06-30'
WINDOWS = ('oficial', 'epilogo', 'temprano')
SOURCES = ('eventos', 'team-stats', '360')
MINUTE_BINS = ((15, '0-15'), (30, '16-30'))
MINUTE_BINS_2H = ((60, '46-60'), (75, '61-75'))


def zone(loc: Sequence[float]) -> int:
    """Zona 6×3 (columna*3 + fila), idéntica a ``extract.zone``."""
    x = min(max(loc[0], 0), 119.999)
    y = min(max(loc[1], 0), 79.999)
    return int(x // ZONE_DX) * ZONE_NY + int(y // (PITCH_Y / ZONE_NY))


def to_frame(loc: Sequence[float], flip: bool) -> list[float]:
    """Única inversión de marco: (x, y) → (120-x, 80-y) si ``flip``."""
    if not flip:
        return [float(loc[0]), float(loc[1])]
    return [PITCH_X - loc[0], PITCH_Y - loc[1]]


def third(x: float) -> str:
    """Tercio del campo en el marco propio: propio, medio o final."""
    if x < THIRD_OWN_MAX_X:
        return 'propio'
    return 'medio' if x < THIRD_FINAL_MIN_X else 'final'


def minute_bin(minute: int, period: int) -> Optional[str]:
    """Tramo de 15 min; añadido en 45+/90+; prórroga aparte; tanda de penales (period 5) → None."""
    if period >= 5:
        return None
    if period >= 3:
        return 'prorroga'
    bins = MINUTE_BINS if period == 1 else MINUTE_BINS_2H
    for limit, name in bins:
        if minute <= limit:
            return name
    return '31-45+' if period == 1 else '76-90+'


def rival_tier(team_id: int, season_rows: list[dict[str, Any]]) -> Optional[str]:
    """Nivel del rival por rango de ``team_season_xgd_pg`` en su temporada: 1–6 alto, 7–12 medio, resto bajo."""
    ranked = sorted((r for r in season_rows if r.get('team_season_xgd_pg') is not None),
                    key=lambda r: -r['team_season_xgd_pg'])
    ids = [r['team_id'] for r in ranked]
    if team_id not in ids:
        return None
    pos = ids.index(team_id)
    if pos < TIER_SIZE:
        return 'alto'
    return 'medio' if pos < 2 * TIER_SIZE else 'bajo'


def is_danger_sp(kind: str, loc: Sequence[float]) -> bool:
    """Balón parado de peligro: todo córner; tiro libre con x ≥ 80; saque de banda con x ≥ 90."""
    if kind == 'corner':
        return True
    if kind == 'fk':
        return loc[0] >= DANGER_FK_MIN_X
    if kind == 'throw':
        return loc[0] >= DANGER_THROW_MIN_X
    return False


def in_box(loc: Sequence[float]) -> bool:
    """Dentro del área rival (x ≥ 102, 18 ≤ y ≤ 62)."""
    return loc[0] >= BOX_MIN_X and BOX_Y[0] <= loc[1] <= BOX_Y[1]


def confidence(n: int) -> str:
    """Banda de confianza por tamaño de muestra."""
    for limit, name in CONFIDENCE_BANDS:
        if n < limit:
            return name
    return 'alta'


def shrink(mean: float, n: int, prior: float, n0: int = SHRINK_N0) -> float:
    """Encogimiento hacia el prior: (n·x̄ + n0·μ0)/(n + n0)."""
    return (n * mean + n0 * prior) / (n + n0)


def check_metric_record(rec: dict[str, Any]) -> list[str]:
    """Errores de contrato de un registro de métrica (lista vacía = válido)."""
    errs = []
    for k in ('id', 'value', 'n', 'unit', 'source', 'window'):
        if k not in rec:
            errs.append(f'falta {k}')
    if rec.get('id') not in DEFINITIONS:
        errs.append('id desconocido: {}'.format(rec.get('id')))
    if 'window' in rec and rec['window'] not in WINDOWS:
        errs.append('ventana inválida: {}'.format(rec['window']))
    if 'source' in rec and rec['source'] not in SOURCES:
        errs.append('fuente inválida: {}'.format(rec['source']))
    return errs



def _d(nombre: str, definicion: str, formula: str, unidad: str, limites: str, fuente: str) -> dict[str, str]:
    """Una definición del glosario."""
    return {'nombre': nombre, 'definicion': definicion, 'formula': formula, 'unidad': unidad,
            'limites': limites, 'fuente': fuente}


EV, TS, F360 = 'eventos', 'team-stats', '360'
DEFINITIONS: dict[str, dict[str, str]] = {
    'coord': _d('Sistema de coordenadas', 'Campo StatsBomb de 120×80 yardas; cada evento en el marco de ataque '
                'de su equipo (ataca hacia x=120). En pantalla el protagonista ataca de izquierda a derecha.',
                'rival: (120-x, 80-y) vía to_frame', 'yardas', 'Los 360 vienen en el marco del equipo actor.', EV),
    'zona': _d('Zona del campo', 'Rejilla de 6 columnas × 3 carriles (20 yd × 26.7 yd).',
               'zona = floor(x/20)·3 + floor(y/26.67)', 'zona 0–17', 'Idéntica a la del simulador.', EV),
    'tercio': _d('Tercio', 'Propio x<40, medio 40–80, final x≥80.', 'umbral en x', 'tercio', 'Marco propio.', EV),
    'posesion': _d('Posesión (secuencia ofensiva)', 'Posesión de StatsBomb con al menos una acción con balón '
                   '(pase, conducción, regate o tiro) del equipo poseedor; se ignoran las solo administrativas.',
                   'possession id con ≥1 acción con balón', 'posesiones', 'Aproximada desde eventos.', EV),
    'origen': _d('Origen de la posesión', 'Robo en juego, portero, banda, tiro libre, córner, saque inicial u otro.',
                 'tipo de reanudación + posesión previa', 'categoría', 'Robo = posesión previa rival en juego.', EV),
    'salida_limpia': _d('Salida limpia', 'Posesión en juego que nace en x<40 y llega a x≥60 sin perder el balón.',
                        'inicio x<40 y max_x≥60', '% de posesiones', 'Solo juego abierto.', EV),
    'progresion_limpia': _d('Progresión limpia', 'Posesión que nace en x<60 y llega a x≥80 sin perder el balón.',
                            'inicio x<60 y max_x≥80', '% de posesiones', 'Solo juego abierto.', EV),
    'creacion': _d('Creación', 'Posesión que entra al área rival o termina en tiro.', 'entrada al área o tiro',
                   '% de posesiones', 'Área: x≥102, 18≤y≤62.', EV),
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
                          'posesión rival; "letal" si fue gol.', 'lossO → tiro rival ≤ 15 s', 'pérdidas/partido',
                          'Asociación descriptiva, no causal.', EV),
    'tipo_error': _d('Tipo de error', 'No forzado (pase fallado con xPass≥0.80 sin presión); bajo presión; decisión '
                     'arriesgada (pase adelante con xPass<0.50); duelo perdido; aislado (360: 0 compañeros ≤10 yd).',
                     'reglas en orden', 'categoría', '360 solo ve jugadores visibles.', EV),
    'fase_presion': _d('Fase de presión', 'Por ubicación del balón rival en nuestro marco: alta x≥80, bloque medio '
                       '40–80, bajo x<40.', 'presiones+acciones def. / acciones rivales en la banda', 'por acción',
                       'Marco propio.', EV),
    'ppda': _d('PPDA', 'Pases rivales permitidos por acción defensiva propia en campo de presión.',
               'pases rivales x<72 (su marco) / (intercepción+falta+entrada) x≥48', 'pases', 'Menor = más presión.', EV),
    'contrapresion': _d('Contrapresión', 'Presión marcada counterpress; recuperación por contrapresión: tras nuestra '
                        'pérdida, la posesión rival dura ≤5 s y acaba en robo propio.', 'rival ≤ 5 s → robo',
                        '% de pérdidas', 'Solo pérdidas en juego.', EV),
    'rec_campo_rival': _d('Robos en campo rival', 'Recuperaciones en juego con x≥60.', 'robo x ≥ 60', 'robos/partido',
                          'Igual al simulador.', EV),
    'rec_alta': _d('Robos altos', 'Recuperaciones en juego con x≥80.', 'robo x ≥ 80', 'robos/partido',
                   'Igual a high_press_shots de extract.', EV),
    'jugada_peligrosa_concedida': _d('Jugada peligrosa concedida', 'Posesión rival con al menos un tiro; orden: gol, '
                                     'xG de la posesión, OBV máximo, fecha.', 'xG_pos = 1-Π(1-xg)', 'jugadas',
                                     'Etiquetas: penal, balón parado, transición, ataque establecido.', EV),
    'bp_peligro': _d('Balón parado de peligro', 'Todos los córners; tiros libres con reanudación en x≥80; saques de '
                     'banda con x≥90 (solo análisis).', 'is_danger_sp', 'jugadas', 'Zonas: área, remate, área chica.', EV),
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
                  'la oficial.', 'fecha ≤ 2025-06-30', 'categoría', 'Lo demás lleva la insignia "Fuera de ventana".', EV),
    'encogimiento': _d('Encogimiento hacia el prior', 'Promedio corregido por muestra chica hacia la carrera previa '
                       'del DT o la liga; intervalo del 80%.', '(n·x̄ + 8·μ0)/(n+8)', 'según métrica',
                       'Confianza: <5 muy baja, 5–11 baja, 12–24 media, ≥25 alta.', TS),
    'vigilancias': _d('Vigilancias (defensa de resguardo)', 'Al robo rival tras nuestra pérdida: jugadores propios '
                      'visibles por detrás del balón.', 'conteo en el cuadro 360 del robo', 'jugadores',
                      'Cota inferior: solo jugadores visibles.', F360),
    'altura_linea': _d('Altura de la línea', 'x media de los 3 jugadores de campo más retrasados visibles.',
                       'media x de los 3 más profundos', 'yardas', 'Cuadros con ≥70% de la región visible.', F360),
}

ASSUMPTIONS = (
    'La posesión se aproxima con el identificador de posesión de StatsBomb; no se mide el tiempo de balón en juego.',
    'Los cuadros 360 solo muestran a los jugadores visibles en la toma de televisión: los conteos son cotas inferiores.',
    'Los eventos no registran desmarques sin balón; lo que no toca el balón solo se ve en 360.',
    'La población de referencia 360 son los rivales observados en los mismos partidos, no toda la liga.',
    'Los tipos de marca en balón parado (zonal, mixto, al hombre) se infieren de posiciones; son tentativos.',
    'El nivel del rival es circular: su diferencia de xG incluye el partido contra nosotros.',
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
)


def render_marco() -> str:
    """Texto Markdown de docs/MARCO_ANALITICO.md, generado desde DEFINITIONS y las listas de supuestos."""
    lines = ['# Marco analítico', '',
             ('Documento generado por `pipeline/framework.py` (`render_marco`). No editar a mano: '
             'cambia `DEFINITIONS` y vuelve a generarlo. La misma fuente alimenta `/api/framework`.'), '',
             '## Definiciones', '']
    for key, d in DEFINITIONS.items():
        lines += ['### {} (`{}`)'.format(d['nombre'], key), '', d['definicion'], '',
                  '- **Fórmula:** {}'.format(d['formula']), '- **Unidad:** {}'.format(d['unidad']),
                  '- **Límites:** {}'.format(d['limites']), '- **Fuente:** {}'.format(d['fuente']), '']
    for title, items in (('Supuestos', ASSUMPTIONS), ('Alcance', SCOPE), ('Límites', LIMITS)):
        lines += ['## ' + title, ''] + ['- ' + t for t in items] + ['']
    lines += ['## Umbrales con nombre', '', '| Constante | Valor |', '|---|---|']
    lines += [f'| `{k}` | {v} |' for k, v in globals().items()
              if k.isupper() and isinstance(v, (int, float)) and not isinstance(v, bool)]
    return '\n'.join(lines) + '\n'


def framework_payload() -> dict[str, Any]:
    """Payload de /api/framework: definiciones, supuestos, alcance y límites."""
    return {'definitions': DEFINITIONS, 'assumptions': list(ASSUMPTIONS), 'scope': list(SCOPE),
            'limits': list(LIMITS), 'windows': list(WINDOWS), 'official_end': OFFICIAL_END}


if __name__ == '__main__':
    import pathlib
    out = pathlib.Path(__file__).resolve().parents[1] / 'docs' / 'MARCO_ANALITICO.md'
    out.write_text(render_marco(), encoding='utf-8')
    print('escrito', out)
