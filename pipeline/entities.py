"""Equipos-entrenador que expone la demo. Cada entidad = (equipo, entrenador, ventana de fechas).

Las funciones de cálculo son puras (reciben listas de partidos); la IO está en
all_matches()/build_entities(), que leen el calendario cacheado de StatsBomb.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from statsbomb import *
from statsbomb import SEASONS_ALL, matches

CURRENT_SEASON = 351
OPEN_END = '2099-01-01'

# (id, etiqueta, equipo StatsBomb, substring del entrenador, desde, hasta, grupo)
# ame_jardine DEBE ser la primera (test_api espera entities[0].team == 'América').
SPECIAL = [
    ('ame_jardine',     'América · Jardine (Tricampeonato)',    'América', 'Jardine', '2023-07-01', '2025-06-30', 'Histórico'),
    ('ame_jardine_epi', 'América · Jardine (Epílogo 2025/26)',  'América', 'Jardine', '2025-07-01', '2026-06-30', 'Epílogo'),
    ('ame_almada',      'América · Almada',                     'América', 'Almada',  '2026-07-01', OPEN_END, 'Actual'),
    ('pac_almada',      'Pachuca · Almada',                     'Pachuca', 'Almada',  '2021-07-01', '2025-06-30', 'Comparación'),
    ('ame_solari',      'América · Solari (antes de Jardine)',  'América', 'Solari',  '2021-07-01', '2023-06-30', 'Comparación'),
    ('ame_ortiz',       'América · Ortiz (antes de Jardine)',   'América', 'Ortiz',   '2021-07-01', '2023-06-30', 'Comparación'),
    ('slp_jardine',     'Atlético San Luis · Jardine',          'Atlético San Luis', 'Jardine', '2021-07-01', '2023-06-30', 'Comparación'),
    ('san_almada',      'Santos · Almada',                      'Santos Laguna', 'Almada', '2021-07-01', '2022-06-30', 'Comparación'),
    ('gdl_paunovic',    'Chivas · Paunović',                    'Guadalajara', 'Paunovic', '2023-01-01', '2023-12-31', 'Histórico'),
    ('gdl_gago',        'Chivas · Gago',                        'Guadalajara', 'Gago', '2024-01-01', '2024-12-31', 'Histórico'),
    ('gdl_milito',      'Chivas · Milito',                      'Guadalajara', 'Milito', '2025-07-01', OPEN_END, 'Actual'),
    ('atl_cocca',       'Atlas · Cocca (Bicampeonato)',         'Atlas', 'Cocca', '2021-07-01', '2022-06-30', 'Histórico'),
]
EXCLUDE_CURRENT = {'América', 'Guadalajara'}   # ya cubiertos arriba
SIDES = ('home', 'away')


def all_matches() -> list[dict]:
    """Partidos disponibles de todas las temporadas (IO: calendario cacheado)."""
    out = []
    for sid in SEASONS_ALL:
        out.extend(m for m in matches(sid) if m['match_status'] == 'available')
    return out


def team_coach(m: dict, side: str) -> tuple[str, str]:
    """(equipo, entrenadores separados por coma) de un lado del partido."""
    t = m[side + '_team']
    return t[side + '_team_name'], ', '.join(x['name'] for x in (t.get('managers') or []))


def special_entities() -> list[dict]:
    """Entidades curadas a mano, en el orden de SPECIAL."""
    return [{'id': eid, 'label': label, 'team': team, 'coach_key': coach, 'd0': d0, 'd1': d1, 'group': grp}
            for eid, label, team, coach, d0, d1, grp in SPECIAL]


def is_covered(team: str, coach: str, date: str, special: list[dict]) -> bool:
    """True si (equipo, DT, fecha) ya está dentro de una entidad curada."""
    return any(s['team'] == team and s['coach_key'] in coach and s['d0'] <= date <= s['d1'] for s in special)


def current_coaches(cur_matches: list[dict]) -> dict[str, tuple[str, str]]:
    """Equipo -> (DT más reciente, fecha) en la temporada actual."""
    cur: dict[str, tuple[str, str]] = {}
    for m in cur_matches:
        if m['match_status'] != 'available':
            continue
        for side in SIDES:
            team, coach = team_coach(m, side)
            if coach and (team not in cur or m['match_date'] > cur[team][1]):
                cur[team] = (coach, m['match_date'])
    return cur


def tenure_start(team: str, coach: str, ms: list[dict]) -> str:
    """Inicio del tramo continuo más reciente de `coach` en `team` ('' si no hay)."""
    hist = sorted((m['match_date'], team_coach(m, s)[1]) for m in ms for s in SIDES
                  if team_coach(m, s)[0] == team and team_coach(m, s)[1])
    if not hist:
        return ''
    d0 = hist[-1][0]
    for d, c in reversed(hist):
        if c != coach:
            break
        d0 = d
    return d0


def current_entities(ms: list[dict], cur_matches: list[dict], special: list[dict]) -> list[dict]:
    """Entidad 'Actual' por equipo de la temporada en curso, sin duplicar las curadas."""
    out = []
    for team, (coach, last) in sorted(current_coaches(cur_matches).items()):
        if team in EXCLUDE_CURRENT or is_covered(team, coach, last, special):
            continue
        d0 = tenure_start(team, coach, ms) or last
        short = coach.split(',')[0]
        out.append({'id': team.lower()[:6].replace(' ', '') + '_' + short.split()[-1].lower(),
                        'label': f'{team} · {short}', 'team': team, 'coach_key': coach, 'd0': d0, 'd1': OPEN_END, 'group': 'Actual'})
    return out


def entity_matches(e: dict, ms: list[dict]) -> list[dict]:
    """Partidos de la entidad: equipo exacto, DT por substring, fecha en [d0, d1]."""
    out = []
    for m in ms:
        for side in SIDES:
            team, coach = team_coach(m, side)
            if team == e['team'] and e['coach_key'] in coach and e['d0'] <= m['match_date'] <= e['d1']:
                out.append({'mid': m['match_id'], 'side': side, 'date': m['match_date']})
    return out


def build_entities_from(ms: list[dict], cur_matches: list[dict]) -> list[dict]:
    """Construye todas las entidades a partir de listas de partidos (función pura)."""
    special = special_entities()
    ents = special + current_entities(ms, cur_matches, special)
    for e in ents:
        e['matches'] = entity_matches(e, ms)
    return ents


def build_entities():
    """(entidades, partidos de la liga) leyendo el calendario cacheado."""
    ms = all_matches()
    return build_entities_from(ms, matches(CURRENT_SEASON)), ms


if __name__ == '__main__':
    ents, ms = build_entities()
    for e in ents:
        print(f"{e['id']:22s} {e['label']:45s} {e['d0']}  n={len(e['matches'])}")
    print('distinct matches', len({x['mid'] for e in ents for x in e['matches']}), 'league matches', len(ms))
