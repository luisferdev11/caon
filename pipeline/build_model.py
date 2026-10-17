"""Etapa 2: agrega los resúmenes por partido (extract.py) en model/model.json.

Por cada equipo-entrenador:
- att: cómo ataca (conteos por fase T/E y zona: acciones, tiros, xG, balón parado ganado,
       pérdidas en juego / con balón muerto, transiciones de zona y cuántas fueron conducciones)
- dfn: lo mismo, pero de sus rivales cuando lo atacan (sin matrices de movimiento)
- shape: once tipo con número, nombre y posición media con y sin balón
- actors: qué puesto toca el balón en cada zona (para la animación)
- style: percentiles del plan de juego
Tipos de equipo: 'real' (Liga MX, API StatsBomb), 'opendata' (Barcelona 2009-11, StatsBomb Open Data),
'synthetic' (arquetipo configurado a mano para validar que el motor responde a una configuración).
"""
import sys, json, math, pathlib, collections, unicodedata
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from entities import *
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
EX = ROOT / 'data' / 'extract'
OUT = ROOT / 'model'
OUT.mkdir(exist_ok=True)
NX, NY, NZ = 6, 3, 18
K_MATCHES = 8
PH_OUT = ('n', 'shot', 'spC', 'spF', 'pen', 'keepF', 'keepT', 'lossO', 'lossXT', 'lossXG', 'lossXF')
LTO_KEYS = ('ltoO', 'ltoXT', 'ltoXG', 'ltoXF', 'ltoKF', 'ltoKT')
CHAIN_KEYS = PH_OUT + ('xg', 'mv', 'mvC') + LTO_KEYS + ('dt', 'dtn', 'corner_tech', 'corner_target', 'pen_place')
SCALAR_KEYS = ('poss', 'poss_regain', 'sp_poss', 'sp_shots', 'sp_xg', 'sp_after_shot', 'pens', 'pens_scored',
               'corners', 'corners_short', 'corner_shots', 'corner_xg', 'corner_headers', 'fk', 'fk_direct', 'fk_direct_xg',
               'fk_cross_shots', 'fk_cross_xg', 'fouls', 'yellow', 'second_yellow', 'red', 'bb_yellow', 'bb_red')

def zeros_like(v):
    return [zeros_like(x) for x in v] if isinstance(v, list) else 0

def add_into(a, b):
    for i in range(len(a)):
        if isinstance(a[i], list): add_into(a[i], b[i])
        else: a[i] += b[i]

class Acc:
    def __init__(self):
        self.c = None
        self.s = collections.Counter()
        self.matches = 0
        # New dict for open‑play signatures: key -> [count, xg, goals]
        self.plays_open = collections.defaultdict(lambda: [0, 0.0, 0])
    def add(self, t):
        if self.c is None:
            self.c = {k: zeros_like(t[k]) for k in CHAIN_KEYS}
        for k in CHAIN_KEYS:
            add_into(self.c[k], t[k])
        for k in SCALAR_KEYS:
            self.s[k] += t[k]
        # Merge open‑play signatures if present
        if 'plays_open' in t:
            for key, vals in t['plays_open'].items():
                self.plays_open[key][0] += vals[0]
                self.plays_open[key][1] += vals[1]
                self.plays_open[key][2] += vals[2]
        self.matches += 1
    def to(self, moves=True):
        c = self.c
        d = {k: c[k] for k in PH_OUT + LTO_KEYS + ('corner_tech', 'corner_target', 'pen_place')}
        d['xg'] = [[round(v, 3) for v in row] for row in c['xg']]
        if moves:
            d['mv'] = c['mv']
            d['mvC'] = c['mvC']
        # Include aggregated open‑play signatures for downstream use
        d['plays_open'] = {k: list(v) for k, v in self.plays_open.items()}
        d['tau'] = [round(c['dt'][p] / max(c['dtn'][p], 1), 3) for p in (0, 1)]
        d.update({k: (round(v, 3) if isinstance(v, float) else v) for k, v in self.s.items()})
        d['matches'] = self.matches
        return d
        d['tau'] = [round(c['dt'][p] / max(c['dtn'][p], 1), 3) for p in (0, 1)]
        d.update({k: (round(v, 3) if isinstance(v, float) else v) for k, v in self.s.items()})
        d['matches'] = self.matches
        return d

