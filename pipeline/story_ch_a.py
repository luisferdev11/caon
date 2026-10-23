# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Capítulos 1–5 de la historia: portada, identidad, con balón, sin balón, transiciones y pérdidas.

Cada hallazgo sale de registros de ``analysis``/``kpis``: el título es el hallazgo, el hecho cita el valor y su
posición descriptiva en la liga, y la interpretación cambia con el nivel del percentil (nunca lo contradice).
"""
from __future__ import annotations

from typing import Optional

import framework as fw
import story_text as st
from story_text import Src, dig, finding, num, pick, rank

PRESS_READING = {'sin_robo': 'Presiona mucho en volumen, pero esas presiones no cortan el circuito rival: el rival completa muchos pases antes de que el equipo actúe.',
                 'selectiva': 'Presiona poco, pero cuando lo hace corta pronto el pase.',
                 'asfixiante': 'Presiona mucho y corta el circuito: el rival casi no sale jugando.',
                 'espera': 'Espera atrás y presiona poco.'}
# Nombre de cada KPI cuando destaca y cuando flojea: «pérdidas costosas» no puede ser una fortaleza (lo mejor es tener pocas).
KPI_PHRASES = {'field_tilt': ('dominio territorial', 'poco dominio territorial'),
               'progresion_limpia': ('progresión limpia', 'poca progresión limpia'),
               'npxg_por_tiro': ('calidad de ocasión', 'baja calidad de ocasión'),
               'perdida_costosa': ('pocas pérdidas costosas', 'muchas pérdidas costosas'),
               'contrapresion_efectiva': ('contrapresión efectiva', 'poca contrapresión efectiva'),
               'vigilancias': ('vigilancias 360 altas', 'pocas vigilancias 360'),
               'bp_diferencial': ('diferencial de balón parado favorable', 'diferencial de balón parado desfavorable')}
FOUR = ('field_tilt', 'progresion_limpia', 'npxg_por_tiro', 'perdida_costosa')


def _p(record: Optional[dict]) -> Optional[float]:
    return None if record is None else record.get('ref_pct')


def _join(words: list) -> str:
    return words[0] if len(words) == 1 else ', '.join(words[:-1]) + ' y ' + words[-1]


# ---------------------------------------------------------------- 1. portada
def _result(s: Src, fid: str = 'portada_resultado', chapter: str = 'portada') -> Optional[dict]:
    rep = dig(s.analysis, ('replay', 'resumen')) or {}
    xpts = next((m for m in (dig(s.analysis, ('replay', 'por_ventana', s.window, 'metricas')) or [])
                 if m.get('id') == 'xpts'), None)
    ppp, xppp, n_sorp = rep.get('puntos_por_partido'), rep.get('xpts_por_partido'), rep.get('sorpresivos')
    if ppp is None or xppp is None:
        return None
    diff = ppp - xppp
    title = f'Sacó {num(ppp)} puntos por partido, lo que pedían sus ocasiones ({num(xppp)})'
    reading = 'Los resultados fueron acordes a las ocasiones que generó.'
    if diff > fw.STORY_BALANCE_PPP:
        title = f'Sacó {num(ppp)} puntos por partido, más de los {num(xppp)} que pedían sus ocasiones'
        reading = 'Sacó más puntos de los que sus ocasiones pedían: parte del resultado vino de la eficacia o la fortuna.'
    elif diff < -fw.STORY_BALANCE_PPP:
        title = f'Sacó {num(ppp)} puntos por partido, menos de los {num(xppp)} que pedían sus ocasiones'
        reading = 'Sacó menos puntos de los que sus ocasiones pedían: el resultado quedó por debajo del juego.'
    fact = (f'{s.n} partidos, {num(ppp)} puntos por partido contra {num(xppp)} esperados por sus ocasiones '
            f'(repetición con xG); {n_sorp} resultados sorpresivos.')
    return finding(fid, chapter, ['xg', 'simulacion'], title, fact, reading,
                   [s.rec('context', 'general', 'puntos'), xpts], 'Comparar puntos reales y esperados cada torneo.')


def _four_kpis(s: Src) -> Optional[dict]:
    rows = [s.kpi(k) for k in FOUR]
    rows = [k for k in rows if k]
    if not rows:
        return None
    good = {k['id']: st.good_pct(k.get('ref_pct'), k['mejor']) for k in rows}
    strong = [KPI_PHRASES[i][0] for i, g in good.items() if g is not None and g >= st.HIGH_MIN]
    weak = [KPI_PHRASES[i][1] for i, g in good.items() if g is not None and g <= st.LOW_MAX]
    if strong:
        title = 'Fuerte en ' + _join(strong) + ('; flojo en ' + _join(weak) if weak else '')
    else:
        title = 'Flojo en ' + _join(weak) if weak else 'Perfil intermedio en los cuatro indicadores clave'
    fact = '; '.join(f"{k['nombre'].lower()}: {st.auto(k['value'])} {k['unit']} ({rank(k.get('ref_pct')) or 'sin referencia'})"
                     for k in rows) + '.'
    reading = ('Los indicadores donde destaca son los que definen su identidad; el tablero (capítulo 11) los '
               'compara partido a partido.' if strong else 'Ningún indicador clave se separa de la liga: su identidad '
               'está en otro lado.')
    return finding('portada_kpis', 'portada', ['field_tilt', 'progresion', 'ocasiones', 'perdidas'], title, fact,
                   reading, rows, 'Seguir estos cuatro números partido a partido.')


def portada(s: Src) -> dict:
    first = _result(s)
    ft = s.kpi('field_tilt')
    conclusion = (f"{s.label}: {first['titulo'].lower()}." if first else None)
    curioso = (f"El {num(ft['value'], 0)} % de sus acciones ocurre en el último tercio." if ft else None)
    return st.chapter('portada', 1, f'{s.label}: la historia en cuatro números', [first, _four_kpis(s)],
                      conclusion, curioso, 'kpi_cards')


# ---------------------------------------------------------------- 2. identidad
def _identity_ball(s: Src) -> Optional[dict]:
    i = s.identity
    title = f"Su sello con balón: {i['build'].lower()} y ataque {i['attack'].lower()}"
    fact = st.cap('; '.join(st.style_phrase(k, s.style.get(k)) for k in ('posesion', 'verticalidad', 'ritmo'))) + '.'
    reading = ('Combina verticalidad alta con ritmo pausado: va directo al área, pero sin acelerar el juego.'
               if 'Directo pero paciente' in i['tags'] else
               'La salida y el ataque salen de la posesión, la verticalidad y el ritmo frente a la liga.')
    return finding('identidad_con_balon', 'identidad', ['identidad', 'construccion'], title, fact, reading,
                   [s.style_ev(k) for k in ('posesion', 'verticalidad', 'ritmo')],
                   'Contrastar este sello con el de cada rival.')


def _identity_nobal(s: Src) -> Optional[dict]:
    i, ppda = s.identity, s.rec('defense', 'presion', 'ppda')
    title = f"Su sello sin balón: {i['defense'].lower()}"
    side = pick(_p(ppda), {'alto': 'el rival hace muchos pases antes de que actúe',
                           'medio': 'el rival hace una cantidad normal de pases antes de que actúe',
                           'bajo': 'corta pronto el pase rival'})
    fact = (f"{st.cap(st.style_phrase('linea', s.style.get('linea')))}; "
            f"{st.style_phrase('volumen_presion', s.style.get('volumen_presion'))}; "
            f"PPDA {num(ppda['value']) if ppda else 's/d'} ({rank(_p(ppda)) or 'sin referencia'}): {side}.")
    reading = PRESS_READING.get(i['pressing'].get('perfil'), 'El volumen de presión y el PPDA cuentan la misma historia.')
    return finding('identidad_sin_balon', 'identidad', ['identidad', 'presion', 'ppda'], title, fact, reading,
                   [s.style_ev('linea'), s.style_ev('volumen_presion'), ppda], 'Vigilar si la presión se traduce en recuperaciones.',
                   pct=_p(ppda))


def _identity_tags(s: Src) -> Optional[dict]:
    tags, evid = s.identity['tags'], s.identity['evidence']
    if not tags:
        return None
    fact = st.cap('; '.join(st.style_phrase(e['metric'], e['pct']) for e in evid)) + '.'
    return finding('identidad_etiquetas', 'identidad', ['identidad', 'consistencia'],
                   'Se le reconoce por: ' + _join(tags[:4]), fact,
                   'Las etiquetas salen de percentiles; si un rasgo no aparece, no destaca frente a la liga.',
                   [s.style_ev(e['metric']) for e in evid], 'Revisar si las etiquetas se sostienen en los partidos de contexto.')


def identidad(s: Src) -> dict:
    i = s.identity
    return st.chapter('identidad', 2, 'Identidad: cómo se le reconoce', [_identity_ball(s), _identity_nobal(s),
                                                                         _identity_tags(s)],
                      f"{s.label} se reconoce por {_join([t.lower() for t in i['tags'][:3]])}." if i['tags'] else None,
                      f"Su salida es «{i['build'].lower()}» y defiende con «{i['defense'].lower()}»." if i['build'] else None,
                      'identity_card')


# ---------------------------------------------------------------- 3. con balón
def _build(s: Src) -> Optional[dict]:
    clean, regain = s.rec('offense', 'construccion', 'salida_limpia'), s.rec('offense', 'construccion', 'salida_limpia_tras_robo')
    gk, gk_play = s.rec('offense', 'construccion', 'saque_puerta_largo'), s.rec('offense', 'construccion', 'portero_en_juego_largo')
    if not clean:
        return None
    title = pick(_p(clean), {'alto': f"Construye desde atrás: {num(clean['value'], 1)} % de sus salidas llega limpio a campo rival",
                             'medio': f"Su salida limpia es intermedia: {num(clean['value'], 1)} % llega a campo rival",
                             'bajo': f"Le cuesta salir limpio: solo {num(clean['value'], 1)} % de sus salidas llega a campo rival"})
    fact = (f"{num(clean['value'], 1)} % de las posesiones que nacen atrás llegan limpias a campo rival "
            f"({rank(_p(clean))})" + (f"; tras robo: {num(regain['value'], 1)} % ({rank(_p(regain))})" if regain else '')
            + (f"; {num(gk['value'], 1)} % de sus saques de puerta son largos ({rank(_p(gk))})." if gk else '.'))
    reading = pick(_p(clean), {'alto': 'La salida corta funciona: el balón avanza sin regalarlo.',
                               'medio': 'La salida no destaca ni para bien ni para mal.',
                               'bajo': 'La salida pierde el balón antes de cruzar la mitad con más frecuencia que la mayoría.'})
    return finding('con_balon_construccion', 'con_balon', ['construccion'], title, fact, reading,
                   [clean, regain, gk, gk_play], 'Revisar la salida tras saque de puerta.', pct=_p(clean))


def _progress(s: Src) -> Optional[dict]:
    prog, per100 = s.rec('offense', 'progresion', 'progresion_limpia'), s.rec('offense', 'progresion', 'prog_por_100')
    top = (dig(s.win('offense'), ('progresion', 'top_progresores')) or [None])[0]
    if not prog:
        return None
    title = pick(_p(prog), {'alto': f"Progresa limpio más que casi toda la liga: {num(prog['value'], 1)} % de sus posesiones",
                            'medio': f"Progresa en la media de la liga: {num(prog['value'], 1)} % de sus posesiones",
                            'bajo': f"Progresa menos que la mayoría: {num(prog['value'], 1)} % de sus posesiones"})
    fact = (f"{num(prog['value'], 1)} % de las posesiones que nacen antes de x=60 llegan limpias a x≥80 ({rank(_p(prog))})"
            + (f"; {num(per100['value'], 1)} acciones progresivas por cada 100 posesiones ({rank(_p(per100))})" if per100 else '')
            + (f". {top['jugador']} hace {num(top['pct_equipo'], 1)} % de las progresiones del equipo." if top else '.'))
    reading = pick(_p(prog), {'alto': 'El equipo avanza con pases y conducciones, no con balones largos.',
                              'medio': 'La progresión no es ni su fuerte ni su debilidad.',
                              'bajo': 'El equipo avanza menos de lo esperado entre su salida y el último tercio.'})
    return finding('con_balon_progresion', 'con_balon', ['progresion', 'progresivos'], title, fact, reading, [prog, per100],
                   'Medir qué pasa si el principal progresor no juega.', pct=_p(prog))


def _chances(s: Src) -> Optional[dict]:
    q, zone = s.rec('offense', 'ocasiones', 'npxg_por_tiro'), s.rec('offense', 'ocasiones', 'tiros_zona_remate')
    xg, entries = s.rec('offense', 'ocasiones', 'npxg_por_partido'), s.rec('offense', 'ocasiones', 'entradas_area')
    if not q:
        return None
    title = pick(_p(q), {'alto': f"Sus tiros valen más: {num(q['value'])} xG por tiro, más que casi toda la liga",
                         'medio': f"Sus tiros valen lo normal: {num(q['value'])} xG por tiro",
                         'bajo': f"Sus tiros valen menos que los de la mayoría: {num(q['value'])} xG por tiro"})
    fact = (f"{num(q['value'], 3)} xG por tiro sin penal ({rank(_p(q))})"
            + (f"; {num(zone['value'], 1)} % desde la zona de remate ({rank(_p(zone))})" if zone else '')
            + (f"; {num(xg['value'])} xG por partido ({rank(_p(xg))})" if xg else '')
            + (f"; {num(entries['value'], 1)} entradas al área por partido ({rank(_p(entries))})." if entries else '.'))
    reading = pick(_p(q), {'alto': 'Busca tiros cercanos y de frente: valen más aunque no siempre sean muchos.',
                           'medio': 'La calidad de sus tiros no se separa de la liga.',
                           'bajo': 'Dispara desde donde valen poco: más volumen que calidad.'})
    return finding('con_balon_ocasiones', 'con_balon', ['ocasiones', 'xg'], title, fact, reading, [q, zone, xg, entries],
                   'Seguir el xG por tiro, no solo el número de tiros.', pct=_p(q))


def _obv(s: Src) -> Optional[dict]:
    tot = s.rec('offense', 'obv', 'por_partido')
    kinds = {k: s.rec('offense', 'obv', 'por_tipo', k) for k in ('pase', 'conduccion', 'tiro')}
    if not tot:
        return None
    title = pick(_p(tot), {'alto': f"Genera más valor con el balón (OBV) que casi todos: {num(tot['value'])} por partido",
                           'medio': f"Su valor con el balón (OBV) es normal: {num(tot['value'])} por partido",
                           'bajo': f"Genera menos valor con el balón (OBV) que la mayoría: {num(tot['value'])} por partido"})
    parts = [f"{n}: {rank(_p(r))}" for n, r in (('pases', kinds['pase']), ('conducciones', kinds['conduccion']),
                                                ('tiros', kinds['tiro'])) if r]
    fact = f"OBV {num(tot['value'])} por partido ({rank(_p(tot))}). Por tipo, " + '; '.join(parts) + '.'
    pa, co = _p(kinds['pase']), _p(kinds['conduccion'])
    reading = ('El valor llega más por conducciones que por pases.' if pa is not None and co is not None and co - pa >= 15
               else 'El valor llega más por pases que por conducciones.' if pa is not None and co is not None and pa - co >= 15
               else 'El valor se reparte entre pases y conducciones.')
    return finding('con_balon_obv', 'con_balon', ['obv'], title, fact, reading, [tot] + list(kinds.values()),
                   'Ver qué jugadores concentran el OBV.', pct=_p(tot))


def _tilt(s: Src) -> Optional[dict]:
    ft = s.rec('offense', 'dominio', 'field_tilt')
    if not ft:
        return None
    title = pick(_p(ft), {'alto': f"Vive en campo rival: {num(ft['value'], 1)} % de sus acciones en el último tercio",
                          'medio': f"Reparte el campo: {num(ft['value'], 1)} % de sus acciones en el último tercio",
                          'bajo': f"Juega lejos del área rival: {num(ft['value'], 1)} % de sus acciones en el último tercio"})
    fact = f"Field tilt {num(ft['value'], 1)} % ({rank(_p(ft))})."
    reading = pick(_p(ft), {'alto': 'Empuja al rival hacia su área; el partido se juega en su mitad de la cancha.',
                            'medio': 'El territorio está repartido con el rival.',
                            'bajo': 'El rival ocupa más el último tercio que el equipo.'})
    return finding('con_balon_field_tilt', 'con_balon', ['field_tilt'], title, fact, reading, [ft],
                   'Cuidar que el dominio de territorio se convierta en tiros de calidad.', pct=_p(ft))


def con_balon(s: Src) -> dict:
    top = (dig(s.win('offense'), ('progresion', 'top_progresores')) or [None])[0]
    fs = [_build(s), _progress(s), _chances(s), _obv(s), _tilt(s)]
    first = next((f for f in fs if f), None)
    return st.chapter('con_balon', 3, 'Con balón: salida, progresión y creación', fs,
                      f"{first['titulo']}." if first else None,
                      f"{top['jugador']} concentra {num(top['pct_equipo'], 1)} % de las acciones progresivas del equipo." if top else None,
                      'shot_map')
