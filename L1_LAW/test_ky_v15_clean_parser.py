#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testmatrise for L1_LAW/ky_v15_clean_parser.py (KY Realization Grammar v1.5, 0 float)."""
from __future__ import annotations

import ast
from fractions import Fraction
from pathlib import Path
import sys
import unittest

ENGINE_DIR = Path(__file__).resolve().parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

import ky_v15_clean_parser as mod  # noqa: E402
from ky_v15_clean_parser import (  # noqa: E402
    KYGate,
    KYV15Engine,
    KYValidity,
    check_d1_operator,
    decode_twos_complement,
    encode_twos_complement,
    evaluate_plasma,
    parse_ky_v15,
    verify_rox_isometry,
)


class TestKYV15CleanParserSuite(unittest.TestCase):
    def test_01_ast_zero_float_in_engine_and_tests(self) -> None:
        forbidden = "flo" + "at"
        for target in (Path(mod.__file__).resolve(), Path(__file__).resolve()):
            tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and type(node.value).__name__ == forbidden:
                    self.fail(f"Flyttallsliteral i {target.name}:{node.lineno}")
                if isinstance(node, ast.Name) and node.id == forbidden:
                    self.fail(f"Flyttallsreferanse i {target.name}:{node.lineno}")

    def test_02_d1_bijective_ops_rox_isometry_and_d12_codec(self) -> None:
        for ok_op in ("ROL", "ROR", "XOR_FROZEN", "NOT", "GRAY", "LFSR_NONSINGULAR"):
            self.assertIs(check_d1_operator(ok_op), KYGate.OPEN)
        for bad_op in ("AND", "OR", "SHL", "SHR"):
            self.assertIs(check_d1_operator(bad_op), KYGate.KILL)

        ok, mark = verify_rox_isometry(0b10110011, 0b01101100, 0xA5, 0xA5)
        self.assertTrue(ok)
        self.assertIs(mark, KYValidity.ROX_OK)

        ok_mut, mark_mut = verify_rox_isometry(0b10110011, 0b01101100, 0xA5, 0x5A)
        self.assertFalse(ok_mut)
        self.assertIs(mark_mut, KYValidity.MASK_MUTATED)

        for v in (-32768, -1, 0, 1, 32767):
            self.assertEqual(decode_twos_complement(encode_twos_complement(v, 16), 16), v)
        with self.assertRaises(OverflowError):
            encode_twos_complement(32768, 16)

    def test_03_exact_rational_plasma_boundaries(self) -> None:
        t_open = Fraction(1, 4)
        t_kill = Fraction(3, 5)
        self.assertIs(evaluate_plasma(Fraction(249, 1000), t_open, t_kill), KYValidity.PLASMA_OPEN)
        self.assertIs(evaluate_plasma(Fraction(1, 4), t_open, t_kill), KYValidity.PLASMA_HOLD)
        self.assertIs(evaluate_plasma(Fraction(599, 1000), t_open, t_kill), KYValidity.PLASMA_HOLD)
        self.assertIs(evaluate_plasma(Fraction(3, 5), t_open, t_kill), KYValidity.PLASMA_KILL)

    def test_04_lossless_unicode_ascii_ast_roundtrip_no_symbol_collision(self) -> None:
        full_ascii = (
            "(RAW -> CANDIDATE -> STRUCT -> VIABILITY => AUTHORIZED !> REALIZED -> WITNESSED) "
            "ROX_OK MASK_FROZEN PLASMA_OPEN ! # OPEN"
        )
        ast1 = parse_ky_v15(full_ascii)
        uni = ast1.to_unicode()
        # Bekreft at WITNESSED = ⊞ og audit = # er helt adskilt
        self.assertIn("⊞", uni)
        self.assertIn("#", uni)
        self.assertEqual(parse_ky_v15(uni), ast1)
        self.assertEqual(parse_ky_v15(uni).to_ascii(), full_ascii)

    def test_05_full_7_layer_chain_stops_at_0mv_without_warrant_and_opens_with_warrant(self) -> None:
        eng = KYV15Engine()
        expr = (
            "(RAW -> CANDIDATE -> STRUCT -> VIABILITY => AUTHORIZED !> REALIZED -> WITNESSED) "
            "ROX_OK MASK_FROZEN PLASMA_OPEN ! # OPEN"
        )
        # Uten PreCommitWarrant + W_ext stanser slusen på tørrkontakt 0 mV HOLD
        res_dry = eng.evaluate(expr)
        self.assertTrue(res_dry.syntax_valid)
        self.assertIs(res_dry.final_verdict, KYGate.HOLD)
        self.assertEqual(res_dry.dry_contact_mv, 0)
        self.assertEqual(res_dry.simulated_latch_mv, 0)

        # Med gyldig PreCommitWarrant forankret til gjeldende chain_head + W_ext -> OPEN (5000 mV L1-simulert)
        warrant = eng.issue_warrant(res_dry.expression_ascii, external_witness_id="marius")
        res_open = eng.evaluate(expr, warrant=warrant)
        self.assertIs(res_open.final_verdict, KYGate.OPEN)
        self.assertEqual(res_open.dry_contact_mv, 0)
        self.assertEqual(res_open.simulated_latch_mv, 5000)

        # Gjenbruk av gammel warrant etter at chain_head har flyttet seg -> KILL
        res_replay = eng.evaluate(expr, warrant=warrant)
        self.assertIs(res_replay.final_verdict, KYGate.KILL)
        self.assertEqual(res_replay.simulated_latch_mv, 0)

    def test_06_all_illegal_shortcuts_reversals_missing_audit_and_worm_claim(self) -> None:
        eng = KYV15Engine()
        bad_cases = [
            "(RAW -> STRUCT) OPEN",                                    # Hopp over D1
            "(RAW -> REALIZED) ! OPEN",                                # Hopp rett til D2
            "(STRUCT -> REALIZED) ! OPEN",                             # Hopp over D1.5 & D2-
            "(REALIZED -> RAW) ! OPEN",                                # Reversering etter D2
            "(KILLED -> RAW) OPEN",                                    # Gjenoppliving fra KILLED
            "(VIABILITY => AUTHORIZED) ROX_OK OPEN",                   # Mangler MASK_FROZEN + PLASMA_OPEN
            "(AUTHORIZED !> REALIZED) OPEN",                           # Mangler `!`
            "(AUTHORIZED !> REALIZED -> WITNESSED) ! OPEN",            # Mangler `#`
            "(VIABILITY ~ VIABILITY) OPEN",                            # Port-avvik (HOLD vs OPEN)
        ]
        for case in bad_cases:
            res = eng.evaluate(case)
            self.assertIs(res.final_verdict, KYGate.KILL, f"Forventet KILL på {case!r}, fikk {res}")
            self.assertEqual(res.simulated_latch_mv, 0)

        # Gyldig pre-D2 HOLD-sløyfe
        hold_res = eng.evaluate("(VIABILITY ~ VIABILITY) PLASMA_HOLD HOLD")
        self.assertIs(hold_res.final_verdict, KYGate.HOLD)
        self.assertEqual(hold_res.simulated_latch_mv, 0)

        # HOLD -> OPEN uten READMIT -> KILL (INVALID_DELAYED_OPEN)
        delayed_bad = eng.evaluate("(RAW -> CANDIDATE) OPEN", prior_state_was_hold=True)
        self.assertIs(delayed_bad.final_verdict, KYGate.KILL)

        # HOLD -> OPEN med eksplisitt READMIT -> OPEN (pre-D2)
        delayed_ok = eng.evaluate("(RAW -> CANDIDATE) READMIT OPEN", prior_state_was_hold=True)
        self.assertIs(delayed_ok.final_verdict, KYGate.OPEN)

        # Hash-kjede alene påstått som fysisk WORM -> KILL
        worm_bad = eng.evaluate("(RAW -> CANDIDATE) OPEN", claims_hash_chain_is_physical_worm=True)
        self.assertIs(worm_bad.final_verdict, KYGate.KILL)


if __name__ == "__main__":
    unittest.main()
