# PWR2 & Power-Law Spin Scrambling vs. Collective Gate — public microtest v0.1

Status: `HOLD`  
Intended repository path: `artifacts/microtests/pwr2_scrambling_collective_gate_v0_1/`

## Scope

This bounded software demonstration establishes the spectral transition between
low-dimensional collective Dicke dynamics (`O(N)`) and exponential fast
scrambling (`2^N` on timescale `t* ~ log N`) within a fixed long-range XY spin
Hamiltonian as a function of initial-state symmetry-breaking spin flips `k`
(inspired by Kuriyattil, Kombe, Daley & Poggi 2026):

```text
Gamma_q^2(K) = lambda_K * (lambda_q - lambda_K)
k*(N) ~ sqrt(N)   <=>   k*(N) / N ~ N^(-1/2)
```

1. **Circulant Fourier Spectrum (`lambda_q`):** Evaluates the exact eigenvalues
   of periodic Powers-of-Two (`PWR2`), Power-Law (`PL`, `alpha=1`), All-to-All
   (`A2A`), and Nearest-Neighbor (`NN`) coupling matrices.
2. **Unique `PWR2` Alternating Instability (`K = N/2`):** Proves that at the
   staggered Neel mode `K = N/2`, only `PWR2` has `lambda_{N/2} > 0`
   (`Gamma_0^2(N/2) = 20.0 > 0` for `N=32`), whereas `PL`, `A2A`, and `NN` satisfy
   `lambda_{N/2} < 0`.
3. **Signed Laplacian Gap & `sqrt(N)` Threshold (`Pi_K`):** Enforces `GATE::OPEN`
   for symmetric collective states (`k=0`), `GATE::HOLD` in the sub-critical or
   chaos-suppressed regime (`0 < k <= sqrt(N)` or `Gamma_max^2 <= 0`), and
   `GATE::KILL` when `k > sqrt(N)` with positive Lyapunov instability.

## Six Verified Invariants (`test_pwr2_scrambling_collective_gate.py` — 6/6 PASS)

1. **Epistemic boundary constant:** `INSPIRED_BY != IMPLEMENTS != PROVES`.
2. **Collective state (`k=0`):** `QFI/N = N`, `Delta > 0`, `GATE::OPEN`.
3. **Unique `PWR2` Neel instability:** `lambda_{N/2} > 0` exclusively for `PWR2`
   (`GATE::KILL` at `k = N/2`).
4. **Power-Law protocol asymmetry:** Alternating flips suppress chaos (`HOLD`),
   whereas one-sided flips (`K=1`, `lambda_1 > 0`) trigger scrambling (`KILL`).
5. **All-to-All integrability:** `Gamma_q^2(K) <= 0` for all `K`.
6. **Critical `sqrt(N)` scaling:** `k <= sqrt(N)` yields `HOLD`, `k > sqrt(N)`
   with `Gamma_max^2 > 0` yields `KILL`.

## Run

```bash
python3 pwr2_scrambling_collective_gate.py
python3 -m unittest -v test_pwr2_scrambling_collective_gate.py
sha256sum -c CHECKSUMS.sha256
```

## Non-goals

`physical_authority=NONE` and `operational_authority=NONE`.
