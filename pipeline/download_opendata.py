"""Barcelona 2009/10 y 2010/11 (La Liga) desde StatsBomb Open Data (licencia abierta con atribución)."""
import json, pathlib, requests, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from statsbomb import _read_json
from concurrent.futures import ThreadPoolExecutor
OUT = pathlib.Path(__file__).resolve().parents[1] / 'data' / 'opendata'
OUT.mkdir(parents=True, exist_ok=True)
RAW = 'https://raw.githubusercontent.com/statsbomb/open-data/master/data'
def get(path):
    f = OUT / path.replace('/', '_')
<<<<<<< HEAD
    if f.exists(): return _read_json(f)
    r = requests.get(f'{RAW}/{path}', timeout=120); r.raise_for_status()
    data = json.loads(r.content.decode('utf-8-sig'))
    f.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False), encoding='utf-8')
=======
    # Try to load cached JSON safely; ignore decode errors and fallback on failure
    if f.exists():
        try:
            return json.load(open(f, encoding='utf-8', errors='ignore'))
        except Exception as e:
            print('Cache corrupto para', path, '-', e, flush=True)
    # No valid cache – fetch from remote and store using UTF‑8
    r = requests.get(f'{RAW}/{path}', timeout=120)
    r.raise_for_status()
    data = r.json()
    f.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
>>>>>>> origin/main
    return data
ids = []
for sid in (21, 22):
    for m in get(f'matches/11/{sid}.json'):
        if 'Barcelona' in (m['home_team']['home_team_name'], m['away_team']['away_team_name']): ids.append(m['match_id'])
print('matches', len(ids), flush=True)
with ThreadPoolExecutor(8) as ex: list(ex.map(lambda i: get(f'events/{i}.json'), ids))
print('done', flush=True)
