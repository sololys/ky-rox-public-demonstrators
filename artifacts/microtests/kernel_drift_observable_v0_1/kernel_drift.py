from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple


Matrix = Sequence[Sequence[float]]


@dataclass(frozen=True)
class WitnessRecord:
    step_id: int
    evidence_id: str
    state_drift: float
    kernel_drift: float
    gate_status: str  # "OPEN" | "HOLD" | "KILL"


def _validated(matrix: Matrix, name: str) -> list[list[float]]:
    if not isinstance(matrix, Sequence) or isinstance(matrix, (str, bytes)) or not matrix:
        raise ValueError(f"{name}_must_be_nonempty_matrix")
    width: int | None = None
    result: list[list[float]] = []
    for row in matrix:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)) or not row:
            raise ValueError(f"{name}_contains_invalid_row")
        values = [float(value) for value in row]
        if any(not math.isfinite(value) for value in values):
            raise ValueError(f"{name}_contains_nonfinite_value")
        width = len(values) if width is None else width
        if len(values) != width:
            raise ValueError(f"{name}_is_ragged")
        result.append(values)
    return result


def compute_gram(X: Matrix) -> list[list[float]]:
    """Computes the relational Gram matrix G(t) = X(t) X(t)^T for N row vectors in R^d."""
    rows = _validated(X, "X")
    n = len(rows)
    d = len(rows[0])
    return [
        [sum(rows[i][k] * rows[j][k] for k in range(d)) for j in range(n)]
        for i in range(n)
    ]


def gram_matrix(features: Matrix) -> list[list[float]]:
    return compute_gram(features)


def frobenius_norm(matrix: Matrix) -> float:
    rows = _validated(matrix, "matrix")
    return math.sqrt(sum(value * value for row in rows for value in row))


def frobenius_diff(A: Matrix, B: Matrix) -> float:
    """Computes the exact Frobenius norm ||A - B||_F."""
    rows_a = _validated(A, "A")
    rows_b = _validated(B, "B")
    if len(rows_a) != len(rows_b) or any(len(ra) != len(rb) for ra, rb in zip(rows_a, rows_b)):
        raise ValueError("matrix_shape_mismatch")
    acc = 0.0
    for row_a, row_b in zip(rows_a, rows_b):
        for val_a, val_b in zip(row_a, row_b):
            diff = val_a - val_b
            acc += diff * diff
    return math.sqrt(acc)


def is_positive_semidefinite_gram(G: Matrix, eps: float = 1e-12) -> bool:
    """
    Verifies symmetric Positive Semidefinite (PSD) structure for a Gram matrix G:
      1. Symmetry: |G_ij - G_ji| <= eps
      2. Non-negative diagonal: G_ii >= -eps
      3. Cauchy-Schwarz principal 2x2 minors: G_ii * G_jj - G_ij^2 >= -eps
    """
    rows = _validated(G, "G")
    n = len(rows)
    if any(len(r) != n for r in rows):
        return False
    for i in range(n):
        if rows[i][i] < -eps:
            return False
        for j in range(i + 1, n):
            if abs(rows[i][j] - rows[j][i]) > eps:
                return False
            if rows[i][i] * rows[j][j] - rows[i][j] * rows[i][j] < -eps:
                return False
    return True


def _difference(left: Matrix, right: Matrix) -> list[list[float]]:
    a = _validated(left, "left")
    b = _validated(right, "right")
    if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
        raise ValueError("matrix_shape_mismatch")
    return [[x - y for x, y in zip(row_a, row_b)] for row_a, row_b in zip(a, b)]


def normalized_kernel_drift(reference: Matrix, observed: Matrix) -> float:
    reference_rows = _validated(reference, "reference")
    observed_rows = _validated(observed, "observed")
    if len(reference_rows) != len(observed_rows) or len(reference_rows[0]) != len(observed_rows[0]):
        raise ValueError("feature_shape_mismatch")
    reference_kernel = gram_matrix(reference_rows)
    observed_kernel = gram_matrix(observed_rows)
    denominator = frobenius_norm(reference_kernel)
    if denominator == 0.0:
        raise ValueError("zero_reference_kernel")
    return frobenius_norm(_difference(observed_kernel, reference_kernel)) / denominator