def load(src, mid):
    try:
        path = EX / f'{src}_{mid}.json'
        raw = path.read_bytes()
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('cp1252')
        return json.loads(text)
    except Exception:
        # Return minimal structure so callers can safely skip missing/corrupt files
        return {'teams': {}}

def short_name(nm):
    parts = [p for p in nm.split() if p.lower() not in ('da', 'de', 'del', 'dos', 'i', 'la', 'van', 'von', 'y')]
    if len(parts) <= 2: return nm
    return parts[0][0] + '. ' + (parts[-2] if len(parts) >= 4 else parts[1])

def ascii_id(s): return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()

def short_team(t):
    return {'Guadalajara': 'Chivas', 'Atlético San Luis': 'San Luis', 'Pumas UNAM': 'Pumas', 'Tigres UANL': 'Tigres', 'Santos Laguna': 'Santos'}.get(t, t)

DISPLAY = {'Herrera Aguirre': ('atlante_herrera', 'Miguel Herrera'), 'Crespo': ('atlas_crespo', 'Hernán Crespo'),
    'Mejía Campo': ('sanluis_mejia', 'Diego Mejía'), 'Huiqui': ('cruzazul_huiqui', 'Joel Huiqui'), 'Lema': ('juarez_lema', 'Gustavo Lema'),
    'Gandolfi': ('leon_gandolfi', 'Javier Gandolfi'), 'Almeyda': ('monterrey_almeyda', 'Matías Almeyda'), 'Reynoso': ('necaxa_reynoso', 'Juan Reynoso'),
    'Mora Mendívil': ('pachuca_mora', 'Benjamín Mora'), 'Espinoza': ('puebla_espinoza', 'Gerardo Espinoza'), 'Esteban Andrés Solari': ('pumas_esolari', 'Esteban Solari'),
    'González Herrera': ('queretaro_gonzalez', 'Esteban González'), 'Paiva': ('santos_paiva', 'Renato Paiva'), 'Vucetich': ('tigres_vucetich', 'Víctor Vucetich'),
    'Abreu': ('tijuana_abreu', 'Sebastián Abreu'), 'Mohamed': ('toluca_mohamed', 'Antonio Mohamed')}
SPECIAL_IDS = {s[0] for s in SPECIAL}
def display(e):
    if e['id'] in SPECIAL_IDS: return e['id'], e['label'], e['coach_key']
    for k, (i, n) in DISPLAY.items():
        if k in e['coach_key']: return i, f"{short_team(e['team'])} · {n}", n
    return e['id'], e['label'], e['coach_key']

