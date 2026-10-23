# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Historia «¿Qué cambia con Almada?» → ``model/story/almada.json`` (Pachuca·Almada contra sus primeros partidos en el América).

El Pachuca de Almada (Cl22–Cl25) está dentro de la ventana oficial; sus primeros partidos en el América (2026/27) son
evidencia temprana: valores crudos y encogidos hacia su carrera, con intervalo del 80 %, y ninguna conclusión fuerte con
muestra chica.
"""
from __future__ import annotations

from typing import Optional

import framework as fw
import story_text as st
from story_ch_a import _join
from story_text import Src, finding

EARLY_NOTE = 'Evidencia temprana: pocos partidos, confianza baja; es una lectura inicial, no una conclusión.'
SHOWN = ('xg', 'xga', 'posesion', 'verticalidad', 'linea', 'volumen_presion', 'presion', 'contrapresion', 'bp_xg')


def tenure(explorer: dict, entity_id: str) -> Optional[dict]:
    """Tenencia del explorador (equipo × ventana de un DT) que enlaza a la entidad."""
    for coach in explorer.get('entrenadores') or []:
        for t in coach.get('tenencias') or []:
            if any(e.get('id') == entity_id for e in t.get('entidades') or []):
                return t
    return None


def _catalog(explorer: dict) -> dict:
    return {m['id']: m for m in explorer.get('metricas') or []}


def _moves(a: list, b: Src) -> list:
    """[(KPI de a, KPI de b, movimiento de percentil «mejor = alto»)] para los KPIs presentes en ambos."""
    out = []
    for k in a:
        o = b.kpi(k['id'])
        if k.get('value') is None or not o:
            continue
        ga, gb = st.good_pct(k.get('ref_pct'), k['mejor']), st.good_pct(o.get('ref_pct'), o['mejor'])
        out.append((k, o, None if ga is None or gb is None else ga - gb))
    return out


def _pachuca(pac: Src) -> Optional[dict]:
    i = pac.identity
    keys = ('posesion', 'contragolpe', 'linea', 'volumen_presion', 'presion')
    fact = st.cap('; '.join(st.style_phrase(k, pac.style.get(k)) for k in keys)) + '.'
    title = f"En el Pachuca, Almada armó un equipo de «{i['build'].lower()}» que defiende con «{i['defense'].lower()}»"
    reading = ('Se le reconoce por: ' + _join(i['tags'][:4]) + '.') if i['tags'] else 'Sin rasgos que destaquen frente a la liga.'
    return finding('almada_pachuca', 'almada_pachuca', ['identidad', 'presion'], title, fact, reading,
                   [pac.style_ev(k) for k in keys], 'Tomar esta huella como la referencia de lo que Almada suele hacer.')


def _vs_base(pac: Src, base: Src) -> Optional[dict]:
    moves = _moves(pac.kpi_rows, base)
    if not moves:
        return None
    far = [m for m in moves if m[2] is not None and abs(m[2]) >= fw.STORY_PCT_SHIFT]
    title = (f"Frente a la base de Jardine, el Pachuca de Almada se separa en {len(far)} de {len(moves)} indicadores"
             + (f": {_join([m[0]['nombre'].lower() for m in far])}" if far else ''))
    fact = '; '.join(f"{k['nombre']}: {st.auto(k['value'])} en el Pachuca contra {st.auto(o['value'])} en el América de Jardine"
                     for k, o, _ in moves) + '.'
    return finding('almada_vs_jardine', 'almada_pachuca', ['kpis', 'identidad'], title, fact,
                   'Dos plantillas, dos ligas y dos épocas: es una comparación descriptiva de estilos, no de calidad.',
                   [m[0] for m in moves], 'Usar estas diferencias para anticipar qué ajustará el América.')


def _early_records(explorer: dict, ame: Src) -> tuple:
    """(tenencia América, tenencia Pachuca, catálogo, [(id, métrica América, métrica Pachuca, separa)])."""
    t_ame, t_pac, cat = tenure(explorer, ame.entity), tenure(explorer, 'pac_almada'), _catalog(explorer)
    rows = []
    for key in SHOWN:
        a, p = (t_ame or {}).get('metrics', {}).get(key), (t_pac or {}).get('metrics', {}).get(key)
        if not a or not p or a.get('value') is None or p.get('value') is None or key not in fw.DEFINITIONS:
            continue
        lo, hi = a.get('ci') or [None, None]
        rows.append((key, a, p, lo is not None and (p['value'] < lo or p['value'] > hi)))
    return t_ame, t_pac, cat, rows


def _show(key: str, v: float) -> str:
    """Valor legible: la posesión (proporción 0–1) se muestra en porcentaje."""
    return f"{st.auto(100 * v)} %" if key == 'posesion' else st.auto(v)


def _ev(key: str, a: dict, cat: dict, window: str) -> dict:
    return {'id': key, 'value': a['value'], 'n': a['n'], 'unit': (cat.get(key) or {}).get('unit', 'valor'), 'source': 'team-stats',
            'window': window, 'scope': 'encogido', 'ci': a.get('ci'), 'ref_pct': a.get('ref_pct')}


def _early(ame: Src, explorer: dict) -> tuple:
    t_ame, _t_pac, cat, rows = _early_records(explorer, ame)
    if not t_ame or not rows:
        return None, None
    sep = [r for r in rows if r[3]]
    title = (f"Primeros {t_ame['n']} partidos de Almada en el América: {len(sep)} de {len(rows)} rasgos ya se separan de su "
             f"Pachuca (evidencia temprana)")
    def name(k: str) -> str:
        return (cat.get(k) or {}).get('nombre', k)
    fact = '; '.join(f"{name(k)}: {_show(k, a['raw'])} crudo, {_show(k, a['value'])} ajustado (intervalo 80 %: {_show(k, a['ci'][0])} a "
                     f"{_show(k, a['ci'][1])}) contra {_show(k, p['value'])} en el Pachuca" for k, a, p, _ in rows[:6]) + '.'
    reading = (f"Confianza {t_ame['confidence']}: los valores se encogen hacia su carrera previa (n0 = 8). " + EARLY_NOTE)
    f1 = finding('almada_america_temprano', 'almada_america', ['kpis', 'identidad'], title, fact, reading,
                 [_ev(k, a, cat, ame.window) for k, a, _, _ in rows], 'Esperar más partidos antes de sacar conclusiones fuertes.')
    changed = [r for r in sep]
    if changed:
        parts = [f"{name(k)} {'sube' if a['value'] > p['value'] else 'baja'} frente al Pachuca" for k, a, p, _ in changed]
        t2, f_text = f"Lo que ya cambió: {_join(parts)}", 'Solo se listan los rasgos cuyo intervalo del 80 % no incluye su valor en el Pachuca.'
    else:
        t2, f_text = ('Aún no hay un cambio que supere el ruido frente a su Pachuca',
                      'Ningún rasgo tiene un intervalo del 80 % que excluya su valor en el Pachuca.')
    f2 = finding('almada_ya_cambio', 'almada_america', ['kpis'], t2, f_text, EARLY_NOTE,
                 [_ev(k, a, cat, ame.window) for k, a, _, _ in (changed or rows[:3])], 'Revisar estos rasgos en la próxima ventana de partidos.')
    return f1, f2


def _watch(ame: Src, pac: Src) -> Optional[dict]:
    moves = [m for m in _moves(ame.kpi_rows, pac) if m[2] is not None and abs(m[2]) >= fw.STORY_PCT_SHIFT]
    if not moves:
        return None
    title = f"Qué vigilar: {_join([m[0]['nombre'].lower() for m in moves])} se mueve{'n' if len(moves) > 1 else ''} frente al Pachuca"
    fact = '; '.join(f"{k['nombre']}: {st.auto(k['value'])} en el América ({k['n_partidos'] if k.get('n_partidos') else k['n']} partidos) contra "
                     f"{st.auto(o['value'])} en el Pachuca" for k, o, _ in moves) + '.'
    return finding('almada_vigilar', 'almada_america', ['kpis'], title, fact,
                   'Un movimiento de percentil de 20 puntos o más con pocos partidos puede ser ruido: se vigila, no se concluye. '
                   + EARLY_NOTE, [m[0] for m in moves], 'Seguir estos indicadores partido a partido.')


def build_almada(pac: Src, ame: Src, base: Src, explorer: dict) -> dict:
    """Capítulos de «¿Qué cambia con Almada?»."""
    f1, f2 = _early(ame, explorer)
    chapters = [st.chapter('almada_pachuca', 1, 'Almada en el Pachuca: su huella', [_pachuca(pac), _vs_base(pac, base)],
                           'La huella de Almada en el Pachuca es el punto de partida para leer su llegada al América.',
                           None, 'identity_compare'),
                st.chapter('almada_america', 2, 'Sus primeros partidos en el América (evidencia temprana)', [f1, f2, _watch(ame, pac)],
                           EARLY_NOTE, None, 'raw_vs_shrunk')]
    st.tag_entities(chapters[:1], pac.entity)
    st.tag_entities(chapters[1:], ame.entity)
    return {'version': 'story.v1', 'id': 'almada', 'titulo': '¿Qué cambia con Almada?', 'entidad': ame.entity,
            'etiqueta': ame.label, 'ventana': ame.window, 'partidos': ame.n, 'capitulos': chapters,
            'nota': f'{EARLY_NOTE} La huella del Pachuca está dentro de la ventana oficial.', 'evidencia_temprana': True}
