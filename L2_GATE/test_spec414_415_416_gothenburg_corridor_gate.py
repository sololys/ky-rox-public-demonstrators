#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhetstester og L1.5 SystemVerilog (iverilog/vvp) Co-Simulering for:
  - SPEC-414 (77 GHz ISAC Kinematic Radar & Phase Cone Gate)
  - SPEC-415 (-240m Benthic K-POD 5-CDC & Acoustic Interlock Gate)
  - SPEC-416 (Infranett Causal Witness W_pre -> W_post & Microgrid/Fiber Gate)
"""

from fractions import Fraction
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../ENGINES/micro_engines")))

from spec414_415_416_gothenburg_corridor_gate import (
    CANONICAL_ASCII,
    CANONICAL_GLYPH,
    KYGrammarGate,
    REG_HOLD,
    REG_KILL,
    REG_PASS,
    STATE_ANCHOR_MAGIC,
    Spec414IsacGate,
    Spec414Telemetry,
    Spec415KpodGate,
    Spec415Telemetry,
    Spec416InfranettGate,
    Spec416InfranettTelemetry,
    pack_205b_hardware_capsule,
    pack_208b_rosetta_d3,
)


class TestGothenburgCorridorSpec414To416(unittest.TestCase):

    def setUp(self) -> None:
        self.nominal_414 = Spec414Telemetry(
            z_real=(Fraction(1, 1), Fraction(1, 1)),
            z_imag=(Fraction(0, 1), Fraction(0, 1)),
            w_real=(Fraction(1, 1), Fraction(1, 1)),
            w_imag=(Fraction(0, 1), Fraction(0, 1)),
            cos2_theta_max=Fraction(93301, 100000),
            prf_multipliers=(7, 9, 11),
            base_clock_dt_ns=125,
            target_velocity_mps=Fraction(120, 1),
            ekf_cov_2x2=(
                (Fraction(1, 100), Fraction(1, 1000)),
                (Fraction(1, 1000), Fraction(1, 100)),
            ),
            ekf_trace_max=Fraction(5, 100),
        )

        self.nominal_415_software = Spec415Telemetry(
            cdc_sync_locked=(True, True, True, True, True),
            hydrostatic_pressure_mpa=Fraction(245, 100),
            acoustic_spl_db=Fraction(1180, 10),
            range_532nm_m=Fraction(4500, 1000),
            range_uwb_m=Fraction(4508, 1000),
            max_tof_divergence_m=Fraction(15, 1000),
            adc_timestamp_ns=0,
            clk_timestamp_ns=1000,
            shunt_current_ua=0,
        )

        self.nominal_416_software = Spec416InfranettTelemetry(
            seq_c=42,
            committed_c_hw=41,
            node_id=0x0416,
            flows_in_mw=(Fraction(125, 2), Fraction(75, 2)),     # Sum = 100 MW
            flows_out_mw=(Fraction(60, 1), Fraction(40, 1)),     # Sum = 100 MW -> Delta_R == 0/1
            fiber_attenuation_db_km=Fraction(195, 1000),         # 0.195 dB/km <= 0.250 dB/km
            fiber_step_loss_db=Fraction(18, 1000),               # 0.018 dB <= 0.050 dB
            grid_freq_hz=Fraction(50000, 1000),                  # 50.000 Hz
            rocof_hz_per_s=Fraction(12, 100),                    # 0.12 Hz/s <= 2.0 Hz/s
            ptp_offset_ns=24,                                    # 24 ns <= 100 ns
            bft_signatures_valid=5,                              # 5 >= 2(2)+1
            bft_fault_tolerance_f=2,
            prev_w_post_sha256=hashlib.sha256(b"GENESIS_INFRANETT_0xABCDEF00").digest(),
            matrix_hash_32b=hashlib.sha256(b"MATRIX_STATE_42").digest(),
            logic_hash_32b=hashlib.sha256(b"LOGIC_SPEC416_V1_5").digest(),
            execution_hash_32b=hashlib.sha256(b"BREAKER_CLOSE_NODE_0416").digest(),
            adc_timestamp_ns=0,                                  # Software demo: no L3 ADC
            clk_timestamp_ns=1000,
            shunt_current_ua=0,                                  # Clamped at 0.00 V DC
        )

    def test_01_ky_orthogonality_and_d12_bijection(self) -> None:
        code, res = KYGrammarGate.verify_orthogonality_and_bijection(CANONICAL_GLYPH)
        self.assertEqual(code, REG_PASS)
        self.assertEqual(res, CANONICAL_ASCII)

        corrupted_glyph = "✓(○ → ∅ → □ → ◇ → ●)#● ▸"
        kill_code, reason = KYGrammarGate.verify_orthogonality_and_bijection(corrupted_glyph)
        self.assertEqual(kill_code, REG_KILL)
        self.assertEqual(reason, "ORTHOGONALITY_VIOLATION_DOT_IN_SUFFIX")

    def test_02_spec414_nominal_and_fine_wilf_kill(self) -> None:
        code, _, horizon = Spec414IsacGate.evaluate(self.nominal_414)
        self.assertEqual(code, REG_PASS)
        self.assertEqual(horizon, 25)

        bad_prf = Spec414Telemetry(**{**self.nominal_414.__dict__, "prf_multipliers": (6, 9, 12)})
        code_kill, msg_kill, _ = Spec414IsacGate.evaluate(bad_prf)
        self.assertEqual(code_kill, REG_KILL)
        self.assertEqual(msg_kill, "SPEC414_FINE_WILF_NON_COPRIME_KILL")

    def test_03_spec415_acoustic_sabotage_and_registry_b_hold(self) -> None:
        code, msg = Spec415KpodGate.evaluate(self.nominal_415_software)
        self.assertEqual(code, REG_HOLD)
        self.assertEqual(msg, "OPEN_AS_SOFTWARE_DEMONSTRATION_0.00V_DC")

        sabotage_kpod = Spec415Telemetry(
            **{**self.nominal_415_software.__dict__, "acoustic_spl_db": Fraction(1465, 10)}
        )
        code_sab, msg_sab = Spec415KpodGate.evaluate(sabotage_kpod)
        self.assertEqual(code_sab, REG_HOLD)
        self.assertEqual(msg_sab, "SPEC415_ACOUSTIC_SABOTAGE_145DB_HOLD")

    def test_04_spec416_infranett_w_pre_w_post_software_hold_and_l3_open(self) -> None:
        # 1. Without L3 ADC/shunt telemetry -> Clamped at HOLD (0.00 V DC)
        code, msg, w_pre, w_post, frame_205 = Spec416InfranettGate.evaluate_and_seal_w_pre_w_post(
            self.nominal_416_software
        )
        self.assertEqual(code, REG_HOLD)
        self.assertEqual(msg, "OPEN_AS_SOFTWARE_DEMONSTRATION_0.00V_DC")
        self.assertEqual(len(w_pre), 119)
        self.assertEqual(len(w_post), 86)
        self.assertEqual(len(frame_205), 205)
        self.assertEqual(w_post[8:40], hashlib.sha256(w_pre).digest())

        # 2. With witnessed L3 ADC (t_ADC >= t_clk) and shunt current (5120 uA >= 500 uA) -> OPEN
        l3_telemetry = Spec416InfranettTelemetry(
            **{
                **self.nominal_416_software.__dict__,
                "adc_timestamp_ns": 1045,
                "clk_timestamp_ns": 1000,
                "shunt_current_ua": 5120,
            }
        )
        code_l3, msg_l3, _, _, _ = Spec416InfranettGate.evaluate_and_seal_w_pre_w_post(l3_telemetry)
        self.assertEqual(code_l3, REG_PASS)
        self.assertEqual(msg_l3, "SPEC416_INFRANETT_L3_WITNESSED_OPEN")

    def test_05_spec416_kirchhoff_toctou_and_fiber_intrusion_gates(self) -> None:
        # 1. Kirchhoff rational imbalance (Delta_R != 0) -> KILL
        bad_kirchhoff = Spec416InfranettTelemetry(
            **{
                **self.nominal_416_software.__dict__,
                "flows_out_mw": (Fraction(60, 1), Fraction(39999, 1000)),
            }
        )
        code_k, msg_k, _, _, _ = Spec416InfranettGate.evaluate_and_seal_w_pre_w_post(bad_kirchhoff)
        self.assertEqual(code_k, REG_KILL)
        self.assertEqual(msg_k, "SPEC416_KIRCHHOFF_IMBALANCE_KILL")

        # 2. Fiber micro-bend optical tap (step loss 0.085 dB > 0.050 dB) -> HOLD
        fiber_tap = Spec416InfranettTelemetry(
            **{
                **self.nominal_416_software.__dict__,
                "fiber_step_loss_db": Fraction(85, 1000),
            }
        )
        code_f, msg_f, _, _, _ = Spec416InfranettGate.evaluate_and_seal_w_pre_w_post(fiber_tap)
        self.assertEqual(code_f, REG_HOLD)
        self.assertEqual(msg_f, "SPEC416_FIBER_OTDR_INTRUSION_HOLD")

        # 3. In-memory TOCTOU mutation between W_pre and W_post -> KILL
        mutated_exec = hashlib.sha256(b"TAMPERED_BREAKER_ACTUATION").digest()
        code_t, msg_t, _, _, _ = Spec416InfranettGate.evaluate_and_seal_w_pre_w_post(
            self.nominal_416_software,
            in_memory_mutated_execution_hash=mutated_exec,
        )
        self.assertEqual(code_t, REG_KILL)
        self.assertEqual(msg_t, "SPEC416_TOCTOU_TRANSIT_MUTATION_KILL")

    def test_06_205b_and_208b_binary_packing(self) -> None:
        hw_205 = pack_205b_hardware_capsule(1, REG_PASS, REG_HOLD, 25, 0)
        self.assertEqual(len(hw_205), 205)

        rosetta_208 = pack_208b_rosetta_d3(
            reg_a=REG_PASS,
            reg_b=REG_HOLD,
            monotonic_seq=1,
            prev_chain_hash=b"\x00" * 32,
            glyph_str=CANONICAL_GLYPH,
            ascii_str=CANONICAL_ASCII,
            ed25519_pubkey_32b=b"\x11" * 32,
            ed25519_sig_64b=b"\x22" * 64,
        )
        self.assertEqual(len(rosetta_208), 208)
        self.assertEqual(rosetta_208[:4], STATE_ANCHOR_MAGIC)

    def test_07_l15_iverilog_rtl_cosimulation_spec415_and_spec416(self) -> None:
        """Kompilerer og simulerer spec415_kpod_cdc_gate.sv og spec416_infranett_witness_gate.sv med iverilog."""
        if shutil.which("iverilog") is None or shutil.which("vvp") is None:
            self.skipTest("iverilog/vvp ikke installert")

        rtl_dir = "/home/sololyset/01_HARDWARE_RTL"
        if not os.path.exists(os.path.join(rtl_dir, "spec415_kpod_cdc_gate.sv")):
            rtl_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../L2_GATE"))

        sv_415 = os.path.join(rtl_dir, "spec415_kpod_cdc_gate.sv")
        sv_416 = os.path.join(rtl_dir, "spec416_infranett_witness_gate.sv")

        # Generate exact 205B (1640-bit) frames from Python L1 Spec416InfranettGate
        _, _, w_pre_hold, w_post_hold, frame_hold_205 = Spec416InfranettGate.evaluate_and_seal_w_pre_w_post(
            self.nominal_416_software
        )
        w_pre_sha_hold = hashlib.sha256(w_pre_hold).hexdigest()
        post_exec_hold = w_post_hold[40:72].hex()
        frame_hold_hex = frame_hold_205.hex()

        l3_open_telemetry = Spec416InfranettTelemetry(
            **{
                **self.nominal_416_software.__dict__,
                "seq_c": 43,
                "committed_c_hw": 42,
                "adc_timestamp_ns": 1050,
                "clk_timestamp_ns": 1000,
                "shunt_current_ua": 5120,
            }
        )
        _, _, w_pre_open, w_post_open, frame_open_205 = Spec416InfranettGate.evaluate_and_seal_w_pre_w_post(
            l3_open_telemetry
        )
        w_pre_sha_open = hashlib.sha256(w_pre_open).hexdigest()
        post_exec_open = w_post_open[40:72].hex()
        frame_open_hex = frame_open_205.hex()

        tb_sv = f"""
