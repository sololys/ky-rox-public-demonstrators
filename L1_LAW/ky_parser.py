#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODULE: ky_parser.py
CLASSIFICATION: KY Realization Grammar v1.5-MASTER & KREATIV-CORE v3.0 Engine (L1)
LOCUS: Zero Level 0 (0xABCDEF00)
EPISTEMIC BOUNDARY: INSPIRED_BY != IMPLEMENTS != PROVES (PHYSICAL_AUTHORITY = NONE)
DESCRIPTION:
    Deterministic fail-closed parser, AST evaluator, Unicode <-> ASCII roundtrip
    serializer, ROX involutive verifier, and Kreativ-Core v3.0 Somatic Clearance engine.
    Note: Software ledger is an append-only SHA-256 hash chain (L1 software, not physical WORM media).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
import hashlib
import re
import struct
from typing import Any, Dict, List, Optional, Tuple


EPISTEMIC_BOUNDARY = "INSPIRED_BY != IMPLEMENTS != PROVES"

D1_ALLOWED_OPERATORS = frozenset({"ROX", "XOR_FROZEN_MASK", "ROL", "ROR", "NOT", "GRAY", "LFSR_NONSINGULAR"})
D1_FORBIDDEN_OPERATORS = frozenset({"AND", "OR", "SHL", "SHR"})


# ============================================================================
# 0. KY v1.0 FORMAL SPECIFICATION PARSER (Node, Gate, Admissibility, KYParser)
# ============================================================================

class Node(Enum):
    RAW = "○"
    ESTIMATE = "∅"
    STRUCT = "□"
    VIABILITY = "◇"
    VIABILITY_ALT = "♢"
    AUTHORIZED = "⊙"
    COMMITTED = "●"


class Verdict(Enum):
    OPEN = "►"
    HOLD = "॥"
    KILL = "X"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Verdict):
            return self.name == other.name
        if isinstance(other, str):
            return other in (self.name, self.value)
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.name)


class Gate(Enum):
    OPEN = "►"
    HOLD = "■"
    HOLD_ALT = "॥"
    KILL = "X"


class Admissibility(Enum):
    PASS = auto()
    HOLD = auto()
    KILL = auto()


@dataclass(frozen=True)
class EvalResult:
    syntax: str = "valid"
    type_status: str = "valid"
    admissibility: str = "pass"
    gate: Any = "OPEN"
    reasons: Any = field(default_factory=list)
    seal_hash: Optional[str] = None
    expression_unicode: str = ""
    expression_ascii: str = ""
    computed_gate: str = ""
    declared_gate: str = ""
    gate_match: bool = True
    final_verdict: str = ""
    d_latch_voltage: float = 0.0
    a5_gate_voltage: float = 0.0
    worm_hash: str = ""
    type_check: str = "valid"
    roundtrip_ok: bool = True
    capsule_205b: Optional[bytes] = None

    @property
    def reason(self) -> str:
        return "; ".join(self.reasons)


