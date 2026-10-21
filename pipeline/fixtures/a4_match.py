"""Partido sintético StatsBomb v8 para probar las analíticas de A4 (ofensiva, defensa, transiciones, peligrosas).

``events()`` arma ~50 eventos coherentes (índice, posesión, reloj, marco propio de cada equipo) y ``an()``
los pasa por ``sequences.build_possessions`` para que el extracto ``an_`` cumpla el contrato real.
Nosotros = 1 (local), ellos = 2. Cada equipo en su propio marco de ataque (x → 120).
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

US, THEM = 1, 2
MID = 900
NAMES = {10: 'Portero Uno', 11: 'Defensa Uno', 12: 'Medio Uno', 13: 'Delantero Uno',
         20: 'Rival Portero', 21: 'Rival Uno', 22: 'Rival Dos'}
GK_IDS = {10, 20}


class _Builder:
    """Agrega eventos con índice, reloj y posesión automáticos."""

    def __init__(self) -> None:
        self.ev: list[dict[str, Any]] = []
        self.t = 0.0
        self.poss = 0
        self.poss_team = US
        self.pattern = 'Regular Play'

    def possession(self, team: int, pattern: str, t: float) -> None:
        self.poss += 1
        self.poss_team, self.pattern, self.t = team, pattern, t

    def add(self, team: int, kind: str, player: int, loc: Any = None, dt: float = 1.0, **body: Any) -> dict:
        i = len(self.ev) + 1
        minute, second = int(self.t // 60), int(self.t % 60)
        e = {'id': f'e{i}', 'index': i, 'period': 1, 'minute': minute, 'second': second,
             'timestamp': f'00:{minute:02d}:{second:02d}.000', 'possession': self.poss,
             'possession_team': {'id': self.poss_team}, 'team': {'id': team}, 'type': {'name': kind},
             'play_pattern': {'name': self.pattern}, 'player': {'id': player, 'name': NAMES[player]},
             'position': {'name': 'Goalkeeper' if player in GK_IDS else 'Center Midfield'}}
        if loc is not None:
            e['location'] = list(loc)
        e.update(body)
        self.ev.append(e)
        self.t += dt
        return e


def _pass(end: Any, ok: bool = True, xpass: Any = None, ptype: Any = None, length: float = 10.0) -> dict:
    p: dict[str, Any] = {'end_location': list(end), 'length': length}
    if not ok:
        p['outcome'] = {'name': 'Incomplete'}
    if xpass is not None:
        p['pass_success_probability'] = xpass
    if ptype:
        p['type'] = {'name': ptype}
    return {'pass': p}


def _shot(xg: float, goal: bool = False, pen: bool = False, ff: Any = None) -> dict:
    s = {'statsbomb_xg': xg, 'outcome': {'name': 'Goal' if goal else 'Off T'},
         'type': {'name': 'Penalty' if pen else 'Open Play'}, 'body_part': {'name': 'Right Foot'},
         'end_location': [120, 40]}
    if ff:
        s['freeze_frame'] = ff
    return {'shot': s}


def _ff() -> list[dict[str, Any]]:
    """Freeze frame del tiro rival con nombres (que nunca deben publicarse)."""
    return [{'location': [116, 40], 'teammate': False, 'player': {'id': 10, 'name': 'Portero Uno'},
             'position': {'name': 'Goalkeeper'}},
            {'location': [104, 30], 'teammate': True, 'player': {'id': 22, 'name': 'Rival Dos'},
             'position': {'name': 'Center Forward'}}]


def _first_half(b: _Builder) -> None:
    # 1 · nosotros, saque de meta largo; conducción progresiva; pase fácil fallado (no forzado)
    b.possession(US, 'From Goal Kick', 0)
    b.add(US, 'Pass', 10, (6, 40), **_pass((50, 30), ptype='Goal Kick', length=44.7), obv_total_net=0.01)
    b.add(US, 'Carry', 11, (50, 30), carry={'end_location': [75, 35]}, obv_total_net=0.05)
    b.add(US, 'Pass', 12, (75, 35), **_pass((70, 60), ok=False, xpass=0.85), obv_total_net=-0.03)
    # 2 · ellos roban (transición) y tiran a los 6 s → nuestra pérdida 1 es costosa (no letal)
    b.possession(THEM, 'Regular Play', 4)
    b.add(THEM, 'Interception', 21, (50, 20), interception={'outcome': {'name': 'Won'}})
    b.add(US, 'Pressure', 12, (70, 60), counterpress=True)
    b.add(THEM, 'Pass', 21, (50, 20), dt=5, **_pass((80, 30), length=31.6), obv_total_net=0.04)
    b.add(THEM, 'Shot', 22, (100, 40), **_shot(0.10), obv_total_net=0.02)
    # 3 · saque de meta corto, salida fallida, pase bajo presión perdido
    b.possession(US, 'From Goal Kick', 20)
    b.add(US, 'Pass', 10, (6, 40), **_pass((20, 20), ptype='Goal Kick', length=25.0))
    b.add(US, 'Pass', 11, (20, 20), **_pass((35, 20)))
    b.add(US, 'Pass', 11, (35, 20), under_pressure=True, **_pass((55, 10), ok=False, xpass=0.6))
    # 4 · posesión rival de 3 s; entrada nuestra (acción defensiva PPDA) → robo rápido (contrapresión)
    b.possession(THEM, 'Regular Play', 26)
    b.add(THEM, 'Pass', 21, (65, 70), dt=2, **_pass((64, 70)))
    b.add(US, 'Duel', 12, (56, 10), duel={'type': {'name': 'Tackle'}})
    # 5 · nosotros: robo en x=55, conducción, pase progresivo, entrada al área, gol en 8 s (contraataque)
    b.possession(US, 'Regular Play', 29)
    b.add(US, 'Ball Recovery', 12, (55, 10))
    b.add(US, 'Carry', 12, (55, 10), carry={'end_location': [70, 20]}, obv_total_net=0.02)
    b.add(US, 'Pass', 12, (70, 20), **_pass((95, 40)), obv_total_net=0.10)
    b.add(US, 'Pass', 13, (95, 40), dt=5, **_pass((105, 40)), obv_total_net=0.08)
    b.add(US, 'Shot', 13, (110, 40), **_shot(0.30, goal=True), obv_total_net=0.25)


def _second_block(b: _Builder) -> None:
    # 6 · ellos saque inicial; pase fallado que interceptamos
    b.possession(THEM, 'From Kick Off', 60)
    b.add(THEM, 'Pass', 21, (60, 40), **_pass((90, 40), ok=False))
    # 7 · nosotros: intercepción, conducción y desposesión (duelo perdido) → pérdida letal
    b.possession(US, 'Regular Play', 65)
    b.add(US, 'Interception', 11, (30, 40), interception={'outcome': {'name': 'Won'}})
    b.add(US, 'Carry', 11, (30, 40), carry={'end_location': [40, 40]}, obv_total_net=-0.01)
    b.add(US, 'Dispossessed', 11, (40, 40), obv_total_net=-0.05)
    # 8 · ellos: robo, pase al área y gol en 5 s (con freeze frame)
    b.possession(THEM, 'Regular Play', 70)
    b.add(THEM, 'Ball Recovery', 21, (80, 40))
    b.add(THEM, 'Pass', 21, (80, 40), dt=3, **_pass((105, 40)), obv_total_net=0.12)
    b.add(THEM, 'Shot', 22, (108, 40), **_shot(0.45, goal=True, ff=_ff()), obv_total_net=0.30)
    # 9 · nosotros saque inicial; pase arriesgado adelante perdido en el área rival
    b.possession(US, 'From Kick Off', 90)
    b.add(US, 'Pass', 12, (60, 40), **_pass((85, 40)), obv_total_net=0.04)
    b.add(US, 'Pass', 13, (85, 40), **_pass((100, 20)))
    b.add(US, 'Pass', 13, (100, 20), **_pass((110, 30), ok=False, xpass=0.3))
    # 10 · ellos salen desde atrás; presionamos alto y cometemos falta en x=75 (PPDA)
    b.possession(THEM, 'Regular Play', 95)
    b.add(THEM, 'Pass', 20, (10, 50), **_pass((40, 50)))
    b.add(US, 'Pressure', 13, (80, 30))
    b.add(US, 'Foul Committed', 12, (75, 25))
    b.add(THEM, 'Pass', 21, (40, 50), **_pass((70, 60), ok=False))


def _third_block(b: _Builder) -> None:
    # 11 · nosotros: robo alto (x=85) y tiro fuera del área
    b.possession(US, 'Regular Play', 100)
    b.add(US, 'Ball Recovery', 12, (85, 20))
    b.add(US, 'Pass', 12, (85, 20), **_pass((100, 12)))
    b.add(US, 'Shot', 13, (100, 12), **_shot(0.05), obv_total_net=-0.02)
    # 12 · ellos saque de meta
    b.possession(THEM, 'From Goal Kick', 110)
    b.add(THEM, 'Pass', 20, (6, 40), **_pass((30, 40), ptype='Goal Kick', length=24.0))
    b.add(THEM, 'Pass', 21, (30, 40), **_pass((60, 40)))
    # 13 · nuestro penal (gol)
    b.possession(US, 'Other', 140)
    b.add(US, 'Shot', 13, (108, 40), **_shot(0.76, goal=True, pen=True))
    # 14 · ellos saque inicial
    b.possession(THEM, 'From Kick Off', 150)
    b.add(THEM, 'Pass', 21, (60, 40), **_pass((70, 40)))
    # 15 · córner rival con remate (balón parado)
    b.possession(THEM, 'From Corner', 160)
    b.add(THEM, 'Pass', 21, (120, 80), **_pass((110, 40), ptype='Corner', length=41.0))
    b.add(THEM, 'Shot', 22, (110, 40), **_shot(0.20), obv_total_net=0.01)
    # 16 · penal rival (atajado)
    b.possession(THEM, 'Other', 175)
    b.add(THEM, 'Shot', 22, (108, 40), **_shot(0.76, pen=True))
    # 17 · nosotros: el portero juega en corto en juego abierto
    b.possession(US, 'Regular Play', 190)
    b.add(US, 'Pass', 10, (10, 40), **_pass((25, 30), length=18.0))


def events() -> list[dict[str, Any]]:
    """Eventos del partido sintético (orden por índice)."""
    b = _Builder()
    _first_half(b)
    _second_block(b)
    _third_block(b)
    return b.ev


def metadata() -> dict[str, Any]:
    return {'match_id': MID, 'home_team': {'home_team_id': US}, 'away_team': {'away_team_id': THEM}}


def an() -> dict[str, Any]:
    """Extracto ``an_`` del partido según el contrato real (sequences.build_possessions)."""
    import sequences
    out = sequences.build_possessions(events(), metadata())
    return dict(out, version=1, match_id=MID, status='ok', home=US, away=THEM)


def team_stats(ppda: float = 10.0) -> list[dict[str, Any]]:
    """Filas de team-stats del partido (valores de validación)."""
    return [{'team_id': US, 'team_match_ppda': ppda, 'team_match_obv': 0.40, 'team_match_np_xg': 0.335},
            {'team_id': THEM, 'team_match_ppda': 6.0, 'team_match_obv': 0.49, 'team_match_np_xg': 0.71}]


def lineups() -> list[dict[str, Any]]:
    return [{'team_id': US, 'lineup': [{'player_id': k, 'player_name': v, 'player_nickname': v.split()[0]}
                                       for k, v in NAMES.items() if k < 20]}]


def f360(isolated_eid: str = 'e25') -> dict[str, Any]:
    """Tabla 'perdidas' 360 con una pérdida propia aislada (err_valid) para probar el cruce por evento."""
    cols = ['team', 'player', 'eid', 'err_valid', 'isolated', 'op3']
    return {'tables': {'perdidas': {'cols': cols, 'rows': [[US, 11, isolated_eid, True, True, 0]]}}}


def context(rows: Any = None, league_ref: Any = None, f360_doc: Any = None) -> Any:
    """EntityContext de un partido sintético (oficial) con cargadores en memoria."""
    import analytics
    rows = rows if rows is not None else [{'id': MID, 'date': '2024-03-01', 'window': 'oficial', 'team_id': US,
                                           'opponent': 'Rival FC', 'venue': 'local', 'score': [2, 1]}]
    an_doc, ev = an(), events()
    ctx = analytics.EntityContext(entity_id='ent', label='Ent', team='Nosotros', coach='DT', matches=rows,
                                  load_an=lambda m: an_doc, load_events=lambda m: ev,
                                  load_f360=lambda m: f360_doc,
                                  league_ref=league_ref if league_ref is not None else {'a4_unidades': {}})
    ctx.load_lineups = lambda m: lineups()
    ctx.load_team_stats = lambda m: team_stats()
    return ctx


def records(obj: Any) -> list:
    """Todos los registros de métrica (dict con id, value y window) de un payload."""
    out = []
    if isinstance(obj, dict):
        if {'id', 'value', 'window'} <= set(obj):
            out.append(obj)
        for v in obj.values():
            out.extend(records(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(records(v))
    return out
