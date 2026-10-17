from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PhaseConeVerdict:
    status: str
    measurement_status: str
    claim_status: str
    sin_theta_ratio: float | None
    is_euclidean_admissible: bool
    angle_deg_if_real: float | None
    imaginary_cos_magnitude_if_ghost: float
    verdict_reason: str
    physical_authority: str = "NONE"
    operational_authority: str = "NONE"
    claim: str = "Sanitized trigonometric phase-cone boundary evaluation only"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_phase_difference(
    delta_phi_rad: float, spacing_lambda_ratio: float = 0.5
) -> PhaseConeVerdict:
    """
    Evaluates the Euclidean wavefront phase-cone invariant across an antenna pair:
        Delta_phi = 2 * pi * (d / lambda) * sin(theta)
    For half-wavelength spacing (d / lambda = 0.5):
        sin(theta) = Delta_phi / pi

    A physical planar wavefront in 3D Euclidean space satisfies |sin(theta)| <= 1.0.
    If |sin(theta)| > 1.0, no real angle theta exists (cos(theta) becomes purely
    imaginary), indicating a non-physical or synthetic phase-offset anomaly.
    """
    if not (math.isfinite(delta_phi_rad) and math.isfinite(spacing_lambda_ratio)):
        return PhaseConeVerdict(
            status="KILL",
            measurement_status="KILL",
            claim_status="HOLD",
            sin_theta_ratio=None,
            is_euclidean_admissible=False,
            angle_deg_if_real=None,
            imaginary_cos_magnitude_if_ghost=0.0,
            verdict_reason="NONFINITE_INPUT",
        )
    if spacing_lambda_ratio <= 0.0:
        return PhaseConeVerdict(
            status="KILL",
            measurement_status="KILL",
            claim_status="HOLD",
            sin_theta_ratio=None,
            is_euclidean_admissible=False,
            angle_deg_if_real=None,
            imaginary_cos_magnitude_if_ghost=0.0,
            verdict_reason="NONPOSITIVE_SPACING_RATIO",
        )

    denom = 2.0 * math.pi * spacing_lambda_ratio
    sin_theta = delta_phi_rad / denom

    if abs(sin_theta) <= 1.0:
        clamped = max(-1.0, min(1.0, sin_theta))
        angle_deg = math.degrees(math.asin(clamped))
        return PhaseConeVerdict(
            status="HOLD",
            measurement_status="OPEN",
            claim_status="HOLD",
            sin_theta_ratio=round(sin_theta, 12),
            is_euclidean_admissible=True,
            angle_deg_if_real=round(angle_deg, 10),
            imaginary_cos_magnitude_if_ghost=0.0,
            verdict_reason="EUCLIDEAN_REAL_WAVEFRONT_ADMISSIBLE",
        )

    imag_cos = math.sqrt(sin_theta * sin_theta - 1.0)
    return PhaseConeVerdict(
        status="KILL",
        measurement_status="KILL",
        claim_status="HOLD",
        sin_theta_ratio=round(sin_theta, 12),
        is_euclidean_admissible=False,
        angle_deg_if_real=None,
        imaginary_cos_magnitude_if_ghost=round(imag_cos, 12),
        verdict_reason="COMPLEX_ANGLE_GHOST_WAVEFRONT_VETO",
    )


def main() -> None:
    fixture = json.loads(Path(__file__).with_name("FIXTURE.json").read_text(encoding="utf-8"))
    ratio = float(fixture["antenna_spacing_wavelength_ratio"])
    phys = evaluate_phase_difference(float(fixture["physical_phase_diff_rad"]), ratio)
    ghost = evaluate_phase_difference(float(fixture["synthetic_ghost_phase_diff_rad"]), ratio)
    report = {
        "claim_status": "HOLD",
        "ghost_injection_case": ghost.to_dict(),
        "operational_authority": "NONE",
        "physical_authority": "NONE",
        "physical_wavefront_case": phys.to_dict(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
