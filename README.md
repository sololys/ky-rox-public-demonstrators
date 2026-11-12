<p align="center">
  <img src="punkt/media/witness-fiber-consequence-cut.svg" alt="Witness Fiber Consequence Cut" width="100%" />
</p>

# KY-ROX Public Demonstrators — Runnable Gates & FPGA Prototypes

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24032490.svg)](https://doi.org/10.5281/zenodo.24032490)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0006--0431--6637-A6CE39?style=flat-square)](https://orcid.org/0009-0006-0431-6637)
[![Granitum Physics](https://img.shields.io/badge/SALON-Granitum_Physics_(LinkedIn)-0A66C2?style=flat-square)](https://www.linkedin.com/groups/40622443/)

> **Coordinate (`4 · Gate`):** [`(0,0) sololys`](https://github.com/sololys) — [`1 · Word`](https://github.com/sololys/skrivevaerelset) → [`2 · Draft`](https://github.com/sololys/epistemic-architectures-notes) → [`3 · Rule`](https://github.com/sololys/epistemic-architectures) → **`[4 · Gate]`** → [`5 · Seal`](https://github.com/sololys/monolitt)

Runnable Python microtests (Python 3.10+ Standard Library only) and synthesizable SystemVerilog (`IEEE 1800-2012`) gate prototypes implementing the specifications in [`epistemic-architectures`](https://github.com/sololys/epistemic-architectures).

$$\Omega(x, e, \Delta_K) = \begin{cases} \mathrm{OPEN} & \text{if } e \neq \varnothing \land \Delta_K(x) \le \tau_K \land \mathrm{Zone}(x) = \mathrm{CLEAR} \\ \mathrm{HOLD} & \text{if } e = \varnothing \lor \mathrm{Zone}(x) = \mathrm{OCCUPIED} \\ \mathrm{KILL} & \text{if } \Delta_K(x) > \tau_K \end{cases}$$

* **Author:** Marius Egerhei Torjusen · Risør, Norway ([ORCID `0009-0006-0431-6637`](https://orcid.org/0009-0006-0431-6637) · Zenodo DOIs [`10.5281/zenodo.18436983`](https://doi.org/10.5281/zenodo.18436983) · [`10.5281/zenodo.22229111`](https://doi.org/10.5281/zenodo.22229111))
* **Epistemic Boundary (`INSPIRED_BY != IMPLEMENTS != PROVES`):** Bounded `L1` software microtests (`48/48 PASS` across 8 suites + `10/10 PASS` in `L1_LAW`) and `L1`/`L1.5` RTL testbenches (`0.00 V DC`, zero physical or operational authority).

---

## I. Run & Verify (`Makefile` & `run_demo.py`)

```bash
# Default invocation fails closed by design (HOLD = 0.00 V DC):
make
# -> [HOLD] 0.00 V DC. System is at rest. (exit code 1)

# Full deterministic verification of L1_LAW (10/10), L2_GATE, and 8 Suites (48/48 PASS):
make verify
# Or directly:
python3 run_demo.py

# Optional SystemVerilog RTL simulation (requires iverilog):
make sim_205b   # 205-byte capsule frame decoder & 12.5 us guillotine testbench
make sim_400c   # 400-cycle temporal bifurcation gate testbench
```

---

## II. Directory Map

| Directory | Role | Primary Artifacts |
| :--- | :--- | :--- |
| **[`L1_LAW/`](L1_LAW/)** | Pure mathematical definitions (`KY_ROX_SCOPE_GATE_V0_2`), KY codec & public boundary contracts. Zero I/O. | [`invariants_pure.py`](L1_LAW/invariants_pure.py) (`10/10 PASS`) · [`ky_parser.py`](L1_LAW/ky_parser.py) · [`PUBLIC_BOUNDARY.md`](L1_LAW/PUBLIC_BOUNDARY.md) · [`STATUS_PUBLIC.md`](L1_LAW/STATUS_PUBLIC.md) · [`SECURITY.md`](L1_LAW/SECURITY.md) |
| **[`L2_GATE/`](L2_GATE/)** | Consequence gate evaluators ($\Omega \circ \Pi_K$) & SystemVerilog RTL gate modules. | [`evaluate_boundaries.py`](L2_GATE/evaluate_boundaries.py) · [`fpga_capsule_frame_205b_decoder.sv`](L2_GATE/fpga_capsule_frame_205b_decoder.sv) · [`kpod_fpga_guillotine_12u5.sv`](L2_GATE/kpod_fpga_guillotine_12u5.sv) · [`temporal_bifurcation_400c.sv`](L2_GATE/temporal_bifurcation_400c.sv) · [`gothenburg_corridor_rosetta_top.sv`](L2_GATE/gothenburg_corridor_rosetta_top.sv) |
| **[`L3_WITNESS/`](L3_WITNESS/)** | Append-only SHA-256 hash-chain log ($W^2$). | [`audit_log.jsonl`](L3_WITNESS/audit_log.jsonl) *(software hash chain, not physical WORM)* |
| **[`artifacts/microtests/`](artifacts/microtests/) & [`monoliths/`](monoliths/)** | The Seven Monoliths & `SPEC-412..415` Domain Gates (`8 x 6/6 = 48/48 PASS` + `CHECKSUMS.sha256`). | See Section III below |
| **[`punkt/contracts/`](punkt/contracts/)** | Claim-level & decision vocabulary contracts (`INSPIRED_BY != IMPLEMENTS != PROVES`). | [`claim-levels.md`](punkt/contracts/claim-levels.md) · [`candidate-not-consequence.md`](punkt/contracts/candidate-not-consequence.md) · [`decision-vocabulary.md`](punkt/contracts/decision-vocabulary.md) |

---

## III. The Seven Monoliths & `SPEC-412..415` Domain Gates (`48/48 PASS`)

Every demonstrator in [`artifacts/microtests/`](artifacts/microtests/) and [`monoliths/`](monoliths/) enforces deterministic execution, unit tests (`6/6 PASS` per suite), and cryptographic integrity:

| Monolith / Gate | Domain & Operator | Mathematical Invariant / Law | Verification |
| :--- | :--- | :--- | :--- |
| **1. [LightBridge v0.1](artifacts/microtests/light_bridge_consequence_gate_v0_1/SURFACE.md)** | Consequence Gate ($\Omega_{\text{bridge}}$) | No silent `HOLD` ($\Delta_K \neq \varnothing$); $\frac{d}{dt}\text{HOLD} = 0$, while $\Delta\tau > \tau_{\max}$ forfeits $\mathcal{P}_{\text{int}} \to \mathcal{P}_{\text{ext}}$ at `0.00 V`. Realization requires $e \neq \varnothing \land \text{Zone} = \text{CLEAR}$. $\Omega_1 \neq \Omega_2 \implies \text{KILL\_GATE\_CAPTURE}$; `reset()` is append-only on $\mathcal{L}$. | [`light_bridge.gd`](artifacts/microtests/light_bridge_consequence_gate_v0_1/light_bridge.gd) · [`light_bridge_gate.py`](artifacts/microtests/light_bridge_consequence_gate_v0_1/light_bridge_gate.py) (**`6/6 PASS`**) |
| **2. [ISAC Phase-Cone v0.1](artifacts/microtests/euclidean_phase_cone_isac_v0_1/SURFACE.md)** | Euclidean Wavefront ($\Pi_{S^1}$) | For $d = \lambda / 2$: $\sin\theta = \Delta\phi / \pi$. Physical wave: $\|\Delta\phi / \pi\| \le 1 \implies \cos\theta \in \mathbb{R} \implies \text{OPEN}$. Synthetic injection: $\|\Delta\phi / \pi\| > 1 \implies \cos\theta \in i\mathbb{R}_{>0} \implies \text{KILL}$. | [`euclidean_phase_cone.py`](artifacts/microtests/euclidean_phase_cone_isac_v0_1/euclidean_phase_cone.py) (**`6/6 PASS`**) |
| **3. [PUNKT // BANE Yin–Yang v0.1](artifacts/microtests/p_np_yinyang_binpacking_v0_1/SURFACE.md)** | Construction Path ($\gamma_P$ vs. $C_{NP}$) | Separates a static certificate point $C \in \mathcal{NP}$ from a sequentially verified construction path $\gamma = (x_0 \to x_n)$ bound by $W_{\text{PRE}}$ and $W_{\text{POST}}$. Status: `p_equals_np_claim_status = HOLD`. | [`yinyang_binpacking.py`](artifacts/microtests/p_np_yinyang_binpacking_v0_1/yinyang_binpacking.py) (**`6/6 PASS`**) |
| **4. [Kernel Drift Observable v0.1](artifacts/microtests/kernel_drift_observable_v0_1/SURFACE.md)** | Relational Geometry ($G_{ij} = \langle \psi_i, \psi_j \rangle$) | Pointwise norm $\|x_t - x_0\|$ is blind to rigid rotations and internal phase shear. Relational drift is measured over the Gram matrix $\Delta_G = \|G(t) - G(0)\|_F$. | [`kernel_drift.py`](artifacts/microtests/kernel_drift_observable_v0_1/kernel_drift.py) (**`6/6 PASS`**) |
| **5. [M-Polynomial & 1-WL Molecular Gate v0.1](artifacts/microtests/mpolynomial_1wl_molecular_gate_v0_1/SURFACE.md)** | Algebraic Graph Gate ($M(G; x, y)$ & $\Pi_K$) | $M(G; x, y) = \sum_{i \le j} m_{ij}x^i y^j$. Soft GNN concatenation ($h_v^{(0)} \parallel M_1 \parallel R \parallel H$) cannot resolve 1-WL co-polynomial collisions (Decalin vs. Bicyclopentyl $\to \text{HOLD}$) or block organic Texas Carbon ($\text{KILL}$), while admitting bio-inorganic `[Fe7MoS9C]` $\mu_6\text{-C}$ ($\text{OPEN}$). | [`mpolynomial_1wl_molecular_gate.py`](artifacts/microtests/mpolynomial_1wl_molecular_gate_v0_1/mpolynomial_1wl_molecular_gate.py) (**`6/6 PASS`**) |
| **6. [PWR2 Scrambling vs. Collective Gate v0.1](artifacts/microtests/pwr2_scrambling_collective_gate_v0_1/SURFACE.md)** | Spectral Spin-Graph Gate ($\Gamma_q^2(K)$ & $k^* \sim \sqrt{N}$) | $\Gamma_q^2(K) = \lambda_K(\lambda_q - \lambda_K)$. At staggered Néel mode $K = N/2$, only `PWR2` has $\lambda_{N/2} > 0$ ($\text{KILL}$ for $k > \sqrt{N}$), while symmetric collective states ($k = 0, \Delta > 0$) pass as $\text{OPEN}$. | [`pwr2_scrambling_collective_gate.py`](artifacts/microtests/pwr2_scrambling_collective_gate_v0_1/pwr2_scrambling_collective_gate.py) (**`6/6 PASS`**) |
| **7. [Horisont I: Staggered-PRF Fine–Wilf Gate v0.1](monoliths/staggered_prf_fine_wilf_gate.py)** | Combinatorial SDR Horizon ($L^* = p + q - \gcd(p,q)$) | Rejects dual-periodic Sturmian multipath ghost collisions at $L^* = 12$ ($p=5, q=8$), enforces array Bragg coherence $R \ge 0.95$, and integrates continuous Doppler range-rate $\int v_r\,\mathrm{d}t$. | [`staggered_prf_fine_wilf_gate.py`](monoliths/staggered_prf_fine_wilf_gate.py) (**`6/6 PASS`**) |
| **8. [Horisont II: Domain Gates `SPEC-412..415` v2.0](monoliths/spec412_415_domain_gates.py)** | Forlik (`SPEC-412`), Orbital (`SPEC-413`), Radar (`SPEC-414`), Benthic K-POD (`SPEC-415`) | 72h cooling-off & UWB proximity ($40/c \pm 4.5\text{ ns}$); sub-half-wavelength $|s_{\text{obs}}| \le 1$ & $K_p < 7.0$ stasis; 16-pt Radix-4 FFT, 5:6 CRT unfolding & Thom $A_5$ pocket ($c_{\text{war}} = +0.5525$); $-240\text{ m}$ 5 CDC locks, $^{57}\text{Fe}$ Mössbauer & Doppler-to-ToF courier bridge. | [`spec412_415_domain_gates.py`](monoliths/spec412_415_domain_gates.py) (**`6/6 PASS`**) |

---

## IV. Claim & Authority Boundary (KY v1.5-MASTER & GKO Lab Note Seksjon 5)

```text
PUBLIC_TREE_GATE             = PASS
MICROTEST_GATE               = PASS (8 suites / 48 unit tests + L1_LAW + L2_GATE)
SCOPE                        = EXACT_CHECKED_TREE_ONLY
CLAIM_STATUS                 = HOLD (INSPIRED_BY != IMPLEMENTS != PROVES)
SIMULATION_CLASSIFICATION    = OPEN_AS_SOFTWARE_DEMONSTRATION (0xABCDEF00 — deterministisk demonstrert i simuleringsmotoren)
HARDWARE_D_LATCH_ACTUATION   = HOLD (Registry B: Ikke fysisk målt silisium-spenning; avventer GPIO/FPGA HIL-logg)
STANDALONE_HASH_OR_UNICODE   = KILL (Registry A: D3 krever eksplisitt skjema/versjon + eksternt anker / HMAC / fysisk WORM)
CANONICAL_KY_GLYPH           = ✓(○ → ∅ → □ → ◇ → ●)#! ▸ (Alternativ A: ● kun D2-node, ! er commit_event, # er witness_hash)
PHYSICAL_AUTHORITY           = NONE (0.00 V DC)
OPERATIONAL_AUTHORITY        = NONE
```

---

<p align="center"><code>GENERATION != AUTHORIZATION != WITNESSED CONSEQUENCE · 0.00 V DC</code></p>

---
**Metadata & Terms:** [ORCID `0009-0006-0431-6637`](https://orcid.org/0009-0006-0431-6637) · [`LICENSE`](LICENSE) · [`NOTICE`](NOTICE)

