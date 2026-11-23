#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sosionomos XOR/ROX Consequence Gate (v0.1) — 0 float, stdlib only.
Implements OMNI-KY & Sosionomos bridge: XOR pre-gate involution, ROX directional
seal, O(1) AnchorIndex, agency-preserving HOLD, mechanical backpressure, and
silent ShadowDAG TRAP isolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import json
from pathlib import Path


MASK_64 = (1 << 64) - 1
STATE_ZERO = 0x00
STATE_CANDIDATE = 0x01
STATE_REALIZED = 0x02
STATE_BOTH = 0x03

AMYGDALA_LUT: tuple[tuple[int, int], ...] = (
    (100, 0),
    (300, 5),
    (600, 20),
    (899, 60),
)
EXCITATION_KILL = 900
RHO_HARD = Fraction(3, 4)
RHO_KILL = Fraction(9, 10)


class Decision(Enum):
    OPEN = "OPEN"
    HOLD = "HOLD"
    KILL = "KILL"
    TRAP = "TRAP"


class NodeTemp(Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


def xor64(x: int, k: int) -> int:
    return (x ^ k) & MASK_64


def rox64(x: int, k: int, rot: int = 13) -> int:
    mixed = (x ^ k) & MASK_64
    return ((mixed << rot) | (mixed >> (64 - rot))) & MASK_64


def valid_state_xor(state_byte: int) -> bool:
    if state_byte not in (STATE_ZERO, STATE_CANDIDATE, STATE_REALIZED, STATE_BOTH):
        return False
    return ((state_byte & 1) ^ ((state_byte >> 1) & 1)) == 1


def double_pulse_ok(word: int, mask_out: int, mask_back: int) -> bool:
    return xor64(xor64(word, mask_out), mask_back) == (word & MASK_64)


def delay_ticks(excitation: int) -> int | None:
    if excitation >= EXCITATION_KILL:
        return None
    for upper, ticks in AMYGDALA_LUT:
        if excitation <= upper:
            return ticks
    return None


def sha256_json(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class Actor:
    actor_id: str
    seq_last: int = 0
    prev_hash: str = "0" * 64
    arena_capacity: int = 100
    used_in: int = 0
    trapped: bool = False
    kill_count: int = 0

    def pressure(self) -> Fraction:
        return Fraction(self.used_in, self.arena_capacity)

    def read_permit(self) -> int:
        return 0 if (self.trapped or self.pressure() >= RHO_HARD) else 1


@dataclass
class Candidate:
    actor_id: str
    payload: str
    parent_hash: str
    sequence: int
    excitation: int
    reach_n: int
    created_tick: int
    state_byte: int = STATE_CANDIDATE
    phase_word: int = 0x13579BDF2468ACE0
    mask_out: int = 0x55AA55AA55AA55AA
    mask_back: int = 0x55AA55AA55AA55AA

    def cand_hash(self, prev_hash: str) -> str:
        return sha256_json({
            "actor_id": self.actor_id,
            "parent_hash": self.parent_hash,
            "payload": self.payload,
            "prev_hash": prev_hash,
            "reach_n": self.reach_n,
            "sequence": self.sequence,
        })


class SosionomosXorRoxGate:
    def __init__(self) -> None:
        self.genesis = sha256_json({"genesis": "SOSIONOMOS_XOR_ROX_v0.1"})
        self.anchor_index: dict[str, NodeTemp] = {self.genesis: NodeTemp.HOT}
        self.public_dag: dict[str, dict] = {
            self.genesis: {"state": STATE_REALIZED, "payload": "GENESIS", "rox": 0}
        }
        self.shadow_dag: dict[str, list[dict]] = {}
        self.actors: dict[str, Actor] = {}
        self.witness: list[dict] = []

    def bootstrap(self, actor_id: str, arena_capacity: int = 100) -> Actor:
        a = Actor(actor_id=actor_id, arena_capacity=arena_capacity)
        self.actors[actor_id] = a
        return a

    def _witness(self, actor_id: str, chash: str, dec: Decision, tick: int, rox_seal: int) -> str:
        prev = self.witness[-1]["witness_hash"] if self.witness else "0" * 64
        rec = {
            "actor_id": actor_id,
            "cand_hash": chash,
            "decision": dec.value,
            "prev_witness": prev,
            "rox_seal": rox_seal,
            "tick": tick,
        }
        wh = sha256_json(rec)
        rec["witness_hash"] = wh
        self.witness.append(rec)
        return wh

    def verify_chain(self) -> bool:
        prev = "0" * 64
        for rec in self.witness:
            if rec["prev_witness"] != prev:
                return False
            body = {k: v for k, v in rec.items() if k != "witness_hash"}
            if sha256_json(body) != rec["witness_hash"]:
                return False
            prev = rec["witness_hash"]
        return True

    def cool(self, node_hash: str, temp: NodeTemp) -> None:
        self.anchor_index[node_hash] = temp
        if temp is NodeTemp.COLD:
            self.public_dag[node_hash]["payload"] = None

    def admit(self, c: Candidate, eval_tick: int) -> tuple[Decision, dict]:
        actor = self.actors[c.actor_id]
        chash = c.cand_hash(actor.prev_hash)

        if actor.pressure() >= RHO_KILL or actor.trapped:
            actor.trapped = True
            seal = rox64(c.phase_word, int(chash[:16], 16), rot=17)
            self.shadow_dag.setdefault(c.actor_id, []).append({"hash": chash, "seal": seal})
            self._witness(c.actor_id, chash, Decision.TRAP, eval_tick, seal)
            return Decision.TRAP, {"ack_shadow": True, "public": False}

        if not valid_state_xor(c.state_byte) or c.state_byte != STATE_CANDIDATE:
            actor.kill_count += 1
            self._witness(c.actor_id, chash, Decision.KILL, eval_tick, 0)
            return Decision.KILL, {"reason": "INVALID_STATE_SUPERPOSITION"}

        if not double_pulse_ok(c.phase_word, c.mask_out, c.mask_back):
            actor.kill_count += 1
            self._witness(c.actor_id, chash, Decision.KILL, eval_tick, 0)
            return Decision.KILL, {"reason": "MASK_MUTATED"}

        if c.parent_hash not in self.anchor_index:
            actor.kill_count += 1
            self._witness(c.actor_id, chash, Decision.KILL, eval_tick, 0)
            return Decision.KILL, {"reason": "ANCHOR_INVALID"}

        if c.sequence != actor.seq_last + 1:
            actor.kill_count += 1
            self._witness(c.actor_id, chash, Decision.KILL, eval_tick, 0)
            return Decision.KILL, {"reason": "SEQUENCE_INVALID"}

        req = delay_ticks(c.excitation)
        if req is None:
            actor.kill_count += 1
            self._witness(c.actor_id, chash, Decision.KILL, eval_tick, 0)
            return Decision.KILL, {"reason": "EXCITATION_OVER_MAX"}

        if (eval_tick - c.created_tick) < req:
            self._witness(c.actor_id, chash, Decision.HOLD, eval_tick, 0)
            return Decision.HOLD, {"remaining": req - (eval_tick - c.created_tick)}

        rox_seal = rox64(c.phase_word, int(chash[:16], 16), rot=13)
        actor.seq_last = c.sequence
        actor.prev_hash = chash
        self.anchor_index[chash] = NodeTemp.HOT
        self.public_dag[chash] = {
            "state": STATE_REALIZED,
            "parent": c.parent_hash,
            "payload": c.payload,
            "rox": rox_seal,
        }
        wh = self._witness(c.actor_id, chash, Decision.OPEN, eval_tick, rox_seal)
        return Decision.OPEN, {"node_hash": chash, "rox_seal": rox_seal, "witness_hash": wh}


def run_fixture() -> dict:
    fixture = json.loads((Path(__file__).resolve().parent / "FIXTURE.json").read_text(encoding="utf-8"))
    gate = SosionomosXorRoxGate()
    gate.bootstrap("alice")
    results = []
    last_public = gate.genesis

    for case in fixture["cases"]:
        aid = case["actor_id"]
        if aid not in gate.actors:
            a = gate.bootstrap(aid, arena_capacity=case.get("arena_capacity", 100))
            a.used_in = case.get("used_in", 0)
        c = Candidate(
            actor_id=aid,
            payload=case["payload"],
            parent_hash=last_public if aid == "alice" else gate.genesis,
            sequence=case["sequence"],
            excitation=case["excitation"],
            reach_n=case["reach_n"],
            created_tick=case["created_tick"],
            state_byte=case.get("state_byte", STATE_CANDIDATE),
            mask_out=case.get("mask_out", 0x55AA55AA55AA55AA),
            mask_back=case.get("mask_back", 0x55AA55AA55AA55AA),
        )
        dec, info = gate.admit(c, case["eval_tick"])
        if dec is Decision.OPEN:
            last_public = info["node_hash"]
        results.append({"id": case["id"], "decision": dec.value, "expected": case["expected"]})

    return {
        "gate": "SOSIONOMOS_XOR_ROX_v0.1",
        "arithmetic": "ZERO_FLOAT_EXACT",
        "public_nodes": len(gate.public_dag),
        "shadow_nodes": sum(len(v) for v in gate.shadow_dag.values()),
        "witness_chain_valid": gate.verify_chain(),
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(run_fixture(), indent=2, sort_keys=True))
