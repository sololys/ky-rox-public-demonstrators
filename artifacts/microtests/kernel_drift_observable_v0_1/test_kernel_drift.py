from __future__ import annotations

import json
from pathlib import Path
import unittest

from kernel_drift import evaluate, gram_matrix, normalized_kernel_drift


FIXTURE = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))


class KernelDriftMicrotest(unittest.TestCase):
    def test_01_gram_matrix_is_deterministic(self) -> None:
        self.assertEqual(gram_matrix([[1, 0], [0, 1]]), [[1.0, 0.0], [0.0, 1.0]])

    def test_02_identical_windows_have_zero_drift(self) -> None:
        reference = FIXTURE["reference_features"]
        self.assertEqual(normalized_kernel_drift(reference, reference), 0.0)

    def test_03_relational_deformation_is_visible(self) -> None:
        self.assertGreater(
            normalized_kernel_drift(
                FIXTURE["reference_features"], FIXTURE["observed_features"]
            ),
            0.0,
        )

    def test_04_valid_measurement_keeps_claim_on_hold(self) -> None:
        result = evaluate(FIXTURE["reference_features"], FIXTURE["observed_features"])
        self.assertEqual(result.measurement_status, "OPEN")
        self.assertEqual(result.claim_status, "HOLD")
        self.assertEqual(result.status, "HOLD")
        self.assertEqual(result.physical_authority, "NONE")

    def test_05_invalid_shape_is_kill(self) -> None:
        result = evaluate([[1.0, 0.0]], [[1.0]])
        self.assertEqual(result.status, "KILL")
        self.assertIsNone(result.kernel_drift)

    def test_06_repeated_runs_match(self) -> None:
        first = evaluate(FIXTURE["reference_features"], FIXTURE["observed_features"])
        second = evaluate(FIXTURE["reference_features"], FIXTURE["observed_features"])
        self.assertEqual(first.to_dict(), second.to_dict())


if __name__ == "__main__":
    unittest.main()
