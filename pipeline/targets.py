import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from entities import *
import json, statistics as st
ents, ms = build_entities()
rows = []
for m in ms:
    f = CACHE / f"v1_matches_{m['match_id']}_team-stats.json"
    if f.exists():
        for r in json.load(open(f)): r['_mid'] = m['match_id']; rows.append(r)
C = ['team_match_goals', 'team_match_np_xg', 'team_match_np_xg_conceded', 'team_match_possession', 'team_match_np_shots', 'team_match_np_shots_conceded', 'team_match_sp_xg', 'team_match_goals_conceded']
def agg(rs): return {c.replace('team_match_', ''): round(st.mean(r[c] for r in rs if r.get(c) is not None), 3) for c in C}
out = {'league': agg(rows)}
# empates de liga
by = {}
for r in rows: by.setdefault(r['_mid'], []).append(r['team_match_goals'])
g = [v for v in by.values() if len(v) == 2]
out['league']['draw_rate'] = round(sum(a == b for a, b in g) / len(g), 3)
import importlib.util
spec = importlib.util.spec_from_file_location('bm', str(pathlib.Path(__file__).parent / 'build_model.py')); bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)
for e in ents:
    mids = {x['mid'] for x in e['matches']}
    rs = [r for r in rows if r['_mid'] in mids and r['team_name'] == e['team']]
    out[bm.ascii_id(bm.display(e)[0])] = agg(rs)
json.dump(out, open(pathlib.Path(__file__).parent / 'targets.json', 'w'), indent=1, ensure_ascii=False)
print(out['league'])