# ---------------------------------------------------------------- forma y actores
def build_shape(xi_list, avgpos, actors):
    freq = collections.Counter(); who = collections.defaultdict(collections.Counter); info = {}
    forms = collections.Counter()
    for xi in xi_list:
        if not xi: continue
        forms[xi['formation']] += 1
        for p in xi['players']:
            freq[p['pos']] += 1; who[p['pos']][p['pid']] += 1; info[p['pid']] = (p['name'], p['jersey'])
    # once tipo: el conjunto de puestos más repetido dentro de la formación más usada
    top_form = forms.most_common(1)[0][0] if forms else None
    sets = collections.Counter(tuple(sorted(p['pos'] for p in xi['players'])) for xi in xi_list if xi and xi['formation'] == top_form)
    slots = list(sets.most_common(1)[0][0]) if sets else [p for p, _ in freq.most_common(11)]
    slots = ['Goalkeeper'] + [p for p in slots if p != 'Goalkeeper']
    def anc(p, k):
        a = avgpos.get(p)
        if not a: return None
        if k == 'con': return [round(a[0] / a[2], 1), round(a[1] / a[2], 1)] if a[2] else None
        return [round(a[3] / a[5], 1), round(a[4] / a[5], 1)] if a[5] else None
    # un jugador distinto por puesto: primero los puestos con titular más claro
    chosen, used = {}, set()
    for p in sorted(slots, key=lambda q: -(who[q].most_common(1)[0][1] if who[q] else 0)):
        for pid, _ in who[p].most_common():
            if pid not in used: chosen[p] = pid; used.add(pid); break
    shape = []
    for p in slots:
        con, sin = anc(p, 'con'), anc(p, 'sin')
        if con is None or sin is None or p not in chosen: continue
        nm, num = info[chosen[p]]
        shape.append(dict(pos=p, name=short_name(nm), num=num, con=con, sin=sin, pid=chosen[p]))
    idx = {s['pos']: i for i, s in enumerate(shape)}
    act = [[0] * len(shape) for _ in range(NZ)]
    for p, arr in actors.items():
        if p in idx: j = idx[p]
        else:
            a = anc(p, 'con')
            if a is None: continue
            j = min(range(len(shape)), key=lambda i: (shape[i]['con'][0] - a[0]) ** 2 + (shape[i]['con'][1] - a[1]) ** 2 + (1e6 if (shape[i]['pos'] == 'Goalkeeper') != (p == 'Goalkeeper') else 0))
        for z in range(NZ): act[z][j] += arr[z]
    act = [[round(v / max(sum(row), 1), 3) for v in row] for row in act]
    form = '-'.join(str(forms.most_common(1)[0][0])) if forms else None
    return shape, act, form

# ---------------------------------------------------------------- estilo (percentiles)
STY = [  # clave, columna StatsBomb, invertir, etiqueta
    ('posesion', 'team_match_possession', False, 'Posesión'),
    ('verticalidad', 'team_match_directness', False, 'Verticalidad'),
    ('ritmo', 'team_match_pace_towards_goal', False, 'Velocidad hacia portería'),
    ('linea', 'team_match_defensive_distance', False, 'Altura de línea defensiva'),
    ('volumen_presion', 'team_match_pressures_adj', False, 'Volumen de presión'),
    ('presion', 'team_match_ppda', True, 'Acciones defensivas por pase rival (PPDA)'),
    ('contrapresion', 'team_match_counterpressures', False, 'Contrapresión'),
    ('saque_largo', 'team_match_gk_long_pass_ratio', False, 'Saque largo del portero'),
    ('centros', 'team_match_crosses_into_box', False, 'Centros al área'),
    ('contragolpe', 'team_match_counter_attacking_shots', False, 'Tiros al contragolpe'),
    ('presion_alta_tiros', 'team_match_high_press_shots', False, 'Tiros tras robo alto'),
    ('xg', 'team_match_np_xg', False, 'xG a favor'),
    ('xga', 'team_match_np_xg_conceded', True, 'Solidez (xG en contra)'),
    ('bp_xg', 'team_match_sp_xg', False, 'Peligro a balón parado'),
]
def my_metrics(m):
    """Métricas propias desde eventos, una por cada métrica StatsBomb de STY (para calibrar)."""
    poss = m.get('passes', 0) / max(m.get('passes', 0) + m.get('opp_passes', 0), 1)
    return {
        'team_match_possession': poss,
        'team_match_directness': m.get('dir_fwd', 0) / max(m.get('dir_tot', 0), 1),
        'team_match_pace_towards_goal': m.get('pace2_sum', 0) / max(m.get('pace2_n', 0), 1),
        'team_match_defensive_distance': m.get('def_x', 0) / max(m.get('def_n', 0), 1),
        'team_match_pressures_adj': m.get('pressures', 0) / max(1 - poss, 0.2),
        'team_match_ppda': math.log(max(m.get('opp_passes_own60', 0), 1) / max(m.get('ppda_den', 0), 1)),
        'team_match_counterpressures': m.get('counterpressures', 0),
        'team_match_gk_long_pass_ratio': m.get('gk_long', 0) / max(m.get('gk_passes', 0), 1),
        'team_match_crosses_into_box': m.get('crosses_box', 0),
        'team_match_counter_attacking_shots': m.get('counter_shots2', 0),
        'team_match_high_press_shots': m.get('high_press_shots', 0),
        'team_match_np_xg': m.get('np_xg', 0), 'team_match_np_xg_conceded': m.get('np_xga', 0),
        'team_match_sp_xg': m.get('sp_xg', 0),
    }

