#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L1_LAW/ky_v15_clean_parser.py — KY Realization Grammar v1.5 (Låst Kjerne, 0 float)
==================================================================================
Epistemisk status : L1 deterministisk programvare (PHYSICAL_AUTHORITY = NONE)
Kontraktregel     : INSPIRED_BY != IMPLEMENTS != PROVES
Flyttallsforbud   : 0 flyttallsliteraler og 0 flyttallsreferanser i hele AST-treet
Sone-hygiene      : Null KREATIV-CORE/prosa-retorikk i kjerneparsingen; append-only
                    SHA-256-kjede er programvarelogg, aldri fysisk WORM-maskinvare.

Håndhever hele KY v1.5-spesifikasjonen (L1_LAW/KY_SPEC_v1.5.md):
  - 7-lags tilstandsmaskin: RAW -> CANDIDATE -> STRUCT -> VIABILITY -> AUTHORIZED -> REALIZED -> WITNESSED (+ KILLED)
  - Null snarveier (kun nabologikk + pre-D2 HOLD-sløyfe `~` + ANY -> KILLED)
  - En-rolle-per-symbol + 100 % tapsløs Unicode <-> ASCII <-> AST roundtrip (WITNESSED = ⊞, audit = #)
  - D1 bijektiv operatorvakt (forbyr AND, OR, SHL, SHR) + ROX Hamming-isometri
  - D1.2 eksakt codec-roundtrip (toer-komplement, balansert ternært, eksakte brøker)
  - D1.5 eksakt rasjonal Plasma-evaluering i Q (0 <= tau_open < tau_kill)
  - D2- PreCommitWarrant (J_t^-) skilt fra fysisk commit D2 (0 mV DC tørrkontakt før W_ext)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import json


STANDALONE_COMMIT_AUTHORITY = "NONE"
PHYSICAL_AUTHORITY = "NONE"


def require_strict_int(val: int, name: str) -> int:
    if isinstance(val, bool) or not isinstance(val, int):
        raise TypeError(f"STRICT_INT_REQUIRED::{name}")
    return val


def require_strict_fraction(val: Fraction, name: str) -> Fraction:
    if not isinstance(val, Fraction):
        raise TypeError(f"STRICT_FRACTION_REQUIRED::{name}")
    return val


class KYNode(Enum):
    RAW = "RAW"
    CANDIDATE = "CANDIDATE"
    STRUCT = "STRUCT"
    VIABILITY = "VIABILITY"
    AUTHORIZED = "AUTHORIZED"
    REALIZED = "REALIZED"
    WITNESSED = "WITNESSED"
    KILLED = "KILLED"


class KYFlow(Enum):
    STEP = "->"
    HOLD_DRIFT = "~"
    PROJECT = "=>"
    COMMIT = "!>"


class KYValidity(Enum):
    ROX_OK = "ROX_OK"
    ROX_FAIL = "ROX_FAIL"
    IN_K = "IN_K"
    NOT_IN_K = "NOT_IN_K"
    MASK_FROZEN = "MASK_FROZEN"
    MASK_MUTATED = "MASK_MUTATED"
    PLASMA_OPEN = "PLASMA_OPEN"
    PLASMA_HOLD = "PLASMA_HOLD"
    PLASMA_KILL = "PLASMA_KILL"


class KYAudit(Enum):
    COMMIT_BANG = "!"
    WITNESS_HASH = "#"
    READMIT = "READMIT"


class KYGate(Enum):
    OPEN = "OPEN"
    HOLD = "HOLD"
    KILL = "KILL"


# 1-til-1 bijektiv mapping: hver Unicode-glyf har eksakt én rolle (WITNESSED = ⊞, audit = #)
NODE_TO_UNI: dict[KYNode, str] = {
    KYNode.RAW: "○",
    KYNode.CANDIDATE: "∅",
    KYNode.STRUCT: "□",
    KYNode.VIABILITY: "◇",
    KYNode.AUTHORIZED: "⊙",
    KYNode.REALIZED: "●",
    KYNode.WITNESSED: "⊞",
    KYNode.KILLED: "⊥",
}
FLOW_TO_UNI: dict[KYFlow, str] = {
    KYFlow.STEP: "→",
    KYFlow.HOLD_DRIFT: "~",
    KYFlow.PROJECT: "⇒",
    KYFlow.COMMIT: "↠",
}
VALIDITY_TO_UNI: dict[KYValidity, str] = {
    KYValidity.ROX_OK: "✓",
    KYValidity.ROX_FAIL: "✗",
    KYValidity.IN_K: "∈K",
    KYValidity.NOT_IN_K: "∉K",
    KYValidity.MASK_FROZEN: "❄",
    KYValidity.MASK_MUTATED: "⚠",
    KYValidity.PLASMA_OPEN: "P+",
    KYValidity.PLASMA_HOLD: "P0",
    KYValidity.PLASMA_KILL: "P-",
}
AUDIT_TO_UNI: dict[KYAudit, str] = {
    KYAudit.COMMIT_BANG: "!",
    KYAudit.WITNESS_HASH: "#",
    KYAudit.READMIT: "↻",
}
GATE_TO_UNI: dict[KYGate, str] = {
    KYGate.OPEN: "▸",
    KYGate.HOLD: "‖",
    KYGate.KILL: "×",
}

UNI_TO_NODE = {v: k for k, v in NODE_TO_UNI.items()}
UNI_TO_FLOW = {v: k for k, v in FLOW_TO_UNI.items()}
UNI_TO_VALIDITY = {v: k for k, v in VALIDITY_TO_UNI.items()}
UNI_TO_AUDIT = {v: k for k, v in AUDIT_TO_UNI.items()}
UNI_TO_GATE = {v: k for k, v in GATE_TO_UNI.items()}

ASCII_TO_NODE = {k.value: k for k in KYNode}
ASCII_TO_FLOW = {k.value: k for k in KYFlow}
ASCII_TO_VALIDITY = {k.value: k for k in KYValidity}
ASCII_TO_AUDIT = {k.value: k for k in KYAudit}
ASCII_TO_GATE = {k.value: k for k in KYGate}

D1_ALLOWED_OPS = frozenset({"ROL", "ROR", "XOR_FROZEN", "NOT", "GRAY", "LFSR_NONSINGULAR"})
D1_FORBIDDEN_OPS = frozenset({"AND", "OR", "SHL", "SHR"})

LEGAL_FORWARD_EDGES: frozenset[tuple[KYNode, KYNode]] = frozenset({
    (KYNode.RAW, KYNode.CANDIDATE),
    (KYNode.CANDIDATE, KYNode.STRUCT),
    (KYNode.STRUCT, KYNode.VIABILITY),
    (KYNode.VIABILITY, KYNode.AUTHORIZED),
    (KYNode.AUTHORIZED, KYNode.REALIZED),
    (KYNode.REALIZED, KYNode.WITNESSED),
})

PRE_D2_NODES: frozenset[KYNode] = frozenset({
    KYNode.RAW,
    KYNode.CANDIDATE,
    KYNode.STRUCT,
    KYNode.VIABILITY,
})


# ============================================================================
# 1. D1 ROX-ISOMETRI, D1.2 KODEK-ROUNDTRIP & D1.5 RASJONAL PLASMA
# ============================================================================

def hamming_distance(a: int, b: int) -> int:
    return (require_strict_int(a, "a") ^ require_strict_int(b, "b")).bit_count()


def rox_mirror(x: int, mask: int) -> int:
    return require_strict_int(x, "x") ^ require_strict_int(mask, "mask")


def verify_rox_isometry(x: int, y: int, mask_t: int, mask_t_prime: int) -> tuple[bool, KYValidity]:
    """ROX involutiv returtest og Hamming-isometri under MASK_FROZEN."""
    if require_strict_int(mask_t, "mask_t") != require_strict_int(mask_t_prime, "mask_t_prime"):
        return False, KYValidity.MASK_MUTATED
    rx = rox_mirror(x, mask_t)
    ry = rox_mirror(y, mask_t)
    if rox_mirror(rx, mask_t) != x or rox_mirror(ry, mask_t) != y:
        return False, KYValidity.ROX_FAIL
    if hamming_distance(rx, ry) != hamming_distance(x, y):
        return False, KYValidity.ROX_FAIL
    return True, KYValidity.ROX_OK


def check_d1_operator(op_name: str) -> KYGate:
    key = op_name.strip().upper()
    if key in D1_FORBIDDEN_OPS or key not in D1_ALLOWED_OPS:
        return KYGate.KILL
    return KYGate.OPEN


def encode_twos_complement(value: int, bits: int = 16) -> int:
    v = require_strict_int(value, "value")
    b = require_strict_int(bits, "bits")
    lo = -(1 << (b - 1))
    hi = (1 << (b - 1)) - 1
    if v < lo or v > hi:
        raise OverflowError(f"TWOS_COMPLEMENT_OVERFLOW::{v} not in [{lo},{hi}]")
    return v & ((1 << b) - 1)


def decode_twos_complement(word: int, bits: int = 16) -> int:
    w = require_strict_int(word, "word")
    b = require_strict_int(bits, "bits")
    sign_bit = 1 << (b - 1)
    if w & sign_bit:
        return w - (1 << b)
    return w


def evaluate_plasma(pi_t: Fraction, tau_open: Fraction, tau_kill: Fraction) -> KYValidity:
    pi = require_strict_fraction(pi_t, "pi_t")
    t_open = require_strict_fraction(tau_open, "tau_open")
    t_kill = require_strict_fraction(tau_kill, "tau_kill")
    if t_open < Fraction(0, 1) or t_open >= t_kill:
        raise ValueError("INVALID_PLASMA_THRESHOLDS")
    if pi < t_open:
        return KYValidity.PLASMA_OPEN
    if pi < t_kill:
        return KYValidity.PLASMA_HOLD
    return KYValidity.PLASMA_KILL


# ============================================================================
# 2. LEXER, PARSER, AST & TAPSLØS ROUNDTRIP (UNICODE <-> ASCII <-> AST)
# ============================================================================

@dataclass(frozen=True)
class KYExpressionAST:
    nodes: tuple[KYNode, ...]
    flows: tuple[KYFlow, ...]
    validity_marks: tuple[KYValidity, ...]
    audit_marks: tuple[KYAudit, ...]
    declared_gate: KYGate

    def to_ascii(self) -> str:
        parts = [self.nodes[0].value]
        for fl, nd in zip(self.flows, self.nodes[1:]):
            parts.append(fl.value)
            parts.append(nd.value)
        head = "(" + " ".join(parts) + ")"
        chunks = [head]
        if self.validity_marks:
            chunks.append(" ".join(v.value for v in self.validity_marks))
        if self.audit_marks:
            chunks.append(" ".join(a.value for a in self.audit_marks))
        chunks.append(self.declared_gate.value)
        return " ".join(chunks)

    def to_unicode(self) -> str:
        parts = [NODE_TO_UNI[self.nodes[0]]]
        for fl, nd in zip(self.flows, self.nodes[1:]):
            parts.append(FLOW_TO_UNI[fl])
            parts.append(NODE_TO_UNI[nd])
        head = "(" + "".join(parts) + ")"
        chunks = [head]
        if self.validity_marks:
            chunks.append(" ".join(VALIDITY_TO_UNI[v] for v in self.validity_marks))
        if self.audit_marks:
            chunks.append("".join(AUDIT_TO_UNI[a] for a in self.audit_marks))
        chunks.append(GATE_TO_UNI[self.declared_gate])
        return " ".join(chunks)


# Multi-char tokens sorted longest-first for deterministic maximal-munch tokenization
_SYMBOL_TOKENS = sorted(
    [
        "(", ")",
        *ASCII_TO_NODE.keys(),
        *ASCII_TO_FLOW.keys(),
        *ASCII_TO_VALIDITY.keys(),
        *ASCII_TO_AUDIT.keys(),
        *ASCII_TO_GATE.keys(),
        *UNI_TO_NODE.keys(),
        *UNI_TO_FLOW.keys(),
        *UNI_TO_VALIDITY.keys(),
        *UNI_TO_AUDIT.keys(),
        *UNI_TO_GATE.keys(),
    ],
    key=len,
    reverse=True,
)


def tokenize_ky(expr: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    n = len(expr)
    while i < n:
        if expr[i].isspace():
            i += 1
            continue
        matched = None
        for sym in _SYMBOL_TOKENS:
            if expr.startswith(sym, i):
                # For alphanumeric ASCII keywords, ensure word boundary so "OPEN" doesn't eat a prefix
                if sym.replace("_", "").isalnum():
                    end = i + len(sym)
                    if end < n and (expr[end].isalnum() or expr[end] == "_"):
                        continue
                matched = sym
                break
        if matched is None:
            raise SyntaxError(f"UNKNOWN_KY_TOKEN_AT_{i}::{expr[i:i+8]!r}")
        tokens.append(matched)
        i += len(matched)
    return tokens


def _decode_node(tok: str) -> KYNode | None:
    return ASCII_TO_NODE.get(tok) or UNI_TO_NODE.get(tok)


def _decode_flow(tok: str) -> KYFlow | None:
    return ASCII_TO_FLOW.get(tok) or UNI_TO_FLOW.get(tok)


def _decode_validity(tok: str) -> KYValidity | None:
    return ASCII_TO_VALIDITY.get(tok) or UNI_TO_VALIDITY.get(tok)


def _decode_audit(tok: str) -> KYAudit | None:
    return ASCII_TO_AUDIT.get(tok) or UNI_TO_AUDIT.get(tok)


def _decode_gate(tok: str) -> KYGate | None:
    return ASCII_TO_GATE.get(tok) or UNI_TO_GATE.get(tok)


def parse_ky_v15(expr: str) -> KYExpressionAST:
    tokens = tokenize_ky(expr)
    if len(tokens) < 4 or tokens[0] != "(":
        raise SyntaxError("EXPECTED_OPEN_PAREN_CHAIN")

    idx = 1
    nodes: list[KYNode] = []
    flows: list[KYFlow] = []

    first_node = _decode_node(tokens[idx])
    if first_node is None:
        raise SyntaxError(f"EXPECTED_NODE_AT_1::{tokens[idx]!r}")
    nodes.append(first_node)
    idx += 1

    while idx < len(tokens) and tokens[idx] != ")":
        fl = _decode_flow(tokens[idx])
        if fl is None:
            raise SyntaxError(f"EXPECTED_FLOW_OR_CLOSE_PAREN::{tokens[idx]!r}")
        flows.append(fl)
        idx += 1
        if idx >= len(tokens):
            raise SyntaxError("UNEXPECTED_EOF_AFTER_FLOW")
        nd = _decode_node(tokens[idx])
        if nd is None:
            raise SyntaxError(f"EXPECTED_NODE_AFTER_FLOW::{tokens[idx]!r}")
        nodes.append(nd)
        idx += 1

    if idx >= len(tokens) or tokens[idx] != ")":
        raise SyntaxError("MISSING_CLOSE_PAREN")
    idx += 1

    validity_marks: list[KYValidity] = []
    while idx < len(tokens):
        vm = _decode_validity(tokens[idx])
        if vm is None:
            break
        validity_marks.append(vm)
        idx += 1

    audit_marks: list[KYAudit] = []
    while idx < len(tokens):
        am = _decode_audit(tokens[idx])
        if am is None:
            break
        audit_marks.append(am)
        idx += 1

    if idx != len(tokens) - 1:
        raise SyntaxError(f"UNEXPECTED_TRAILING_TOKENS::{tokens[idx:]!r}")
    gate = _decode_gate(tokens[idx])
    if gate is None:
        raise SyntaxError(f"EXPECTED_FINAL_GATE::{tokens[idx]!r}")

    return KYExpressionAST(
        nodes=tuple(nodes),
        flows=tuple(flows),
        validity_marks=tuple(validity_marks),
        audit_marks=tuple(audit_marks),
        declared_gate=gate,
    )


# ============================================================================
# 3. D2- PRE-COMMIT WARRANT, EVALUATOR & APPEND-ONLY SHA-256 VITNEKJEDE
# ============================================================================

@dataclass(frozen=True)
class PreCommitWarrant:
    warrant_id: str
    prev_witness_hash: str
    expression_ascii: str
    external_witness_id: str


@dataclass(frozen=True)
class KYV15EvalResult:
    syntax_valid: bool
    computed_gate: KYGate
    declared_gate: KYGate
    final_verdict: KYGate
    dry_contact_mv: int       # Alltid 0 mV DC inne i F
    simulated_latch_mv: int   # 5000 mV DC kun ved OPEN + verifisert warrant + W_ext
    reasons: tuple[str, ...]
    expression_ascii: str
    expression_unicode: str
    witness_hash: str


class KYV15Engine:
    """Konflikt-fri KY v1.5 evaluator med 0 mV luftgap og append-only SHA-256-kjede."""

    def __init__(self, tau_open: Fraction = Fraction(1, 4), tau_kill: Fraction = Fraction(3, 5)) -> None:
        self._tau_open = require_strict_fraction(tau_open, "tau_open")
        self._tau_kill = require_strict_fraction(tau_kill, "tau_kill")
        if self._tau_open < Fraction(0, 1) or self._tau_open >= self._tau_kill:
            raise ValueError("INVALID_PLASMA_THRESHOLDS")
        self._chain_head: str = "0" * 64
        self._ledger: list[dict[str, object]] = []

    @property
    def chain_head(self) -> str:
        return self._chain_head

    @property
    def ledger_len(self) -> int:
        return len(self._ledger)

    def issue_warrant(self, expression_ascii: str, external_witness_id: str) -> PreCommitWarrant:
        if not external_witness_id.strip():
            raise ValueError("EXTERNAL_WITNESS_REQUIRED_FOR_WARRANT")
        raw = f"{self._chain_head}|{expression_ascii}|{external_witness_id}".encode("utf-8")
        wid = hashlib.sha256(raw).hexdigest()[:24]
        return PreCommitWarrant(
            warrant_id=wid,
            prev_witness_hash=self._chain_head,
            expression_ascii=expression_ascii,
            external_witness_id=external_witness_id.strip(),
        )

    def evaluate(
        self,
        expr: str,
        *,
        prior_state_was_hold: bool = False,
        warrant: PreCommitWarrant | None = None,
        claims_hash_chain_is_physical_worm: bool = False,
    ) -> KYV15EvalResult:
        try:
            ast_node = parse_ky_v15(expr)
        except SyntaxError as exc:
            h = self._append_witness(expr, KYGate.KILL, 0, (f"SYNTAX_ERROR::{exc}",))
            return KYV15EvalResult(
                syntax_valid=False,
                computed_gate=KYGate.KILL,
                declared_gate=KYGate.KILL,
                final_verdict=KYGate.KILL,
                dry_contact_mv=0,
                simulated_latch_mv=0,
                reasons=(f"SYNTAX_ERROR::{exc}",),
                expression_ascii="",
                expression_unicode="",
                witness_hash=h,
            )

        reasons: list[str] = []
        vset = set(ast_node.validity_marks)
        aset = set(ast_node.audit_marks)
        nset = set(ast_node.nodes)
        computed = KYGate.OPEN

        # 0. WORM-demarkasjon (Registry A): hash-kjede alene er KILL som fysisk WORM
        if claims_hash_chain_is_physical_worm:
            reasons.append("KILL_HASH_CHAIN_ALONE_IS_NOT_PHYSICAL_WORM")
            computed = KYGate.KILL

        # 1. Overgangslover (null snarveier, null gjenoppliving, kun nabologikk + pre-D2 ~ sløyfe)
        for src, fl, dst in zip(ast_node.nodes, ast_node.flows, ast_node.nodes[1:]):
            if src is KYNode.KILLED:
                reasons.append("KILL_RESURRECTION_FROM_KILLED_FORBIDDEN")
                computed = KYGate.KILL
            elif dst is KYNode.KILLED:
                computed = KYGate.KILL
                reasons.append("EXPLICIT_TRANSITION_TO_KILLED")
            elif fl is KYFlow.HOLD_DRIFT:
                if src == dst and src in PRE_D2_NODES:
                    if computed is not KYGate.KILL:
                        computed = KYGate.HOLD
                else:
                    reasons.append(f"KILL_ILLEGAL_HOLD_DRIFT::{src.value}~{dst.value}")
                    computed = KYGate.KILL
            elif (src, dst) not in LEGAL_FORWARD_EDGES:
                reasons.append(f"KILL_ILLEGAL_SHORTCUT_OR_REVERSAL::{src.value}->{dst.value}")
                computed = KYGate.KILL

            # Spesifikk regel 4: VIABILITY -> AUTHORIZED krever ROX_OK, MASK_FROZEN og PLASMA_OPEN
            if src is KYNode.VIABILITY and dst is KYNode.AUTHORIZED:
                required = {KYValidity.ROX_OK, KYValidity.MASK_FROZEN, KYValidity.PLASMA_OPEN}
                if not required.issubset(vset):
                    missing = sorted(r.value for r in required - vset)
                    reasons.append(f"KILL_AUTHORIZED_MISSING_GUARDS::{','.join(missing)}")
                    computed = KYGate.KILL

            # Spesifikk regel 5: AUTHORIZED -> REALIZED krever `!`
            if src is KYNode.AUTHORIZED and dst is KYNode.REALIZED and KYAudit.COMMIT_BANG not in aset:
                reasons.append("KILL_REALIZED_WITHOUT_COMMIT_MARKER_BANG")
                computed = KYGate.KILL

            # Spesifikk regel 6: REALIZED -> WITNESSED krever `#`
            if src is KYNode.REALIZED and dst is KYNode.WITNESSED and KYAudit.WITNESS_HASH not in aset:
                reasons.append("KILL_WITNESSED_WITHOUT_AUDIT_HASH")
                computed = KYGate.KILL

        # 2. Validitetsmerker (ROX_FAIL / MASK_MUTATED / NOT_IN_K / PLASMA_KILL -> KILL; PLASMA_HOLD -> HOLD)
        hard_kills = vset & {
            KYValidity.ROX_FAIL,
            KYValidity.MASK_MUTATED,
            KYValidity.NOT_IN_K,
            KYValidity.PLASMA_KILL,
        }
        if hard_kills:
            reasons.append(f"KILL_VALIDITY_FAILURE::{','.join(sorted(k.value for k in hard_kills))}")
            computed = KYGate.KILL
        elif KYValidity.PLASMA_HOLD in vset and computed is not KYGate.KILL:
            computed = KYGate.HOLD
            reasons.append("HOLD_PLASMA_RISK_BAND")

        # 3. HOLD -> OPEN uten eksplisitt READMIT -> KILL (INVALID_DELAYED_OPEN)
        if prior_state_was_hold and ast_node.declared_gate is KYGate.OPEN and KYAudit.READMIT not in aset:
            reasons.append("KILL_INVALID_DELAYED_OPEN_MISSING_READMIT")
            computed = KYGate.KILL

        # 4. Portdom-samsvar (fail-closed ved uoverensstemmelse)
        if computed is not ast_node.declared_gate:
            reasons.append(f"KILL_GATE_MISMATCH::computed={computed.value},declared={ast_node.declared_gate.value}")
            final = KYGate.KILL
        else:
            final = computed

        # 5. D2- PreCommitWarrant + luftgap-suverenitet (0 mV DC uten gyldig warrant + W_ext)
        canonical_ascii = ast_node.to_ascii()
        canonical_uni = ast_node.to_unicode()
        simulated_mv = 0

        if final is KYGate.OPEN and (KYNode.REALIZED in nset or KYNode.WITNESSED in nset):
            if warrant is None:
                reasons.append("HOLD_DRY_CONTACT_0MV_AWAITING_WARRANT_AND_W_EXT")
                final = KYGate.HOLD
            elif (
                warrant.prev_witness_hash != self._chain_head
                or warrant.expression_ascii != canonical_ascii
                or not warrant.external_witness_id.strip()
            ):
                reasons.append("KILL_INVALID_PRECOMMIT_WARRANT")
                final = KYGate.KILL
            else:
                simulated_mv = 5000

        h = self._append_witness(canonical_ascii, final, simulated_mv, tuple(reasons))
        return KYV15EvalResult(
            syntax_valid=True,
            computed_gate=computed,
            declared_gate=ast_node.declared_gate,
            final_verdict=final,
            dry_contact_mv=0,
            simulated_latch_mv=simulated_mv,
            reasons=tuple(reasons),
            expression_ascii=canonical_ascii,
            expression_unicode=canonical_uni,
            witness_hash=h,
        )

    def _append_witness(self, expr_ascii: str, verdict: KYGate, latch_mv: int, reasons: tuple[str, ...]) -> str:
        payload = {
            "prev": self._chain_head,
            "seq": len(self._ledger) + 1,
            "expr": expr_ascii,
            "verdict": verdict.value,
            "simulated_latch_mv": latch_mv,
            "reasons": list(reasons),
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        self._ledger.append({**payload, "sha256": digest})
        self._chain_head = digest
        return digest