class KYParser:
    """
    Fail-closed deterministisk parser for KY v1.0 (samt Dør 22 seal-kompatibilitet).
    Standardtilstand for ethvert brudd er KILL.
    Støtter både direkte instansiering `KYParser(expression).parse()` (Master Grammar v1.0)
    og gjenbrukbar instansiering `KYParser().parse(expression)`.
    """

    VALID_CHAIN = [
        Node.RAW,
        Node.ESTIMATE,
        Node.STRUCT,
        Node.VIABILITY,
        Node.AUTHORIZED,
        Node.COMMITTED,
    ]

    MASTER_V10_NODES = ("○", "∅", "□", "◇", "●")

    def __init__(
        self,
        expression: Optional[str] = None,
        strict_mode: bool = True,
        delta_R_threshold: float = 2.5,
        bbob_limits: Any = (-10.0, 10.0),
        max_allowed_energy: float = 50.0,
        **kwargs: Any,
    ) -> None:
        self.raw_expr: Optional[str] = expression.strip() if isinstance(expression, str) else None
        self.reasons: List[str] = []
        self.strict_mode = strict_mode
        self.ledger_hash = hashlib.sha256(b"LOCUS_ZERO_KY_V10").hexdigest()
        self._delta_R_threshold = delta_R_threshold
        self._bbob_limits = bbob_limits
        self._max_allowed_energy = max_allowed_energy

    def _parse_master_v10(self) -> EvalResult:
        """Eksakt KY v1.0 Master Grammar & Typology fail-closed evaluering."""
        self.reasons = []
        raw_expr = self.raw_expr or ""

        # 1. Base Structure Check
        if not raw_expr.startswith("(") or len(raw_expr) < 4:
            return self._fail_v10("Syntaktisk brudd: Mangler gyldig innpakning.")

        # 2. Gate Extraction
        gate_char = raw_expr[-1]
        try:
            gate = Verdict(gate_char)
        except ValueError:
            return self._fail_v10(f"Ugyldig port-dom: {gate_char}")

        # 3. Content & Audit Extraction
        content_end = raw_expr.rfind(")")
        if content_end == -1:
            return self._fail_v10("Syntaktisk brudd: Mangler lukket parentes.")

        chain = raw_expr[1:content_end]
        suffix = raw_expr[content_end + 1 : -1].strip()

        # Alternativ A: ● er utelukkende en D2 tilstandsnode, aldri et commit-suffix
        if "●" in suffix:
            return self._fail_v10(
                "Illegal suffix symbol '●' (Note: '●' is strictly a state node, use '!' for commit)"
            )

        # 4. Type & Transition Check
        if not self._check_transitions(chain):
            return self._fail_v10("Type-brudd: Ulovlig overgang i topologien.")

        # 5. Admissibility & Audit Check
        if Node.COMMITTED.value in chain:
            if "#" not in suffix and "!" not in suffix:
                return self._fail_v10(
                    "Audit-brudd: Irreversibel overgang mangler hash (#) eller commit (!)."
                )

        if "∉K" in suffix or "≠" in suffix:
            if gate != Verdict.KILL:
                return self._fail_v10("Admissibility-brudd: Inadmissible markør krever KILL-gate.")
            return self._success_v10(Verdict.KILL, "Inadmissible uttrykk korrekt terminert.")

        # 6. Gate Alignment
        computed_gate = self._compute_gate(chain, suffix)
        if computed_gate != gate:
            return self._fail_v10(
                f"Gate-mismatch: Forventet {computed_gate.value}, funnet {gate.value}."
            )

        return self._success_v10(computed_gate, "Kjede validert. Gate i overensstemmelse.")

    def _check_transitions(self, chain: str) -> bool:
        nodes = chain.replace("→", "").replace("↝", "").replace("⇒", "").replace("⇢", "").replace(" ", "")
        valid_path = "".join(self.MASTER_V10_NODES)
        return bool(nodes) and (nodes in valid_path)

    def _compute_gate(self, chain: str, suffix: str) -> Verdict:
        if Node.COMMITTED.value in chain and ("#" in suffix or "!" in suffix):
            return Verdict.OPEN
        if Node.VIABILITY.value in chain or "~" in chain:
            return Verdict.HOLD
        return Verdict.KILL

    def _fail_v10(self, reason: str) -> EvalResult:
        self.reasons.append(reason)
        return EvalResult(
            syntax="invalid",
            type_status="invalid",
            type_check="invalid",
            admissibility="kill",
            gate=Verdict.KILL,
            reasons=list(self.reasons),
        )

    def _success_v10(self, gate: Verdict, reason: str) -> EvalResult:
        self.reasons.append(reason)
        adm = "pass" if gate == Verdict.OPEN else ("hold" if gate == Verdict.HOLD else "kill")
        return EvalResult(
            syntax="valid",
            type_status="valid",
            type_check="valid",
            admissibility=adm,
            gate=gate,
            reasons=list(self.reasons),
        )

    def evaluate_candidate(
        self,
        entropy_gradient: float,
        dR_dt: float,
        energy_cost_J: float,
        state_vector: Any,
        candidate_id: str = "cand_allfarvei",
    ) -> Tuple[str, str]:
        try:
            from .thermodynamic_admissibility_filter import ThermodynamicAdmissibilityFilter
        except ImportError:
            from thermodynamic_admissibility_filter import ThermodynamicAdmissibilityFilter
        filt = ThermodynamicAdmissibilityFilter(
            delta_R_threshold=self._delta_R_threshold,
            bbob_limits=self._bbob_limits,
            max_allowed_energy=self._max_allowed_energy,
        )
        return filt.evaluate_candidate(
            entropy_gradient=entropy_gradient,
            dR_dt=dR_dt,
            energy_cost_J=energy_cost_J,
            state_vector=state_vector,
            candidate_id=candidate_id,
        )

    def parse(self, expression: Optional[str] = None) -> EvalResult:
        if expression is None and self.raw_expr is not None:
            return self._parse_master_v10()
        if expression is None:
            return self._fail_v10("Syntaktisk brudd: Mangler uttrykk.")

        reasons: List[str] = []
        expression = expression.strip()

        # 1. Syntaktisk dekomponering (Fail-closed init)
        match = re.match(
            r'^(?:(⊨|✓|∉K|⊢)\s*)?\((.*?)\)(.*?)\s*([►■॥X])(?:\s*→\s*•\s*([#!]*))?$',
            expression,
        )
        if not match:
            return EvalResult(
                "invalid",
                "invalid",
                "kill",
                "KILL",
                ["Syntaktisk brudd: Mangler port eller feil struktur."],
            )

        prefix_mark, chain_str, suffix_str, gate_str, seal_audit = match.groups()
        gate = Gate.HOLD if gate_str == "॥" else Gate(gate_str)

        # Anti-Engine sjekk: • (U+2022) i prepare-fasen
        if "•" in chain_str:
            return EvalResult(
                "valid",
                "invalid",
                "kill",
                "KILL",
                ["ANTI-ENGINE COLLAPSE: Ulovlig commit-node (•) i prepare-fasen."],
            )

        # Ghost Win sjekk: Seal etter KILL eller HOLD
        if seal_audit is not None and gate != Gate.OPEN:
            return EvalResult(
                "valid",
                "invalid",
                "kill",
                "KILL",
                ["GHOST WIN FORSØK: Forsegling (→•#) er forbudt etter KILL/HOLD."],
            )

        # 2. Tokenisering av noder
        nodes: List[Node] = []
        for char in chain_str:
            if char == "♢":
                nodes.append(Node.VIABILITY)
            elif char in [n.value for n in self.VALID_CHAIN]:
                nodes.append(Node(char))

        if not nodes:
            return EvalResult(
                "invalid",
                "invalid",
                "kill",
                gate.name,
                ["Ingen gjenkjennelige noder i kjeden."],
            )

        # 3. Type- og sekvensvalidering (Overgangsmatrise)
        type_valid = True
        for i in range(len(nodes) - 1):
            curr_idx = self.VALID_CHAIN.index(nodes[i])
            next_idx = self.VALID_CHAIN.index(nodes[i + 1])
            if next_idx - curr_idx != 1:
                type_valid = False
                reasons.append(f"Ulovlig overgang: {nodes[i].value} → {nodes[i+1].value}")
                break

        # 4. Admissibilitets-sjekk (Audit og inngrep)
        admissibility = Admissibility.PASS
        combined_marks = (prefix_mark or "") + (suffix_str or "") + (seal_audit or "")

        if "∉K" in combined_marks or "≠" in combined_marks:
            admissibility = Admissibility.KILL
            reasons.append("Markør ∉K tvinger ubetinget KILL.")

        if Node.COMMITTED in nodes and not any(mark in combined_marks for mark in ["#", "!"]):
            admissibility = Admissibility.KILL
            reasons.append("Irreversibel overgang mangler audit-markør (# eller !).")

        if nodes[-1] == Node.VIABILITY and gate == Gate.OPEN and not any(mark in combined_marks for mark in ["#", "!"]):
            admissibility = Admissibility.KILL
            reasons.append("WITNESS FEIL: Overgang til VIABILITY ved OPEN krever forsegling/audit (# eller !).")

        if gate == Gate.HOLD and Node.STRUCT not in nodes:
            admissibility = Admissibility.KILL
            reasons.append("STRUCT FAIL: HOLD krever at strukturen minst har nådd □ (STRUCT).")

        if not type_valid:
            admissibility = Admissibility.KILL

        if gate == Gate.HOLD and admissibility != Admissibility.KILL:
            admissibility = Admissibility.HOLD
            reasons.append("Uttrykket er eksplisitt satt på HOLD.")

        # 5. Port-samsvar (Gate-enforcement)
        gate_matches = False
        if admissibility == Admissibility.PASS and gate == Gate.OPEN:
            gate_matches = True
        elif admissibility == Admissibility.HOLD and gate == Gate.HOLD:
            gate_matches = True
        elif admissibility == Admissibility.KILL and gate == Gate.KILL:
            gate_matches = True

        if not gate_matches:
            admissibility = Admissibility.KILL
            gate = Gate.KILL
            reasons.append("Port-dom samsvarer ikke med intern gyldighet. Fallback til KILL.")
        else:
            reasons.append("Port samsvarer med intern gyldighet.")

        seal_hash: Optional[str] = None
        if gate == Gate.OPEN and admissibility == Admissibility.PASS:
            seal_hash = hashlib.sha256(f"{self.ledger_hash}||{expression}".encode("utf-8")).hexdigest()
            self.ledger_hash = seal_hash

        return EvalResult(
            syntax="valid",
            type_status="valid" if type_valid else "invalid",
            admissibility=admissibility.name.lower(),
            gate=gate.name,
            reasons=reasons,
            seal_hash=seal_hash,
        )

# ============================================================================
# 1. CANONICAL ALPHABET & ROSETTA MAPPING TABLES
# ============================================================================

UNICODE_TO_ASCII_NODES: Dict[str, str] = {
    "○": "raw",
    "∅": "estimate",
    "□": "struct",
    "△": "threshold",
    "◇": "viability",
    "●": "committed",
}
ASCII_TO_UNICODE_NODES: Dict[str, str] = {v: k for k, v in UNICODE_TO_ASCII_NODES.items()}

