# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Capítulos 9–12 de la historia: jugadores y cambios, ¿mereció ganar?, tablero de KPIs y epílogo."""
from __future__ import annotations

from typing import Optional

import framework as fw
import story_text as st
from story_ch_a import _join, _result
from story_text import Src, dig, finding, num, rank


def _minutes_ev(p: dict, window: str) -> dict:
    return {'id': 'minutos_jugador', 'value': p['share_minutos'], 'n': p['partidos'], 'unit': '% de los minutos del equipo',
            'source': 'eventos', 'window': window, 'scope': f"jugador:{p['id']}"}


# ---------------------------------------------------------------- 9. jugadores y cambios
def _core(s: Src) -> Optional[dict]:
    squad = dig(s.win('usage'), ('plantilla',)) or []
    core = [p for p in squad if p['share_minutos'] >= fw.CORE_MINUTES_PCT]
    if not squad:
        return None
    title = (f"Un núcleo estable: {len(core)} jugadores juegan más de {fw.CORE_MINUTES_PCT} % de los minutos" if len(core) >= 8
             else f"Reparte los minutos: solo {len(core)} jugadores superan {fw.CORE_MINUTES_PCT} % de los minutos")
    fact = '; '.join(f"{p['jugador']} ({p['posicion'].lower()}, {num(p['share_minutos'], 0)} %)" for p in squad[:6]) + '.'
    return finding('jugadores_nucleo', 'jugadores_cambios', ['roles', 'alineaciones'], title, fact,
                   'Los minutos describen quién sostiene el sistema; no distinguen lesiones ni suspensiones.',
                   [_minutes_ev(p, s.window) for p in squad[:3]], 'Planear el reemplazo de los jugadores de mayor peso.')


def _roles(s: Src) -> Optional[dict]:
    xi = dig(s.win('usage'), ('xi_base',)) or []
    movers = [p for p in xi if len(p.get('roles') or []) >= 2 and p['roles'][1]['pct_minutos'] >= 25]
    if not xi:
        return None
    title = (f"{len(movers)} de sus {len(xi)} titulares base cambian de puesto con frecuencia" if movers
             else f"Sus {len(xi)} titulares base ocupan un puesto fijo")
    fact = ('; '.join(f"{p['jugador']}: " + ', '.join(f"{r['posicion'].lower()} {num(r['pct_minutos'], 0)} %" for r in p['roles'][:3])
                      for p in movers[:4]) + '.') if movers else 'Cada titular base juega casi todos sus minutos en un solo puesto.'
    return finding('jugadores_roles', 'jugadores_cambios', ['roles'], title, fact,
                   'Un jugador con dos puestos da flexibilidad al sistema; el puesto sale de la alineación registrada.',
                   [_minutes_ev(p, s.window) for p in (movers or xi)[:3]], 'Identificar qué jugadores sostienen más de un rol.')


def _lineups(s: Src) -> Optional[dict]:
    forms, rot = dig(s.win('usage'), ('formaciones',)) or [], s.rec('usage', 'rotacion')
    if not forms:
        return None
    top = forms[0]
    title = f"Juega {num(top['pct'], 0)} % de sus partidos en {top['formacion']} y usa {len(forms)} formaciones"
    fact = '; '.join(f"{f['formacion']}: {num(f['pct'], 1)} % ({f['n']})" for f in forms[:4])
    fact += (f". Cambia {num(rot['value'], 1)} titulares de un partido al siguiente." if rot else '.')
    ev = {'id': 'formacion', 'value': top['pct'], 'n': top['n'], 'unit': '% de los partidos', 'source': 'eventos',
          'window': s.window, 'scope': f"formacion:{top['formacion']}"}
    return finding('jugadores_alineaciones', 'jugadores_cambios', ['alineaciones'], title, fact,
                   'La formación registrada no describe el comportamiento durante el juego.', [ev, rot],
                   'Contrastar la rotación con el calendario de partidos.')


