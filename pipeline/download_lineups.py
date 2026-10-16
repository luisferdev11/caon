import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from entities import *
import requests, json
from concurrent.futures import ThreadPoolExecutor
ents, ms = build_entities()
ids = sorted({x['mid'] for e in ents for x in e['matches']})
def f(m):
    for k in range(3):
        try: get(f'v4/lineups/{m}'); return
        except Exception as ex: err = ex
    print('ERR', m, err, flush=True)
with ThreadPoolExecutor(8) as ex: list(ex.map(f, ids))
OD = pathlib.Path(__file__).resolve().parents[1] / 'data' / 'opendata'
RAW = 'https://raw.githubusercontent.com/statsbomb/open-data/master/data'
od = [int(p.stem.split('_')[1]) for p in OD.glob('events_*.json')]
def g(m):
    p = OD / f'lineups_{m}.json'
    if not p.exists(): p.write_text(requests.get(f'{RAW}/lineups/{m}.json', timeout=60).text)
with ThreadPoolExecutor(8) as ex: list(ex.map(g, od))
print('done', len(ids), len(od))
