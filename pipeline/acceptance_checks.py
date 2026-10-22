# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Checks reales de aceptación (AC-03…AC-15) sobre payloads ya cargados; ``acceptance.py`` los conecta a su registro.

Cada función recibe datos (dicts, texto o un detector) y devuelve ``(estado, evidencia)``; ``None`` en la entrada
principal significa que el artefacto aún no existe → ``PENDING``. Nada aquí lee disco ni red.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Optional

OK, FAIL, PENDING = 'ok', 'fail', 'pending'
Result = tuple[str, str]
JARDINE_N, JARDINE_EPI_N, PACHUCA_MIN_PCT = 91, 38, 0.90
DANGEROUS_MAX_BYTES, DANGEROUS_TOP, SHOT_X_MAX = 250 * 1024, 10, 25
RULES_MIN_PCT, LLM_MODELS_MIN = 90, 3
SHAPE_BLOCKS = ('bloque', 'cambios', 'corners', 'cordura', 'errores', 'kpi')
LIST_KEYS = ('juego_abierto', 'balon_parado', 'penales')
FORECAST_LABEL = 'no es un pronóstico'


def _dig(node: Any, *path: str) -> Any:
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
    return node


def _verdict(problems: list, ok_text: str) -> Result:
    return (FAIL, '; '.join(problems)) if problems else (OK, ok_text)


# ---------------------------------------------------------------- AC-03
def ac03(model: dict, rows_jardine: list, rows_pachuca: list, have: Optional[Callable[[str, Any], bool]]) -> Result:
    """Jardine n=91 oficial y epílogo n=38; 100 % de Jardine con mx_, an_ y f360_; Pachuca ≥90 % con eventos."""
    ents = {e.get('id'): e for e in (model or {}).get('entities', [])}
    j, epi = ents.get('ame_jardine'), ents.get('ame_jardine_epi')
    problems = []
    if not j or j.get('n') != JARDINE_N or j.get('official') is not True:
        problems.append(f"ame_jardine n={(j or {}).get('n')} oficial={(j or {}).get('official')}")
    if not epi or epi.get('n') != JARDINE_EPI_N:
        problems.append(f"ame_jardine_epi n={(epi or {}).get('n')}")
    if 'pac_almada' not in ents:
        problems.append('pac_almada ausente')
    if problems or have is None:
        return (FAIL, '; '.join(problems)) if problems else (PENDING, 'sin data/extract para verificar la cobertura')
    for kind in ('mx', 'an', 'f360'):
        miss = [r['match_id'] for r in rows_jardine if not have(kind, r['match_id'])]
        if miss:
            problems.append(f'{kind}: faltan {len(miss)} de {len(rows_jardine)} partidos de Jardine')
    ev = [r['match_id'] for r in rows_pachuca if have('events', r['match_id'])]
    if rows_pachuca and len(ev) / len(rows_pachuca) < PACHUCA_MIN_PCT:
        problems.append(f'pac_almada con eventos {len(ev)}/{len(rows_pachuca)}')
    return _verdict(problems, f'Jardine n={JARDINE_N} con mx_/an_/f360_ al 100 %; epílogo n={JARDINE_EPI_N}; '
                              f'pac_almada con eventos {len(ev)}/{len(rows_pachuca)}')


# ---------------------------------------------------------------- AC-06 y AC-15
def ac06(story: Optional[dict]) -> Result:
    """Doce capítulos con hallazgos y cada componente del reto con al menos un hallazgo con evidencia."""
    if story is None:
        return PENDING, 'model/story/jardine.json aún no existe'
    problems = []
    chapters = story.get('capitulos') or []
    empty = [c.get('orden') for c in chapters if not c.get('hallazgos')]
    if len(chapters) != 12 or empty:
        problems.append(f'{len(chapters)} capítulos; sin hallazgos: {empty}')
    uncovered = [k for k, v in (story.get('cobertura') or {}).items() if not v]
    if uncovered:
        problems.append('componentes sin hallazgo: ' + ', '.join(uncovered))
    n = sum(len(c.get('hallazgos') or []) for c in chapters)
    return _verdict(problems, f'12 capítulos, {n} hallazgos y {len(story.get("cobertura") or {})} componentes cubiertos')