def _subs(s: Src) -> Optional[dict]:
    c = dig(s.win('usage'), ('cambios',)) or {}
    avg, imp = s.rec('usage', 'cambios', 'minuto_medio'), s.rec('usage', 'cambios', 'asociacion', 'metricas', 'xg_favor')
    if not avg or c.get('por_partido') is None:
        return None
    title = f"Hace {num(c['por_partido'], 1)} cambios por partido, el primero hacia el minuto {num(c['primer_cambio_medio'], 0)}"
    assoc = dig(c, ('asociacion',)) or {}
    fact = (f"{num(c['por_partido'], 2)} cambios por partido; minuto medio {num(avg['value'], 1)}; {c.get('en_descanso', 0)} en el "
            f"descanso" + (f". En {assoc['elegibles']} cambios comparables, el xG a favor 15 min después cambió "
                           f"{st.signed(imp['value'], 3)} en promedio." if imp and assoc.get('elegibles') else '.'))
    return finding('jugadores_cambios_ritmo', 'jugadores_cambios', ['sustituciones'], title, fact,
                   'Asociación descriptiva, no efecto: compara 15 minutos antes y después y excluye cambios con gol o '
                   'ventana incompleta.', [avg, imp], 'Revisar los cambios que se hacen en el descanso.')


def _subs_state(s: Src) -> Optional[dict]:
    states = dig(s.win('usage'), ('cambios', 'por_estado')) or {}
    win, lose = states.get('ganando'), states.get('perdiendo')
    if not win or not lose:
        return None
    gap = win['minuto_medio'] - lose['minuto_medio']
    title = (f"Cambia antes cuando va perdiendo (minuto {num(lose['minuto_medio'], 0)}) que cuando va ganando "
             f"(minuto {num(win['minuto_medio'], 0)})" if gap >= 3 else
             f"Cambia a la misma hora ganando y perdiendo (minutos {num(win['minuto_medio'], 0)} y {num(lose['minuto_medio'], 0)})"
             if abs(gap) < 3 else f"Cambia antes cuando va ganando (minuto {num(win['minuto_medio'], 0)}) que cuando va perdiendo")
    ev = [{'id': 'cambios', 'value': v['minuto_medio'], 'n': v['n'], 'unit': 'minuto', 'source': 'eventos', 'window': s.window,
           'scope': f'estado:{k}'} for k, v in states.items()]
    return finding('jugadores_cambios_marcador', 'jugadores_cambios', ['sustituciones', 'contexto_marcador'], title,
                   '; '.join(f"{k}: minuto {num(v['minuto_medio'], 1)} ({v['n']} cambios)" for k, v in states.items()) + '.',
                   'Los cambios dependen del marcador: la hora del cambio no compara bien entre estados.', ev,
                   'Anticipar los cambios cuando el marcador lo permita.')


def jugadores(s: Src) -> dict:
    fs = [_core(s), _roles(s), _lineups(s), _subs(s), _subs_state(s)]
    first = next((f for f in fs if f), None)
    xi = (dig(s.win('usage'), ('plantilla',)) or [None])[0]
    return st.chapter('jugadores_cambios', 9, 'Jugadores y cambios: quién sostiene el sistema', fs,
                      f"{first['titulo']}." if first else None,
                      f"{xi['jugador']} jugó {num(xi['share_minutos'], 0)} % de los minutos del equipo." if xi else None, 'xi_lineup')


# ---------------------------------------------------------------- 10. ¿mereció ganar?
def _deserved(s: Src) -> Optional[dict]:
    rep = dig(s.analysis, ('replay', 'resumen')) or {}
    metrics = dig(s.analysis, ('replay', 'por_ventana', s.window, 'metricas')) or []
    xpts = next((m for m in metrics if m.get('id') == 'xpts'), None)
    surp = next((m for m in metrics if m.get('id') == 'resultado_sorpresivo'), None)
    if rep.get('puntos') is None or rep.get('xpts') is None:
        return None
    diff = rep['puntos'] - rep['xpts']
    per_match = diff / max(rep.get('n') or 1, 1)
    title = (f"Sumó {num(rep['puntos'], 0)} puntos y sus ocasiones valían {num(rep['xpts'], 1)}: {st.signed(diff, 1)} de diferencia")
    reading = ('Sumó más puntos de los que sus ocasiones pedían: parte del resultado vino de la eficacia o la fortuna.'
               if per_match > fw.STORY_BALANCE_PPP else
               'Sumó menos puntos de los que sus ocasiones pedían: el resultado quedó por debajo del juego.'
               if per_match < -fw.STORY_BALANCE_PPP else 'El resultado fue acorde a lo que generó en la cancha.')
    fact = (f"Puntos reales {num(rep['puntos'], 0)} y esperados {num(rep['xpts'], 1)}; {rep.get('sorpresivos')} resultados "
            f"sorpresivos (menos de 20 % de probabilidad) de {rep['n']}.")
    return finding('merecio_resultado', 'merecio_ganar', ['xg', 'simulacion'], title, fact, reading, [xpts, surp],
                   'Comparar puntos y xPts cada torneo.')


