#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UNIT TESTS: KY PARSER & D3 WORM LEDGER (KY v1.5-MASTER)
========================================================
Status: L1 Kjørende Verifikasjonstest // LOCUS ZERO
Verifiserer:
  - Gyldig OPEN forsegler D3 WORM hash-kjeden
  - Gyldig HOLD (Wandering dynamics) bevarer tilstand uten å forurense ledger
  - Gyldig KILL avviser inadmissible kandidater
  - Anti-Engine beskyttelse (• i Prepare) trigger KILL
  - Ghost Win beskyttelse (Seal etter KILL) trigger KILL
  - Manglende Seal etter OPEN trigger KILL
  - Manglende STRUCT (□) i HOLD trigger KILL
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../ENGINES/micro_engines")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../ENGINES")))

try:
    from micro_engines.ky_parser import KYParser, KYEngine, EvalResult, Verdict
except ImportError:
    from ky_parser import KYParser, KYEngine, EvalResult, Verdict


class TestKYRealizationGrammar(unittest.TestCase):
    """KY v1.0 Master Grammar & Typology Validation Matrix (6 kanoniske tester)."""

    def test_valid_open_expression(self):
        # Gyldig strukturert setning med witness (D0 -> D3)
        parser = KYParser("(○→∅→□→◇→●)#!►")
        result = parser.parse()
        self.assertEqual(result.gate, Verdict.OPEN)
        self.assertEqual(result.syntax, "valid")

    def test_valid_hold_expression(self):
        # Midlertidig hold, strukturen er aktiv men ikke autorisert
        parser = KYParser("(□→◇)॥")
        result = parser.parse()
        self.assertEqual(result.gate, Verdict.HOLD)

    def test_invalid_shortcut(self):
        # Anti-Engine Collapse: Kortslutning fra RAW direkte til COMMITTED
        parser = KYParser("(○→●)#!►")
        result = parser.parse()
        self.assertEqual(result.gate, Verdict.KILL)
        self.assertIn("Type-brudd: Ulovlig overgang i topologien.", result.reasons)

    def test_irreversible_without_audit(self):
        # Forsøk på irreversibel commit uten kryptografisk bevis (WORM/Hash)
        parser = KYParser("(□→◇→●)►")
        result = parser.parse()
        self.assertEqual(result.gate, Verdict.KILL)
        self.assertIn("Audit-brudd: Irreversibel overgang mangler hash (#) eller commit (!).", result.reasons)

    def test_explicit_inadmissibility(self):
        # Kandidat feiler i speil-rommet, merkes som inadmissible
        parser = KYParser("(∅→□)∉KX")
        result = parser.parse()
        self.assertEqual(result.gate, Verdict.KILL)
        self.assertIn("Inadmissible uttrykk korrekt terminert.", result.reasons)

    def test_gate_mismatch(self):
        # Uoverensstemmelse mellom strukturstatus og anmodet dom (Bløff)
        parser = KYParser("(○→∅)►")
        result = parser.parse()
        self.assertEqual(result.gate, Verdict.KILL)
        self.assertIn("Gate-mismatch: Forventet X, funnet ►.", result.reasons[0])



