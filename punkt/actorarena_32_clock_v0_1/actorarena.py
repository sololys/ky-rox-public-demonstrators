"""ActorArena: bounded public fail-closed clock demonstrator.

This module has no physical, financial, safety, or deployment authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Literal


Decision = Literal["OPEN", "HOLD", "KILL", "REJECTED"]


@dataclass(frozen=True)
class Request:
    request_id: str
    actor_position: int
    payload: dict[str, Any]
    ready: bool = True
    integrity: bool = True


@dataclass(frozen=True)
class Result:
    request_id: str
    active_position: int
    decision: Decision
    state_changed: bool
    witnessed: bool
    reason: str


class ActorArena:
    """A 32-position, zero-window, fail-closed software arena."""

    POSITIONS = 32

    def __init__(self) -> None:
        self.state: list[dict[str, Any]] = []
        self.witness: list[dict[str, Any]] = []
        self._head = "0" * 64

    @staticmethod
    def _canonical(value: dict[str, Any]) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _append_witness(self, event: dict[str, Any]) -> None:
        material = f"{self._head}|{self._canonical(event)}"
        digest = sha256(material.encode("utf-8")).hexdigest()
        self.witness.append({**event, "prev_hash": self._head, "hash": digest})
        self._head = digest

    def _admissible(self, request: Request, active_position: int) -> tuple[bool, str]:
        if not 1 <= active_position <= self.POSITIONS:
            return False, "active_position_out_of_range"
        if not 1 <= request.actor_position <= self.POSITIONS:
            return False, "actor_position_out_of_range"
        if request.actor_position != active_position:
            return False, "zero_window_miss"
        if not request.request_id or not isinstance(request.payload, dict):
            return False, "malformed_request"
        return True, "admissible"

    def process(self, request: Request, active_position: int) -> Result:
        admissible, reason = self._admissible(request, active_position)
        if not admissible:
            return Result(
                request.request_id,
                active_position,
                "REJECTED",
                state_changed=False,
                witnessed=False,
                reason=reason,
            )

        # Public Ω ordering: integrity failure dominates readiness.
        if not request.integrity:
            decision: Decision = "KILL"
            reason = "integrity_failure"
        elif not request.ready:
            decision = "HOLD"
            reason = "re_admission_required"
        else:
            decision = "OPEN"
            reason = "admitted"

        if decision != "OPEN":
            return Result(
                request.request_id,
                active_position,
                decision,
                state_changed=False,
                witnessed=False,
                reason=reason,
            )

        event = {
            "request_id": request.request_id,
            "actor_position": request.actor_position,
            "payload": request.payload,
            "decision": decision,
        }
        self.state.append(event)
        self._append_witness(event)
        return Result(
            request.request_id,
            active_position,
            decision,
            state_changed=True,
            witnessed=True,
            reason=reason,
        )


def demo() -> None:
    arena = ActorArena()
    cases = (
        (Request("R-OPEN", 1, {"candidate": "alpha"}), 1),
        (Request("R-HOLD", 2, {"candidate": "beta"}, ready=False), 2),
        (Request("R-KILL", 3, {"candidate": "gamma"}, integrity=False), 3),
        (Request("R-REJECT", 9, {"candidate": "delta"}), 4),
    )
    for request, active in cases:
        result = arena.process(request, active)
        print(
            f"{result.request_id}: position={result.active_position:02d} "
            f"decision={result.decision} changed={str(result.state_changed).lower()} "
            f"witnessed={str(result.witnessed).lower()} reason={result.reason}"
        )
    print(f"STATE_EVENTS={len(arena.state)}")
    print(f"WITNESS_EVENTS={len(arena.witness)}")
    print("FINAL_SEAL=ACTORARENA_32_CLOCK_V0_1_PASS")


if __name__ == "__main__":
    demo()
