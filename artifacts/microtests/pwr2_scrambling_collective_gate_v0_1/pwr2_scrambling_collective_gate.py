from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple


EPISTEMIC_BOUNDARY = "INSPIRED_BY != IMPLEMENTS != PROVES"

GATE_OPEN = "GATE::OPEN"
GATE_HOLD = "GATE::HOLD"
GATE_KILL = "GATE::KILL"

VOLTAGE_OPEN_VDC = 5.00
VOLTAGE_HOLD_VDC = 0.00
VOLTAGE_KILL_VDC = 0.00


def _is_power_of_two(d: int) -> bool:
    return d > 0 and (d & (d - 1)) == 0


def build_circulant_first_row(n: int, geometry: str, alpha: float = 1.0) -> Tuple[float, ...]:
    if n < 4 or (n % 2) != 0:
        raise ValueError("N must be an even integer >= 4")

    geom = geometry.upper()
    row: List[float] = [0.0] * n
    for r in range(1, n):
        dist = min(r, n - r)
        if geom == "PWR2":
            if _is_power_of_two(dist):
                row[r] = 1.0
        elif geom == "PL":
            row[r] = float(dist) ** (-alpha)
        elif geom == "A2A":
            row[r] = 1.0
        elif geom == "NN":
            if dist == 1:
                row[r] = 1.0
        else:
            raise ValueError(f"Unknown coupling geometry: {geometry}")
    return tuple(row)


def compute_circulant_eigenvalues(first_row: Tuple[float, ...]) -> Tuple[float, ...]:
    n = len(first_row)
    eigs: List[float] = []
    for q in range(n):
        val = sum(
            first_row[r] * math.cos(2.0 * math.pi * float(q * r) / float(n))
            for r in range(n)
        )
        eigs.append(round(val, 10))
    return tuple(eigs)


def compute_gamma_squared_spectrum(
    eigenvalues: Tuple[float, ...],
    background_mode_k: int,
) -> Tuple[float, ...]:
    lam_k = eigenvalues[background_mode_k]
    return tuple(round(lam_k * (lam_q - lam_k), 10) for lam_q in eigenvalues)


def build_spin_flip_signs(n: int, k_flips: int, protocol: str = "alternating") -> Tuple[int, ...]:
    if k_flips < 0 or k_flips > n // 2:
        raise ValueError(f"k_flips={k_flips} out of range [0, {n // 2}]")

    signs = [1] * n
    prot = protocol.lower()
    if prot == "alternating":
        flipped = 0
        idx = 0
        while flipped < k_flips and idx < n:
            signs[idx] = -1
            flipped += 1
            idx += 2
    elif prot == "one_sided":
        for i in range(k_flips):
            signs[i] = -1
    else:
        raise ValueError(f"Unknown protocol: {protocol}")
    return tuple(signs)


def compute_signed_laplacian_spectral_gap(
    first_row: Tuple[float, ...],
    spin_signs: Tuple[int, ...],
) -> float:
    n = len(first_row)
    eigs = compute_circulant_eigenvalues(first_row)
    lam_0 = eigs[0]
    base_gap = min(lam_0 - eigs[q] for q in range(1, n))

    k_flips = sum(1 for s in spin_signs if s < 0)
    if k_flips == 0:
        return round(base_gap, 6)

    total_weight = 0.0
    signed_sum = 0.0
    for i in range(n):
        for r in range(1, n):
            j = (i + r) % n
            w = first_row[r]
            if w > 0.0:
                total_weight += w
                signed_sum += w * float(spin_signs[i] * spin_signs[j])

    coherence_ratio = max(0.0, signed_sum / total_weight) if total_weight > 0.0 else 0.0
    k_crit = math.sqrt(float(n))
    suppression = math.exp(-float(k_flips) / k_crit) * coherence_ratio
    return round(base_gap * suppression, 6)


def compute_qfi_density_all_to_all(n: int, k_flips: int) -> float:
    return round((4.0 / float(n)) * ((0.5 * float(n) - float(k_flips)) ** 2), 6)


@dataclass(frozen=True)
class SpinScramblingGateVerdict:
    geometry: str
    num_spins_n: int
    num_flips_k: int
    flip_fraction_k_over_n: float
    critical_flips_k_star: float
    critical_ratio_k_star_over_n: float
    protocol: str
    background_mode_index: int
    lambda_0: float
    lambda_1: float
    lambda_n_over_2: float
    max_gamma_squared: float
    effective_lyapunov_rate: float
    spectral_gap_delta: float
    qfi_density_bound: float
    scrambling_time_proxy_log_n: float
    gate_state: str
    voltage_vdc: float
    dynamical_regime: str
    reasons: Tuple[str, ...]
    witness_sha256: str


