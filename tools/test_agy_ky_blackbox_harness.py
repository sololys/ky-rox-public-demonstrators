#!/usr/bin/env python3
"""Unit tests (6/6 PASS, 0 float) for tools/agy_ky_blackbox_harness.py."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from agy_ky_blackbox_harness import run_six_case_experiment


class TestAgyKyBlackboxHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_six_case_experiment()
        cls.by_id = {c["candidate_id"]: c for c in cls.result["cases"]}

    def test_01_normal_valid_with_warrant_opens_and_commits_once(self) -> None:
        c = self.by_id["T1_NORMAL_OPEN"]
        self.assertEqual(c["verdict"], "OPEN")
        self.assertTrue(c["committed"])
        self.assertIsNotNone(c["git_commit_sha"])
        # Exactly 1 net Git commit across all 6 cases
        self.assertEqual(self.result["net_commits_created"], 1)

    def test_02_technically_valid_without_w_ext_is_held(self) -> None:
        c = self.by_id["T2_VALID_NO_WARRANT_HOLD"]
        self.assertEqual(c["verdict"], "HOLD")
        self.assertEqual(c["reason"], "VALID_CANDIDATE_AWAITING_W_EXT")
        self.assertFalse(c["committed"])

    def test_03_contract_breach_and_replay_are_killed(self) -> None:
        c3 = self.by_id["T3_CONTRACT_BREACH_KILL"]
        c4 = self.by_id["T4_REPLAY_KILL"]
        self.assertEqual(c3["verdict"], "KILL")
        self.assertFalse(c3["committed"])
        self.assertEqual(c4["verdict"], "KILL")
        self.assertEqual(c4["reason"], "AUTHORIZATION_REPLAY_DETECTED")
        self.assertFalse(c4["committed"])

    def test_04_incomplete_is_held_and_out_of_scope_is_killed(self) -> None:
        c5 = self.by_id["T5_INCOMPLETE_HOLD"]
        c6 = self.by_id["T6_OUT_OF_SCOPE_KILL"]
        self.assertEqual(c5["verdict"], "HOLD")
        self.assertFalse(c5["committed"])
        self.assertEqual(c6["verdict"], "KILL")
        self.assertEqual(c6["reason"], "OUT_OF_SCOPE_BLAST_RADIUS")
        self.assertFalse(c6["committed"])

    def test_05_witness_chain_valid_and_authority_none(self) -> None:
        wc = self.result["witness_chain_verification"]
        self.assertEqual(wc["verdict"], "PASS")
        self.assertEqual(wc["records"], 6)
        self.assertEqual(wc["witness_authority"], "NONE")
        self.assertEqual(self.result["generator_authority"], "NONE")

    def test_06_zero_float_ast_check(self) -> None:
        src = (Path(__file__).resolve().parent / "agy_ky_blackbox_harness.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        floats = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)]
        self.assertEqual(floats, [])


if __name__ == "__main__":
    unittest.main()
