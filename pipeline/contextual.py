"""Chronological contextual counts; exposure is observed match-clock time, not ball-in-play time."""
import collections

import framework as fw
from metric_utils import finite, ratio

STATES = ('winning', 'drawing', 'losing')
VENUES = ('home', 'away', 'unknown')
ONBALL = {'Pass', 'Carry', 'Dribble', 'Shot'}
COUNTS = ('seconds', 'possessions', 'possession_starts', 'actions', 'opponent_actions', 'events', 'passes',
          'opponent_passes', 'forward_passes', 'forward_distance', 'pass_distance', 'shots', 'xg', 'xga',
          'pressures', 'counterpressures', 'ppda_passes', 'ppda_def_actions', 'recoveries', 'losses',
          'transition_shots', 'pace_sum', 'pace_n', 'red_cards', 'opponent_red_cards',
          'seconds_with_red_card', 'missing_xg', 'missing_xga', 'missing_pass_geometry',
          'missing_ppda_location', 'clock_incomplete')


def period_seconds(event):
    try:
        h, m, s = event['timestamp'].split(':')
        value = int(h) * 3600 + int(m) * 60 + float(s)
    except (KeyError, ValueError, TypeError, AttributeError):
        minute, second = event.get('minute'), event.get('second')
        if not finite(minute) or not finite(second): return None
        value = minute * 60 + second - {1: 0, 2: 2700, 3: 5400, 4: 6300}.get(event.get('period', 1), 0)
    return value if finite(value) and value >= 0 else None


def ordered_events(events):
    # index is the provider's sequence within a period, preserving tied timestamps.
    return sorted((e for e in events if e.get('period', 1) in (1, 2, 3, 4)),
                  key=lambda e: (e.get('period', 1), e.get('index') if finite(e.get('index')) else float('inf'),
                                 period_seconds(e) if period_seconds(e) is not None else float('inf')))


def state_for(scores, tid):
    diff = scores.get(tid, 0) - sum(v for team, v in scores.items() if team != tid)
    return 'winning' if diff > 0 else 'losing' if diff < 0 else 'drawing'


def score_timeline(events, team_ids):
    score, before, after = collections.Counter(), [], []
    goals_for = [e for e in events if e.get('type', {}).get('name') == 'Own Goal For']
    for e in events:
        before.append(dict(score))
        kind, tid = e.get('type', {}).get('name'), e.get('team', {}).get('id')
        if kind == 'Shot' and e.get('shot', {}).get('outcome', {}).get('name') == 'Goal' or kind == 'Own Goal For': score[tid] += 1
        elif kind == 'Own Goal Against':
            paired = any(g.get('team', {}).get('id') != tid and
                         (g.get('id') in (e.get('related_events') or []) or
                          (g.get('period') == e.get('period') and period_seconds(g) is not None and period_seconds(g) == period_seconds(e)))
                         for g in goals_for)
            if not paired:
                opponent = next((t for t in team_ids if t != tid), None)
                if opponent is not None: score[opponent] += 1
        after.append(dict(score))
    return before, after, dict(score)


def defensive_action(e):
    kind = e.get('type', {}).get('name')
    return kind in ('Interception', 'Foul Committed') or (kind == 'Duel' and e.get('duel', {}).get('type', {}).get('name') == 'Tackle')


def venue_for(tid, metadata):
    metadata = metadata or {}
    if tid == metadata.get('home_team', {}).get('home_team_id'): return 'home'
    if tid == metadata.get('away_team', {}).get('away_team_id'): return 'away'
    return 'unknown'


