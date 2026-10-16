import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from entities import *
from concurrent.futures import ThreadPoolExecutor
ents, ms = build_entities()
ev_ids = sorted({x['mid'] for e in ents for x in e['matches']})
jobs = [f'v8/events/{m}' for m in ev_ids] + [f"v1/matches/{m['match_id']}/team-stats" for m in ms]
print('jobs', len(jobs), flush=True)
def f(p):
    for k in range(3):
        try: get(p); return
        except Exception as ex: err = ex
    print('ERR', p, err, flush=True)
with ThreadPoolExecutor(8) as ex:
    for i, _ in enumerate(ex.map(f, jobs)):
        if i % 200 == 0: print(i, flush=True)
print('done')
