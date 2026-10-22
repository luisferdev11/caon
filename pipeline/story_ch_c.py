# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Capítulos 6–8 de la historia: lo que más dolió, balón parado, consistencia y contexto."""
from __future__ import annotations

from typing import Optional

import framework as fw
import story_text as st
from story_ch_a import _p
from story_text import Src, dig, finding, num, pick, rank

# ---------------------------------------------------------------- 6. lo que más dolió
PLAY_KEYS = (('juego_abierto', 'juego abierto'), ('balon_parado', 'balón parado'))


def _play_ev(play: dict, window: str) -> dict:
    """Evidencia de una jugada concreta: su xG de posesión (id registrado de xG concedido)."""
    return {'id': 'xg_concedido', 'value': play['xg_posesion'], 'n': 1, 'unit': 'xG de la posesión', 'source': 'eventos',
            'window': window, 'scope': f"jugada:{play['match_id']}:{play['posesion']}"}


def _danger_summary(s: Src) -> Optional[dict]:
    r = dig(s.win('dangerous'), ('resumen',)) or {}
    per, xgt = r.get('jugadas_por_partido'), r.get('xg_por_tipo') or {}
    if not per or per.get('value') is None:
        return None
    open_, sp = xgt.get('juego_abierto'), xgt.get('balon_parado')
    parts = [v['value'] for v in xgt.values() if isinstance(v, dict) and v.get('value') is not None]
    share = (100 * sp['value'] / sum(parts)) if sp and sp.get('value') is not None and sum(parts) > 0 else None
    goals, lost, tags = r.get('goles_por_tipo') or {}, r.get('goles_tras_perdida'), r.get('por_etiqueta') or {}
    title = f"Concede {num(per['value'], 1)} jugadas con tiro por partido" + (
        f"; {num(share, 0)} % de su xG concedido en jugadas peligrosas nace de balón parado" if share is not None else '')
    fact = (f"{num(per['value'], 1)} posesiones rivales con tiro por partido. xG de posesión por partido: juego abierto "
            f"{num(open_['value']) if open_ else 's/d'}, balón parado {num(sp['value']) if sp else 's/d'}. Goles concedidos: "
            f"{goals.get('juego_abierto', 's/d')} en juego abierto, {goals.get('balon_parado', 's/d')} a balón parado y "
            f"{goals.get('penales', 's/d')} penales"
            + (f"; {num(lost['value'], 0)} llegaron tras una pérdida propia" if lost and lost.get('value') is not None else '')
            + (f"; {tags['transicion']} jugadas nacieron en transición." if tags.get('transicion') is not None else '.'))
    return finding('dolor_resumen', 'lo_que_mas_dolio', ['jugadas_peligrosas', 'bp_defensivo', 'transiciones'], title, fact,
                   'Una jugada peligrosa es una posesión rival con tiro: no distingue si fue evitable; sirve para ubicar '
                   'de dónde vienen los tiros que más cuestan.', [per, open_, sp, lost],
                   'Entrenar las situaciones que más repiten estas jugadas.')


def _top_plays(s: Src, key: str, label: str) -> Optional[dict]:
    plays = (dig(s.win('dangerous'), (key,)) or [])[:3]
    if not plays:
        return None
    goals = sum(bool(p.get('gol')) for p in plays)
    title = f"Las {len(plays)} jugadas de {label} que más dolieron: {goals} terminaron en gol"
    fact = ' · '.join(p['hecho'] for p in plays)
    reading = ' '.join(dict.fromkeys(p['interpretacion'] for p in plays if p.get('interpretacion')))
    f = finding(f'dolor_{key}', 'lo_que_mas_dolio', ['jugadas_peligrosas'] + (['bp_defensivo'] if key == 'balon_parado' else []),
                title, fact, reading, [_play_ev(p, s.window) for p in plays],
                'Revisar el video de estas jugadas con el cuerpo técnico.')
    if f:
        f['detalle'] = {'jugadas': [{'match_id': p['match_id'], 'posesion': p['posesion']} for p in plays]}
    return f


def lo_que_mas_dolio(s: Src) -> dict:
    fs = [_danger_summary(s)] + [_top_plays(s, k, label) for k, label in PLAY_KEYS]
    first = next((f for f in fs if f), None)
    top = (dig(s.win('dangerous'), ('juego_abierto',)) or [None])[0]
    return st.chapter('lo_que_mas_dolio', 6, 'Lo que más dolió: las jugadas peligrosas en contra', fs,
                      f"{first['titulo']}." if first else None,
                      (f"La jugada más cara: {top['hecho']}" if top else None), 'danger_plays')


