from __future__ import annotations

import json
from pathlib import Path
import unittest

from yinyang_binpacking import evaluate_binpacking_candidate


FIXTURE = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))


class YinYangBinPackingMicrotest(unittest.TestCase):
    def test_01_valid_micro_certificate_routes_to_open_with_p_np_hold(self) -> None:
        res = evaluate_binpacking_candidate(FIXTURE)
        self.assertEqual(res.measurement_status, "OPEN")
        self.assertEqual(res.route_directory, "01_OPEN/")
        self.assertEqual(res.p_equals_np_claim_status, "HOLD")
        self.assertEqual(res.claim_status, "HOLD")

    def test_02_incomplete_candidate_routes_to_hold(self) -> None:
        incomplete = dict(FIXTURE, complete_flag=False)
        res = evaluate_binpacking_candidate(incomplete)
        self.assertEqual(res.measurement_status, "HOLD")
        self.assertEqual(res.route_directory, "02_HOLD/")

    def test_03_capacity_breach_routes_to_kill(self) -> None:
        breach = dict(FIXTURE, item_count=3, claimed_total=12)
        res = evaluate_binpacking_candidate(breach)
        self.assertEqual(res.status, "KILL")
        self.assertEqual(res.route_directory, "03_KILL_ARKIV/")

    def test_04_claimed_total_contradiction_routes_to_kill(self) -> None:
        contradiction = dict(FIXTURE, claimed_total=7)
        res = evaluate_binpacking_candidate(contradiction)
        self.assertEqual(res.status, "KILL")
        self.assertEqual(res.route_directory, "03_KILL_ARKIV/")

    def test_05_duplicate_item_routes_to_kill(self) -> None:
        dup = dict(FIXTURE, duplicate_flag=True)
        res = evaluate_binpacking_candidate(dup)
        self.assertEqual(res.status, "KILL")
        self.assertEqual(res.route_directory, "03_KILL_ARKIV/")

    def test_06_witness_hashes_are_distinct_and_authority_is_none(self) -> None:
        res = evaluate_binpacking_candidate(FIXTURE)
        self.assertEqual(len(res.w_pre_hash), 64)
        self.assertEqual(len(res.w_post_hash), 64)
        self.assertNotEqual(res.w_pre_hash, res.w_post_hash)
        self.assertEqual(res.physical_authority, "NONE")


if __name__ == "__main__":
    unittest.main()
