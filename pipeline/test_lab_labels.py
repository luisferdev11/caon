"""lab.html (solo presentación): los nombres de cuadrantes y ejes vienen de /api/framework, no de literales."""
import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import labels

LAB = (pathlib.Path(__file__).resolve().parents[1] / 'frontend' / 'lab.html').read_text(encoding='utf-8')


def maps_block() -> str:
    start = LAB.index('  const MAPS = {')
    return LAB[start:LAB.index('  function renderMap(', start)]


class LabLabelsTest(unittest.TestCase):
    def test_no_literal_quadrant_names(self):
        names = set(labels.QUADRANTS['off'].values()) | set(labels.QUADRANTS['dfn'].values()) | set(labels.DFN_QUALIFIED.values())
        block = maps_block()
        for name in sorted(names):
            self.assertNotIn(name, block, f'nombre de cuadrante escrito a mano en MAPS: {name}')

    def test_maps_read_names_from_framework_labels(self):
        block = maps_block()
        self.assertRegex(block, r'ETIQ\.cuadrantes')
        self.assertRegex(block, r'ETIQ\.ejes')
        self.assertIn("fetch('/api/framework')", LAB)

    def test_axis_literals_gone(self):
        for ax in labels.AXES.values():
            for text in ax:
                self.assertIsNone(re.search(r"(xa|ya):\s*'" + re.escape(text) + "'", maps_block()), text)


if __name__ == '__main__':
    unittest.main()
