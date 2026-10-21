"""Etapa 1: resume cada partido (eventos StatsBomb) en conteos compactos por equipo.

Framework (definiciones que usa todo lo demás):
- Posesión: eventos con el mismo `possession` id de StatsBomb (StatsBomb abre una posesión nueva en cada
  reanudación, también cuando la reanuda el mismo equipo).
- Acción con balón: Pass, Carry, Dribble o Shot del equipo en posesión (con ubicación).
- Zonas: rejilla 6 (largo) x 3 (ancho) sobre 120x80 yardas, en la orientación del equipo que ataca.
- Recuperación: posesión de juego abierto (Regular Play / From Counter) que sigue a una posesión rival.
- Fase de transición (T): acciones de los primeros 10 s de una posesión que empezó con recuperación.
  Todo lo demás es fase de ataque establecido (E).
- Balón parado peligroso (BP): posesión From Corner, o From Free Kick cuya primera acción está en x >= 80.
- Resultado de cada acción en zona z y fase f:
    move   pase o conducción a la zona w dentro de la misma posesión
    shot   tiro en juego abierto (sin penales), con xG
    spC    gana un córner                       spF   gana una falta peligrosa (x >= 80)
    pen    gana un penal
    keepF  le hacen falta lejos del área: tiro libre a su favor      keepT  el rival la saca: saque de banda a favor
    lossO  pierde en juego (el rival sigue en juego abierto)
    lossXT / lossXG / lossXF  pierde con balón muerto: saque de banda / saque de meta / falta o fuera de juego rival
- Balón parado en detalle: córners (cortos, técnica, zona de caída, remates, de cabeza), faltas directas o
  centradas, penales (lanzador, lado), faltas y tarjetas, lanzadores y rematadores.
Salida: data/extract/<fuente>_<match>.json. Solo conteos agregados.
"""
import sys, json, pathlib, collections
from multiprocessing import Pool
from functools import lru_cache
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from contextual import extract_context, ordered_events, score_timeline, state_for, defensive_action

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data' / 'cache'
OD = ROOT / 'data' / 'opendata'
OUT = ROOT / 'data' / 'extract'
OUT.mkdir(parents=True, exist_ok=True)
NX, NY, NZ = 6, 3, 18
ONBALL = {'Pass', 'Carry', 'Dribble', 'Shot'}
OPEN_RESTARTS = {'Regular Play', 'From Counter', 'From Keeper'}
SP_PLAY = {'From Corner', 'From Free Kick', 'From Throw In'}
DEF_TYPES = {'Pressure', 'Duel', 'Interception', 'Ball Recovery', 'Block', 'Clearance', 'Foul Committed'}
T_WINDOW = 10.0
CORNER_TARGETS = ('corto', 'primer palo', 'área chica', 'segundo palo', 'punto penal', 'borde')
PH_KEYS = ('n', 'shot', 'xg', 'spC', 'spF', 'pen', 'keepF', 'keepT', 'lossO', 'lossXT', 'lossXG', 'lossXF')
LTO_KEYS = ('ltoO', 'ltoXT', 'ltoXG', 'ltoXF', 'ltoKF', 'ltoKT')

def _read_json_file(path):
    raw = pathlib.Path(path).read_bytes()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('cp1252')
    return json.loads(text)

@lru_cache(maxsize=2)
def _metadata_index(src):
    paths = CACHE.glob('v6_competitions_73_seasons_*_matches.json') if src == 'mx' else OD.glob('matches_*.json')
    out = {}
    for path in paths:
        for match in _read_json_file(path): out[match['match_id']] = match
    return out


def _match_metadata(mid, src='mx'):
    return _metadata_index(src).get(mid)


def _score_context(events):
    ordered = ordered_events(events)
    ids = {e.get('team', {}).get('id') for e in ordered}
    before, _, _ = score_timeline(ordered, ids)
    return {e.get('index'): score for e, score in zip(ordered, before)}


_state_for = state_for


