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
    hold_jurisdiction: str
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
    consequence-gate contract (light_bridge.gd), including:
      - No silent HOLD (delta_k rationale required)
      - Dual-Clock Law (time never opens HOLD; expiry forfeits P_INT -> P_EXT)
      - Explicit non-empty evidence_id required for OPEN
      - Occupancy clearance deferral
      - Gate-capture neutrality guard (Omega_1 != Omega_2 -> KILL_GATE_CAPTURE)
      - Append-only SHA-256 witness hash chain across KILL and RESET
    """

    def __init__(self, bridge_id: str = "LB-001", hold_tau_max: float = 14.0) -> None:
        self.bridge_id = bridge_id
        self.hold_tau_max = hold_tau_max
        self.state = "HOLD_BLUEPRINT"
        self.hold_jurisdiction = "P_INT"
        self.active_hold_delta_k = ""
        self.hold_elapsed_time = 0.0
        self.is_hold_deadline_forfeited = False
        self.collision_enabled = False
        self.modeled_voltage_v = 0.00
        self.is_kill_latched = False
        self.occupants: list[str] = []
        self.pending_evidence_id: str = ""
        self.active_evidence_id: str = ""
        self.witness_history: list[dict[str, Any]] = []
        self.last_hash = "0" * 64
        self.set_to_hold("INIT_PROPOSAL", "Initial placement of Light Bridge candidate")

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
        record = dict(payload)
        record["event_hash"] = digest
        self.last_hash = digest
        self.witness_history.append(record)
        return record

    def verify_witness_chain(self) -> bool:
        expected_prev = "0" * 64
        for idx, entry in enumerate(self.witness_history):
            if entry.get("sequence_number") != idx:
                return False
            if entry.get("previous_hash") != expected_prev:
                return False
            check_payload = {
                "action_type": entry["action_type"],
                "bridge_id": entry["bridge_id"],
                "details": entry["details"],
                "previous_hash": entry["previous_hash"],
                "sequence_number": entry["sequence_number"],
                "system_disclaimer": entry["system_disclaimer"],
            }
            canonical = json.dumps(check_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            recomputed = hashlib.sha256(canonical).hexdigest()
            if recomputed != entry.get("event_hash"):
                return False
            expected_prev = recomputed
        return expected_prev == self.last_hash

    def set_to_hold(
        self,
        proposal_id: str,
        rationale: str = "",
    ) -> dict[str, Any] | bool:
        clean_rationale = rationale.strip()
        if not clean_rationale:
            self.collision_enabled = False
            self.modeled_voltage_v = 0.00
            self.hold_jurisdiction = "P_EXT"
            self._append_witness(
                "REJECTED_SILENT_HOLD",
                {
                    "collision_enabled": False,
                    "delta_k": "EMPTY",
                    "hold_jurisdiction": self.hold_jurisdiction,
                    "modeled_voltage_v": 0.00,
                    "proposal_id": proposal_id,
                    "state": "HOLD_BLUEPRINT",
                },
            )
            return False

        self.state = "HOLD_BLUEPRINT"
        self.collision_enabled = False
        self.modeled_voltage_v = 0.00
        self.hold_elapsed_time = 0.0
        self.hold_jurisdiction = "P_INT"
        self.active_hold_delta_k = clean_rationale
        self.is_hold_deadline_forfeited = False
        return self._append_witness(
            "SET_TO_HOLD",
            {
                "collision_enabled": False,
                "delta_k": clean_rationale,
                "hold_jurisdiction": self.hold_jurisdiction,
                "modeled_voltage_v": 0.00,
                "proposal_id": proposal_id,
                "state": self.state,
            },
        )

    def advance_hold_clock(self, delta_seconds: float) -> dict[str, Any]:
        if delta_seconds < 0.0:
            raise ValueError("negative_time_delta")
        if self.state != "HOLD_BLUEPRINT":
            return {
                "status": "NOT_IN_HOLD",
                "hold_jurisdiction": self.hold_jurisdiction,
                "open_authorized": self.state == "OPEN_REALIZED",
            }

        # First Clock Law: HOLD never transitions to OPEN merely because time passes
        self.hold_elapsed_time += delta_seconds
        self.collision_enabled = False
        self.modeled_voltage_v = 0.00

        # Second Clock Law: stalling past hold_tau_max forfeits P_INT -> P_EXT and purges pending warrant
        if (
            self.hold_tau_max > 0.0
            and self.hold_elapsed_time > self.hold_tau_max
            and self.hold_jurisdiction == "P_INT"
            and not self.is_hold_deadline_forfeited
        ):
            had_pending = bool(self.pending_evidence_id)
            self.pending_evidence_id = ""
            self.hold_jurisdiction = "P_EXT"
            self.is_hold_deadline_forfeited = True
            record = self._append_witness(
                "HOLD_DEADLINE_FORFEITED",
                {
                    "collision_enabled": False,
                    "delta_k": self.active_hold_delta_k,
                    "elapsed_tau": self.hold_elapsed_time,
                    "hold_jurisdiction": "P_EXT",
                    "hold_tau_max": self.hold_tau_max,
                    "modeled_voltage_v": 0.00,
                    "open_authorized": False,
                    "pending_clearance_stalled": had_pending,
                    "pending_evidence_purged": had_pending,
                    "previous_jurisdiction": "P_INT",
                    "state": "HOLD_BLUEPRINT",
                },
            )
            return {
                "status": "HOLD_DEADLINE_FORFEITED",
                "hold_jurisdiction": self.hold_jurisdiction,
                "open_authorized": False,
                "pending_evidence_purged": had_pending,
                "witness": record,
            }

        return {
            "status": "HOLD_ACTIVE",
            "hold_jurisdiction": self.hold_jurisdiction,
            "open_authorized": False,
        }

    def tick_time(self, delta_seconds: float) -> str:
        self.advance_hold_clock(delta_seconds)
        return self.state

    def audit_gate_neutrality(self, omega_a: str, omega_b: str) -> dict[str, Any]:
        rule_a = omega_a.strip().upper()
        rule_b = omega_b.strip().upper()
        if not rule_a or not rule_b or rule_a != rule_b:
            kill_rec = self.trigger_kill("KILL_GATE_CAPTURE")
            return {
                "neutral": False,
                "status": "KILL_GATE_CAPTURE",
                "omega_a": rule_a,
                "omega_b": rule_b,
                "witness": kill_rec,
            }
        return {
            "neutral": True,
            "status": "VALID_NEUTRAL_GATE",
            "omega_a": rule_a,
            "omega_b": rule_b,
        }

    def enter_zone(self, body_id: str) -> None:
        if not body_id.strip():
            raise ValueError("empty_body_id")
        if body_id not in self.occupants:
            self.occupants.append(body_id)

    def exit_zone(self, body_id: str) -> dict[str, Any] | None:
        if body_id in self.occupants:
            self.occupants.remove(body_id)
        if (
            not self.occupants
            and self.pending_evidence_id
            and self.hold_jurisdiction == "P_INT"
            and not self.is_hold_deadline_forfeited
        ):
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
            self.active_hold_delta_k = "ZONE_OCCUPIED_BY_PLAYER"
            self.hold_elapsed_time = 0.0
            self.hold_jurisdiction = "P_INT"
            self.is_hold_deadline_forfeited = False
            return {"status": "DEFERRED_ZONE_OCCUPIED", "state": self.state}
        return self._apply_open(cleaned)

    def _apply_open(self, evidence_id: str) -> dict[str, Any]:
        self.state = "OPEN_REALIZED"
        self.collision_enabled = True
        self.modeled_voltage_v = 5.00
        self.hold_elapsed_time = 0.0
        self.is_hold_deadline_forfeited = False
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
        self.hold_elapsed_time = 0.0
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
        clean_reason = reason.strip() or "USER_CANVAS_RESET"
        self.is_kill_latched = False
        self.pending_evidence_id = ""
        self._append_witness(
            "RESET_CANVAS",
            {
                "is_kill_latched": False,
                "modeled_voltage_v": 0.00,
                "reason": clean_reason,
                "state": "HOLD_BLUEPRINT",
            },
        )
        res = self.set_to_hold("RESET_PROPOSAL", clean_reason)
        assert isinstance(res, dict)
        return res


def evaluate_fixture(fixture: dict[str, Any]) -> BridgeSnapshot:
    gate = LightBridgeDeterministicGate(fixture.get("bridge_id", "LB-PUBLIC-001"))

    # Verify silent HOLD is rejected with P_EXT escalation while staying de-energized
    silent_res = gate.set_to_hold("PROP-SILENT", "   ")
    inv_silent_hold_rejected = (
        silent_res is False
        and gate.hold_jurisdiction == "P_EXT"
        and not gate.collision_enabled
        and gate.modeled_voltage_v == 0.00
    )
    gate.set_to_hold("PROP-RESTORE", "Await explicit witness packet")

    # Verify Dual-Clock Law: time passage never opens HOLD, stalling forfeits P_INT -> P_EXT,
    # and any pending clearance warrant is purged so post-mortem zone exit cannot open bridge
    gate.enter_zone("PLAYER-STALL")
    gate.attempt_open("EV-STALE-001")
    clock_res = gate.advance_hold_clock(3600.0)
    post_exit = gate.exit_zone("PLAYER-STALL")
    inv_hold_time = (
        gate.state == "HOLD_BLUEPRINT"
        and not gate.collision_enabled
        and gate.modeled_voltage_v == 0.00
    )
    inv_dual_clock_forfeit = (
        clock_res["status"] == "HOLD_DEADLINE_FORFEITED"
        and clock_res["pending_evidence_purged"] is True
        and gate.pending_evidence_id == ""
        and post_exit is None
        and gate.hold_jurisdiction == "P_EXT"
        and not clock_res["open_authorized"]
        and not gate.collision_enabled
    )

    # Verify OPEN requires non-empty explicit evidence
    res_empty = gate.attempt_open("   ")
    inv_explicit_evidence = (res_empty["status"] == "REJECTED_MISSING_EVIDENCE" and gate.state == "HOLD_BLUEPRINT")

    # Verify occupied zone defers realization until clearance
    gate.enter_zone("PLAYER-1")
    res_deferred = gate.attempt_open("EV-VALID-001")
    was_deferred = (res_deferred["status"] == "DEFERRED_ZONE_OCCUPIED" and gate.state == "HOLD_BLUEPRINT")
    gate.exit_zone("PLAYER-1")
    opened_after_clearance = (gate.state == "OPEN_REALIZED" and gate.collision_enabled)
    inv_occupancy_deferral = (was_deferred and opened_after_clearance)

    # Verify asymmetric consequence rules (Omega_1 != Omega_2) trigger sticky KILL_GATE_CAPTURE
    gate.enter_zone("PLAYER-1")
    capture_res = gate.audit_gate_neutrality("OMEGA_STRICT_V1", "OMEGA_PRIVILEGED_BYPASS")
    inv_gate_capture_kill = (
        not capture_res["neutral"]
        and capture_res["status"] == "KILL_GATE_CAPTURE"
        and gate.state == "KILL_ABORTED"
        and not gate.collision_enabled
        and gate.is_kill_latched
        and gate.pending_evidence_id == ""
    )
    gate.exit_zone("PLAYER-1")

    # Verify Reset appends to witness history without erasing it, restoring P_INT HOLD
    count_before_reset = len(gate.witness_history)
    gate.reset_bridge("CANVAS_RESET")
    inv_append_only_reset = (
        len(gate.witness_history) > count_before_reset
        and gate.state == "HOLD_BLUEPRINT"
        and gate.hold_jurisdiction == "P_INT"
        and not gate.is_kill_latched
    )

    inv_witness_chain = gate.verify_witness_chain()

    invariants = {
        "append_only_reset": inv_append_only_reset,
        "dual_clock_deadline_forfeits_and_purges_pending": inv_dual_clock_forfeit,
        "explicit_evidence_required": inv_explicit_evidence,
        "gate_capture_asymmetry_triggers_kill": inv_gate_capture_kill,
        "hold_never_opens_by_time": inv_hold_time,
        "kill_disables_collision_and_cancels_pending": inv_gate_capture_kill,
        "occupied_zone_defers_realization": inv_occupancy_deferral,
        "silent_hold_rejected": inv_silent_hold_rejected,
        "witness_chain_intact": inv_witness_chain,
    }
    all_ok = all(invariants.values())

    return BridgeSnapshot(
        status="HOLD" if all_ok else "KILL",
        measurement_status="OPEN" if all_ok else "KILL",
        claim_status="HOLD",
        final_bridge_state=gate.state,
        hold_jurisdiction=gate.hold_jurisdiction,
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
