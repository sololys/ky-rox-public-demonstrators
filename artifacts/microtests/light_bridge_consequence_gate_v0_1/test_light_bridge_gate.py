from __future__ import annotations

import json
from pathlib import Path
import unittest

from light_bridge_gate import LightBridgeDeterministicGate, evaluate_fixture


FIXTURE = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))


class LightBridgeConsequenceGateMicrotest(unittest.TestCase):
    def test_01_hold_never_transitions_to_open_by_time(self) -> None:
        gate = LightBridgeDeterministicGate("LB-TEST-01")
        gate.tick_time(86400.0)
        self.assertEqual(gate.state, "HOLD_BLUEPRINT")
        self.assertFalse(gate.collision_enabled)

    def test_02_open_requires_nonempty_explicit_evidence(self) -> None:
        gate = LightBridgeDeterministicGate("LB-TEST-02")
        res = gate.attempt_open("   ")
        self.assertEqual(res["status"], "REJECTED_MISSING_EVIDENCE")
        self.assertEqual(gate.state, "HOLD_BLUEPRINT")

    def test_03_occupied_zone_defers_rather_than_bypasses_realization(self) -> None:
        gate = LightBridgeDeterministicGate("LB-TEST-03")
        gate.enter_zone("PLAYER-A")
        deferred = gate.attempt_open("EV-001")
        self.assertEqual(deferred["status"], "DEFERRED_ZONE_OCCUPIED")
        self.assertFalse(gate.collision_enabled)
        gate.exit_zone("PLAYER-A")
        self.assertEqual(gate.state, "OPEN_REALIZED")
        self.assertTrue(gate.collision_enabled)

    def test_04_kill_disables_collision_and_cancels_pending_authorization(self) -> None:
        gate = LightBridgeDeterministicGate("LB-TEST-04")
        gate.enter_zone("PLAYER-B")
        gate.attempt_open("EV-002")
        gate.trigger_kill("ANOMALY")
        self.assertEqual(gate.state, "KILL_ABORTED")
        self.assertFalse(gate.collision_enabled)
        self.assertEqual(gate.pending_evidence_id, "")
        gate.exit_zone("PLAYER-B")
        self.assertEqual(gate.state, "KILL_ABORTED")

    def test_05_reset_appends_to_witness_history_without_erasing(self) -> None:
        gate = LightBridgeDeterministicGate("LB-TEST-05")
        gate.trigger_kill("TEST_KILL")
        before = len(gate.witness_history)
        gate.reset_bridge("RESET_TEST")
        self.assertGreater(len(gate.witness_history), before)
        self.assertEqual(gate.state, "HOLD_BLUEPRINT")
        self.assertFalse(gate.is_kill_latched)

    def test_06_fixture_evaluation_and_authority_bounds(self) -> None:
        snap = evaluate_fixture(FIXTURE)
        self.assertEqual(snap.measurement_status, "OPEN")
        self.assertEqual(snap.claim_status, "HOLD")
        self.assertEqual(snap.physical_authority, "NONE")
        self.assertTrue(all(snap.invariants_verified.values()))


if __name__ == "__main__":
    unittest.main()