def zone(loc):
    x = min(max(loc[0], 0), 119.999); y = min(max(loc[1], 0), 79.999)
    return int(x // 20) * NY + int(y // (80 / 3))

def ts(e):
    ms = 0.0
    try: ms = float('0.' + e['timestamp'].split('.')[1])
    except Exception: pass
    return e['minute'] * 60 + e['second'] + ms

def first_onball(pe, tid=None):
    return next((e for e in pe if e['type']['name'] in ONBALL and 'location' in e and (tid is None or e['team']['id'] == tid)), None)

def has_pen(pe):
    return any(e['type']['name'] == 'Shot' and e['shot']['type']['name'] == 'Penalty' for e in pe)

ADMIN = {'Foul Committed', 'Foul Won', 'Bad Behaviour', 'Injury Stoppage', 'Substitution', 'Referee Ball-Drop', 'Tactical Shift',
         'Player Off', 'Player On', 'Half Start', 'Half End', 'Starting XI', 'Camera On', 'Camera off'}
def is_admin(pe):
    """Posesión sin balón en juego (solo falta, tarjeta, lesión...): no cuenta para saber cómo sigue el juego."""
    return all(e['type']['name'] in ADMIN for e in pe)

def is_sp(pe):
    pp = pe[0]['play_pattern']['name']
    if has_pen(pe): return False
    if pp == 'From Corner': return True
    if pp == 'From Free Kick':
        f = first_onball(pe)
        return bool(f and f['location'][0] >= 80)
    return False

def corner_target(p):
    """Zona de caída del córner, normalizada como si se cobrara desde el lado y=0."""
    if p['pass']['length'] < 15: return 0
    x, y = p['pass']['end_location']
    if p['location'][1] > 40: y = 80 - y
    if x >= 114:
        return 1 if y < 36 else (2 if y <= 44 else 3)
    if x >= 102: return 3 if y > 50 else 4
    return 5

def new_team():
    z2 = lambda: [[0] * NZ for _ in range(2)]
    m2 = lambda: [[[0] * NZ for _ in range(NZ)] for _ in range(2)]
    d = {k: z2() for k in PH_KEYS}
    d['xg'] = [[0.0] * NZ for _ in range(2)]
    d.update(mv=m2(), mvC=m2(), dt=[0.0, 0.0], dtn=[0, 0], poss=0, poss_regain=0,
             sp_poss=0, sp_shots=0, sp_xg=0.0, sp_after_shot=0, pens=0, pens_scored=0, pen_place=[0, 0, 0],
             corners=0, corners_short=0, corner_tech=[0, 0, 0], corner_target=[0] * 6, corner_shots=0, corner_xg=0.0, corner_headers=0,
             fk=0, fk_direct=0, fk_direct_xg=0.0, fk_cross_shots=0, fk_cross_xg=0.0,
             fouls=0, yellow=0, second_yellow=0, red=0, bb_yellow=0, bb_red=0,
             actors=collections.defaultdict(lambda: [0] * NZ), avgpos=collections.defaultdict(lambda: [0.0, 0.0, 0, 0.0, 0.0, 0]),
             takers=dict(corner=collections.Counter(), fk=collections.Counter(), pen=collections.Counter(), sp_shooter=collections.Counter()),
             m=collections.Counter(),
             context=dict(score_state={}, venue={}))
    for k in LTO_KEYS: d[k] = [[0] * NZ for _ in range(NZ)]
    return d

def _process(args):
    src, mid = args
    out = OUT / f'{src}_{mid}.json'
    if out.exists() and '--force' not in sys.argv:
        if _read_json_file(out).get('extract_version') == 2: return str(out)
    if src == 'mx':
        E = _read_json_file(CACHE / f'v8_events_{mid}.json'); L = _read_json_file(CACHE / f'v4_lineups_{mid}.json')
    else:
        E = _read_json_file(OD / f'events_{mid}.json')
        try:
            L = _read_json_file(OD / f'lineups_{mid}.json')
        except (OSError, UnicodeError, json.JSONDecodeError):
            L = []
    nick = {}
    for t in L:
        for p in t['lineup']: nick[p['player_id']] = (p.get('player_nickname') or p['player_name'], p.get('jersey_number'))
    E = ordered_events(E)
    teams = {}
    for e in E: teams.setdefault(e['team']['id'], e['team']['name'])
    metadata = _match_metadata(mid, src)
    contexts, context_status = extract_context(E, metadata, is_sp=is_sp)
    T = {tid: new_team() for tid in teams}
    for tid in T:
        T[tid]['context'] = contexts.get(tid, {})
        T[tid]['context_status'] = context_status
    xi = {}
    for e in E:
        if e['type']['name'] == 'Starting XI':
            xi[e['team']['id']] = dict(formation=e['tactics']['formation'],
                                      players=[dict(pos=p['position']['name'], pid=p['player']['id'],
                                                    name=nick.get(p['player']['id'], (p['player']['name'], None))[0],
                                                    jersey=p.get('jersey_number') or nick.get(p['player']['id'], (None, None))[1]) for p in e['tactics']['lineup']])
    other = {a: b for a in teams for b in teams if a != b}
    # ---------- posiciones medias, métricas, faltas, tarjetas y contexto ----------
    for event_index, e in enumerate(E):
        tid = e['team']['id']; A = T[tid]; t = e['type']['name']
        if 'location' in e and 'position' in e:
            a = A['avgpos'][e['position']['name']]
            if e['possession_team']['id'] == tid: a[0] += e['location'][0]; a[1] += e['location'][1]; a[2] += 1
            else: a[3] += e['location'][0]; a[4] += e['location'][1]; a[5] += 1
        m = A['m']
        if t == 'Pass':
            m['passes'] += 1
            if e['location'][0] < 72: m['passes_own60'] += 1
            if e.get('position', {}).get('name') == 'Goalkeeper':
                m['gk_passes'] += 1
                if e['pass']['length'] >= 32: m['gk_long'] += 1
            el = e['pass']['end_location']
            if e['pass'].get('cross') and el[0] >= 102 and 18 <= el[1] <= 62: m['crosses_box'] += 1
        if t in DEF_TYPES and 'location' in e:
            m['def_n'] += 1; m['def_x'] += e['location'][0]
            if e['location'][0] >= 48 and defensive_action(e):
                m['ppda_den'] += 1
        if t == 'Pressure':
            m['pressures'] += 1
            if e.get('counterpress'): m['counterpressures'] += 1
        if t == 'Shot' and e['shot']['type']['name'] != 'Penalty':
            m['np_xg'] += e['shot']['statsbomb_xg']
            if e['play_pattern']['name'] in SP_PLAY: m['sp_xg'] += e['shot']['statsbomb_xg']
        if t == 'Foul Committed':
            A['fouls'] += 1
            cd = (e.get('foul_committed') or {}).get('card', {}).get('name')
            if cd == 'Yellow Card': A['yellow'] += 1
            elif cd == 'Second Yellow': A['second_yellow'] += 1
            elif cd == 'Red Card': A['red'] += 1
        if t == 'Bad Behaviour':
            cd = (e.get('bad_behaviour') or {}).get('card', {}).get('name')
            if cd == 'Yellow Card': A['bb_yellow'] += 1
            elif cd in ('Red Card', 'Second Yellow'): A['bb_red'] += 1
    # ---------- cadena por posesiones ----------
    poss = collections.OrderedDict()
    for e in E: poss.setdefault(e['possession'], []).append(e)
    P = list(poss.values())
    for i, pe in enumerate(P):
        tid = pe[0]['possession_team']['id']
        if tid not in T: continue
        A = T[tid]; pp = pe[0]['play_pattern']['name']
        acts_all = [e for e in pe if e['team']['id'] == tid and e['type']['name'] in ONBALL and 'location' in e]
        for e in acts_all:
            if e['type']['name'] == 'Shot' and e['shot']['type']['name'] == 'Penalty':
                A['pens'] += 1; A['takers']['pen'][e['player']['id']] += 1
                if e['shot']['outcome']['name'] == 'Goal': A['pens_scored'] += 1
                y = e['shot']['end_location'][1]
                A['pen_place'][0 if y < 38.5 else (2 if y > 41.5 else 1)] += 1
        acts = [e for e in acts_all if not (e['type']['name'] == 'Shot' and e['shot']['type']['name'] == 'Penalty')]
        if not acts: continue
        # directness / pace / contragolpe (posesiones de juego abierto)
        prev = P[i - 1] if i > 0 else None
        regain = prev is not None and prev[0]['possession_team']['id'] != tid and pp in ('Regular Play', 'From Counter')
        if not is_sp(pe):
            fwd = tot = 0.0
            for e in acts:
                if e['type']['name'] in ('Pass', 'Carry'):
                    el = e['pass']['end_location'] if e['type']['name'] == 'Pass' else e['carry']['end_location']
                    fwd += max(0.0, el[0] - e['location'][0]); tot += ((el[0] - e['location'][0]) ** 2 + (el[1] - e['location'][1]) ** 2) ** 0.5
            A['m']['dir_fwd'] += fwd; A['m']['dir_tot'] += tot
        if regain and acts[0]['location'][0] >= 80:
            A['m']['high_press_shots'] += sum(1 for e in acts if e['type']['name'] == 'Shot')
        shots_np = [e for e in acts if e['type']['name'] == 'Shot']
        if shots_np:
            sh = shots_np[0]; d_ = max(ts(sh) - ts(acts[0]), 0.5)
            if regain and acts[0]['location'][0] < 60 and d_ <= 15: A['m']['counter_shots2'] += 1
            if not is_sp(pe):
                A['m']['pace2_sum'] += max(sh['location'][0] - acts[0]['location'][0], 0) / d_; A['m']['pace2_n'] += 1
        # balón parado peligroso
        if is_sp(pe):
            A['sp_poss'] += 1
            for e in acts:
                if e['type']['name'] == 'Shot': A['sp_shots'] += 1; A['sp_xg'] += e['shot']['statsbomb_xg']
            f0 = acts[0]
            if pp == 'From Corner':
                if f0['type']['name'] == 'Pass':
                    A['corners'] += 1; A['takers']['corner'][f0['player']['id']] += 1
                    if f0['pass']['length'] < 15: A['corners_short'] += 1
                    tech = (f0['pass'].get('technique') or {}).get('name')
                    if tech in ('Inswinging', 'Outswinging', 'Straight'): A['corner_tech'][('Inswinging', 'Outswinging', 'Straight').index(tech)] += 1
                    A['corner_target'][corner_target(f0)] += 1
                for e in acts:
                    if e['type']['name'] == 'Shot':
                        A['corner_shots'] += 1; A['corner_xg'] += e['shot']['statsbomb_xg']; A['takers']['sp_shooter'][e['player']['id']] += 1
                        if (e['shot'].get('body_part') or {}).get('name') == 'Head': A['corner_headers'] += 1
            else:
                A['fk'] += 1; A['takers']['fk'][f0['player']['id']] += 1
                if f0['type']['name'] == 'Shot':
                    A['fk_direct'] += 1; A['fk_direct_xg'] += f0['shot']['statsbomb_xg']
                else:
                    for e in acts:
                        if e['type']['name'] == 'Shot':
                            A['fk_cross_shots'] += 1; A['fk_cross_xg'] += e['shot']['statsbomb_xg']; A['takers']['sp_shooter'][e['player']['id']] += 1
            continue
        A['poss'] += 1
        if regain: A['poss_regain'] += 1
        t0 = ts(pe[0])
        k = i + 1
        while k < len(P) and is_admin(P[k]): k += 1
        nxt = P[k] if k < len(P) else None
        for j, e in enumerate(acts):
            ph = 1 if (regain and ts(e) - t0 <= T_WINDOW) else 0
            z = zone(e['location'])
            A['actors'][e.get('position', {}).get('name', '?')][z] += 1
            A['n'][ph][z] += 1
            if e['type']['name'] == 'Shot':
                A['shot'][ph][z] += 1; A['xg'][ph][z] += e['shot']['statsbomb_xg']
                if nxt is not None and nxt[0]['possession_team']['id'] == tid and is_sp(nxt): A['sp_after_shot'] += 1
                break
            if j + 1 < len(acts):
                w = zone(acts[j + 1]['location'])
                A['mv'][ph][z][w] += 1
                if e['type']['name'] in ('Carry', 'Dribble'): A['mvC'][ph][z][w] += 1
                d = ts(acts[j + 1]) - ts(e)
                if 0 <= d <= 30: A['dt'][ph] += d; A['dtn'][ph] += 1
                continue
            # última acción: ¿cómo sigue el juego?
            if nxt is None: A['n'][ph][z] -= 1; break
            nt = nxt[0]['possession_team']['id']; npp = nxt[0]['play_pattern']['name']
            g = first_onball(nxt, nt)
            gz = zone(g['location']) if g is not None else None
            if nt != tid:
                if npp in OPEN_RESTARTS:
                    A['lossO'][ph][z] += 1
                    if gz is not None: A['ltoO'][z][gz] += 1
                else:
                    key = 'T' if npp == 'From Throw In' else ('G' if npp == 'From Goal Kick' else 'F')
                    A['lossX' + key][ph][z] += 1
                    if gz is not None: A['ltoX' + key][z][gz] += 1
            elif has_pen(nxt):
                A['pen'][ph][z] += 1
            elif is_sp(nxt):
                (A['spC'] if npp == 'From Corner' else A['spF'])[ph][z] += 1
            elif npp == 'From Throw In':
                A['keepT'][ph][z] += 1
                if gz is not None: A['ltoKT'][z][gz] += 1
            elif npp in ('From Free Kick', 'Other', 'From Goal Kick'):
                A['keepF'][ph][z] += 1
                if gz is not None: A['ltoKF'][z][gz] += 1
            elif gz is not None:
                A['mv'][ph][z][gz] += 1   # el mismo equipo sigue en juego abierto
            else:
                A['n'][ph][z] -= 1
    res = dict(src=src, mid=mid, extract_version=2, context_status=context_status, teams={}, names={str(k): v for k, v in nick.items()})
    for tid, A in T.items():
        A['m']['opp_passes_own60'] = T[other[tid]]['m']['passes_own60'] if tid in other else 0
        A['m']['opp_passes'] = T[other[tid]]['m']['passes'] if tid in other else 0
        A['m']['np_xga'] = T[other[tid]]['m']['np_xg'] if tid in other else 0
        d = {k: v for k, v in A.items() if k not in ('actors', 'avgpos', 'm', 'takers')}
        d['actors'] = dict(A['actors']); d['avgpos'] = dict(A['avgpos']); d['m'] = dict(A['m'])
        d['takers'] = {k: {str(p): c for p, c in v.items()} for k, v in A['takers'].items()}
        d['name'] = teams[tid]; d['xi'] = xi.get(tid)
        d['xg'] = [[round(v, 4) for v in row] for row in d['xg']]
        res['teams'][str(tid)] = d
    out.write_text(json.dumps(res, separators=(',', ':'), ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return str(out)

def process(args):
    """Quarantine incomplete matches instead of producing partial simulator counts."""
    try:
        return _process(args)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        src, mid = args
        out = OUT / f'{src}_{mid}.json'
        failed = dict(src=src, mid=mid, extract_version=2, teams={},
                      status='invalid', reason=f'{type(exc).__name__}: {exc}')
        out.write_text(json.dumps(failed, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        print(f'WARN: {src}/{mid}: {failed["reason"]}', flush=True)
        return str(out)


def jobs():
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from entities import build_entities
    ents, ms = build_entities()
    mx = sorted({x['mid'] for e in ents for x in e['matches']})
    od = sorted(int(p.stem.split('_')[1]) for p in OD.glob('events_*.json'))
    return [('mx', m) for m in mx] + [('od', m) for m in od]

if __name__ == '__main__':
    J = jobs()
    with Pool(8) as p:
        for k, _ in enumerate(p.imap_unordered(process, J, chunksize=4)):
            if k % 100 == 0: print(k, len(J), flush=True)
    print('done', len(J))
