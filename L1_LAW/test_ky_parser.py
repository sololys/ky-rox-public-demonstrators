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
    from micro_engines.ky_parser import (
        KYParser,
        KYEngine,
        KYGrammarEngine,
        SomaticCampaignCandidate,
        WitnessCapsule205B,
        L2PosixPtyLoopbackBridge,
        BalkongLinter,
        UnclosedTrajectoryLeakException,
        CantileverOverloadException,
        evaluate_ky_expression,
        to_ascii,
        from_ascii,
        verify_rox_involution,
        evaluate_plasma_risk,
        D1_ALLOWED_OPERATORS,
        D1_FORBIDDEN_OPERATORS,
        EvalResult,
        Verdict,
    )
except ImportError:
    from ky_parser import (
        KYParser,
        KYEngine,
        KYGrammarEngine,
        SomaticCampaignCandidate,
        WitnessCapsule205B,
        L2PosixPtyLoopbackBridge,
        BalkongLinter,
        UnclosedTrajectoryLeakException,
        CantileverOverloadException,
        evaluate_ky_expression,
        to_ascii,
        from_ascii,
        verify_rox_involution,
        evaluate_plasma_risk,
        D1_ALLOWED_OPERATORS,
        D1_FORBIDDEN_OPERATORS,
        EvalResult,
        Verdict,
    )


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
        self.assertEqual(res_hold.a5_gate_voltage, 2.50)
        self.assertEqual(res_kill.a5_gate_voltage, 0.00)

    def test_04_spec416_205b_capsule_and_kreativ_core_v31_granitum(self):
        """Verifiserer 205-byte vitnekapsel (119B + 86B), D1 bijeksjoner, Nash-resolvent (gamma=0) og kobordisme (d1*d2=0)."""
        self.assertTrue({"ROX", "NOT", "GRAY"}.issubset(D1_ALLOWED_OPERATORS))
        self.assertEqual(D1_ALLOWED_OPERATORS & D1_FORBIDDEN_OPERATORS, frozenset())

        engine = KYGrammarEngine()
        cand_scar = SomaticCampaignCandidate(
            campaign_id="AE-2026-SCAR",
            title="The Geometric Scar",
            classification="BØFF",
            u_raw=100.0,
            c_k=25.0,
            s_irr=10.0,
            r_w=15.0,
            has_material_warrant=True,
            rox_payload=0xCAFEBABE,
            rox_mask_in=0xA5A5A5A5,
            rox_mask_out=0xA5A5A5A5,
            plasma_noise_pi=0.12,
            ky_expression="✓(○ → ∅ → □ → ◇ → ●)#! ▸",
            gamma_nash=0.0,
            cobordism_d1_d2=0.0,
            delta_prov=0.0,
            hangtag_id="KC-ARR-2026-025",
        )
        res_scar = engine.evaluate_kreativ_core_campaign(cand_scar)
        self.assertEqual(res_scar["omega_verdict"], "OPEN")
        self.assertEqual(res_scar["nash_resolvent"], 1.0)
        self.assertEqual(res_scar["capsule_205b_len"], 205)
        self.assertEqual(res_scar["rtl_verdict_code"], 0x01)
        self.assertEqual(res_scar["a5_gate_voltage"], 5.00)

        # Compliance Division sirkulær FARV-felle (d1*d2 != 0 -> 0xFF TRAP_TAMPER)
        cand_farv = SomaticCampaignCandidate(
            campaign_id="AE-2026-SHEEN-FARV",
            title="The Flawless Sheen (Compliance Override)",
            classification="BLØFF",
            u_raw=100.0,
            c_k=25.0,
            s_irr=10.0,
            r_w=15.0,
            has_material_warrant=True,
            rox_payload=0xCAFEBABE,
            rox_mask_in=0xA5A5A5A5,
            rox_mask_out=0xA5A5A5A5,
            plasma_noise_pi=0.12,
            ky_expression="✓(○ → ∅ → □ → ◇ → ●)#! ▸",
            gamma_nash=0.0,
            cobordism_d1_d2=2.0,
            delta_prov=2.0,
            hangtag_id="KC-ARR-2026-025",
        )
        res_farv = engine.evaluate_kreativ_core_campaign(cand_farv)
        self.assertEqual(res_farv["omega_verdict"], "KILL")
        self.assertEqual(res_farv["rtl_verdict_code"], 0xFF)
        self.assertEqual(res_farv["a5_gate_voltage"], 0.00)

    def test_05_v15_master_canonical_test_vectors_and_rtl_verify_o1(self):
        """Verifiserer alle 6 kanoniske KY v1.5-MASTER testvektorer med ↻, 𝒪, ◊, ∥, ▶, ✕ og rtl_verify_o1()."""
        test_vectors = [
            ("↻(○ → ∅ → □) ▶", "OPEN", 5000),
            ("↻(○ ⇒ ∅ → □ → ◊ → 𝒪 ↦ ●)#! ▶", "OPEN", 5000),
            ("↻(□ ~ □↺) ∥", "HOLD", 2500),
            ("(○ → ●) ≠ ✕", "KILL", 0),
            ("(∅ → □) ∉K ✕", "KILL", 0),
            ("↻(□ ↦ ●) ▶", "KILL", 0),
        ]
        for expr_str, expected_gate, expected_mv in test_vectors:
            res = evaluate_ky_expression(expr_str)
            self.assertEqual(res.gate, expected_gate, f"Feil på {expr_str}")
            self.assertEqual(res.voltage_mv, expected_mv)
            if res.capsule_205b is not None:
                rtl_ok, _, msg = res.capsule_205b.rtl_verify_o1()
                self.assertTrue(rtl_ok, msg)
                self.assertEqual(len(res.capsule_205b.raw_205b), 205)

    def test_06_spor2_roundtrip_codec_unicode_ascii_ast(self):
        """Spor 2: Verifiserer toveis konvertering to_ascii(expr) og from_ascii(ky_block) med decode(encode(x)) == x."""
        expr_full = "↻(○ ⇒ ∅ → □ → ◊ → 𝒪 ↦ ●)#! ▶"
        ascii_blk = to_ascii(expr_full)
        self.assertEqual(
            ascii_blk,
            "KY[ validate(raw => estimate -> struct -> viability -> authorized !> committed) audit(hash,commit) gate=open ]",
        )
        self.assertEqual(from_ascii(ascii_blk), expr_full)

        expr_hold = "↻(□ ~ □↺) ∥"
        ascii_hold = to_ascii(expr_hold)
        self.assertEqual(from_ascii(ascii_hold), expr_hold)

        expr_kill = "(∅ → □) ∉K ✕"
        ascii_kill = to_ascii(expr_kill)
        self.assertEqual(from_ascii(ascii_kill), expr_kill)

    def test_07_spor1_l2_posix_pty_serial_loopback_247b_and_rs208(self):
        """Spor 1: Verifiserer 247-byte L2 wire-frame + RS(208,205) over ekte POSIX PTY (/dev/pts/*)."""
        res = evaluate_ky_expression("↻(○ ⇒ ∅ → □ → ◊ → 𝒪 ↦ ●)#! ▶")
        self.assertIsNotNone(res.capsule_205b)
        bridge = L2PosixPtyLoopbackBridge()

        # 1. RS(208,205) paritet over GF(2^8)
        rs_parity = bridge.rs208_compute_parity(res.capsule_205b.raw_205b)
        self.assertEqual(len(rs_parity), 3)
        self.assertTrue(bridge.rs208_verify(res.capsule_205b.raw_205b + rs_parity))

        # 2. Nominell 247-byte pakke over /dev/pts/* -> 5000 mV OPEN
        wire_247b = bridge.pack_247b_wire_frame(seq_counter=1, capsule=res.capsule_205b)
        self.assertEqual(len(wire_247b), 247)
        pty_ok = bridge.transmit_and_verify_over_pty(wire_247b, rs_parity_3b=rs_parity)
        self.assertEqual(pty_ok["status"], "L2_LOOPBACK_SIMULATED_EFFECT")
        self.assertEqual(pty_ok["voltage_mv"], 5000)

        # 3. Enkelt bit-flip i nyttelasten -> KILL_LINK_INTEGRITY (0 mV)
        corrupted = bytearray(wire_247b)
        corrupted[42] ^= 0x01
        pty_flip = bridge.transmit_and_verify_over_pty(bytes(corrupted), rs_parity_3b=rs_parity)
        self.assertEqual(pty_flip["status"], "KILL_LINK_INTEGRITY")
        self.assertEqual(pty_flip["voltage_mv"], 0)

        # 4. Trunkert ramme (< 247 B) -> KILL_TRUNCATED_FRAME (0 mV)
        pty_trunc = bridge.transmit_and_verify_over_pty(wire_247b[:140], timeout_sec=0.02)
        self.assertEqual(pty_trunc["status"], "KILL_TRUNCATED_FRAME")
        self.assertEqual(pty_trunc["voltage_mv"], 0)

    def test_08_spor3_balkong_linter_omveiens_tektonikk(self):
        """Spor 3: Verifiserer BalkongLinter mot lukket digresjon, ufullendt lekkasje og overbelastet balkong."""
        linter = BalkongLinter(max_cantilever_ratio=0.50)
        anchor_prose = " ".join(["granitt"] * 120)

        # 1. Gyldig lukket balkong: [∘Φ-UTFLUKT] -> [⊠SOMA-ANKER] -> [⊙ ≺ 1 // POINCARÉ-LÅS]
        valid_md = (
            f"# Kapittel 1\n{anchor_prose}\n"
            "[∘Φ-UTFLUKT // 0,00 V DC // Rev¹]\n"
            "En kort utflukt til Via Fondazza med [⊠SOMA-ANKER: 5,0 mm kald luft og fastnøkkel].\n"
            "[⊙ ≺ 1 // POINCARÉ-LÅS // 5,00 V DC // ΔR = 0]\n"
        )
        res_ok = linter.lint_text(valid_md, strict_raise=True)
        self.assertTrue(res_ok.passed)
        self.assertEqual(res_ok.gate_verdict, "OPEN")
        self.assertEqual(res_ok.voltage_mv, 5000)

        # 2. Ufullendt lekkasje (mangler POINCARÉ-LÅS før neste kapittel) -> UnclosedTrajectoryLeakException
        leak_md = (
            f"# Kapittel 1\n{anchor_prose}\n"
            "[∘Φ-UTFLUKT // 0,00 V DC // Rev¹]\n"
            "Utflukt med [⊠SOMA-ANKER] som glemmer å lukke låsen.\n"
            "## Kapittel 1.2\nMer tekst.\n"
        )
        with self.assertRaises(UnclosedTrajectoryLeakException):
            linter.lint_text(leak_md, strict_raise=True)

        # 3. Overbelastet balkong (M_boy > Omega_kjerne) -> CantileverOverloadException
        heavy_excursion = " ".join(["digresjon"] * 100)
        overload_md = (
            "# Kort kapittel\nKun ti ord i hovedbjelken her nå.\n"
            f"[∘Φ-UTFLUKT // 0,00 V DC // Rev¹]\n{heavy_excursion} [⊠SOMA-ANKER]\n"
            "[⊙ ≺ 1 // POINCARÉ-LÅS // 5,00 V DC // ΔR = 0]\n"
        )
        with self.assertRaises(CantileverOverloadException):
            linter.lint_text(overload_md, strict_raise=True)


if __name__ == '__main__':
    unittest.main()