def _dominance(s: Src) -> Optional[dict]:
    rep = dig(s.analysis, ('replay', 'resumen')) or {}
    share, tilt = dig(rep, ('dominio', 'xg_share')), dig(rep, ('dominio', 'field_tilt'))
    xpts, ft = next((m for m in (dig(s.analysis, ('replay', 'por_ventana', s.window, 'metricas')) or []) if m.get('id') == 'xpts'), None), s.rec('offense', 'dominio', 'field_tilt')
    if share is None:
        return None
    title = (f"Se queda con {num(100 * share, 0)} % del xG de sus partidos" if share > 0.55 else
             f"Reparte el xG con sus rivales ({num(100 * share, 0)} % para el equipo)" if share >= 0.45 else
             f"Genera solo {num(100 * share, 0)} % del xG de sus partidos")
    fact = (f"Participación en el xG total: {num(100 * share, 1)} %" + (f"; field tilt {num(100 * tilt, 1)} %" if tilt is not None else '')
            + f" en {rep.get('n')} partidos.")
    return finding('merecio_dominio', 'merecio_ganar', ['xg', 'field_tilt', 'simulacion'], title, fact,
                   'Repetir cada partido 20,000 veces con el xG de sus tiros reales sirve para interpretar el resultado, '
                   'no para pronosticar.', [xpts, ft], 'Usar la repetición para explicar resultados, no para predecirlos.')


def _by_tournament(s: Src) -> Optional[dict]:
    rows = [r for r in (dig(s.analysis, ('replay', 'por_torneo')) or []) if r.get('window') == s.window and r.get('n')]
    if len(rows) < 2:
        return None
    best = max(rows, key=lambda r: r['puntos_por_partido'] - r['xpts_por_partido'])
    worst = min(rows, key=lambda r: r['puntos_por_partido'] - r['xpts_por_partido'])
    ev = [{'id': 'xpts', 'value': r['xpts_por_partido'], 'n': r['n'], 'unit': 'puntos por partido', 'source': 'eventos',
           'window': s.window, 'scope': f"torneo:{r['torneo']}"} for r in (best, worst)]
    title = (f"Su torneo más afortunado: {best['torneo']} ({num(best['puntos_por_partido'])} puntos por partido contra "
             f"{num(best['xpts_por_partido'])} esperados)")
    fact = '; '.join(f"{r['torneo']}: {num(r['puntos_por_partido'])} contra {num(r['xpts_por_partido'])} esperados, {r['sorpresivos']} sorpresivos"
                     for r in rows) + '.'
    return finding('merecio_torneos', 'merecio_ganar', ['simulacion'], title, fact,
                   f"El más desafortunado fue {worst['torneo']}; la diferencia entre puntos y xPts mezcla eficacia, fortuna y estado del marcador.",
                   ev, 'Comparar puntos y xPts torneo a torneo.')


def merecio(s: Src) -> dict:
    fs = [_deserved(s), _dominance(s), _by_tournament(s)]
    first = next((f for f in fs if f), None)
    surp = dig(s.analysis, ('replay', 'resumen', 'sorpresivos'))
    return st.chapter('merecio_ganar', 10, '¿Mereció ganar? Lo que dicen las ocasiones', fs,
                      f"{first['titulo']}." if first else None,
                      f"{surp} de sus {s.n} resultados fueron sorpresivos (menos de 20 % de probabilidad)." if surp is not None else None,
                      'replay_summary')


# ---------------------------------------------------------------- 11. tablero de KPIs
def _board(s: Src, rows: list) -> Optional[dict]:
    good = [(k, st.good_pct(k.get('ref_pct'), k['mejor'])) for k in rows]
    top = [k['nombre'].lower() for k, g in good if g is not None and g >= st.HIGH_MIN]
    low = [k['nombre'].lower() for k, g in good if g is not None and g <= st.LOW_MAX]
    title = (f"{len(top)} de {len(rows)} indicadores destacan sobre la liga" + (f"; {len(low)} {'queda' if len(low) == 1 else 'quedan'} por debajo de la mayoría" if low else ''))
    fact = '; '.join(f"{k['nombre']}: {num(k['value'])} ({rank(k.get('ref_pct')) or 'sin referencia de liga'})" for k in rows) + '.'
    return finding('tablero_resumen', 'tablero_kpis', ['kpis', 'xg', 'field_tilt', 'progresivos'], title, fact,
                   'Cada indicador se compara con la liga (percentil) y consigo mismo (semáforo en sus terciles); '
                   + (f"destaca en {_join(top)}." if top else 'ninguno destaca sobre la liga.'), rows,
                   'Revisar el tablero antes de cada partido.')


