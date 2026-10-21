"""Extrae las secuencias ofensivas rivales más peligrosas desde eventos StatsBomb.

Una jugada es una posesión de StatsBomb del rival que termina en tiro. Se conservan
únicamente eventos observados de esa posesión; las posiciones no se interpolan.
La puntuación es configurable y prioriza goles:
    100 * gol + 10 * xG + min(max(x_remate - 80, 0), 40)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data' / 'cache'

ACTION_TYPES = {
    'Pass', 'Carry', 'Dribble', 'Shot', 'Ball Recovery', 'Pressure',
    'Duel', 'Interception', 'Dispossessed', 'Clearance', 'Block',
}
DEFENSIVE_TYPES = {'Pressure', 'Duel', 'Interception', 'Ball Recovery', 'Clearance', 'Block'}
ATTACK_TYPES = {'Pass', 'Carry', 'Dribble', 'Shot'}
_MATCH_PLAYS = {}
_EVENTS = {}


def _json(path):
    raw = path.read_bytes()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('cp1252')
    return json.loads(text)


def _timestamp(event):
    stamp = event.get('timestamp', '00:00:00')
    try:
        parts = stamp.split(':')
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except (ValueError, IndexError):
        return event.get('minute', 0) * 60 + event.get('second', 0)


def _location(value):
    return [round(float(value[0]), 2), round(float(value[1]), 2)] if value and len(value) >= 2 else None


def _event_row(event, opponent_id, analyzed_id):
    kind = event.get('type', {}).get('name')
    detail = event.get(kind.lower().replace(' ', '_'), {}) if kind else {}
    row = {
        'type': kind,
        'team': 'rival' if event.get('team', {}).get('id') == opponent_id else 'analizado',
        'player': (event.get('player') or {}).get('name'),
        'minute': event.get('minute'),
        'second': event.get('second'),
        'location': _location(event.get('location')),
        'end_location': None,
    }
    if kind == 'Pass':
        row['end_location'] = _location(detail.get('end_location'))
        row['recipient'] = (detail.get('recipient') or {}).get('name')
        row['cross'] = bool(detail.get('cross'))
    elif kind in ('Carry', 'Dribble'):
        row['end_location'] = _location(detail.get('end_location'))
    elif kind == 'Shot':
        row['xg'] = round(float(detail.get('statsbomb_xg', 0) or 0), 4)
        row['outcome'] = (detail.get('outcome') or {}).get('name')
        row['goal'] = row['outcome'] == 'Goal'
        row['end_location'] = _location(detail.get('end_location'))
    return row


def _score(shot):
    x = (shot.get('location') or [0, 0])[0]
    return round(
        (100 if shot.get('goal') else 0)
        + 10 * (shot.get('xg') or 0)
        + min(max(x - 80, 0), 40),
        3,
    )


def dangerous_for_match(match, analyzed_team, limit=None):
    """Devuelve tiros rivales con su posesión y contexto defensivo observado."""
    mid = match['match_id']
    cache_key = (mid, analyzed_team)
    if cache_key in _MATCH_PLAYS:
        plays = _MATCH_PLAYS[cache_key]
        return plays[:limit] if limit else plays
    path = CACHE / f'v8_events_{mid}.json'
    if not path.exists():
        return []
    if mid not in _EVENTS:
        _EVENTS[mid] = _json(path)
    events = _EVENTS[mid]
    home = match['home_team']
    away = match['away_team']
    home_id = home['home_team_id']
    away_id = away['away_team_id']
    analyzed_id = home_id if analyzed_team == home['home_team_name'] else away_id
    opponent_id = away_id if analyzed_id == home_id else home_id
    opponent = away['away_team_name'] if analyzed_id == home_id else home['home_team_name']
    possessions = {}
    for event in events:
        pid = event.get('possession')
        if pid is not None:
            possessions.setdefault(pid, []).append(event)

    out = []
    for pid, possession in possessions.items():
        if not possession or possession[0].get('possession_team', {}).get('id') != opponent_id:
            continue
        shots = [e for e in possession if e.get('type', {}).get('name') == 'Shot' and e.get('team', {}).get('id') == opponent_id]
        if not shots:
            continue
        shot = shots[-1]
        rows = [
            _event_row(e, opponent_id, analyzed_id)
            for e in possession
            if e.get('type', {}).get('name') in ACTION_TYPES
        ]
        rows = [r for r in rows if r['team'] == 'rival' or r['type'] in DEFENSIVE_TYPES]
        if not rows:
            continue
        observed = [r for r in rows if r.get('location') and r['team'] == 'rival' and r['type'] in ATTACK_TYPES]
        first = observed[0].get('location') if observed else None
        last = shot.get('location')
        score = _score(_event_row(shot, opponent_id, analyzed_id))
        defensive = [r for r in rows if r['team'] == 'analizado']
        start_time = _timestamp(possession[0])
        end_time = _timestamp(shot)
        out.append({
            'id': f'{mid}:{pid}',
            'match_id': mid,
            'date': match['match_date'],
            'opponent': opponent,
            'venue': 'local' if analyzed_id == home_id else 'visitante',
            'score': [match.get('home_score'), match.get('away_score')],
            'minute': shot.get('minute'),
            'second': shot.get('second'),
            'period': shot.get('period'),
            'result': 'Gol' if (shot.get('shot') or {}).get('outcome', {}).get('name') == 'Goal' else 'Remate',
            'goal': (shot.get('shot') or {}).get('outcome', {}).get('name') == 'Goal',
            'xg': round(float((shot.get('shot') or {}).get('statsbomb_xg', 0) or 0), 4),
            'shot_location': _location(shot.get('location')),
            'progression': round(last[0] - first[0], 2) if first and last else None,
            'duration': round(max(0, end_time - start_time), 2),
            'actions': rows,
            'defensive_context': {
                'pressures': sum(r['type'] == 'Pressure' for r in defensive),
                'duels': sum(r['type'] == 'Duel' for r in defensive),
                'interceptions': sum(r['type'] == 'Interception' for r in defensive),
                'recoveries': sum(r['type'] == 'Ball Recovery' for r in defensive),
            },
            'observed_coordinates': True,
            'has_360': False,
            'danger_score': score,
            'limitation': 'Solo se muestran eventos registrados en la posesión; no se interpolan posiciones ni movimientos sin evento.',
        })
    out.sort(key=lambda p: (p['goal'], p['danger_score'], p['xg'], p['date'], p['minute'] or 0), reverse=True)
    _MATCH_PLAYS[cache_key] = out
    return out[:limit] if limit else out


def dangerous_for_entity(entity, match_by_id, limit=5):
    plays = []
    for item in entity.get('matches', []):
        match = match_by_id.get(item['mid'])
        if match:
            plays.extend(dangerous_for_match(match, entity['team']))
    plays.sort(key=lambda p: (p['goal'], p['danger_score'], p['xg'], p['date'], p['minute'] or 0), reverse=True)
    return plays[:limit]
