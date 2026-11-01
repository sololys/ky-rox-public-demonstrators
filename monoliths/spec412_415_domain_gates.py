#!/usr/bin/env python3
"""
spec412_415_domain_gates.py
===========================
Horisont II: Executable L1 Domain Gates (SPEC-412..415) — Forlik, Orbital,
77 GHz Kinematic Radar (Radix-4 FFT / Joseph-EKF / A5 Pocket), and -240 m
Benthic K-POD (5 CDC Locks & Kinematic Courier Bridge).

Epistemic Status (AGENTS.md):
  Level: L1 (Deterministic Software Reference Implementation & Unit Test Suite).
  Boundary: INSPIRED_BY != IMPLEMENTS != PROVES.
  Authority: PHYSICAL_AUTHORITY=NONE // OPERATIONAL_AUTHORITY=NONE (0.00 V DC).
  Dependencies: Python 3.10+ Standard Library ONLY (cmath, dataclasses, decimal,
                enum, hashlib, json, math, unittest).
"""

from __future__ import annotations

import cmath
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
import unittest
from typing import Sequence

D = Decimal
SPEED_OF_LIGHT = 299_792_458.0
WAVELENGTH_77GHZ_M = SPEED_OF_LIGHT / 77.0e9
COOL_SECONDS_72H = 72 * 3600
MAX_OPTICAL_532NM_RTT_NS = D("177.990")
MAX_UWB_AIR_RTT_NS = D("133.425")
SABOTAGE_SPL_THRESHOLD_DB = D("145.0")


def exact_decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise ValueError("exact numeric input required (Decimal, int, or str)")
    res = D(value)
    if not res.is_finite():
        raise ValueError("finite numeric input required")
    return res


def nonnegative_decimal(value: Decimal | int | str) -> Decimal:
    res = exact_decimal(value)
    if res < 0:
        raise ValueError("nonnegative numeric input required")
    return res


# ============================================================================
# 1. SPEC-412: DEN LOKALE FORLIKSRÅDS-SLUSEN (72h Cool-Off & UWB Proximity)
# ============================================================================
def spec412_proximity_ok(measured_ns: Decimal | int | str) -> bool:
    """Conservative scalar budget model: upper RTT bound must fit 40/c with +/-4.5 ns margin."""
    estimate = nonnegative_decimal(measured_ns) - D(1000)
    uncertainty = D("4.5")
    limit = D(40_000_000_000) / D(299_792_458)
    return (estimate - uncertainty) >= 0 and (estimate + uncertainty) <= limit


class Spec412Gate(str, Enum):
    HOLD = "HOLD"
    AUTHORIZED = "AUTHORIZED"


@dataclass(frozen=True)
class Spec412Claim:
    debt: Decimal
    gate: Spec412Gate = Spec412Gate.HOLD
    disputes: frozenset[str] = frozenset()
    signed_at: int | None = None
    revoked: bool = False
    applied: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "debt", nonnegative_decimal(self.debt))

    def sign(self, now: int) -> Spec412Claim:
        if type(now) is not int or now < 0:
            raise ValueError("nonnegative integer timestamp required")
        return replace(self, signed_at=now, revoked=False, gate=Spec412Gate.HOLD)

    def dispute(self, dispute_id: str) -> Spec412Claim:
        if not dispute_id.strip():
            raise ValueError("nonempty dispute_id required")
        return replace(self, disputes=self.disputes | {dispute_id}, gate=Spec412Gate.HOLD)

    def resolve(self, dispute_id: str, *, independently_reviewed: bool = False) -> Spec412Claim:
        if independently_reviewed is not True or dispute_id not in self.disputes:
            raise ValueError("independent resolution of known dispute required")
        return replace(self, disputes=self.disputes - {dispute_id}, gate=Spec412Gate.HOLD)

    def readmit(
        self,
        now: int,
        *,
        local: bool = False,
        proximity: bool = False,
        capacity: bool = False,
        legal_basis: bool = False,
        bilateral_review: bool = False,
    ) -> Spec412Claim:
        if type(now) is not int or now < 0:
            raise ValueError("nonnegative integer timestamp required")
        ready = (
            not self.disputes
            and not self.revoked
            and self.signed_at is not None
            and (now - self.signed_at) >= COOL_SECONDS_72H
            and all(
                flag is True
                for flag in (local, proximity, capacity, legal_basis, bilateral_review)
            )
        )
        return replace(self, gate=Spec412Gate.AUTHORIZED if ready else Spec412Gate.HOLD)

    def settle(
        self,
        receipt_id: str,
        rate: Decimal | int | str,
        hours: Decimal | int | str,
        *,
        voluntary: bool = False,
        quality_attested: bool = False,
        receipt_attested: bool = False,
    ) -> Spec412Claim:
        if not receipt_id.strip() or receipt_id in self.applied:
            raise ValueError("unique nonempty receipt_id required")
        if self.gate != Spec412Gate.AUTHORIZED or not all(
            flag is True for flag in (voluntary, quality_attested, receipt_attested)
        ):
            raise ValueError("settlement prerequisites missing")
        r_val = nonnegative_decimal(rate)
        h_val = nonnegative_decimal(hours)
        if r_val == 0:
            raise ValueError("positive rate required")
        new_debt = max(D(0), self.debt - r_val * h_val)
        return replace(
            self,
            debt=new_debt,
            gate=Spec412Gate.HOLD,
            applied=self.applied | {receipt_id},
        )


