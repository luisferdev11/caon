"""Observed player participation, positions and substitutions.

This module deliberately keeps registered positions separate from tactical
interpretations.  All intervals are derived from lineup position intervals and
event timestamps; missing fields remain missing and are reported as warnings.
"""
import collections
import json
import math
import pathlib


MIN_SAMPLE_MINUTES = 15


def read_json(path):
    raw = pathlib.Path(path).read_bytes()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('cp1252')
    return json.loads(text)


def clock_seconds(value):
    if not value:
        return None
    parts = str(value).split(':')
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except (TypeError, ValueError):
        return None


def event_seconds(event):
    minute = event.get('minute')
    second = event.get('second')
    if not isinstance(minute, (int, float)) or not isinstance(second, (int, float)):
        return None
    fraction = 0.0
    timestamp = event.get('timestamp') or ''
    if '.' in timestamp:
        try:
            fraction = float('0.' + timestamp.rsplit('.', 1)[1])
        except ValueError:
            pass
    return minute * 60 + second + fraction


def _finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def _name(player):
    return player.get('player_nickname') or player.get('player_name')


def _position_at(segments, moment):
    for segment in segments:
        start = segment['from_seconds']
        end = segment['to_seconds']
        if start <= moment and (end is None or moment < end):
            return segment.get('position')
    return None


def _state_before(events, moment, team_id):
    scores = collections.defaultdict(int)
    for event in events:
        timestamp = event_seconds(event)
        if timestamp is not None and timestamp >= moment:
            break
        kind = (event.get('type') or {}).get('name')
        scoring_team = event.get('team', {}).get('id')
        if kind == 'Shot' and (event.get('shot') or {}).get('outcome', {}).get('name') == 'Goal':
            scores[scoring_team] += 1
        elif kind == 'Own Goal For':
            scores[scoring_team] += 1
    own = scores.get(team_id, 0)
    opponent = max((score for key, score in scores.items() if key != team_id), default=0)
    return 'winning' if own > opponent else ('losing' if own < opponent else 'drawing')


def _states_at(events, moments, team_id):
    scores = collections.defaultdict(int)
    states = {}
    event_index = 0
    for moment in sorted(moments):
        while event_index < len(events):
            event = events[event_index]
            timestamp = event_seconds(event)
            if timestamp is None or timestamp >= moment:
                break
            kind = (event.get('type') or {}).get('name')
            scoring_team = event.get('team', {}).get('id')
            if kind == 'Shot' and (event.get('shot') or {}).get('outcome', {}).get('name') == 'Goal':
                scores[scoring_team] += 1
            elif kind == 'Own Goal For':
                scores[scoring_team] += 1
            event_index += 1
        own = scores.get(team_id, 0)
        opponent = max((score for key, score in scores.items() if key != team_id), default=0)
        states[moment] = 'winning' if own > opponent else ('losing' if own < opponent else 'drawing')
    return states


def _match_end(events):
    times = [event_seconds(event) for event in events]
    valid = [value for value in times if _finite(value)]
    return max(valid) if valid else None


def _registered_segments(player, match_end, warnings):
    segments = []
    positions = player.get('positions') or []
    if not positions:
        return segments
    for position in positions:
        start = clock_seconds(position.get('from'))
        end = clock_seconds(position.get('to'))
        if start is None:
            warnings.append('jugador sin minuto de entrada: %s' % (_name(player) or player.get('player_id')))
            continue
        if end is None and match_end is not None:
            end = match_end
        if end is not None and end < start:
            warnings.append('intervalo invertido para %s' % (_name(player) or player.get('player_id')))
            continue
        if not position.get('position'):
            warnings.append('posición ausente para %s' % (_name(player) or player.get('player_id')))
        segments.append({
            'position': position.get('position'),
            'position_id': position.get('position_id'),
            'from_seconds': start,
            'to_seconds': end,
            'from_minute': round(start / 60, 3),
            'to_minute': round(end / 60, 3) if end is not None else None,
            'start_reason': position.get('start_reason'),
            'end_reason': position.get('end_reason'),
            'counterpart_id': position.get('counterpart_id'),
            'counterpart_name': position.get('counterpart_name'),
        })
    return segments


