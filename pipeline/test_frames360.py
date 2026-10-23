"""Tests de la biblioteca 360 (frames360.py) y del extractor por partido (extract_360.py)."""
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import frames360 as f3

FIX = HERE / 'fixtures'


def pl(x, y, teammate=True, actor=False, keeper=False):
    """Jugador de freeze_frame sintético."""
    return {'teammate': teammate, 'actor': actor, 'keeper': keeper, 'location': [x, y]}


FULL = [0.0, 0.0, 120.0, 0.0, 120.0, 80.0, 0.0, 80.0, 0.0, 0.0]


class GeometryTests(unittest.TestCase):
    def test_point_in_polygon_square(self):
        sq = f3.polygon_from_flat([0, 0, 10, 0, 10, 10, 0, 10, 0, 0])
        self.assertTrue(f3.point_in_polygon((5, 5), sq))
        self.assertFalse(f3.point_in_polygon((15, 5), sq))
        self.assertFalse(f3.point_in_polygon((5, -1), sq))

    def test_point_in_polygon_triangle(self):
        tri = f3.polygon_from_flat([0, 0, 10, 0, 0, 10])
        self.assertTrue(f3.point_in_polygon((2, 2), tri))
        self.assertFalse(f3.point_in_polygon((8, 8), tri))

    def test_roi_fraction_half_visible(self):
        half = f3.polygon_from_flat([0, 0, 60, 0, 60, 80, 0, 80])
        self.assertAlmostEqual(f3.roi_visible_fraction(half, (40, 0, 80, 80)), 0.5, places=6)
        self.assertEqual(f3.roi_visible_fraction(half, (0, 0, 60, 80)), 1.0)
        self.assertEqual(f3.roi_visible_fraction(half, (70, 0, 120, 80)), 0.0)

    def test_roi_fraction_degenerate_rect_is_zero(self):
        self.assertEqual(f3.roi_visible_fraction(f3.polygon_from_flat(FULL), (30, 0, 30, 80)), 0.0)
        self.assertEqual(f3.roi_visible_fraction([], (0, 0, 10, 10)), 0.0)

    def test_convex_hull_and_area(self):
        pts = [(0, 0), (4, 0), (4, 3), (0, 3), (2, 1), (1, 2)]
        hull = f3.convex_hull(pts)
        self.assertEqual(len(hull), 4)
        self.assertAlmostEqual(f3.polygon_area(hull), 12.0)
        self.assertEqual(f3.polygon_area(f3.convex_hull([(0, 0), (1, 1)])), 0.0)

    def test_deepest_line_and_goal_side(self):
        pts = [(10, 0), (20, 0), (30, 0), (50, 0), (70, 0)]
        self.assertAlmostEqual(f3.deepest_line(pts), 20.0)
        self.assertIsNone(f3.deepest_line(pts[:2]))
        self.assertEqual(f3.goal_side(pts, 40), 3)


class ViewTests(unittest.TestCase):
    def frame(self):
        return {'visible_area': [0, 0, 60, 0, 60, 80, 0, 80, 0, 0],
                'freeze_frame': [pl(30, 20, actor=True), pl(5, 40, keeper=True),
                                 pl(50, 60, teammate=False), pl(115, 40, teammate=False, keeper=True)]}

    def test_view_actor_perspective_keeps_coords(self):
        v = f3.view(self.frame(), team_is_actor=True)
        self.assertEqual(v['actor'], (30.0, 20.0))
        self.assertEqual(v['own'], [(30.0, 20.0)])
        self.assertEqual(v['own_gk'], [(5.0, 40.0)])
        self.assertEqual(v['opp'], [(50.0, 60.0)])

    def test_view_other_perspective_flips_everything(self):
        v = f3.view(self.frame(), team_is_actor=False)
        self.assertEqual(v['own'], [(70.0, 20.0)])
        self.assertEqual(v['own_gk'], [(5.0, 40.0)])
        self.assertEqual(v['opp'], [(90.0, 60.0)])
        self.assertEqual(v['actor'], (90.0, 60.0))
        self.assertTrue(f3.point_in_polygon((100, 10), v['poly']))
        self.assertFalse(f3.point_in_polygon((10, 10), v['poly']))


def full_view(own, opp, actor=None):
    """Vista ya normalizada con todo el campo visible."""
    return {'own': own, 'opp': opp, 'own_gk': [], 'opp_gk': [], 'actor': actor,
            'poly': f3.polygon_from_flat(FULL)}