UNICODE_TO_ASCII_FLOWS: Dict[str, str] = {
    "→": "->",
    "~": "~",
    "↦": "=>",
    "⇒": "!>",
}
ASCII_TO_UNICODE_FLOWS: Dict[str, str] = {v: k for k, v in UNICODE_TO_ASCII_FLOWS.items()}

UNICODE_TO_ASCII_GATES: Dict[str, str] = {
    "▸": "open",
    "‖": "hold",
    "✕": "kill",
}
ASCII_TO_UNICODE_GATES: Dict[str, str] = {v: k for k, v in UNICODE_TO_ASCII_GATES.items()}

VALIDITY_MARKS = {"∈K", "∉K", "⊢", "⊬", "≠"}
FIELD_MARKS = {"∞", "≈", "⊗", "⊕", "Ψ", "ΔK", "↺"}
AUDIT_MARKS = {"#", "!"}
TIME_MARKS = {"τ", "∂", "⌈", "t*"}

# Strictly legal step-by-step transitions in D0 -> D3
LEGAL_TRANSITIONS: Dict[Tuple[str, str], str] = {
    ("○", "∅"): "UNCONDITIONAL",     # D0 (RAW) -> D1 (ESTIMATE)
    ("∅", "□"): "UNCONDITIONAL",     # D1 (ESTIMATE) -> D1.2 (STRUCT)
    ("□", "◇"): "UNCONDITIONAL",     # D1.2 (STRUCT) -> D1.5 (VIABILITY)
    ("◇", "●"): "REQUIRES_AUDIT",    # D1.5 (VIABILITY) -> D2 (COMMITTED)
    ("□", "●"): "REQUIRES_AUDIT",    # Conditional: requires explicit validation + audit
    ("○", "□"): "REQUIRES_VALIDATE", # Conditional: requires explicit ✓ validation
    ("□", "□"): "REQUIRES_DRIFT",    # Allowed under ~ (continuous hold/stabilization)
    ("◇", "◇"): "REQUIRES_DRIFT",    # Allowed under ~ or ↺
    ("□", "△"): "UNCONDITIONAL",     # Struct to Threshold inspection
    ("◇", "△"): "UNCONDITIONAL",     # Viability to Threshold inspection
}


# ============================================================================
# 2. AST & EVALUATION DATA STRUCTURES
# ============================================================================

@dataclass(frozen=True)
class KYAST:
    has_prefix_validate: bool
    nodes: Tuple[str, ...]
    flows: Tuple[str, ...]
    fields: Tuple[str, ...]
    validity_mark: Optional[str]
    audits: Tuple[str, ...]
    times: Tuple[str, ...]
    declared_gate: str


@dataclass(frozen=True)
class SomaticCampaignCandidate:
    campaign_id: str
    title: str
    classification: str
    u_raw: float         # Raw somatic pressure (T_p)
    c_k: float           # Bi-Lipschitz structural cost (Pi_K)
    s_irr: float         # Irreversible premature commit risk
    r_w: float           # Witness exposure cost
    has_material_warrant: bool
    rox_payload: int
    rox_mask_in: int
    rox_mask_out: int
    plasma_noise_pi: float
    ky_expression: str
    gamma_nash: float = 0.0          # Sovereign decoupling gamma=0 -> det(I - 0*J_Nash)^(-1) = 1.0
    j_nash_eigenvalue: float = 0.5   # Spectral Nash coupling eigenvalue
    cobordism_d1_d2: float = 0.0     # Thom cobordism boundary-of-boundary: d1*d2 == 0
    delta_prov: float = 0.0          # Ma'at bilateral provenance: |w_inst - w_borger| + delta_epist == 0
    hangtag_id: str = "KC-ARR-2026-025"


