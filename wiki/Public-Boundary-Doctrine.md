# 🛡️ Public Boundary & Claim Doctrine

Authoritative Contracts:
* [`PUBLIC_BOUNDARY.md`](https://github.com/sololys/ky-rox-public-demonstrators/blob/main/PUBLIC_BOUNDARY.md)
* [`punkt/contracts/claim-levels.md`](https://github.com/sololys/ky-rox-public-demonstrators/blob/main/punkt/contracts/claim-levels.md)
* [`punkt/contracts/candidate-not-consequence.md`](https://github.com/sololys/ky-rox-public-demonstrators/blob/main/punkt/contracts/candidate-not-consequence.md)

---

## 🏛️ The PUNKT // BANE Separation

This repository is strictly designated as a **PUNKT** sink:

* **PUNKT:** A frozen, reviewed, and versioned public reference artifact.
* **BANE:** Exploratory work, active prototypes, and unreleased intellectual property that are **not** hosted in this repository.

> *A public branch is still public. Draft status does not create confidentiality.*

---

## 🔒 What Belongs in Public vs. What Is Prohibited

### Permitted in this Repository:
* Sanitized demonstrator source code.
* Deterministic public test fixtures and expected terminal outputs.
* Cryptographic release attestations and SHA-256 checksum manifests.
* Public-facing documentation, schemas, and architectural diagrams.

### Strictly Prohibited (Must Never Merge Here):
* Protected core architecture, proprietary algorithms, or closed control logic.
* Operational thresholds, decision tables, or production calibrations.
* Hardware interlock mappings or physical actuator pinouts.
* Internal audit-chain schemas or private ledger implementations.
* Patent-sensitive mechanisms or active IP applications.
* References to private repositories, credentials, or internal deployment parameters.

---

## 🚦 Claim Levels: OPEN, HOLD, KILL

### `OPEN`
* The artifact is a bounded software demonstrator.
* Its declared test can be reproduced deterministically for the exact revision.
* Its output may be reported as a software result within the declared test surface.
* **Its authority ends at the software boundary.**

### `HOLD`
* Production suitability claims.
* Physical hardware or safety claims.
* Generalization beyond the documented test surface.
* Scientific or physical interpretations without separate external lab validation.
* Any transition from candidate output to external consequence.

### `KILL`
* Treating a demonstrator result as physical or operational authorization.
* Presenting an uncertified software artifact as a safety component.
* Publishing protected implementation material through a public path.
* Claiming that an `OPEN` software verdict establishes production, scientific, or physical validity.
