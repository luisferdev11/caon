"""Datos sintéticos para probar balón parado, contexto y uso de plantilla (A5).

``match_events``: eventos StatsBomb v8 de un partido (córners, tiro libre, saque de banda, cambios).
``an_match``: extracto ``an_<mid>`` mínimo (contrato sequences) con posesiones propias y rivales.
``f360_bloque``: tabla 360 ``bloque`` en columnas para probar las deltas de forma ante cambios.
"""
from __future__ import annotations

US, THEM = 1, 2
POSITIONS = ['Goalkeeper', 'Right Back', 'Right Center Back', 'Left Center Back', 'Left Back',
             'Center Defensive Midfield', 'Right Center Midfield', 'Left Center Midfield', 'Right Wing',
             'Left Wing', 'Center Forward']


def _ev(i, team, typ, minute, **kw):
    e = {'id': f'e{i}', 'index': i, 'period': 1 if minute < 45 else 2, 'minute': minute,
         'second': kw.pop('second', 0), 'possession': kw.pop('possession', i),
         'team': {'id': team, 'name': 'Nos' if team == US else 'Ellos'}, 'type': {'name': typ},
         'play_pattern': {'name': kw.pop('pattern', 'Regular Play')}}
    e.update(kw)
    return e


def _lineup(i, team, base, formation=433):
    xi = [{'player': {'id': base + k, 'name': f'J{base + k}'}, 'position': {'name': pos}}
          for k, pos in enumerate(POSITIONS)]
    return _ev(i, team, 'Starting XI', 0, tactics={'formation': formation, 'lineup': xi})


def _shot(i, team, minute, xg, outcome='Off T', loc=(105, 40), pattern='Regular Play', player=111,
          kind='Open Play', possession=None, body='Right Foot'):
    return _ev(i, team, 'Shot', minute, pattern=pattern, location=list(loc), possession=possession or i,
               player={'id': player, 'name': f'J{player}'},
               shot={'statsbomb_xg': xg, 'outcome': {'name': outcome}, 'type': {'name': kind},
                     'body_part': {'name': body}})


def match_events(goal_minute=30, sub_minute=60, rival_sub=None, penalty=False):
    """Un partido: córner propio con remate (xG .3, gol), tiro libre peligroso rival, un cambio propio.

    El remate de cabeza del córner pertenece a la posesión 3 (misma jugada). Tras el cambio hay un tiro
    propio (xG .2) y ninguno antes, así que la asociación descriptiva de xG a favor es positiva.
    """
    evs = [
        _lineup(1, US, 100), _lineup(2, THEM, 200, formation=4231),
        _ev(3, US, 'Pass', goal_minute - 1, pattern='From Corner', location=[120, 0.1], possession=3,
            player={'id': 109, 'name': 'J109'}, position={'name': 'Left Wing'},
            **{'pass': {'type': {'name': 'Corner'}, 'end_location': [114, 36], 'length': 37,
                        'technique': {'name': 'Inswinging'}, 'body_part': {'name': 'Right Foot'},
                        'recipient': {'id': 102, 'name': 'J102'}}}),
        _ev(31, THEM, 'Duel', goal_minute - 1, pattern='From Corner', location=[6, 44], possession=3,
            player={'id': 202, 'name': 'J202'}, duel={'type': {'name': 'Aerial Lost'}}),
        _shot(4, US, goal_minute, 0.3, 'Goal', (114, 36), 'From Corner', 102, possession=3, body='Head'),
        _shot(5, THEM, 40, 0.06, 'Saved', (95, 40), 'From Free Kick', 210, kind='Free Kick'),
        _ev(6, US, 'Pass', 50, pattern='From Throw In', location=[95, 79], possession=6,
            player={'id': 104, 'name': 'J104'},
            **{'pass': {'type': {'name': 'Throw-in'}, 'end_location': [100, 70], 'length': 11}}),
        _ev(7, US, 'Pass', 55, pattern='From Corner', location=[120, 79.9], possession=7,
            player={'id': 109, 'name': 'J109'},
            **{'pass': {'type': {'name': 'Corner'}, 'end_location': [112, 75], 'length': 9,
                        'technique': None, 'recipient': {'id': 108, 'name': 'J108'}}}),
        _ev(71, US, 'Ball Receipt*', 55, pattern='From Corner', location=[112, 75], possession=7,
            player={'id': 108, 'name': 'J108'}),
        _ev(72, THEM, 'Pass', 58, pattern='From Corner', location=[120, 0.1], possession=72,
            player={'id': 209, 'name': 'J209'},
            **{'pass': {'type': {'name': 'Corner'}, 'end_location': [116, 42], 'length': 42,
                        'technique': {'name': 'Outswinging'}, 'recipient': {'id': 203, 'name': 'J203'}}}),
        _ev(73, US, 'Clearance', 58, pattern='From Corner', location=[4, 38], possession=72,
            player={'id': 103, 'name': 'J103'}),
        _ev(8, US, 'Substitution', sub_minute, player={'id': 110, 'name': 'J110'}, position={'name': 'Center Forward'},
            substitution={'replacement': {'id': 111, 'name': 'J111'}, 'outcome': {'name': 'Tactical'}}),
        _shot(9, US, sub_minute + 5, 0.2, 'Off T', (105, 40), player=111),
        _ev(10, THEM, 'Pass', 90, location=[50, 40], player={'id': 205, 'name': 'J205'},
            **{'pass': {'end_location': [60, 40], 'length': 10}}),
    ]
    if rival_sub is not None:
        evs.append(_ev(11, THEM, 'Substitution', rival_sub, player={'id': 210, 'name': 'J210'},
                       substitution={'replacement': {'id': 211, 'name': 'J211'}, 'outcome': {'name': 'Tactical'}}))
    if penalty:   # penal propio con patrón de balón parado: nunca cuenta como xG de balón parado
        evs.append(_shot(13, US, 80, 0.76, 'Goal', (108, 40), 'From Free Kick', 110, kind='Penalty'))
    evs.append(_ev(12, US, 'Pass', 61, location=[30, 40], player={'id': 111, 'name': 'J111'},
                   position={'name': 'Center Forward'}, **{'pass': {'end_location': [40, 40], 'length': 10}}))
    return sorted(evs, key=lambda e: (e['minute'], e['index']))


