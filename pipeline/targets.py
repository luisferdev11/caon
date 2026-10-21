"""Observed validation targets. Coverage is per metric; no observations => null."""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import json
import statistics as st
from entities import build_entities, CACHE
from statsbomb import _read_json
from metric_utils import finite
from build_model import ascii_id, display

C = ['team_match_goals', 'team_match_np_xg', 'team_match_np_xg_conceded', 'team_match_possession', 'team_match_np_shots', 'team_match_np_shots_conceded', 'team_match_sp_xg', 'team_match_goals_conceded']
<<<<<<< HEAD


def agg(rows):
    out, counts = {}, {}
    for c in C:
        values = [r[c] for r in rows if finite(r.get(c))]
        key = c.replace('team_match_', '')
        out[key] = round(st.mean(values), 3) if values else None
        counts[key] = len(values)
    out['coverage'] = {'rows': len(rows), 'valid_matches': counts, 'match_ids': sorted({r['_mid'] for r in rows if '_mid' in r})}
    return out


def main():
    ents, ms = build_entities()
    rows = []
    for m in ms:
        f = CACHE / f"v1_matches_{m['match_id']}_team-stats.json"
        if f.exists():
            for r in _read_json(f):
                r['_mid'] = m['match_id']; rows.append(r)
    out = {'league': agg(rows)}
    by = {}
    for r in rows:
        if finite(r.get('team_match_goals')): by.setdefault(r['_mid'], []).append(r['team_match_goals'])
    goals = [v for v in by.values() if len(v) == 2]
    out['league']['draw_rate'] = round(sum(a == b for a, b in goals) / len(goals), 3) if goals else None
    for e in ents:
        mids = {x['mid'] for x in e['matches']}
        out[ascii_id(display(e)[0])] = agg([r for r in rows if r['_mid'] in mids and r['team_name'] == e['team']])
    pathlib.Path(__file__).with_name('targets.json').write_text(json.dumps(out, indent=1, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print('Targets:', len(out), 'entidades/referencias')


if __name__ == '__main__': main()
=======
def agg(rs):
    result = {}
    for c in C:
        values = [r[c] for r in rs if r.get(c) is not None]
        key = c.replace('team_match_', '')
        if values:
            result[key] = round(st.mean(values), 3)
        else:
            result[key] = None
    return result
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
>>>>>>> origin/main