class TestKYParser(unittest.TestCase):
    def setUp(self):
        self.parser = KYParser()

    def test_01_valid_open_with_seal_grows_ledger(self):
        """Tester at gyldig OPEN forsegler D3 WORM hash-kjeden irreversibelt."""
        init_hash = self.parser.ledger_hash
        res = self.parser.parse("✓(○→∅→□⇒♢)►→•#")
        self.assertEqual(res.gate, "OPEN")
        self.assertEqual(res.syntax, "valid")
        self.assertIsNotNone(res.seal_hash)
        self.assertNotEqual(res.seal_hash, init_hash)
        self.assertEqual(self.parser.ledger_hash, res.seal_hash)

    def test_02_valid_kill_inadmissible_candidate(self):
        """Tester at kandidat merket med ∉K korrekt avvises med KILL."""
        init_hash = self.parser.ledger_hash
        res = self.parser.parse("∉K(○→∅→□)X")
        self.assertEqual(res.gate, "KILL")
        self.assertEqual(res.syntax, "valid")
        self.assertEqual(self.parser.ledger_hash, init_hash)

    def test_03_valid_hold_wandering_dynamics(self):
        """Tester at gyldig HOLD med STRUCT bekreftet forblir i beite-sløyfe."""
        init_hash = self.parser.ledger_hash
        res = self.parser.parse("✓(○→∅→□)■")
        self.assertEqual(res.gate, "HOLD")
        self.assertEqual(res.syntax, "valid")
        self.assertEqual(self.parser.ledger_hash, init_hash)

    def test_04_anti_engine_commit_in_prepare_kill(self):
        """Tester at forsøk på commit i prepare avvises som Anti-Engine."""
        res = self.parser.parse("(○→∅→•→□)►→•#")
        self.assertEqual(res.gate, "KILL")
        self.assertIn("ANTI-ENGINE COLLAPSE", res.reason)

    def test_05_ghost_win_seal_after_kill(self):
        """Tester at forsøk på å forsegle konsekvens etter KILL avvises."""
        res = self.parser.parse("(○→∅→□)X→•#")
        self.assertEqual(res.gate, "KILL")
        self.assertIn("GHOST WIN FORSØK", res.reason)

    def test_06_missing_seal_after_open_kill(self):
        """Tester at OPEN uten Seal-fase avvises med WITNESS FEIL."""
        res = self.parser.parse("(○→∅→□→♢)►")
        self.assertEqual(res.gate, "KILL")
        self.assertIn("WITNESS FEIL", res.reason)

    def test_07_missing_struct_in_hold_kill(self):
        """Tester at manglende STRUCT (□) i HOLD avvises med STRUCT FAIL."""
        res = self.parser.parse("(○→∅)■")
        self.assertEqual(res.gate, "KILL")
        self.assertIn("STRUCT FAIL", res.reason)

    # ------------------------------------------------------------------
    # KY v1.0 Formell Spesifikasjon Testmatrise (7 kanoniske tester)
    # ------------------------------------------------------------------
    def test_valid_open(self):
        """Gyldig autorisert uttrykk."""
        res = self.parser.parse("⊨(○→∅→□)►")
        self.assertEqual(res.admissibility, "pass")
        self.assertEqual(res.gate, "OPEN")

    def test_valid_audit_commit(self):
        """Gyldig kommittert uttrykk med audit (#)."""
        res = self.parser.parse("(○→∅→□→♢→⊙→●)#!►")
        self.assertEqual(res.admissibility, "pass")
        self.assertEqual(res.gate, "OPEN")
        self.assertEqual(res.type_status, "valid")

    def test_invalid_transition(self):
        """Kortslutning fra RAW direkte til COMMITTED."""
        res = self.parser.parse("(○→●)X")
        self.assertEqual(res.type_status, "invalid")
        self.assertEqual(res.admissibility, "kill")
        self.assertEqual(res.gate, "KILL")
        self.assertTrue(any("Ulovlig overgang" in r for r in res.reasons))

    def test_missing_audit_on_commit(self):
        """Realisering uten kryptografisk/bevitnet historikk."""
        res = self.parser.parse("(○→∅→□→♢→⊙→●)►")
        self.assertEqual(res.admissibility, "kill")
        self.assertEqual(res.gate, "KILL")
        self.assertTrue(any("mangler audit-markør" in r for r in res.reasons))

    def test_explicit_hold(self):
        """Strukturelt gyldig, men eksplisitt satt på HOLD."""
        res = self.parser.parse("(○→∅→□)■")
        self.assertEqual(res.admissibility, "hold")
        self.assertEqual(res.gate, "HOLD")

    def test_inadmissible_override(self):
        """Inadmissible markør overstyrer og tvinger KILL."""
        res = self.parser.parse("(○→∅→□)∉KX")
        self.assertEqual(res.admissibility, "kill")
        self.assertEqual(res.gate, "KILL")

    def test_gate_mismatch(self):
        """Gyldig indre struktur, men porten sier KILL (fail-closed fallback)."""
        res = self.parser.parse("(○→∅→□)X")
        self.assertEqual(res.admissibility, "kill")
        self.assertEqual(res.gate, "KILL")
        self.assertTrue(any("samsvarer ikke" in r for r in res.reasons))


class TestKYEngineV15Master(unittest.TestCase):
    """
    KY Realization Grammar v1.5-MASTER (Locus 0xABCDEF00):
    Verifiserer Alternativ A (● kun tilstandsnode, aldri suffix, ! er commit-event)
    og D1.2 Codec Roundtrip (decode(encode(x)) == x).
    """

    def test_01_canonical_glyph_string_and_d12_roundtrip(self):
        expr = "✓(○ → ∅ → □ → ◇ → ●)#! ▸"
        res = KYEngine.evaluate_glyph_expr(expr)
        self.assertEqual(res.syntax, "valid")
        self.assertEqual(res.type_check, "valid")
        self.assertEqual(res.admissibility, "pass")
        self.assertEqual(res.gate, "OPEN")
        self.assertTrue(res.roundtrip_ok)
        self.assertEqual(
            res.expression_ascii,
            "validate(raw -> estimate -> struct -> viability -> committed)#! OPEN",
        )
        self.assertEqual(KYEngine.from_ascii(res.expression_ascii), expr)

    def test_02_semantic_dual_role_eliminated_bullet_in_suffix_rejected(self):
        """Alternativ A: ● i suffikset skal avvises momentant med syntax=invalid og KILL."""
        bad_expr = "✓(○ → ∅ → □ → ◇ → ●)#● ▸"
        res = KYEngine.evaluate_glyph_expr(bad_expr)
        self.assertEqual(res.syntax, "invalid")
        self.assertEqual(res.gate, "KILL")
        self.assertFalse(res.roundtrip_ok)
        self.assertTrue(any("Illegal suffix symbol '●'" in r for r in res.reasons))

        # Også i KYParser v1.0:
        res_v10 = KYParser("(○→∅→□→◇→●)#●►").parse()
        self.assertEqual(res_v10.gate, Verdict.KILL)
        self.assertEqual(res_v10.syntax, "invalid")

    def test_03_hold_and_kill_roundtrip(self):
        hold_expr = "(□ ~ □) ⏸"
        res_hold = KYEngine.evaluate_glyph_expr(hold_expr)
        self.assertEqual(res_hold.gate, "HOLD")
        self.assertEqual(res_hold.admissibility, "hold")
        self.assertTrue(res_hold.roundtrip_ok)

        kill_expr = "(○ → ∅ → □)∉K ✕"
        res_kill = KYEngine.evaluate_glyph_expr(kill_expr)
        self.assertEqual(res_kill.gate, "KILL")
        self.assertEqual(res_kill.admissibility, "kill")
        self.assertTrue(res_kill.roundtrip_ok)


if __name__ == '__main__':
    unittest.main()
