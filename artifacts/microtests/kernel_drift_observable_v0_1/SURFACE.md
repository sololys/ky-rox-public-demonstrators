# Kernel Drift Observable — public microtest v0.1

Status: `HOLD`  
Intended repository path: `artifacts/microtests/kernel_drift_observable_v0_1/`

## Scope

This bounded software demonstration establishes the exact mathematical separation
between global coordinate displacement (`STATE DRIFT`) and internal structural
collapse (`KERNEL DRIFT`):

```text
STATE DRIFT (Delta_state) != KERNEL DRIFT (Delta_G)
```

For an ensemble `X(t)` of vectors in Euclidean space:

1. **Pointwise State Drift (`Delta_state = ||X(t) - X(0)||_F`):** Sensitive to
   harmless global rigid rotations `U in O(d)`.
2. **Relational Gram Kernel Drift (`Delta_G = ||G(t) - G(0)||_F`):** Invariant
   under any orthogonal transformation (`Delta_G = 0`), while immediately
   exposing internal shear, scaling, or spectral collapse (`Delta_G > tau_G`).

## Six Verified Invariants (`test_kernel_drift.py` — 6/6 PASS)

1. **Null-point identity:** `X(t) = X(0) => Delta_state = 0` and `Delta_G = 0`.
2. **Orthogonal invariance (blindness test):** Under rigid rotation `U^T U = I`,
   `Delta_state > 0` while `Delta_G <= 1e-12` (`OPEN`).
3. **Relational shear detection:** Internal relative deformation forces
   `Delta_G > tau_G` (`KILL`).
4. **Scaling & spectral breach:** Uniform scaling `X(t) = alpha X(0)` (`alpha != 1`)
   yields `Delta_G = |alpha^2 - 1| ||G(0)||_F > tau_G` (`KILL`).
5. **Positive Semidefinite (PSD) guarantee:** Synthetic non-PSD Gram matrices or
   shape mismatches trigger immediate `KILL`.
6. **Witness enforcement & append-only ledger:** Missing `evidence_id` forces
   `HOLD`, and every evaluation appends an immutable `WitnessRecord`.

## Source basis

Sanitized from the author-owned research note *Kernel Drift as an Early-Warning
Observable for Loss of Viability in Projection-Constrained Dynamics*.

Only the generic mathematical observable and explicit claim boundary cross this
public cut. No private sensor calibration, operational threshold, hardware, or
patent mechanism is included.

## Run

```bash
python kernel_drift.py
python -m unittest -v test_kernel_drift.py
sha256sum -c CHECKSUMS.sha256
```

The first command must match `EXPECTED_OUTPUT.txt`. The tests must report six
passing tests. Any mismatch is `HOLD`.

## Non-goals

This artifact is not:

- evidence of a new physical law;
- proof of early-warning advantage;
- a production detector or safety component;
- a physical, operational, or commit authority;
- a publication of protected architecture or operational thresholds.

`physical_authority=NONE` and `operational_authority=NONE`.
