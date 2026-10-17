# P-NP Yin-Yang Bin Packing (Point, Path & Witness) — public microtest v0.1

Status: `HOLD`  
Intended repository path: `artifacts/microtests/p_np_yinyang_binpacking_v0_1/`

## Scope

This bounded software demonstration separates an unregulated candidate placement
(`NP` certificate point `C`) from a step-verified construction sequence (`P`
path `gamma` with `W_PRE` and `W_POST` hashes):

- `VERIFY(I, C) in P` is demonstrated on the micro-certificate `2 x 4 = 8 <= 8`.
- `FIND(I)` is not thereby shown to lie in `P`.
- `p_equals_np_claim_status` is explicitly locked to `HOLD`.

## Run

```bash
python yinyang_binpacking.py
python -m unittest -v test_yinyang_binpacking.py
sha256sum -c CHECKSUMS.sha256
```

The first command must match `EXPECTED_OUTPUT.txt`. The tests must report six
passing tests. Any mismatch is `HOLD`.

## Non-goals

This artifact is not:

- a proof or claim that `P = NP` or `P != NP`;
- a polynomial-time solver for general NP-hard Bin Packing;
- a physical, operational, or commit authority.

`physical_authority=NONE` and `operational_authority=NONE`.