def _windows(chapter: dict) -> set:
    return {f.get('window') for f in chapter.get('hallazgos') or []} | {
        e.get('window') for f in chapter.get('hallazgos') or [] for e in f.get('evidencia') or []}


def ac15(jardine: Optional[dict], almada: Optional[dict]) -> Result:
    """Capítulos 1–11 solo con ventana oficial; epílogo y Almada en el América marcados como fuera de ventana."""
    if jardine is None:
        return PENDING, 'model/story/jardine.json aún no existe'
    problems = []
    for c in jardine.get('capitulos') or []:
        want = {'epilogo'} if c.get('orden') == 12 else {'oficial'}
        extra = _windows(c) - want - {None}
        if extra:
            problems.append(f"capítulo {c.get('orden')} con ventana {sorted(extra)}")
    if almada is not None:
        chs = almada.get('capitulos') or []
        if len(chs) >= 2 and (_windows(chs[0]) - {'oficial', None} or _windows(chs[1]) - {'temprano', None}):
            problems.append('Almada mezcla ventanas')
        if not almada.get('evidencia_temprana'):
            problems.append('Almada sin bandera de evidencia temprana')
    return _verdict(problems, 'conclusiones solo en la ventana oficial; epílogo y evidencia temprana marcados')


# ---------------------------------------------------------------- AC-07 y AC-08
def ac07(analysis: Optional[dict]) -> Result:
    """Vigilancias, contexto del error, bloque, rompe-líneas, cambios y córner, con cobertura y cordura aprobada."""
    if analysis is None:
        return PENDING, 'analysis de Jardine aún no existe'
    win = _dig(analysis, 'shape360', 'ventanas', 'oficial') or {}
    problems = [f'falta {k}' for k in SHAPE_BLOCKS if not win.get(k)]
    if not _dig(win, 'kpi', 'coverage', 'n_valid'):
        problems.append('vigilancias sin cobertura n_valid')
    if not (win.get('metricas') or {}).get('rompe_pct'):
        problems.append('falta rompe-líneas')
    for k in ('tipos', 'zonas', 'jugadores'):
        if not _dig(win, 'errores', k):
            problems.append(f'errores sin {k}')
    if not _dig(win, 'cambios', 'validos'):
        problems.append('cambios sin momentos válidos')
    if _dig(win, 'cordura', 'aprobado') is not True:
        problems.append('prueba de cordura de coordenadas no aprobada')
    return _verdict(problems, 'bloques 360 completos con cobertura y cordura aprobada')


def ac08(analysis: Optional[dict], story: Optional[dict], ui: bool) -> Result:
    """Tipología de pérdidas por tipo, zona y jugador en el payload y en la historia; visible en la UI."""
    if analysis is None:
        return PENDING, 'analysis de Jardine aún no existe'
    lost = _dig(analysis, 'transitions', 'ventanas', 'oficial', 'perdidas') or {}
    problems = []
    if len(lost.get('por_tipo') or []) < 5:
        problems.append('menos de 5 tipos de pérdida')
    if not lost.get('por_zona'):
        problems.append('sin zonas')
    if not lost.get('por_jugador'):
        problems.append('sin jugadores')
    ids = {f.get('id') for c in (story or {}).get('capitulos') or [] for f in c.get('hallazgos') or []}
    if 'transiciones_tipologia' not in ids:
        problems.append('la historia no tiene el hallazgo de tipología')
    if problems:
        return FAIL, '; '.join(problems)
    return (OK, 'tipología en payload, historia y UI') if ui else (PENDING, 'tipología en payload e historia; falta verla en la UI')


# ---------------------------------------------------------------- AC-09
def _sorted_plays(plays: list) -> bool:
    keys = [(bool(p.get('gol')), p.get('xg_posesion') or 0, p.get('obv_max') or 0) for p in plays]
    return all(a >= b for a, b in zip(keys, keys[1:]))  # noqa: RUF007 - pairwise no existe en 3.9