# ---------------------------------------------------------------- 7. balón parado
def _sp_off(s: Src) -> Optional[dict]:
    xg, corners = s.rec('setpieces', 'ofensivo', 'xg_bp'), dig(s.win('setpieces'), ('ofensivo', 'corners')) or {}
    kinds = dig(s.win('setpieces'), ('ofensivo', 'por_tipo')) or {}
    if not xg:
        return None
    total = sum(v['xg'] for v in kinds.values()) or None
    corner_share = (100 * kinds['corner']['xg'] / total) if total and kinds.get('corner') else None
    title = f"A balón parado genera {num(xg['value'])} xG por partido" + (
        f"; {num(corner_share, 0)} % sale de córners" if corner_share is not None else '')
    fact = (f"{num(xg['value'])} xG por partido de jugadas de balón parado de peligro ({xg['n']} partidos)"
            + (f"; {num(corners['por_partido'], 1)} córners por partido, {num(corners['corto_pct'], 0)} % cortos, "
               f"{num(corners['xg_por_corner'], 3)} xG por córner" if corners.get('por_partido') is not None else '')
            + (f"; {num(corners['remates']['cabeza_pct'], 0)} % de los remates de córner son de cabeza." if dig(corners, ('remates', 'cabeza_pct')) is not None else '.'))
    return finding('bp_ofensivo', 'balon_parado', ['bp_ofensivo', 'xg'], title, fact,
                   'Cuenta todos los córners, los tiros libres desde x≥80 y los saques de banda desde x≥90; sin penales.',
                   [xg], 'Repetir las rutinas de córner que más xG dan.')


def _sp_def(s: Src) -> Optional[dict]:
    xg = s.rec('setpieces', 'defensivo', 'xg_bp')
    m = s.win('shape360').get('metricas') or {}
    pair, area = m.get('corner_emparejamiento'), m.get('corner_area')
    if not xg:
        return None
    title = f"Concede {num(xg['value'])} xG por partido a balón parado"
    if pair and pair.get('value') is not None:
        title += pick(_p(pair), {'alto': '; marca al hombre más que casi toda la liga en córners',
                                 'medio': '; marca en córners como la mayoría',
                                 'bajo': '; en córners marca al hombre menos que la mayoría'})
    fact = (f"{num(xg['value'])} xG por partido en contra ({xg['n']} partidos)"
            + (f"; en córners rivales {num(pair['value'], 1)} % de los atacantes en el área tiene marca a 1.5 yd o menos "
               f"({rank(_p(pair))})" if pair and pair.get('value') is not None else '')
            + (f"; {num(area['value'], 1)} defensores visibles en el área ({rank(_p(area))})." if area and area.get('value') is not None else '.'))
    return finding('bp_defensivo', 'balon_parado', ['bp_defensivo', '360'], title, fact,
                   'La marca se infiere de posiciones 360 (jugadores visibles, cota inferior): es una lectura tentativa, '
                   'no un esquema confirmado.', [xg, pair, area], 'Revisar la marca en los córners rivales con video.')


def _sp_diff(s: Src) -> Optional[dict]:
    d = s.rec('setpieces', 'diferencial')
    if not d:
        return None
    lo, hi = (d.get('ci') or [None, None])
    if lo is not None and lo > 0:
        title, reading = (f"A balón parado gana la partida: {st.signed(d['value'])} xG por partido",
                          'La banda del 80 % queda por encima de cero: el saldo favorable supera el ruido.')
    elif hi is not None and hi < 0:
        title, reading = (f"A balón parado pierde la partida: {st.signed(d['value'])} xG por partido",
                          'La banda del 80 % queda por debajo de cero: el saldo desfavorable supera el ruido.')
    else:
        title, reading = (f"A balón parado está parejo: {st.signed(d['value'])} xG por partido",
                          'La banda del 80 % incluye el cero: no se puede afirmar un saldo.')
    fact = (f"Diferencial {st.signed(d['value'], 3)} xG por partido" + (f" (banda 80 %: {num(lo, 3)} a {num(hi, 3)})" if lo is not None else '')
            + f" en {d['n']} partidos.")
    return finding('bp_diferencial', 'balon_parado', ['bp_ofensivo', 'bp_defensivo'], title, fact, reading, [d],
                   'Seguir el diferencial de balón parado (KPI 7).')