# ---------------------------------------------------------------- arquetipo sintético
def col(z): return z // NY

ATLETI = dict(
    id='arq_autobus', label='Autobús y contra (arquetipo tipo Atlético)', team='Arquetipo', coach='Configurado',
    formation='4-4-2',
    # ataque, fase E (posesión establecida): juego directo, pierde más en salida, busca adelante
    att_E=dict(lossO_by_col=[1.9, 1.9, 1.6, 1.45, 1.35, 1.25], forward_bias=1.0, shot_by_col=[1, 1, 1, 0.5, 0.5, 0.55], xg=1.0, lossX=1.3),
    # ataque, fase T (transición tras robo): vertical, preciso y letal
    att_T=dict(lossO_by_col=[1.1, 1.1, 1.0, 0.95, 0.95, 0.95], forward_bias=1.7, shot_by_col=[1, 1, 1, 1.0, 1.0, 1.0], xg=1.0, lossX=1.0),
    # rivales atacando contra él: dejan circular atrás, se atascan cerca del área, tiros de poca calidad
    dfn_E=dict(lossO_by_col=[0.55, 0.6, 0.9, 1.15, 1.45, 1.45], shot_by_col=[1, 1, 1, 0.8, 0.65, 0.65], xg=0.75, lossX=1.0, forward_bias=1.0),
    dfn_T=dict(lossO_by_col=[1, 1, 1.1, 1.3, 1.45, 1.45], shot_by_col=[1, 1, 1, 0.7, 0.6, 0.6], xg=0.75, lossX=1.0, forward_bias=1.0),
    sp_att=dict(shots=1.0, xg=1.1), sp_dfn=dict(shots=0.72, xg=0.85),
    style=dict(posesion=6, verticalidad=95, ritmo=93, linea=8, volumen_presion=22, presion=35, contrapresion=15, saque_largo=88,
               centros=55, contragolpe=97, presion_alta_tiros=20, xg=70, xga=97, bp_xg=92),
    shape=[  # puesto, número, rol, con balón [x,y], sin balón [x,y] (orientación propia: ataca hacia x=120)
        ('Goalkeeper', 1, 'Portero', [7, 40], [4, 40]),
        ('Right Back', 2, 'Lateral der.', [42, 70], [17, 66]),
        ('Right Center Back', 4, 'Central der.', [30, 50], [14, 47]),
        ('Left Center Back', 5, 'Central izq.', [30, 30], [14, 33]),
        ('Left Back', 3, 'Lateral izq.', [42, 10], [17, 14]),
        ('Right Midfield', 7, 'Volante der.', [66, 68], [30, 64]),
        ('Right Center Midfield', 6, 'Mediocentro', [52, 46], [27, 45]),
        ('Left Center Midfield', 8, 'Mediocentro', [52, 34], [27, 35]),
        ('Left Midfield', 11, 'Volante izq.', [66, 12], [30, 16]),
        ('Right Center Forward', 9, 'Delantero', [84, 48], [44, 46]),
        ('Left Center Forward', 10, 'Delantero', [80, 32], [42, 34]),
    ])

