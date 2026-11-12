from __future__ import annotations

import json
from pathlib import Path
import unittest

from light_bridge_gate import LightBridgeDeterministicGate, evaluate_fixture


FIXTURE = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))


class LightBridgeConsequenceGateMicrotest(unittest.TestCase):
    def test_01_dual_clock_law_and_no_silent_hold(self) -> None:
        gate = LightBridgeDeterministicGate("LB-TEST-01", hold_tau_max=14.0)
        self.assertIs(gate.set_to_hold("PROP-OMITTED"), False)
        self.assertIs(gate.set_to_hold("PROP-EMPTY", "   "), False)
        self.assertEqual(gate.hold_jurisdiction, "P_EXT")
        self.assertFalse(gate.collision_enabled)

        gate.set_to_hold("PROP-VALID", "Await witness signature")
        self.assertEqual(gate.hold_jurisdiction, "P_INT")
        with self.assertRaises(ValueError):
            gate.advance_hold_clock(-0.1)

        active = gate.advance_hold_clock(10.0)
        self.assertEqual(active["status"], "HOLD_ACTIVE")
        self.assertEqual(gate.hold_jurisdiction, "P_INT")
        self.assertFalse(gate.collision_enabled)

        forfeit = gate.advance_hold_clock(5.0)
        self.assertEqual(forfeit["status"], "HOLD_DEADLINE_FORFEITED")
        self.assertEqual(gate.hold_jurisdiction, "P_EXT")
        self.assertEqual(gate.state, "HOLD_BLUEPRINT")
        self.assertFalse(gate.collision_enabled)
        self.assertEqual(gate.modeled_voltage_v, 0.00)

    def test_02_open_requires_nonempty_explicit_evidence(self) -> None:
        gate = LightBridgeDeterministicGate("LB-TEST-02")
        res = gate.attempt_open("   ")
        self.assertEqual(res["status"], "REJECTED_MISSING_EVIDENCE")
        self.assertEqual(gate.state, "HOLD_BLUEPRINT")

    def test_03_occupied_zone_defers_rather_than_bypasses_realization(self) -> None:
        gate = LightBridgeDeterministicGate("LB-TEST-03", hold_tau_max=14.0)
        gate.enter_zone("PLAYER-A")
        deferred = gate.attempt_open("EV-001")
        self.assertEqual(deferred["status"], "DEFERRED_ZONE_OCCUPIED")
        self.assertFalse(gate.collision_enabled)
        gate.exit_zone("PLAYER-A")
        self.assertEqual(gate.state, "OPEN_REALIZED")
        self.assertTrue(gate.collision_enabled)

        # Post-mortem sovereignty guard: if occupancy stalls past hold_tau_max,
        # P_INT -> P_EXT purges pending_evidence_id so later zone exit cannot open bridge.
        stalled = LightBridgeDeterministicGate("LB-TEST-03-STALL", hold_tau_max=14.0)
        stalled.enter_zone("PLAYER-STALL")
        self.assertEqual(stalled.attempt_open("EV-STALE")["status"], "DEFERRED_ZONE_OCCUPIED")
        stalled.advance_hold_clock(3.0)
        forfeit = stalled.advance_hold_clock(12.0)  # t = 15.0 s > 14.0 s
        self.assertEqual(forfeit["status"], "HOLD_DEADLINE_FORFEITED")
        self.assertEqual(stalled.hold_jurisdiction, "P_EXT")
        self.assertEqual(stalled.pending_evidence_id, "")
        self.assertIsNone(stalled.exit_zone("PLAYER-STALL"))  # t = 15.1 s exit
        self.assertEqual(stalled.state, "HOLD_BLUEPRINT")
        self.assertFalse(stalled.collision_enabled)
        self.assertEqual(stalled.modeled_voltage_v, 0.00)

    def test_04_kill_and_gate_capture_neutrality_guard(self) -> None:
        gate = LightBridgeDeterministicGate("LB-TEST-04")
        neutral = gate.audit_gate_neutrality("OMEGA_STD_V1", "omega_std_v1")
        self.assertTrue(neutral["neutral"])
        self.assertEqual(gate.state, "HOLD_BLUEPRINT")

        gate.enter_zone("PLAYER-B")
        gate.attempt_open("EV-002")
        capture = gate.audit_gate_neutrality("OMEGA_STD_V1", "OMEGA_CAPTURED_BYPASS")
        self.assertFalse(capture["neutral"])
        self.assertEqual(capture["status"], "KILL_GATE_CAPTURE")
        self.assertEqual(gate.state, "KILL_ABORTED")
        self.assertTrue(gate.is_kill_latched)
        self.assertFalse(gate.collision_enabled)
        self.assertEqual(gate.pending_evidence_id, "")
        gate.exit_zone("PLAYER-B")
        self.assertEqual(gate.state, "KILL_ABORTED")
        self.assertEqual(gate.attempt_open("EV-003")["status"], "REJECTED_LATCHED_KILL")

    def test_05_reset_appends_to_witness_history_without_erasing(self) -> None:
        gate = LightBridgeDeterministicGate("LB-TEST-05")
        gate.trigger_kill("TEST_KILL")
        before = len(gate.witness_history)
        gate.reset_bridge("RESET_TEST")
        self.assertGreater(len(gate.witness_history), before)
        self.assertEqual(gate.state, "HOLD_BLUEPRINT")
        self.assertEqual(gate.hold_jurisdiction, "P_INT")
        self.assertFalse(gate.is_kill_latched)
        self.assertTrue(gate.verify_witness_chain())

    def test_06_fixture_evaluation_and_authority_bounds(self) -> None:
        snap = evaluate_fixture(FIXTURE)
        self.assertEqual(snap.measurement_status, "OPEN")
        self.assertEqual(snap.claim_status, "HOLD")
        self.assertEqual(snap.hold_jurisdiction, "P_INT")
        self.assertEqual(snap.physical_authority, "NONE")
        self.assertTrue(all(snap.invariants_verified.values()))


if __name__ == "__main__":
    unittest.main()
