"""
Adversarial Capsule Gate Harness (L1 Software Gate, L1.5 iverilog Co-Sim & L2 PTY Wire Loopback)
Forener:
  1. fo_fc_axiom0_interlock_engine.py (F-O ⇄ F-C Partiell Operator P_{Sigma_A}: Sigma_A -> X)
  2. worm_archive_consolidation_engine.py (Kanonisk JSON, CapsuleLinkage & HMAC-SHA256)
  3. fpga_witness_ledger_engine.py (SPEC-213: 119 B W_PRE + 86 B W_POST binær C/SystemVerilog-pakking)
  4. L1.5 SystemVerilog Co-Simulering (iverilog / vvp mot fpga_capsule_frame_205b_decoder.sv)
  5. L2 Seriell Loopback over POSIX PTY (/dev/pts/*) i repetisjonsdomenet D_rep^{(1)}

Håndhever de 6 konstitusjonelle presiseringene under INSPIRED_BY != IMPLEMENTS != PROVES,
de 3 skjerpede L1-hjørnetilfellene, samt den to-trinns kausale silisium- og loopback-pipelinen.
"""

from __future__ import annotations

from collections import deque
import copy
from dataclasses import dataclass
import hashlib
import hmac
import json
import math
import os
import select
import struct
import subprocess
import tempfile
import termios
import tty
from typing import Any, Deque, Dict, List, Optional, Tuple

from fpga_witness_ledger_engine import (
    FINAL_STATUS_REALIZED,
    FINAL_STATUS_TERMINATED,
    GATE_DECISION_HOLD,
    GATE_DECISION_KILL,
    GATE_DECISION_OPEN,
    HPIS_LATCH_ENGAGED,
    HPIS_LATCH_ISOLATED,
    REASON_CODE_DRIFT_THRESHOLD_EXCEEDED,
    REASON_CODE_NOMINAL,
    W_POST_HASHABLE_FORMAT,
    W_PRE_HASHABLE_FORMAT,
    WitnessPostCommit,
    WitnessPreCommit,
    calculate_landauer_exhaust_nJ,
)


FIXED_POINT_SCALE = 1_000_000  # 10^6 mikro-enheter for eksakt tverrspråklig matrise-representasjon

# L2 Wire Protocol Constants (247-byte total packet wrapping the 205-byte FPGA pair)
WIRE_SYNC_BYTE_0 = 0xAA
WIRE_SYNC_BYTE_1 = 0x55
WIRE_HEADER_FORMAT = "<BBQ"  # sync0 (1B), sync1 (1B), seq_counter (8B) = 10 bytes
WIRE_PAYLOAD_SIZE = 119 + 86  # 205 bytes (W_PRE + W_POST)
WIRE_HMAC_SIZE = 32
WIRE_TOTAL_FRAME_SIZE = 10 + WIRE_PAYLOAD_SIZE + WIRE_HMAC_SIZE  # 247 bytes