def ac09(analysis: Optional[dict]) -> Result:
    """Top 10 por gol, xG de la posesión y OBV; con «hecho»/«interpretación»; x media concedida < 25; ≤ 250 KB."""
    if analysis is None:
        return PENDING, 'analysis de Jardine aún no existe'
    win = _dig(analysis, 'dangerous', 'ventanas', 'oficial') or {}
    problems = []
    for key in LIST_KEYS:
        plays = win.get(key)
        if plays is None:
            problems.append(f'falta {key}')
            continue
        if len(plays) > DANGEROUS_TOP:
            problems.append(f'{key} tiene {len(plays)} jugadas (máximo {DANGEROUS_TOP})')
        if not _sorted_plays(plays):
            problems.append(f'{key} no está ordenada por gol, xG de la posesión y OBV')
        if any(not (p.get('hecho') and p.get('interpretacion')) for p in plays):
            problems.append(f'{key} con jugadas sin Hecho/Interpretación')
    x = _dig(analysis, 'defense', 'ventanas', 'oficial', 'concedido', 'x_media_tiros_concedidos', 'value')
    if x is None or x >= SHOT_X_MAX:
        problems.append(f'x media de tiros concedidos {x} (debe ser < {SHOT_X_MAX})')
    size = len(json.dumps(analysis.get('dangerous'), ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    if size > DANGEROUS_MAX_BYTES:
        problems.append(f'dangerous pesa {size} bytes (máximo {DANGEROUS_MAX_BYTES})')
    return _verdict(problems, f'top {DANGEROUS_TOP} ordenado, con texto, x media {x} y {size // 1024} KB')


# ---------------------------------------------------------------- AC-10, AC-12, AC-14
def ac10(benchmark: Optional[str]) -> Result:
    """Reglas ≥ 90 % de acierto y benchmark con al menos 3 modelos que no son de Anthropic."""
    if benchmark is None:
        return PENDING, 'docs/NL_BENCHMARK.md aún no existe'
    models, rules = set(), None
    for line in benchmark.splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 3:
            continue
        pct = re.match(r'(\d+)\s*%', cells[1])
        if cells[0].lower().startswith('parser de reglas') and pct:
            rules = int(pct.group(1))
        elif re.fullmatch(r'[\w.\-]+/[\w.\-:]+', cells[0]) and not cells[0].lower().startswith('anthropic/'):
            models.add(cells[0])
    problems = []
    if rules is None or rules < RULES_MIN_PCT:
        problems.append(f'reglas {rules} % (mínimo {RULES_MIN_PCT} %)')
    if len(models) < LLM_MODELS_MIN:
        problems.append(f'{len(models)} modelos no-Anthropic (mínimo {LLM_MODELS_MIN})')
    return _verdict(problems, f'reglas {rules} %; {len(models)} modelos no-Anthropic en el benchmark')


def ac12(explorer: Optional[dict]) -> Result:
    """Todos los equipos y DTs con identidad, confianza, marca de muestra chica y métricas: ninguna tarjeta vacía."""
    if explorer is None:
        return PENDING, 'model/explorer.json aún no existe'
    problems, counts = [], {}
    for key in ('equipos', 'entrenadores'):
        items = explorer.get(key) or []
        counts[key] = len(items)
        if not items:
            problems.append(f'sin {key}')
        for it in items:
            name = it.get('label') or it.get('key') or '?'
            if not it.get('metrics'):
                problems.append(f'{key}: «{name}» sin métricas')
            elif not isinstance(it.get('identity'), dict) or not it.get('confidence') or not isinstance(it.get('small_sample'), bool):
                problems.append(f'{key}: «{name}» sin identidad, confianza o marca de muestra chica')
    return _verdict(problems[:6], f"{counts.get('equipos')} equipos y {counts.get('entrenadores')} DTs completos")


def ac14(analysis: Optional[dict], lab_text: Optional[str]) -> Result:
    """Repetición con xG (xPts contra puntos) y el duelo de estilos rotulado «no es un pronóstico»."""
    if analysis is None:
        return PENDING, 'analysis de Jardine aún no existe'
    rep = (analysis.get('replay') or {})
    problems = []
    if _dig(rep, 'resumen', 'puntos') is None or _dig(rep, 'resumen', 'xpts') is None:
        problems.append('la repetición no trae puntos y xPts')
    if not any(m.get('id') == 'xpts' for m in _dig(rep, 'por_ventana', 'oficial', 'metricas') or []):
        problems.append('falta el registro xpts de la ventana oficial')
    if lab_text is None or FORECAST_LABEL not in lab_text:
        problems.append(f'lab.html sin la leyenda «{FORECAST_LABEL}»')
    return _verdict(problems, 'repetición con xG (puntos contra xPts) y duelo de estilos rotulado como no pronóstico')
