<p align="center">
  <img src="punkt/media/witness-fiber-consequence-cut.svg" alt="Witness Fiber Consequence Cut" width="100%" />
</p>

# `sololys/ky-rox-public-demonstrators` — L2 Consequence Gate Demonstrators (Morandi-Core)

$$\boxed{\text{CANDIDATE\_GENERATION} \neq \text{AUTHORIZATION} \neq \text{REALIZED\_CONSEQUENCE}}$$

$$\Omega(x, e, \Delta_K) = \begin{cases} \text{OPEN} & \text{if } e \neq \varnothing \land \Delta_K(x) \le \tau_K \land \text{Zone}(x) = \text{CLEAR} \\ \text{HOLD} & \text{if } e = \varnothing \lor \text{Zone}(x) = \text{OCCUPIED} \\ \text{KILL} & \text{if } \Delta_K(x) > \tau_K \end{cases}$$

**Compiled Ingress (EN):** Bounded, deterministic `L1` software microtests (`24/24 PASS`) demonstrating fail-closed consequence gating (`OPEN / HOLD / KILL`). Zero external dependencies ($\Sigma_{\text{ext}} = \emptyset$, Python 3.10+ Standard Library only). Zero physical or operational authority (`0.00 V DC`).
**Kompilert Ingress (NO):** Avgrensede, deterministiske `L1`-mikrotester (`24/24 PASS`) for fail-closed konsekvensporter (`OPEN / HOLD / KILL`). Null eksterne avhengigheter ($\Sigma_{\text{ext}} = \emptyset$, kun Python 3.10+ standardbibliotek). Null fysisk eller operasjonell autoritet (`0,00 V DC`).

---

## I. Execution Contract (`Makefile` & `run_demo.py`)

```bash
# Default invocation fails closed by design (HOLD = 0.00 V DC):
make
# -> [HOLD] 0.00 V DC. System is at rest. (exit code 1)

# Full deterministic verification of L1_LAW, L2_GATE, Public Surface, and 4 Monoliths (24/24 PASS):
make verify
# Or directly:
python3 run_demo.py
```

---

## II. Subtractive Room Topology

| Room | Role | Primary Artifacts |
| :--- | :--- | :--- |
| **[`L1_LAW/`](L1_LAW/)** | Pure mathematical definitions & public boundary contracts. Zero I/O. | [`invariants_pure.py`](L1_LAW/invariants_pure.py) · [`PUBLIC_BOUNDARY.md`](L1_LAW/PUBLIC_BOUNDARY.md) · [`STATUS_PUBLIC.md`](L1_LAW/STATUS_PUBLIC.md) · [`SECURITY.md`](L1_LAW/SECURITY.md) |
| **[`L2_GATE/`](L2_GATE/)** | Boundary projection & consequence gate evaluator ($\Omega \circ \Pi_K$). | [`evaluate_boundaries.py`](L2_GATE/evaluate_boundaries.py) |
| **[`L3_WITNESS/`](L3_WITNESS/)** | Append-only SHA-256 cryptographic receipts ($W^2$). | [`audit_log.jsonl`](L3_WITNESS/audit_log.jsonl) |
| **[`artifacts/microtests/`](artifacts/microtests/)** | The Four Monoliths (`4 x 6/6 = 24/24 PASS` + `CHECKSUMS.sha256`). | See Section III below |
| **[`punkt/contracts/`](punkt/contracts/)** | Claim-level & decision vocabulary contracts (`INSPIRED_BY != IMPLEMENTS != PROVES`). | [`claim-levels.md`](punkt/contracts/claim-levels.md) · [`candidate-not-consequence.md`](punkt/contracts/candidate-not-consequence.md) · [`decision-vocabulary.md`](punkt/contracts/decision-vocabulary.md) |

---

## III. The Four Monoliths (`24/24 PASS`)

Every demonstrator in [`artifacts/microtests/`](artifacts/microtests/) enforces pinned inputs (`FIXTURE.json`), deterministic stdout matching (`EXPECTED_OUTPUT.txt`), unit tests (`6/6 PASS`), and cryptographic integrity (`CHECKSUMS.sha256`):

| Monolith | Domain & Operator | Mathematical Invariant / Law | Verification |
| :--- | :--- | :--- | :--- |
| **1. [LightBridge v0.1](artifacts/microtests/light_bridge_consequence_gate_v0_1/SURFACE.md)** | Consequence Gate ($\Omega_{\text{bridge}}$) | $\frac{d}{dt}\text{HOLD} = 0$. Realization requires $e \neq \varnothing \land \text{Zone} = \text{CLEAR}$. On `KILL`, collision geometry is severed at $\Delta t = 0$. `reset()` is strictly append-only on witness log $\mathcal{L}$. | [`light_bridge.gd`](artifacts/microtests/light_bridge_consequence_gate_v0_1/light_bridge.gd) · [`light_bridge_gate.py`](artifacts/microtests/light_bridge_consequence_gate_v0_1/light_bridge_gate.py) (**`6/6 PASS`**) |
| **2. [ISAC Phase-Cone v0.1](artifacts/microtests/euclidean_phase_cone_isac_v0_1/SURFACE.md)** | Euclidean Wavefront ($\Pi_{S^1}$) | For $d = \lambda / 2$: $\sin\theta = \Delta\phi / \pi$. Physical wave: $\|\Delta\phi / \pi\| \le 1 \implies \cos\theta \in \mathbb{R} \implies \text{OPEN}$. Synthetic injection: $\|\Delta\phi / \pi\| > 1 \implies \cos\theta \in i\mathbb{R}_{>0} \implies \text{KILL}$. | [`euclidean_phase_cone.py`](artifacts/microtests/euclidean_phase_cone_isac_v0_1/euclidean_phase_cone.py) (**`6/6 PASS`**) |
| **3. [PUNKT // BANE Yin–Yang v0.1](artifacts/microtests/p_np_yinyang_binpacking_v0_1/SURFACE.md)** | Construction Path ($\gamma_P$ vs. $C_{NP}$) | Separates a static certificate point $C \in \mathcal{NP}$ from a sequentially verified construction path $\gamma = (x_0 \to x_n)$ bound by $W_{\text{PRE}}$ and $W_{\text{POST}}$. Status: `p_equals_np_claim_status = HOLD`. | [`yinyang_binpacking.py`](artifacts/microtests/p_np_yinyang_binpacking_v0_1/yinyang_binpacking.py) (**`6/6 PASS`**) |
| **4. [Kernel Drift Observable v0.1](artifacts/microtests/kernel_drift_observable_v0_1/SURFACE.md)** | Relational Geometry ($G_{ij} = \langle \psi_i, \psi_j \rangle$) | Pointwise norm $\|x_t - x_0\|$ is blind to rigid rotations and internal phase shear. Relational drift is measured over the Gram matrix $\Delta_G = \|G(t) - G(0)\|_F$. | [`kernel_drift.py`](artifacts/microtests/kernel_drift_observable_v0_1/kernel_drift.py) (**`6/6 PASS`**) |

---

## IV. Claim & Authority Boundary

```text
PUBLIC_TREE_GATE        = PASS
MICROTEST_GATE          = PASS (4 suites / 24 unit tests)
SCOPE                   = EXACT_CHECKED_TREE_ONLY
CLAIM_STATUS            = HOLD (INSPIRED_BY != IMPLEMENTS != PROVES)
PHYSICAL_AUTHORITY      = NONE (0.00 V DC)
OPERATIONAL_AUTHORITY   = NONE
```

---

<p align="center"><code>GENERATION != AUTHORIZATION != WITNESSED CONSEQUENCE · 0.00 V DC</code></p>
