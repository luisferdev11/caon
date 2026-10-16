"""Laboratorio: variantes de definición para replicar pace_towards_goal, directness y counter_attacking_shots."""
import sys, json, pathlib, collections, math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'pipeline'))
from multiprocessing import Pool
import numpy as np
from extract import CACHE, ts, ONBALL, is_sp
def per_match(mid):
    E = [e for e in json.load(open(CACHE / f'v8_events_{mid}.json')) if e['period'] <= 4]
    poss = collections.OrderedDict()
    for e in E: poss.setdefault(e['possession'], []).append(e)
    P = list(poss.values()); out = collections.defaultdict(lambda: collections.Counter())
    for i, pe in enumerate(P):
        tid = pe[0]['possession_team']['id']; name = pe[0]['possession_team']['name']; m = out[name]
        acts = [e for e in pe if e['team']['id'] == tid and e['type']['name'] in ONBALL and 'location' in e]
        if not acts or is_sp(pe) or pe[0]['play_pattern']['name'] in ('From Corner', 'From Free Kick', 'From Throw In', 'From Goal Kick', 'From Kick Off'): pass
        prev = P[i - 1] if i > 0 else None
        regain = prev is not None and prev[0]['possession_team']['id'] != tid and pe[0]['play_pattern']['name'] in ('Regular Play', 'From Counter')
        if not acts: continue
        t0 = ts(acts[0]); x0 = acts[0]['location'][0]
        endx = acts[-1]['location'][0]
        last = acts[-1]
        if last['type']['name'] == 'Pass': endx = last['pass']['end_location'][0]
        elif last['type']['name'] == 'Carry': endx = last['carry']['end_location'][0]
        dur = max(ts(acts[-1]) - t0, 0.5)
        path = 0.0
        for e in acts:
            if e['type']['name'] in ('Pass', 'Carry'):
                el = e['pass']['end_location'] if e['type']['name'] == 'Pass' else e['carry']['end_location']
                path += math.hypot(el[0] - e['location'][0], el[1] - e['location'][1])
        net = endx - x0
        openp = not is_sp(pe)
        if openp:
            if net > 0: m['p3_prog'] += net; m['p3_dur'] += dur
            if endx >= 80: m['p2_prog'] += max(net, 0); m['p2_dur'] += dur
            if net > 0: m['p1_sum'] += net / dur; m['p1_n'] += 1
            if path > 10: m['d1_sum'] += max(net, 0) / path; m['d1_n'] += 1
            m['d2_net'] += max(net, 0); m['d2_path'] += path
            if endx >= 80 and path > 0: m['d4_net'] += max(net, 0); m['d4_path'] += path
        shots_ = [e for e in acts if e['type']['name'] == 'Shot' and e['shot']['type']['name'] != 'Penalty']
        if shots_ and openp:
            sh = shots_[0]; d_ = max(ts(sh) - t0, 0.5); pr = sh['location'][0] - x0
            m['p4_prog'] += max(pr, 0); m['p4_dur'] += d_
            m['p5_sum'] += max(pr, 0) / d_; m['p5_n'] += 1
            pth = 0.0
            for e in acts:
                if e is sh: break
                if e['type']['name'] in ('Pass', 'Carry'):
                    el = e['pass']['end_location'] if e['type']['name'] == 'Pass' else e['carry']['end_location']
                    pth += math.hypot(el[0] - e['location'][0], el[1] - e['location'][1])
            if pth > 0: m['d5_sum'] += max(pr, 0) / pth; m['d5_n'] += 1; m['d6_net'] += max(pr, 0); m['d6_path'] += pth
        for e in acts:
            if e['type']['name'] != 'Shot' or e['shot']['type']['name'] == 'Penalty': continue
            dt = ts(e) - t0
            if regain and x0 < 60 and dt <= 15: m['c1'] += 1
            if regain and x0 < 40 and dt <= 20: m['c2'] += 1
            if regain and dt <= 12: m['c3'] += 1
            if regain and x0 < 60 and dt <= 20: m['c4'] += 1
            if regain and x0 < 80 and dt <= 10: m['c5'] += 1
    return mid, {k: dict(v) for k, v in out.items()}
if __name__ == '__main__':
    from entities import build_entities
    ents, ms = build_entities()
    mids = sorted({x['mid'] for e in ents for x in e['matches']})
    with Pool(8) as p: res = dict(p.map(per_match, mids))
    xs = collections.defaultdict(list); ys = collections.defaultdict(list)
    for mid, teams in res.items():
        f = CACHE / f'v1_matches_{mid}_team-stats.json'
        sb = {r['team_name']: r for r in json.load(open(f))}
        for name, m in teams.items():
            r = sb.get(name)
            if not r: continue
            g = lambda k: m.get(k, 0)
            V = {'pace_p1': (g('p1_sum') / max(g('p1_n'), 1), 'team_match_pace_towards_goal'),
                 'pace_p2': (g('p2_prog') / max(g('p2_dur'), 1), 'team_match_pace_towards_goal'),
                 'pace_p3': (g('p3_prog') / max(g('p3_dur'), 1), 'team_match_pace_towards_goal'),
                 'dir_d1': (g('d1_sum') / max(g('d1_n'), 1), 'team_match_directness'),
                 'dir_d2': (g('d2_net') / max(g('d2_path'), 1), 'team_match_directness'),
                 'dir_d4': (g('d4_net') / max(g('d4_path'), 1), 'team_match_directness'),
                 'pace_p4': (g('p4_prog') / max(g('p4_dur'), 1), 'team_match_pace_towards_goal'),
                 'pace_p5': (g('p5_sum') / max(g('p5_n'), 1), 'team_match_pace_towards_goal'),
                 'dir_d5': (g('d5_sum') / max(g('d5_n'), 1), 'team_match_directness'),
                 'dir_d6': (g('d6_net') / max(g('d6_path'), 1), 'team_match_directness'),
                 'cnt_c1': (g('c1'), 'team_match_counter_attacking_shots'), 'cnt_c2': (g('c2'), 'team_match_counter_attacking_shots'),
                 'cnt_c3': (g('c3'), 'team_match_counter_attacking_shots'), 'cnt_c4': (g('c4'), 'team_match_counter_attacking_shots'),
                 'cnt_c5': (g('c5'), 'team_match_counter_attacking_shots')}
            for k, (x, col) in V.items():
                if r.get(col) is None: continue
                xs[k].append(x); ys[k].append(r[col])
    for k in sorted(xs):
        x, y = np.array(xs[k]), np.array(ys[k]); print(f'{k:10s} R² {np.corrcoef(x, y)[0,1]**2:.2f}  n={len(x)}')