def _poss(pid, team, period, t0, t1, state, mbin, shots=(), passes=3, f3=1, prog=0, sp=None):
    return {'id': pid, 'team': team, 'period': period, 't0': float(t0), 't1': float(t1), 'minute_bin': mbin,
            'score_state': state, 'origin': {'type': sp['type'] if sp else 'regain_open', 'loc': [50, 40]},
            'shots': [{'xg': x, 'goal': g, 'penalty': p, 'x': 110, 'y': 40, 't': float(t0)} for x, g, p in shots],
            'xg': sum(x for x, _, _ in shots), 'n_passes': passes, 'n_final_third': f3, 'n_prog': prog, 'sp': sp}


def an_match(mid, xf=1.0, xa=0.5, us_first=True, sp_for=0.2, sp_against=0.1, pen=0.0, tilt=(6, 4)):
    """Extracto ``an_`` con 6 posesiones: 2 en empate, luego gol (propio si ``us_first``), 2 tras el gol.

    Reparte xG en juego abierto ``xf``/``xa`` en 2 tiros cada uno; un balón parado de peligro por lado (córner
    propio con ``sp_for``, tiro libre rival con ``sp_against``) y opcionalmente un penal propio ``pen``.
    """
    lead, trail = ('ganando', 'perdiendo') if us_first else ('perdiendo', 'ganando')
    goal = (xf / 2, True, False) if us_first else (xf / 2, False, False)
    opp_goal = (xa / 2, not us_first, False)
    ps = [
        _poss(1, US, 1, 0, 300, 'empatando', '0-15', [goal], passes=10, f3=tilt[0] // 2, prog=2),
        _poss(2, THEM, 1, 300, 600, 'empatando', '0-15', [opp_goal], passes=5, f3=tilt[1] // 2),
        _poss(3, US, 1, 600, 900, lead, '0-15', [(xf / 2, False, False)], passes=10, f3=tilt[0] - tilt[0] // 2,
              prog=1),
        _poss(4, THEM, 2, 2700, 3000, trail, '46-60', [(xa / 2, False, False)], passes=5,
              f3=tilt[1] - tilt[1] // 2),
        _poss(5, US, 2, 3000, 3300, lead, '46-60', [(sp_for, False, False)] + ([(pen, False, True)] if pen else []),
              passes=2, f3=0, sp={'type': 'corner', 'danger': True}),
        _poss(6, THEM, 2, 3300, 3600, trail, '46-60', [(sp_against, False, False)], passes=1, f3=0,
              sp={'type': 'fk', 'danger': True}),
    ]
    return {'version': 1, 'match_id': mid, 'home': US, 'away': THEM, 'possessions': ps, 'events_light': {}}


def f360_bloque(rows):
    """Tabla 360 ``bloque`` en columnas: rows = [(team, period, t, last_line, length, width, hull, valid)]."""
    cols = ['team', 'eid', 'period', 't', 'bx', 'by', 'zone', 'n_vis', 'last_line', 'length', 'width',
            'hull_area', 'between', 'valid']
    return {'tables': {'bloque': {'cols': cols, 'rows': [
        [tm, f'b{i}', per, t, 60, 40, 9, 9, ll, ln, wd, hl, 5, ok]
        for i, (tm, per, t, ll, ln, wd, hl, ok) in enumerate(rows)]}}}


def f360_corner(rows):
    """Tabla 360 ``corner_def`` en columnas: rows = [(team, def_box, def_six, pairing, marking, valid)]."""
    cols = ['team', 'eid', 'period', 't', 'def_box', 'def_six', 'att_box', 'near_post', 'far_post', 'pairing',
            'unpaired_six', 'marking', 'valid']
    return {'tables': {'corner_def': {'cols': cols, 'rows': [
        [tm, f'c{i}', 1, 100.0 + i, db, ds, 6, 1, 1, pr, 1, mk, ok]
        for i, (tm, db, ds, pr, mk, ok) in enumerate(rows)]}}}