def _event_metrics(events, team_id, start, end):
    selected = []
    for event in events:
        timestamp = event_seconds(event)
        if timestamp is not None and start <= timestamp < end:
            selected.append(event)
    passes = opponent_passes = pressures = defensive = shots = 0
    xg = 0.0
    forward_distance = 0.0
    pass_distance = 0.0
    for event in selected:
        kind = (event.get('type') or {}).get('name')
        event_team = (event.get('team') or {}).get('id')
        if kind == 'Pass':
            if event_team == team_id:
                passes += 1
            else:
                opponent_passes += 1
            location = event.get('location')
            end_location = (event.get('pass') or {}).get('end_location')
            if event_team == team_id and location and end_location:
                distance = math.hypot(end_location[0] - location[0], end_location[1] - location[1])
                pass_distance += distance
                forward_distance += max(end_location[0] - location[0], 0)
        if event_team == team_id and kind == 'Pressure':
            pressures += 1
        if event_team == team_id and kind in {'Pressure', 'Duel', 'Interception', 'Ball Recovery', 'Foul Committed'}:
            defensive += 1
        if event_team == team_id and kind == 'Shot':
            shots += 1
            value = (event.get('shot') or {}).get('statsbomb_xg')
            if _finite(value):
                xg += value
    return {
        'minutes': round((end - start) / 60, 3),
        'events': len(selected),
        'passes': passes,
        'opponent_passes': opponent_passes,
        'pressures': pressures,
        'shots': shots,
        'xg': round(xg, 4),
        'directness': round(forward_distance / pass_distance, 4) if pass_distance else None,
        'ppda_all_zone': round(opponent_passes / defensive, 4) if defensive else None,
        'sufficient_sample': (end - start) / 60 >= MIN_SAMPLE_MINUTES,
    }


def _lineup_intervals(lineup, events, team_id, match_end, warnings):
    players = {}
    for player in lineup:
        player_id = player.get('player_id')
        if player_id is None:
            warnings.append('jugador sin player_id: %s' % (_name(player) or '<sin nombre>'))
            continue
        segments = _registered_segments(player, match_end, warnings)
        players[player_id] = {
            'player_id': player_id,
            'name': _name(player),
            'team': player.get('team_name'),
            'jersey_number': player.get('jersey_number'),
            'starter': any(segment.get('start_reason') == 'Starting XI' for segment in segments),
            'segments': segments,
        }
    return players


def _substitutions(events, players, team_id, venue, score):
    result = []
    warnings = []
    for event in sorted(events, key=lambda item: item.get('index', 0)):
        if (event.get('type') or {}).get('name') != 'Substitution':
            continue
        if (event.get('team') or {}).get('id') != team_id:
            continue
        replacement = (event.get('substitution') or {}).get('replacement') or {}
        player_out = event.get('player') or {}
        if not player_out.get('id') or not replacement.get('id'):
            warnings.append('sustitución sin jugador de entrada o salida')
            continue
        moment = event_seconds(event)
        if moment is None:
            warnings.append('sustitución sin minuto verificable')
            continue
        position_out = (event.get('position') or {}).get('name')
        position_in = _position_at((players.get(replacement['id']) or {}).get('segments', []), moment)
        result.append({
            'minute': round(moment / 60, 3),
            'match_second': round(moment, 3),
            'player_out': {'player_id': player_out.get('id'), 'name': player_out.get('name')},
            'player_in': {'player_id': replacement.get('id'), 'name': replacement.get('name')},
            'score_state': _state_before(events, moment, team_id),
            'venue': venue,
            'team': team_id,
            'position_out': position_out,
            'position_in': position_in,
            'reason': ((event.get('substitution') or {}).get('outcome') or {}).get('name'),
        })
    return result, warnings


def _composition_intervals(events, players, team_id, venue, match_end):
    boundaries = {0.0}
    for player in players.values():
        for segment in player['segments']:
            boundaries.add(segment['from_seconds'])
            if segment['to_seconds'] is not None:
                boundaries.add(segment['to_seconds'])
    for event in events:
        timestamp = event_seconds(event)
        if timestamp is not None and (event.get('type') or {}).get('name') in {'Shot', 'Own Goal For'}:
            boundaries.add(timestamp)
    if match_end is not None:
        boundaries.add(match_end)
    ordered = sorted(boundaries)
    state_by_moment = _states_at(events, ordered, team_id)
    intervals = []
    for start, end in zip(ordered, ordered[1:]):
        if end <= start:
            continue
        active = tuple(sorted(
            player_id for player_id, player in players.items()
            if any(segment['from_seconds'] <= start and
                   (segment['to_seconds'] is None or start < segment['to_seconds'])
                   for segment in player['segments'])
        ))
        if not active:
            continue
        state = state_by_moment[start]
        if intervals and intervals[-1]['players'] == list(active) and intervals[-1]['score_state'] == state:
            intervals[-1]['end_minute'] = round(end / 60, 3)
            intervals[-1]['end_second'] = round(end, 3)
        else:
            intervals.append({
                'start_minute': round(start / 60, 3),
                'end_minute': round(end / 60, 3),
                'start_second': round(start, 3),
                'end_second': round(end, 3),
                'players': list(active),
                'score_state': state,
                'venue': venue,
                'metrics': None,
            })
    for interval in intervals:
        interval['metrics'] = _event_metrics(
            events, team_id, interval['start_second'], interval['end_second'])
    return intervals


