"""
SPEC-213: FPGA WITNESS LEDGER (WORM) L1 REFERENCE ENGINE
Architecture: Phronesis Engine // Sovereign Witness Track
Target: FPGA Append-Only Memory C-Struct Specification
Author: Marius E. Torjusen (ORCID: 0009-0006-0431-6637), Independent Researcher

Implements:
  1. Exact binary C-struct serialization (W_PRE 119 bytes, W_POST 86 bytes).
  2. Asymmetric two-phase commit:
     - W_PRE: Intent, candidate hash, kernel drift D_K, gate decision, anchor.
     - W_POST: Consequence, HPIS latch status, Landauer thermal receipt, final status.
  3. Strict thermodynamic receipt verification:
     If gate_decision == KILL, thermo_exhaust_nJ must be > 0.0.
     Zero-exhaust KILL triggers ThermalDeficitBreachError (hardware breach).
  4. Orphan intent recovery:
     Unclosed W_PRE triggers KILL_SYSTEM_PANIC_ORPHAN and seals the chain fail-closed.
  5. Cryptographic involution & append-only hash chain audit.
"""

import math
import time
import struct
import hashlib
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

# --- SYSTEM CONSTANTS & THERMODYNAMICS ---
KB = 1.380649e-23           # Boltzmann constant (J/K)
TEMP_K = 298.15             # Operating temperature (Kelvin)
LANDAUER_LIMIT_J = KB * TEMP_K * math.log(2) # 2.8533e-21 J/bit
N_MICROSTATES_SCALING = 1e15 # Physical bits erased per unit norm

# Gate Decisions
GATE_DECISION_OPEN = 0x01
GATE_DECISION_HOLD = 0x02
GATE_DECISION_KILL = 0x03

# Reason Codes
REASON_CODE_NOMINAL = 0x0000
REASON_CODE_DRIFT_THRESHOLD_EXCEEDED = 0x0401
REASON_CODE_ORPHAN_INTENT = 0x0402
REASON_CODE_THERMAL_DEFICIT_BREACH = 0x0403

# HPIS Latch Status
HPIS_LATCH_ISOLATED = 0x00
HPIS_LATCH_ENGAGED = 0x01

# Final Status
FINAL_STATUS_REALIZED = 0x01
FINAL_STATUS_TERMINATED = 0x0F

# Binary Struct Formats (Packed, Little-Endian)
# WitnessPreCommit: uint64, uint64, 32s, float, uint8, uint16, 32s, 32s
W_PRE_FORMAT = "<QQ32sfBH32s32s"
W_PRE_HASHABLE_FORMAT = "<QQ32sfBH32s" # First 87 bytes hashed into w_pre_hash

# WitnessPostCommit: uint64, uint64, 32s, uint8, float, uint8, 32s
W_POST_FORMAT = "<QQ32sBfB32s"
W_POST_HASHABLE_FORMAT = "<QQ32sBfB" # First 54 bytes hashed into w_post_hash

assert struct.calcsize(W_PRE_FORMAT) == 119, f"W_PRE size must be 119, got {struct.calcsize(W_PRE_FORMAT)}"
assert struct.calcsize(W_POST_FORMAT) == 86, f"W_POST size must be 86, got {struct.calcsize(W_POST_FORMAT)}"


class ThermalDeficitBreachError(Exception):
    """Raised when a KILL verdict provides zero or negative thermodynamic exhaust."""
    pass


class OrphanIntentError(Exception):
    """Raised when an unclosed W_PRE intent is encountered on recovery."""
    pass


