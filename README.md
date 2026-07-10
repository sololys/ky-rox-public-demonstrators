# ky-rox-public-demonstrators: Fail-Closed Realization Architecture

**Prediction is not action.**

A generated candidate must never become a realized consequence merely because a model, controller, sensor, pipeline, or actuator can continue. Computational momentum does not equal physical authority.

This repository is the public showroom and deterministic software surface for the **KY-ROX Realization Grammar Architecture**. It isolates speculative execution from state mutability to answer one structural question:

> When may a candidate become an authorized software result, and what additional boundary is required before irreversible consequence?

---

## The structural invariant

> $$\text{Candidate} \neq \text{Consequence}$$

The resistance of the gate is invariant to the velocity, volume, or confidence of the generator. Admission requires explicit type progression and authorization; it cannot be achieved by omission, timeout, or computational continuation.

---

## 1. Core architecture loop

Every evaluated transition follows:

$$x_{t+1}=\Omega(\Pi_K(\Phi(x_t)))$$

- **$\Phi$ — Generate:** explores noisy data, proposals, and possible trajectories.
- **$\Pi_K$ — Project:** validates structure, type, boundaries, and invariants.
- **$\Omega$ — Gate:** returns the deterministic decision `OPEN`, `HOLD`, or `KILL`.

```text
OPEN = passage to a bounded software result
HOLD = preserved candidate requiring re-admission
KILL = rejected candidate / no passage
```

`HOLD` is never delayed `OPEN`.

---

## 2. Immutable type progression

```text
RAW
→ ESTIMATE
→ STRUCT
→ VIABILITY
→ SIM_AUTHORIZED
→ explicit COMMIT boundary
→ WITNESS
```

- **RAW:** event, operator input, telemetry, or proposal ingress.
- **ESTIMATE:** speculative generation and candidate trajectory.
- **STRUCT:** validated types, data structures, and integrity checks.
- **VIABILITY:** bounded evaluation against declared constraints.
- **SIM_AUTHORIZED:** permission for an explicit, bounded software result.
- **COMMITTED:** used only when a separately authorized irreversible transition actually occurs.
- **WITNESS:** downstream history of the evaluated or committed event.

Any shortcut across a required stage is a type violation and must fail closed.

```text
OPEN != COMMITTED
SIM_AUTHORIZED != PHYSICAL_ACTION
WITNESS != AUTHORITY
```

---

## 3. Demonstrator scopes

This repository contains public reference layouts for:

- candidate/consequence separation;
- deterministic `OPEN/HOLD/KILL` gates;
- fail-closed input handling;
- bounded simulation results;
- hash-linked trace and witness principles;
- deterministic replay, manifests, and reproducible run logs;
- read-only terminal observability surfaces.

The public demonstrators do not expose protected interlock details, private thresholds, production witness internals, or unpublished core algorithms.

---

## 4. Intended research contexts

The architecture is relevant to systems where computation must not silently become external action, including:

- industrial and cyber-physical control research;
- robotics and autonomous-system simulation;
- critical-infrastructure governance models;
- AI-assisted action pipelines;
- developer tooling for typed authorization and audit.

---

## Claim and authority boundary

These artifacts are:

- deterministic software demonstrators;
- architectural and research instruments;
- local test surfaces.

They are not:

- safety-certified components;
- production interlocks;
- deployed hardware controllers;
- empirical validation of new physics;
- autonomous physical authority.

```text
FAIL_OPEN_EXPLORATION=ALLOWED
FAIL_CLOSED_CONSEQUENCE=REQUIRED
NO_COMMIT_BY_DEFAULT=TRUE
PHYSICAL_AUTHORITY=NONE
```
