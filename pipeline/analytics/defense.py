"""Sin balón: presión por fase, PPDA, contrapresión, recuperaciones nombradas y lo concedido (tema 'defense').

Fuente: posesiones ``an_<mid>`` + eventos v8, vía ``a4_facts``. Presiones y robos están en el marco propio
(alta x≥80, bloque medio 40–80, bajo x<40). Los tiros rivales se voltean con ``framework.to_frame``: el
protagonista defiende la portería IZQUIERDA (x=0). PPDA de eventos: pases rivales en juego con x<72 (su marco)
por intercepción, falta, entrada o regate sufrido propio con x≥48; se valida contra ``team_match_ppda``.
"""
from __future__ import annotations

from typing import Any

from analytics import a4_common as ac
from analytics import a4_reference, register
from analytics.a4_facts import BANDS

SERIES_KEYS = ('ppda', 'intensidad_alta', 'rec_campo_rival', 'xg_c')
N_ZONES = 18
FRAME_NOTE = 'Tiros concedidos: el protagonista defiende la portería izquierda (x=0).'


def values(n: dict[str, Any]) -> ac.Values:
    """Valores de la ventana (o de una unidad de referencia) desde los conteos sumados."""
    d, m = n.get('def') or {}, n.get('partidos', 0)
    press, acts, rival = d.get('presiones') or {}, d.get('acciones_def') or {}, d.get('acciones_rival') or {}
    robos, robos_tiro = d.get('robos') or {}, d.get('robos_tiro') or {}
    shots_c = d.get('tiros_np_c', 0)
    total_press = sum(press.values())
    out = {
        'ppda': (ac.ratio(d.get('ppda_pases', 0), d.get('ppda_acciones', 0)), d.get('ppda_acciones', 0)),
        'pct_presiones_altas': (ac.ratio(press.get('alta', 0), total_press, 100.0), total_press),
        'contrapresiones': (ac.ratio(d.get('contrapresiones', 0), m), m),
        'rec_campo_rival': (ac.ratio(robos.get('campo_rival', 0), m), m),
        'rec_alta': (ac.ratio(robos.get('alta', 0), m), m),
        'rec_campo_rival_tiro': (ac.ratio(robos_tiro.get('campo_rival', 0), m), m),
        'rec_alta_tiro': (ac.ratio(robos_tiro.get('alta', 0), m), m),
        'xg_c': (ac.ratio(d.get('xg_np_c', 0.0), m), m),
        'npxg_tiro_c': (ac.ratio(d.get('xg_np_c', 0.0), shots_c), shots_c),
        'tiros_zona_c': (ac.ratio(d.get('tiros_zona_c', 0), shots_c, 100.0), shots_c),
        'entradas_area_c': (ac.ratio(d.get('posesiones_area_c', 0), m), m),
        'x_media_c': (ac.ratio(d.get('x_tiros_np_c', 0.0), shots_c), shots_c),
    }
    for b in BANDS:
        out[f'intensidad_{b}'] = (ac.ratio(acts.get(b, 0), rival.get(b, 0)), rival.get(b, 0))
        out[f'presiones_{b}'] = (ac.ratio(press.get(b, 0), m), m)
    return out


def _ppda_validation(ctx: Any, rows: list[dict[str, Any]], facts: list[dict[str, Any]]) -> dict[str, Any]:
    """PPDA de eventos contra team_match_ppda (correlación por partido y cociente medio)."""
    load = getattr(ctx, 'load_team_stats', ac.load_team_stats)
    pairs = []
    for row, f in zip(rows, facts):
        ts = next((r for r in load(row['id']) or [] if r.get('team_id') == row['team_id']), None)
        mine = values(f['n'])['ppda'][0]
        if ts and ts.get('team_match_ppda') and mine is not None:
            pairs.append((mine, float(ts['team_match_ppda'])))
    return {'n': len(pairs), 'r': ac.pearson([a for a, _ in pairs], [b for _, b in pairs]),
            'cociente_medio': ac.rnd(sum(a / b for a, b in pairs) / len(pairs), 3) if pairs else None,
            'nota': 'PPDA de eventos vs team-stats; la escala difiere (StatsBomb cuenta más acciones defensivas).'}


def _pressing(rec: ac.Recorder, v: ac.Values, validation: dict[str, Any]) -> dict[str, Any]:
    return {
        'ppda': rec.from_values(v, 'ppda', 'ppda', 'pases rivales por acción defensiva', scope='eventos'),
        'intensidad_por_fase': {b: rec.from_values(v, f'intensidad_{b}', 'fase_presion',
                                                   'presiones y acciones defensivas por acción rival',
                                                   scope=f'intensidad:{b}') for b in BANDS},
        'presiones_por_fase': {b: rec.from_values(v, f'presiones_{b}', 'fase_presion', 'presiones por partido',
                                                  scope=f'presiones:{b}') for b in BANDS},
        'pct_presiones_altas': rec.from_values(v, 'pct_presiones_altas', 'fase_presion', '% de presiones en x≥80',
                                               scope='pct_alta'),
        'contrapresiones': rec.from_values(v, 'contrapresiones', 'contrapresion', 'presiones por partido'),
        'validacion_ppda': validation,
    }