@dataclass(frozen=True)
class WitnessPreCommit:
    sequence_id: int          # uint64_t
    timestamp_ns: int         # uint64_t
    candidate_hash: bytes     # 32 bytes
    kernel_drift_val: float   # float (4 bytes)
    gate_decision: int        # uint8_t
    reason_code: int          # uint16_t
    prev_block_hash: bytes    # 32 bytes
    w_pre_hash: bytes         # 32 bytes

    def to_bytes(self) -> bytes:
        return struct.pack(
            W_PRE_FORMAT,
            self.sequence_id,
            self.timestamp_ns,
            self.candidate_hash,
            self.kernel_drift_val,
            self.gate_decision,
            self.reason_code,
            self.prev_block_hash,
            self.w_pre_hash
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "WitnessPreCommit":
        unpacked = struct.unpack(W_PRE_FORMAT, data)
        return cls(*unpacked)

    def compute_hash(self) -> bytes:
        hashable_bytes = struct.pack(
            W_PRE_HASHABLE_FORMAT,
            self.sequence_id,
            self.timestamp_ns,
            self.candidate_hash,
            self.kernel_drift_val,
            self.gate_decision,
            self.reason_code,
            self.prev_block_hash
        )
        return hashlib.sha256(hashable_bytes).digest()


@dataclass(frozen=True)
class WitnessPostCommit:
    sequence_id: int          # uint64_t
    timestamp_ns: int         # uint64_t
    w_pre_hash: bytes         # 32 bytes
    hpis_latch_status: int    # uint8_t
    thermo_exhaust_nJ: float  # float (4 bytes)
    final_status: int         # uint8_t
    w_post_hash: bytes        # 32 bytes

    def to_bytes(self) -> bytes:
        return struct.pack(
            W_POST_FORMAT,
            self.sequence_id,
            self.timestamp_ns,
            self.w_pre_hash,
            self.hpis_latch_status,
            self.thermo_exhaust_nJ,
            self.final_status,
            self.w_post_hash
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "WitnessPostCommit":
        unpacked = struct.unpack(W_POST_FORMAT, data)
        return cls(*unpacked)

    def compute_hash(self) -> bytes:
        hashable_bytes = struct.pack(
            W_POST_HASHABLE_FORMAT,
            self.sequence_id,
            self.timestamp_ns,
            self.w_pre_hash,
            self.hpis_latch_status,
            self.thermo_exhaust_nJ,
            self.final_status
        )
        return hashlib.sha256(hashable_bytes).digest()


def calculate_landauer_exhaust_nJ(kernel_drift: float) -> float:
    """Calculates theoretical Landauer erasure cost in nano-Joules."""
    erased_bits = abs(kernel_drift) * N_MICROSTATES_SCALING
    joules = erased_bits * LANDAUER_LIMIT_J
    return joules * 1e9 # Convert Joules to nano-Joules


class FpgaWitnessLedgerEngine:
    """
    Simulates FPGA hardware append-only memory controller for the Witness Ledger.
    Maintains invariant: Every realized state requires an asymmetric pair (W_PRE, W_POST).
    """
    def __init__(self, genesis_label: bytes = b"WORM_GENESIS_2026_PHRONESIS_CORE"):
        self.genesis_hash: bytes = hashlib.sha256(genesis_label).digest()
        self.pre_ledger: List[WitnessPreCommit] = []
        self.post_ledger: List[WitnessPostCommit] = []
        self.sequence_counter: int = 0
        self.current_anchor: bytes = self.genesis_hash
        self.pending_intent: Optional[WitnessPreCommit] = None

    def evaluate_and_seal(
        self,
        candidate_payload: bytes,
        kernel_drift: float,
        drift_threshold: float = 0.01,
        force_thermal_exhaust_override: Optional[float] = None
    ) -> Tuple[WitnessPreCommit, WitnessPostCommit]:
        """
        Executes complete 4-step realization causal chain:
        EVALUATE -> SEAL INTENT (W_PRE) -> ACTUATE -> MEASURE & SEAL CONSEQUENCE (W_POST).
        """
        if self.pending_intent is not None:
            raise OrphanIntentError(
                f"Cannot evaluate new candidate: Unresolved intent found for sequence_id={self.pending_intent.sequence_id}."
            )

        self.sequence_counter += 1
        seq_id = self.sequence_counter
        t_intent_ns = time.time_ns()
        cand_hash = hashlib.sha256(candidate_payload).digest()

        # 1. EVALUATE
        if kernel_drift >= drift_threshold:
            decision = GATE_DECISION_KILL
            reason = REASON_CODE_DRIFT_THRESHOLD_EXCEEDED
        else:
            decision = GATE_DECISION_OPEN
            reason = REASON_CODE_NOMINAL

        # 2. SEAL INTENT (W_PRE)
        # Construct temporary pre-commit to calculate its hash
        pre_hashable = struct.pack(
            W_PRE_HASHABLE_FORMAT,
            seq_id,
            t_intent_ns,
            cand_hash,
            kernel_drift,
            decision,
            reason,
            self.current_anchor
        )
        w_pre_hash = hashlib.sha256(pre_hashable).digest()

        w_pre = WitnessPreCommit(
            sequence_id=seq_id,
            timestamp_ns=t_intent_ns,
            candidate_hash=cand_hash,
            kernel_drift_val=kernel_drift,
            gate_decision=decision,
            reason_code=reason,
            prev_block_hash=self.current_anchor,
            w_pre_hash=w_pre_hash
        )

        # Lock intent into memory
        self.pre_ledger.append(w_pre)
        self.pending_intent = w_pre

        # 3. ACTUATE HPIS
        if decision == GATE_DECISION_OPEN:
            hpis_latch = HPIS_LATCH_ENGAGED
            final_status = FINAL_STATUS_REALIZED
            exhaust_nJ = 0.0
        else:
            hpis_latch = HPIS_LATCH_ISOLATED
            final_status = FINAL_STATUS_TERMINATED
            if force_thermal_exhaust_override is not None:
                exhaust_nJ = force_thermal_exhaust_override
            else:
                exhaust_nJ = calculate_landauer_exhaust_nJ(kernel_drift)

        # 4. MEASURE & AUDIT THERMODYNAMIC RECEIPT
        if decision == GATE_DECISION_KILL and exhaust_nJ <= 0.0:
            # Hardware breach: Free erasure is physically/logically prohibited!
            raise ThermalDeficitBreachError(
                f"Hardware breach: KILL decision recorded at sequence_id={seq_id} with zero/negative thermal exhaust ({exhaust_nJ} nJ)."
            )

        t_post_ns = time.time_ns()

        # Construct post-commit to calculate final epoch hash
        post_hashable = struct.pack(
            W_POST_HASHABLE_FORMAT,
            seq_id,
            t_post_ns,
            w_pre_hash,
            hpis_latch,
            exhaust_nJ,
            final_status
        )
        w_post_hash = hashlib.sha256(post_hashable).digest()

        w_post = WitnessPostCommit(
            sequence_id=seq_id,
            timestamp_ns=t_post_ns,
            w_pre_hash=w_pre_hash,
            hpis_latch_status=hpis_latch,
            thermo_exhaust_nJ=exhaust_nJ,
            final_status=final_status,
            w_post_hash=w_post_hash
        )

        self.post_ledger.append(w_post)
        self.current_anchor = w_post_hash
        self.pending_intent = None # Intent successfully resolved

        return w_pre, w_post

    def recover_orphan_intent(self) -> WitnessPostCommit:
        """
        Handles recovery from interrupted power or crash during intent realization.
        Enforces KILL_SYSTEM_PANIC_ORPHAN, pays Landauer rest exhaust, and closes the chain.
        """
        if self.pending_intent is None:
            raise ValueError("No orphan intent to recover.")

        orphan = self.pending_intent
        t_recovery_ns = time.time_ns()
        exhaust_nJ = calculate_landauer_exhaust_nJ(orphan.kernel_drift_val)
        hpis_latch = HPIS_LATCH_ISOLATED
        final_status = FINAL_STATUS_TERMINATED

        post_hashable = struct.pack(
            W_POST_HASHABLE_FORMAT,
            orphan.sequence_id,
            t_recovery_ns,
            orphan.w_pre_hash,
            hpis_latch,
            exhaust_nJ,
            final_status
        )
        w_post_hash = hashlib.sha256(post_hashable).digest()

        recovery_post = WitnessPostCommit(
            sequence_id=orphan.sequence_id,
            timestamp_ns=t_recovery_ns,
            w_pre_hash=orphan.w_pre_hash,
            hpis_latch_status=hpis_latch,
            thermo_exhaust_nJ=exhaust_nJ,
            final_status=final_status,
            w_post_hash=w_post_hash
        )

        self.post_ledger.append(recovery_post)
        self.current_anchor = w_post_hash
        self.pending_intent = None

        return recovery_post

    def verify_ledger_integrity(self) -> Tuple[bool, str]:
        """
        Audits full chain integrity:
        1. Lens: sequence_id matches 1:1 between pre and post ledgers.
        2. Cryptographic involution: prev_block_hash anchors match previous w_post_hash.
        3. Internal struct hashes match recomputed SHA-256.
        4. Thermodynamic invariant: All KILL entries have thermo_exhaust_nJ > 0.
        """
        if len(self.pre_ledger) != len(self.post_ledger):
            return False, f"Ledger count mismatch: {len(self.pre_ledger)} pre vs {len(self.post_ledger)} post."

        anchor = self.genesis_hash
        for i, (pre, post) in enumerate(zip(self.pre_ledger, self.post_ledger)):
            if pre.sequence_id != post.sequence_id:
                return False, f"Sequence ID mismatch at index {i}: pre={pre.sequence_id}, post={post.sequence_id}"

            if pre.prev_block_hash != anchor:
                return False, f"Pre-commit anchor broken at sequence {pre.sequence_id}"

            if pre.compute_hash() != pre.w_pre_hash:
                return False, f"Pre-commit SHA-256 corrupted at sequence {pre.sequence_id}"

            if post.w_pre_hash != pre.w_pre_hash:
                return False, f"Post-commit does not lock pre-commit hash at sequence {pre.sequence_id}"

            if post.compute_hash() != post.w_post_hash:
                return False, f"Post-commit SHA-256 corrupted at sequence {post.sequence_id}"

            if pre.gate_decision == GATE_DECISION_KILL:
                if post.thermo_exhaust_nJ <= 0.0:
                    return False, f"Thermodynamic audit failure at sequence {post.sequence_id}: Zero exhaust on KILL."
                if post.hpis_latch_status != HPIS_LATCH_ISOLATED:
                    return False, f"HPIS safety violation at sequence {post.sequence_id}: Latch engaged on KILL."

            if pre.gate_decision == GATE_DECISION_OPEN:
                if post.hpis_latch_status != HPIS_LATCH_ENGAGED:
                    return False, f"HPIS failure at sequence {post.sequence_id}: Latch isolated on OPEN."

            anchor = post.w_post_hash

        return True, "LEDGER_INTEGRITY_VERIFIED_AUTHENTIC"
