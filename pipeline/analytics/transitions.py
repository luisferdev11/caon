"""Transiciones y pérdidas (tema 'transitions'): tipología del error con tasa de costosa por tipo, tercio, zona y
jugador; contrapresión efectiva (≤5 s); transiciones de 10 s y contraataques de 15 s en ambos sentidos.

Pérdida en juego = la siguiente posesión rival nace en juego abierto (``extract_360.find_losses``). Tipología
única de ``frames360.classify_error``; 'aislado' solo con 360 (cota inferior: jugadores visibles). Costosa =
tiro rival ≤15 s tras el robo; letal = gol. Asociación descriptiva, no causal.
"""
from __future__ import annotations

from typing import Any

from analytics import a4_common as ac
from analytics import a4_reference, register
from analytics.a4_transition_facts import ERROR_TYPES

TOP_PLAYERS = 10
N_ZONES = 18
THIRDS = ('propio', 'medio', 'final')
TYPE_ES = {'no_forzado': 'No forzado', 'bajo_presion': 'Bajo presión', 'decision_arriesgada': 'Decisión arriesgada',
           'duelo_perdido': 'Duelo perdido', 'aislado': 'Aislado (360)', 'otro': 'Otro'}
THIRD_ES = {'propio': 'Tercio propio', 'medio': 'Medio campo', 'final': 'Último tercio'}
SERIES_KEYS = ('contrapresion_efectiva', 'costosas_partido', 'perdidas_partido')
NOTE = ('Pérdida en juego: la siguiente posesión rival nace en juego abierto. Costosa: tiro rival en ≤15 s; '
        'letal: gol. Descriptivo, no causal.')


def values(n: dict[str, Any]) -> ac.Values:
    """Valores de la ventana (o de una unidad de referencia) desde los conteos sumados."""
    t, m = n.get('tr') or {}, n.get('partidos', 0)
    lo = t.get('perdidas') or {}
    total = lo.get('n', 0)
    tr, tc = t.get('transiciones') or {}, t.get('transiciones_c') or {}
    iso = t.get('aislado') or {}
    out = {
        'perdidas_partido': (ac.ratio(total, m), m), 'costosas_partido': (ac.ratio(lo.get('costosa', 0), m), m),
        'tasa_costosa': (ac.ratio(lo.get('costosa', 0), total, 100.0), total),
        'contrapresion_efectiva': (ac.ratio(lo.get('rec5', 0), total, 100.0), total),
        'transiciones_partido': (ac.ratio(tr.get('n', 0), m), m), 'xg10_partido': (ac.ratio(tr.get('xg10', 0.0), m), m),
        'contras_partido': (ac.ratio((t.get('contras') or {}).get('n', 0), m), m),
        'transiciones_c_partido': (ac.ratio(tc.get('n', 0), m), m),
        'xg10_c_partido': (ac.ratio(tc.get('xg10', 0.0), m), m),
        'contras_c_partido': (ac.ratio((t.get('contras_c') or {}).get('n', 0), m), m),
        'aislado_pct': (ac.ratio(iso.get('aisladas', 0), iso.get('validas', 0), 100.0), iso.get('validas', 0)),
    }
    for tipo, row in (t.get('por_tipo') or {}).items():
        out[f'pct_{tipo}'] = (ac.ratio(row['n'], total, 100.0), total)
        out[f'tasa_{tipo}'] = (ac.ratio(row['costosa'], row['n'], 100.0), row['n'])
    return out