class WitnessCapsule205B:
    """
    SPEC-213 / SPEC-416 Canonical 205-Byte (1640-bit) Binary Witness Capsule:
      - WitnessPreCommit  (W_pre  = 119 B, '<QQ32sfBH32s32s')
      - WitnessPostCommit (W_post =  86 B, '<QQ32sBfB32s')
      - Involution lock: post.w_pre_hash == pre.w_pre_hash
    """

    W_PRE_STRUCT = struct.Struct("<QQ32sfBH32s32s")   # 8+8+32+4+1+2+32+32 = 119 B
    W_POST_STRUCT = struct.Struct("<QQ32sBfB32s")     # 8+8+32+1+4+1+32    =  86 B
    TOTAL_BYTES = 205

    GATE_DECISION_MAP = {"OPEN": 0x01, "HOLD": 0x02, "KILL": 0x03}
    FINAL_STATUS_MAP = {"OPEN": 0x01, "HOLD": 0x02, "KILL": 0x03, "MISMATCH": 0xEE, "TRAP": 0xFF}

    @classmethod
    def pack_capsule(
        cls,
        sequence_id: int,
        timestamp_pre_ns: int,
        timestamp_post_ns: int,
        candidate_payload: bytes,
        kernel_drift_val: float,
        gate_decision: str,
        reason_code: int,
        prev_block_hash: bytes,
        hpis_latch_status: int = 0x01,
        thermo_exhaust_nJ: float = 12.5,
        tamper_post_hash: bool = False,
    ) -> bytes:
        cand_hash = hashlib.sha256(candidate_payload).digest()
        prev_h = prev_block_hash if len(prev_block_hash) == 32 else hashlib.sha256(prev_block_hash).digest()
        g_code = cls.GATE_DECISION_MAP.get(gate_decision.upper(), 0x03)

        pre_header = struct.pack(
            "<QQ32sfBH32s",
            sequence_id,
            timestamp_pre_ns,
            cand_hash,
            float(kernel_drift_val),
            g_code,
            reason_code & 0xFFFF,
            prev_h,
        )
        w_pre_hash = hashlib.sha256(pre_header).digest()
        w_pre_bytes = cls.W_PRE_STRUCT.pack(
            sequence_id,
            timestamp_pre_ns,
            cand_hash,
            float(kernel_drift_val),
            g_code,
            reason_code & 0xFFFF,
            prev_h,
            w_pre_hash,
        )

        post_ref_hash = hashlib.sha256(b"TAMPERED_PRE_HASH").digest() if tamper_post_hash else w_pre_hash
        f_code = 0xFF if tamper_post_hash else cls.FINAL_STATUS_MAP.get(gate_decision.upper(), 0x03)
        post_header = struct.pack(
            "<QQ32sBfB",
            sequence_id,
            timestamp_post_ns,
            post_ref_hash,
            hpis_latch_status & 0xFF,
            float(thermo_exhaust_nJ),
            f_code,
        )
        w_post_hash = hashlib.sha256(post_header).digest()
        w_post_bytes = cls.W_POST_STRUCT.pack(
            sequence_id,
            timestamp_post_ns,
            post_ref_hash,
            hpis_latch_status & 0xFF,
            float(thermo_exhaust_nJ),
            f_code,
            w_post_hash,
        )
        return w_pre_bytes + w_post_bytes

    @classmethod
    def verify_capsule(cls, capsule_bytes: bytes, tau_max_ns: int = 30_000_000_000) -> Dict[str, Any]:
        if len(capsule_bytes) != cls.TOTAL_BYTES:
            return {
                "valid": False,
                "rtl_verdict_code": 0xFF,
                "verdict": "KILL",
                "voltage_v": 0.00,
                "reason": f"Invalid capsule length: {len(capsule_bytes)} != 205",
            }
        w_pre = cls.W_PRE_STRUCT.unpack(capsule_bytes[:119])
        w_post = cls.W_POST_STRUCT.unpack(capsule_bytes[119:])

        seq_pre, ts_pre, cand_hash, drift_val, g_code, r_code, prev_h, w_pre_hash = w_pre
        seq_post, ts_post, post_w_pre_hash, hpis_latch, exhaust_nj, f_code, w_post_hash = w_post

        recomputed_pre = hashlib.sha256(capsule_bytes[:87]).digest()
        recomputed_post = hashlib.sha256(capsule_bytes[119:173]).digest()
        dt_ns = ts_post - ts_pre

        involution_ok = (w_pre_hash == post_w_pre_hash) and (w_pre_hash == recomputed_pre) and (w_post_hash == recomputed_post)
        seq_ok = (seq_pre == seq_post)
        time_ok = (0 <= dt_ns <= tau_max_ns)
        thermo_ok = (exhaust_nj > 0.0)

        if not (involution_ok and seq_ok and time_ok and thermo_ok) or f_code in (0xEE, 0xFF):
            return {
                "valid": False,
                "involution_ok": involution_ok,
                "seq_ok": seq_ok,
                "time_ok": time_ok,
                "rtl_verdict_code": 0xFF,
                "verdict": "KILL",
                "voltage_v": 0.00,
                "w_pre_hash": w_pre_hash.hex(),
                "w_post_hash": w_post_hash.hex(),
                "reason": "0xFF TRAP_TAMPER: Involution or tau_max violation",
            }

        if g_code == 0x01 and f_code == 0x01 and hpis_latch == 0x01 and abs(drift_val) <= 1e-6:
            return {
                "valid": True,
                "involution_ok": True,
                "seq_ok": True,
                "time_ok": True,
                "rtl_verdict_code": 0x01,
                "verdict": "OPEN",
                "voltage_v": 5.00,
                "w_pre_hash": w_pre_hash.hex(),
                "w_post_hash": w_post_hash.hex(),
                "reason": "0x01 REALIZED: 205B capsule verified in O(1)",
            }
        if g_code == 0x02 and f_code == 0x02:
            return {
                "valid": True,
                "involution_ok": True,
                "seq_ok": True,
                "time_ok": True,
                "rtl_verdict_code": 0x02,
                "verdict": "HOLD",
                "voltage_v": 2.50,
                "w_pre_hash": w_pre_hash.hex(),
                "w_post_hash": w_post_hash.hex(),
                "reason": "0x02 HOLD: A5 Butterfly Pocket stasis (2.50 V DC)",
            }
        return {
            "valid": False,
            "involution_ok": involution_ok,
            "seq_ok": seq_ok,
            "time_ok": time_ok,
            "rtl_verdict_code": 0x03,
            "verdict": "KILL",
            "voltage_v": 0.00,
            "w_pre_hash": w_pre_hash.hex(),
            "w_post_hash": w_post_hash.hex(),
            "reason": "0x03 KILL: Gate decision or drift violation",
        }


# ============================================================================
# 3. PARSER, SERIALIZER & FAIL-CLOSED EVALUATOR
# ============================================================================