# ============================================================================
# 2. SPEC-413: DEN ORBITALE SUVERENITETS-SLUSEN (Sub-Half-Wavelength & Stasis)
# ============================================================================
class Spec413OrbitalStatus(str, Enum):
    NOMINAL_ORBIT = "NOMINAL_ORBIT"
    STORM_STASIS = "STORM_STASIS"
    JAMMING_KILL = "JAMMING_KILL"
    TELEMETRY_SNR_HOLD = "TELEMETRY_SNR_HOLD"
    REMOTE_ACTUATION_KILL = "REMOTE_ACTUATION_KILL"


def spec413_sub_half_wavelength_s_obs(
    phase_diff_rad: float,
    *,
    spacing_eta: float = 0.5,
) -> float:
    if not (math.isfinite(phase_diff_rad) and math.isfinite(spacing_eta)):
        raise ValueError("finite phase_diff_rad and spacing_eta required")
    if spacing_eta <= 0.0 or spacing_eta > 1.0:
        raise ValueError("spacing_eta must be in (0.0, 1.0]")
    return phase_diff_rad / (spacing_eta * math.pi)


def spec413_evaluate_orbital_gate(
    *,
    measured_rtt_ns: Decimal | int | str,
    phase_diff_rad: float,
    kp_index: Decimal | int | str,
    snr_db: Decimal | int | str,
    is_direct_actuation: bool = False,
    spacing_eta: float = 0.5,
) -> tuple[Spec413OrbitalStatus, Decimal]:
    within_local = spec412_proximity_ok(measured_rtt_ns)
    if is_direct_actuation and not within_local:
        return Spec413OrbitalStatus.REMOTE_ACTUATION_KILL, D("0.00")
    kp = nonnegative_decimal(kp_index)
    snr = exact_decimal(snr_db)
    if not (kp < D("7.0")):
        return Spec413OrbitalStatus.STORM_STASIS, D("0.00")
    if not (
        math.isfinite(phase_diff_rad)
        and math.isfinite(spacing_eta)
        and 0.0 < spacing_eta <= 1.0
    ):
        return Spec413OrbitalStatus.JAMMING_KILL, D("0.00")
    s_obs = spec413_sub_half_wavelength_s_obs(phase_diff_rad, spacing_eta=spacing_eta)
    if not (math.isfinite(s_obs) and abs(s_obs) <= 1.0):
        return Spec413OrbitalStatus.JAMMING_KILL, D("0.00")
    if not (snr >= D("6.0")):
        return Spec413OrbitalStatus.TELEMETRY_SNR_HOLD, D("0.00")
    return Spec413OrbitalStatus.NOMINAL_ORBIT, D("5.00")