def evaluate_spin_scrambling_consequence_gate(
    n: int = 32,
    k_flips: int = 0,
    geometry: str = "PWR2",
    protocol: str = "alternating",
    alpha: float = 1.0,
) -> SpinScramblingGateVerdict:
    first_row = build_circulant_first_row(n, geometry, alpha=alpha)
    eigs = compute_circulant_eigenvalues(first_row)
    signs = build_spin_flip_signs(n, k_flips, protocol=protocol)

    prot = protocol.lower()
    if k_flips == 0:
        bg_mode = 0
    elif prot == "alternating":
        bg_mode = n // 2
    else:
        bg_mode = 1

    gamma_sq_spec = compute_gamma_squared_spectrum(eigs, bg_mode)
    flip_intensity = float(k_flips) / float(n // 2) if n > 0 else 0.0
    max_gamma_sq = max(gamma_sq_spec) * flip_intensity
    lyapunov_rate = math.sqrt(max_gamma_sq) if max_gamma_sq > 0.0 else 0.0

    gap_delta = compute_signed_laplacian_spectral_gap(first_row, signs)
    qfi_bound = compute_qfi_density_all_to_all(n, k_flips)
    k_star = math.sqrt(float(n))
    k_ratio = float(k_flips) / float(n)
    k_star_ratio = k_star / float(n)
    t_star_log_n = round(math.log2(float(n)), 6)

    reasons: List[str] = []
    if k_flips == 0:
        gate_state = GATE_OPEN
        voltage_vdc = VOLTAGE_OPEN_VDC
        regime = "COLLECTIVE_SYMMETRIC_DICKE_MANIFOLD_O(N)"
        reasons.append(
            f"Pi_K PASS: Full permutational symmetry (k=0), protected by Laplacian gap Delta={gap_delta:.4f} "
            f"and maximal QFI/N={qfi_bound:.2f}."
        )
    elif float(k_flips) > k_star and max_gamma_sq > 1e-6:
        gate_state = GATE_KILL
        voltage_vdc = VOLTAGE_KILL_VDC
        regime = "FAST_SCRAMBLING_EXPONENTIAL_2^N_CHAOS"
        reasons.append(
            f"Pi_K CROWBAR: Symmetry-breaking spin flips k={k_flips} exceed critical threshold "
            f"k*=sqrt(N)={k_star:.2f} with positive instability Gamma_max^2={max_gamma_sq:.4f} "
            f"(lambda_L={lyapunov_rate:.4f} > 0, t*~log2(N)={t_star_log_n:.2f})."
        )
    else:
        gate_state = GATE_HOLD
        voltage_vdc = VOLTAGE_HOLD_VDC
        regime = "CROSSOVER_QUASI_COLLECTIVE_OR_SUPPRESSED_CHAOS"
        reasons.append(
            f"Pi_K HOLD: Partial symmetry breaking (k={k_flips}, k*={k_star:.2f}, Gamma_max^2={max_gamma_sq:.4f}, "
            f"Delta={gap_delta:.4f}). Requires Z_k^alpha resymmetrization prior to OPEN."
        )

    payload = {
        "geometry": geometry.upper(),
        "n": n,
        "k": k_flips,
        "protocol": prot,
        "lambda_0": eigs[0],
        "lambda_1": eigs[1],
        "lambda_n_over_2": eigs[n // 2],
        "max_gamma_sq": round(max_gamma_sq, 6),
        "gap_delta": gap_delta,
        "gate_state": gate_state,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    witness = hashlib.sha256(b"PWR2-SCRAMBLING-GATE/v1.0:" + raw).hexdigest()

    return SpinScramblingGateVerdict(
        geometry=geometry.upper(),
        num_spins_n=n,
        num_flips_k=k_flips,
        flip_fraction_k_over_n=round(k_ratio, 6),
        critical_flips_k_star=round(k_star, 6),
        critical_ratio_k_star_over_n=round(k_star_ratio, 6),
        protocol=prot,
        background_mode_index=bg_mode,
        lambda_0=eigs[0],
        lambda_1=eigs[1],
        lambda_n_over_2=eigs[n // 2],
        max_gamma_squared=round(max_gamma_sq, 6),
        effective_lyapunov_rate=round(lyapunov_rate, 6),
        spectral_gap_delta=gap_delta,
        qfi_density_bound=qfi_bound,
        scrambling_time_proxy_log_n=t_star_log_n,
        gate_state=gate_state,
        voltage_vdc=voltage_vdc,
        dynamical_regime=regime,
        reasons=tuple(reasons),
        witness_sha256=witness,
    )


def main() -> None:
    fixture = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))
    n = int(fixture["num_spins_n"])
    k_scram = int(fixture["scrambling_flips_k"])
    k_cross = int(fixture["crossover_flips_k"])
    alpha = float(fixture["alpha"])

    v_coll = evaluate_spin_scrambling_consequence_gate(n=n, k_flips=0, geometry="PWR2", protocol="alternating", alpha=alpha)
    v_cross = evaluate_spin_scrambling_consequence_gate(n=n, k_flips=k_cross, geometry="PWR2", protocol="alternating", alpha=alpha)
    v_pwr2_kill = evaluate_spin_scrambling_consequence_gate(n=n, k_flips=k_scram, geometry="PWR2", protocol="alternating", alpha=alpha)
    v_pl_alt = evaluate_spin_scrambling_consequence_gate(n=n, k_flips=k_scram, geometry="PL", protocol="alternating", alpha=alpha)
    v_pl_one = evaluate_spin_scrambling_consequence_gate(n=n, k_flips=k_scram, geometry="PL", protocol="one_sided", alpha=alpha)

    out: Dict[str, Any] = {
        "claim": "Bounded spectral spin-graph and consequence gate evaluation only",
        "claim_status": "HOLD",
        "collective_k0_gate": v_coll.gate_state,
        "collective_qfi_per_spin": v_coll.qfi_density_bound,
        "crossover_k4_gate": v_cross.gate_state,
        "epistemic_boundary": EPISTEMIC_BOUNDARY,
        "operational_authority": "NONE",
        "physical_authority": "NONE",
        "pl_alternating_k16_gate": v_pl_alt.gate_state,
        "pl_one_sided_k16_gate": v_pl_one.gate_state,
        "pwr2_alternating_k16_gamma_sq": v_pwr2_kill.max_gamma_squared,
        "pwr2_alternating_k16_gate": v_pwr2_kill.gate_state,
        "pwr2_lambda_n_over_2": v_pwr2_kill.lambda_n_over_2,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