class KYGrammarEngine:
    """Deterministic parser and fail-closed evaluator for KY v1.5-MASTER."""

    def __init__(self, tau_open: float = 0.25, tau_kill: float = 0.60) -> None:
        self.tau_open = tau_open
        self.tau_kill = tau_kill
        self._worm_chain: List[str] = [
            hashlib.sha256(b"LOCUS_ZERO_0xABCDEF00_KREATIV_CORE_V3").hexdigest()
        ]

    def _seal_worm(self, record_str: str) -> str:
        prev = self._worm_chain[-1]
        h = hashlib.sha256(f"{prev}||{record_str}".encode("utf-8")).hexdigest()
        self._worm_chain.append(h)
        return h[:16]

    def parse_unicode(self, expr: str) -> Optional[KYAST]:
        s = expr.strip().replace(" ", "")
        if not s:
            return None

        # 1. Extract gate (last character)
        gate_char = s[-1]
        if gate_char not in UNICODE_TO_ASCII_GATES:
            return None
        s = s[:-1]

        # 2. Check prefix ✓
        has_prefix_validate = False
        if s.startswith("✓"):
            has_prefix_validate = True
            s = s[1:]

        # 3. Locate parenthesized chain
        if not s.startswith("(") or ")" not in s:
            return None
        close_idx = s.find(")")
        chain_str = s[1:close_idx]
        rest = s[close_idx + 1:]

        if not chain_str:
            return None

        # 4. Parse chain: node (flow node)* field_clause*
        nodes: List[str] = []
        flows: List[str] = []
        fields: List[str] = []

        i = 0
        expect_node = True
        while i < len(chain_str):
            if chain_str[i:i+2] == "ΔK":
                fields.append("ΔK")
                i += 2
                continue
            ch = chain_str[i]
            if expect_node:
                if ch in UNICODE_TO_ASCII_NODES:
                    nodes.append(ch)
                    expect_node = False
                    i += 1
                else:
                    return None
            else:
                if ch in UNICODE_TO_ASCII_FLOWS:
                    flows.append(ch)
                    expect_node = True
                    i += 1
                elif ch in FIELD_MARKS:
                    fields.append(ch)
                    i += 1
                else:
                    return None

        if expect_node or not nodes:
            return None

        # 5. Parse validity_mark and suffix (audits / times)
        validity_mark: Optional[str] = None
        for vm in sorted(VALIDITY_MARKS, key=len, reverse=True):
            if rest.startswith(vm):
                validity_mark = vm
                rest = rest[len(vm):]
                break

        audits: List[str] = []
        times: List[str] = []
        j = 0
        while j < len(rest):
            if rest[j:j+2] == "t*":
                times.append("t*")
                j += 2
            elif rest[j] in AUDIT_MARKS:
                audits.append(rest[j])
                j += 1
            elif rest[j] in TIME_MARKS:
                times.append(rest[j])
                j += 1
            else:
                return None

        return KYAST(
            has_prefix_validate=has_prefix_validate,
            nodes=tuple(nodes),
            flows=tuple(flows),
            fields=tuple(fields),
            validity_mark=validity_mark,
            audits=tuple(audits),
            times=tuple(times),
            declared_gate=gate_char,
        )

    def ast_to_unicode(self, ast: KYAST) -> str:
        prefix = "✓" if ast.has_prefix_validate else ""
        parts = [ast.nodes[0]]
        for fl, nd in zip(ast.flows, ast.nodes[1:]):
            parts.append(fl)
            parts.append(nd)
        chain_s = "".join(parts) + "".join(ast.fields)
        vm_s = ast.validity_mark if ast.validity_mark else ""
        suf_s = "".join(ast.audits) + "".join(ast.times)
        return f"{prefix}({chain_s}){vm_s}{suf_s} {ast.declared_gate}"

    def ast_to_ascii(self, ast: KYAST) -> str:
        parts = [UNICODE_TO_ASCII_NODES[ast.nodes[0]]]
        for fl, nd in zip(ast.flows, ast.nodes[1:]):
            parts.append(UNICODE_TO_ASCII_FLOWS[fl])
            parts.append(UNICODE_TO_ASCII_NODES[nd])
        chain_ascii = " ".join(parts)

        if ast.has_prefix_validate:
            body = f"validate({chain_ascii})"
        else:
            body = f"chain({chain_ascii})"

        clauses = [body]
        if ast.validity_mark:
            clauses.append(f"mark({ast.validity_mark})")
        if ast.audits:
            audit_names = ["hash" if a == "#" else "commit" for a in ast.audits]
            clauses.append(f"audit({','.join(audit_names)})")
        clauses.append(f"gate={UNICODE_TO_ASCII_GATES[ast.declared_gate]}")
        return f"KY[ {' '.join(clauses)} ]"

    def ascii_to_unicode(self, ascii_str: str) -> Optional[str]:
        s = ascii_str.strip()
        if not (s.startswith("KY[") and s.endswith("]")):
            return None
        inner = s[3:-1].strip()

        has_validate = inner.startswith("validate(")
        if not (has_validate or inner.startswith("chain(")):
            return None
        open_p = inner.find("(")
        close_p = inner.find(")")
        if open_p == -1 or close_p == -1:
            return None

        chain_tokens = inner[open_p + 1:close_p].strip().split()
        if not chain_tokens or len(chain_tokens) % 2 == 0:
            return None

        nodes: List[str] = []
        flows: List[str] = []
        for idx, tok in enumerate(chain_tokens):
            if idx % 2 == 0:
                if tok not in ASCII_TO_UNICODE_NODES:
                    return None
                nodes.append(ASCII_TO_UNICODE_NODES[tok])
            else:
                if tok not in ASCII_TO_UNICODE_FLOWS:
                    return None
                flows.append(ASCII_TO_UNICODE_FLOWS[tok])

        rest = inner[close_p + 1:].strip()
        validity_mark = None
        if "mark(" in rest:
            m_start = rest.find("mark(") + 5
            m_end = rest.find(")", m_start)
            validity_mark = rest[m_start:m_end]

        audits: List[str] = []
        if "audit(" in rest:
            a_start = rest.find("audit(") + 6
            a_end = rest.find(")", a_start)
            for item in rest[a_start:a_end].split(","):
                item = item.strip()
                if item == "hash":
                    audits.append("#")
                elif item == "commit":
                    audits.append("!")

        if "gate=" not in rest:
            return None
        g_name = rest.split("gate=")[-1].strip()
        if g_name not in ASCII_TO_UNICODE_GATES:
            return None
        gate_u = ASCII_TO_UNICODE_GATES[g_name]

        ast = KYAST(
            has_prefix_validate=has_validate,
            nodes=tuple(nodes),
            flows=tuple(flows),
            fields=(),
            validity_mark=validity_mark,
            audits=tuple(audits),
            times=(),
            declared_gate=gate_u,
        )
        return self.ast_to_unicode(ast)

    def evaluate(self, expr: str) -> EvalResult:
        ast = self.parse_unicode(expr)
        if ast is None:
            w_hash = self._seal_worm(f"SYNTAX_INVALID||{expr}")
            return EvalResult(
                expression_unicode=expr,
                expression_ascii="INVALID_ASCII",
                syntax="invalid",
                type_status="invalid",
                admissibility="kill",
                computed_gate="KILL",
                declared_gate="INVALID",
                gate_match=False,
                final_verdict="KILL",
                d_latch_voltage=0.00,
                worm_hash=w_hash,
                reasons=["Syntax error: failed EBNF tokenization -> immediate fail-closed KILL"],
            )

        declared_gate_str = UNICODE_TO_ASCII_GATES[ast.declared_gate].upper()
        reasons: List[str] = []
        type_valid = True
        requires_audit = False
        is_hold_flow = False

        # 1. Check node-to-node transitions
        for src, fl, dst in zip(ast.nodes[:-1], ast.flows, ast.nodes[1:]):
            pair = (src, dst)
            if pair not in LEGAL_TRANSITIONS:
                type_valid = False
                reasons.append(f"Illegal transition: {src} -> {dst} (violates D0->D3 layer ordering)")
                continue

            rule = LEGAL_TRANSITIONS[pair]
            if rule == "REQUIRES_AUDIT":
                requires_audit = True
            elif rule == "REQUIRES_VALIDATE" and not (ast.has_prefix_validate or ast.validity_mark in {"∈K", "⊢"}):
                type_valid = False
                reasons.append(f"Transition {src} -> {dst} requires explicit validation mark")
            elif rule == "REQUIRES_DRIFT" and fl != "~" and "↺" not in ast.fields:
                type_valid = False
                reasons.append(f"Self-transition {src} -> {dst} requires continuous drift (~) or loop (↺)")

            if fl == "⇒":
                requires_audit = True
            if fl == "~":
                is_hold_flow = True

        if "●" in ast.nodes:
            requires_audit = True

        # 2. Check Audit Law (Section 7.1)
        has_audit = len(ast.audits) > 0
        if requires_audit and not has_audit:
            reasons.append("Audit Law violation: irreversible transition (⇒ or ●) lacks # or ! audit mark")

        # 3. Determine computed admissibility & gate
        if ast.validity_mark in {"∉K", "⊬", "≠"}:
            admissibility = "kill"
            computed_gate = "KILL"
            reasons.append(f"Validity mark {ast.validity_mark} forces KILL")
        elif not type_valid or (requires_audit and not has_audit):
            admissibility = "kill"
            computed_gate = "KILL"
        elif ast.nodes[-1] == "△":
            if declared_gate_str in {"HOLD", "KILL"}:
                admissibility = declared_gate_str.lower()
                computed_gate = declared_gate_str
                reasons.append(f"Threshold node △ resolves to {computed_gate}")
            else:
                admissibility = "kill"
                computed_gate = "KILL"
                reasons.append("Illegal transition: THRESHOLD (△) cannot resolve to OPEN")
        elif is_hold_flow and "●" not in ast.nodes:
            admissibility = "hold"
            computed_gate = "HOLD"
            reasons.append("Expression in continuous stabilization (~) without commit -> HOLD")
        elif ast.has_prefix_validate or ast.validity_mark in {"∈K", "⊢"}:
            admissibility = "pass"
            computed_gate = "OPEN"
            reasons.append("Expression passes validation, typecheck, and audit law")
        else:
            admissibility = "hold"
            computed_gate = "HOLD"
            reasons.append("Unvalidated admissible structure defaults to HOLD")

        # 4. Fail-closed gate consistency check
        gate_match = (computed_gate == declared_gate_str)
        if not gate_match:
            final_verdict = "KILL"
            reasons.append(
                f"Gate mismatch: computed={computed_gate} vs declared={declared_gate_str} -> fail-closed KILL"
            )
        else:
            final_verdict = computed_gate
            reasons.append("Gate matches computed status")

        voltage = 5.00 if final_verdict == "OPEN" else 0.00
        a5_voltage = 5.00 if final_verdict == "OPEN" else (2.50 if final_verdict == "HOLD" else 0.00)
        u_str = self.ast_to_unicode(ast)
        a_str = self.ast_to_ascii(ast)
        w_hash = self._seal_worm(f"{u_str}||{final_verdict}||{voltage:.2f}V")
        capsule = WitnessCapsule205B.pack_capsule(
            sequence_id=len(self._worm_chain),
            timestamp_pre_ns=1_000_000,
            timestamp_post_ns=1_012_500,
            candidate_payload=u_str.encode("utf-8"),
            kernel_drift_val=0.0 if final_verdict in ("OPEN", "HOLD") else 1.0,
            gate_decision=final_verdict,
            reason_code=0x0000 if final_verdict == "OPEN" else (0x00A5 if final_verdict == "HOLD" else 0xDEAD),
            prev_block_hash=self._worm_chain[-2].encode("utf-8"),
            hpis_latch_status=0x01 if final_verdict == "OPEN" else 0x00,
        )

        return EvalResult(
            expression_unicode=u_str,
            expression_ascii=a_str,
            syntax="valid",
            type_status="valid" if type_valid else "invalid",
            admissibility=admissibility,
            computed_gate=computed_gate,
            declared_gate=declared_gate_str,
            gate_match=gate_match,
            final_verdict=final_verdict,
            d_latch_voltage=voltage,
            a5_gate_voltage=a5_voltage,
            worm_hash=w_hash,
            capsule_205b=capsule,
            reasons=reasons,
        )

    def evaluate_kreativ_core_campaign(self, cand: SomaticCampaignCandidate) -> Dict[str, object]:
        """Evaluates Aethelgard campaign candidates under KREATIV-CORE v3.1-GRANITUM, SPEC-400 & SPEC-416."""
        # 1. Compute Integrity-Adjusted Utility, Nash Spectral Resolvent & Nullpunkt Margin
        u_tot = cand.u_raw - (cand.c_k + cand.s_irr + cand.r_w)
        denom = 1.0 - (cand.gamma_nash * cand.j_nash_eigenvalue)
        nash_resolvent = (1.0 / denom) if abs(denom) > 1e-9 else 0.0
        u_nash = nash_resolvent * u_tot
        mu_supra = u_nash / cand.u_raw if cand.u_raw > 0 else -1.0

        # 2. ROX Involutive & Mask Integrity Check
        mask_frozen = (cand.rox_mask_in == cand.rox_mask_out)
        rox_roundtrip = ((cand.rox_payload ^ cand.rox_mask_in) ^ cand.rox_mask_out) == cand.rox_payload
        rox_ok = mask_frozen and rox_roundtrip

        # 3. Cobordism (d1*d2 == 0) & Ma'at Bilateral Provenance (Delta_prov == 0)
        cobordism_ok = abs(cand.cobordism_d1_d2) <= 1e-9
        provenance_ok = abs(cand.delta_prov) <= 1e-9

        # 4. Plasma Epistemic Risk Status
        if cand.plasma_noise_pi < self.tau_open:
            plasma_status = "PLASMA_OPEN"
        elif cand.plasma_noise_pi < self.tau_kill:
            plasma_status = "PLASMA_HOLD"
        else:
            plasma_status = "PLASMA_KILL"

        # 5. Evaluate KY Realization Expression
        ky_eval = self.evaluate(cand.ky_expression)

        # 6. Synthesize Fail-Closed Sovereignty Verdict
        if (
            not cand.has_material_warrant
            or mu_supra < 0.0
            or not rox_ok
            or not cobordism_ok
            or not provenance_ok
            or plasma_status == "PLASMA_KILL"
        ):
            omega_verdict = "KILL"
            ontological_class = "BLØFF (Ghost Win / Dead Noise / 0xFF TRAP_TAMPER)"
        elif plasma_status == "PLASMA_HOLD" or ky_eval.final_verdict == "HOLD":
            omega_verdict = "HOLD"
            ontological_class = "THEORETICAL ASYLUM (D1 Buffer / A5 Pocket 2.50 V)"
        elif ky_eval.final_verdict == "OPEN" and mu_supra >= 0.0 and rox_ok and cobordism_ok and provenance_ok:
            omega_verdict = "OPEN"
            ontological_class = "BØFF (Load-Bearing Form / True Strategy)"
        else:
            omega_verdict = "KILL"
            ontological_class = "INTEGRITY COLLAPSE"

        capsule_205b = WitnessCapsule205B.pack_capsule(
            sequence_id=len(self._worm_chain),
            timestamp_pre_ns=1_000_000,
            timestamp_post_ns=1_012_500,
            candidate_payload=f"{cand.campaign_id}||{cand.hangtag_id}".encode("utf-8"),
            kernel_drift_val=float(abs(cand.delta_prov) + abs(cand.cobordism_d1_d2)),
            gate_decision=omega_verdict,
            reason_code=0x0000 if omega_verdict == "OPEN" else (0x00A5 if omega_verdict == "HOLD" else 0x00FF),
            prev_block_hash=self._worm_chain[-1].encode("utf-8"),
            hpis_latch_status=0x01 if omega_verdict == "OPEN" else 0x00,
            tamper_post_hash=not (cobordism_ok and provenance_ok),
        )
        capsule_audit = WitnessCapsule205B.verify_capsule(capsule_205b)

        return {
            "campaign_id": cand.campaign_id,
            "title": cand.title,
            "hangtag_id": cand.hangtag_id,
            "u_tot": round(u_tot, 2),
            "nash_resolvent": round(nash_resolvent, 4),
            "u_nash": round(u_nash, 2),
            "mu_supra": round(mu_supra, 4),
            "rox_ok": rox_ok,
            "cobordism_ok": cobordism_ok,
            "provenance_ok": provenance_ok,
            "plasma_status": plasma_status,
            "ky_verdict": ky_eval.final_verdict,
            "omega_verdict": omega_verdict,
            "ontological_class": ontological_class,
            "d_latch_voltage": 5.00 if omega_verdict == "OPEN" else 0.00,
            "a5_gate_voltage": 5.00 if omega_verdict == "OPEN" else (2.50 if omega_verdict == "HOLD" else 0.00),
            "ky_ascii": ky_eval.expression_ascii,
            "worm_hash": ky_eval.worm_hash,
            "capsule_205b_len": len(capsule_205b),
            "w_pre_hash": capsule_audit["w_pre_hash"],
            "w_post_hash": capsule_audit["w_post_hash"],
            "rtl_verdict_code": capsule_audit["rtl_verdict_code"],
        }


