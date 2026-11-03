#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhetstester for Registry B (HOLD -> L3 HIL) D-Latch Telemetry Protocol (0xABCDEF00).
"""

import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../ENGINES/micro_engines")))

from registry_b_dlatch_telemetry_protocol import (
    PhysicalADCSample,
    RegistryBDLatchTelemetryVerifier,
)


class TestRegistryBDLatchTelemetryProtocol(unittest.TestCase):

    def setUp(self) -> None:
        self.verifier = RegistryBDLatchTelemetryVerifier()
        self.ky_ascii = "validate(raw -> estimate -> struct -> viability -> committed)#! OPEN"
        self.w_pre_hash = hashlib.sha256(b"W_PRE_ANCHOR_0xABCDEF00").digest()

    def test_01_missing_adc_telemetry_stays_in_registry_b_hold(self) -> None:
        """Uten fysisk ADC-telemetri er tilstanden låst i REGISTRY_B_HOLD (OPEN_AS_SOFTWARE_DEMONSTRATION)."""
        verdict = self.verifier.evaluate_telemetry(
            seq_c_hw=1,
            commanded_gate="OPEN",
            ky_canonical_ascii=self.ky_ascii,
            w_pre_hash=self.w_pre_hash,
            adc_sample=None,
        )
        self.assertEqual(verdict.registry_b_status, "HOLD_SOFTWARE_DEMO_ONLY")
        self.assertEqual(verdict.claim_classification, "OPEN_AS_SOFTWARE_DEMONSTRATION")
        self.assertIsNone(verdict.rosetta_envelope_208b)

    def test_02_valid_open_adc_sample_resolves_registry_b_and_seals_208b_envelope(self) -> None:
        """Gyldig fysisk 5.00V / 4.98mA måling i kausal tidsorden løser ut Registry B og forsegler 208B Rosetta-konvolutt."""
        sample = PhysicalADCSample(
            t_w_pre_ns=1_000_000,
            t_clk_edge_ns=1_000_500,
            t_adc_sample_ns=1_001_500,
            t_w_post_ns=1_002_000,
            v_pre_rest_mv=12,
            v_q_measured_mv=4985,
            v_post_reset_mv=10,
            i_shunt_ua=4985,
            r_crowbar_mohm=0,
            e_snubber_nj=0,
        )
        verdict = self.verifier.evaluate_telemetry(
            seq_c_hw=1,
            commanded_gate="OPEN",
            ky_canonical_ascii=self.ky_ascii,
            w_pre_hash=self.w_pre_hash,
            adc_sample=sample,
        )
        self.assertEqual(verdict.registry_b_status, "OPEN_L3_SILICON_WITNESSED")
        self.assertEqual(verdict.claim_classification, "L3_SILICON_D_LATCH_WITNESSED")
        self.assertEqual(verdict.impedance_verified, "ACTIVE_LOAD")
        self.assertIsNotNone(verdict.rosetta_envelope_208b)
        self.assertEqual(len(verdict.rosetta_envelope_208b), 208)

    def test_03_interlock_mismatch_commanded_open_but_measured_0v(self) -> None:
        """Kommandert OPEN (5000 mV), men fysisk målt 15 mV -> KILL_INTERLOCK_MISMATCH."""
        sample = PhysicalADCSample(
            t_w_pre_ns=1_000_000,
            t_clk_edge_ns=1_000_500,
            t_adc_sample_ns=1_001_500,
            t_w_post_ns=1_002_000,
            v_pre_rest_mv=10,
            v_q_measured_mv=15,
            v_post_reset_mv=10,
            i_shunt_ua=0,
            r_crowbar_mohm=0,
            e_snubber_nj=0,
        )
        verdict = self.verifier.evaluate_telemetry(
            seq_c_hw=1,
            commanded_gate="OPEN",
            ky_canonical_ascii=self.ky_ascii,
            w_pre_hash=self.w_pre_hash,
            adc_sample=sample,
        )
        self.assertEqual(verdict.registry_b_status, "KILL_INTERLOCK_MISMATCH")
        self.assertEqual(verdict.claim_classification, "FAIL_CLOSED_KILL")

    def test_04_floating_pin_zero_shunt_current_rejected(self) -> None:
        """Åpen/flytende pin med 5000 mV men uten reell laststrøm (2 uA < 500 uA) -> KILL_IMPEDANCE_FAULT."""
        sample = PhysicalADCSample(
            t_w_pre_ns=1_000_000,
            t_clk_edge_ns=1_000_500,
            t_adc_sample_ns=1_001_500,
            t_w_post_ns=1_002_000,
            v_pre_rest_mv=10,
            v_q_measured_mv=5000,
            v_post_reset_mv=10,
            i_shunt_ua=2,
            r_crowbar_mohm=0,
            e_snubber_nj=0,
        )
        verdict = self.verifier.evaluate_telemetry(
            seq_c_hw=1,
            commanded_gate="OPEN",
            ky_canonical_ascii=self.ky_ascii,
            w_pre_hash=self.w_pre_hash,
            adc_sample=sample,
        )
        self.assertEqual(verdict.registry_b_status, "KILL_IMPEDANCE_FAULT")

    def test_05_causal_timing_violation_adc_before_clock(self) -> None:
        """ADC-måling tatt før klokke-flanke (t_adc < t_clk) -> KILL_CAUSAL_TIMING."""
        sample = PhysicalADCSample(
            t_w_pre_ns=1_000_000,
            t_clk_edge_ns=1_001_500,
            t_adc_sample_ns=1_000_500,
            t_w_post_ns=1_002_000,
            v_pre_rest_mv=10,
            v_q_measured_mv=5000,
            v_post_reset_mv=10,
            i_shunt_ua=5000,
            r_crowbar_mohm=0,
            e_snubber_nj=0,
        )
        verdict = self.verifier.evaluate_telemetry(
            seq_c_hw=1,
            commanded_gate="OPEN",
            ky_canonical_ascii=self.ky_ascii,
            w_pre_hash=self.w_pre_hash,
            adc_sample=sample,
        )
        self.assertEqual(verdict.registry_b_status, "KILL_CAUSAL_TIMING")

    def test_06_kill_crowbar_and_landauer_snubber_verification(self) -> None:
        """KILL krever 0.00V (<= 50 mV), R_crowbar <= 10 Ohm og E_snubber > 0 nJ."""
        valid_kill_sample = PhysicalADCSample(
            t_w_pre_ns=2_000_000,
            t_clk_edge_ns=2_000_500,
            t_adc_sample_ns=2_001_500,
            t_w_post_ns=2_002_000,
            v_pre_rest_mv=10,
            v_q_measured_mv=8,
            v_post_reset_mv=8,
            i_shunt_ua=0,
            r_crowbar_mohm=1200,
            e_snubber_nj=450,
        )
        v_ok = self.verifier.evaluate_telemetry(
            seq_c_hw=1,
            commanded_gate="KILL",
            ky_canonical_ascii="chain(raw -> estimate -> struct)[∉K] KILL",
            w_pre_hash=self.w_pre_hash,
            adc_sample=valid_kill_sample,
        )
        self.assertEqual(v_ok.registry_b_status, "OPEN_L3_SILICON_WITNESSED")
        self.assertEqual(v_ok.impedance_verified, "LOW_Z_CROWBAR")

        # KILL uten snubber-energi (E_snubber = 0) avvises
        zero_energy_sample = PhysicalADCSample(
            t_w_pre_ns=3_000_000,
            t_clk_edge_ns=3_000_500,
            t_adc_sample_ns=3_001_500,
            t_w_post_ns=3_002_000,
            v_pre_rest_mv=10,
            v_q_measured_mv=8,
            v_post_reset_mv=8,
            i_shunt_ua=0,
            r_crowbar_mohm=1200,
            e_snubber_nj=0,
        )
        v_bad = self.verifier.evaluate_telemetry(
            seq_c_hw=2,
            commanded_gate="KILL",
            ky_canonical_ascii="chain(raw -> estimate -> struct)[∉K] KILL",
            w_pre_hash=self.w_pre_hash,
            adc_sample=zero_energy_sample,
        )
        self.assertEqual(v_bad.registry_b_status, "KILL_IMPEDANCE_FAULT")

    def test_07_monotonic_counter_replay_rejected(self) -> None:
        """Gjenbruk av seq_c_hw <= committed_c_hw avvises deterministisk."""
        sample = PhysicalADCSample(
            t_w_pre_ns=1_000_000,
            t_clk_edge_ns=1_000_500,
            t_adc_sample_ns=1_001_500,
            t_w_post_ns=1_002_000,
            v_pre_rest_mv=12,
            v_q_measured_mv=4985,
            v_post_reset_mv=10,
            i_shunt_ua=4985,
            r_crowbar_mohm=0,
            e_snubber_nj=0,
        )
        self.verifier.evaluate_telemetry(
            seq_c_hw=5,
            commanded_gate="OPEN",
            ky_canonical_ascii=self.ky_ascii,
            w_pre_hash=self.w_pre_hash,
            adc_sample=sample,
        )
        replay = self.verifier.evaluate_telemetry(
            seq_c_hw=5,
            commanded_gate="OPEN",
            ky_canonical_ascii=self.ky_ascii,
            w_pre_hash=self.w_pre_hash,
            adc_sample=sample,
        )
        self.assertEqual(replay.registry_b_status, "KILL_INTERLOCK_MISMATCH")


if __name__ == "__main__":
    unittest.main()
