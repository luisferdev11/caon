"""T-03.10: ids nuevos en DEFINITIONS y constantes de analytics con un solo origen (framework.py)."""
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import explorer
import framework as fw
from analytics import (
    a4_facts,
    a4_reference,
    context,
    dangerous,
    dangerous_detail,
    match_xg,
    offense,
    replay,
    setpieces,
    transitions,
    usage,
    usage_subs,
)

NEW_IDS = ('puntos', 'xg_dif', 'salida_portero', 'xg_origen', 'rec_tiro')
ALIASES = (
    (replay, 'REPLAY_DRAWS', 'REPLAY_DRAWS'), (replay, 'DESERVED_P', 'DESERVED_P'), (replay, 'BALANCE_PTS', 'BALANCE_PTS'),
    (replay, 'EPILOGUE_END', 'EPILOGUE_END'), (match_xg, 'BIG_CHANCE_XG', 'BIG_CHANCE_XG'),
    (a4_reference, 'REF_MIN_MATCHES', 'REF_MIN_MATCHES'), (explorer, 'REF_MIN_MATCHES', 'REF_MIN_MATCHES'),
    (a4_facts, 'LONG_PASS_YD', 'LONG_PASS_YD'), (dangerous, 'TOP_N', 'DANGEROUS_TOP_N'),
    (dangerous, 'PAYLOAD_MAX_BYTES', 'DANGEROUS_PAYLOAD_MAX_BYTES'), (dangerous_detail, 'MAX_ACTIONS', 'DANGEROUS_MAX_ACTIONS'),
    (offense, 'TOP_PROGRESSORS', 'PROGRESSORS_TOP'), (transitions, 'TOP_PLAYERS', 'LOSS_PLAYERS_TOP'),
    (setpieces, 'SHORT_CORNER_YD', 'SHORT_CORNER_YD'), (setpieces, 'CONTACT_SCAN_EVENTS', 'CONTACT_SCAN_EVENTS'),
    (setpieces, 'TOP_N', 'SETPIECES_TOP_N'), (context, 'BOOT_DRAWS', 'BOOT_DRAWS'), (context, 'REGULAR_STAGES', 'REGULAR_STAGES'),
    (context, 'CONSISTENCY_MIN_INSIDE', 'CONSISTENCY_MIN_INSIDE'), (context, 'CONSISTENCY_MIN_MATCHES', 'CONSISTENCY_MIN_MATCHES'),
    (context, 'FINDINGS_TOP', 'FINDINGS_TOP'), (usage, 'XI_SIZE', 'XI_SIZE'), (usage, 'SQUAD_TOP', 'SQUAD_TOP'),
    (usage_subs, 'HALFTIME_MINUTE', 'HALFTIME_MINUTE'),
)


class ConstantsTest(unittest.TestCase):
    def test_new_ids_are_defined_and_valid(self):
        for key in NEW_IDS:
            self.assertIn(key, fw.DEFINITIONS)
            d = fw.DEFINITIONS[key]
            self.assertTrue(all(d.get(k) for k in ('nombre', 'definicion', 'formula', 'unidad', 'limites', 'fuente')), key)

    def test_modules_take_their_constants_from_the_framework(self):
        for module, local, name in ALIASES:
            self.assertEqual(getattr(module, local), getattr(fw, name), f'{module.__name__}.{local}')

    def test_one_reference_threshold(self):
        self.assertEqual(fw.REF_MIN_MATCHES, fw.CONSISTENCY_MIN_MATCHES)
        self.assertEqual(fw.REF_MIN_MATCHES, fw.TIER_MIN_MATCHES)

    def test_context_publishes_points_and_xg_diff_as_contract_records(self):
        for key in ('puntos', 'xg_dif'):
            self.assertEqual(context.METRIC_META[key][0], key)
        rec = context._record('puntos', 1.5, 10, 'oficial', 'ame_jardine')
        self.assertEqual(rec['id'], 'puntos')
        self.assertEqual(fw.check_metric_record(rec), [])
        self.assertNotIn('id_pendiente', rec)


if __name__ == '__main__':
    unittest.main()
