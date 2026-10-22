# M-Polynomial & 1-Weisfeiler-Lehman (1-WL) Molecular Gate — public microtest v0.1

Status: `HOLD`  
Intended repository path: `artifacts/microtests/mpolynomial_1wl_molecular_gate_v0_1/`

## Scope

This bounded software demonstration establishes the exact mathematical separation
between soft Message Passing Neural Network (MPNN) feature concatenation and a
hard fail-closed molecular consequence gate (`Pi_K`):

```text
M(G; x, y) = sum_{i <= j} m_{ij}(G) x^i y^j
SOFT GNN EMBEDDING (h_v^(0) || M_1 || R || H) != CONSEQUENCE GATE (Pi_K)
```

For a molecular graph `G = (V, E)`:

1. **Exact Edge-Degree Partitioning (`E_{ij}`):** Decomposes `E(G)` by endpoint
   degrees `(i, j)` and extracts First/Second Zagreb (`M_1, M_2`), Randic (`R`),
   Harmonic (`H`), and Symmetric Division Degree (`SDD`) indices via closed
   differential and integral operators at `x = y = 1`.
2. **1-WL Bottleneck & Co-Polynomial Isomers:** Demonstrates that Decalin (`2xC6`)
   and Bicyclopentyl (`2xC5`) share both identical 1-WL color refinement
   signatures and identical M-polynomials (`6*x^2*y^2 + 4*x^2*y^3 + x^3*y^3`),
   forcing `GATE::HOLD` (`0.00 V DC`) until higher-order cycle motifs are witnessed.
3. **Bio-Inorganic `[Fe7MoS9C]` Cluster vs. Organic Valence Breach:** Admits the
   18-atom `[Fe7MoS9C]` FeMo-cofactor cluster with interstitial `mu6-C` carbide
   (`6*x^2*y^4 + 6*x^3*y^3 + 12*x^3*y^4 + 6*x^4*y^6`, `M_1 = 216`, `M_2 = 390`)
   when all 6 neighbors are `Fe/Mo`, while immediately severing organic
   pentavalent "Texas Carbon" hallucinations to `GATE::KILL` (`0.00 V DC`).

## Six Verified Invariants (`test_mpolynomial_1wl_molecular_gate.py` — 6/6 PASS)

1. **Epistemic boundary constant:** `INSPIRED_BY != IMPLEMENTS != PROVES`.
2. **Isomer separation (`n-Butane` vs. `Isobutane`):** Exact separation via
   `M(G; x, y)` (`2*x^1*y^2 + x^2*y^2` vs. `3*x^1*y^3`).
3. **1-WL & M-Polynomial collision (`Decalin` vs. `Bicyclopentyl`):** Identical
   1-WL and `M(G; x, y)` force `GATE::HOLD` (`0.00 V DC`) prior to cycle witness.
4. **Disconnected ghost graph (`Benzene C6` vs. `2xC3`):** Identical 1-WL and
   `6*x^2*y^2`, severed to `GATE::KILL` (`0.00 V DC`) via `beta_0 = 2`.
5. **Valence violation (`Texas Carbon`):** Soft GNN produces finite embeddings,
   whereas `Pi_K` forces immediate `GATE::KILL` (`0.00 V DC`).
6. **Bio-inorganic `[Fe7MoS9C]` cluster:** Exact `M(G; x, y)` and `M_1 = 216.0`,
   `M_2 = 390.0` verified (`GATE::OPEN`).

## Run

```bash
python3 mpolynomial_1wl_molecular_gate.py
python3 -m unittest -v test_mpolynomial_1wl_molecular_gate.py
sha256sum -c CHECKSUMS.sha256
```

## Non-goals

`physical_authority=NONE` and `operational_authority=NONE`.
