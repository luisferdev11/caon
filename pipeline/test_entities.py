"""Tests de pipeline/entities.py: división de Jardine, comparativos y deduplicación."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import entities as E

OFFICIAL_END = '2025-06-30'


def _m(mid, date, home, hcoach, away, acoach):
    """Partido sintético con el mismo formato que la API v6."""
    return {'match_id': mid, 'match_date': date, 'match_status': 'available',
            'home_team': {'home_team_name': home, 'managers': [{'name': hcoach}]},
            'away_team': {'away_team_name': away, 'managers': [{'name': acoach}]}}


FIXTURE = [
    _m(1, '2021-08-01', 'América', 'Santiago Hernán Solari Poggio', 'Pachuca', 'Jorge Guillermo Almada Álves'),
    _m(2, '2022-04-01', 'América', 'Fernando Ortiz', 'Atlético San Luis', 'André Soares Jardine'),
    _m(3, '2021-09-01', 'Santos Laguna', 'Jorge Guillermo Almada Álves', 'Toluca', 'X'),
    _m(4, '2024-02-01', 'América', 'André Soares Jardine', 'Pachuca', 'Jorge Guillermo Almada Álves'),
    _m(5, '2025-06-30', 'Toluca', 'X', 'América', 'André Soares Jardine'),
    _m(6, '2025-08-01', 'América', 'André Soares Jardine', 'Toluca', 'X'),
    _m(7, '2026-08-01', 'América', 'Jorge Guillermo Almada Álves', 'Pachuca', 'Otro DT'),
    _m(8, '2025-03-01', 'Pachuca', 'Jorge Guillermo Almada Álves, Darwin Ariel Quintana Mestrallet', 'Toluca', 'X'),
]


def _by_id(ents):
    return {e['id']: e for e in ents}


def _mids(e):
    return sorted(x['mid'] for x in e['matches'])


class TestSpecial(unittest.TestCase):
    def test_jardine_first_and_official_window(self):
        first = E.SPECIAL[0]
        self.assertEqual(first[0], 'ame_jardine')
        self.assertEqual((first[4], first[5]), ('2023-07-01', OFFICIAL_END))

    def test_new_entities_present_with_groups(self):
        groups = {s[0]: s[6] for s in E.SPECIAL}
        self.assertEqual(groups['ame_jardine_epi'], 'Epílogo')
        for eid in ('pac_almada', 'ame_ortiz', 'ame_solari', 'slp_jardine', 'san_almada'):
            self.assertEqual(groups[eid], 'Comparación', eid)
        for eid in ('ame_almada', 'gdl_paunovic', 'gdl_gago', 'gdl_milito', 'atl_cocca'):
            self.assertIn(eid, groups)

    def test_ids_unique(self):
        ids = [s[0] for s in E.SPECIAL]
        self.assertEqual(len(ids), len(set(ids)))


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.ents = _by_id(E.build_entities_from(FIXTURE, FIXTURE))

    def test_jardine_split(self):
        self.assertEqual(_mids(self.ents['ame_jardine']), [4, 5])
        self.assertEqual(_mids(self.ents['ame_jardine_epi']), [6])

    def test_comparisons(self):
        self.assertEqual(_mids(self.ents['ame_solari']), [1])
        self.assertEqual(_mids(self.ents['ame_ortiz']), [2])
        self.assertEqual(_mids(self.ents['slp_jardine']), [2])
        self.assertEqual(_mids(self.ents['san_almada']), [3])
        self.assertEqual(_mids(self.ents['pac_almada']), [1, 4, 8])
        self.assertEqual(_mids(self.ents['ame_almada']), [7])

    def test_official_flag_rule(self):
        """build_model marca official = max(fechas) <= 2025-06-30."""
        for eid in ('ame_jardine', 'pac_almada', 'ame_ortiz', 'slp_jardine'):
            dates = [x['date'] for x in self.ents[eid]['matches']]
            self.assertTrue(max(dates) <= OFFICIAL_END, eid)
        self.assertFalse(max(x['date'] for x in self.ents['ame_jardine_epi']['matches']) <= OFFICIAL_END)

    def test_no_duplicate_current_entities(self):
        """América y Pachuca·Almada no deben duplicarse como 'Actual'."""
        ents = E.build_entities_from(FIXTURE, FIXTURE)
        keys = [(e['team'], e['coach_key'].split(',')[0], e['d0']) for e in ents]
        self.assertEqual(len(keys), len(set(keys)))
        actual_teams = [e['team'] for e in ents if e['group'] == 'Actual' and e['id'] not in self.special_ids()]
        self.assertNotIn('América', actual_teams)
        self.assertIn('Toluca', actual_teams)

    def test_current_pachuca_coach_kept(self):
        cur = [e for e in self.ents.values() if e['team'] == 'Pachuca' and e['group'] == 'Actual']
        self.assertEqual([e['coach_key'] for e in cur], ['Otro DT'])

    @staticmethod
    def special_ids():
        return {s[0] for s in E.SPECIAL}


class TestDuplicate(unittest.TestCase):
    def test_is_covered(self):
        special = [{'team': 'Pachuca', 'coach_key': 'Almada', 'd0': '2021-07-01', 'd1': '2025-06-30'}]
        self.assertTrue(E.is_covered('Pachuca', 'Jorge Guillermo Almada Álves', '2024-01-01', special))
        self.assertFalse(E.is_covered('Pachuca', 'Otro DT', '2026-01-01', special))
        self.assertFalse(E.is_covered('Pachuca', 'Jorge Guillermo Almada Álves', '2026-01-01', special))


if __name__ == '__main__':
    unittest.main()
