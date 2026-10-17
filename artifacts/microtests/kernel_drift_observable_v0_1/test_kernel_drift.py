from __future__ import annotations

import json
import math
from pathlib import Path
import unittest

from kernel_drift import (
    KernelDriftGate,
    compute_gram,
    evaluate,
    frobenius_diff,
    normalized_kernel_drift,
)


FIXTURE = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))


class KernelDriftMicrotest(unittest.TestCase):
    def test_01_null_point_identity(self) -> None:
        """Invariant 1: X(t) = X(0) => Delta_state = 0 and Delta_G = 0."""
        reference = FIXTURE["reference_features"]
        gate = KernelDriftGate(reference, tau_g=1e-9)
        rec = gate.evaluate(reference, evidence_id="EV-NULL-01")
        self.assertEqual(rec.state_drift, 0.0)
        self.assertEqual(rec.kernel_drift, 0.0)
        self.assertEqual(rec.gate_status, "OPEN")
        self.assertEqual(normalized_kernel_drift(reference, reference), 0.0)

    def test_02_orthogonal_invariance_blindness_test(self) -> None:
        """Invariant 2: X(t) = X(0) U^T with U^T U = I => Delta_state > 0 and Delta_G <= eps."""
        X0 = [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [1.0, 1.0, 0.0]]
        theta = math.pi / 3.0  # 60-degree rigid rotation in the (x, y) plane
        c, s = math.cos(theta), math.sin(theta)
        X_rot = [[x * c - y * s, x * s + y * c, z] for x, y, z in X0]

        gate = KernelDriftGate(X0, tau_g=1e-9)
        rec = gate.evaluate(X_rot, evidence_id="EV-ROT-01")
        self.assertGreater(rec.state_drift, 1.0)
        self.assertLessEqual(rec.kernel_drift, 1e-12)
        self.assertEqual(rec.gate_status, "OPEN")

    def test_03_relational_shear_detection(self) -> None:
        """Invariant 3: Internal shear deformation breaks orthogonality and triggers KILL."""
        reference = FIXTURE["reference_features"]
        observed = FIXTURE["observed_features"]
        gate = KernelDriftGate(reference, tau_g=1e-9)
        rec = gate.evaluate(observed, evidence_id="EV-SHEAR-01")
        self.assertGreater(rec.kernel_drift, 1e-9)
        self.assertEqual(rec.gate_status, "KILL")

    def test_04_scaling_and_spectral_breach(self) -> None:
        """Invariant 4: X(t) = alpha X(0) with alpha != 1 => Delta_G = |alpha^2 - 1| ||G(0)||_F > tau_G -> KILL."""
        X0 = FIXTURE["reference_features"]
        alpha = 1.25
        X_scaled = [[alpha * val for val in row] for row in X0]
        G0 = compute_gram(X0)
        zero_mat = [[0.0 for _ in row] for row in G0]
        g0_norm = frobenius_diff(G0, zero_mat)

        gate = KernelDriftGate(X0, tau_g=1e-9)
        rec = gate.evaluate(X_scaled, evidence_id="EV-SCALE-01")
        expected_dg = abs(alpha * alpha - 1.0) * g0_norm
        self.assertAlmostEqual(rec.kernel_drift, expected_dg, places=10)
        self.assertEqual(rec.gate_status, "KILL")

    def test_05_positive_semidefinite_psd_guarantee_and_shape_guard(self) -> None:
        """Invariant 5: Non-PSD synthetic Gram matrix (negative eigenvalue/minor) or shape mismatch -> KILL."""
        X0 = [[1.0, 0.0], [0.0, 1.0]]
        gate = KernelDriftGate(X0, tau_g=1.0)
        # Inject synthetic impossible Gram matrix with negative diagonal / violated Cauchy-Schwarz
        non_psd_gram = [[1.0, 2.0], [2.0, 1.0]]  # det = 1 - 4 = -3 < 0
        rec_psd = gate.evaluate(X0, evidence_id="EV-PSD-01", injected_gram=non_psd_gram)
        self.assertEqual(rec_psd.gate_status, "KILL")

        # Shape mismatch also triggers KILL
        bad_shape = evaluate([[1.0, 0.0]], [[1.0]])
        self.assertEqual(bad_shape.status, "KILL")

    def test_06_witness_enforcement_and_append_only_ledger(self) -> None:
        """Invariant 6: Missing evidence -> HOLD, and ledger is strictly append-only."""
        X0 = FIXTURE["reference_features"]
        gate = KernelDriftGate(X0, tau_g=1e-9)
        r1 = gate.evaluate(X0, evidence_id="   ")
        self.assertEqual(r1.gate_status, "HOLD")
        self.assertEqual(len(gate.ledger), 1)

        r2 = gate.evaluate(X0, evidence_id="EV-VALID-02")
        self.assertEqual(r2.gate_status, "OPEN")
        self.assertEqual(len(gate.ledger), 2)

        result = evaluate(FIXTURE["reference_features"], FIXTURE["observed_features"])
        self.assertEqual(result.measurement_status, "OPEN")
        self.assertEqual(result.claim_status, "HOLD")
        self.assertEqual(result.physical_authority, "NONE")


if __name__ == "__main__":
    unittest.main()