def balon_parado(s: Src) -> dict:
    fs = [_sp_off(s), _sp_def(s), _sp_diff(s)]
    first = next((f for f in fs[2:] + fs[:2] if f), None)
    c = dig(s.win('setpieces'), ('ofensivo', 'corners')) or {}
    return st.chapter('balon_parado', 7, 'Balón parado: lo que da y lo que concede', fs,
                      f"{first['titulo']}." if first else None,
                      (f"Cobra {num(c['por_partido'], 1)} córners por partido." if c.get('por_partido') is not None else None),
                      'set_pieces')


# ---------------------------------------------------------------- 8. consistencia y contexto
DIM_TEXT = {'marcador': {'perdiendo': 'Cuando va perdiendo', 'ganando': 'Cuando va ganando', 'empatando': 'Cuando va empatado'},
            'rival': {'alto': 'Contra rivales fuertes', 'medio': 'Contra rivales de nivel medio', 'bajo': 'Contra rivales débiles'},
            'fase': {'liguilla': 'En liguilla', 'regular': 'En torneo regular'},
            'localia': {'local': 'De local', 'visita': 'De visita'}}
METRIC_TEXT = {'field_tilt': ('su field tilt', '%'), 'posesion': ('su posesión', '%'), 'xg': ('su xG por partido', ''),
               'xga': ('su xG en contra por partido', ''), 'xg_dif': ('su diferencia de xG por partido', ''),
               'puntos': ('sus puntos por partido', ''), 'volumen_presion': ('su volumen de presión', ''),
               'verticalidad': ('su verticalidad', ''), 'ritmo': ('su ritmo de ataque', ''), 'xg_90': ('su xG por 90 min', ''),
               'xga_90': ('su xG en contra por 90 min', '')}


def _scale(metric: str, v: float) -> float:
    return v * 100 if metric == 'posesion' else v


def _context_ev(s: Src, metric: str, dim: str, group: str, h: dict) -> Optional[dict]:
    """Valor del grupo como evidencia: id, unidad y fuente salen del catálogo ``context.metricas``."""
    meta = dig(s.win('context'), ('metricas', metric)) or {}
    mid = meta.get('id') or metric
    if mid not in fw.DEFINITIONS:
        return None
    return {'id': mid, 'value': h['valor'], 'n': h['n'], 'unit': meta.get('unidad', 'valor del grupo'),
            'source': meta.get('fuente', 'team-stats'), 'window': s.window, 'scope': f'{dim}:{group}'}


def _from_groups(s: Src, dim: str) -> Optional[dict]:
    """Grupo y métrica con mayor diferencia relativa a su banda, en el formato de ``hallazgos``."""
    best, weight = None, -1.0
    for group, body in (dig(s.win('context'), ('dimensiones', dim, 'grupos')) or {}).items():
        for metric, d in (body or {}).items():
            if (not isinstance(d, dict) or d.get('dif') is None or not d.get('banda_dif') or d.get('resto') is None
                    or d.get('n', 0) < fw.KPI_MIN_MATCHES):
                continue
            width = (d['banda_dif'][1] - d['banda_dif'][0]) or 1e-9
            if abs(d['dif']) / width > weight:
                weight = abs(d['dif']) / width
                best = {'dimension': dim, 'grupo': group, 'metrica': metric, 'valor': d['valor'], 'resto': d['resto'],
                        'dif': d['dif'], 'banda_dif': d['banda_dif'], 'n': d['n'], 'confianza': d.get('confianza', 'baja')}
    return best


def _dim_finding(s: Src, dim: str) -> Optional[dict]:
    hs = [h for h in (dig(s.win('context'), ('hallazgos',)) or []) if h['dimension'] == dim and h['n'] >= fw.KPI_MIN_MATCHES]
    h = hs[0] if hs else _from_groups(s, dim)
    if h is None:
        return None
    name, unit = METRIC_TEXT.get(h['metrica'], (h['metrica'], ''))
    who = DIM_TEXT.get(dim, {}).get(h['grupo'], f"En los minutos {h['grupo']}" if dim == 'minuto' else f"En el grupo «{h['grupo']}»")
    v, rest = _scale(h['metrica'], h['valor']), _scale(h['metrica'], h['resto'])
    lo, hi = h['banda_dif']
    noise = not (lo > 0 or hi < 0)
    both = f"{st.auto(v)}{' ' + unit if unit else ''} contra {st.auto(rest)}{' ' + unit if unit else ''} en el resto"
    title = f"{who}: {name} sin cambio claro ({both})" if noise else f"{who}: {name} {both}"
    reading = ('La diferencia queda dentro del ruido (banda del 80 %): no se puede afirmar un cambio. '
               if noise else 'La diferencia supera el ruido (banda del 80 %), pero no separa el efecto del rival, la plantilla '
               'ni el calendario. ') + ('Muestra chica: lectura con cautela.' if h['n'] < fw.CONFIDENCE_BANDS[2][0] else '')
    fact = (f"{who} ({h['n']} partidos): {name} {num(v, 2)}{' ' + unit if unit else ''}, resto {num(rest, 2)}{' ' + unit if unit else ''}; "
            f"diferencia {st.signed(_scale(h['metrica'], h['dif']))} con banda del 80 % de {num(_scale(h['metrica'], lo))} a "
            f"{num(_scale(h['metrica'], hi))}; confianza {h['confianza']}.")
    ev = _context_ev(s, h['metrica'], dim, h['grupo'], h)
    return finding(f'contexto_{dim}', 'consistencia_contexto', [f'contexto_{dim}'], title, fact, reading.strip(), [ev],
                   'Preparar el plan de partido distinto para este contexto si la diferencia se repite.')


