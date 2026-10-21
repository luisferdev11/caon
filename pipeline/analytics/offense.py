# ruff: noqa: UP045  (Python 3.9: se usa Optional, nunca "X | Y")
"""Con balón: construcción, progresión, ocasiones, OBV por acción y zona, dominio territorial (tema 'offense').

Fuente: posesiones ``an_<mid>`` (contrato sequences) + eventos v8, vía ``a4_facts``. Marco propio: el
protagonista ataca hacia x=120 (de izquierda a derecha en pantalla). npxG excluye penales; los penales no
entran al mapa de tiros. Cada número publicado es un registro de métrica con id del framework y, si se
puede, percentil frente a equipos-temporada de la liga (``a4_reference``).
"""
from __future__ import annotations

from typing import Any, Optional

import framework as fw

from analytics import a4_common as ac
from analytics import a4_reference, register

TOP_PROGRESSORS = fw.PROGRESSORS_TOP
OBV_TYPES = ('pase', 'conduccion', 'tiro', 'portero', 'otras')
SERIES_KEYS = ('field_tilt', 'progresion_limpia', 'npxg_tiro', 'tiros_zona', 'salida_limpia')
N_ZONES = 18
FRAME_NOTE = 'Protagonista ataca de izquierda a derecha (hacia x=120).'


def _pct(d: dict[str, int]) -> tuple[Optional[float], int]:
    return ac.ratio(d.get('ok', 0), d.get('n', 0), 100.0), d.get('n', 0)


def values(n: dict[str, Any]) -> ac.Values:
    """Valores de la ventana (o de una unidad de referencia) desde los conteos sumados."""
    o, m = n.get('off') or {}, n.get('partidos', 0)
    sal = o.get('salida') or {}
    obv = o.get('obv') or {}
    shots, poss = o.get('tiros_np', 0), o.get('posesiones', 0)
    f3 = o.get('f3', 0) + o.get('f3_rival', 0)
    out = {
        'salida_limpia': _pct(sal.get('total') or {}), 'salida_limpia_portero': _pct(sal.get('portero') or {}),
        'salida_limpia_robo': _pct(sal.get('robo') or {}), 'progresion_limpia': _pct(o.get('progresion') or {}),
        'saque_largo': (ac.ratio(o.get('gk_saque_largo', 0), o.get('gk_saque', 0), 100.0), o.get('gk_saque', 0)),
        'portero_juego_largo': (ac.ratio(o.get('gk_juego_largo', 0), o.get('gk_juego', 0), 100.0),
                                o.get('gk_juego', 0)),
        'prog_100': (ac.ratio(o.get('prog', 0), poss, 100.0), poss), 'prog_partido': (ac.ratio(o.get('prog', 0), m), m),
        'field_tilt': (ac.ratio(o.get('f3', 0), f3, 100.0), f3),
        'npxg_tiro': (ac.ratio(o.get('xg_np', 0.0), shots), shots),
        'tiros_zona': (ac.ratio(o.get('tiros_zona', 0), shots, 100.0), shots),
        'npxg_partido': (ac.ratio(o.get('xg_np', 0.0), m), m),
        'entradas_area': (ac.ratio(o.get('posesiones_area', 0), m), m),
        'creacion': (ac.ratio(o.get('posesiones_area', 0), poss, 100.0), poss),
        'obv_partido': (ac.ratio(obv.get('total', 0.0), m), m),
    }
    for t in OBV_TYPES:
        out[f'obv_{t}'] = (ac.ratio(obv.get(t, 0.0), m), m)
    return out


def _buildup(rec: ac.Recorder, v: ac.Values) -> dict[str, Any]:
    return {
        'saque_puerta_largo': rec.from_values(v, 'saque_largo', 'salida_portero', '% de saques de puerta largos',
                                              scope='saque_puerta'),
        'portero_en_juego_largo': rec.from_values(v, 'portero_juego_largo', 'salida_portero',
                                                  '% de pases largos del portero en juego', scope='portero_en_juego'),
        'salida_limpia': rec.from_values(v, 'salida_limpia', 'salida_limpia', '% de posesiones que nacen en x<40'),
        'salida_limpia_tras_portero': rec.from_values(v, 'salida_limpia_portero', 'salida_limpia',
                                                      '% (saque de puerta o portero)', scope='tras_portero'),
        'salida_limpia_tras_robo': rec.from_values(v, 'salida_limpia_robo', 'salida_limpia', '% (robo en juego)',
                                                   scope='tras_robo'),
    }


