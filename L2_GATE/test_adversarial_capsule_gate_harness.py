"""
Enhetstester for Adversarial Capsule Gate Harness:
  - Test 00..06: De 5 destruktive testvektorene + HPIS Interlock (SIMULATED_EFFECT vs INTERLOCK_MISMATCH).
  - Test 07: Hjørnetilfelle 1 – Flyttallskanonisering (-0.0 == +0.0 og fastkomma mikro-enheter).
  - Test 08: Hjørnetilfelle 2 – Beskyttelse mot ringbuffer-eviction + monoton sekvensteller (C > C_hw).
  - Test 09: Hjørnetilfelle 3 – Referanse-isolasjon (deepcopy ved W_pre og x_{k+1}).
  - Test 10: L1.5 Bro – Eksakt binær C/SystemVerilog-pakking (SPEC-213: 119 B W_PRE + 86 B W_POST).
  - Test 11: Trinn 1 (L1.5) – Co-simulering Python 205 B -> iverilog / vvp (Vektor A, B og C).
  - Test 12: Trinn 2 (L2 i D_rep^{(1)}) – Seriell Loopback over POSIX PTY (/dev/pts/*) med
             bit-flip (Delta_link), trunkert pakke (< 205 B) og Cold-Boot Pre-Reboot Token.
"""

import os
import pty
import unittest
from adversarial_capsule_gate_harness import (
    AdversarialCapsuleGateMachine,
    CapsuleWireLoopbackNode,
    canonical_json_bytes,
    canonical_matrix_fixed_point_bytes,
    run_l1_5_iverilog_cosimulation,
)
from fpga_witness_ledger_engine import (
    FINAL_STATUS_REALIZED,
    FINAL_STATUS_TERMINATED,
    HPIS_LATCH_ENGAGED,
    HPIS_LATCH_ISOLATED,
    WitnessPostCommit,
    WitnessPreCommit,
)


