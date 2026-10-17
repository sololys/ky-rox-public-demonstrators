from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BridgeSnapshot:
    status: str
    measurement_status: str
    claim_status: str
    final_bridge_state: str
    collision_enabled: bool
    modeled_voltage_v: float
    is_kill_latched: bool
    witness_count: int
    final_witness_hash: str
    invariants_verified: dict[str, bool]
    physical_authority: str = "NONE"
    operational_authority: str = "NONE"
    claim: str = "Bounded software consequence-gate state machine only"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LightBridgeDeterministicGate:
    """
    Deterministic reference verifier for the Godot 4 LightBridgeActor
    consequence-gate contract (light_bridge.gd).
    """

    def __init__(self, bridge_id: str = "LB-001") -> None:
        self.bridge_id = bridge_id
        self.state = "HOLD_BLUEPRINT"
        self.collision_enabled = False
        self.modeled_voltage_v = 0.00
        self.is_kill_latched = False
        self.occupants: list[str] = []
        self.pending_evidence_id: str = ""
        self.active_evidence_id: str = ""
        self.witness_history: list[dict[str, Any]] = []
        self.last_hash = "0" * 64
        self.set_to_hold("INIT_PROPOSAL")

    def _append_witness(self, action_type: str, details: dict[str, Any]) -> dict[str, Any]:
        seq = len(self.witness_history)
        payload = {
            "action_type": action_type,
            "bridge_id": self.bridge_id,
            "details": details,
            "previous_hash": self.last_hash,
            "sequence_number": seq,
            "system_disclaimer": "MODELED_SOFTWARE_STATE_NOT_PHYSICAL_WORM",
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        payload["event_hash"] = digest
        self.last_hash = digest
        self.witness_history.append(payload)
        return payload

    def set_to_hold(self, proposal_id: str) -> dict[str, Any]:
        self.state = "HOLD_BLUEPRINT"
        self.collision_enabled = False
        self.modeled_voltage_v = 0.00
        return self._append_witness(
            "SET_TO_HOLD",
            {
                "collision_enabled": False,
                "modeled_voltage_v": 0.00,
                "proposal_id": proposal_id,
                "state": self.state,
            },
        )

    def tick_time(self, delta_seconds: float) -> str:
        if delta_seconds < 0.0:
            raise ValueError("negative_time_delta")
        # Invariant 1: HOLD never transitions to OPEN merely because time passes
        return self.state

    def enter_zone(self, body_id: str) -> None:
        if not body_id.strip():
            raise ValueError("empty_body_id")
        if body_id not in self.occupants:
            self.occupants.append(body_id)

    def exit_zone(self, body_id: str) -> dict[str, Any] | None:
        if body_id in self.occupants:
            self.occupants.remove(body_id)
        if not self.occupants and self.pending_evidence_id:
            ev = self.pending_evidence_id
            self.pending_evidence_id = ""
            return self._apply_open(ev)
        return None

    def attempt_open(self, evidence_id: str) -> dict[str, Any]:
        cleaned = evidence_id.strip()
        # Invariant 2: OPEN requires a non-empty explicit evidence ID
        if not cleaned:
            return {"status": "REJECTED_MISSING_EVIDENCE", "state": self.state}
        if self.is_kill_latched or self.state == "KILL_ABORTED":
            return {"status": "REJECTED_LATCHED_KILL", "state": self.state}
        if self.state == "OPEN_REALIZED":
            return {"status": "ALREADY_OPEN", "state": self.state}
        # Invariant 3: An occupied bridge zone defers, rather than bypasses, realization
        if self.occupants:
            self.pending_evidence_id = cleaned
            return {"status": "DEFERRED_ZONE_OCCUPIED", "state": self.state}
        return self._apply_open(cleaned)

    def _apply_open(self, evidence_id: str) -> dict[str, Any]:
        self.state = "OPEN_REALIZED"
        self.collision_enabled = True
        self.modeled_voltage_v = 5.00
        self.active_evidence_id = evidence_id
        record = self._append_witness(
            "AUTHORIZE_OPEN",
            {
                "collision_enabled": True,
                "evidence_id": evidence_id,
                "modeled_voltage_v": 5.00,
                "state": self.state,
            },
        )
        return {"status": "AUTHORIZED_OPEN", "state": self.state, "witness": record}

    def trigger_kill(self, reason: str = "EMERGENCY_FAIL_CLOSED") -> dict[str, Any]:
        # Invariant 4: KILL disables collision and cancels pending authorization
        self.state = "KILL_ABORTED"
        self.is_kill_latched = True
        self.collision_enabled = False
        self.modeled_voltage_v = 0.00
        self.pending_evidence_id = ""
        return self._append_witness(
            "KILL_COLLAPSE",
            {
                "collision_enabled": False,
                "is_kill_latched": True,
                "modeled_voltage_v": 0.00,
                "reason": reason,
                "state": self.state,
            },
        )

    def reset_bridge(self, reason: str = "USER_CANVAS_RESET") -> dict[str, Any]:
        # Invariant 5: Reset appends to the witness history; it does not erase it
        self.is_kill_latched = False
        self.pending_evidence_id = ""
        self._append_witness(
            "RESET_CANVAS",
            {
                "is_kill_latched": False,
                "modeled_voltage_v": 0.00,
                "reason": reason,
                "state": "HOLD_BLUEPRINT",
            },
        )
        return self.set_to_hold("RESET_PROPOSAL")


def evaluate_fixture(fixture: dict[str, Any]) -> BridgeSnapshot:
    gate = LightBridgeDeterministicGate(fixture.get("bridge_id", "LB-PUBLIC-001"))

    # Verify Invariant 1: time passage does not open HOLD
    gate.tick_time(3600.0)
    inv_hold_time = (gate.state == "HOLD_BLUEPRINT" and not gate.collision_enabled)

    # Verify Invariant 2: empty evidence rejected
    res_empty = gate.attempt_open("   ")
    inv_explicit_evidence = (res_empty["status"] == "REJECTED_MISSING_EVIDENCE" and gate.state == "HOLD_BLUEPRINT")

    # Verify Invariant 3: occupied zone defers realization until clearance
    gate.enter_zone("PLAYER-1")
    res_deferred = gate.attempt_open("EV-VALID-001")
    was_deferred = (res_deferred["status"] == "DEFERRED_ZONE_OCCUPIED" and gate.state == "HOLD_BLUEPRINT")
    gate.exit_zone("PLAYER-1")
    opened_after_clearance = (gate.state == "OPEN_REALIZED" and gate.collision_enabled)
    inv_occupancy_deferral = (was_deferred and opened_after_clearance)

    # Verify Invariant 4: KILL disables collision and cancels pending authorization
    gate.enter_zone("PLAYER-1")
    gate.trigger_kill("BOUNDARY_ANOMALY")
    inv_kill_guillotine = (
        gate.state == "KILL_ABORTED"
        and not gate.collision_enabled
        and gate.is_kill_latched
        and gate.pending_evidence_id == ""
    )

    # Verify Invariant 5: Reset appends to witness history without erasing it
    count_before_reset = len(gate.witness_history)
    gate.reset_bridge("CANVAS_RESET")
    inv_append_only_reset = (
        len(gate.witness_history) > count_before_reset
        and gate.state == "HOLD_BLUEPRINT"
        and not gate.is_kill_latched
    )

    invariants = {
        "append_only_reset": inv_append_only_reset,
        "explicit_evidence_required": inv_explicit_evidence,
        "hold_never_opens_by_time": inv_hold_time,
        "kill_disables_collision_and_cancels_pending": inv_kill_guillotine,
        "occupied_zone_defers_realization": inv_occupancy_deferral,
    }
    all_ok = all(invariants.values())

    return BridgeSnapshot(
        status="HOLD" if all_ok else "KILL",
        measurement_status="OPEN" if all_ok else "KILL",
        claim_status="HOLD",
        final_bridge_state=gate.state,
        collision_enabled=gate.collision_enabled,
        modeled_voltage_v=gate.modeled_voltage_v,
        is_kill_latched=gate.is_kill_latched,
        witness_count=len(gate.witness_history),
        final_witness_hash=gate.last_hash,
        invariants_verified=invariants,
    )


def main() -> None:
    fixture = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))
    result = evaluate_fixture(fixture)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
