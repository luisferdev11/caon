"""Temporal aggregation of observed match summaries.

The module consumes the per-match extracts already produced by extract.py.
It deliberately reports coverage and dispersion instead of labeling a style
as stable or unstable.
"""
import math
import statistics

from contextual import summarize_bucket

PERIOD_SIZE = 8
MIN_PERIOD_MATCHES = 5
METRICS = (
    'possession', 'directness', 'pace_towards_goal', 'ppda',
    'pressures_per_opp_pass', 'shots', 'xg', 'xga',
    'transition_shots_per_possession',
)


def _rate(num, den):
    return num / den if den else None


def _finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def match_metrics(team):
    """Derive comparable per-match values from the existing event summary."""
    m = team.get('m') or {}
    possessions = team.get('poss', 0) or 0
    shots = sum(sum(row) for row in (team.get('shot') or []))
    return {
        'possession': _rate(m.get('passes', 0), m.get('passes', 0) + m.get('opp_passes', 0)),
        'directness': _rate(m.get('dir_fwd', 0), m.get('dir_tot', 0)),
        'pace_towards_goal': _rate(m.get('pace2_sum', 0), m.get('pace2_n', 0)),
        'ppda': _rate(m.get('opp_passes_own60', 0), m.get('ppda_den', 0)),
        'pressures_per_opp_pass': _rate(m.get('pressures', 0), m.get('opp_passes', 0)),
        'shots': shots,
        'xg': m.get('np_xg') if _finite(m.get('np_xg')) else None,
        'xga': m.get('np_xga') if _finite(m.get('np_xga')) else None,
        'transition_shots_per_possession': _rate(m.get('counter_shots2', 0), possessions),
    }


def _context_add(target, source):
    for key, value in (source or {}).items():
        if isinstance(value, (int, float)) and math.isfinite(value):
            target[key] = target.get(key, 0) + value


def _context_rates(counter):
    return summarize_bucket(counter)


def _context_period(rows):
    dimensions = {'score_state': {}, 'venue': {}}
    for dimension, rates in dimensions.items():
        keys = sorted({key for row in rows for key in (row['context'].get(dimension) or {})})
        for key in keys:
            counter = {}
            for row in rows:
                values = (row['context'].get(dimension) or {}).get(key)
                if not values:
                    continue
                _context_add(counter, values)
                if 'matches' not in values:
                    counter['matches'] = counter.get('matches', 0) + int(values.get('seconds', 0) > 0)
            rates[key] = _context_rates(counter)
    return dimensions


def aggregate_period(rows):
    metrics = {}
    coverage = {}
    for metric in METRICS:
        values = [row['metrics'].get(metric) for row in rows]
        valid = [value for value in values if _finite(value)]
        coverage[metric] = {'valid_matches': len(valid), 'missing_matches': len(values) - len(valid)}
        metrics[metric] = round(statistics.fmean(valid), 6) if valid else None
    return {
        'start': rows[0]['date'],
        'end': rows[-1]['date'],
        'matches': len(rows),
        'observations': coverage,
        'metrics': metrics,
        'sufficient_sample': len(rows) >= MIN_PERIOD_MATCHES,
        'context': _context_period(rows),
    }


def _period_rows(rows):
    periods = []
    for start in range(0, len(rows), PERIOD_SIZE):
        chunk = rows[start:start + PERIOD_SIZE]
        if len(chunk) < MIN_PERIOD_MATCHES and periods:
            periods[-1].extend(chunk)
        else:
            periods.append(chunk)
    return periods


def build_temporal(entity_matches, match_by_id, extracts):
    rows = []
    unavailable = []
    seen = set()
    for item in sorted(entity_matches, key=lambda value: (value.get('date') or '', value['mid'])):
        mid = item['mid']
        if mid in seen:
            continue
        seen.add(mid)
        match = match_by_id.get(mid)
        extract = extracts.get(mid)
        if not match or not extract:
            unavailable.append({'match_id': mid, 'reason': 'metadatos o extracción ausente'})
            continue
        team = next((value for value in extract.get('teams', {}).values()
                     if value.get('name') == match.get('_entity_team')), None)
        if team is None:
            unavailable.append({'match_id': mid, 'reason': 'equipo no encontrado en la extracción'})
            continue
        rows.append({
            'match_id': mid,
            'date': item.get('date') or match.get('match_date'),
            'venue': item.get('side'),
            'opponent': match.get('_opponent'),
            'score': match.get('_score'),
            'metrics': match_metrics(team),
            'context': team.get('context') or {},
        })
    rows.sort(key=lambda value: (value['date'] or '', value['match_id']))
    periods = [aggregate_period(chunk) for chunk in _period_rows(rows)]
    series = {}
    for metric in METRICS:
        values = [period['metrics'][metric] for period in periods if period['metrics'][metric] is not None]
        delta = [round(values[index] - values[index - 1], 6) for index in range(1, len(values))]
        series[metric] = {
            'period_values': values,
            'mean': round(statistics.fmean(values), 6) if values else None,
            'stdev': round(statistics.stdev(values), 6) if len(values) >= 2 else None,
            'min': min(values) if values else None,
            'max': max(values) if values else None,
            'consecutive_differences': delta,
            'periods_with_data': len(values),
        }
    return {
        'period_size': PERIOD_SIZE,
        'minimum_period_matches': MIN_PERIOD_MATCHES,
        'matches': rows,
        'periods': periods,
        'series': series,
        'coverage': {
            'input_matches': len(entity_matches),
            'observed_matches': len(rows),
            'unavailable_matches': unavailable,
        },
        'note': 'Variación descriptiva por bloques cronológicos; no establece estabilidad ni causalidad.',
    }