def synth(L, cfg_E, cfg_T, sp_cfg, n_matches, moves=True):
    """Conteos sintéticos a partir de la liga, con multiplicadores por fase y por columna de la cancha."""
    c = L.c; out = {k: zeros_like(c[k]) for k in CHAIN_KEYS}
    f = n_matches / L.matches
    other_keys = ('spC', 'spF', 'pen', 'keepF', 'keepT')
    for ph, cfg in ((0, cfg_E), (1, cfg_T)):
        for z in range(NZ):
            n = c['n'][ph][z]
            if n == 0: continue
            k = col(z)
            r = {'shot': c['shot'][ph][z] / n * cfg['shot_by_col'][k], 'lossO': c['lossO'][ph][z] / n * cfg['lossO_by_col'][k]}
            for key in ('lossXT', 'lossXG', 'lossXF'): r[key] = c[key][ph][z] / n * cfg['lossX']
            for key in other_keys: r[key] = c[key][ph][z] / n
            tot = sum(r.values())
            if tot > 0.95: r = {kk: v * 0.95 / tot for kk, v in r.items()}
            N = n * f
            out['n'][ph][z] = N
            for key, v in r.items(): out[key][ph][z] = v * N
            xps = c['xg'][ph][z] / max(c['shot'][ph][z], 1)
            out['xg'][ph][z] = r['shot'] * N * xps * cfg['xg']
            row = c['mv'][ph][z]
            if sum(row):
                w = [row[j] * cfg['forward_bias'] ** (col(j) - k) for j in range(NZ)]
                sw = sum(w); moves_n = N * (1 - sum(r.values()))
                out['mv'][ph][z] = [v / sw * moves_n for v in w]
                out['mvC'][ph][z] = [out['mv'][ph][z][j] * (c['mvC'][ph][z][j] / row[j] if row[j] else 0) for j in range(NZ)]
        out['dt'][ph] = c['dt'][ph] * f; out['dtn'][ph] = c['dtn'][ph] * f
    for k in LTO_KEYS: out[k] = [[v * f for v in row] for row in c[k]]
    for k in ('corner_tech', 'corner_target', 'pen_place'): out[k] = [v * f for v in c[k]]
    A = Acc(); A.c = out; A.matches = n_matches
    for k in SCALAR_KEYS: A.s[k] = L.s[k] * f
    for k in ('sp_shots', 'corner_shots', 'fk_cross_shots', 'corner_headers', 'fk_direct'): A.s[k] *= sp_cfg['shots']
    for k in ('sp_xg', 'corner_xg', 'fk_cross_xg', 'fk_direct_xg'): A.s[k] *= sp_cfg['shots'] * sp_cfg['xg']
    d = A.to(moves)
    for k in PH_OUT: d[k] = [[round(v, 2) for v in r] for r in d[k]]
    for k in LTO_KEYS: d[k] = [[round(v, 2) for v in r] for r in d[k]]
    for k in ('corner_tech', 'corner_target', 'pen_place'): d[k] = [round(v, 2) for v in d[k]]
    for k in SCALAR_KEYS: d[k] = round(d[k], 3) if isinstance(d.get(k), float) else d.get(k)
    if moves:
        for k in ('mv', 'mvC'): d[k] = [[[round(v, 2) for v in r] for r in m] for m in d[k]]
    return d

def roles_for(shape, tk):
    """Lanzador de córners, faltas y penales y rematadores de balón parado: el jugador del once tipo que más lo hizo."""
    pid2slot = {s.get('pid'): i for i, s in enumerate(shape)}
    def best(counter, fallback):
        for pid, _ in counter.most_common():
            if pid in pid2slot: return pid2slot[pid]
        return fallback
    fwd = max(range(len(shape)), key=lambda i: shape[i]['con'][0])
    mid = max((i for i in range(len(shape)) if shape[i]['pos'] != 'Goalkeeper'), key=lambda i: -abs(shape[i]['con'][0] - 70) - abs(shape[i]['con'][1] - 40) / 3)
    aerial = [pid2slot[p] for p, _ in tk['sp_shooter'].most_common() if p in pid2slot][:4]
    cbs = [i for i, s in enumerate(shape) if 'Center Back' in s['pos']]
    for i in cbs + [fwd]:
        if len(aerial) >= 4: break
        if i not in aerial: aerial.append(i)
    return dict(corner=best(tk['corner'], mid), fk=best(tk['fk'], mid), pen=best(tk['pen'], fwd), aerial=aerial)

