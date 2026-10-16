"""Cliente mínimo de la API de StatsBomb.

- Credenciales en el archivo .env de la raíz del repo (ver .env.example).
- Cada respuesta se guarda en data/cache/; si ya existe no se vuelve a pedir.
"""
import os, json, pathlib, requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
CACHE = DATA / 'cache'
CACHE.mkdir(parents=True, exist_ok=True)
API = 'https://data.statsbomb.com/api'

# credenciales: variables de entorno o .env
_env = ROOT / '.env'
if _env.exists():
    for line in _env.read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

def _auth():
    try:
        return (os.environ['USER_STATSBOMB'], os.environ['PSWD_STATSBOMB'])
    except KeyError:
        raise SystemExit('Faltan USER_STATSBOMB / PSWD_STATSBOMB: copia .env.example a .env y llena tus credenciales.')

def get(path):
    """GET a la API con caché en disco."""
    f = CACHE / (path.strip('/').replace('/', '_') + '.json')
    if f.exists():
        return json.load(open(f))
    r = requests.get(f'{API}/{path}', auth=_auth(), timeout=120)
    r.raise_for_status()
    f.write_text(r.text)
    return r.json()

# Liga MX (competición 73). Ventana oficial del reto: Apertura 2021 – Clausura 2025.
SEASONS_ALL = {108: '2021/22', 235: '2022/23', 281: '2023/24', 317: '2024/25', 318: '2025/26', 351: '2026/27'}
SEASONS = {k: v for k, v in SEASONS_ALL.items() if k in (108, 235, 281, 317)}

def matches(sid):
    return get(f'v6/competitions/73/seasons/{sid}/matches')
