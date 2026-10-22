# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Capítulos 4–5 de la historia: sin balón (presión, recuperación, bloque 360) y transiciones y pérdidas."""
from __future__ import annotations

from typing import Optional

import story_text as st
from story_ch_a import PRESS_READING, _p
from story_text import Src, dig, finding, num, pick, rank


# ---------------------------------------------------------------- 4. sin balón
def _pressing(s: Src) -> Optional[dict]:
    ppda, high = s.rec('defense', 'presion', 'ppda'), s.rec('defense', 'presion', 'pct_presiones_altas')
    if not ppda:
        return None
    profile = (s.identity.get('pressing') or {})
    title = profile.get('texto') or pick(_p(ppda), {'alto': f"Deja jugar al rival: PPDA {num(ppda['value'], 1)}",
                                                    'medio': f"Presión intermedia: PPDA {num(ppda['value'], 1)}",
                                                    'bajo': f"Corta pronto el pase rival: PPDA {num(ppda['value'], 1)}"})
    meaning = pick(_p(ppda), {'alto': 'el rival completa muchos pases antes de que el equipo actúe',
                              'medio': 'el rival completa una cantidad normal de pases antes de que el equipo actúe',
                              'bajo': 'el equipo corta pronto el circuito de pases rival'})
    fact = (f"PPDA {num(ppda['value'], 1)} ({rank(_p(ppda))}): {meaning}"
            + (f"; {num(high['value'], 1)} % de sus presiones ocurren en el último tercio ({rank(_p(high))})." if high else '.'))
    reading = PRESS_READING.get(profile.get('perfil'), 'El volumen de presión y el PPDA cuentan la misma historia.')
    return finding('sin_balon_presion', 'sin_balon', ['presion', 'ppda'], title, fact, reading, [ppda, high],
                   'Revisar si la presión alta se convierte en recuperaciones.', pct=_p(ppda))


def _recoveries(s: Src) -> Optional[dict]:
    rival, high = s.rec('defense', 'recuperaciones', 'rec_campo_rival'), s.rec('defense', 'recuperaciones', 'rec_alta')
    shot = s.rec('defense', 'recuperaciones', 'rec_campo_rival_con_tiro')
    if not rival:
        return None
    title = pick(_p(rival), {'alto': f"Recupera en campo rival más que casi toda la liga: {num(rival['value'], 1)} robos por partido",
                             'medio': f"Recupera en campo rival lo normal: {num(rival['value'], 1)} robos por partido",
                             'bajo': f"Recupera en campo rival menos que la mayoría: {num(rival['value'], 1)} robos por partido"})
    fact = (f"{num(rival['value'], 1)} robos por partido en campo rival ({rank(_p(rival))})"
            + (f"; {num(high['value'], 1)} en zona alta ({rank(_p(high))})" if high else '')
            + (f"; {num(shot['value'])} posesiones con tiro en 15 s tras robo ({rank(_p(shot))})." if shot else '.'))
    reading = pick(_p(shot) if shot else _p(rival), {'alto': 'Sus robos arriba suelen terminar en tiro.',
                                                     'medio': 'Sus robos arriba terminan en tiro con frecuencia normal.',
                                                     'bajo': 'Pocos de sus robos arriba terminan en tiro.'})
    return finding('sin_balon_recuperacion', 'sin_balon', ['presion', 'transiciones'], title, fact, reading, [rival, high, shot],
                   'Medir cuántas recuperaciones se quedan sin continuidad.', pct=_p(rival))


