"""Equipos-entrenador que expone la demo. Cada entidad = (equipo, entrenador, ventana de fechas)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from statsbomb import *

# (id, etiqueta, equipo StatsBomb, substring del entrenador, desde, hasta, grupo)
SPECIAL = [
    ('ame_jardine', 'América · Jardine (Tricampeonato)', 'América', 'Jardine', '2023-07-01', '2024-12-31', 'Histórico'),
    ('ame_almada',  'América · Almada',                  'América', 'Almada',  '2026-07-01', '2099-01-01', 'Actual'),
    ('gdl_paunovic','Chivas · Paunović',                 'Guadalajara', 'Paunovic', '2023-01-01', '2023-12-31', 'Histórico'),
    ('gdl_gago',    'Chivas · Gago',                     'Guadalajara', 'Gago', '2024-01-01', '2024-12-31', 'Histórico'),
    ('gdl_milito',  'Chivas · Milito',                   'Guadalajara', 'Milito', '2025-07-01', '2099-01-01', 'Actual'),
    ('atl_cocca',   'Atlas · Cocca (Bicampeonato)',      'Atlas', 'Cocca', '2021-07-01', '2022-06-30', 'Histórico'),
]
EXCLUDE_CURRENT = {'América', 'Guadalajara'}   # ya cubiertos arriba

def all_matches():
    out = []
    for sid in SEASONS_ALL:
        for m in matches(sid):
            if m['match_status'] != 'available': continue
            out.append(m)
    return out

def team_coach(m, side):
    t = m[side + '_team']
    return t[side + '_team_name'], ', '.join(x['name'] for x in (t.get('managers') or []))

def build_entities():
    ms = all_matches()
    ents = []
    for eid, label, team, coach, d0, d1, grp in SPECIAL:
        ents.append(dict(id=eid, label=label, team=team, coach_key=coach, d0=d0, d1=d1, group=grp))
    # entrenador actual de cada equipo que juega 2026/27
    cur = {}
    for m in matches(351):
        if m['match_status'] != 'available': continue
        for side in ['home', 'away']:
            team, coach = team_coach(m, side)
            if coach and (team not in cur or m['match_date'] > cur[team][1]): cur[team] = (coach, m['match_date'])
    for team, (coach, _) in sorted(cur.items()):
        if team in EXCLUDE_CURRENT: continue
        # tramo continuo del entrenador actual con ese equipo (hacia atrás hasta otro DT)
        hist = sorted((m['match_date'], team_coach(m, s)[1]) for m in ms for s in ['home', 'away'] if team_coach(m, s)[0] == team and team_coach(m, s)[1])
        d0 = hist[-1][0]
        for d, c in reversed(hist):
            if c != coach: break
            d0 = d
        short = coach.split(',')[0]
        ents.append(dict(id=team.lower()[:6].replace(' ', '') + '_' + short.split()[-1].lower(), label=f'{team} · {short}',
                         team=team, coach_key=coach, d0=d0, d1='2099-01-01', group='Actual'))
    for e in ents:
        e['matches'] = []
        for m in ms:
            for side in ['home', 'away']:
                team, coach = team_coach(m, side)
                if team == e['team'] and e['coach_key'] in coach and e['d0'] <= m['match_date'] <= e['d1']:
                    e['matches'].append(dict(mid=m['match_id'], side=side, date=m['match_date']))
    return ents, ms

if __name__ == '__main__':
    ents, ms = build_entities()
    for e in ents: print(f"{e['id']:22s} {e['label']:45s} {e['d0']}  n={len(e['matches'])}")
    print('distinct matches', len({x['mid'] for e in ents for x in e['matches']}), 'league matches', len(ms))