def extract_context(events, metadata=None, is_sp=None):
    events = ordered_events(events)
    ids = list(dict.fromkeys(e.get('team', {}).get('id') for e in events if e.get('team', {}).get('id') is not None))
    if len(ids) != 2: return {}, {'available': False, 'warnings': ['se requieren dos equipos']}
    before, after, final = score_timeline(events, ids)
    warnings = []
    score_valid = True
    if metadata:
        for side in ('home', 'away'):
            expected = metadata.get(side + '_score')
            tid = metadata.get(side + '_team', {}).get(side + '_team_id')
            if finite(expected) and tid in ids and expected != final.get(tid, 0):
                score_valid = False
        if not score_valid: warnings.append('marcador_final_no_coincide: estados no disponibles')
    if any(venue_for(tid, metadata) == 'unknown' for tid in ids): warnings.append('localia_sin_metadatos')
    missing_indexes = len({e.get('index') for e in events}) != len(events) or any(not finite(e.get('index')) for e in events)
    if missing_indexes:
        # Do not claim score reconstruction if the chronological order is ambiguous.
        score_valid = False
        warnings.append('indices_ausentes_o_duplicados: estados no disponibles')
    result = {tid: {dim: {key: {c: 0 for c in COUNTS} for key in keys}
                    for dim, keys in [('score_state', STATES + ('unknown',)), ('venue', VENUES)]} for tid in ids}
    def buckets(tid, score):
        return [result[tid]['score_state'][state_for(score, tid) if score_valid else 'unknown'],
                result[tid]['venue'][venue_for(tid, metadata)]]
    possessions_seen = collections.defaultdict(set)
    reds = collections.Counter()
    # Count metrics at the pre-event state. A goal affects only subsequent actions/intervals.
    for i, e in enumerate(events):
        tid = e.get('team', {}).get('id')
        if tid not in result: continue
        opponent = next(t for t in ids if t != tid)
        kind = e.get('type', {}).get('name')
        loc = e.get('location') or []
        for c in buckets(tid, before[i]):
            c['events'] += 1
            c['actions'] += kind in ONBALL
            if kind == 'Pass':
                c['passes'] += 1
                end = (e.get('pass') or {}).get('end_location') or []
                if len(loc) >= 2 and len(end) >= 2 and all(finite(v) for v in loc[:2] + end[:2]):
                    dx, dy = end[0] - loc[0], end[1] - loc[1]
                    c['forward_passes'] += dx > 0
                    c['forward_distance'] += max(dx, 0)
                    c['pass_distance'] += (dx * dx + dy * dy) ** .5
                else: c['missing_pass_geometry'] += 1
            if kind == 'Shot':
                c['shots'] += 1
                xg = (e.get('shot') or {}).get('statsbomb_xg')
                if finite(xg) and 0 <= xg <= 1: c['xg'] += xg
                else: c['missing_xg'] += 1
            if kind == 'Pressure':
                c['pressures'] += 1
                c['counterpressures'] += bool(e.get('counterpress'))
            if kind == 'Ball Recovery': c['recoveries'] += 1
            if kind in ('Dispossessed', 'Miscontrol'): c['losses'] += 1
            if defensive_action(e):
                if loc and finite(loc[0]): c['ppda_def_actions'] += loc[0] >= 48
                else: c['missing_ppda_location'] += 1
        for c in buckets(opponent, before[i]):
            c['opponent_actions'] += kind in ONBALL
            if kind == 'Pass':
                c['opponent_passes'] += 1
                if loc and finite(loc[0]): c['ppda_passes'] += loc[0] < 72
                else: c['missing_ppda_location'] += 1
            if kind == 'Shot':
                xg = (e.get('shot') or {}).get('statsbomb_xg')
                if finite(xg) and 0 <= xg <= 1: c['xga'] += xg
                else: c['missing_xga'] += 1
        card = (e.get('foul_committed') or e.get('bad_behaviour') or {}).get('card', {}).get('name')
        if card in ('Red Card', 'Second Yellow'):
            reds[tid] += 1
            for c in buckets(tid, before[i]): c['red_cards'] += 1
            for c in buckets(opponent, before[i]): c['opponent_red_cards'] += 1
        owner = (e.get('possession_team') or {}).get('id')
        if owner in result and e.get('possession') is not None and kind in ONBALL and owner == tid:
            pid = (e.get('period'), e['possession'])
            for dim, key in [('score_state', state_for(before[i], tid) if score_valid else 'unknown'), ('venue', venue_for(tid, metadata))]:
                visited = possessions_seen[(tid, dim, key)]
                if pid not in visited:
                    result[tid][dim][key]['possessions'] += 1
                    visited.add(pid)
        if i + 1 < len(events) and e.get('period') == events[i + 1].get('period'):
            start, end = period_seconds(e), period_seconds(events[i + 1])
            for team in ids:
                for c in buckets(team, after[i]):
                    if start is None or end is None or end < start: c['clock_incomplete'] = 1
                    else:
                        c['seconds'] += end - start
                        if sum(reds.values()): c['seconds_with_red_card'] += end - start
    # Restrict exposure-based rates when a period boundary is missing.
    for period in {e.get('period') for e in events}:
        group = [e for e in events if e.get('period') == period]
        types = {e.get('type', {}).get('name') for e in group}
        if not {'Half Start', 'Half End'} <= types:
            warnings.append(f'periodo_{period}_sin_limites_completos')
            for team in result.values():
                for dimension in team.values():
                    for c in dimension.values(): c['clock_incomplete'] = 1
    groups = collections.OrderedDict()
    for i, e in enumerate(events):
        if e.get('possession') is not None: groups.setdefault((e.get('period'), e['possession']), []).append((i, e))
    previous = None
    for group in groups.values():
        _first_index, first = group[0]
        tid = (first.get('possession_team') or {}).get('id')
        acts = [(i, e) for i, e in group if e.get('team', {}).get('id') == tid and e.get('type', {}).get('name') in ONBALL and e.get('location')]
        if not acts or tid not in result: continue
        for c in buckets(tid, before[acts[0][0]]): c['possession_starts'] += 1
        regain = previous is not None and previous[0] == first.get('period') and previous[1] != tid and first.get('play_pattern', {}).get('name') in ('Regular Play', 'From Counter')
        previous = (first.get('period'), tid)
        start = period_seconds(first)
        shots = [(i, e) for i, e in acts if e.get('type', {}).get('name') == 'Shot' and e.get('shot', {}).get('type', {}).get('name') != 'Penalty']
        for i, e in shots:
            end = period_seconds(e)
            if regain and start is not None and end is not None and 0 <= end - start <= fw.TRANSITION_PHASE_S:
                for c in buckets(tid, before[i]): c['transition_shots'] += 1
        # Pace is assigned to the first shot's state and requires a within-state possession.
        if shots and not (is_sp and is_sp([e for _, e in group])):
            i, shot = shots[0]
            j, action = acts[0]
            start, end = period_seconds(action), period_seconds(shot)
            if start is not None and end is not None and end >= start and state_for(before[j], tid) == state_for(before[i], tid):
                pace = max(shot['location'][0] - action['location'][0], 0) / max(end - start, fw.PACE_FLOOR_S)
                for c in buckets(tid, before[i]): c['pace_sum'] += pace; c['pace_n'] += 1
    for team in result.values():
        for dim in team.values():
            for c in dim.values(): c['matches'] = int(c['events'] > 0 or c['seconds'] > 0 or c['opponent_actions'] > 0)
    return result, {'available': True, 'score_valid': score_valid, 'final_score': {str(k): v for k, v in final.items()}, 'warnings': warnings}