def build_match_personnel(match_id, lineup_data, events, team_name, venue=None,
                           opponent=None, score=None, date=None, source='mx'):
    warnings = []
    events = sorted(events, key=lambda item: item.get('index', 0))
    team_data = next((item for item in lineup_data if item.get('team_name') == team_name), None)
    if team_data is None:
        return None, ['equipo sin lineup: %s' % team_name]
    team_id = team_data.get('team_id')
    match_end = _match_end(events)
    players = _lineup_intervals(team_data.get('lineup') or [], events, team_id, match_end, warnings)
    if len(players) < 11:
        warnings.append('lineup incompleto: %d jugadores identificables' % len(players))
    active_start = [player_id for player_id, player in players.items()
                    if any(segment['from_seconds'] <= 0 and
                           (segment['to_seconds'] is None or segment['to_seconds'] > 0)
                           for segment in player['segments'])]
    if len(active_start) != 11:
        warnings.append('alineación inicial observada con %d jugadores' % len(active_start))
    substitutions, substitution_warnings = _substitutions(
        events, players, team_id, venue, score)
    warnings.extend(substitution_warnings)
    disciplinary_events = []
    for event in events:
        if (event.get('type') or {}).get('name') != 'Bad Behaviour':
            continue
        if (event.get('team') or {}).get('id') != team_id:
            continue
        card = ((event.get('bad_behaviour') or {}).get('card') or {}).get('name')
        if card not in {'Red Card', 'Second Yellow'}:
            continue
        moment = event_seconds(event)
        disciplinary_events.append({
            'minute': round(moment / 60, 3) if moment is not None else None,
            'type': card,
            'player_id': (event.get('player') or {}).get('id'),
            'player_name': (event.get('player') or {}).get('name'),
        })
    player_rows = []
    positions = set()
    for player in players.values():
        total_seconds = sum(
            max(segment['to_seconds'] - segment['from_seconds'], 0)
            for segment in player['segments']
            if segment['to_seconds'] is not None
        )
        for segment in player['segments']:
            if segment.get('position'):
                positions.add(segment['position'])
        player_rows.append({
            'player_id': player['player_id'],
            'name': player['name'],
            'team': team_name,
            'starter': player['starter'],
            'start_minute': min((segment['from_minute'] for segment in player['segments']), default=None),
            'end_minute': max((segment['to_minute'] for segment in player['segments']
                               if segment['to_minute'] is not None), default=None),
            'minutes_played': round(total_seconds / 60, 3),
            'positions': [segment['position'] for segment in player['segments'] if segment.get('position')],
            'position_intervals': player['segments'],
            'substitution_information': [
                {'start_reason': segment.get('start_reason'), 'end_reason': segment.get('end_reason'),
                 'counterpart_id': segment.get('counterpart_id'),
                 'counterpart_name': segment.get('counterpart_name')}
                for segment in player['segments']
                if segment.get('start_reason') != 'Starting XI' or segment.get('end_reason') != 'Final Whistle'
            ],
        })
    player_rows.sort(key=lambda row: (not row['starter'], row['start_minute'] or 0, row['name'] or ''))
    intervals = _composition_intervals(events, players, team_id, venue, match_end)
    for interval in intervals:
        interval['players'] = [
            {'player_id': player_id, 'name': players[player_id]['name'],
             'position': _position_at(players[player_id]['segments'], interval['start_second'])}
            for player_id in interval['players']
        ]
    return {
        'match_id': match_id,
        'date': date,
        'team': team_name,
        'opponent': opponent,
        'venue': venue,
        'score': score,
        'source': source,
        'match_minutes_observed': round(match_end / 60, 3) if match_end is not None else None,
        'players': player_rows,
        'starting_lineup': [row['player_id'] for row in player_rows if row['starter']],
        'intervals': intervals,
        'substitutions': substitutions,
        'disciplinary_events': disciplinary_events,
        'warnings': sorted(set(warnings)),
        'coverage': {
            'players_identified': len(player_rows),
            'positions_observed': len(positions),
            'substitutions': len(substitutions),
            'has_lineup': True,
        },
    }, warnings