def _progression(rec: ac.Recorder, v: ac.Values, agg: dict[str, Any], ctx: Any,
                 rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = agg['n']['off'].get('prog', 0)
    top = ac.top_players(agg.get('prog_jugador') or {}, rows, key=lambda n: -n, limit=TOP_PROGRESSORS,
                         lineups_fn=getattr(ctx, 'load_lineups', ac.load_lineups))
    for p in top:
        p['pct_equipo'] = ac.rnd(ac.ratio(p['n'], total, 100.0), 1)
    return {
        'progresion_limpia': rec.from_values(v, 'progresion_limpia', 'progresion_limpia',
                                             '% de posesiones que nacen en x<60'),
        'prog_por_100': rec.from_values(v, 'prog_100', 'prog', 'acciones progresivas por 100 posesiones'),
        'prog_por_partido': rec.from_values(v, 'prog_partido', 'prog', 'acciones progresivas por partido',
                                            scope='por_partido'),
        'top_progresores': top,
    }


def _origins(rec: ac.Recorder, origen: dict[str, dict[str, float]], m: int) -> list[dict[str, Any]]:
    out = []
    for kind, row in sorted(origen.items(), key=lambda kv: -kv[1]['xg']):
        out.append({'origen': kind, 'nombre': ac.ORIGIN_ES.get(kind, kind), 'posesiones': row['posesiones'],
                    'tiros': row['tiros'], 'goles': row['goles'],
                    'xg': rec('xg_origen', ac.ratio(row['xg'], m), m, 'xG sin penal por partido', scope=f'origen:{kind}')})
    return out


def _chances(rec: ac.Recorder, v: ac.Values, agg: dict[str, Any]) -> dict[str, Any]:
    m = agg['n']['partidos']
    np_shots = [[round(r[0]), round(r[1]), r[2], r[3]] for r in agg.get('tiros') or [] if not r[4]]
    return {
        'npxg_por_tiro': rec.from_values(v, 'npxg_tiro', 'npxg_por_tiro', 'xG por tiro'),
        'tiros_zona_remate': rec.from_values(v, 'tiros_zona', 'tiros_zona_remate', '% de tiros sin penal'),
        'npxg_por_partido': rec.from_values(v, 'npxg_partido', 'xg', 'xG sin penal por partido', scope='eventos'),
        'entradas_area': rec.from_values(v, 'entradas_area', 'entradas_area', 'posesiones por partido'),
        'creacion': rec.from_values(v, 'creacion', 'creacion', '% de posesiones'),
        'por_origen': _origins(rec, agg['n']['off'].get('origen') or {}, m),
        'mapa_tiros': {'cols': ['x', 'y', 'xg', 'goal'], 'rows': np_shots, 'n': len(np_shots),
                       'nota': 'Tiros reales sin penal; ' + FRAME_NOTE},
    }


def _validation(ctx: Any, rows: list[dict[str, Any]], facts: list[dict[str, Any]]) -> dict[str, Any]:
    """OBV y npxG de eventos contra team-stats del mismo partido (correlación y diferencia media)."""
    load = getattr(ctx, 'load_team_stats', ac.load_team_stats)
    pairs: dict[str, list[tuple[float, float]]] = {'obv_total': [], 'obv_pase': [], 'obv_conduccion': [], 'xg_np': []}
    for row, f in zip(rows, facts):
        ts = next((r for r in load(row['id']) or [] if r.get('team_id') == row['team_id']), None)
        if not ts:
            continue
        o = f['n']['off']
        for key, mine, theirs in (('obv_total', o['obv']['total'], ts.get('team_match_obv')),
                                  ('obv_pase', o['obv']['pase'], ts.get('team_match_obv_pass')),
                                  ('obv_conduccion', o['obv']['conduccion'], ts.get('team_match_obv_dribble_carry')),
                                  ('xg_np', o['xg_np'], ts.get('team_match_np_xg'))):
            if theirs is not None:
                pairs[key].append((mine, float(theirs)))
    return {k: {'n': len(p), 'r': ac.pearson([a for a, _ in p], [b for _, b in p]),
                'dif_media_abs': ac.rnd(sum(abs(a - b) for a, b in p) / len(p), 4) if p else None}
            for k, p in pairs.items()}


def _obv(rec: ac.Recorder, v: ac.Values, agg: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    m = agg['n']['partidos']
    zones = agg['n']['off'].get('obv_zona') or {}
    return {
        'por_partido': rec.from_values(v, 'obv_partido', 'obv', 'OBV por partido'),
        'por_tipo': {t: rec.from_values(v, f'obv_{t}', 'obv', 'OBV por partido', scope=f'tipo:{t}')
                     for t in OBV_TYPES},
        'por_zona': [ac.rnd(ac.ratio(zones.get(str(z), 0.0), m), 4) for z in range(N_ZONES)],
        'por_zona_nota': 'OBV por partido de pases, conducciones y regates según la zona 6×3 de inicio '
                         '(índice = columna·3 + carril). ' + FRAME_NOTE,
        'validacion': validation,
    }


def window_payload(ctx: Any, wf: dict[str, Any], window: str, pops: dict[str, list[float]]) -> dict[str, Any]:
    """Payload de una ventana a partir de sus hechos sumados."""
    agg, rows = wf['agg'], wf['rows']
    v = values(agg['n'])
    rec = ac.Recorder(ctx.entity_id, window, pops)
    return {
        'n_partidos': agg['n']['partidos'],
        'construccion': _buildup(rec, v),
        'progresion': _progression(rec, v, agg, ctx, rows),
        'ocasiones': _chances(rec, v, agg),
        'obv': _obv(rec, v, agg, _validation(ctx, rows, wf['facts'])),
        'dominio': {'field_tilt': rec.from_values(v, 'field_tilt', 'field_tilt', '% de acciones en último tercio')},
        'serie': ac.series(rows, wf['facts'], values, SERIES_KEYS),
    }


def build(ctx: Any) -> dict[str, Any]:
    """Payload por ventana (oficial | epilogo | temprano)."""
    wins = ac.window_facts(ctx)
    pops = a4_reference.populations_for(ctx, values) if wins else {}
    return {'ventanas': {w: window_payload(ctx, wf, w, pops) for w, wf in wins.items()}, 'marco': FRAME_NOTE,
            'referencia': ac.reference_note(pops)}


register('offense', build)
