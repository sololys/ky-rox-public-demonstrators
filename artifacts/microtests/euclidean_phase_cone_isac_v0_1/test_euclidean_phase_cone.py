from __future__ import annotations

import json
import math
from pathlib import Path
import unittest

from euclidean_phase_cone import evaluate_phase_difference


FIXTURE = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))


class EuclideanPhaseConeMicrotest(unittest.TestCase):
    def test_01_boresight_zero_phase_is_zero_degrees(self) -> None:
        res = evaluate_phase_difference(0.0, 0.5)
        self.assertEqual(res.measurement_status, "OPEN")
        self.assertTrue(res.is_euclidean_admissible)
        self.assertEqual(res.angle_deg_if_real, 0.0)

    def test_02_half_pi_phase_is_thirty_degrees(self) -> None:
        res = evaluate_phase_difference(math.pi / 2.0, 0.5)
        self.assertEqual(res.measurement_status, "OPEN")
        self.assertAlmostEqual(res.angle_deg_if_real or 0.0, 30.0, places=7)

    def test_03_boundary_pi_phase_is_ninety_degrees(self) -> None:
        res = evaluate_phase_difference(math.pi, 0.5)
        self.assertEqual(res.measurement_status, "OPEN")
        self.assertAlmostEqual(res.angle_deg_if_real or 0.0, 90.0, places=7)

    def test_04_super_euclidean_phase_injection_is_kill(self) -> None:
        res = evaluate_phase_difference(float(FIXTURE["synthetic_ghost_phase_diff_rad"]), 0.5)
        self.assertEqual(res.status, "KILL")
        self.assertEqual(res.measurement_status, "KILL")
        self.assertFalse(res.is_euclidean_admissible)
        self.assertGreater(res.imaginary_cos_magnitude_if_ghost, 0.0)

    def test_05_invalid_spacing_or_nan_is_kill(self) -> None:
        bad_spacing = evaluate_phase_difference(1.0, 0.0)
        self.assertEqual(bad_spacing.status, "KILL")
        bad_nan = evaluate_phase_difference(float("nan"), 0.5)
        self.assertEqual(bad_nan.status, "KILL")

    def test_06_authority_remains_none_on_valid_measurement(self) -> None:
        res = evaluate_phase_difference(float(FIXTURE["physical_phase_diff_rad"]), 0.5)
        self.assertEqual(res.claim_status, "HOLD")
        self.assertEqual(res.physical_authority, "NONE")
        self.assertEqual(res.operational_authority, "NONE")


if __name__ == "__main__":
    unittest.main()
