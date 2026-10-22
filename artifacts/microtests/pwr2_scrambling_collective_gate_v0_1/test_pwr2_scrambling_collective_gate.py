from __future__ import annotations

import unittest

from pwr2_scrambling_collective_gate import (
    EPISTEMIC_BOUNDARY,
    GATE_HOLD,
    GATE_KILL,
    GATE_OPEN,
    build_circulant_first_row,
    compute_circulant_eigenvalues,
    compute_gamma_squared_spectrum,
    evaluate_spin_scrambling_consequence_gate,
)


class TestPWR2ScramblingCollectiveGate(unittest.TestCase):
    def test_01_epistemic_boundary(self) -> None:
        self.assertEqual(EPISTEMIC_BOUNDARY, "INSPIRED_BY != IMPLEMENTS != PROVES")

    def test_02_collective_symmetric_state_k0_open(self) -> None:
        v = evaluate_spin_scrambling_consequence_gate(n=32, k_flips=0, geometry="PWR2", protocol="alternating")
        self.assertEqual(v.gate_state, GATE_OPEN)
        self.assertEqual(v.voltage_vdc, 5.00)
        self.assertAlmostEqual(v.qfi_density_bound, 32.0)
        self.assertGreater(v.spectral_gap_delta, 0.0)
        self.assertAlmostEqual(v.max_gamma_squared, 0.0)

    def test_03_pwr2_unique_positive_lambda_n_over_2_scrambling(self) -> None:
        n = 32
        eigs_pwr2 = compute_circulant_eigenvalues(build_circulant_first_row(n, "PWR2"))
        eigs_pl = compute_circulant_eigenvalues(build_circulant_first_row(n, "PL", alpha=1.0))
        eigs_a2a = compute_circulant_eigenvalues(build_circulant_first_row(n, "A2A"))
        eigs_nn = compute_circulant_eigenvalues(build_circulant_first_row(n, "NN"))

        self.assertGreater(eigs_pwr2[n // 2], 0.0)
        self.assertLess(eigs_pl[n // 2], 0.0)
        self.assertLess(eigs_a2a[n // 2], 0.0)
        self.assertLess(eigs_nn[n // 2], 0.0)

        v_pwr2 = evaluate_spin_scrambling_consequence_gate(n=32, k_flips=16, geometry="PWR2", protocol="alternating")
        self.assertEqual(v_pwr2.gate_state, GATE_KILL)
        self.assertEqual(v_pwr2.voltage_vdc, 0.00)
        self.assertGreater(v_pwr2.max_gamma_squared, 0.0)
        self.assertGreater(v_pwr2.effective_lyapunov_rate, 0.0)

    def test_04_power_law_protocol_asymmetry_alternating_vs_one_sided(self) -> None:
        v_pl_alt = evaluate_spin_scrambling_consequence_gate(n=32, k_flips=16, geometry="PL", protocol="alternating")
        v_pl_one = evaluate_spin_scrambling_consequence_gate(n=32, k_flips=16, geometry="PL", protocol="one_sided")

        self.assertEqual(v_pl_alt.gate_state, GATE_HOLD)
        self.assertLessEqual(v_pl_alt.max_gamma_squared, 0.0)

        self.assertEqual(v_pl_one.gate_state, GATE_KILL)
        self.assertGreater(v_pl_one.max_gamma_squared, 0.0)
        self.assertGreater(v_pl_one.lambda_1, 0.0)

    def test_05_all_to_all_integrable_never_scrambles(self) -> None:
        n = 32
        eigs_a2a = compute_circulant_eigenvalues(build_circulant_first_row(n, "A2A"))
        for k_mode in (0, 1, n // 2):
            gamma_sq = compute_gamma_squared_spectrum(eigs_a2a, k_mode)
            self.assertLessEqual(max(gamma_sq), 0.0)

    def test_06_critical_sqrt_n_scaling_hold_vs_kill(self) -> None:
        v_sub = evaluate_spin_scrambling_consequence_gate(n=64, k_flips=4, geometry="PWR2", protocol="alternating")
        v_sup = evaluate_spin_scrambling_consequence_gate(n=64, k_flips=12, geometry="PWR2", protocol="alternating")

        self.assertAlmostEqual(v_sub.critical_flips_k_star, 8.0)
        self.assertAlmostEqual(v_sub.critical_ratio_k_star_over_n, 0.125)
        self.assertEqual(v_sub.gate_state, GATE_HOLD)
        self.assertEqual(v_sup.gate_state, GATE_KILL)


if __name__ == "__main__":
    unittest.main()
