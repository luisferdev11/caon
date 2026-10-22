"""Un solo punto de entrada para el pipeline de datos.

    python pipeline/run.py download   # baja eventos, alineaciones y estadísticas (requiere .env)
    python pipeline/run.py extract    # resume cada partido en data/extract/ (mx_, an_, f360_)
    python pipeline/run.py build      # extract + analysis
    python pipeline/run.py analysis   # referencias 360/A4, model.json, entities, analysis, explorer, xg, KPIs e historia
                                      # (no repite extract)
    python pipeline/run.py validate   # compara la simulación con los datos reales (requiere Node)
    python pipeline/run.py referee    # árbitro automático (requiere Node)
    python pipeline/run.py all        # download, build, validate, referee en orden

Variable CAON_LEAGUE_SCOPE=legacy restaura la referencia de liga anterior (sin entidades de Comparación).
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = [sys.executable, '-I', '-X', 'utf8']
PYM = [sys.executable, '-X', 'utf8', '-m']  # módulos del paquete analytics: se ejecutan desde pipeline/


def _py(name: str) -> list:
    return PY + [str(HERE / name)]


EXTRACT = [_py('extract.py'), _py('extract_analysis.py'), _py('extract_360.py')]
ANALYSIS = [PYM + ['analytics.shape360_ref'], PYM + ['analytics.a4_reference'], _py('build_model.py'),
            _py('check_model.py'), _py('targets.py'), _py('build_analysis.py'), _py('kpis.py'), _py('story.py'),
            [sys.executable, '-X', 'utf8', str(HERE / 'audit_coherence.py')]]   # al final: audita lo ya publicado
STEPS = {
    'download': [_py('download.py'), _py('download_lineups.py'), _py('download_opendata.py')],
    'extract': EXTRACT,
    'build': EXTRACT + ANALYSIS,
    'analysis': ANALYSIS,
    'validate': [['node', str(HERE / 'validate.js'), '600']],
    'referee': [['node', str(HERE / 'referee.js'), '3']],
}
ORDER = ['download', 'build', 'validate', 'referee']


def cwd_for(cmd: list):
    """Los comandos con -m necesitan pipeline/ como directorio de trabajo."""
    return HERE if '-m' in cmd else None


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in STEPS and sys.argv[1] != 'all':
        print(__doc__); sys.exit(1)
    steps = ORDER if sys.argv[1] == 'all' else [sys.argv[1]]
    for step in steps:
        print(f'\n=== {step} ===', flush=True)
        for cmd in STEPS[step]:
            subprocess.run(cmd, check=True, cwd=cwd_for(cmd))

if __name__ == '__main__':
    main()
