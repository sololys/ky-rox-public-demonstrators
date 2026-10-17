# Euclidean Wavefront Phase-Cone Gate (ISAC Geometry) — public microtest v0.1

Status: `HOLD`  
Intended repository path: `artifacts/microtests/euclidean_phase_cone_isac_v0_1/`

## Scope

This bounded software demonstration evaluates the fundamental trigonometric
phase-cone invariant for a planar wavefront incident on a half-wavelength
interferometer baseline (`d = lambda / 2`):

```text
sin(theta) = Delta_phi / pi
```

1. **Physical Euclidean wavefront (`|Delta_phi / pi| <= 1.0`):** Lies on the real
   unit circle (`theta in [-90 deg, +90 deg]`) -> `measurement_status = OPEN`.
2. **Non-Euclidean phase-offset anomaly (`|Delta_phi / pi| > 1.0`):** Requires a
   complex angle where `cos(theta) = i * sqrt(sin^2(theta) - 1)` -> `status = KILL`.

Only the generic trigonometric boundary crosses this public cut. No private RF
hardware, array calibration, operational threshold, or defense architecture is
included.

## Run

```bash
python euclidean_phase_cone.py
python -m unittest -v test_euclidean_phase_cone.py
sha256sum -c CHECKSUMS.sha256
```

The first command must match `EXPECTED_OUTPUT.txt`. The tests must report six
passing tests. Any mismatch is `HOLD`.

## Non-goals

This artifact is not:

- a radar, RF sensor, or physical interferometer implementation;
- a proof of immunity against physical multipath or RF interference;
- a physical, operational, or commit authority.

`physical_authority=NONE` and `operational_authority=NONE`.
