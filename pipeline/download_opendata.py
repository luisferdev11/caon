"""Barcelona 2009/10 y 2010/11 (La Liga) desde StatsBomb Open Data (licencia abierta con atribución)."""
import json, pathlib, requests
from concurrent.futures import ThreadPoolExecutor
OUT = pathlib.Path(__file__).resolve().parents[1] / 'data' / 'opendata'
RAW = 'https://raw.githubusercontent.com/statsbomb/open-data/master/data'
def get(path):
    f = OUT / path.replace('/', '_')
    if f.exists(): return json.load(open(f))
    r = requests.get(f'{RAW}/{path}', timeout=120); r.raise_for_status(); f.write_text(r.text); return r.json()
ids = []
for sid in (21, 22):
    for m in get(f'matches/11/{sid}.json'):
        if 'Barcelona' in (m['home_team']['home_team_name'], m['away_team']['away_team_name']): ids.append(m['match_id'])
print('matches', len(ids), flush=True)
with ThreadPoolExecutor(8) as ex: list(ex.map(lambda i: get(f'events/{i}.json'), ids))
print('done', flush=True)