`default_nettype none
`timescale 1ns/1ps

module tb_gothenburg_corridor;
    logic clk = 1'b0;
    always #5 clk = ~clk;

    logic        rst_n;
    // SPEC-415 signals
    logic [4:0]  cdc_valid;
    logic [31:0] magic_415;
    logic        crc_415;
    logic [15:0] spl_dbx;
    logic [15:0] r_532_mm;
    logic [15:0] r_uwb_mm;
    logic        adc_ok_415;
    logic [15:0] shunt_415;
    wire  [1:0]  state_415;
    wire         pin_415;

    spec415_kpod_cdc_gate dut_415 (
        .clk_sys_i          (clk),
        .rst_n_i            (rst_n),
        .cdc_async_valid_i  (cdc_valid),
        .frame_magic_i      (magic_415),
        .capsule_crc_ok_i   (crc_415),
        .acoustic_spl_dbx_i (spl_dbx),
        .range_532nm_mm_i   (r_532_mm),
        .range_uwb_mm_i     (r_uwb_mm),
        .adc_time_valid_i   (adc_ok_415),
        .shunt_current_ua_i (shunt_415),
        .gate_state_o       (state_415),
        .actuate_pin_o      (pin_415)
    );

    // SPEC-416 signals (1640-bit / 205B direct decoder)
    logic          frame_valid_416;
    logic [1639:0] frame_205b_416;
    logic [255:0]  comp_w_pre_sha;
    logic [255:0]  exp_post_exec;
    logic [15:0]   step_mdb;
    logic [15:0]   rocof_mhz_s;
    logic          crc_416;
    wire  [1:0]    state_416;
    wire           pin_416;

    spec416_infranett_witness_gate dut_416 (
        .clk_sys_i            (clk),
        .rst_n_i              (rst_n),
        .frame_valid_i        (frame_valid_416),
        .frame_205b_i         (frame_205b_416),
        .computed_w_pre_sha_i (comp_w_pre_sha),
        .expected_post_exec_i (exp_post_exec),
        .otdr_step_loss_mdb_i (step_mdb),
        .rocof_abs_mhz_s_i    (rocof_mhz_s),
        .crc32_valid_i        (crc_416),
        .gate_state_o         (state_416),
        .breaker_actuate_o    (pin_416)
    );

    initial begin
        rst_n = 1'b0;
        cdc_valid  = 5'b11111;
        magic_415  = 32'hABCD_EF00;
        crc_415    = 1'b1;
        spl_dbx    = 16'd1180;
        r_532_mm   = 16'd4500;
        r_uwb_mm   = 16'd4508;
        adc_ok_415 = 1'b0;
        shunt_415  = 16'd0;

        frame_valid_416 = 1'b0;
        frame_205b_416  = 1640'h{frame_hold_hex};
        comp_w_pre_sha  = 256'h{w_pre_sha_hold};
        exp_post_exec   = 256'h{post_exec_hold};
        step_mdb        = 16'd18;
        rocof_mhz_s     = 16'd120;
        crc_416         = 1'b1;

        #20 rst_n = 1'b1;
        // Single-cycle packet arrival strobe for seq=42 (HOLD frame)
        @(negedge clk);
        frame_valid_416 = 1'b1;
        @(negedge clk);
        frame_valid_416 = 1'b0;
        #10;
        if (state_415 !== 2'b00 || pin_415 !== 1'b0) $fatal(1, "415 Reg B HOLD failed");
        if (state_416 !== 2'b00 || pin_416 !== 1'b0) $fatal(1, "416 Reg B HOLD failed");

        // Supply witnessed L3 HIL 205B frame (seq=43, dt_ADC=50ns, shunt=5120uA) -> OPEN
        @(negedge clk);
        adc_ok_415 = 1'b1; shunt_415 = 16'd5120;
        frame_205b_416  = 1640'h{frame_open_hex};
        comp_w_pre_sha  = 256'h{w_pre_sha_open};
        exp_post_exec   = 256'h{post_exec_open};
        frame_valid_416 = 1'b1;
        @(negedge clk);
        frame_valid_416 = 1'b0;
        #10;
        if (state_415 !== 2'b01 || pin_415 !== 1'b1) $fatal(1, "415 L3 OPEN failed");
        if (state_416 !== 2'b01 || pin_416 !== 1'b1) $fatal(1, "416 L3 OPEN failed");

        // Trigger acoustic sabotage (146.5 dB) on 415 -> HOLD (0.00V)
        @(negedge clk);
        spl_dbx = 16'd1465;
        #10;
        if (state_415 !== 2'b00 || pin_415 !== 1'b0) $fatal(1, "415 SPL HOLD failed");

        // Trigger TOCTOU / Replay on 416 and 162.0 dB shockwave on 415 -> Permanent KILL latch
        @(negedge clk);
        spl_dbx         = 16'd1620;
        exp_post_exec   = 256'hDEAD_BEEF;
        frame_valid_416 = 1'b1;
        @(negedge clk);
        frame_valid_416 = 1'b0;
        #10;
        if (state_415 !== 2'b11 || pin_415 !== 1'b0) $fatal(1, "415 KILL latch failed");
        if (state_416 !== 2'b11 || pin_416 !== 1'b0) $fatal(1, "416 KILL latch failed");

        $display("RTL_GOTHENBURG_CORRIDOR_415_416_PASS");
        $finish;
    end