# ============================================================================
# 4. KY v1.5-MASTER SINGLE-PASS O(n) REFERENCE PARSER & ROUNDTRIP CODEC
#    (Alternativ A Locked: '●' strictly state node, '!' commit event, D1.2 Codec)
# ============================================================================

NODES: Dict[str, str] = {
    "○": "raw",        # D0: Raw Bit Field
    "∅": "estimate",   # D1: Reversible Phase / Estimate
    "□": "struct",     # D1.2: Structural Numeric / Admissible
    "△": "threshold",  # D1.5: Threshold Boundary
    "◇": "viability",  # D1.5: Viability / Numeric Risk
    "●": "committed",  # D2: Committed Symbolic State (KUN NODE, IKKE SUFFIX)
}
ASCII_TO_NODE: Dict[str, str] = {v: k for k, v in NODES.items()}

FLOWS: Dict[str, str] = {
    "→": "->",   # Direkte evolusjon
    "~": "~",    # Kontinuerlig drift
    "⇒": "=>",   # Projeksjon (Pi_K)
    "↦": "!>",   # Irreversibel overgang
}
ASCII_TO_FLOW: Dict[str, str] = {v: k for k, v in FLOWS.items()}

GATES: Dict[str, str] = {
    "▸": "OPEN",
    "⏸": "HOLD",
    "‖": "HOLD",
    "✕": "KILL",
}
ASCII_TO_GATE: Dict[str, str] = {
    "OPEN": "▸",
    "HOLD": "⏸",
    "KILL": "✕",
}