def _pairs(lineups):
    appearances = collections.Counter()
    shared_minutes = collections.Counter()
    for match in lineups:
        starters = tuple(sorted(match['starting_lineup']))
        for index, player_id in enumerate(starters):
            for other in starters[index + 1:]:
                appearances[(player_id, other)] += 1
        for interval in match['intervals']:
            ids = sorted(player['player_id'] for player in interval['players'])
            minutes = interval['metrics']['minutes']
            for index, player_id in enumerate(ids):
                for other in ids[index + 1:]:
                    shared_minutes[(player_id, other)] += minutes
    return appearances, shared_minutes


def build_personnel(matches, loader, team_name, source='mx', match_cache=None):
    """Build one entity's personnel summary from real cached responses."""
    match_rows = []
    unavailable = []
    source_counts = collections.Counter()
    for item in matches:
        try:
            lineup = loader('lineup', item['mid'])
            events = loader('events', item['mid'])
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            unavailable.append({'match_id': item['mid'], 'reason': str(exc)})
            continue
        cache_key = (source, item['mid'], team_name)
        if match_cache is not None and cache_key in match_cache:
            row = match_cache[cache_key]
            warnings = row['warnings']
        else:
            row, warnings = build_match_personnel(
                item['mid'], lineup, events, team_name,
                venue=item.get('side'), opponent=item.get('opponent'),
                score=item.get('score'), date=item.get('date'), source=source)
            if match_cache is not None and row is not None:
                match_cache[cache_key] = row
        if row is None:
            unavailable.append({'match_id': item['mid'], 'reason': warnings[0]})
            continue
        match_rows.append(row)
        source_counts['matches_with_lineup'] += 1
        source_counts['matches_with_substitutions'] += bool(row['substitutions'])
    player_stats = {}
    for match in match_rows:
        for player in match['players']:
            aggregate = player_stats.setdefault(player['player_id'], {
                'player_id': player['player_id'], 'name': player['name'], 'team': team_name,
                'matches': 0, 'starts': 0, 'minutes': 0.0, 'positions': collections.Counter(),
            })
            aggregate['matches'] += player['minutes_played'] > 0
            aggregate['starts'] += player['starter']
            aggregate['minutes'] += player['minutes_played']
            aggregate['positions'].update(position for position in player['positions'] if position)
    players = []
    for aggregate in player_stats.values():
        players.append(dict(
            player_id=aggregate['player_id'], name=aggregate['name'], team=aggregate['team'],
            matches=aggregate['matches'], starts=aggregate['starts'],
            minutes=round(aggregate['minutes'], 3),
            positions=[{'name': name, 'appearances': count}
                       for name, count in aggregate['positions'].most_common()],
        ))
    players.sort(key=lambda player: (-player['minutes'], -player['starts'], player['name'] or ''))
    lineup_counts = collections.Counter(tuple(sorted(row['starting_lineup'])) for row in match_rows)
    appearances, shared_minutes = _pairs(match_rows)
    player_names = {player['player_id']: player['name'] for row in match_rows for player in row['players']}
    starting_lineups = [{
        'players': [{'player_id': player_id, 'name': player_names.get(player_id)}
                    for player_id in lineup],
        'matches': count,
    } for lineup, count in lineup_counts.most_common(10)]
    combinations = [{
        'players': [{'player_id': pair[0], 'name': player_names.get(pair[0])},
                    {'player_id': pair[1], 'name': player_names.get(pair[1])}],
        'starting_appearances': appearances[pair],
        'shared_minutes': round(minutes, 3),
    } for pair, minutes in shared_minutes.most_common(20)]
    warnings = [warning for row in match_rows for warning in row['warnings']]
    identified = sum(len(row['players']) for row in match_rows)
    positioned = sum(row['coverage']['positions_observed'] > 0 for row in match_rows)
    return {
        'coverage': {
            'source': source,
            'input_matches': len(matches),
            'matches_with_lineup': len(match_rows),
            'matches_without_lineup': len(unavailable),
            'matches_with_substitutions': source_counts['matches_with_substitutions'],
            'players_identifiable': len(players),
            'player_appearances_identifiable': identified,
            'matches_with_positions': positioned,
            'unavailable_matches': unavailable,
            'warnings': collections.Counter(warnings).most_common(20),
        },
        'players': players,
        'starting_lineups': starting_lineups,
        'combinations': combinations,
        'substitutions': [substitution | {'match_id': row['match_id'], 'date': row['date'],
                                          'opponent': row['opponent']}
                         for row in match_rows for substitution in row['substitutions']],
        'matches': match_rows,
        'sample_note': 'Los resultados son descriptivos y no establecen causalidad.',
    }