endmodule
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tb_path = os.path.join(tmpdir, "tb_gothenburg_corridor.sv")
            vvp_bin = os.path.join(tmpdir, "sim.vvp")
            with open(tb_path, "w", encoding="utf-8") as f:
                f.write(tb_sv)
            subprocess.run(
                ["iverilog", "-g2012", "-o", vvp_bin, sv_415, sv_416, tb_path],
                check=True,
                capture_output=True,
                text=True,
            )
            res = subprocess.run(["vvp", vvp_bin], check=True, capture_output=True, text=True)
            self.assertIn("RTL_GOTHENBURG_CORRIDOR_415_416_PASS", res.stdout)

    def test_08_l15_iverilog_master_top_208b_rosetta_and_205b_capsules(self) -> None:
        """Verifiserer gothenburg_corridor_rosetta_top.sv (208B Rosetta D3 + SPEC-213 + SPEC-415 + SPEC-416)."""
        if shutil.which("iverilog") is None or shutil.which("vvp") is None:
            self.skipTest("iverilog/vvp ikke installert")

        rtl_dir = "/home/sololyset/01_HARDWARE_RTL"
        if not os.path.exists(os.path.join(rtl_dir, "gothenburg_corridor_rosetta_top.sv")):
            rtl_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../L2_GATE"))

        sv_213 = os.path.join(rtl_dir, "fpga_capsule_frame_205b_decoder.sv")
        sv_415 = os.path.join(rtl_dir, "spec415_kpod_cdc_gate.sv")
        sv_416 = os.path.join(rtl_dir, "spec416_infranett_witness_gate.sv")
        sv_top = os.path.join(rtl_dir, "gothenburg_corridor_rosetta_top.sv")

        import struct as _struct

        # 1. Build SPEC-213 119B (LE) + 86B (LE) valid realized capsule
        w_pre_hash_213 = hashlib.sha256(b"SPEC213_PRE_HASH_42").digest()
        w_pre_le = _struct.pack(
            "<QQ32sfBH32s32s",
            42,
            1000,
            b"\xAA" * 32,
            0.0,
            0x01,  # OPEN
            0,
            b"\x00" * 32,
            w_pre_hash_213,
        )
        w_post_le = _struct.pack(
            "<QQ32sBfB32s",
            42,
            1050,
            w_pre_hash_213,
            0x01,  # HPIS latch engaged
            1.25,  # Positive Landauer exhaust
            0x01,  # Final status REALIZED
            b"\xBB" * 32,
        )
        w_pre_le_hex = w_pre_le[::-1].hex()
        w_post_le_hex = w_post_le[::-1].hex()

        # 2. Build SPEC-416 205B frames (seq=42 HOLD, seq=43 L3 OPEN)
        _, _, w_pre_hold, w_post_hold, frame_hold_205 = Spec416InfranettGate.evaluate_and_seal_w_pre_w_post(
            self.nominal_416_software
        )
        l3_open_telemetry = Spec416InfranettTelemetry(
            **{
                **self.nominal_416_software.__dict__,
                "seq_c": 43,
                "committed_c_hw": 42,
                "adc_timestamp_ns": 1050,
                "clk_timestamp_ns": 1000,
                "shunt_current_ua": 5120,
            }
        )
        _, _, w_pre_open, w_post_open, frame_open_205 = Spec416InfranettGate.evaluate_and_seal_w_pre_w_post(
            l3_open_telemetry
        )

        # 3. Build 208B Rosetta D3 envelopes (reg_b=0x00 for seq=42 HOLD, reg_b=0x01 for seq=43 L3 OPEN)
        rosetta_hold_208 = pack_208b_rosetta_d3(
            reg_a=0x01,
            reg_b=0x00,
            monotonic_seq=42,
            prev_chain_hash=b"\x00" * 32,
            glyph_str=CANONICAL_GLYPH,
            ascii_str=CANONICAL_ASCII,
            ed25519_pubkey_32b=b"\x11" * 32,
            ed25519_sig_64b=b"\x22" * 64,
        )
        rosetta_open_208 = pack_208b_rosetta_d3(
            reg_a=0x01,
            reg_b=0x01,
            monotonic_seq=43,
            prev_chain_hash=hashlib.sha256(rosetta_hold_208).digest(),
            glyph_str=CANONICAL_GLYPH,
            ascii_str=CANONICAL_ASCII,
            ed25519_pubkey_32b=b"\x11" * 32,
            ed25519_sig_64b=b"\x33" * 64,
        )

        glyph_sha_hex = hashlib.sha256(CANONICAL_GLYPH.encode("utf-8")).hexdigest()
        ascii_sha_hex = hashlib.sha256(CANONICAL_ASCII.encode("utf-8")).hexdigest()

        tb_top_sv = f"""
`default_nettype none
`timescale 1ns/1ps

module tb_gothenburg_rosetta_top;
    logic clk = 1'b0;
    always #5 clk = ~clk;

    logic          rst_n;
    logic          frame_valid;
    logic [1663:0] rosetta_208b;
    logic [255:0]  exp_glyph_sha;
    logic [255:0]  exp_ascii_sha;
    logic          ed25519_ok;
    logic [951:0]  s213_pre_le;
    logic [687:0]  s213_post_le;
    logic [4:0]    kpod_cdc;
    logic [15:0]   kpod_spl;
    logic [15:0]   kpod_532;
    logic [15:0]   kpod_uwb;
    logic [1639:0] infra_205b;
    logic [255:0]  infra_pre_sha;
    logic [255:0]  infra_exec_sha;
    logic [15:0]   infra_step_mdb;
    logic [15:0]   infra_rocof;
    logic          infra_crc_ok;

    wire [1:0] top_state;
    wire [1:0] s415_state;
    wire [1:0] s416_state;
    wire [7:0] s213_verdict;
    wire       kpod_pin;
    wire       infra_pin;
    wire       master_5v;

    gothenburg_corridor_rosetta_top dut (
        .clk_sys_i                  (clk),
        .rst_n_i                    (rst_n),
        .frame_valid_i              (frame_valid),
        .rosetta_208b_i             (rosetta_208b),
        .expected_ky_glyph_sha_i    (exp_glyph_sha),
        .expected_ky_ascii_sha_i    (exp_ascii_sha),
        .ed25519_sig_valid_i        (ed25519_ok),
        .spec213_w_pre_le_i         (s213_pre_le),
        .spec213_w_post_le_i        (s213_post_le),
        .kpod_cdc_async_valid_i     (kpod_cdc),
        .kpod_acoustic_spl_dbx_i    (kpod_spl),
        .kpod_range_532nm_mm_i      (kpod_532),
        .kpod_range_uwb_mm_i        (kpod_uwb),
        .infranett_frame_205b_i     (infra_205b),
        .infranett_comp_w_pre_sha_i (infra_pre_sha),
        .infranett_exp_post_exec_i  (infra_exec_sha),
        .infranett_otdr_step_mdb_i  (infra_step_mdb),
        .infranett_rocof_mhz_s_i    (infra_rocof),
        .infranett_crc32_valid_i    (infra_crc_ok),
        .top_gate_state_o           (top_state),
        .spec415_state_o            (s415_state),
        .spec416_state_o            (s416_state),
        .spec213_verdict_o          (s213_verdict),
        .kpod_actuate_pin_o         (kpod_pin),
        .infranett_breaker_pin_o    (infra_pin),
        .master_5v_rail_en_o        (master_5v)
    );

    initial begin
        rst_n          = 1'b0;
        frame_valid    = 1'b0;
        rosetta_208b   = 1664'h{rosetta_hold_208.hex()};
        exp_glyph_sha  = 256'h{glyph_sha_hex};
        exp_ascii_sha  = 256'h{ascii_sha_hex};
        ed25519_ok     = 1'b1;
        s213_pre_le    = 952'h{w_pre_le_hex};
        s213_post_le   = 688'h{w_post_le_hex};
        kpod_cdc       = 5'b11111;
        kpod_spl       = 16'd1180;
        kpod_532       = 16'd4500;
        kpod_uwb       = 16'd4508;
        infra_205b     = 1640'h{frame_hold_205.hex()};
        infra_pre_sha  = 256'h{hashlib.sha256(w_pre_hold).hexdigest()};
        infra_exec_sha = 256'h{w_post_hold[40:72].hex()};
        infra_step_mdb = 16'd18;
        infra_rocof    = 16'd120;
        infra_crc_ok   = 1'b1;

        #25 rst_n = 1'b1;
        // Strobe seq=42 (Software demo HOLD: reg_b == 0x00, shunt == 0)
        @(negedge clk);
        frame_valid = 1'b1;
        @(negedge clk);
        frame_valid = 1'b0;
        #20;
        if (top_state !== 2'b00 || master_5v !== 1'b0 || kpod_pin !== 1'b0 || infra_pin !== 1'b0)
            $fatal(1, "Master top HOLD failed");

        // Strobe seq=43 (L3 HIL Witnessed OPEN: reg_b == 0x01, dt_ADC=50ns, shunt=5120uA)
        @(negedge clk);
        rosetta_208b   = 1664'h{rosetta_open_208.hex()};
        infra_205b     = 1640'h{frame_open_205.hex()};
        infra_pre_sha  = 256'h{hashlib.sha256(w_pre_open).hexdigest()};
        infra_exec_sha = 256'h{w_post_open[40:72].hex()};
        frame_valid    = 1'b1;
        @(negedge clk);
        frame_valid    = 1'b0;
        #20;
        if (top_state !== 2'b01 || master_5v !== 1'b1 || kpod_pin !== 1'b1 || infra_pin !== 1'b1)
            $fatal(1, "Master top L3 OPEN failed");

        // Invalidate Ed25519 signature (Registry A breach) -> Immediate permanent KILL
        @(negedge clk);
        ed25519_ok  = 1'b0;
        frame_valid = 1'b1;
        @(negedge clk);
        frame_valid = 1'b0;
        #20;
        if (top_state !== 2'b11 || master_5v !== 1'b0 || kpod_pin !== 1'b0 || infra_pin !== 1'b0)
            $fatal(1, "Master top Registry A KILL trap failed");

        $display("RTL_MASTER_ROSETTA_208B_205B_TOP_PASS");
        $finish;
    end
endmodule
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tb_path = os.path.join(tmpdir, "tb_gothenburg_rosetta_top.sv")
            vvp_bin = os.path.join(tmpdir, "sim_top.vvp")
            with open(tb_path, "w", encoding="utf-8") as f:
                f.write(tb_top_sv)
            subprocess.run(
                ["iverilog", "-g2012", "-o", vvp_bin, sv_213, sv_415, sv_416, sv_top, tb_path],
                check=True,
                capture_output=True,
                text=True,
            )
            res = subprocess.run(["vvp", vvp_bin], check=True, capture_output=True, text=True)
            self.assertIn("RTL_MASTER_ROSETTA_208B_205B_TOP_PASS", res.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