def _conceded(s: Src) -> Optional[dict]:
    xg = s.rec('defense', 'concedido', 'xg_concedido')
    per = s.rec('defense', 'concedido', 'npxg_por_tiro')
    entries = s.rec('defense', 'concedido', 'entradas_area')
    if not xg:
        return None
    title = pick(_p(xg), {'alto': f"Concede mucho: {num(xg['value'])} xG por partido, más que casi toda la liga",
                          'medio': f"Concede lo normal: {num(xg['value'])} xG por partido",
                          'bajo': f"Concede poco: {num(xg['value'])} xG por partido, menos que casi toda la liga"})
    fact = (f"{num(xg['value'])} xG sin penal concedido por partido ({rank(_p(xg))})"
            + (f"; {num(per['value'], 3)} xG por tiro concedido ({rank(_p(per))})" if per else '')
            + (f"; {num(entries['value'], 1)} entradas rivales al área por partido ({rank(_p(entries))})." if entries else '.'))
    low_both = _p(xg) is not None and _p(xg) <= st.LOW_MAX and (per is None or _p(per) is None or _p(per) <= st.LOW_MAX)
    reading = ('Limita tanto el volumen como la calidad de los tiros rivales.' if low_both
               else pick(_p(xg), {'alto': 'Los rivales encuentran tiros de valor con frecuencia.',
                                  'medio': 'Su defensa limita a los rivales como la mayoría de la liga.',
                                  'bajo': 'Su defensa limita el valor de los tiros rivales.'}))
    return finding('sin_balon_concedido', 'sin_balon', ['organizacion_defensiva', 'xg'], title, fact, reading,
                   [xg, per, entries], 'Vigilar las jugadas que rompen este bloque (capítulo 6).', pct=_p(xg))


def _block(s: Src) -> Optional[dict]:
    m = s.win('shape360').get('metricas') or {}
    height, long_, between = m.get('altura_sin_balon'), m.get('bloque_largo'), m.get('bloque_entre')
    if not height or height.get('value') is None:
        return None
    long_ok = long_ and long_.get('value') is not None
    both = _p(height) is not None and _p(height) >= st.HIGH_MIN and long_ok and _p(long_) <= st.LOW_MAX
    if both:
        title = (f"Defiende adelantado y compacto: línea a {num(height['value'], 1)} yd y bloque de "
                 f"{num(long_['value'], 1)} yd de largo")
    else:
        title = f"Su bloque sin balón: línea a {num(height['value'], 1)} yd de su portería" + (
            f" y {num(long_['value'], 1)} yd de largo" if long_ok else '')
    fact = (f"Altura de línea sin balón {num(height['value'], 1)} yd ({rank(_p(height))})"
            + (f"; largo del bloque {num(long_['value'], 1)} yd ({rank(_p(long_))})" if long_ok else '')
            + (f"; {num(between['value'], 1)} jugadores visibles entre el balón y la portería ({rank(_p(between))})."
               if between and between.get('value') is not None else '.')
            + ' Medidas con 360: solo jugadores visibles (cota inferior).')
    reading = ('Un bloque corto cerca del balón suele cubrir el espacio entre líneas; la línea adelantada deja más espacio '
               'a su espalda.' if both else 'La forma del bloque se mide con los jugadores visibles en 360; sirve para '
               'comparar contra la liga, no como medida exacta.')
    return finding('sin_balon_bloque_360', 'sin_balon', ['organizacion_defensiva', '360'], title, fact, reading,
                   [height, long_, between], 'Revisar la espalda de la línea en las jugadas peligrosas.')


def sin_balon(s: Src) -> dict:
    fs = [_pressing(s), _recoveries(s), _conceded(s), _block(s)]
    ppda = s.rec('defense', 'presion', 'ppda')
    first = next((f for f in fs if f), None)
    return st.chapter('sin_balon', 4, 'Sin balón: presión, recuperación y bloque', fs,
                      f"{first['titulo']}." if first else None,
                      (f"El rival hace en promedio {num(ppda['value'], 1)} pases antes de que el equipo haga una acción "
                       f"defensiva (PPDA).") if ppda else None, 'defense_map')


