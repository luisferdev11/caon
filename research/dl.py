import sys; sys.path.insert(0,'.')
from sb import *
from concurrent.futures import ThreadPoolExecutor
ids=[]
for sid in SEASONS:
    for m in matches(sid):
        if m['match_status_360']!='available': continue
        if 'rica' in m['home_team']['home_team_name'] or 'rica' in m['away_team']['away_team_name']:
            ids.append(m['match_id'])
print(len(ids),flush=True)
def f(mid):
    for p in [f'v8/events/{mid}',f'v2/360-frames/{mid}',f'v4/lineups/{mid}',f'v1/matches/{mid}/team-stats']:
        try: get(p)
        except Exception as e: print('ERR',p,e,flush=True)
    return mid
with ThreadPoolExecutor(6) as ex:
    for i,_ in enumerate(ex.map(f,ids)):
        if i%20==0: print(i,flush=True)
print('done')
