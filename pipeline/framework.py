# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Marco analítico canónico: constantes con nombre, registro DEFINITIONS y helpers geométricos.

Es la única fuente de umbrales. ``/api/framework`` y ``docs/MARCO_ANALITICO.md`` se generan de
``DEFINITIONS`` (textos en ``framework_defs.py``). Coordenadas StatsBomb 120×80 yd; cada evento en el marco
de ataque de su equipo (x→120).
"""
from __future__ import annotations

import importlib
import importlib.util
import math
import pathlib
import sys
from collections.abc import Sequence
from types import ModuleType
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
SHOOTOUT_PERIOD = 5         # tanda de penales: fuera de todo análisis
SUB_WINDOW_MIN = 15         # forma/impacto 15 min antes y después de un cambio
SUB_GAP_MIN = 2             # ±2 min alrededor del cambio excluidos

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
SURPRISE_P = 0.20           # "resultado sorpresivo": P(resultado real) < 0.20
KPI_TRAFFIC_PCT = (33, 67)  # semáforo de KPIs en los terciles propios del DT
VIG_LOW_MAX = 2             # "pocas vigilancias": ≤2 jugadores visibles detrás del balón

# --- 360 (puerta de visibilidad y radios; frames360 debe importarlos de aquí) -----------------------
GRID_STEP_YD = 2.0            # muestreo de la región de interés (ROI) en malla de 2 yd
MIN_ROI_VISIBLE = 0.70        # cuadro válido si ≥70 % de la ROI es visible
MIN_SHAPE_PLAYERS = 7         # forma del bloque solo con ≥7 jugadores de campo visibles
DEEP_LINE_N = 3               # altura de línea = media x de los 3 más retrasados
ROI_BACK_YD = 25.0            # ROI de forma: 25 yd detrás del balón ...
ROI_FRONT_YD = 10.0           # ... 10 yd delante ...
ROI_HALF_WIDTH_YD = 25.0      # ... y ±25 yd a lo ancho
ERROR_OPP_RADIUS_YD = 5.0     # rivales cercanos al error
PRESS_SUPPORT_RADIUS_YD = 10.0  # compañeros que acompañan la presión
FREE_OPTION_RADIUS_YD = 15.0  # opciones de pase del rival cerca del balón
FREE_OPTION_MARGIN_YD = 3.0   # opción libre si ningún defensor está a ≤3 yd
PAIRING_RADIUS_YD = 1.5       # atacante emparejado si un defensor está a ≤1.5 yd

OFFICIAL_END = '2025-06-30'

# --- Analítica por tema (constantes movidas desde analytics/*: un solo valor por concepto) ------------
REPLAY_DRAWS = 20000          # sorteos por partido de la repetición con xG
DESERVED_P = 0.50             # "mereció ganar / perder" si esa probabilidad es >= 0.50
BALANCE_PTS = 1.0             # |puntos - xPts| <= 1 -> resultado acorde a las ocasiones
BIG_CHANCE_XG = 0.30          # "gran ocasion": tiro con xG >= 0.30
EPILOGUE_END = '2026-06-30'   # fin del epilogo (temporada 2025/26); despues = evidencia temprana
REF_MIN_MATCHES = 10          # partidos minimos de un equipo-temporada para entrar a una referencia
LONG_PASS_YD = 35.0           # pase largo (convencion StatsBomb "long ball")
DANGEROUS_TOP_N = 10          # jugadas peligrosas publicadas por categoria
DANGEROUS_MAX_ACTIONS = 15    # acciones dibujadas por jugada peligrosa
DANGEROUS_PAYLOAD_MAX_BYTES = 250_000
PROGRESSORS_TOP = 8           # jugadores listados en progresion
LOSS_PLAYERS_TOP = 10         # jugadores listados en perdidas
SHORT_CORNER_YD = 15.0        # corner corto: pase de menos de 15 yd (= extract.corner_target)
CONTACT_SCAN_EVENTS = 8       # eventos tras el corner en los que se busca el primer contacto
SETPIECES_TOP_N = 5           # rematadores y zonas listados en balon parado
BOOT_DRAWS = 1000             # remuestreos bootstrap de las bandas del contexto
REGULAR_STAGES = ('Regular Season', 'Apertura', 'Clausura')  # lo demas (play-in, liguilla) va aparte
CONSISTENCY_MIN_INSIDE = 3    # partido "a su manera": >=3 de los 5 rasgos dentro del IQR propio
CONSISTENCY_MIN_MATCHES = REF_MIN_MATCHES   # minimo de partidos para el indice de consistencia
FINDINGS_TOP = 12             # hallazgos de contexto ordenados que se publican
XI_SIZE = 11                  # once titular
SQUAD_TOP = 25                # jugadores listados en la plantilla
HALFTIME_MINUTE = 45          # minuto de StatsBomb al reanudar el segundo tiempo
WINDOWS = ('oficial', 'epilogo', 'temprano')
SOURCES = ('eventos', 'team-stats', '360')
MINUTE_BINS = ((15, '0-15'), (30, '16-30'))
MINUTE_BINS_2H = ((60, '46-60'), (75, '61-75'))
ROUND_DIGITS = 4
MISSING_REASON = 'sin dato suficiente'


def _sibling(name: str) -> ModuleType:
    """Importa un módulo hermano de ``pipeline/`` aunque este archivo se haya cargado por ruta."""
    try:
        return importlib.import_module(name)
    except ImportError:
        if name in sys.modules:
            return sys.modules[name]
        spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(f'{name}.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module


_defs = _sibling('framework_defs')
DEFINITIONS: dict[str, dict[str, str]] = _defs.DEFINITIONS
KPIS: tuple = _defs.KPIS
ASSUMPTIONS: tuple = _defs.ASSUMPTIONS
SCOPE: tuple = _defs.SCOPE
LIMITS: tuple = _defs.LIMITS


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
    if period >= SHOOTOUT_PERIOD:
        return None
    if period >= 3:
        return 'prorroga'
    bins = MINUTE_BINS if period == 1 else MINUTE_BINS_2H
    for limit, name in bins:
        if minute <= limit:
            return name
    return '31-45+' if period == 1 else '76-90+'


def window_of(date: Optional[str]) -> Optional[str]:
    """Ventana por fecha ISO: 'oficial' hasta OFFICIAL_END, si no 'epilogo' ('temprano' lo asigna la entidad)."""
    if not date:
        return None
    return 'oficial' if str(date)[:10] <= OFFICIAL_END else 'epilogo'


def _tier_of(team_id: int, rows: list[dict[str, Any]]) -> Optional[str]:
    ranked = sorted((r for r in rows if r.get('team_season_xgd_pg') is not None),
                    key=lambda r: -r['team_season_xgd_pg'])
    ids = [r['team_id'] for r in ranked]
    if team_id not in ids:
        return None
    pos = ids.index(team_id)
    if pos < TIER_SIZE:
        return 'alto'
    return 'medio' if pos < 2 * TIER_SIZE else 'bajo'


def rival_tier(team_id: int, season_rows: list[dict[str, Any]],
               prev_rows: Optional[list[dict[str, Any]]] = None) -> Optional[str]:
    """Nivel del rival por rango de ``team_season_xgd_pg``: 1–6 alto, 7–12 medio, resto bajo.

    Si el rival tiene menos de TIER_MIN_MATCHES partidos en la temporada y aparece en ``prev_rows``
    (temporada previa), se usa esa; si no, la actual.
    """
    row = next((r for r in season_rows if r.get('team_id') == team_id), None)
    short = row is not None and (row.get('team_season_matches') or 0) < TIER_MIN_MATCHES
    if short and prev_rows:
        prev = _tier_of(team_id, prev_rows)
        if prev is not None:
            return prev
    return _tier_of(team_id, season_rows)


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


def metric(mid: str, value: Optional[float], n: int, unit: str, source: str, window: str,
           motivo: Optional[str] = None, **extra: Any) -> dict[str, Any]:
    """Registro de métrica del contrato; valor ausente o no finito → null con ``motivo``.

    Lanza KeyError si ``mid`` no está en DEFINITIONS y ValueError si la ventana o la fuente no existen.
    """
    if mid not in DEFINITIONS:
        raise KeyError(f'id de métrica desconocido: {mid}')
    if window not in WINDOWS or source not in SOURCES:
        raise ValueError(f'ventana o fuente inválida: {window} / {source}')
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    rec: dict[str, Any] = {'id': mid, 'value': round(float(value), ROUND_DIGITS) if ok else None, 'n': int(n),
                           'unit': unit, 'source': source, 'window': window}
    if not ok:
        rec['motivo'] = motivo or MISSING_REASON
    rec.update(extra)
    return rec


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


def thresholds() -> dict[str, Any]:
    """Constantes numéricas con nombre (y pares de umbrales) de este módulo."""
    def numeric(v: Any) -> bool:
        if isinstance(v, tuple):
            return bool(v) and all(isinstance(x, (int, float)) for x in v)
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in globals().items()
            if k.isupper() and not k.startswith('_') and numeric(v)}


def label_rules() -> dict[str, Any]:
    """Reglas del motor de etiquetas (``labels``) para el glosario y /api/framework."""
    lab = _sibling('labels')
    profiles = {k: {'texto': p['texto'], 'afirma': {s: lab.int_bounds(r) for s, r in p['claims'].items()}}
                for k, p in lab.PRESS_PROFILES.items()}
    qualified = [{'linea': side, 'perfil': prof, 'nombre': name} for (side, prof), name in lab.DFN_QUALIFIED.items()]
    return {'cuadrantes': lab.QUADRANTS, 'ejes': lab.AXES, 'combinada': lab.COMBINED, 'selectiva': lab.SELECTIVE,
            'sin_robo': lab.SIN_ROBO, 'perfiles_presion': profiles, 'calificados': qualified,
            'nombres_calificados': list(lab.DFN_QUALIFIED.values()),
            'conflictos': [list(c) for c in lab.conflict_pairs()], 'extremo_alto': lab.HI, 'extremo_bajo': lab.LO,
            'banda_central': lab.CENTER_BAND}


def _marco_definitions() -> list[str]:
    lines = ['## Definiciones', '']
    for key, d in DEFINITIONS.items():
        lines += ['### {} (`{}`)'.format(d['nombre'], key), '', d['definicion'], '',
                  '- **Fórmula:** {}'.format(d['formula']), '- **Unidad:** {}'.format(d['unidad']),
                  '- **Límites:** {}'.format(d['limites']), '- **Fuente:** {}'.format(d['fuente']), '']
    return lines


def _marco_kpis() -> list[str]:
    lines = ['## KPIs de identidad', '',
             'Cada KPI lleva semáforo en los terciles propios del DT (P{}/P{}) y la frase descriptiva "en partidos '
             'en verde sumó X pts/partido".'.format(*KPI_TRAFFIC_PCT), '',
             '| # | KPI | Métrica (`id`) | Apoyo | Mejor |', '|---|---|---|---|---|']
    for i, k in enumerate(KPIS, 1):
        apoyo = ', '.join(f'`{a}`' for a in k['apoyo']) or '—'
        lines.append('| {} | {} | `{}` | {} | {} |'.format(i, k['nombre'], k['id'], apoyo, k['mejor']))
    return lines + ['']


def _marco_labels() -> list[str]:
    r = label_rules()
    lines = ['## Motor de etiquetas', '',
             'Una sola función (`labels.identity`) produce tarjetas, etiquetas y puntos del mapa: la tarjeta '
             '"Enfoque defensivo" es el cuadrante del mapa defensivo. Extremos: percentil ≥{} o ≤{}; centro '
             '"Equilibrado" si ambos ejes están a menos de {} puntos de 50.'.format(
                 r['extremo_alto'], r['extremo_bajo'], r['banda_central']), '',
             '- **Mapa ofensivo:** x = {}, y = {}.'.format(*r['ejes']['off']),
             '- **Mapa defensivo:** x = {}, y = {} (media de volumen de presión, PPDA invertido y '
             'contrapresión).'.format(*r['ejes']['dfn']),
             '- **Regla combinada:** "{}" (verticalidad alta con ritmo bajo; sustituye a las dos etiquetas '
             'sueltas).'.format(r['combinada']),
             '- **Presión selectiva:** "{}".'.format(r['selectiva']), '',
             '| Cuadrante ofensivo | | Cuadrante defensivo | |', '|---|---|---|---|']
    for pos in ('tl', 'tr', 'bl', 'br'):
        lines.append('| {} | {} | {} | {} |'.format(pos, r['cuadrantes']['off'][pos], pos, r['cuadrantes']['dfn'][pos]))
    lines += _marco_pressing(r)
    lines += ['', 'Pares excluyentes (nunca aparecen juntos; incluye los deducidos de afirmaciones disjuntas):', '']
    lines += [f'- {a} ↔ {b}' for a, b in r['conflictos']]
    return lines + ['']


def _marco_pressing(r: dict[str, Any]) -> list[str]:
    d = DEFINITIONS['perfil_presion']
    lines = ['', '### Regla de presión', '', d['definicion'], '',
             '| Perfil | Texto | Afirma (percentiles) |', '|---|---|---|']
    for key, p in r['perfiles_presion'].items():
        claims = ', '.join(f'{s} {lo}–{hi}' for s, (lo, hi) in p['afirma'].items())
        lines.append(f"| `{key}` | {p['texto']} | {claims} |")
    lines += ['', '| Línea | Perfil | Tarjeta y nombre en el mapa |', '|---|---|---|']
    lines += [f"| {q['linea']} | `{q['perfil']}` | {q['nombre']} |" for q in r['calificados']]
    return lines


def render_marco() -> str:
    """Texto Markdown de docs/MARCO_ANALITICO.md, generado desde DEFINITIONS, KPIS y el motor de etiquetas."""
    lines = ['# Marco analítico', '',
             ('Documento generado por `pipeline/framework.py` (`render_marco`). No editar a mano: '
              'cambia `DEFINITIONS` (en `framework_defs.py`) y vuelve a generarlo. La misma fuente alimenta '
              '`/api/framework`.'), '']
    lines += _marco_definitions() + _marco_kpis() + _marco_labels()
    for title, items in (('Supuestos', ASSUMPTIONS), ('Alcance', SCOPE), ('Límites', LIMITS)):
        lines += ['## ' + title, ''] + ['- ' + t for t in items] + ['']
    lines += ['## Umbrales con nombre', '', '| Constante | Valor |', '|---|---|']
    lines += [f'| `{k}` | {v} |' for k, v in thresholds().items()]
    return '\n'.join(lines) + '\n'


def framework_payload() -> dict[str, Any]:
    """Payload de /api/framework: definiciones, KPIs, etiquetas, umbrales, supuestos, alcance y límites."""
    return {'definitions': DEFINITIONS, 'kpis': [dict(k, apoyo=list(k['apoyo'])) for k in KPIS],
            'etiquetas': label_rules(), 'thresholds': thresholds(), 'assumptions': list(ASSUMPTIONS),
            'scope': list(SCOPE), 'limits': list(LIMITS), 'windows': list(WINDOWS), 'official_end': OFFICIAL_END}


if __name__ == '__main__':
    out = pathlib.Path(__file__).resolve().parents[1] / 'docs' / 'MARCO_ANALITICO.md'
    out.write_text(render_marco(), encoding='utf-8')
    print('escrito', out)
