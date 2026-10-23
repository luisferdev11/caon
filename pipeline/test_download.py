"""Tests de download_360.py (backoff, trabajos, corrida) y download_all.py (plan por prioridad)."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import download_360 as D
import download_all as A


class HTTPErr(Exception):
    def __init__(self, code):
        super().__init__(f'HTTP {code}')
        self.response = type('R', (), {'status_code': code})()


class TestBackoff(unittest.TestCase):
    def test_retries_on_429_then_ok(self):
        calls, sleeps = [], []

        def getter(path):
            calls.append(path)
            if len(calls) < 3:
                raise HTTPErr(429)
            return {}
        ok, err = D.fetch_with_backoff('v8/events/1', getter, sleeps.append)
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertEqual(sleeps, [2, 4])

    def test_gives_up_after_all_delays(self):
        sleeps = []

        def getter(path):
            raise HTTPErr(503)
        ok, err = D.fetch_with_backoff('p', getter, sleeps.append)
        self.assertFalse(ok)
        self.assertIn('503', err)
        self.assertEqual(sleeps, [2, 4, 8, 16, 32])

    def test_no_retry_on_404(self):
        sleeps = []

        def getter(path):
            raise HTTPErr(404)
        ok, _ = D.fetch_with_backoff('p', getter, sleeps.append)
        self.assertFalse(ok)
        self.assertEqual(sleeps, [])

    def test_retry_on_timeout(self):
        import requests
        n = []

        def getter(path):
            n.append(1)
            if len(n) == 1:
                raise requests.Timeout('t')
            return {}
        ok, _ = D.fetch_with_backoff('p', getter, lambda s: None)
        self.assertTrue(ok)


class TestJobs(unittest.TestCase):
    def test_jobs_for_match_with_and_without_360(self):
        m = {'match_id': 7, 'match_status_360': 'available'}
        self.assertEqual(D.jobs_for_match(m), ['v8/events/7', 'v4/lineups/7', 'v2/360-frames/7'])
        m2 = {'match_id': 8, 'match_status_360': 'unscheduled'}
        self.assertEqual(D.jobs_for_match(m2), ['v8/events/8', 'v4/lineups/8'])
        self.assertEqual(D.jobs_for_match(m, kinds=('360',)), ['v2/360-frames/7'])

    def test_cache_name(self):
        self.assertEqual(D.cache_name('v2/360-frames/7'), 'v2_360-frames_7.json')

    def test_run_jobs_skips_cached_and_records_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = pathlib.Path(tmp)
            (cache / 'v8_events_1.json').write_text('[]')
            got = []

            def getter(path):
                got.append(path)
                if path.endswith('/2'):
                    raise HTTPErr(404)
                return []
            stats = D.run_jobs(['v8/events/1', 'v8/events/2', 'v8/events/3'], getter, cache,
                               threads=2, sleep=lambda s: None)
        self.assertEqual(sorted(got), ['v8/events/2', 'v8/events/3'])
        self.assertEqual(stats['cached'], 1)
        self.assertEqual(stats['ok'], 1)
        self.assertEqual([f['path'] for f in stats['failures']], ['v8/events/2'])


def _m(mid, sid, home, away, date='2024-01-01', s360='available'):
    return {'match_id': mid, 'match_date': date, 'match_status': 'available', 'match_status_360': s360,
            'season': {'season_id': sid},
            'home_team': {'home_team_name': home, 'managers': []},
            'away_team': {'away_team_name': away, 'managers': []}}


class TestPlan(unittest.TestCase):
    def setUp(self):
        self.ms = [_m(1, 235, 'Pachuca', 'Toluca'), _m(2, 281, 'América', 'León'),
                   _m(3, 108, 'Atlético San Luis', 'Atlas'), _m(4, 108, 'Santos Laguna', 'Necaxa')]
        self.ms += [_m(100 + i, 281 if i % 2 else 317, 'Toluca', 'León') for i in range(60)]
        self.ms += [_m(900, 318, 'Toluca', 'León'), _m(901, 351, 'Atlas', 'León')]
        self.ents = [{'id': 'pac_almada', 'matches': [{'mid': 1}]},
                     {'id': 'ame_jardine', 'matches': [{'mid': 2}]},
                     {'id': 'slp_jardine', 'matches': [{'mid': 3}]},
                     {'id': 'san_almada', 'matches': [{'mid': 4}]}]

    def test_neutral_sample_is_fixed_and_neutral(self):
        a = A.neutral_sample(self.ms, 40, 7)
        b = A.neutral_sample(self.ms, 40, 7)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 40)
        self.assertTrue(all(100 <= x < 160 for x in a))

    def test_priority_order(self):
        plan = A.build_plan(self.ents, self.ms, cached_events=set(), seed=7, neutral_n=40)
        pr = {mid: p for p, mid, _ in plan}
        self.assertEqual(pr[1], 1)
        self.assertEqual(pr[2], 1)
        self.assertEqual(pr[3], 2)
        self.assertEqual(pr[4], 4)
        self.assertEqual(pr[900], 6)
        self.assertEqual(pr[901], 6)
        self.assertEqual([p for p, _, _ in plan], sorted(p for p, _, _ in plan))
        self.assertEqual(len({mid for _, mid, _ in plan}), len(plan))

    def test_p3_only_360_and_p4_cached_events_360(self):
        plan = A.build_plan(self.ents, self.ms, cached_events={150}, seed=7, neutral_n=40)
        rows = {mid: (p, kinds) for p, mid, kinds in plan}
        p3 = [mid for mid, (p, _) in rows.items() if p == 3]
        self.assertEqual(len(p3), 40 - (1 if 150 in A.neutral_sample(self.ms, 40, 7) else 0))
        if 150 not in A.neutral_sample(self.ms, 40, 7):
            self.assertEqual(rows[150], (4, ('360',)))

    def test_jobs_from_plan(self):
        plan = [(1, 1, ('events', 'lineups', '360'))]
        jobs = A.plan_jobs(plan, {1: self.ms[0]})
        self.assertEqual(jobs, [(1, 'v8/events/1'), (1, 'v4/lineups/1'), (1, 'v2/360-frames/1')])

    def test_ids_jobs_events_lineups_and_missing(self):
        by = {1: self.ms[0], 100: self.ms[4]}
        jobs = A.ids_jobs([100, 1, 777], by, ('events', 'lineups'))
        self.assertEqual(jobs, ['v8/events/1', 'v4/lineups/1', 'v8/events/100', 'v4/lineups/100'])

    def test_ids_jobs_360_only_where_available(self):
        by = {5: _m(5, 281, 'A', 'B', s360='unscheduled')}
        self.assertEqual(A.ids_jobs([5], by, ('events', '360')), ['v8/events/5'])

    def test_parse_ids_arg(self):
        self.assertEqual(A.parse_ids('3,1, 2'), [1, 2, 3])
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / 'n.json'
            f.write_text(json.dumps({'match_ids': [9, 4]}), encoding='utf-8')
            self.assertEqual(A.parse_ids('@' + str(f)), [4, 9])


class TestCoverage(unittest.TestCase):
    def test_entity_coverage_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache, ext = pathlib.Path(tmp) / 'c', pathlib.Path(tmp) / 'e'
            cache.mkdir()
            ext.mkdir()
            (cache / 'v8_events_1.json').write_text('[]')
            (cache / 'v2_360-frames_1.json').write_text('[]')
            (ext / 'mx_1.json').write_text('{}')
            ents = [{'id': 'x', 'label': 'X', 'matches': [{'mid': 1}, {'mid': 2}]}]
            by_id = {1: {'match_status_360': 'available'}, 2: {'match_status_360': 'available'}}
            rows = A.entity_coverage(ents, by_id, cache, ext)
        self.assertEqual(rows, [{'id': 'x', 'label': 'X', 'matches': 2, 'events': 1, 'lineups': 0,
                                 'avail360': 2, 'f360': 1, 'mx': 1}])
        md = A.coverage_markdown(rows, 'hoy')
        self.assertIn('| x | X | 2 | 1 (50%) | 0 (0%) | 1/2 | 1 (50%) |', md)


class TestStubs(unittest.TestCase):
    def test_stale_stubs_only_invalid_with_missing_cache(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            cache, ext = pathlib.Path(tmp) / 'c', pathlib.Path(tmp) / 'e'
            cache.mkdir()
            ext.mkdir()
            bad = {'status': 'invalid', 'reason': 'FileNotFoundError: x', 'extract_version': 2}
            (ext / 'mx_1.json').write_text(json.dumps(bad))
            (ext / 'mx_2.json').write_text(json.dumps({'status': 'invalid', 'reason': 'OSError: y'}))
            (cache / 'v8_events_2.json').write_text('[]')
            (cache / 'v4_lineups_2.json').write_text('[]')
            (ext / 'mx_3.json').write_text(json.dumps({'extract_version': 2, 'teams': {}}))
            (ext / 'od_4.json').write_text(json.dumps(bad))
            (ext / 'mx_5.json').write_text(json.dumps(bad))
            (cache / 'v8_events_5.json').write_text('[]')
            (cache / 'v4_lineups_5.json').write_text('[]')
            other = {'status': 'invalid', 'reason': 'KeyError: x', 'extract_version': 2}
            (ext / 'mx_6.json').write_text(json.dumps(other))
            (cache / 'v8_events_6.json').write_text('[]')
            (cache / 'v4_lineups_6.json').write_text('[]')
            got = A.stale_stubs(ext, cache)
        self.assertEqual([p.name for p in got], ['mx_1.json', 'mx_5.json'])


if __name__ == '__main__':
    unittest.main()