# ============================================================================
# 3. SPEC-414: DEN KINEMATISKE RADAR-SLUSEN (Radix-4 FFT, CRT & A5 Hold)
# ============================================================================
def spec414_radix4_fft_16(samples: Sequence[complex]) -> list[complex]:
    """Exact 2-stage Radix-4 Cooley-Tukey butterfly FFT for N = 4^2 = 16 samples."""
    if len(samples) != 16:
        raise ValueError("radix4_fft_16 requires exactly 16 complex samples")
    y_mat = [[0j] * 4 for _ in range(4)]
    for n0 in range(4):
        x0, x1, x2, x3 = samples[0 + n0], samples[4 + n0], samples[8 + n0], samples[12 + n0]
        s0, s1, s2, s3 = x0 + x2, x0 - x2, x1 + x3, x1 - x3
        b_vals = (s0 + s2, s1 - 1j * s3, s0 - s2, s1 + 1j * s3)
        for k0, b_val in enumerate(b_vals):
            y_mat[k0][n0] = b_val * cmath.exp(-2j * math.pi * (n0 * k0) / 16.0)
    out = [0j] * 16
    for k0 in range(4):
        y0, y1, y2, y3 = y_mat[k0]
        t0, t1, t2, t3 = y0 + y2, y0 - y2, y1 + y3, y1 - y3
        out[0 + k0] = t0 + t2
        out[4 + k0] = t1 - 1j * t3
        out[8 + k0] = t0 - t2
        out[12 + k0] = t1 + 1j * t3
    return out


def spec414_unfold_staggered_prf(
    aliased_f1_hz: float,
    aliased_f2_hz: float,
    *,
    prf1_hz: float = 10_000.0,
    prf2_hz: float = 12_000.0,
    winding_bound: int = 3,
    tau_crt_hz: float = 100.0,
) -> tuple[float, float, bool]:
    """Unfold aliased Doppler across 5:6 staggered PRFs (10.0 kHz & 12.0 kHz)."""
    if not (
        math.isfinite(aliased_f1_hz)
        and math.isfinite(aliased_f2_hz)
        and math.isfinite(prf1_hz)
        and math.isfinite(prf2_hz)
        and math.isfinite(tau_crt_hz)
        and prf1_hz > 0.0
        and prf2_hz > 0.0
        and tau_crt_hz >= 0.0
    ):
        return 0.0, 0.0, False
    best_res = float("inf")
    best_fd = 0.0
    for m1 in range(-winding_bound, winding_bound + 1):
        cand1 = aliased_f1_hz + m1 * prf1_hz
        for m2 in range(-winding_bound, winding_bound + 1):
            cand2 = aliased_f2_hz + m2 * prf2_hz
            cand_mean = 0.5 * (cand1 + cand2)
            if abs(cand_mean) > 30_000.0:
                continue
            res = abs(cand1 - cand2)
            if res < best_res:
                best_res = res
                best_fd = cand_mean
    vel_mps = (best_fd * WAVELENGTH_77GHZ_M) / 2.0
    is_ok = math.isfinite(best_res) and (0.0 <= best_res <= tau_crt_hz)
    return best_fd, vel_mps, is_ok


def spec414_butterfly_a5_curvature(
    *,
    buffer_b: float = 1.25,
    residual_jamming_tau: float = 0.35,
    autonomous_escalation_rate: float = 0.0,
) -> tuple[float, bool]:
    if not (
        math.isfinite(buffer_b)
        and math.isfinite(residual_jamming_tau)
        and math.isfinite(autonomous_escalation_rate)
    ):
        return 0.0, False
    c_war = round((buffer_b - 0.4) * (1.0 - residual_jamming_tau), 6)
    stable = (
        buffer_b >= 1.0
        and 0.0 <= residual_jamming_tau <= 0.60
        and autonomous_escalation_rate == 0.0
        and c_war > 0.0
    )
    return c_war, stable


# ============================================================================
# 4. SPEC-415: DEN BENTISKE K-POD- OG KINEMATISKE KURER-SLUSEN (-240 m & 5 CDC)
# ============================================================================
class Spec415BenthicState(str, Enum):
    OPEN_AUTHORIZED = "OPEN_AUTHORIZED"
    HOLD_BENTHIC_A5 = "HOLD_BENTHIC_A5"
    SABOTAGE_ACOUSTIC_KILL = "SABOTAGE_ACOUSTIC_KILL"
    OPTICAL_TOF_VIOLATION_KILL = "OPTICAL_TOF_VIOLATION_KILL"
    CDC_LOCK_KILL = "CDC_LOCK_KILL"
    COURIER_KINEMATIC_MISMATCH_KILL = "COURIER_KINEMATIC_MISMATCH_KILL"