def _types(rec: ac.Recorder, v: ac.Values, by_type: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    out = []
    for tipo in ERROR_TYPES:
        row = by_type.get(tipo) or {}
        if not row.get('n'):
            continue
        out.append({'tipo': tipo, 'nombre': TYPE_ES[tipo], 'n': row['n'], 'costosas': row['costosa'],
                    'letales': row['letal'],
                    'pct': rec.from_values(v, f'pct_{tipo}', 'tipo_error', '% de pérdidas', scope=f'pct:{tipo}'),
                    'tasa_costosa': rec.from_values(v, f'tasa_{tipo}', 'perdida_costosa', '% de pérdidas del tipo',
                                                    scope=f'tipo:{tipo}')})
    return out


def _thirds(rec: ac.Recorder, by_third: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    out = []
    for third in THIRDS:
        row = by_third.get(third) or {'n': 0, 'costosa': 0, 'letal': 0}
        out.append({'tercio': third, 'nombre': THIRD_ES[third], 'n': row['n'], 'costosas': row['costosa'],
                    'letales': row['letal'],
                    'tasa_costosa': rec('perdida_costosa', ac.ratio(row['costosa'], row['n'], 100.0), row['n'],
                                        '% de pérdidas del tercio', scope=f'tercio:{third}')})
    return out


def _players(ctx: Any, agg: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    top = ac.top_players(agg.get('perdida_jugador') or {}, rows, key=lambda r: (-r['costosa'], -r['n']),
                         limit=TOP_PLAYERS, lineups_fn=getattr(ctx, 'load_lineups', ac.load_lineups))
    return [{'jugador': p['jugador'], 'player_id': p['player_id'], 'n': p['n'], 'costosas': p['costosa'],
             'letales': p['letal'], 'tasa_costosa': ac.rnd(ac.ratio(p['costosa'], p['n'], 100.0), 1)} for p in top]


def _losses(rec: ac.Recorder, v: ac.Values, agg: dict[str, Any], ctx: Any,
            rows: list[dict[str, Any]]) -> dict[str, Any]:
    t = agg['n']['tr']
    zones = t.get('por_zona') or {}
    zone_rows = []
    for z in range(N_ZONES):
        row = zones.get(str(z)) or {'n': 0, 'costosa': 0, 'letal': 0}
        zone_rows.append([z, row['n'], row['costosa'], row['letal']])
    iso = t.get('aislado') or {}
    return {
        'por_partido': rec.from_values(v, 'perdidas_partido', 'perdida', 'pérdidas en juego por partido'),
        'costosas_por_partido': rec.from_values(v, 'costosas_partido', 'perdida_costosa', 'pérdidas por partido'),
        'tasa_costosa': rec.from_values(v, 'tasa_costosa', 'perdida_costosa', '% de pérdidas en juego', scope='tasa'),
        'letales': rec('perdida_letal', t['perdidas'].get('letal', 0), agg['n']['partidos'], 'pérdidas (total ventana)'),
        'por_tipo': _types(rec, v, t.get('por_tipo') or {}),
        'por_tercio': _thirds(rec, t.get('por_tercio') or {}),
        'por_zona': {'cols': ['zona', 'n', 'costosas', 'letales'], 'rows': zone_rows,
                     'nota': 'Zona 6×3 del error en el marco propio (índice = columna·3 + carril).'},
        'por_jugador': _players(ctx, agg, rows),
        'aislado_360': {'validas': iso.get('validas', 0), 'aisladas': iso.get('aisladas', 0),
                        'pct': rec.from_values(v, 'aislado_pct', 'tipo_error', '% de pérdidas con 360 válido',
                                               scope='aislado_360', source='360',
                                               nota='Sin compañero visible a ≤10 yd (cota inferior).')},
        'nota': NOTE,
    }


def _transitions(rec: ac.Recorder, v: ac.Values, t: dict[str, Any]) -> dict[str, Any]:
    def side(key: str, xg_key: str, scope: str) -> dict[str, Any]:
        row = t.get(key) or {}
        return {'por_partido': rec.from_values(v, key + '_partido', 'transicion', 'posesiones tras robo por partido',
                                               scope=scope),
                'xg_10s_por_partido': rec.from_values(v, xg_key, 'transicion', 'xG en los primeros 10 s por partido',
                                                      scope=f'{scope}:xg_10s'),
                'tiros_10s': row.get('tiros10', 0), 'goles_10s': row.get('goles10', 0)}
    return {'ofensivas': side('transiciones', 'xg10_partido', 'propia'),
            'defensivas': side('transiciones_c', 'xg10_c_partido', 'concedida'),
            'contraataques': {'por_partido': rec.from_values(v, 'contras_partido', 'contraataque', 'por partido'),
                              'goles': (t.get('contras') or {}).get('goles', 0)},
            'contraataques_concedidos': {'por_partido': rec.from_values(v, 'contras_c_partido', 'contraataque',
                                                                        'por partido', scope='concedido'),
                                         'goles': (t.get('contras_c') or {}).get('goles', 0)}}


def window_payload(ctx: Any, wf: dict[str, Any], window: str, pops: dict[str, list[float]]) -> dict[str, Any]:
    """Payload de una ventana a partir de sus hechos sumados."""
    agg, rows = wf['agg'], wf['rows']
    v = values(agg['n'])
    rec = ac.Recorder(ctx.entity_id, window, pops)
    return {
        'n_partidos': agg['n']['partidos'],
        'perdidas': _losses(rec, v, agg, ctx, rows),
        'contrapresion_efectiva': rec.from_values(v, 'contrapresion_efectiva', 'contrapresion_efectiva',
                                                  '% de pérdidas recuperadas en ≤5 s'),
        'transiciones': _transitions(rec, v, agg['n']['tr']),
        'serie': ac.series(rows, wf['facts'], values, SERIES_KEYS),
    }


def build(ctx: Any) -> dict[str, Any]:
    """Payload por ventana (oficial | epilogo | temprano)."""
    wins = ac.window_facts(ctx)
    pops = a4_reference.populations_for(ctx, values) if wins else {}
    return {'ventanas': {w: window_payload(ctx, wf, w, pops) for w, wf in wins.items()},
            'referencia': ac.reference_note(pops)}


register('transitions', build)
