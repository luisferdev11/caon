"""Descarga reanudable de eventos, lineups y 360 de StatsBomb con backoff exponencial.

Funciones puras/inyectables (getter, sleep) para poder probarlas sin red.
La caché en disco (data/cache) hace la reanudación: lo ya bajado no se vuelve a pedir.
Uso directo: python pipeline/download_360.py <match_id> ... (solo 360).
"""
import pathlib
import sys
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

BACKOFF_DELAYS_S = (2, 4, 8, 16, 32)
DOWNLOAD_THREADS = 4
RETRY_STATUS = {429, 500, 502, 503, 504}
PATHS = {'events': 'v8/events/{}', 'lineups': 'v4/lineups/{}', '360': 'v2/360-frames/{}'}
ALL_KINDS = ('events', 'lineups', '360')


def cache_name(path: str) -> str:
    """Nombre del archivo de caché que usa statsbomb.get para `path`."""
    return path.strip('/').replace('/', '_') + '.json'


def is_retriable(ex: Exception) -> bool:
    """429/5xx, timeouts y errores de conexión se reintentan; 4xx no."""
    if isinstance(ex, (requests.Timeout, requests.ConnectionError)):
        return True
    code = getattr(getattr(ex, 'response', None), 'status_code', None)
    return code in RETRY_STATUS


def fetch_with_backoff(path: str, getter: Callable[[str], object], sleep: Callable[[float], None],
                       delays: Sequence[float] = BACKOFF_DELAYS_S) -> tuple:
    """(ok, error) tras intentar `getter(path)` con esperas `delays` entre reintentos."""
    for attempt in range(len(delays) + 1):
        try:
            getter(path)
            return True, None
        except Exception as ex:  # noqa: BLE001  (se registra y se decide si reintentar)
            err = f'{type(ex).__name__}: {ex}'
            if not is_retriable(ex) or attempt == len(delays):
                return False, err
            sleep(delays[attempt])
    return False, 'sin intentos'


def jobs_for_match(m: dict, kinds: Iterable[str] = ALL_KINDS) -> list:
    """Rutas de API para un partido; 360 solo si match_status_360 == 'available'."""
    out = []
    for k in kinds:
        if k == '360' and m.get('match_status_360') != 'available':
            continue
        out.append(PATHS[k].format(m['match_id']))
    return out


def run_jobs(paths: Sequence[str], getter: Callable[[str], object], cache: pathlib.Path,
             threads: int = DOWNLOAD_THREADS, sleep: Callable[[float], None] = time.sleep,
             on_progress: Callable[[dict], None] = lambda s: None, deadline: float = 0.0) -> dict:
    """Baja `paths` no cacheados en paralelo. deadline (epoch s) > 0 detiene trabajos nuevos."""
    stats = {'total': len(paths), 'cached': 0, 'ok': 0, 'failures': [], 'skipped_deadline': 0}
    lock = threading.Lock()
    todo = [p for p in paths if not (cache / cache_name(p)).exists()]
    stats['cached'] = len(paths) - len(todo)

    def work(p: str) -> None:
        if deadline and time.time() > deadline:
            with lock:
                stats['skipped_deadline'] += 1
            return
        ok, err = fetch_with_backoff(p, getter, sleep)
        with lock:
            if ok:
                stats['ok'] += 1
            else:
                stats['failures'].append({'path': p, 'error': err})
            on_progress(stats)

    with ThreadPoolExecutor(threads) as ex:
        list(ex.map(work, todo))
    return stats


if __name__ == '__main__':
    from statsbomb import CACHE, get
    ids = [int(a) for a in sys.argv[1:]]
    res = run_jobs([PATHS['360'].format(i) for i in ids], get, CACHE)
    print({k: (v if k != 'failures' else len(v)) for k, v in res.items()})