def normalized_raw_drift(reference: Matrix, observed: Matrix) -> float:
    reference_rows = _validated(reference, "reference")
    observed_rows = _validated(observed, "observed")
    difference = _difference(observed_rows, reference_rows)
    denominator = frobenius_norm(reference_rows)
    if denominator == 0.0:
        raise ValueError("zero_reference_features")
    return frobenius_norm(difference) / denominator


class KernelDriftGate:
    """
    Deterministic consequence gate Omega_kernel(X(t), e, tau_G):
      - OPEN if e != empty and Delta_G(t) <= tau_G
      - HOLD if e == empty and Delta_G(t) <= tau_G
      - KILL if Delta_G(t) > tau_G or shape mismatch or non-PSD Gram injection
    """

    def __init__(self, X_ref: Matrix, tau_g: float = 1e-9) -> None:
        rows = _validated(X_ref, "X_ref")
        self._X0: List[List[float]] = [list(row) for row in rows]
        self._G0: List[List[float]] = compute_gram(self._X0)
        self._tau_g: float = float(tau_g)
        self._ledger: List[WitnessRecord] = []

    @property
    def ledger(self) -> Tuple[WitnessRecord, ...]:
        return tuple(self._ledger)

    def evaluate(
        self,
        X_t: Matrix,
        evidence_id: Optional[str],
        injected_gram: Optional[Matrix] = None,
    ) -> WitnessRecord:
        step = len(self._ledger)

        try:
            rows_t = _validated(X_t, "X_t")
        except (TypeError, ValueError, OverflowError):
            rec = WitnessRecord(step, str(evidence_id or "").strip(), math.inf, math.inf, "KILL")
            self._ledger.append(rec)
            return rec

        if len(rows_t) != len(self._X0) or any(len(r) != len(self._X0[0]) for r in rows_t):
            rec = WitnessRecord(step, str(evidence_id or "").strip(), math.inf, math.inf, "KILL")
            self._ledger.append(rec)
            return rec

        d_state = frobenius_diff(rows_t, self._X0)
        G_t = _validated(injected_gram, "injected_gram") if injected_gram is not None else compute_gram(rows_t)

        if not is_positive_semidefinite_gram(G_t):
            rec = WitnessRecord(step, str(evidence_id or "").strip(), d_state, math.inf, "KILL")
            self._ledger.append(rec)
            return rec

        d_kernel = frobenius_diff(G_t, self._G0)

        if d_kernel > self._tau_g:
            status = "KILL"
        elif not evidence_id or not evidence_id.strip():
            status = "HOLD"
        else:
            status = "OPEN"

        rec = WitnessRecord(
            step_id=step,
            evidence_id=evidence_id.strip() if evidence_id else "",
            state_drift=d_state,
            kernel_drift=d_kernel,
            gate_status=status,
        )
        self._ledger.append(rec)
        return rec


@dataclass(frozen=True)
class Measurement:
    status: str
    measurement_status: str
    claim_status: str
    reason: str
    kernel_drift: float | None
    raw_state_drift: float | None
    physical_authority: str = "NONE"
    operational_authority: str = "NONE"
    claim: str = "Synthetic diagnostic measurement only"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate(reference: Matrix, observed: Matrix) -> Measurement:
    try:
        kernel = normalized_kernel_drift(reference, observed)
        raw = normalized_raw_drift(reference, observed)
    except (TypeError, ValueError, OverflowError) as exc:
        return Measurement(
            status="KILL",
            measurement_status="KILL",
            claim_status="HOLD",
            reason=str(exc),
            kernel_drift=None,
            raw_state_drift=None,
        )
    return Measurement(
        status="HOLD",
        measurement_status="OPEN",
        claim_status="HOLD",
        reason="BENCHMARK_ADVANTAGE_NOT_ESTABLISHED_BY_SYNTHETIC_FIXTURE",
        kernel_drift=round(kernel, 12),
        raw_state_drift=round(raw, 12),
    )


def main() -> None:
    fixture = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))
    result = evaluate(fixture["reference_features"], fixture["observed_features"])
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