def signature_plays(team_acc, league_acc, n_matches):
    """Return list of open‑play signature plays sorted by relevance.
    Each entry dict contains: key, count, per10, share, lift, xg_per_shot, goals.
    """
    team_dict = team_acc.plays_open
    league_dict = league_acc.plays_open
    total_league = sum(v[0] for v in league_dict.values()) or 1
    total_team = sum(v[0] for v in team_dict.values()) or 1
    out = []
    for key, vals in team_dict.items():
        cnt, xg, goals = vals
        if cnt == 0:
            continue
        per10 = cnt * 10 / max(n_matches, 1)
        share = cnt / total_team
        league_cnt = league_dict.get(key, [0, 0, 0])[0]
        lift = (cnt / total_team) / (league_cnt / total_league) if league_cnt else (cnt / total_team)
        xg_per_shot = xg / cnt if cnt else 0
        out.append({
            "key": key,
            "count": cnt,
            "per10": round(per10, 2),
            "share": round(share, 3),
            "lift": round(lift, 2),
            "xg_per_shot": round(xg_per_shot, 3),
            "goals": goals,
        })
    out.sort(key=lambda d: d["count"] * (d["lift"] ** 0.5), reverse=True)
    return out
# ---------------------------------------------------------------- main
def main():
    ents, ms = build_entities()
    LEAGUE = Acc()
    mx_ids = sorted({x['mid'] for e in ents for x in e['matches']})
    EXT = {mid: load('mx', mid) for mid in mx_ids}
    for X in EXT.values():
        for t in X['teams'].values(): LEAGUE.add(t)
    # estilo: referencia StatsBomb (equipo-temporada de toda la liga)
    rows = []
    for m in ms:
        f = CACHE / f"v1_matches_{m['match_id']}_team-stats.json"
        if not f.exists(): continue
        for r in json.load(open(f)):
            r['_mid'] = m['match_id']
            if r.get('team_match_pressures') is not None and r.get('team_match_possession'):
                r['team_match_pressures_adj'] = r['team_match_pressures'] / (1 - r['team_match_possession'])
            rows.append(r)
    grp = collections.defaultdict(list)
    for r in rows: grp[(r['team_name'], r['season_id'])].append(r)
    def mean(rs, c):
        v = [r[c] for r in rs if r.get(c) is not None]
        return sum(v) / len(v) if v else None
    ref = {c: sorted(x for x in (mean(rs, c) for rs in grp.values() if len(rs) >= 10) if x is not None) for _, c, _, _ in STY}
    league_mean = {c: mean(rows, c) for _, c, _, _ in STY}
    def pct(c, v, inv):
        d = ref[c]; p = 100 * sum(1 for x in d if x < v) / len(d)
        return round(100 - p if inv else p)
    # calibración: métricas propias (eventos) -> escala StatsBomb, partido a partido en Liga MX
    sb_by = {(r['_mid'], r['team_name']): r for r in rows}
    pairs = collections.defaultdict(list)
    for mid, X in EXT.items():
        for t in X['teams'].values():
            r = sb_by.get((mid, t['name']))
            if not r: continue
            mm = my_metrics(t['m'])
            for _, c, _, _ in STY:
                y = r.get(c)
                if y is None: continue
                if c == 'team_match_ppda': y = math.log(max(y, 0.5))
                pairs[c].append((mm[c], y))
    CAL = {}
    print('Calibración métricas propias -> StatsBomb (por partido, Liga MX):')
    for _, c, _, lab in STY:
        x, y = np.array(pairs[c]).T
        b, a = np.polyfit(x, y, 1); r2 = float(np.corrcoef(x, y)[0, 1] ** 2)
        CAL[c] = (float(a), float(b), r2); print(f'  {lab:45s} R² {r2:.2f}  (n={len(x)})')
    def from_events(mlist):
        vals = collections.defaultdict(list)
        for m in mlist:
            mm = my_metrics(m)
            for _, c, _, _ in STY:
                a, b, r2 = CAL[c]
                if r2 < 0.5: continue          # métrica que no replicamos bien desde eventos: se omite
                v = a + b * mm[c]
                vals[c].append(math.exp(v) if c == 'team_match_ppda' else v)
        return {c: sum(v) / len(v) for c, v in vals.items()}
    def style_from_means(means, n):
        s, raw = {}, {}
        for key, c, inv, lab in STY:
            v = means.get(c)
            if v is None: continue
            vs = (n * v + K_MATCHES * league_mean[c]) / (n + K_MATCHES)
            s[key] = pct(c, vs, inv); raw[key] = round(v, 3)
        return s, raw
    def entity_from_matches(src, mids, team_name):
        att, dfn = Acc(), Acc()
        xis = []
        avg = collections.defaultdict(lambda: [0.0] * 6)
        actors = collections.defaultdict(lambda: [0] * NZ)
        mlist = []
        tk = {k: collections.Counter() for k in ('corner', 'fk', 'pen', 'sp_shooter')}
        for mid in mids:
            X = EXT[mid] if src == 'mx' else load(src, mid)
            if not X or 'teams' not in X:
                continue
            tms = list(X['teams'].values())
            me = next((t for t in tms if t['name'] == team_name), None)
            if me is None or len(tms) != 2:
                continue
            op = next(t for t in tms if t is not me)
            att.add(me); dfn.add(op); xis.append(me['xi']); mlist.append(me['m'])
            for k in tk:
                for pid, cnt in me['takers'][k].items():
                    tk[k][int(pid)] += cnt
            for p, a in me['avgpos'].items():
                for i in range(6):
                    avg[p][i] += a[i]
            for p, a in me['actors'].items():
                for z in range(NZ):
                    actors[p][z] += a[z]
        shape, act, form = build_shape(xis, avg, actors)
        if not shape:
            return None
        # Compute roles for this entity
        roles = roles_for(shape, tk)
        return att, dfn, shape, act, form, mlist, roles
    # ---------------- mapa de estilos
    # ejes en percentiles (mismas métricas que el plan de juego):
    #   con balón: x = ritmo de ataque (media de velocidad hacia portería y tiros al contragolpe), y = posesión
    #   sin balón: x = altura de línea, y = intensidad de presión (media de volumen de presión y contrapresión)
    def map_point(st_):
        g = st_.get
        off = [round((g('ritmo') + g('contragolpe')) / 2), g('posesion')] if None not in (g('ritmo'), g('contragolpe'), g('posesion')) else None
        dfn = [g('linea'), round((g('volumen_presion') + g('contrapresion')) / 2)] if None not in (g('linea'), g('volumen_presion'), g('contrapresion')) else None
        return off, dfn
    def surname(full):
        parts = full.split()
        return parts[-2] if len(parts) >= 4 else parts[-1]
    mid2m = {m['match_id']: m for m in ms}
    urows = collections.defaultdict(list)
    for r in rows:
        m = mid2m.get(r['_mid'])
        if not m: continue
        side = 'home' if m['home_team']['home_team_name'] == r['team_name'] else 'away'
        mg = m[side + '_team'].get('managers') or []
        if len(mg) != 1: continue
        urows[(r['team_name'], mg[0]['name'], mg[0].get('nickname'), SEASONS_ALL[m['season']['season_id']])].append(r)
    units = []
    for (team, full, nick, season), rs in sorted(urows.items(), key=lambda kv: (kv[0][0], kv[0][3])):
        if len(rs) < 8: continue
        st_, _ = style_from_means({c: mean(rs, c) for _, c, _, _ in STY}, len(rs))
        off, dfn = map_point(st_)
        if off is None or dfn is None: continue
        units.append(dict(team=short_team(team), team_full=team, coach=nick or surname(full), coach_full=full, season=season, n=len(rs), off=off, dfn=dfn))

        # Build list of entities with styles and metrics
        out_ents = []
        for e in ents:
            mids = [x['mid'] for x in e['matches']]
            result = entity_from_matches('mx', mids, e['team'])
            if result is None:
                continue
            att, dfn, shape, act, form, mlist, roles = result
            did, dlabel, coach = display(e)
            rs = [r for r in rows if r['_mid'] in set(mids) and r['team_name'] == e['team']]
            s, raw = style_from_means({c: mean(rs, c) for _, c, _, _ in STY}, len(rs))
            dates = [x['date'] for x in e['matches']]
            out_ents.append(dict(id=ascii_id(did), label=dlabel, team=e['team'], coach=coach, group=e['group'], kind='real',
                                 d0=min(dates), d1=max(dates), n=len(rs), official=max(dates) <= '2025-06-30', formation=form,
                                 style=s, raw=raw, shape=shape, actors=act, roles=roles, att=att.to(True), dfn=dfn.to(False)))

        # Barcelona 2009-11 (StatsBomb Open Data)
        od_ids = sorted(int(p.stem.split('_')[1]) for p in EX.glob('od_*.json'))
        att, dfn, shape, act, form, mlist, roles = entity_from_matches('od', od_ids, 'Barcelona')
        s, raw = style_from_means(from_events(mlist), len(mlist))
        out_ents.append(dict(id='barca_guardiola', label='Barcelona 2009–11 (Guardiola)', team='Barcelona', coach='Pep Guardiola', group='Validación', kind='opendata',
                             d0='2009-08-29', d1='2011-05-21', n=att.matches, official=False, formation=form, style=s, raw=raw, shape=shape, actors=act, roles=roles,
                             att=att.to(True), dfn=dfn.to(False),
                             note='La Liga 2009/10 y 2010/11, StatsBomb Open Data. Estilo con métricas propias de eventos calibradas a la escala StatsBomb.'))

        # Arquetipo sintético
        C = ATLETI
        sh = [dict(pos=p, name=role, num=num, con=con, sin=sin) for p, num, role, con, sin in C['shape']]
        act = []
        for z in range(NZ):
            cx, cy = (col(z) + 0.5) * 20, (z % NY + 0.5) * 80 / 3
            w = [math.exp(-(((s_['con'][0] - cx) ** 2 + (s_['con'][1] - cy) ** 2) ** 0.5) / 11) * (0.15 if s_['pos'] == 'Goalkeeper' and col(z) > 0 else 1) for s_ in sh]
            act.append([round(v / sum(w), 3) for v in w])
        out_ents.append(dict(id=C['id'], label=C['label'], team=C['team'], coach=C['coach'], group='Validación', kind='synthetic',
                             d0=None, d1=None, n=60, official=False, formation=C['formation'], style=C['style'], raw={}, shape=sh, actors=act,
                             roles=dict(corner=5, fk=7, pen=9, aerial=[2, 3, 9, 10]),
                             att=synth(LEAGUE, C['att_E'], C['att_T'], C['sp_att'], 60, True),
                             dfn=synth(LEAGUE, C['dfn_E'], C['dfn_T'], C['sp_dfn'], 60, False),
                             note='Arquetipo configurado a mano (no son datos de un equipo real): bloque bajo, deja la pelota al rival y contragolpea con verticalidad.'))
    for e, raw_e in zip(out_ents, list(ents) + [None, None]):
        off, dfn = map_point(e['style'])
        traj = []
        if raw_e is not None:
            traj = [i for i, u in enumerate(units) if u['team_full'] == raw_e['team'] and raw_e['coach_key'] in u['coach_full']]
        e['map'] = dict(off=off, dfn=dfn, traj=traj)
    for u in units: u.pop('team_full'); u.pop('coach_full')
    model_map = dict(units=units)

    model = dict(map=model_map, meta=dict(nx=NX, ny=NY, k_matches=K_MATCHES, built='2026-10-15', t_window=10,
                           style_labels={k: lab for k, _, _, lab in STY},
                           calibration={c: round(CAL[c][2], 2) for c in CAL},
                           note='Parámetros agregados derivados de datos de eventos Hudl StatsBomb. Sin eventos crudos.'),
                 league=LEAGUE.to(True), entities=out_ents)
    json.dump(model, open(OUT / 'model.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('\nwrote', OUT / 'model.json', (OUT / 'model.json').stat().st_size // 1024, 'KB')
    for e in out_ents:
        # Safely encode label for console output
        safe_label = e['label'].encode('utf-8', errors='ignore').decode('utf-8')
        print(f"  {e['id']:20s} {safe_label:45s} n={e['n']:3d} {e['formation']}  " +
              ' '.join(f"{s['num']}:{s['name']}" for s in e['shape']))

if __name__ == '__main__':
    main()
