#!/usr/bin/env python3
"""Unit tests (6/6 PASS) for Sosionomos XOR/ROX Consequence Gate v0.1."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from sosionomos_xor_rox_gate import (
    Candidate,
    Decision,
    NodeTemp,
    STATE_BOTH,
    STATE_CANDIDATE,
    STATE_REALIZED,
    STATE_ZERO,
    SosionomosXorRoxGate,
    rox64,
    run_fixture,
    valid_state_xor,
    xor64,
)


class TestSosionomosXorRoxMicrotest(unittest.TestCase):
    def test_01_fixture_all_cases_match(self) -> None:
        out = run_fixture()
        self.assertTrue(out["witness_chain_valid"])
        for row in out["results"]:
            self.assertEqual(row["decision"], row["expected"])

    def test_02_xor_involution_and_rox_non_involution(self) -> None:
        w = 0xDEADBEEFCAFEBABE
        k = 0x0123456789ABCDEF
        self.assertEqual(xor64(xor64(w, k), k), w)
        self.assertNotEqual(rox64(rox64(w, k), k), w)
        self.assertTrue(valid_state_xor(STATE_CANDIDATE))
        self.assertTrue(valid_state_xor(STATE_REALIZED))
        self.assertFalse(valid_state_xor(STATE_ZERO))
        self.assertFalse(valid_state_xor(STATE_BOTH))

    def test_03_mask_mutated_kills_candidate(self) -> None:
        g = SosionomosXorRoxGate()
        g.bootstrap("alice")
        c = Candidate("alice", "bad_phase", g.genesis, 1, 10, 5, 0, mask_out=0x1111, mask_back=0x1112)
        d, info = g.admit(c, 0)
        self.assertEqual(d, Decision.KILL)
        self.assertEqual(info["reason"], "MASK_MUTATED")

    def test_04_hold_allows_revise_without_sequence_lock(self) -> None:
        g = SosionomosXorRoxGate()
        g.bootstrap("alice")
        c_hot = Candidate("alice", "loud", g.genesis, 1, 700, 40, 0)
        d1, _ = g.admit(c_hot, 5)
        self.assertEqual(d1, Decision.HOLD)
        self.assertEqual(g.actors["alice"].seq_last, 0)

        c_calm = Candidate("alice", "calm", g.genesis, 1, 50, 10, 6)
        d2, _ = g.admit(c_calm, 6)
        self.assertEqual(d2, Decision.OPEN)
        self.assertEqual(g.actors["alice"].seq_last, 1)

    def test_05_backpressure_and_cold_anchor_survival(self) -> None:
        g = SosionomosXorRoxGate()
        bot = g.bootstrap("bot", arena_capacity=10)
        bot.used_in = 8
        self.assertEqual(bot.read_permit(), 0)
        bot.used_in = 9
        d_bot, info_bot = g.admit(Candidate("bot", "spam", g.genesis, 1, 10, 5, 0), 0)
        self.assertEqual(d_bot, Decision.TRAP)
        self.assertFalse(info_bot["public"])

        g.bootstrap("alice")
        d1, info1 = g.admit(Candidate("alice", "root", g.genesis, 1, 10, 5, 0), 0)
        self.assertEqual(d1, Decision.OPEN)
        h1 = info1["node_hash"]
        g.cool(h1, NodeTemp.COLD)
        self.assertIsNone(g.public_dag[h1]["payload"])
        d2, _ = g.admit(Candidate("alice", "child", h1, 2, 10, 5, 1), 1)
        self.assertEqual(d2, Decision.OPEN)
        self.assertTrue(g.verify_chain())

    def test_06_zero_float_ast_check(self) -> None:
        src = (Path(__file__).resolve().parent / "sosionomos_xor_rox_gate.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        floats = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)]
        self.assertEqual(floats, [])


if __name__ == "__main__":
    unittest.main()
