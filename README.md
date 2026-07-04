# ky-rox-public-demonstrators: Fail-Closed Realization Architecture

**Prediction is not action.**

A generated candidate must never become a realized consequence merely because a model, controller, sensor, pipeline, or actuator can continue. Computational momentum does not equal physical authority.

This repository serves as the public showroom and deterministic software surface for the **KY-ROX Realization Grammar Architecture**. It isolates speculative execution from state mutability to answer one uncompromising structural question: *When should a candidate be allowed to become consequence?*

---

### ─── The Structural Invariant ───
> $$\text{Candidate} \neq \text{Consequence}$$
> 
> *The resistance of the gate is invariant to the velocity, volume, or confidence of the generator. Admission requires explicit, step-by-step type-progression and authorization; it can never be achieved by omission, timeout, or computational continuation.*

---

### 1. The Core Architecture Loop
Every transition in this architecture is governed by the strict mathematical filter:

$$x_{t+1}=\Omega(\Pi_K(\Phi(x_t)))$$

* **$\Phi$ (Generate):** Fail-open exploration layer. Handles noisy data, high-dimensional proposals, and continuous controller loops.
* **$\Pi_K$ (Project):** Strict kernel projection. Validates structure, type, and computes the projection residual $\Delta_K(x) = \Phi(x) - \Pi_K(\Phi(x))$.
* **$\Omega$ (Gate):** Deterministic evaluation interface (`OPEN` / `HOLD` / `KILL`).

---

### 2. Immutable Node Lifecycle (Type-Progression)
Nodene har en ufravikelig livssyklus. Enhver snarvei eller kortslutning (f.eks. direkte fra RAW til STRUCT utenom ESTIMATE) tolkes som et ontologisk typebrudd og utløser øyeblikkelig terminering til en fail-closed terminal tilstand ($\bot$).

$$\text{RAW} \longrightarrow \text{ESTIMATE} \longrightarrow \text{STRUCT} \longrightarrow \text{VIABILITY} \longrightarrow \text{COMMITTED}$$

* **RAW $(\bullet)$:** Raw event, player/operator input, or telemetry ingress.
* **ESTIMATE $(\diamond)$:** Speculative generation and potential state trajectory.
* **STRUCT $(\Box)$:** Validated data structures, explicit typing, and hash checks.
* **VIABILITY $(\bigcirc)$:** Evaluation against physical constraints, safety bounds, or environment lore.
* **COMMITTED $(\Theta)$:** Admitted transition permanently written to the *Witness Log*.

---

### 3. Demonstrator Scopes Included
This repository contains reference software layouts for checking boundaries across multiple domains:

* **Candidate / Consequence Separation:** Decoupling of state proposals from core execution surfaces.
* **Explicit Gate Semantics:** Programmatic realization of `OPEN` (commit), `HOLD` (freeze/blueprint), and `KILL` (lock/collapse).
* **Fail-Closed Ingress Control:** Immediate drop to a zero-stimuli or zero-action safe state ($\bot$) if boundaries are breached.
* **Witness Discipline:** Hash-chained logging preventing historical data from retroactively altering generator permissions.
* **Deterministic Run Validation:** Manifest verification and cryptographic hash checks for reproducible execution logs.

---

### 4. Target Deployment Contexts
Designed for cyber-physical and autonomous environments where computation cannot be allowed to drift into unsafe physical reality:
* Industrial automation & cyber-physical control loops.
* Autonomous tactical loops and robotic systems.
* Critical grid infrastructure and functional safety boundaries.
* AI-assisted action pipelines requiring runtime governance.

---

### Boundaries of the Claim
* **Not** a safety-certified component.
* **Not** a production interlock.
* **Not** hardware validation (see E-TOR specifications for physical hardware locks).

* **Fail-Open Exploration.**
* **Fail-Closed Consequence.**
