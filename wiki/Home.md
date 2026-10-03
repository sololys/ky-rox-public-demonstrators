# 🏛️ KY-ROX Public Demonstrators: Verification Portal

Welcome to the **KY-ROX Public Demonstrators** Knowledge Base and Independent Attestation Portal.

* **Repository:** [`sololys/ky-rox-public-demonstrators`](https://github.com/sololys/ky-rox-public-demonstrators)
* **Author:** Marius Egerhei Torjusen (ORCID: [0009-0006-0431-6637](https://orcid.org/0009-0006-0431-6637))
* **Entity:** ReismannPoint Systems AS // Kreativ Systems ([kreativ-systems.org](https://kreativ-systems.org/))
* **Classification:** Public PUNKT Sink // L1 Software Demonstrators (`CLAIM_STATUS=HOLD`)

---

## ⚖️ Governing Separation

All artifacts in this repository operate under an absolute epistemic and operational boundary:

$$\boxed{\mathbf{\text{CANDIDATE\_GENERATION} \neq \text{REALIZED\_CONSEQUENCE}}}$$

```text
PHYSICAL_AUTHORITY     = NONE
OPERATIONAL_AUTHORITY  = NONE
REPOSITORY_STATUS      = HOLD
RELEASE_GATE_STATUS    = OPEN (Bounded Software Only)
```

A software demonstrator may generate or evaluate a candidate, but **it grants no physical, operational, financial, safety, or production authority**. Capability, confidence, repetition, and continued execution do not supply authority.

---

## ⚡ Quickstart: Running the Demonstrator Locally

Clone the repository and run the standalone, zero-dependency fail-closed demonstrator:

```bash
git clone https://github.com/sololys/ky-rox-public-demonstrators.git
cd ky-rox-public-demonstrators
python3 run_demo.py
```

* **Runtime:** `< 0.2 seconds`
* **Requirements:** Standard `python3` with `cryptography` module.
* **Output:** 4 deterministic phases verifying Merkle LCA split-brain resolution and adversarial attack rejection.

---

## 📚 Wiki Navigation

1. **[Brahman.1 Demonstrator Walkthrough](Brahman-1-Demonstrator)**  
   Detailed examination of the 4 execution phases: Canonical baseline, disconnected divergence, Merkle LCA reconciliation (`OPEN`), and fork forgery rejection (`KILL`).

2. **[Third-Party Evaluator Attestation](Third-Party-Attestation)**  
   Formal verification checklist and declaration template for independent evaluators, academic peers, and grant auditors.

3. **[Public Boundary & Claim Doctrine](Public-Boundary-Doctrine)**  
   The **PUNKT // BANE** doctrine, public disclosure restrictions, and the formal definitions of `OPEN`, `HOLD`, and `KILL`.

4. **[Public Microtests](Microtests)**  
   Kernel Drift Observable v0.1: Deterministic synthetic measurement, surface contracts, and pinned SHA-256 checksums.

---

## 🛡️ The PUNKT // BANE Model

| Mode | Public Meaning |
| :--- | :--- |
| **PUNKT** | A frozen, reviewed, and versioned public reference artifact. |
| **BANE** | Exploratory, proprietary, or patent-sensitive work that is **never** hosted in this public repository. |

This repository is a public **PUNKT** sink—not a **BANE** workspace. All material crossing the public boundary is strictly sanitized.