def _recoveries(rec: ac.Recorder, v: ac.Values, agg: dict[str, Any]) -> dict[str, Any]:
    m = agg['n']['partidos']
    zones = agg['n']['def'].get('robos_zona') or {}
    return {
        'rec_campo_rival': rec.from_values(v, 'rec_campo_rival', 'rec_campo_rival', 'robos por partido'),
        'rec_alta': rec.from_values(v, 'rec_alta', 'rec_alta', 'robos por partido'),
        'rec_campo_rival_con_tiro': rec.from_values(v, 'rec_campo_rival_tiro', 'presion_alta_tiros',
                                                    'posesiones con tiro ≤15 s por partido', scope='robo_x60'),
        'rec_alta_con_tiro': rec.from_values(v, 'rec_alta_tiro', 'presion_alta_tiros',
                                             'posesiones con tiro ≤15 s por partido', scope='robo_x80'),
        'por_zona': [zones.get(str(z), 0) for z in range(N_ZONES)],
        'por_zona_por_partido': [ac.rnd(ac.ratio(zones.get(str(z), 0), m), 3) for z in range(N_ZONES)],
        'por_zona_nota': 'Robos por zona 6×3 en el marco propio (índice = columna·3 + carril).',
    }


def _origins_conceded(rec: ac.Recorder, origen: dict[str, dict[str, float]], m: int) -> list[dict[str, Any]]:
    out = []
    for kind, row in sorted(origen.items(), key=lambda kv: -kv[1]['xg']):
        out.append({'origen': kind, 'nombre': ac.ORIGIN_ES.get(kind, kind), 'posesiones': row['posesiones'],
                    'tiros': row['tiros'], 'goles': row['goles'],
                    'xg': rec('xg_concedido', ac.ratio(row['xg'], m), m, 'xG sin penal por partido',
                              scope=f'origen:{kind}')})
    return out


def _conceded(rec: ac.Recorder, v: ac.Values, agg: dict[str, Any]) -> dict[str, Any]:
    m = agg['n']['partidos']
    rows = [[round(r[0]), round(r[1]), r[2], r[3]] for r in agg.get('tiros_c') or [] if not r[4]]
    return {
        'xg_concedido': rec.from_values(v, 'xg_c', 'xg_concedido', 'xG sin penal por partido'),
        'npxg_por_tiro': rec.from_values(v, 'npxg_tiro_c', 'npxg_por_tiro', 'xG por tiro concedido',
                                         scope='concedido'),
        'tiros_zona_remate': rec.from_values(v, 'tiros_zona_c', 'tiros_zona_remate', '% de tiros rivales sin penal',
                                             scope='concedido'),
        'entradas_area': rec.from_values(v, 'entradas_area_c', 'entradas_area', 'posesiones rivales por partido',
                                         scope='concedido'),
        'x_media_tiros_concedidos': rec.from_values(v, 'x_media_c', 'x_media_tiros_concedidos',
                                                    'yd desde la portería propia (x=0)'),
        'por_origen': _origins_conceded(rec, agg['n']['def'].get('origen_c') or {}, m),
        'mapa_tiros': {'cols': ['x', 'y', 'xg', 'goal'], 'rows': rows, 'n': len(rows),
                       'nota': 'Tiros rivales reales sin penal; ' + FRAME_NOTE},
    }


def window_payload(ctx: Any, wf: dict[str, Any], window: str, pops: dict[str, list[float]]) -> dict[str, Any]:
    """Payload de una ventana a partir de sus hechos sumados."""
    agg, rows = wf['agg'], wf['rows']
    v = values(agg['n'])
    rec = ac.Recorder(ctx.entity_id, window, pops)
    return {
        'n_partidos': agg['n']['partidos'],
        'presion': _pressing(rec, v, _ppda_validation(ctx, rows, wf['facts'])),
        'recuperaciones': _recoveries(rec, v, agg),
        'concedido': _conceded(rec, v, agg),
        'serie': ac.series(rows, wf['facts'], values, SERIES_KEYS),
    }


def build(ctx: Any) -> dict[str, Any]:
    """Payload por ventana (oficial | epilogo | temprano)."""
    wins = ac.window_facts(ctx)
    pops = a4_reference.populations_for(ctx, values) if wins else {}
    return {'ventanas': {w: window_payload(ctx, wf, w, pops) for w, wf in wins.items()}, 'marco': FRAME_NOTE,
            'referencia': ac.reference_note(pops)}


register('defense', build)
