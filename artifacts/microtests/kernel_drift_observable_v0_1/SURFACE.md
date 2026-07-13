# Kernel Drift Observable — public microtest v0.1

Status: `HOLD`  
Intended repository path: `artifacts/microtests/kernel_drift_observable_v0_1/`

## Scope

This bounded software demonstration computes two deterministic measurements from
synthetic feature windows:

- normalized change in their relational Gram kernels;
- normalized pointwise feature drift as a simple baseline.

The measurement is `OPEN` when valid inputs can be evaluated. The overall claim
remains `HOLD`: one synthetic fixture cannot establish that kernel drift predicts
loss of viability earlier or better than a simpler diagnostic.

## Source basis

Sanitized from the author-owned research note *Kernel Drift as an Early-Warning
Observable for Loss of Viability in Projection-Constrained Dynamics*.

Only the generic mathematical observable and explicit claim boundary cross this
public cut. No private gate, Witness, hardware, deployment, or patent mechanism is
included.

## Run

```bash
python kernel_drift.py
python -m unittest -v
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
