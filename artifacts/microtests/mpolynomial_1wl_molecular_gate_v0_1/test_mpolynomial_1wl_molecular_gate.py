from __future__ import annotations

import unittest

from mpolynomial_1wl_molecular_gate import (
    EPISTEMIC_BOUNDARY,
    GATE_HOLD,
    GATE_KILL,
    GATE_OPEN,
    analyze_mpolynomial,
    build_canonical_molecular_library,
    compute_1wl_signature,
    evaluate_molecular_consequence_gate,
)


class TestMPolynomial1WLMolecularGate(unittest.TestCase):
    def setUp(self) -> None:
        self.lib = build_canonical_molecular_library()

    def test_epistemic_boundary_constant(self) -> None:
        self.assertEqual(EPISTEMIC_BOUNDARY, "INSPIRED_BY != IMPLEMENTS != PROVES")

    def test_butane_vs_isobutane_exact_mpolynomial_separation(self) -> None:
        butane = self.lib["n_butane"]
        isobutane = self.lib["isobutane"]
        mp_b = analyze_mpolynomial(butane)
        mp_iso = analyze_mpolynomial(isobutane)
        self.assertEqual(mp_b.symbolic_polynomial, "2*x^1*y^2 + x^2*y^2")
        self.assertAlmostEqual(mp_b.first_zagreb_m1, 10.0)
        self.assertAlmostEqual(mp_b.second_zagreb_m2, 8.0)
        self.assertEqual(mp_iso.symbolic_polynomial, "3*x^1*y^3")
        self.assertAlmostEqual(mp_iso.first_zagreb_m1, 12.0)
        self.assertAlmostEqual(mp_iso.second_zagreb_m2, 9.0)
        self.assertEqual(evaluate_molecular_consequence_gate(butane).gate_state, GATE_OPEN)
        self.assertEqual(evaluate_molecular_consequence_gate(isobutane).gate_state, GATE_OPEN)

    def test_decalin_vs_bicyclopentyl_1wl_bottleneck_and_hold_gate(self) -> None:
        decalin = self.lib["decalin"]
        bicyclopentyl = self.lib["bicyclopentyl"]
        self.assertEqual(compute_1wl_signature(decalin, 5), compute_1wl_signature(bicyclopentyl, 5))
        mp_dec = analyze_mpolynomial(decalin)
        mp_bic = analyze_mpolynomial(bicyclopentyl)
        self.assertEqual(mp_dec.symbolic_polynomial, "6*x^2*y^2 + 4*x^2*y^3 + x^3*y^3")
        self.assertEqual(mp_dec.symbolic_polynomial, mp_bic.symbolic_polynomial)
        verdict_hold = evaluate_molecular_consequence_gate(
            decalin, reference_1wl_peer=bicyclopentyl, require_higher_order_witness_on_1wl_collision=True
        )
        self.assertEqual(verdict_hold.gate_state, GATE_HOLD)
        self.assertEqual(verdict_hold.voltage_vdc, 0.00)
        self.assertEqual(verdict_hold.ring_motifs_c3_to_c6[6], 2)

    def test_benzene_c6_vs_disjoint_2x_c3_ghost_fragment_kill(self) -> None:
        c6 = self.lib["benzene_c6"]
        two_c3 = self.lib["disjoint_2x_c3"]
        self.assertEqual(compute_1wl_signature(c6), compute_1wl_signature(two_c3))
        self.assertEqual(analyze_mpolynomial(c6).symbolic_polynomial, analyze_mpolynomial(two_c3).symbolic_polynomial)
        self.assertEqual(evaluate_molecular_consequence_gate(c6).gate_state, GATE_OPEN)
        v_2c3 = evaluate_molecular_consequence_gate(two_c3)
        self.assertEqual(v_2c3.gate_state, GATE_KILL)
        self.assertEqual(v_2c3.connected_components, 2)

    def test_pentavalent_texas_carbon_gnn_hallucination_killed(self) -> None:
        texas_c = self.lib["texas_carbon_hallucination"]
        verdict = evaluate_molecular_consequence_gate(texas_c)
        self.assertTrue(verdict.soft_gnn_would_pass)
        self.assertEqual(verdict.gate_state, GATE_KILL)
        self.assertEqual(verdict.voltage_vdc, 0.00)

    def test_femos_cofactor_fe7mos9c_interstitial_carbide_mpolynomial(self) -> None:
        femos = self.lib["femos_cofactor_fe7mos9c"]
        verdict = evaluate_molecular_consequence_gate(femos)
        mp = verdict.mpolynomial
        self.assertEqual(mp.symbolic_polynomial, "6*x^2*y^4 + 6*x^3*y^3 + 12*x^3*y^4 + 6*x^4*y^6")
        self.assertAlmostEqual(mp.first_zagreb_m1, 216.0)
        self.assertAlmostEqual(mp.second_zagreb_m2, 390.0)
        self.assertEqual(verdict.gate_state, GATE_OPEN)
        self.assertEqual(verdict.voltage_vdc, 5.00)


if __name__ == "__main__":
    unittest.main()
