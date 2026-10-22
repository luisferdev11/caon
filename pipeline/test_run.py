"""Tests de run.py: el orden de los pasos del pipeline."""
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run


def names(cmds: list) -> list:
    """Nombre corto de cada comando: archivo .py o módulo de -m."""
    out = []
    for c in cmds:
        out.append(c[c.index('-m') + 1] if '-m' in c else pathlib.Path(c[-1]).name)
    return out


class TestSteps(unittest.TestCase):
    def test_analysis_is_steps_4_to_9(self):
        self.assertEqual(names(run.STEPS['analysis']),
                         ['analytics.shape360_ref', 'analytics.a4_reference', 'build_model.py', 'check_model.py',
                          'targets.py', 'build_analysis.py', 'kpis.py', 'story.py', 'audit_coherence.py'])

    def test_build_is_extract_then_analysis(self):
        self.assertEqual(names(run.STEPS['build']),
                         ['extract.py', 'extract_analysis.py', 'extract_360.py'] + names(run.STEPS['analysis']))

    def test_all_does_not_repeat_extract(self):
        self.assertEqual(run.ORDER, ['download', 'build', 'validate', 'referee'])

    def test_module_commands_run_from_pipeline_dir(self):
        mod = [c for c in run.STEPS['analysis'] if '-m' in c]
        self.assertTrue(mod and all(run.cwd_for(c) == run.HERE for c in mod))
        self.assertIsNone(run.cwd_for(run.STEPS['extract'][0]))


class TestIsolatedStart(unittest.TestCase):
    """run.py arranca los scripts con -I (sin el directorio del script en sys.path): deben poder importar sus módulos."""

    def test_extract_analysis_starts_in_isolated_mode(self):
        cmd = next(c for c in run.STEPS['extract'] if c[-1].endswith('extract_analysis.py')) + ['--help']
        done = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr[-300:])


if __name__ == '__main__':
    unittest.main()
