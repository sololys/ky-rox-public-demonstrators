from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Sequence


Matrix = Sequence[Sequence[float]]


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


def gram_matrix(features: Matrix) -> list[list[float]]:
    rows = _validated(features, "features")
    return [
        [sum(a * b for a, b in zip(left, right)) for right in rows]
        for left in rows
    ]


def frobenius_norm(matrix: Matrix) -> float:
    rows = _validated(matrix, "matrix")
    return math.sqrt(sum(value * value for row in rows for value in row))


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