LEGAL_TRANSITIONS_BY_NAME: Dict[Tuple[str, str], str] = {
    ("raw", "estimate"): "UNCONDITIONAL",
    ("estimate", "struct"): "UNCONDITIONAL",
    ("struct", "viability"): "UNCONDITIONAL",
    ("viability", "committed"): "REQUIRES_AUDIT",
    ("struct", "committed"): "REQUIRES_AUDIT",
    ("raw", "struct"): "REQUIRES_EXPLICIT_VALIDATION",
    ("struct", "struct"): "DRIFT_ALLOWED",
    ("viability", "viability"): "DRIFT_ALLOWED",
    ("struct", "threshold"): "UNCONDITIONAL",
    ("viability", "threshold"): "UNCONDITIONAL",
}


class KYEngine:
    """Deterministisk O(n) evaluerings- og codec-motor for KY v1.5-MASTER (Locus 0xABCDEF00)."""

    @staticmethod
    def _build_glyph(
        has_prefix_validation: bool,
        nodes: List[str],
        flows: List[str],
        validity_mark: Optional[str],
        audits: List[str],
        declared_gate: str,
    ) -> str:
        prefix = "✓" if has_prefix_validation else ""
        parts = [ASCII_TO_NODE[nodes[0]]]
        for fl, nd in zip(flows, nodes[1:]):
            parts.append(fl)
            parts.append(ASCII_TO_NODE[nd])
        chain_glyph = " ".join(parts)
        vm = validity_mark if validity_mark else ""
        aud = "".join(audits)
        gate_glyph = ASCII_TO_GATE[declared_gate]
        return f"{prefix}({chain_glyph}){vm}{aud} {gate_glyph}"

    @staticmethod
    def to_ascii(
        has_prefix_validation: bool,
        nodes: List[str],
        flows: List[str],
        validity_mark: Optional[str],
        audits: List[str],
        declared_gate: str,
    ) -> str:
        parts = [nodes[0]]
        for fl, nd in zip(flows, nodes[1:]):
            parts.append(FLOWS[fl])
            parts.append(nd)
        chain_ascii = " ".join(parts)
        wrapper = "validate" if has_prefix_validation else "chain"
        vm_part = f"[{validity_mark}]" if validity_mark else ""
        aud_part = "".join(audits)
        return f"{wrapper}({chain_ascii}){vm_part}{aud_part} {declared_gate}"

    @staticmethod
    def from_ascii(ascii_repr: str) -> str:
        s = ascii_repr.strip()
        if not s:
            return ""
        tokens = s.split()
        declared_gate = tokens[-1]
        if declared_gate not in ASCII_TO_GATE:
            return ""
        body = s[: s.rfind(declared_gate)].strip()

        if body.startswith("validate("):
            has_prefix_validation = True
            inner_start = len("validate(")
        elif body.startswith("chain("):
            has_prefix_validation = False
            inner_start = len("chain(")
        else:
            return ""

        close_idx = body.find(")", inner_start)
        if close_idx == -1:
            return ""

        chain_tokens = body[inner_start:close_idx].strip().split()
        if len(chain_tokens) < 3 or len(chain_tokens) % 2 == 0:
            return ""

        nodes: List[str] = []
        flows: List[str] = []
        for idx, tok in enumerate(chain_tokens):
            if idx % 2 == 0:
                if tok not in ASCII_TO_NODE:
                    return ""
                nodes.append(tok)
            else:
                if tok not in ASCII_TO_FLOW:
                    return ""
                flows.append(ASCII_TO_FLOW[tok])

        suffix = body[close_idx + 1 :].strip()
        validity_mark: Optional[str] = None
        if suffix.startswith("[") and "]" in suffix:
            end_b = suffix.find("]")
            validity_mark = suffix[1:end_b]
            suffix = suffix[end_b + 1 :].strip()

        audits = [ch for ch in suffix if ch in AUDIT_MARKS]
        return KYEngine._build_glyph(
            has_prefix_validation, nodes, flows, validity_mark, audits, declared_gate
        )

    @staticmethod
    def evaluate_glyph_expr(expr: str) -> EvalResult:
        s = expr.strip()
        reasons: List[str] = []

        if not s:
            return EvalResult(
                syntax="invalid",
                type_status="invalid",
                type_check="invalid",
                admissibility="kill",
                gate="KILL",
                roundtrip_ok=False,
                reasons=("Empty expression",),
            )

        # 1. Identifiser Gate (siste tegn)
        gate_glyph = s[-1]
        if gate_glyph not in GATES:
            return EvalResult(
                syntax="invalid",
                type_status="invalid",
                type_check="invalid",
                admissibility="kill",
                gate="KILL",
                roundtrip_ok=False,
                reasons=(f"Missing or invalid gate: {gate_glyph}",),
            )
        declared_gate = GATES[gate_glyph]
        body = s[:-1].strip()

        # 2. Sjekk prefix-validering (✓)
        has_prefix_validation = False
        if body.startswith("✓"):
            has_prefix_validation = True
            body = body[1:].strip()

        # 3. Ekstraher kjede innenfor parenteser: ( ... )
        if not body.startswith("(") or ")" not in body:
            return EvalResult(
                syntax="invalid",
                type_status="invalid",
                type_check="invalid",
                admissibility="kill",
                gate="KILL",
                roundtrip_ok=False,
                reasons=("Malformed parenthesis chain",),
            )

        close_idx = body.find(")")
        chain_str = body[1:close_idx].strip()
        suffix_str = body[close_idx + 1 :].strip()

        # 4. Parse suffix (Validity marks & Audit marks)
        validity_mark: Optional[str] = None
        audits: List[str] = []

        rem = suffix_str
        for vm in sorted(VALIDITY_MARKS, key=len, reverse=True):
            if rem.startswith(vm):
                validity_mark = vm
                rem = rem[len(vm) :].strip()
                break

        for ch in rem:
            if ch in AUDIT_MARKS:
                audits.append(ch)
            elif not ch.isspace():
                return EvalResult(
                    syntax="invalid",
                    type_status="invalid",
                    type_check="invalid",
                    admissibility="kill",
                    gate="KILL",
                    roundtrip_ok=False,
                    reasons=(
                        f"Illegal suffix symbol '{ch}' (Note: '●' is strictly a state node, use '!' for commit)",
                    ),
                )

        # 5. Tokeniser kjeden (Node Flow Node ...)
        nodes: List[str] = []
        flows: List[str] = []
        i = 0
        expect_node = True
        while i < len(chain_str):
            if chain_str[i].isspace():
                i += 1
                continue
            if expect_node:
                ch = chain_str[i]
                if ch not in NODES:
                    return EvalResult(
                        syntax="invalid",
                        type_status="invalid",
                        type_check="invalid",
                        admissibility="kill",
                        gate="KILL",
                        roundtrip_ok=False,
                        reasons=(f"Invalid node glyph: {ch}",),
                    )
                nodes.append(NODES[ch])
                expect_node = False
                i += 1
            else:
                ch = chain_str[i]
                if ch not in FLOWS:
                    return EvalResult(
                        syntax="invalid",
                        type_status="invalid",
                        type_check="invalid",
                        admissibility="kill",
                        gate="KILL",
                        roundtrip_ok=False,
                        reasons=(f"Invalid flow glyph: {ch}",),
                    )
                flows.append(ch)
                expect_node = True
                i += 1

        if expect_node or len(nodes) < 2:
            return EvalResult(
                syntax="invalid",
                type_status="invalid",
                type_check="invalid",
                admissibility="kill",
                gate="KILL",
                roundtrip_ok=False,
                reasons=("Incomplete transition chain",),
            )

        # 6. D1.2 Codec Roundtrip Test: Unicode -> Canonical ASCII -> Unicode
        ascii_repr = KYEngine.to_ascii(
            has_prefix_validation, nodes, flows, validity_mark, audits, declared_gate
        )
        reconstructed = KYEngine.from_ascii(ascii_repr)
        canonical_input = KYEngine._build_glyph(
            has_prefix_validation, nodes, flows, validity_mark, audits, declared_gate
        )
        roundtrip_ok = reconstructed == canonical_input
        if not roundtrip_ok:
            return EvalResult(
                syntax="valid",
                type_status="invalid",
                type_check="invalid",
                admissibility="kill",
                gate="KILL",
                roundtrip_ok=False,
                expression_unicode=canonical_input,
                expression_ascii=ascii_repr,
                reasons=("D1.2 Codec Roundtrip failure: decode(encode(x)) != x",),
            )

        # 7. Evaluer lovlige overganger (LEGAL_TRANSITIONS_BY_NAME)
        type_valid = True
        requires_audit = False
        has_drift = False

        for src, fl, dst in zip(nodes[:-1], flows, nodes[1:]):
            pair = (src, dst)
            if pair not in LEGAL_TRANSITIONS_BY_NAME:
                type_valid = False
                reasons.append(f"Illegal transition: {src} -> {dst}")
                continue
            rule = LEGAL_TRANSITIONS_BY_NAME[pair]
            if rule == "REQUIRES_AUDIT":
                requires_audit = True
            elif rule == "REQUIRES_EXPLICIT_VALIDATION" and not (
                has_prefix_validation or validity_mark in {"∈K", "⊢"}
            ):
                type_valid = False
                reasons.append(f"Transition {src} -> {dst} requires explicit validation")
            elif rule == "DRIFT_ALLOWED" and fl != "~":
                type_valid = False
                reasons.append(f"Self-transition {src} -> {dst} requires continuous drift (~)")

            if fl in ("↦", "⇒"):
                requires_audit = True
            if fl == "~":
                has_drift = True

        if "committed" in nodes:
            requires_audit = True

        # 8. Audit-lov for D2/D3: krever både '#' (witness hash) og '!' (commit event) ved commit, eller minst én audit-markør
        has_commit_audit = ("!" in audits and "#" in audits) if "committed" in nodes else (len(audits) > 0)
        if requires_audit and not has_commit_audit:
            reasons.append("Audit violation: transition to committed requires '#' (witness_hash) and '!' (commit_event)")

        # 9. Bestem admissibilitet og portdom
        if validity_mark in {"∉K", "⊬", "≠"}:
            admissibility = "kill"
            computed_gate = "KILL"
            reasons.append(f"Validity mark {validity_mark} forces KILL")
        elif not type_valid or (requires_audit and not has_commit_audit):
            admissibility = "kill"
            computed_gate = "KILL"
        elif has_drift and "committed" not in nodes:
            admissibility = "hold"
            computed_gate = "HOLD"
            reasons.append("Continuous drift (~) without commit resolves to HOLD")
        elif has_prefix_validation or validity_mark in {"∈K", "⊢"} or ("committed" in nodes and has_commit_audit):
            admissibility = "pass"
            computed_gate = "OPEN"
            reasons.append("Valid chain, typecheck, roundtrip, and audit verified")
        else:
            admissibility = "hold"
            computed_gate = "HOLD"
            reasons.append("Unvalidated chain defaults to HOLD")

        if computed_gate != declared_gate:
            final_gate = "KILL"
            admissibility = "kill"
            reasons.append(f"Gate mismatch: computed {computed_gate} != declared {declared_gate} -> KILL")
        else:
            final_gate = computed_gate

        capsule = WitnessCapsule205B.pack_capsule(
            sequence_id=1,
            timestamp_pre_ns=1_000_000,
            timestamp_post_ns=1_012_500,
            candidate_payload=canonical_input.encode("utf-8"),
            kernel_drift_val=0.0 if final_gate in ("OPEN", "HOLD") else 1.0,
            gate_decision=final_gate,
            reason_code=0x0000 if final_gate == "OPEN" else (0x00A5 if final_gate == "HOLD" else 0xDEAD),
            prev_block_hash=b"LOCUS_ZERO_0xABCDEF00_KY_V15_MST",
            hpis_latch_status=0x01 if final_gate == "OPEN" else 0x00,
        )

        return EvalResult(
            syntax="valid",
            type_status="valid" if type_valid else "invalid",
            type_check="valid" if type_valid else "invalid",
            admissibility=admissibility,
            gate=final_gate,
            roundtrip_ok=roundtrip_ok,
            expression_unicode=canonical_input,
            expression_ascii=ascii_repr,
            computed_gate=computed_gate,
            declared_gate=declared_gate,
            gate_match=(computed_gate == declared_gate),
            final_verdict=final_gate,
            d_latch_voltage=5.00 if final_gate == "OPEN" else 0.00,
            a5_gate_voltage=5.00 if final_gate == "OPEN" else (2.50 if final_gate == "HOLD" else 0.00),
            capsule_205b=capsule,
            reasons=tuple(reasons),
        )

