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
    """GET a la API con caché en disco.

    This version is defensive: it guards against corrupted cache files and empty
    responses that may happen on Windows when the API returns non‑ASCII characters
    or when a previous request failed and left an empty/HTML file on disk.
    """
    f = CACHE / (path.strip('/').replace('/', '_') + '.json')
    # Helper to fetch from the API
    def _fetch_and_cache():
        r = requests.get(f'{API}/{path}', auth=_auth(), timeout=120)
        r.raise_for_status()
        # Guard against empty bodies – treat them as an error
        if not r.text.strip():
            raise ValueError('Respuesta vacía de la API para %s' % path)
        # Write using utf-8 and ignore characters that cannot be encoded
        f.write_text(r.text, encoding='utf-8', errors='ignore')
        return r.json()

    # If we have a cached file, try to load it safely
    if f.exists():
        try:
            raw = f.read_bytes()
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                text = raw.decode('cp1252')
            return json.loads(text)
        except Exception as e:
            # Cache is corrupted or not valid JSON – remove and refetch
            print('Cache corrupto para', path, '-', e, flush=True)
            try:
                f.unlink()
            except Exception:
                pass
            return _fetch_and_cache()
    # No cache – fetch normally
    return _fetch_and_cache()

# Liga MX (competición 73). Ventana oficial del reto: Apertura 2021 – Clausura 2025.
SEASONS_ALL = {108: '2021/22', 235: '2022/23', 281: '2023/24', 317: '2024/25', 318: '2025/26', 351: '2026/27'}
SEASONS = {k: v for k, v in SEASONS_ALL.items() if k in (108, 235, 281, 317)}

def matches(sid):
    return get(f'v6/competitions/73/seasons/{sid}/matches')
