"""Un solo punto de entrada para el pipeline de datos.

    python pipeline/run.py download   # baja eventos, alineaciones y estadísticas (requiere .env)
    python pipeline/run.py extract    # resume cada partido en data/extract/
    python pipeline/run.py build      # construye model/model.json
    python pipeline/run.py validate   # compara la simulación con los datos reales (requiere Node)
    python pipeline/run.py referee    # árbitro automático (requiere Node)
    python pipeline/run.py all        # todo lo anterior en orden
"""
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = [sys.executable, '-I', '-X', 'utf8']
STEPS = {
    'download': [PY + [str(HERE / 'download.py')], PY + [str(HERE / 'download_lineups.py')], PY + [str(HERE / 'download_opendata.py')]],
    'extract': [PY + [str(HERE / 'extract.py')]],
    'build': [PY + [str(HERE / 'build_model.py')], PY + [str(HERE / 'check_model.py')], PY + [str(HERE / 'targets.py')]],
    'validate': [['node', str(HERE / 'validate.js'), '600']],
    'referee': [['node', str(HERE / 'referee.js'), '3']],
}
ORDER = ['download', 'extract', 'build', 'validate', 'referee']

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in STEPS and sys.argv[1] != 'all':
        print(__doc__); sys.exit(1)
    steps = ORDER if sys.argv[1] == 'all' else [sys.argv[1]]
    for step in steps:
        print(f'\n=== {step} ===', flush=True)
        for cmd in STEPS[step]:
            subprocess.run(cmd, check=True)

if __name__ == '__main__':
    main()