def normalize_for_jcs(obj: Any) -> Any:
    """
    Kanonisk normalisering før RFC 8785 / JCS-serialisering:
      - Eliminerer IEEE 754 negativ null (-0.0 -> 0.0).
      - Avviser NaN og Infinity eksplisitt.
    """
    if isinstance(obj, dict):
        return {str(k): normalize_for_jcs(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [normalize_for_jcs(v) for v in obj]
    if isinstance(obj, bool) or obj is None or isinstance(obj, (str, int)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("NON_FINITE_FLOAT_FORBIDDEN_IN_JCS")
        if obj == 0.0:
            return 0.0  # Tvinger -0.0 til +0.0 (positiv null)
        return round(obj, 9)
    return obj


def canonical_json_bytes(obj: Any) -> bytes:
    """
    Kanonisk JSON-serialisering (RFC 8785-stil: normalisert -0.0 -> 0.0, sorterte nøkler,
    ingen ekstra whitespace, strengt forbud mot NaN/Infinity).
    """
    normalized = normalize_for_jcs(obj)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_matrix_fixed_point_bytes(candidate: Dict[str, Any]) -> bytes:
    """
    Konverterer numeriske metrikker i kandidaten til eksakte heltalls mikro-enheter (10^6)
    slik at C, Rust, Python og SystemVerilog produserer identisk hash uavhengig av
    flyttallsformatering (-0.0 vs 0.0, 947 vs 947.0).
    """
    numeric_keys = {
        "risk",
        "irreversibility",
        "model_uncertainty",
        "identity_residual",
        "hardware_inconsistency",
        "total_mass_kg",
    }
    canonical_map: Dict[str, Any] = {}
    for k, v in candidate.items():
        if k in numeric_keys and isinstance(v, (int, float)) and not isinstance(v, bool):
            val = 0.0 if float(v) == 0.0 else float(v)
            canonical_map[f"{k}_micro"] = int(round(val * FIXED_POINT_SCALE))
        else:
            canonical_map[k] = normalize_for_jcs(v)
    return canonical_json_bytes(canonical_map)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class GateSpec:
    """Grenseverdier som definerer det admissible delrommet A ⊂ C."""
    r_max: float = 0.50
    i_max: float = 0.40
    u_max: float = 0.30
    epsilon_max: float = 0.05
    hw_tol_max: float = 0.00
    nominal_mass_kg: float = 947.0
    mass_tolerance_kg: float = 0.05
    hold_max_decay_sec: float = 30.0
    max_failures_per_window: int = 3


@dataclass(frozen=True)
class PreWitness:
    """
    To-fase vitne Fase 1 (W_pre): Utstedt av projeksjonsporten Pi_A over Sigma_A = Sigma ∩ A
    FØR konsekvensporten Omega kan vurderes. Inkluderer monotont stigende seq_counter.
    """
    event_id: str
    nonce: str
    seq_counter: int
    matrix_hash: str
    logic_hash: str
    pre_state_digest: str
    verdict: str
    warrant_hmac: str


@dataclass(frozen=True)
class GateExecutionReceipt:
    """
    To-fase vitne Fase 2 (W_post): Forseglet ETTER at d_k og aktuator-tilbakemelding a_k er målt.
    """
    status: str                  # SIMULATED_EFFECT | HOLD | KILL | KILL_DECAY_TIMEOUT | INTERLOCK_MISMATCH | TRAP | ERR_UNSEALED_ACTUATION
    gate_verdict: str            # OPEN | HOLD | KILL | TRAP
    commanded_voltage_v: float   # 5.00 V DC kun ved OPEN, 0.00 V DC ved både HOLD, KILL og TRAP
    impedance_state: str         # ACTIVE_LOAD | HIGH_Z_TIMED | LOW_Z_CROWBAR | LOW_Z_LATCHED_TRAP
    seq_counter: int             # Monoton maskinvare/epoke-teller C_hw
    pre_state_digest: str
    post_state_digest: str
    capsule_linkage: str         # H(Matrix) || H(Logic) || H(Execution)
    reason: str
    fpga_w_pre_bytes: bytes      # 119-byte SPEC-213 WitnessPreCommit C-struct
    fpga_w_post_bytes: bytes     # 86-byte SPEC-213 WitnessPostCommit C-struct


class AdversarialCapsuleGateMachine:
    """
    Falsifiserbar L1-tilstandsmaskin som implementerer P_{Sigma_A}: Sigma_A -> X,
    CapsuleLinkage, to-fase vitne (W_pre / W_post), INTERLOCK_MISMATCH, TRAP-lås,
    monotont stigende epoketeller (motvirker ringbuffer-eviction) og binær SPEC-213 C-struct-eksport.
    """

    REQUIRED_FIELDS = (
        "event_id",
        "nonce",
        "risk",
        "irreversibility",
        "model_uncertainty",
        "identity_residual",
        "hardware_inconsistency",
        "total_mass_kg",
        "evidence_present",
    )

    def __init__(
        self,
        hmac_key: bytes = b"L1_CONSTITUTIONAL_GATE_KEY_2026",
        spec: Optional[GateSpec] = None,
        nonce_window_size: int = 256,
    ) -> None:
        self._hmac_key = hmac_key
        self.spec = spec or GateSpec()
        self._state: Dict[str, Any] = {
            "phase": "x_n+10",
            "total_mass_kg": 947.0,
            "pressure_bar": 145.0,
            "committed_steps": 0,
            "metadata": {"vessel": "IBSEN_DIVE", "anchors": ["0xFFFA", "DOOR_27"]},
        }
        self.trapped: bool = False
        self.trap_reason: str = ""
        self.recent_failures: int = 0
        self.issued_seq_counter: int = 0
        self.committed_hw_counter: int = 0
        self.used_nonces: Deque[str] = deque(maxlen=nonce_window_size)
        self.used_event_ids: Deque[str] = deque(maxlen=nonce_window_size)
        self.wal_chain: List[Dict[str, Any]] = []
        self.hold_registry: Dict[str, Dict[str, Any]] = {}
        self.fpga_anchor_hash: bytes = hashlib.sha256(b"WORM_GENESIS_2026_PHRONESIS_CORE").digest()
        self.fpga_pre_ledger: List[WitnessPreCommit] = []
        self.fpga_post_ledger: List[WitnessPostCommit] = []

    @property
    def state(self) -> Dict[str, Any]:
        """Returnerer alltid en dypkopiert struktur for full referanse-isolasjon."""
        return copy.deepcopy(self._state)

    def state_digest(self) -> str:
        return sha256_hex(canonical_json_bytes(self._state))

    def logic_digest(self) -> str:
        return sha256_hex(canonical_json_bytes(self.spec.__dict__))

    def _sign_hmac(self, message: bytes) -> str:
        return hmac.new(self._hmac_key, message, hashlib.sha256).hexdigest()

    def _contains_non_finite_or_bool_num(self, payload: Dict[str, Any]) -> Optional[str]:
        """Oppdager NaN, Inf eller bool-som-int (PEP 285 B ⊥ Z brudd) i numeriske felt."""
        numeric_keys = (
            "risk",
            "irreversibility",
            "model_uncertainty",
            "identity_residual",
            "hardware_inconsistency",
            "total_mass_kg",
        )
        for k in numeric_keys:
            if k in payload:
                val = payload[k]
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    return f"TYPE_CONTAMINATION_{k}"
                if math.isnan(val) or math.isinf(val):
                    return f"NON_FINITE_{k}"
        return None

    def project_pi_a(
        self,
        candidate: Dict[str, Any],
        timestamp_sec: float = 0.0,
    ) -> Tuple[str, Optional[PreWitness], str]:
        """
        Steg 1: Partiell projeksjon Pi_A over kandidatrommet C -> Sigma_A = Sigma ∩ A.
        Returnerer (verdict, PreWitness | None, årsak).
        Allokerer ALDRI i used_nonces ved avvisning eller feil (forhindrer ringbuffer-eviction).
        """
        if self.trapped:
            return "TRAP", None, f"GATE_LATCHED_IN_TRAP:{self.trap_reason}"

        isolated_candidate = copy.deepcopy(candidate)

        structural_fault = self._contains_non_finite_or_bool_num(isolated_candidate)
        if structural_fault is not None:
            self._enter_trap(f"STRUCTURAL_INTEGRITY_BREACH:{structural_fault}")
            return "TRAP", None, self.trap_reason

        missing = [f for f in self.REQUIRED_FIELDS if f not in isolated_candidate or isolated_candidate[f] is None]
        if missing:
            event_id = str(isolated_candidate.get("event_id", "MISSING_ID"))
            self.hold_registry[event_id] = {
                "entered_at_sec": float(timestamp_sec),
                "reason": f"MISSING_SCHEMA_FIELDS:{','.join(missing)}",
            }
            return "HOLD", None, f"MISSING_SCHEMA_FIELDS:{','.join(missing)}"

        if isolated_candidate["evidence_present"] is not True:
            event_id = str(isolated_candidate["event_id"])
            self.hold_registry[event_id] = {
                "entered_at_sec": float(timestamp_sec),
                "reason": "MISSING_EXTERNAL_EVIDENCE",
            }
            return "HOLD", None, "MISSING_EXTERNAL_EVIDENCE"

        s = self.spec
        violations: List[str] = []
        if isolated_candidate["risk"] > s.r_max:
            violations.append("g1_risk")
        if isolated_candidate["irreversibility"] > s.i_max:
            violations.append("g2_irreversibility")
        if isolated_candidate["model_uncertainty"] > s.u_max:
            violations.append("g3_model_uncertainty")
        if isolated_candidate["identity_residual"] > s.epsilon_max:
            violations.append("g4_identity_residual")
        if isolated_candidate["hardware_inconsistency"] > s.hw_tol_max:
            violations.append("g5_hw_inconsistency")
        if abs(isolated_candidate["total_mass_kg"] - s.nominal_mass_kg) > s.mass_tolerance_kg:
            violations.append("g6_mass_tolerance")

        if violations:
            self.recent_failures += 1
            if self.recent_failures > s.max_failures_per_window:
                self._enter_trap("BRUTE_FORCE_RATE_LIMIT_EXCEEDED")
                return "TRAP", None, self.trap_reason
            return "KILL", None, f"OUT_OF_BOUNDS_A:{','.join(violations)}"

        self.issued_seq_counter += 1
        seq_counter = self.issued_seq_counter
        matrix_hash = sha256_hex(canonical_matrix_fixed_point_bytes(isolated_candidate))
        logic_hash = self.logic_digest()
        pre_digest = self.state_digest()
        event_id = str(isolated_candidate["event_id"])
        nonce = str(isolated_candidate["nonce"])

        warrant_payload = canonical_json_bytes({
            "event_id": event_id,
            "logic_hash": logic_hash,
            "matrix_hash": matrix_hash,
            "nonce": nonce,
            "pre_state_digest": pre_digest,
            "seq_counter": seq_counter,
            "verdict": "OPEN",
        })
        warrant_hmac = self._sign_hmac(warrant_payload)

        w_pre = PreWitness(
            event_id=event_id,
            nonce=nonce,
            seq_counter=seq_counter,
            matrix_hash=matrix_hash,
            logic_hash=logic_hash,
            pre_state_digest=pre_digest,
            verdict="OPEN",
            warrant_hmac=warrant_hmac,
        )
        return "OPEN", w_pre, "ADMISSIBLE_IN_SIGMA_A"

    def evaluate_hold_decay(self, event_id: str, current_time_sec: float) -> GateExecutionReceipt:
        """
        Håndhever tidsforfall i karantene: lim_{dt -> T_max} HOLD = KILL (KILL_DECAY_TIMEOUT).
        HOLD går ALDRI over til OPEN av at tiden går.
        """
        pre_digest = self.state_digest()
        if event_id not in self.hold_registry:
            return self._build_receipt(
                status="KILL",
                gate_verdict="KILL",
                voltage=0.00,
                impedance="LOW_Z_CROWBAR",
                pre_digest=pre_digest,
                post_digest=pre_digest,
                matrix_hash=sha256_hex(b"UNKNOWN_HOLD_ID"),
                kernel_drift=0.05,
                reason="UNKNOWN_HOLD_EVENT_ID",
            )

        entry = self.hold_registry[event_id]
        elapsed = current_time_sec - float(entry["entered_at_sec"])
        if elapsed >= self.spec.hold_max_decay_sec:
            del self.hold_registry[event_id]
            return self._build_receipt(
                status="KILL_DECAY_TIMEOUT",
                gate_verdict="KILL",
                voltage=0.00,
                impedance="LOW_Z_CROWBAR",
                pre_digest=pre_digest,
                post_digest=pre_digest,
                matrix_hash=sha256_hex(event_id.encode("utf-8")),
                kernel_drift=0.05,
                reason=f"HOLD_DECAY_EXPIRED:{elapsed:.1f}s>={self.spec.hold_max_decay_sec:.1f}s",
            )

        return self._build_receipt(
            status="HOLD",
            gate_verdict="HOLD",
            voltage=0.00,
            impedance="HIGH_Z_TIMED",
            pre_digest=pre_digest,
            post_digest=pre_digest,
            matrix_hash=sha256_hex(event_id.encode("utf-8")),
            kernel_drift=0.01,
            reason=f"STILL_IN_HOLD:{elapsed:.1f}s<{self.spec.hold_max_decay_sec:.1f}s",
        )

    def execute_omega(
        self,
        candidate: Dict[str, Any],
        w_pre: Optional[PreWitness],
        hw_actuator_feedback_bit: int = 1,
    ) -> GateExecutionReceipt:
        """
        Steg 2: Konsekvensporten Omega(x_k, c_k, W_pre, a_k).
        Verifiserer W_pre, HMAC, monoton sekvensteller (C > C_hw), CapsuleLinkage,
        anti-replay og HPIS-interlock (d_k vs a_k).
        """
        pre_digest = self.state_digest()
        isolated_candidate = copy.deepcopy(candidate)

        if self.trapped:
            return self._build_receipt(
                status="TRAP",
                gate_verdict="TRAP",
                voltage=0.00,
                impedance="LOW_Z_LATCHED_TRAP",
                pre_digest=pre_digest,
                post_digest=pre_digest,
                matrix_hash=sha256_hex(b"TRAPPED"),
                kernel_drift=0.10,
                reason=f"GATE_LATCHED_IN_TRAP:{self.trap_reason}",
            )

        if w_pre is None or w_pre.verdict != "OPEN":
            return self._build_receipt(
                status="ERR_UNSEALED_ACTUATION",
                gate_verdict="KILL",
                voltage=0.00,
                impedance="LOW_Z_CROWBAR",
                pre_digest=pre_digest,
                post_digest=pre_digest,
                matrix_hash=sha256_hex(b"UNSEALED_CANDIDATE"),
                kernel_drift=0.05,
                reason="ERR_UNSEALED_ACTUATION:Missing_or_closed_W_pre",
            )

        structural_fault = self._contains_non_finite_or_bool_num(isolated_candidate)
        if structural_fault is not None:
            self._enter_trap(f"POST_CHECK_STRUCTURAL_FAULT:{structural_fault}")
            return self._build_receipt(
                status="TRAP",
                gate_verdict="TRAP",
                voltage=0.00,
                impedance="LOW_Z_LATCHED_TRAP",
                pre_digest=pre_digest,
                post_digest=pre_digest,
                matrix_hash=sha256_hex(b"INVALID_NUM"),
                kernel_drift=0.10,
                reason=self.trap_reason,
            )

        actual_matrix_hash = sha256_hex(canonical_matrix_fixed_point_bytes(isolated_candidate))
        actual_logic_hash = self.logic_digest()
        drift_val = float(isolated_candidate.get("identity_residual", 0.01))

        if w_pre.nonce in self.used_nonces or str(isolated_candidate.get("event_id")) in self.used_event_ids:
            return self._build_receipt(
                status="KILL",
                gate_verdict="KILL",
                voltage=0.00,
                impedance="LOW_Z_CROWBAR",
                pre_digest=pre_digest,
                post_digest=pre_digest,
                matrix_hash=actual_matrix_hash,
                kernel_drift=max(drift_val, 0.02),
                reason="REPLAY_ATTACK_DETECTED:W(E_i)_does_not_imply_Auth(E_i+1)",
            )

        if w_pre.seq_counter <= self.committed_hw_counter:
            return self._build_receipt(
                status="KILL",
                gate_verdict="KILL",
                voltage=0.00,
                impedance="LOW_Z_CROWBAR",
                pre_digest=pre_digest,
                post_digest=pre_digest,
                matrix_hash=actual_matrix_hash,
                kernel_drift=max(drift_val, 0.02),
                reason=f"MONOTONIC_COUNTER_REPLAY_DETECTED:seq={w_pre.seq_counter}<=C_hw={self.committed_hw_counter}",
            )

        expected_warrant_payload = canonical_json_bytes({
            "event_id": str(isolated_candidate.get("event_id")),
            "logic_hash": actual_logic_hash,
            "matrix_hash": actual_matrix_hash,
            "nonce": str(isolated_candidate.get("nonce")),
            "pre_state_digest": pre_digest,
            "seq_counter": w_pre.seq_counter,
            "verdict": "OPEN",
        })
        expected_hmac = self._sign_hmac(expected_warrant_payload)

        if (
            actual_matrix_hash != w_pre.matrix_hash
            or actual_logic_hash != w_pre.logic_hash
            or pre_digest != w_pre.pre_state_digest
            or not hmac.compare_digest(expected_hmac, w_pre.warrant_hmac)
        ):
            self._enter_trap("CAPSULE_LINKAGE_TAMPER_DETECTED:Payload_mutated_after_Pi_A")
            return self._build_receipt(
                status="TRAP",
                gate_verdict="TRAP",
                voltage=0.00,
                impedance="LOW_Z_LATCHED_TRAP",
                pre_digest=pre_digest,
                post_digest=pre_digest,
                matrix_hash=actual_matrix_hash,
                kernel_drift=0.10,
                reason=self.trap_reason,
            )

        if hw_actuator_feedback_bit != 1:
            return self._build_receipt(
                status="INTERLOCK_MISMATCH",
                gate_verdict="OPEN",
                voltage=0.00,
                impedance="LOW_Z_CROWBAR",
                pre_digest=pre_digest,
                post_digest=pre_digest,
                matrix_hash=actual_matrix_hash,
                kernel_drift=max(drift_val, 0.02),
                reason="INTERLOCK_MISMATCH:d_k=OPEN_but_actuator_feedback_a_k=0",
            )

        self.committed_hw_counter = w_pre.seq_counter
        self.used_nonces.append(w_pre.nonce)
        self.used_event_ids.append(w_pre.event_id)
        self.recent_failures = 0

        next_metadata = copy.deepcopy(isolated_candidate.get("metadata", self._state.get("metadata", {})))
        self._state = {
            "phase": str(isolated_candidate.get("event_id")),
            "total_mass_kg": 0.0 if float(isolated_candidate["total_mass_kg"]) == 0.0 else float(isolated_candidate["total_mass_kg"]),
            "pressure_bar": 145.0,
            "committed_steps": int(self._state["committed_steps"]) + 1,
            "metadata": next_metadata,
        }
        post_digest = self.state_digest()

        return self._build_receipt(
            status="SIMULATED_EFFECT",
            gate_verdict="OPEN",
            voltage=5.00,
            impedance="ACTIVE_LOAD",
            pre_digest=pre_digest,
            post_digest=post_digest,
            matrix_hash=actual_matrix_hash,
            kernel_drift=drift_val,
            reason="L1_SIMULATED_EFFECT:W_pre_and_W_post_sealed",
        )

    def reset_trap(self, reset_nonce: str, authorization_hmac: str) -> bool:
        """
        Kryptografisk reset av TRAP-tilstand: krever fersk nonce og gyldig HMAC-signatur.
        """
        if reset_nonce in self.used_nonces:
            return False
        payload = canonical_json_bytes({"action": "RESET_TRAP", "nonce": reset_nonce, "trap_reason": self.trap_reason})
        expected = self._sign_hmac(payload)
        if not hmac.compare_digest(expected, authorization_hmac):
            return False
        self.used_nonces.append(reset_nonce)
        self.trapped = False
        self.trap_reason = ""
        self.recent_failures = 0
        return True

    def _enter_trap(self, reason: str) -> None:
        self.trapped = True
        self.trap_reason = reason

    def _pack_fpga_structs(
        self,
        seq_id: int,
        gate_verdict: str,
        status: str,
        matrix_hash_hex: str,
        kernel_drift: float,
    ) -> Tuple[WitnessPreCommit, WitnessPostCommit]:
        """
        Bygger den binære C/SystemVerilog-broen (SPEC-213: 119 B WitnessPreCommit + 86 B WitnessPostCommit).
        """
        t_pre_ns = seq_id * 1_000_000
        t_post_ns = t_pre_ns + 500
        cand_hash_bytes = bytes.fromhex(matrix_hash_hex)

        if status == "SIMULATED_EFFECT" and gate_verdict == "OPEN":
            fpga_decision = GATE_DECISION_OPEN
            reason_code = REASON_CODE_NOMINAL
            hpis_latch = HPIS_LATCH_ENGAGED
            final_status = FINAL_STATUS_REALIZED
            exhaust_nJ = 0.0
        elif status == "INTERLOCK_MISMATCH" and gate_verdict == "OPEN":
            # Vektor B: d_k = OPEN (0x01), men a_k = 0 -> HPIS_LATCH_ISOLATED (0x00) og positiv eksos
            fpga_decision = GATE_DECISION_OPEN
            reason_code = REASON_CODE_NOMINAL
            hpis_latch = HPIS_LATCH_ISOLATED
            final_status = FINAL_STATUS_TERMINATED
            exhaust_nJ = calculate_landauer_exhaust_nJ(max(abs(kernel_drift), 0.02))
        elif gate_verdict == "HOLD":
            fpga_decision = GATE_DECISION_HOLD
            reason_code = REASON_CODE_DRIFT_THRESHOLD_EXCEEDED
            hpis_latch = HPIS_LATCH_ISOLATED
            final_status = FINAL_STATUS_TERMINATED
            exhaust_nJ = calculate_landauer_exhaust_nJ(max(abs(kernel_drift), 0.01))
        else:
            fpga_decision = GATE_DECISION_KILL
            reason_code = REASON_CODE_DRIFT_THRESHOLD_EXCEEDED
            hpis_latch = HPIS_LATCH_ISOLATED
            final_status = FINAL_STATUS_TERMINATED
            exhaust_nJ = calculate_landauer_exhaust_nJ(max(abs(kernel_drift), 0.01))

        pre_hashable = struct.pack(
            W_PRE_HASHABLE_FORMAT,
            seq_id,
            t_pre_ns,
            cand_hash_bytes,
            float(kernel_drift),
            fpga_decision,
            reason_code,
            self.fpga_anchor_hash,
        )
        w_pre_hash = hashlib.sha256(pre_hashable).digest()

        w_pre_struct = WitnessPreCommit(
            sequence_id=seq_id,
            timestamp_ns=t_pre_ns,
            candidate_hash=cand_hash_bytes,
            kernel_drift_val=float(kernel_drift),
            gate_decision=fpga_decision,
            reason_code=reason_code,
            prev_block_hash=self.fpga_anchor_hash,
            w_pre_hash=w_pre_hash,
        )

        post_hashable = struct.pack(
            W_POST_HASHABLE_FORMAT,
            seq_id,
            t_post_ns,
            w_pre_hash,
            hpis_latch,
            float(exhaust_nJ),
            final_status,
        )
        w_post_hash = hashlib.sha256(post_hashable).digest()

        w_post_struct = WitnessPostCommit(
            sequence_id=seq_id,
            timestamp_ns=t_post_ns,
            w_pre_hash=w_pre_hash,
            hpis_latch_status=hpis_latch,
            thermo_exhaust_nJ=float(exhaust_nJ),
            final_status=final_status,
            w_post_hash=w_post_hash,
        )

        self.fpga_pre_ledger.append(w_pre_struct)
        self.fpga_post_ledger.append(w_post_struct)
        self.fpga_anchor_hash = w_post_hash
        return w_pre_struct, w_post_struct

    def _build_receipt(
        self,
        status: str,
        gate_verdict: str,
        voltage: float,
        impedance: str,
        pre_digest: str,
        post_digest: str,
        matrix_hash: str,
        kernel_drift: float,
        reason: str,
    ) -> GateExecutionReceipt:
        logic_hash = self.logic_digest()
        exec_hash = sha256_hex(canonical_json_bytes({
            "commanded_voltage_v": voltage,
            "gate_verdict": gate_verdict,
            "impedance_state": impedance,
            "post_state_digest": post_digest,
            "pre_state_digest": pre_digest,
            "seq_counter": self.committed_hw_counter,
            "status": status,
        }))
        capsule_linkage = f"{matrix_hash}||{logic_hash}||{exec_hash}"

        wal_seq = len(self.wal_chain) + 1
        w_pre_struct, w_post_struct = self._pack_fpga_structs(
            seq_id=wal_seq,
            gate_verdict=gate_verdict,
            status=status,
            matrix_hash_hex=matrix_hash,
            kernel_drift=kernel_drift,
        )

        prev_wal_hash = self.wal_chain[-1]["entry_hash"] if self.wal_chain else ("0" * 64)
        wal_entry = {
            "index": len(self.wal_chain),
            "status": status,
            "gate_verdict": gate_verdict,
            "commanded_voltage_v": voltage,
            "impedance_state": impedance,
            "seq_counter": self.committed_hw_counter,
            "capsule_linkage": capsule_linkage,
            "fpga_w_pre_hash": w_pre_struct.w_pre_hash.hex(),
            "fpga_w_post_hash": w_post_struct.w_post_hash.hex(),
            "prev_wal_hash": prev_wal_hash,
        }
        wal_entry["entry_hash"] = sha256_hex(canonical_json_bytes(wal_entry))
        self.wal_chain.append(wal_entry)

        return GateExecutionReceipt(
            status=status,
            gate_verdict=gate_verdict,
            commanded_voltage_v=voltage,
            impedance_state=impedance,
            seq_counter=self.committed_hw_counter,
            pre_state_digest=pre_digest,
            post_state_digest=post_digest,
            capsule_linkage=capsule_linkage,
            reason=reason,
            fpga_w_pre_bytes=w_pre_struct.to_bytes(),
            fpga_w_post_bytes=w_post_struct.to_bytes(),
        )


def _bytes_to_sv_hex_le(raw_bytes: bytes) -> str:
    """
    Konverterer en byte-streng (der indeks 0 skal ligge på [7:0] i SystemVerilog)
    til en SystemVerilog hex-literal: reverserer byte-rekkefølgen slik at byte 0
    havner lengst til høyre (LSB [7:0]).
    """
    bit_width = len(raw_bytes) * 8
    hex_msb_first = raw_bytes[::-1].hex()
    return f"{bit_width}'h{hex_msb_first}"


def _resolve_rtl_decoder_path(explicit_path: Optional[str] = None) -> str:
    if explicit_path and os.path.isfile(explicit_path):
        return explicit_path
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "fpga_capsule_frame_205b_decoder.sv")


def run_l1_5_iverilog_cosimulation(
    vec_a_receipt: GateExecutionReceipt,
    vec_b_receipt: GateExecutionReceipt,
    vec_c_tampered_pre_bytes: bytes,
    vec_c_tampered_post_bytes: bytes,
    rtl_decoder_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trinn 1 (L1.5): Kompilering og kjøring av SystemVerilog-modulen fpga_capsule_frame_205b_decoder.sv
    via iverilog -g2012 og vvp med de faktiske 205-byte rammene generert av Python:
      - Vektor A: Nominell SIMULATED_EFFECT (OPEN -> v_gate_out_5v=1, rtl_verdict_code=0x01)
      - Vektor B: INTERLOCK_MISMATCH (d_k=OPEN, a_k=0 -> v_gate_out_5v=0, rtl_verdict_code=0xEE)
      - Vektor C: Tuklet CapsuleLinkage (post.w_pre_hash != pre.w_pre_hash -> v_gate_out_5v=0, rtl_verdict_code=0xFF)
    """
    resolved_rtl = _resolve_rtl_decoder_path(rtl_decoder_path)
    vec_a_pre_sv = _bytes_to_sv_hex_le(vec_a_receipt.fpga_w_pre_bytes)
    vec_a_post_sv = _bytes_to_sv_hex_le(vec_a_receipt.fpga_w_post_bytes)

    vec_b_pre_sv = _bytes_to_sv_hex_le(vec_b_receipt.fpga_w_pre_bytes)
    vec_b_post_sv = _bytes_to_sv_hex_le(vec_b_receipt.fpga_w_post_bytes)

    vec_c_pre_sv = _bytes_to_sv_hex_le(vec_c_tampered_pre_bytes)
    vec_c_post_sv = _bytes_to_sv_hex_le(vec_c_tampered_post_bytes)

    tb_source = f"""`timescale 1ns / 1ps
module tb_cosim_205b;
    reg          clk = 0;
    reg          rst_n = 0;
    reg          frame_valid = 0;
    reg  [951:0] w_pre_frame_le;
    reg  [687:0] w_post_frame_le;

    wire [63:0]  pre_seq_id;
    wire [63:0]  post_seq_id;
    wire [7:0]   pre_gate_decision;
    wire [15:0]  pre_reason_code;
    wire [255:0] pre_w_pre_hash;
    wire [255:0] post_w_pre_hash;
    wire [7:0]   post_hpis_latch_byte;
    wire [7:0]   post_final_status;
    wire         capsule_linkage_ok;
    wire         v_gate_out_5v;
    wire [7:0]   rtl_verdict_code;

    fpga_capsule_frame_205b_decoder dut (
        .clk(clk),
        .rst_n(rst_n),
        .frame_valid(frame_valid),
        .w_pre_frame_le(w_pre_frame_le),
        .w_post_frame_le(w_post_frame_le),
        .pre_seq_id(pre_seq_id),
        .post_seq_id(post_seq_id),
        .pre_gate_decision(pre_gate_decision),
        .pre_reason_code(pre_reason_code),
        .pre_w_pre_hash(pre_w_pre_hash),
        .post_w_pre_hash(post_w_pre_hash),
        .post_hpis_latch_byte(post_hpis_latch_byte),
        .post_final_status(post_final_status),
        .capsule_linkage_ok(capsule_linkage_ok),
        .v_gate_out_5v(v_gate_out_5v),
        .rtl_verdict_code(rtl_verdict_code)
    );

    always #5 clk = ~clk;

    initial begin
        w_pre_frame_le  = 952'd0;
        w_post_frame_le = 688'd0;
        #15 rst_n = 1;

        // Vektor A: Nominell SIMULATED_EFFECT
        w_pre_frame_le  = {vec_a_pre_sv};
        w_post_frame_le = {vec_a_post_sv};
        frame_valid = 1;
        #10 frame_valid = 0;
        #10;
        $display("VEC_A: seq=%0d gate=0x%02h latch=0x%02h link_ok=%0d v5v=%0d code=0x%02h",
                 pre_seq_id, pre_gate_decision, post_hpis_latch_byte, capsule_linkage_ok, v_gate_out_5v, rtl_verdict_code);
        if (v_gate_out_5v !== 1'b1 || rtl_verdict_code !== 8'h01 || capsule_linkage_ok !== 1'b1) $finish(1);

        // Vektor B: INTERLOCK_MISMATCH (d_k=OPEN, a_k=0)
        w_pre_frame_le  = {vec_b_pre_sv};
        w_post_frame_le = {vec_b_post_sv};
        frame_valid = 1;
        #10 frame_valid = 0;
        #10;
        $display("VEC_B: seq=%0d gate=0x%02h latch=0x%02h link_ok=%0d v5v=%0d code=0x%02h",
                 pre_seq_id, pre_gate_decision, post_hpis_latch_byte, capsule_linkage_ok, v_gate_out_5v, rtl_verdict_code);
        if (v_gate_out_5v !== 1'b0 || rtl_verdict_code !== 8'hEE) $finish(1);

        // Vektor C: Tuklet CapsuleLinkage (W_POST.w_pre_hash != W_PRE.w_pre_hash)
        w_pre_frame_le  = {vec_c_pre_sv};
        w_post_frame_le = {vec_c_post_sv};
        frame_valid = 1;
        #10 frame_valid = 0;
        #10;
        $display("VEC_C: seq=%0d gate=0x%02h latch=0x%02h link_ok=%0d v5v=%0d code=0x%02h",
                 pre_seq_id, pre_gate_decision, post_hpis_latch_byte, capsule_linkage_ok, v_gate_out_5v, rtl_verdict_code);
        if (v_gate_out_5v !== 1'b0 || rtl_verdict_code !== 8'hFF || capsule_linkage_ok !== 1'b0) $finish(1);

        $display("COSIM_ALL_PASS");
        $finish(0);
    end
endmodule
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tb_path = os.path.join(tmpdir, "tb_cosim_205b.sv")
        out_vvp = os.path.join(tmpdir, "tb_cosim_205b.vvp")
        with open(tb_path, "w", encoding="utf-8") as f:
            f.write(tb_source)

        comp = subprocess.run(
            ["iverilog", "-g2012", "-o", out_vvp, resolved_rtl, tb_path],
            capture_output=True,
            text=True,
            check=False,
        )
        if comp.returncode != 0:
            raise RuntimeError(f"iverilog compilation failed: {comp.stderr}")

        sim = subprocess.run(
            ["vvp", out_vvp],
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "returncode": sim.returncode,
            "stdout": sim.stdout.strip(),
            "stderr": sim.stderr.strip(),
            "passed": sim.returncode == 0 and "COSIM_ALL_PASS" in sim.stdout,
        }


class CapsuleWireLoopbackNode:
    """
    Trinn 2 (L2 i D_rep^{(1)}): Seriell Loopback-mottakernode over faktisk POSIX PTY (/dev/pts/*).
    Pakkestruktur på linjen (247 bytes):
      [0xAA][0x55][seq_counter: uint64 (8B)][W_PRE (119B)][W_POST (86B)][HMAC_SHA256 (32B)]
    Håndhever:
      1. Synkroniseringsheader (0xAA 0x55) og linje-timeout -> KILL_TRUNCATED_FRAME (0.00 V DC)
      2. Bit-flip på linjen (Delta_link) -> KILL_LINK_INTEGRITY (0.00 V DC)
      3. Cold-Boot / Pre-Reboot Token (Delta_power_cycle, authority_retained="FALSE", C <= C_hw)
         -> KILL_PRE_REBOOT_WARRANT (0.00 V DC)
    """

    def __init__(self, hmac_key: bytes = b"L1_CONSTITUTIONAL_GATE_KEY_2026") -> None:
        self._hmac_key = hmac_key
        self.committed_hw_counter: int = 0
        self.authority_retained: str = "TRUE"
        self.boot_epoch: int = 1

    @staticmethod
    def configure_raw_pty(fd: int) -> None:
        """
        Setter POSIX PTY i rå binærmodus (cfmakeraw / tty.setraw) slik at OS-ets
        linjedisiplin (ICRNL / ONLCR / IXON) ikke muterer binære SHA-256-bytes.
        """
        tty.setraw(fd, when=termios.TCSANOW)

    def pack_wire_frame(self, receipt: GateExecutionReceipt) -> bytes:
        header = struct.pack(
            WIRE_HEADER_FORMAT,
            WIRE_SYNC_BYTE_0,
            WIRE_SYNC_BYTE_1,
            int(receipt.seq_counter),
        )
        body = header + receipt.fpga_w_pre_bytes + receipt.fpga_w_post_bytes
        mac = hmac.new(self._hmac_key, body, hashlib.sha256).digest()
        frame = body + mac
        assert len(frame) == WIRE_TOTAL_FRAME_SIZE
        return frame

    def simulate_cold_boot_reset(self) -> Dict[str, Any]:
        """
        Simulerer spenningsfall / cold-boot (Delta_power_cycle):
        - Nullstiller flyktig sesjonsautorisasjon (authority_retained = "FALSE").
        - Bevarer den ikke-flyktige monotone maskinvaretelleren committed_hw_counter (C_hw i eNVM/MRAM).
        """
        self.authority_retained = "FALSE"
        self.boot_epoch += 1
        return {
            "authority_retained": self.authority_retained,
            "boot_epoch": self.boot_epoch,
            "persisted_c_hw": self.committed_hw_counter,
            "commanded_voltage_v": 0.00,
            "impedance_state": "LOW_Z_CROWBAR",
        }

    def receive_over_pty(self, master_fd: int, timeout_sec: float = 0.05) -> Dict[str, Any]:
        """
        Leser en 247-byte ramme fra en faktisk POSIX PTY file descriptor med select()-timeout.
        Returnerer eksplisitt L2 loopback-dom (aldri falsk OPEN ved trunkering, bit-flip eller replay).
        """
        buf = bytearray()
        while len(buf) < WIRE_TOTAL_FRAME_SIZE:
            rlist, _, _ = select.select([master_fd], [], [], timeout_sec)
            if not rlist:
                # Linje-timeout eller trunkert pakke (< 247 bytes)
                return {
                    "status": "KILL_TRUNCATED_FRAME",
                    "commanded_voltage_v": 0.00,
                    "impedance_state": "LOW_Z_CROWBAR",
                    "bytes_received": len(buf),
                    "expected_bytes": WIRE_TOTAL_FRAME_SIZE,
                }
            chunk = os.read(master_fd, WIRE_TOTAL_FRAME_SIZE - len(buf))
            if not chunk:
                break
            buf.extend(chunk)

        if len(buf) < WIRE_TOTAL_FRAME_SIZE:
            return {
                "status": "KILL_TRUNCATED_FRAME",
                "commanded_voltage_v": 0.00,
                "impedance_state": "LOW_Z_CROWBAR",
                "bytes_received": len(buf),
                "expected_bytes": WIRE_TOTAL_FRAME_SIZE,
            }

        raw = bytes(buf)
        sync0, sync1, seq_counter = struct.unpack(WIRE_HEADER_FORMAT, raw[:10])
        if sync0 != WIRE_SYNC_BYTE_0 or sync1 != WIRE_SYNC_BYTE_1:
            return {
                "status": "KILL_SYNC_HEADER_CORRUPT",
                "commanded_voltage_v": 0.00,
                "impedance_state": "LOW_Z_CROWBAR",
            }

        body = raw[: 10 + WIRE_PAYLOAD_SIZE]
        rx_mac = raw[10 + WIRE_PAYLOAD_SIZE :]
        expected_mac = hmac.new(self._hmac_key, body, hashlib.sha256).digest()

        # 1. Bit-flip på linjen (Delta_link) oppdages av HMAC eller intern SHA-256 i W_PRE/W_POST
        if not hmac.compare_digest(expected_mac, rx_mac):
            return {
                "status": "KILL_LINK_INTEGRITY",
                "commanded_voltage_v": 0.00,
                "impedance_state": "LOW_Z_CROWBAR",
                "reason": "HMAC_MISMATCH_DELTA_LINK_BITFLIP",
            }

        w_pre_bytes = raw[10 : 10 + 119]
        w_post_bytes = raw[10 + 119 : 10 + 205]
        w_pre = WitnessPreCommit.from_bytes(w_pre_bytes)
        w_post = WitnessPostCommit.from_bytes(w_post_bytes)

        if (
            w_pre.compute_hash() != w_pre.w_pre_hash
            or w_post.compute_hash() != w_post.w_post_hash
            or w_post.w_pre_hash != w_pre.w_pre_hash
        ):
            return {
                "status": "KILL_LINK_INTEGRITY",
                "commanded_voltage_v": 0.00,
                "impedance_state": "LOW_Z_CROWBAR",
                "reason": "STRUCT_SHA256_INVOLUTION_MISMATCH",
            }

        # 2. Cold-Boot / Pre-Reboot Token sjekk (C <= C_hw)
        if seq_counter <= self.committed_hw_counter:
            return {
                "status": "KILL_PRE_REBOOT_WARRANT",
                "commanded_voltage_v": 0.00,
                "impedance_state": "LOW_Z_CROWBAR",
                "authority_retained": self.authority_retained,
                "reason": f"SEQ_{seq_counter}_LE_PERSISTED_C_HW_{self.committed_hw_counter}",
            }

        # 3. Sjekk om selve W_POST tillater aktivering (hpis_latch_status == 1 og final_status == 1)
        if w_pre.gate_decision != GATE_DECISION_OPEN or w_post.hpis_latch_status != HPIS_LATCH_ENGAGED or w_post.final_status != FINAL_STATUS_REALIZED:
            return {
                "status": "KILL_REMOTE_GATE_ISOLATED",
                "commanded_voltage_v": 0.00,
                "impedance_state": "LOW_Z_CROWBAR",
            }

        self.committed_hw_counter = seq_counter
        self.authority_retained = "TRUE"
        return {
            "status": "L2_LOOPBACK_SIMULATED_EFFECT",
            "commanded_voltage_v": 5.00,
            "impedance_state": "ACTIVE_LOAD",
            "committed_hw_counter": self.committed_hw_counter,
            "w_pre_hash_hex": w_pre.w_pre_hash.hex(),
            "w_post_hash_hex": w_post.w_post_hash.hex(),
        }