def _consistency(s: Src) -> Optional[dict]:
    c = s.rec('context', 'consistencia')
    if not c:
        return None
    title = pick(_p(c), {'alto': f"Es consistente: {num(c['value'], 0)} % de sus partidos se parecen al equipo típico",
                         'medio': f"Consistencia media: {num(c['value'], 0)} % de sus partidos se parecen al equipo típico",
                         'bajo': f"Cambia mucho de partido a partido: solo {num(c['value'], 0)} % se parecen al equipo típico"})
    disp = (c.get('dispersion') or {})
    wide = [st.STYLE_NAMES.get(k, k) for k, v in disp.items() if v.get('relativa') is not None and v['relativa'] >= 1.25]
    fact = (f"{num(c['value'], 1)} % de los partidos tienen al menos 3 de 5 rasgos (xG, xG en contra, posesión, presión, "
            f"verticalidad) dentro de su rango habitual" + (f" ({rank(_p(c))})" if _p(c) is not None else '')
            + (f". Varía más que la liga en: {', '.join(wide)}." if wide else '.'))
    return finding('contexto_consistencia', 'consistencia_contexto', ['consistencia', 'identidad'], title, fact,
                   'Un equipo puede ser reconocible y aun así variar en su producción de ocasiones.', [c],
                   'Revisar qué partidos salen de su rango habitual y por qué.', pct=_p(c))


def _club_or_coach(s: Src) -> Optional[dict]:
    jc = dig(s.analysis, ('context', 'jardine_o_club')) or {}
    rasgos = jc.get('rasgos') or []
    if s.window != jc.get('window') or not rasgos:
        return None
    n_club = sum('club' in r['lectura'] for r in rasgos)
    n_dt = sum('Jardine' in r['lectura'] or 'entrenador' in r['lectura'] for r in rasgos)
    none = len(rasgos) - n_club - n_dt
    title = (f"¿Jardine o el club? {n_club} rasgos parecen del club, {n_dt} de Jardine y {none} sin señal clara")
    cat = dig(s.win('context'), ('metricas',)) or {}
    ev = []
    for par in jc.get('pares') or []:      # medias comparadas del propio contexto: nunca un percentil distinto al del estilo
        for metric, d in (par.get('metricas') or {}).items():
            if d.get('supera_ruido') and metric in fw.DEFINITIONS and len(ev) < 6:
                ev.append({'id': metric, 'value': d['protagonista'], 'n': (jc.get('n') or {}).get(s.entity, s.n),
                           'unit': (cat.get(metric) or {}).get('unidad', 'media por partido'), 'source': jc.get('source', 'team-stats'),
                           'window': s.window, 'scope': f"club:{par['otro']}"})
    return finding('contexto_jardine_o_club', 'consistencia_contexto', ['jardine_o_club', 'identidad'], title,
                   ' '.join(r['texto'] for r in rasgos[:4]),
                   'Comparación descriptiva de la ventana oficial: plantillas, rivales y épocas distintas; no aísla el efecto '
                   'del entrenador.', ev,
                   'Contrastar con el trabajo del siguiente entrenador antes de atribuir un rasgo a una persona.', modo='dt')


def consistencia_contexto(s: Src) -> dict:
    dims = ['localia', 'rival', 'marcador', 'minuto', 'fase']
    fs = [_consistency(s)] + [_dim_finding(s, d) for d in dims] + [_club_or_coach(s)]
    first = next((f for f in fs if f), None)
    mark = next((f for f in fs if f and f['id'] == 'contexto_marcador'), None)
    return st.chapter('consistencia_contexto', 8, 'Consistencia y contexto: cuándo cambia', fs,
                      f"{first['titulo']}." if first else None, (mark['titulo'] + '.') if mark else None, 'context_small_multiples')