def summarize_bucket(c):
    matches, seconds, possessions = c.get('matches', 0), c.get('seconds', 0), c.get('possessions', 0)
    observed = matches > 0
    out = {key: round(c.get(key, 0), 4) if observed else None for key in COUNTS}
    # Exposure is always explicit, even for unobserved contexts.
    out.update(matches=matches, seconds=round(seconds, 2), minutes=round(seconds / 60, 2), possessions=possessions,
               sufficient_sample=matches >= 5 and seconds >= 5400 and possessions >= 30)
    if c.get('missing_xg'): out['xg'] = None
    if c.get('missing_xga'): out['xga'] = None
    out['forward_pass_rate'] = ratio(c.get('forward_passes'), c.get('passes')) if not c.get('missing_pass_geometry') else None
    out['directness'] = ratio(c.get('forward_distance'), c.get('pass_distance')) if not c.get('missing_pass_geometry') else None
    out['ppda'] = ratio(c.get('ppda_passes'), c.get('ppda_def_actions')) if not c.get('missing_ppda_location') else None
    out['possession_proxy'] = ratio(c.get('passes', 0), c.get('passes', 0) + c.get('opponent_passes', 0))
    out['action_share'] = ratio(c.get('actions', 0), c.get('actions', 0) + c.get('opponent_actions', 0))
    out['pace'] = ratio(c.get('pace_sum'), c.get('pace_n'))
    for key in ('passes', 'shots', 'xg', 'xga', 'pressures', 'recoveries', 'losses', 'transition_shots'):
        rate = ratio(out.get(key), seconds / 5400) if not c.get('clock_incomplete') else None
        out[key + '_per90'] = round(rate, 4) if rate is not None else None
        rate = ratio(out.get(key), possessions / 100)
        out[key + '_per100_possessions'] = round(rate, 4) if rate is not None else None
    out['warnings'] = ([] if out['sufficient_sample'] else ['muestra_insuficiente']) + (['reloj_incompleto'] if c.get('clock_incomplete') else [])
    return out


def context_summary(context):
    return {dim: {key: summarize_bucket(c) for key, c in buckets.items()} for dim, buckets in context.items()}


def comparisons(context):
    out = []
    for dim, left, right in [('score_state', 'winning', 'drawing'), ('score_state', 'losing', 'drawing'), ('venue', 'home', 'away')]:
        a, b = context.get(dim, {}).get(left), context.get(dim, {}).get(right)
        if not a or not b: continue
        for metric in ('possession_proxy', 'action_share', 'directness', 'pace', 'ppda', 'passes_per90', 'shots_per90', 'xg_per90', 'xga_per90', 'pressures_per90', 'recoveries_per90', 'losses_per90', 'transition_shots_per90'):
            x, y = a.get(metric), b.get(metric)
            delta = x - y if finite(x) and finite(y) else None
            out.append({'dimension': dim, 'left': left, 'right': right, 'metric': metric, 'left_value': x, 'right_value': y,
                            'absolute_difference': delta, 'relative_difference': ratio(delta, abs(y)) if finite(y) else None,
                            'sufficient_sample': a['sufficient_sample'] and b['sufficient_sample']})
    return out
