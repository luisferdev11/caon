"""Tests de extract_analysis: una corrida sobre un caché sintético y el salto de archivos al día."""
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import extract_analysis as ea

FIX = json.loads((HERE / 'fixtures' / 'mini_match_events.json').read_text(encoding='utf-8'))


class ExtractAnalysisTests(unittest.TestCase):
    def test_process_writes_versioned_file_and_skips_up_to_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache, out = pathlib.Path(tmp) / 'cache', pathlib.Path(tmp) / 'out'
            cache.mkdir()
            out.mkdir()
            (cache / 'v8_events_77.json').write_text(json.dumps(FIX['events']), encoding='utf-8')
            self.assertEqual(ea.pending_ids(cache, out, force=False), [77])
            status = ea.process_one(77, cache, out, metadata=FIX['metadata'])
            self.assertEqual(status, 'ok')
            doc = json.loads((out / 'an_77.json').read_text(encoding='utf-8'))
            self.assertEqual(doc['version'], ea.VERSION)
            self.assertEqual(len(doc['possessions']), 4)
            self.assertEqual(ea.pending_ids(cache, out, force=False), [])
            self.assertEqual(ea.pending_ids(cache, out, force=True), [77])


if __name__ == '__main__':
    unittest.main()