# ---------------------------------------------------------------- 5. transiciones y pérdidas
def _losses(s: Src) -> Optional[dict]:
    per, costly = s.rec('transitions', 'perdidas', 'por_partido'), s.rec('transitions', 'perdidas', 'costosas_por_partido')
    rate = s.rec('transitions', 'perdidas', 'tasa_costosa')
    if not per:
        return None
    title = pick(_p(per), {'alto': f"Pierde mucho el balón en juego: {num(per['value'], 1)} por partido",
                           'medio': f"Pierde el balón en juego lo normal: {num(per['value'], 1)} por partido",
                           'bajo': f"Pierde poco el balón en juego: {num(per['value'], 1)} por partido"})
    fact = (f"{num(per['value'], 1)} pérdidas en juego por partido ({rank(_p(per))})"
            + (f"; {num(costly['value'])} por partido terminan en tiro rival en 15 s ({rank(_p(costly))})" if costly else '')
            + (f"; {num(rate['value'], 1)} % de las pérdidas son costosas." if rate else '.'))
    reading = ('Perder pocas veces el balón no significa perderlo sin consecuencias: lo que importa es cuántas '
               'pérdidas se vuelven tiro rival.' if _p(per) is not None and _p(per) <= st.LOW_MAX else
               'Cada pérdida en juego abre una transición rival; lo costoso es la que termina en tiro.')
    return finding('transiciones_perdidas', 'transiciones', ['transiciones', 'perdidas'], title, fact, reading,
                   [per, costly, rate], 'Seguir las pérdidas costosas por partido (KPI 5).', pct=_p(per))


def _types(s: Src) -> Optional[dict]:
    rows = dig(s.win('transitions'), ('perdidas', 'por_tipo')) or []
    iso = s.rec('transitions', 'perdidas', 'aislado_360', 'pct')
    rows = [r for r in rows if r.get('n') and isinstance(r.get('pct'), dict) and r['pct'].get('value') is not None]
    if not rows:
        return None
    common = max(rows, key=lambda r: r['n'])
    costly = max((r for r in rows if r['n'] >= 30 and isinstance(r.get('tasa_costosa'), dict)
                  and r['tasa_costosa'].get('value') is not None), key=lambda r: r['tasa_costosa']['value'], default=None)
    title = f"Su pérdida más común es «{common['nombre'].lower()}» ({num(common['pct']['value'], 1)} %)"
    if costly and costly is not common:
        title += f"; la que más cuesta es «{costly['nombre'].lower()}» ({num(costly['tasa_costosa']['value'], 1)} % acaba en tiro rival)"
    fact = '; '.join(f"{r['nombre']}: {num(r['pct']['value'], 1)} % de las pérdidas ({rank(_p(r['pct']))})" for r in rows[:4])
    fact += (f". Con 360, {num(iso['value'], 1)} % de las pérdidas ocurre sin compañero a 10 yd o menos ({rank(_p(iso))})."
             if iso else '.')
    return finding('transiciones_tipologia', 'transiciones', ['perdidas', '360', 'transiciones'], title, fact,
                   'La tipología separa la pérdida forzada por el rival de la que nace de una decisión propia; '
                   'la segunda es la que más se puede trabajar con decisión y entrenamiento.',
                   [common['pct'], costly['tasa_costosa'] if costly else None, iso],
                   'Priorizar la corrección del tipo que más cuesta.', pct=_p(common['pct']))


def _thirds(s: Src) -> Optional[dict]:
    rows = [r for r in (dig(s.win('transitions'), ('perdidas', 'por_tercio')) or [])
            if isinstance(r.get('tasa_costosa'), dict) and r['tasa_costosa'].get('value') is not None]
    if not rows:
        return None
    worst = max(rows, key=lambda r: r['tasa_costosa']['value'])
    best = min(rows, key=lambda r: r['tasa_costosa']['value'])
    title = (f"Perder en el {worst['nombre'].lower()} cuesta más: {num(worst['tasa_costosa']['value'], 1)} % acaba en tiro "
             f"rival en 15 s")
    fact = '; '.join(f"{r['nombre']}: {num(r['tasa_costosa']['value'], 1)} % ({r['costosas']} de {r['n']})" for r in rows) + '.'
    return finding('transiciones_tercios', 'transiciones', ['perdidas', 'transiciones'], title, fact,
                   f"Cuanto más cerca de su portería, más peligrosa es la pérdida (menos costosa: {best['nombre'].lower()}).",
                   [worst['tasa_costosa'], best['tasa_costosa']], 'Cuidar la circulación en el tercio donde la pérdida más cuesta.')