class MetricTests(unittest.TestCase):
    def test_rest_defense_counts(self):
        own = [(10, 40), (20, 30), (25, 70), (60, 40), (80, 40)]
        opp = [(30, 40), (50, 10), (70, 40)]
        r = f3.rest_defense(full_view(own, opp), (40, 40))
        self.assertEqual(r['own_goal_side'], 3)
        self.assertEqual(r['own_central'], 2)
        self.assertEqual(r['opp_ahead'], 1)
        self.assertEqual(r['superiority'], 2)
        self.assertTrue(r['valid'])

    def test_rest_defense_invalid_when_roi_hidden(self):
        v = full_view([(10, 40)], [])
        v['poly'] = f3.polygon_from_flat([60, 0, 120, 0, 120, 80, 60, 80])
        self.assertFalse(f3.rest_defense(v, (50, 40))['valid'])

    def test_error_context(self):
        own = [(50, 40), (55, 45), (80, 10)]
        opp = [(52, 41), (54, 38), (70, 40)]
        r = f3.error_context(full_view(own, opp, actor=(50, 40)), (50, 40))
        self.assertEqual(r['teammates_near'], 1)
        self.assertEqual(r['opps_near'], 2)
        self.assertEqual(r['opps_pressing'], 1)
        self.assertAlmostEqual(r['nearest_opp'], 2.24, places=2)
        self.assertFalse(r['isolated'])
        lone = f3.error_context(full_view([(50, 40)], opp), (50, 40))
        self.assertTrue(lone['isolated'])

    def test_block_shape_requires_seven_visible(self):
        own = [(20, 10), (22, 30), (21, 50), (19, 70), (40, 20), (42, 60), (60, 40)]
        r = f3.block_shape(full_view(own, []), (70, 40))
        self.assertTrue(r['valid'])
        self.assertAlmostEqual(r['last_line'], 20.0)
        self.assertAlmostEqual(r['length'], 41.0)
        self.assertAlmostEqual(r['width'], 60.0)
        self.assertGreater(r['hull_area'], 0)
        self.assertEqual(r['between'], 7)
        self.assertFalse(f3.block_shape(full_view(own[:6], []), (70, 40))['valid'])

    def test_block_gate_uses_ball_centred_window(self):
        """Basta con ver la ventana alrededor del balón (la cámara rara vez muestra todo el ancho)."""
        own = [(50, 30), (52, 40), (51, 50), (49, 60), (60, 35), (62, 45), (68, 40)]
        v = full_view(own, [])
        v['poly'] = f3.polygon_from_flat([40, 10, 90, 10, 90, 70, 40, 70])
        self.assertTrue(f3.block_shape(v, (70, 40))['valid'])
        self.assertFalse(f3.block_shape(v, (70, 5))['valid'])

    def test_line_height(self):
        own = [(25, 10), (30, 30), (35, 50), (28, 70), (45, 20), (50, 60), (70, 40)]
        r = f3.line_height(full_view(own, []), (30, 30))
        self.assertAlmostEqual(r['height'], (25 + 28 + 30) / 3)
        self.assertTrue(r['valid'])

    def test_packing_lower_bound(self):
        opp = [(45, 40), (55, 20), (65, 40), (90, 40)]
        r = f3.packing(full_view([], opp), (40, 40), (70, 40))
        self.assertEqual(r['bypassed'], 3)
        self.assertEqual(f3.packing(full_view([], opp), (40, 40), (35, 40))['bypassed'], 0)

    def test_coordinated_pressure(self):
        own = [(60, 40), (65, 45), (75, 40)]
        opp = [(61, 40), (70, 30), (64, 46), (90, 10)]
        r = f3.coordinated_pressure(full_view(own, opp, actor=(60, 40)), (60, 40))
        self.assertEqual(r['support'], 2)
        self.assertEqual(r['free_options'], 1)
        self.assertTrue(r['valid'])

    def test_corner_organization_man_marking(self):
        own = [(5, 35), (8, 45), (10, 30), (12, 50), (3, 40)]
        opp = [(5.5, 35.5), (8.5, 45), (10, 31), (12, 50.5)]
        r = f3.corner_organization(full_view(own, opp), (120 - 120, 80 - 0.5))
        self.assertEqual(r['def_box'], 5)
        self.assertEqual(r['att_box'], 4)
        self.assertAlmostEqual(r['pairing'], 1.0)
        self.assertEqual(r['marking'], 'al hombre')
        zonal = f3.corner_organization(full_view([(3, 32), (3, 38), (3, 44), (3, 48)], opp), (0, 79.5))
        self.assertEqual(zonal['marking'], 'zonal')

    def test_classify_error(self):
        self.assertEqual(f3.classify_error('duelo', None, False, False, 0), 'duelo_perdido')
        self.assertEqual(f3.classify_error('pase', 0.9, True, False, 0), 'bajo_presion')
        self.assertEqual(f3.classify_error('pase', 0.9, False, False, 1), 'bajo_presion')
        self.assertEqual(f3.classify_error('pase', 0.9, False, False, 0), 'no_forzado')
        self.assertEqual(f3.classify_error('pase', 0.3, False, True, 0), 'decision_arriesgada')
        self.assertEqual(f3.classify_error('pase', 0.6, False, False, None), 'otro')

    def test_compact_points(self):
        v = full_view([(1.234, 2)], [(3, 4)], actor=(1.234, 2))
        v['own_gk'] = [(0.5, 40)]
        self.assertEqual(f3.compact_points(v), [[1.2, 2.0, 4], [3.0, 4.0, 1], [0.5, 40.0, 2]])