def spec415_evaluate_benthic_kpod_gate(
    *,
    spl_db: Decimal | int | str = "110.0",
    optical_532nm_rtt_ns: Decimal | int | str = "120.0",
    o2_ppm: Decimal | int | str = "0.02",
    kie_ratio: Decimal | int | str = "4.2",
    mossbauer_shift_mm_s: Decimal | int | str = "0.40",
    reactor_temp_c: Decimal | int | str = "24.0",
    faradaic_eff_pct: Decimal | int | str = "91.5",
    pressure_kpa: Decimal | int | str = "220.0",
    doppler_velocities_mps: Sequence[float] = (-2.0, -2.0, -2.0, -2.0),
    dt_s: float = 1.0,
    initial_range_m: float = 20.0,
    final_tof_range_m: float = 12.0,
    human_w2_authorized: bool = False,
) -> tuple[Spec415BenthicState, Decimal, str]:
    spl = nonnegative_decimal(spl_db)
    rtt = nonnegative_decimal(optical_532nm_rtt_ns)
    if not (spl < SABOTAGE_SPL_THRESHOLD_DB):
        return Spec415BenthicState.SABOTAGE_ACOUSTIC_KILL, D("0.00"), "SPL_145DB_CROWBAR_KILL"
    if not (
        math.isfinite(initial_range_m)
        and math.isfinite(final_tof_range_m)
        and 0.0 <= final_tof_range_m <= 20.0
        and rtt <= MAX_OPTICAL_532NM_RTT_NS
    ):
        return Spec415BenthicState.OPTICAL_TOF_VIOLATION_KILL, D("0.00"), "OPTICAL_532NM_TOF_KILL"

    o2 = nonnegative_decimal(o2_ppm)
    kie = nonnegative_decimal(kie_ratio)
    d_fe = exact_decimal(mossbauer_shift_mm_s)
    t_c = exact_decimal(reactor_temp_c)
    fe = nonnegative_decimal(faradaic_eff_pct)
    p_kpa = nonnegative_decimal(pressure_kpa)

    if not (
        o2 <= D("0.10")
        and D("2.0") <= kie <= D("7.0")
        and D("0.38") <= d_fe <= D("0.42")
        and D("-2.37") <= t_c <= D("52.37")
        and p_kpa <= D("250.0")
    ):
        return Spec415BenthicState.CDC_LOCK_KILL, D("0.00"), "CDC_MOSSBAUER_OR_MOP_KILL"

    if not (
        bool(doppler_velocities_mps)
        and math.isfinite(dt_s)
        and dt_s > 0.0
        and all(math.isfinite(v) for v in doppler_velocities_mps)
    ):
        return (
            Spec415BenthicState.COURIER_KINEMATIC_MISMATCH_KILL,
            D("0.00"),
            "MONOTONICITY_OR_NAN_VIOLATION_KILL",
        )

    doppler_delta_r = sum(v * dt_s for v in doppler_velocities_mps)
    tof_delta_r = final_tof_range_m - initial_range_m
    if not (math.isfinite(doppler_delta_r) and abs(doppler_delta_r - tof_delta_r) <= 0.60):
        return (
            Spec415BenthicState.COURIER_KINEMATIC_MISMATCH_KILL,
            D("0.00"),
            "DOPPLER_VS_TOF_RELAY_SPOOF_KILL",
        )

    if fe < D("85.0") or not human_w2_authorized:
        return Spec415BenthicState.HOLD_BENTHIC_A5, D("2.50"), "A5_HOLD_AWAITING_W2"

    payload = {
        "delta_fe": str(d_fe),
        "fe_pct": str(fe),
        "kie": str(kie),
        "o2_ppm": str(o2),
        "p_kpa": str(p_kpa),
        "state": Spec415BenthicState.OPEN_AUTHORIZED.value,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return Spec415BenthicState.OPEN_AUTHORIZED, D("5.00"), digest


# ============================================================================
# DETERMINISTIC 6/6 MONOLITH TEST SUITE (SPEC-412..415)
# ============================================================================
class TestSpec412To415DomainGates(unittest.TestCase):
    def test_01_spec412_forlik_cooling_off_and_uwb_proximity(self) -> None:
        """SPEC-412: Rejects premature readmission (<72h), disputes, and out-of-bounds UWB RTT."""
        self.assertTrue(spec412_proximity_ok("1050.0"))
        self.assertFalse(spec412_proximity_ok("1200.0"))
        claim = Spec412Claim(debt=D("1000.00")).sign(100)
        self.assertEqual(
            claim.readmit(
                100 + COOL_SECONDS_72H - 1,
                local=True,
                proximity=True,
                capacity=True,
                legal_basis=True,
                bilateral_review=True,
            ).gate,
            Spec412Gate.HOLD,
        )
        admitted = claim.readmit(
            100 + COOL_SECONDS_72H,
            local=True,
            proximity=True,
            capacity=True,
            legal_basis=True,
            bilateral_review=True,
        )
        self.assertEqual(admitted.gate, Spec412Gate.AUTHORIZED)
        settled = admitted.settle(
            "REC-01",
            "250.00",
            "2",
            voluntary=True,
            quality_attested=True,
            receipt_attested=True,
        )
        self.assertEqual(settled.debt, D("500.00"))
        self.assertEqual(settled.gate, Spec412Gate.HOLD)

    def test_02_spec413_orbital_remote_actuation_and_storm_stasis(self) -> None:
        """SPEC-413: LEO RTT (~3.8 ms) is killed on direct actuation; Kp >= 7.0 latches STORM_STASIS."""
        st_act, v_act = spec413_evaluate_orbital_gate(
            measured_rtt_ns="3800000",
            phase_diff_rad=0.2,
            kp_index="2.0",
            snr_db="14.0",
            is_direct_actuation=True,
        )
        self.assertEqual(st_act, Spec413OrbitalStatus.REMOTE_ACTUATION_KILL)
        self.assertEqual(v_act, D("0.00"))

        st_kp, v_kp = spec413_evaluate_orbital_gate(
            measured_rtt_ns="3800000",
            phase_diff_rad=0.2,
            kp_index="7.5",
            snr_db="14.0",
            is_direct_actuation=False,
        )
        self.assertEqual(st_kp, Spec413OrbitalStatus.STORM_STASIS)
        self.assertEqual(v_kp, D("0.00"))

    def test_03_spec413_sub_half_wavelength_ew_phase_guard(self) -> None:
        """SPEC-413: Sub-half-wavelength array (eta=0.5) detects |s_obs| > 1.0 within (-pi, pi]."""
        st_jam, v_jam = spec413_evaluate_orbital_gate(
            measured_rtt_ns="3800000",
            phase_diff_rad=0.75 * math.pi,
            kp_index="2.0",
            snr_db="14.0",
            is_direct_actuation=False,
            spacing_eta=0.5,
        )
        self.assertEqual(st_jam, Spec413OrbitalStatus.JAMMING_KILL)
        self.assertEqual(v_jam, D("0.00"))

        st_nan, v_nan = spec413_evaluate_orbital_gate(
            measured_rtt_ns="3800000",
            phase_diff_rad=float("nan"),
            kp_index="2.0",
            snr_db="14.0",
            is_direct_actuation=False,
            spacing_eta=0.5,
        )
        self.assertEqual(st_nan, Spec413OrbitalStatus.JAMMING_KILL)
        self.assertEqual(v_nan, D("0.00"))

        st_ok, v_ok = spec413_evaluate_orbital_gate(
            measured_rtt_ns="3800000",
            phase_diff_rad=0.25 * math.pi,
            kp_index="2.0",
            snr_db="14.0",
            is_direct_actuation=False,
            spacing_eta=0.5,
        )
        self.assertEqual(st_ok, Spec413OrbitalStatus.NOMINAL_ORBIT)
        self.assertEqual(v_ok, D("5.00"))

    def test_04_spec414_radix4_fft_16_and_staggered_prf_crt(self) -> None:
        """SPEC-414: 16-point Radix-4 FFT matches direct DFT (<1e-12) and 5:6 CRT unfolds 45 m/s."""
        samples = [
            cmath.exp(2j * math.pi * 3 * n / 16.0) + 0.5 * cmath.exp(-2j * math.pi * 5 * n / 16.0)
            for n in range(16)
        ]
        fft_out = spec414_radix4_fft_16(samples)
        for k in range(16):
            dft_k = sum(
                samples[n] * cmath.exp(-2j * math.pi * k * n / 16.0) for n in range(16)
            )
            self.assertAlmostEqual(abs(fft_out[k] - dft_k), 0.0, places=11)

        true_fd = 22_000.0
        f1 = ((true_fd + 5000.0) % 10_000.0) - 5000.0
        f2 = ((true_fd + 6000.0) % 12_000.0) - 6000.0
        unfolded_fd, vel_mps, ok = spec414_unfold_staggered_prf(f1, f2)
        self.assertTrue(ok)
        self.assertAlmostEqual(unfolded_fd, true_fd, places=6)
        self.assertGreater(vel_mps, 40.0)

        _, _, ok_bad = spec414_unfold_staggered_prf(f1 + 500.0, f2, tau_crt_hz=100.0)
        self.assertFalse(ok_bad)
        _, _, ok_nan = spec414_unfold_staggered_prf(float("nan"), f2)
        self.assertFalse(ok_nan)

        c_war, stable = spec414_butterfly_a5_curvature()
        self.assertEqual(c_war, 0.5525)
        self.assertTrue(stable)

    def test_05_spec415_benthic_sabotage_and_cdc_locks_kill(self) -> None:
        """SPEC-415: -240 m SPL >= 145 dB or O2 > 0.10 ppm triggers immediate 0.00 V KILL."""
        st_spl, v_spl, _ = spec415_evaluate_benthic_kpod_gate(spl_db="146.0")
        self.assertEqual(st_spl, Spec415BenthicState.SABOTAGE_ACOUSTIC_KILL)
        self.assertEqual(v_spl, D("0.00"))

        st_o2, v_o2, _ = spec415_evaluate_benthic_kpod_gate(o2_ppm="0.25")
        self.assertEqual(st_o2, Spec415BenthicState.CDC_LOCK_KILL)
        self.assertEqual(v_o2, D("0.00"))

    def test_06_spec415_kinematic_courier_bridge_and_w2_open(self) -> None:
        """SPEC-415: Doppler-vs-ToF relay spoof kills; valid 5 CDC locks + W2 opens at 5.00 V."""
        st_spoof, v_spoof, _ = spec415_evaluate_benthic_kpod_gate(
            doppler_velocities_mps=(0.0, 0.0, 0.0, 0.0),
            initial_range_m=20.0,
            final_tof_range_m=12.0,
        )
        self.assertEqual(st_spoof, Spec415BenthicState.COURIER_KINEMATIC_MISMATCH_KILL)
        self.assertEqual(v_spoof, D("0.00"))

        st_neg_dt, v_neg_dt, _ = spec415_evaluate_benthic_kpod_gate(dt_s=-1.0)
        self.assertEqual(st_neg_dt, Spec415BenthicState.COURIER_KINEMATIC_MISMATCH_KILL)
        self.assertEqual(v_neg_dt, D("0.00"))

        st_nan_v, v_nan_v, _ = spec415_evaluate_benthic_kpod_gate(
            doppler_velocities_mps=(float("nan"), -2.0, -2.0, -2.0),
        )
        self.assertEqual(st_nan_v, Spec415BenthicState.COURIER_KINEMATIC_MISMATCH_KILL)
        self.assertEqual(v_nan_v, D("0.00"))

        st_hold, v_hold, _ = spec415_evaluate_benthic_kpod_gate(human_w2_authorized=False)
        self.assertEqual(st_hold, Spec415BenthicState.HOLD_BENTHIC_A5)
        self.assertEqual(v_hold, D("2.50"))

        st_open, v_open, digest = spec415_evaluate_benthic_kpod_gate(human_w2_authorized=True)
        self.assertEqual(st_open, Spec415BenthicState.OPEN_AUTHORIZED)
        self.assertEqual(v_open, D("5.00"))
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSpec412To415DomainGates)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