def _lights(s: Src, rows: list) -> Optional[dict]:
    cand = [k for k in rows if k.get('semaforo') and k.get('frase')
            and k['semaforo']['verde']['pts_partido'] is not None and k['semaforo']['rojo']['pts_partido'] is not None]
    if not cand:
        return None
    k = max(cand, key=lambda r: abs(r['semaforo']['verde']['pts_partido'] - r['semaforo']['rojo']['pts_partido']))
    v, r = k['semaforo']['verde'], k['semaforo']['rojo']
    return finding('tablero_semaforo', 'tablero_kpis', ['kpis', 'consistencia'],
                   f"En partidos en verde de {k['nombre'].lower()} sumó {num(v['pts_partido'])} puntos por partido contra {num(r['pts_partido'])} en rojo",
                   k['frase'] + f" Umbrales propios: {num(k['umbrales']['p33'], 2)} y {num(k['umbrales']['p67'], 2)}.",
                   'Asociación descriptiva: el semáforo no prueba que el indicador cause los puntos (el marcador también mueve el '
                   'territorio y la posesión).', [k], 'No tomar una asociación como regla sin revisar el contexto del partido.', modo='dt')


def tablero(s: Src) -> dict:
    rows = [k for k in s.kpi_rows if k.get('value') is not None]
    fs = [_board(s, rows) if rows else None, _lights(s, rows)]
    first = next((f for f in fs if f), None)
    best = max(((k, st.good_pct(k.get('ref_pct'), k['mejor'])) for k in rows if k.get('ref_pct') is not None),
               key=lambda kv: kv[1], default=None)
    return st.chapter('tablero_kpis', 11, 'Tablero de KPIs: siete números para seguir al equipo', fs,
                      f"{first['titulo']}." if first else None,
                      f"Su indicador más alto frente a la liga es {best[0]['nombre'].lower()}." if best else None, 'kpi_board')


# ---------------------------------------------------------------- 12. epílogo (fuera de ventana)
def _shift(epi: Src, off: Src) -> Optional[dict]:
    pairs = [(k, off.kpi(k['id'])) for k in epi.kpi_rows if k.get('value') is not None]
    pairs = [(e, o) for e, o in pairs if o]
    if not pairs:
        return None
    moves = []
    for e, o in pairs:
        ge, go = st.good_pct(e.get('ref_pct'), e['mejor']), st.good_pct(o.get('ref_pct'), o['mejor'])
        moves.append((e, o, None if ge is None or go is None else ge - go))
    moved = [m for m in moves if m[2] is not None and abs(m[2]) >= fw.STORY_PCT_SHIFT]
    title = (f"Fuera de ventana: {len(moved)} de {len(moves)} indicadores se mueven {fw.STORY_PCT_SHIFT} puntos o más de percentil "
             f"frente al Tricampeonato")
    fact = '; '.join(f"{e['nombre']}: {st.auto(e['value'])} ahora contra {st.auto(o['value'])} en la ventana oficial" for e, o, _ in moves) + '.'
    if moved:
        fact += f" Se mueven: {_join([m[0]['nombre'].lower() for m in moved])}."
    return finding('epilogo_cambios', 'epilogo', ['kpis', 'identidad'], title, fact,
                   'El epílogo (temporada 2025/26) queda fuera de la ventana oficial: se muestra para contexto y no entra a '
                   'las conclusiones del reto.', [e for e, _, _ in moves], 'Tomarlo como evidencia adicional, no como conclusión.')


def epilogo(epi: Src, off: Src) -> dict:
    fs = [_result(epi, 'epilogo_resultado', 'epilogo'), _shift(epi, off)]
    first = next((f for f in fs if f), None)
    return st.chapter('epilogo', 12, 'Epílogo: 2025/26, fuera de la ventana oficial', fs,
                      f"{first['titulo']}." if first else None, None, 'epilogue_compare')