def load_fixture():
    with open(FIX / 'frames360_match.json', encoding='utf-8') as fh:
        return json.load(fh)


class ExtractTests(unittest.TestCase):
    def test_extract_fixture_tables(self):
        import extract_360 as x3
        fx = load_fixture()
        out = x3.extract_match(fx['mid'], fx['events'], fx['frames'])
        self.assertEqual(out['version'], x3.VERSION)
        self.assertEqual(sorted(out['teams']), [10, 20])
        self.assertEqual(out['n_linked'], len(fx['frames']))
        loss = x3.rows_as_dicts(out['tables']['perdidas'])
        self.assertEqual(len(loss), 1)
        self.assertEqual(loss[0]['team'], 10)
        self.assertEqual(loss[0]['tipo'], 'bajo_presion')
        self.assertEqual(loss[0]['shot15'], 1)
        self.assertEqual(loss[0]['vig_gs'], 2)
        gk = x3.rows_as_dicts(out['tables']['saque_meta'])
        self.assertEqual(gk[0]['team'], 20)
        self.assertGreater(gk[0]['kick_mean_x'], 60)
        self.assertEqual(len(out['snapshots']), 1)
        cov = out['coverage']['perdidas']['10']
        self.assertEqual(cov['rows'], 1)

    def test_output_is_strict_json(self):
        import extract_360 as x3
        fx = load_fixture()
        out = x3.extract_match(fx['mid'], fx['events'], fx['frames'])
        json.dumps(out, ensure_ascii=False, allow_nan=False)

    def test_up_to_date_skip(self):
        import extract_360 as x3
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            src = p / 'a.json'
            src.write_text('[]', encoding='utf-8')
            out = p / 'f360_1.json'
            self.assertFalse(x3.is_up_to_date(out, [src]))
            out.write_text(json.dumps({'version': x3.VERSION}), encoding='utf-8')
            self.assertTrue(x3.is_up_to_date(out, [src]))
            out.write_text(json.dumps({'version': -1}), encoding='utf-8')
            self.assertFalse(x3.is_up_to_date(out, [src]))


REAL_MID = 3799357
REAL = HERE.parent / 'data' / 'cache'


@unittest.skipUnless((REAL / f'v2_360-frames_{REAL_MID}.json').exists(), 'sin caché 360 real')
class RealDataSanityTests(unittest.TestCase):
    def test_goal_kick_orientation(self):
        """En el marco del equipo que defiende, el equipo que saca de meta está en x media > 60."""
        import extract_360 as x3
        ev = json.loads((REAL / f'v8_events_{REAL_MID}.json').read_text(encoding='utf-8'))
        fr = json.loads((REAL / f'v2_360-frames_{REAL_MID}.json').read_text(encoding='utf-8'))
        out = x3.extract_match(REAL_MID, ev, fr)
        gk = [r['kick_mean_x'] for r in x3.rows_as_dicts(out['tables']['saque_meta']) if r['kick_mean_x']]
        self.assertGreaterEqual(len(gk), 3)
        self.assertGreater(sum(gk) / len(gk), 60)
        self.assertEqual(out['n_linked'], out['n_frames'])


if __name__ == '__main__':
    unittest.main()