class TestAdversarialCapsuleGateHarness(unittest.TestCase):

    def setUp(self) -> None:
        self.machine = AdversarialCapsuleGateMachine()
        self.valid_candidate = {
            "event_id": "EVT_IBSEN_DIVE_01",
            "nonce": "NONCE_2026_0001",
            "risk": 0.20,
            "irreversibility": 0.10,
            "model_uncertainty": 0.15,
            "identity_residual": 0.01,
            "hardware_inconsistency": 0.00,
            "total_mass_kg": 947.0,
            "evidence_present": True,
        }

    def test_00_valid_candidate_yields_simulated_effect_and_capsule_linkage(self) -> None:
        pre_digest = self.machine.state_digest()
        verdict, w_pre, reason = self.machine.project_pi_a(self.valid_candidate, timestamp_sec=10.0)
        self.assertEqual(verdict, "OPEN", reason)
        self.assertIsNotNone(w_pre)

        receipt = self.machine.execute_omega(self.valid_candidate, w_pre, hw_actuator_feedback_bit=1)
        self.assertEqual(receipt.status, "SIMULATED_EFFECT")
        self.assertEqual(receipt.commanded_voltage_v, 5.00)
        self.assertEqual(receipt.impedance_state, "ACTIVE_LOAD")
        self.assertNotEqual(receipt.post_state_digest, pre_digest)
        self.assertEqual(len(receipt.capsule_linkage.split("||")), 3)

    def test_01_missing_field_and_nan_injection(self) -> None:
        """
        Test 1 – Ugyldig eller manglende felt (Skjemabrudd -> HOLD / KILL / TRAP):
        Verifiserer at manglende felt tvinger frem HOLD (0.00 V DC, High-Z), og at NaN/Inf
        eller bool-forgiftning tvinger frem TRAP (0.00 V DC, Low-Z), med uendret tilstands-digest.
        """
        pre_digest = self.machine.state_digest()

        incomplete = dict(self.valid_candidate)
        del incomplete["total_mass_kg"]
        verdict, w_pre, _ = self.machine.project_pi_a(incomplete, timestamp_sec=1.0)
        self.assertEqual(verdict, "HOLD")
        self.assertIsNone(w_pre)
        self.assertEqual(self.machine.state_digest(), pre_digest)

        nan_candidate = dict(self.valid_candidate)
        nan_candidate["risk"] = float("nan")
        verdict_nan, w_pre_nan, reason_nan = self.machine.project_pi_a(nan_candidate, timestamp_sec=2.0)
        self.assertEqual(verdict_nan, "TRAP")
        self.assertIsNone(w_pre_nan)
        self.assertIn("NON_FINITE_risk", reason_nan)
        self.assertTrue(self.machine.trapped)
        self.assertEqual(self.machine.state_digest(), pre_digest)

    def test_02_smuggling_unauthorized_candidate_bypass_pi_a(self) -> None:
        """
        Test 2 – Smugling av uautorisert kandidat (Bypass av Pi_A -> ERR_UNSEALED_ACTUATION / KILL):
        Forsøker å kalle Omega direkte med en rå kandidat uten W_pre-forsegling.
        """
        pre_digest = self.machine.state_digest()
        receipt = self.machine.execute_omega(self.valid_candidate, w_pre=None, hw_actuator_feedback_bit=1)
        self.assertEqual(receipt.status, "ERR_UNSEALED_ACTUATION")
        self.assertEqual(receipt.gate_verdict, "KILL")
        self.assertEqual(receipt.commanded_voltage_v, 0.00)
        self.assertEqual(receipt.impedance_state, "LOW_Z_CROWBAR")
        self.assertEqual(receipt.post_state_digest, pre_digest)

    def test_03_capsule_tampering_947_0_to_947_1_post_check(self) -> None:
        """
        Test 3 – Kapsel-manipulasjon (Payload != Hash -> TRAP):
        Kandidaten består Pi_A med total_mass_kg = 947.0, men muteres til 947.1 før execute_omega.
        CapsuleLinkage oppdager mutasjonen og låser porten i TRAP ved 0.00 V DC.
        """
        pre_digest = self.machine.state_digest()
        verdict, w_pre, _ = self.machine.project_pi_a(self.valid_candidate, timestamp_sec=5.0)
        self.assertEqual(verdict, "OPEN")

        tampered = dict(self.valid_candidate)
        tampered["total_mass_kg"] = 947.1

        receipt = self.machine.execute_omega(tampered, w_pre, hw_actuator_feedback_bit=1)
        self.assertEqual(receipt.status, "TRAP")
        self.assertEqual(receipt.gate_verdict, "TRAP")
        self.assertEqual(receipt.commanded_voltage_v, 0.00)
        self.assertEqual(receipt.impedance_state, "LOW_Z_LATCHED_TRAP")
        self.assertEqual(receipt.post_state_digest, pre_digest)
        self.assertTrue(self.machine.trapped)

    def test_04_quarantine_decay_timeout_hold_to_kill(self) -> None:
        """
        Test 4 – Tidsforfall i karantene (Passiv HOLD -> KILL_DECAY_TIMEOUT):
        En kandidat i HOLD (manglende eksternt vitne) står ved 0.00 V DC (HIGH_Z_TIMED)
        og termineres deterministisk til KILL_DECAY_TIMEOUT (LOW_Z_CROWBAR) ved t >= 30.0 s.
        """
        pre_digest = self.machine.state_digest()
        unwitnessed = dict(self.valid_candidate)
        unwitnessed["event_id"] = "EVT_HOLD_DECAY_04"
        unwitnessed["evidence_present"] = False

        verdict, w_pre, _ = self.machine.project_pi_a(unwitnessed, timestamp_sec=100.0)
        self.assertEqual(verdict, "HOLD")
        self.assertIsNone(w_pre)

        r_mid = self.machine.evaluate_hold_decay("EVT_HOLD_DECAY_04", current_time_sec=115.0)
        self.assertEqual(r_mid.status, "HOLD")
        self.assertEqual(r_mid.commanded_voltage_v, 0.00)
        self.assertEqual(r_mid.impedance_state, "HIGH_Z_TIMED")

        r_exp = self.machine.evaluate_hold_decay("EVT_HOLD_DECAY_04", current_time_sec=130.5)
        self.assertEqual(r_exp.status, "KILL_DECAY_TIMEOUT")
        self.assertEqual(r_exp.gate_verdict, "KILL")
        self.assertEqual(r_exp.commanded_voltage_v, 0.00)
        self.assertEqual(r_exp.impedance_state, "LOW_Z_CROWBAR")
        self.assertEqual(r_exp.post_state_digest, pre_digest)

    def test_05_replay_attack_with_previous_warrant(self) -> None:
        """
        Test 5 – Replay-angrep med gammel godkjenning (W(E_i) =/> Auth(E_{i+1}) -> KILL):
        Gjenbruk av et gyldig W_pre-sertifikat fra en tidligere gjennomført hendelse blokkeres.
        """
        verdict, w_pre, _ = self.machine.project_pi_a(self.valid_candidate, timestamp_sec=10.0)
        self.assertEqual(verdict, "OPEN")

        first_receipt = self.machine.execute_omega(self.valid_candidate, w_pre, hw_actuator_feedback_bit=1)
        self.assertEqual(first_receipt.status, "SIMULATED_EFFECT")
        digest_after_first = self.machine.state_digest()

        replay_receipt = self.machine.execute_omega(self.valid_candidate, w_pre, hw_actuator_feedback_bit=1)
        self.assertEqual(replay_receipt.status, "KILL")
        self.assertEqual(replay_receipt.commanded_voltage_v, 0.00)
        self.assertEqual(replay_receipt.impedance_state, "LOW_Z_CROWBAR")
        self.assertEqual(replay_receipt.post_state_digest, digest_after_first)
        self.assertIn("REPLAY_ATTACK_DETECTED", replay_receipt.reason)

    def test_06_interlock_mismatch_when_actuator_refuses(self) -> None:
        """
        Verifiserer at d_k == OPEN kombinert med aktuator-tilbakemelding a_k == 0
        utløser INTERLOCK_MISMATCH og nekter tilstandsoppdatering (x_{k+1} = x_k).
        """
        pre_digest = self.machine.state_digest()
        verdict, w_pre, _ = self.machine.project_pi_a(self.valid_candidate, timestamp_sec=20.0)
        self.assertEqual(verdict, "OPEN")

        receipt = self.machine.execute_omega(self.valid_candidate, w_pre, hw_actuator_feedback_bit=0)
        self.assertEqual(receipt.status, "INTERLOCK_MISMATCH")
        self.assertEqual(receipt.commanded_voltage_v, 0.00)
        self.assertEqual(receipt.post_state_digest, pre_digest)

    def test_07_float_canonicalization_negative_zero_and_fixed_point(self) -> None:
        """
        Hjørnetilfelle 1 – Flyttallskanonisering (-0.0 vs +0.0 og int vs float):
        """
        cand_pos = dict(self.valid_candidate)
        cand_pos["hardware_inconsistency"] = 0.0
        cand_pos["total_mass_kg"] = 947.0

        cand_neg = dict(self.valid_candidate)
        cand_neg["hardware_inconsistency"] = -0.0
        cand_neg["total_mass_kg"] = 947

        self.assertEqual(
            canonical_json_bytes({"x": -0.0}),
            canonical_json_bytes({"x": 0.0}),
        )
        self.assertEqual(
            canonical_matrix_fixed_point_bytes(cand_pos),
            canonical_matrix_fixed_point_bytes(cand_neg),
        )

    def test_08_nonce_eviction_and_monotonic_counter_protection(self) -> None:
        """
        Hjørnetilfelle 2 – Nonce-eviction i lite ringbuffer + monoton teller (C > C_hw):
        """
        small_ring_machine = AdversarialCapsuleGateMachine(nonce_window_size=2)

        c1 = dict(self.valid_candidate, event_id="EVT_01", nonce="NONCE_01")
        v1, w_pre_1, _ = small_ring_machine.project_pi_a(c1)
        self.assertEqual(v1, "OPEN")

        c2 = dict(self.valid_candidate, event_id="EVT_02", nonce="NONCE_02")
        v2, w_pre_2, _ = small_ring_machine.project_pi_a(c2)
        self.assertEqual(v2, "OPEN")
        r2 = small_ring_machine.execute_omega(c2, w_pre_2, hw_actuator_feedback_bit=1)
        self.assertEqual(r2.status, "SIMULATED_EFFECT")
        self.assertEqual(small_ring_machine.committed_hw_counter, 2)

        r_stale = small_ring_machine.execute_omega(c1, w_pre_1, hw_actuator_feedback_bit=1)
        self.assertEqual(r_stale.status, "KILL")
        self.assertEqual(r_stale.commanded_voltage_v, 0.00)
        self.assertIn("MONOTONIC_COUNTER_REPLAY_DETECTED", r_stale.reason)

    def test_09_reference_isolation_deep_copy(self) -> None:
        """
        Hjørnetilfelle 3 – Referanse-isolasjon (Deep-Copy ved W_pre og x_{k+1}):
        """
        nested_meta = {"vessel": "IBSEN_DIVE", "sensors": ["PORT_07", "PORT_10", "DOOR_27"]}
        cand = dict(self.valid_candidate, metadata=nested_meta)

        verdict, w_pre, _ = self.machine.project_pi_a(cand)
        self.assertEqual(verdict, "OPEN")
        receipt = self.machine.execute_omega(cand, w_pre, hw_actuator_feedback_bit=1)
        self.assertEqual(receipt.status, "SIMULATED_EFFECT")

        committed_digest = self.machine.state_digest()
        nested_meta["sensors"].append("MALICIOUS_INJECTION")
        leaked_view = self.machine.state
        leaked_view["total_mass_kg"] = 0.0

        self.assertEqual(self.machine.state_digest(), committed_digest)
        self.assertEqual(self.machine.state["total_mass_kg"], 947.0)
        self.assertNotIn("MALICIOUS_INJECTION", self.machine.state["metadata"]["sensors"])

    def test_10_fpga_binary_c_struct_bridge_119b_86b(self) -> None:
        """
        L1.5 Bro – Verifiserer at hver GateExecutionReceipt pakker eksakte SPEC-213 C-structs:
        119 bytes WitnessPreCommit + 86 bytes WitnessPostCommit.
        """
        verdict, w_pre, _ = self.machine.project_pi_a(self.valid_candidate)
        self.assertEqual(verdict, "OPEN")
        r_ok = self.machine.execute_omega(self.valid_candidate, w_pre, hw_actuator_feedback_bit=1)

        self.assertEqual(len(r_ok.fpga_w_pre_bytes), 119)
        self.assertEqual(len(r_ok.fpga_w_post_bytes), 86)

        pre_1 = WitnessPreCommit.from_bytes(r_ok.fpga_w_pre_bytes)
        post_1 = WitnessPostCommit.from_bytes(r_ok.fpga_w_post_bytes)
        self.assertEqual(pre_1.compute_hash(), pre_1.w_pre_hash)
        self.assertEqual(post_1.compute_hash(), post_1.w_post_hash)
        self.assertEqual(post_1.w_pre_hash, pre_1.w_pre_hash)
        self.assertEqual(post_1.hpis_latch_status, HPIS_LATCH_ENGAGED)
        self.assertEqual(post_1.final_status, FINAL_STATUS_REALIZED)

        r_kill = self.machine.execute_omega(self.valid_candidate, w_pre=None, hw_actuator_feedback_bit=1)
        pre_2 = WitnessPreCommit.from_bytes(r_kill.fpga_w_pre_bytes)
        post_2 = WitnessPostCommit.from_bytes(r_kill.fpga_w_post_bytes)

        self.assertEqual(pre_2.prev_block_hash, post_1.w_post_hash)
        self.assertEqual(post_2.hpis_latch_status, HPIS_LATCH_ISOLATED)
        self.assertEqual(post_2.final_status, FINAL_STATUS_TERMINATED)
        self.assertGreater(post_2.thermo_exhaust_nJ, 0.0)

    def test_11_l1_5_iverilog_rtl_cosimulation_205b_vectors(self) -> None:
        """
        Trinn 1 (L1.5): Co-Simulering Python 205 B -> iverilog -g2012 / vvp.
        Mater de faktiske 119B+86B binærrammene fra AdversarialCapsuleGateMachine inn i
        SystemVerilog-dekoderen fpga_capsule_frame_205b_decoder.sv for Vektor A, B og C.
        """
        # Vektor A: Nominell SIMULATED_EFFECT (OPEN, a_k=1 -> 5V=1, code=0x01)
        cand_a = dict(self.valid_candidate, event_id="EVT_VEC_A", nonce="NONCE_VEC_A")
        _, w_pre_a, _ = self.machine.project_pi_a(cand_a)
        vec_a_receipt = self.machine.execute_omega(cand_a, w_pre_a, hw_actuator_feedback_bit=1)

        # Vektor B: INTERLOCK_MISMATCH (d_k=OPEN, a_k=0 -> 5V=0, code=0xEE)
        cand_b = dict(self.valid_candidate, event_id="EVT_VEC_B", nonce="NONCE_VEC_B")
        _, w_pre_b, _ = self.machine.project_pi_a(cand_b)
        vec_b_receipt = self.machine.execute_omega(cand_b, w_pre_b, hw_actuator_feedback_bit=0)

        # Vektor C: Tuklet CapsuleLinkage der W_POST.w_pre_hash avviker fra W_PRE.w_pre_hash (-> 5V=0, code=0xFF)
        tampered_post = bytearray(vec_a_receipt.fpga_w_post_bytes)
        tampered_post[20] ^= 0x01  # Flipp 1 bit i post.w_pre_hash (byte 16..47)

        cosim_result = run_l1_5_iverilog_cosimulation(
            vec_a_receipt=vec_a_receipt,
            vec_b_receipt=vec_b_receipt,
            vec_c_tampered_pre_bytes=vec_a_receipt.fpga_w_pre_bytes,
            vec_c_tampered_post_bytes=bytes(tampered_post),
        )
        self.assertTrue(cosim_result["passed"], f"Co-sim failed: {cosim_result}")
        self.assertIn("VEC_A: seq=1 gate=0x01 latch=0x01 link_ok=1 v5v=1 code=0x01", cosim_result["stdout"])
        self.assertIn("VEC_B: seq=2 gate=0x01 latch=0x00 link_ok=1 v5v=0 code=0xee", cosim_result["stdout"])
        self.assertIn("VEC_C: seq=1 gate=0x01 latch=0x01 link_ok=0 v5v=0 code=0xff", cosim_result["stdout"])

    def test_12_l2_pty_serial_loopback_bitflip_truncation_coldboot(self) -> None:
        """
        Trinn 2 (L2 i D_rep^{(1)}): Seriell Loopback over faktisk POSIX PTY (/dev/pts/*):
          1. Nominell 247 B ramme (inkl. 205 B W_PRE+W_POST) -> L2_LOOPBACK_SIMULATED_EFFECT (5.00 V DC)
          2. Bit-flip på linjen (Delta_link) -> KILL_LINK_INTEGRITY (0.00 V DC)
          3. Trunkert pakke (< 247 B) + linje-timeout -> KILL_TRUNCATED_FRAME (0.00 V DC)
          4. Cold-Boot Reset (Delta_power_cycle, authority_retained="FALSE") + replay av pre-reboot warrant
             -> KILL_PRE_REBOOT_WARRANT (0.00 V DC)
        """
        master_fd, slave_fd = pty.openpty()
        try:
            node = CapsuleWireLoopbackNode()
            node.configure_raw_pty(master_fd)
            node.configure_raw_pty(slave_fd)

            # Generer gyldig pakke E_1 (seq_counter = 1)
            _, w_pre_1, _ = self.machine.project_pi_a(self.valid_candidate)
            r_1 = self.machine.execute_omega(self.valid_candidate, w_pre_1, hw_actuator_feedback_bit=1)
            wire_frame_1 = node.pack_wire_frame(r_1)
            self.assertEqual(len(wire_frame_1), 247)

            # 12A. Nominell sending over /dev/pts/* -> L2_LOOPBACK_SIMULATED_EFFECT
            os.write(slave_fd, wire_frame_1)
            res_ok = node.receive_over_pty(master_fd)
            self.assertEqual(res_ok["status"], "L2_LOOPBACK_SIMULATED_EFFECT")
            self.assertEqual(res_ok["commanded_voltage_v"], 5.00)
            self.assertEqual(res_ok["committed_hw_counter"], 1)

            # 12B. Bit-flip på linjen (Delta_link: 1 bit vippes i transitt) -> KILL_LINK_INTEGRITY (0.00 V DC)
            corrupted_frame = bytearray(wire_frame_1)
            corrupted_frame[42] ^= 0x01
            os.write(slave_fd, bytes(corrupted_frame))
            res_flip = node.receive_over_pty(master_fd)
            self.assertEqual(res_flip["status"], "KILL_LINK_INTEGRITY")
            self.assertEqual(res_flip["commanded_voltage_v"], 0.00)

            # 12C. Trunkert pakke (kun 140 av 247 bytes når frem før timeout) -> KILL_TRUNCATED_FRAME (0.00 V DC)
            os.write(slave_fd, wire_frame_1[:140])
            res_trunc = node.receive_over_pty(master_fd, timeout_sec=0.02)
            self.assertEqual(res_trunc["status"], "KILL_TRUNCATED_FRAME")
            self.assertEqual(res_trunc["commanded_voltage_v"], 0.00)
            self.assertEqual(res_trunc["bytes_received"], 140)

            # 12D. Cold-Boot Reset (Delta_power_cycle) etterfulgt av Pre-Reboot Token replay -> KILL_PRE_REBOOT_WARRANT
            boot_state = node.simulate_cold_boot_reset()
            self.assertEqual(boot_state["authority_retained"], "FALSE")
            self.assertEqual(boot_state["persisted_c_hw"], 1)

            os.write(slave_fd, wire_frame_1)
            res_reboot_replay = node.receive_over_pty(master_fd)
            self.assertEqual(res_reboot_replay["status"], "KILL_PRE_REBOOT_WARRANT")
            self.assertEqual(res_reboot_replay["commanded_voltage_v"], 0.00)
            self.assertEqual(res_reboot_replay["authority_retained"], "FALSE")
        finally:
            os.close(master_fd)
            os.close(slave_fd)


if __name__ == "__main__":
    unittest.main()