def _counterpress(s: Src) -> Optional[dict]:
    cp = s.rec('transitions', 'contrapresion_efectiva')
    if not cp:
        return None
    title = pick(_p(cp), {'alto': f"Recupera pronto sus pérdidas: {num(cp['value'], 1)} % en 5 s, más que casi toda la liga",
                          'medio': f"Recupera pronto {num(cp['value'], 1)} % de sus pérdidas: a la par de la liga",
                          'bajo': f"Recupera pronto pocas pérdidas: {num(cp['value'], 1)} % en 5 s, menos que la mayoría"})
    fact = f"{num(cp['value'], 1)} % de las pérdidas en juego se recuperan en 5 s o menos ({rank(_p(cp))})."
    reading = pick(_p(cp), {'alto': 'El equipo reacciona al perder y evita transiciones rivales.',
                            'medio': 'La reacción al perder no se separa de la liga.',
                            'bajo': 'La reacción al perder es más lenta que la de la mayoría.'})
    return finding('transiciones_contrapresion', 'transiciones', ['transiciones', 'presion'], title, fact, reading, [cp],
                   'Seguir la contrapresión efectiva (KPI 4).', pct=_p(cp))


def _counters(s: Src) -> Optional[dict]:
    given = s.rec('transitions', 'transiciones', 'contraataques', 'por_partido')
    taken = s.rec('transitions', 'transiciones', 'contraataques_concedidos', 'por_partido')
    xg10 = s.rec('transitions', 'transiciones', 'ofensivas', 'xg_10s_por_partido')
    if not taken:
        return None
    title = pick(_p(taken), {'alto': f"Concede más contraataques que la mayoría: {num(taken['value'], 2)} por partido",
                             'medio': f"Concede contraataques como la liga: {num(taken['value'], 2)} por partido",
                             'bajo': f"Concede menos contraataques que casi toda la liga: {num(taken['value'], 2)} por partido"})
    goals = dig(s.win('transitions'), ('transiciones', 'contraataques', 'goles'))
    goals_c = dig(s.win('transitions'), ('transiciones', 'contraataques_concedidos', 'goles'))
    fact = (f"Concede {num(taken['value'], 2)} contraataques por partido ({rank(_p(taken))})"
            + (f" y {goals_c} goles de ese tipo" if goals_c is not None else '')
            + (f"; hace {num(given['value'], 2)} ({rank(_p(given))})" if given else '')
            + (f", con {goals} goles" if goals is not None and given else '')
            + (f"; su xG en los primeros 10 s tras robo es {num(xg10['value'], 2)} por partido ({rank(_p(xg10))})." if xg10 else '.'))
    return finding('transiciones_contraataques', 'transiciones', ['transiciones'], title, fact,
                   'Un contraataque es una posesión que nace en su campo y termina en tiro en 15 s; sirve para medir cómo '
                   'protege su espalda.', [taken, given, xg10], 'Vigilar los contraataques concedidos tras pérdida en campo rival.',
                   pct=_p(taken))


def transiciones(s: Src) -> dict:
    fs = [_losses(s), _types(s), _thirds(s), _counterpress(s), _counters(s)]
    rate = s.rec('transitions', 'perdidas', 'tasa_costosa')
    first = next((f for f in fs if f), None)
    return st.chapter('transiciones', 5, 'Transiciones y pérdidas: qué cuesta perder el balón', fs,
                      f"{first['titulo']}." if first else None,
                      f"De cada 100 pérdidas en juego, {num(rate['value'], 0)} terminan en tiro rival en 15 s." if rate else None,
                      'loss_types')

