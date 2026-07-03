# KY-ROX Public Demonstrators

Fail-open exploration. Fail-closed consequence.

KY-ROX is a realization-grammar architecture for systems where generated candidates must be separated from realized consequences.

In many cyber-physical systems, the dangerous step is not prediction.
The dangerous step is when prediction becomes action.

KY-ROX focuses on that boundary.

Core question:

When should a candidate be allowed to become consequence?

This repository contains public demonstrators that make that question inspectable through deterministic software tests, reproducible run logs, and manifest/hash discipline.

## Why this matters

Modern systems increasingly combine prediction, automation, and physical action.

That creates a hard boundary problem:

- an AI model can suggest
- a controller can compute
- a sensor can report
- a pipeline can trigger
- an actuator can execute

But a suggestion is not a consequence.

KY-ROX treats execution as an admitted transition, not as a natural continuation of computation.

## Core principle

Candidate != Consequence

A candidate may be explored freely.

A consequence must pass the gate.

## Application areas

KY-ROX is relevant to domains where unsafe or irreversible actions must be blocked before they become real-world consequences.

Potential application areas include:

- cyber-physical systems
- grid and infrastructure control
- AI-assisted automation
- robotics and autonomous systems
- industrial safety interlocks
- process control
- aerospace and launch sequencing
- audit-driven control systems
- deterministic runtime governance
- safety-critical decision pipelines

This repository does not claim production readiness in these domains.
It provides public, reproducible demonstrators of the underlying gate logic.

## Functional safety relevance, not certification

KY-ROX is not presented as a safety certification system, SIL-rated component, or production-ready interlock.

Its industrial relevance is narrower and more foundational: it demonstrates deterministic gate behavior before a candidate is allowed to become consequence.

The public demonstrators are relevant to functional-safety questions such as:

- separating prediction from action
- forcing explicit OPEN / HOLD / KILL decisions
- failing closed instead of allowing unsafe continuation
- detecting rate-of-change escalation before accumulated threshold failure
- preserving reproducible logs, hashes, and manifest discipline
- keeping simulation claims separate from hardware or certification claims

These artifacts do not claim IEC 61508 compliance, SIL certification, hardware validation, regulatory approval, or suitability for deployment in a safety-related system without independent hazard analysis, engineering verification, validation, and certification work.

## Current public demonstrators

### KY-Gate Admissible Learning Simulator v0.1

An interactive React simulator for admissible learning.

It demonstrates:

- Candidate != Realized Experience
- RAW -> ESTIMATE -> STRUCT -> GATE type progression
- ternary Omega / Omega_Q decisions: OPEN, HOLD, KILL
- HOLD/QHOLD as re-admission discipline, not delayed OPEN
- Witness Ledger admission for validated experience only
- QML-style residual leakage monitoring r_A(rho)

Path:

```text
apps/ky-gate-admissible-learning-simulator/
```

### CPS Derivative Gate v0.1

A deterministic software microtest comparing two safety logics in the same simulated grid-overload event.

Baseline gate:

R(t) >= R_LIMIT

KY-ROX derivative gate:

dR/dt >= DELTA_R

## Verified result

KY-ROX derivative gate HOLD: 8.7s
KY-ROX derivative gate KILL: 8.9s
Baseline threshold gate KILL: 9.6s

Observed KILL lead time: 0.7s
Irreversibility budget saved at KY-ROX KILL: 0.468273

RESULT=PASS

## What this demonstrates

The microtest shows that derivative-gating can detect simulated irreversible escalation before ordinary accumulated-threshold gating in the same deterministic CPS event.

Public point:

Do not wait only for damage level.
Watch the rate at which consequence becomes irreversible.

Path:

```text
artifacts/microtests/cps_derivative_gate_v0_1/
```

### Interval Kill-Switch with Memory v0.1

A deterministic software microtest for fail-closed interval gating with accumulated stress memory.

It demonstrates:

- stable persistence remains admissible
- boundary drift triggers HOLD
- accumulated latent stress triggers KILL
- a trajectory is not rejected merely because it continues

Path:

```text
artifacts/microtests/interval_killswitch_memory_v0_1/
```

Claim boundary:

This is a public software demonstrator of gate semantics, not a physical safety validation system, product certification, or deployment boundary design.

## What this repository shows

- deterministic microtests
- reproducible run logs
- manifest/hash verification
- bounded claim levels
- simulated gate behavior
- public-facing realization-grammar concepts

## What this repository protects

This repository is the public surface, not the protected implementation core.

It does not disclose:

- protected claim material
- deployment boundary designs
- deployment thresholds
- hardware safety implementation
- private witness records
- unreleased experimental protocols
- confidential architecture notes
- operational parameters for real systems

## Claim level

Unless explicitly stated otherwise, artifacts in this repository are:

SOFTWARE SIMULATION
DETERMINISTIC MICROTEST
PUBLIC DEMONSTRATOR

They are not:

PHYSICAL VALIDATION
PRODUCT CERTIFICATION
PRODUCTION SAFETY DESIGN
HARDWARE ENFORCEMENT PROOF

## Repository structure rule

Small public notes should live under `docs/` as consolidated documents.

Artifact folders should be used only when a demonstrator needs multiple files: code, run logs, manifests, hashes, fixtures, or packaged outputs.

## Public rule

Public enough to be inspected.
Bounded enough to protect the core.

Show the gate.
Do not show the lock.

## Public Demonstrator Package

See `STATUS_PUBLIC.md` and `docs/PUBLIC_PACKAGE_v0_1.md` for the current public demonstrator package.

This package presents KY–ROX as a deterministic software demonstrator for candidate/consequence separation, OPEN/HOLD/KILL gating, and witness discipline.

It is not a safety certification system, a deployment boundary, a hardware validation report, or a claim of physical safety certification.

# KY–ROX Consequence Gate v1.0
**Deterministic Consequence Selection Layer for Autonomous Systems & AI Action Pipelines.**

## The Core Axiom
> *Reality is not generated. Reality is admitted.*

As autonomous agents, Large Language Models (LLMs), and complex stochastic control systems transition from passive dashboards to active environments, they introduce a critical vulnerability: **Consequence Leakage**. Traditional architectures lack a fail-closed boundary that separates a generated proposal from a realized, irreversible transaction.

**KY–ROX Consequence Gate** inserts a formal, deterministic execution barrier between the generative engine ($\Phi$) and downstream action layers, enforcing structural admissibility before any state mutation can be treated as historical consequence.

---

## Architectural Stack Map

The runtime sequence guarantees that no candidate proposal can derive authority from its own persistence or optimization score. Every action must traverse a strict, one-way pipeline:

# KY-ROX Shadow Gate — Release Pathway Demonstrator v0.1

Dette dokumentet definerer de operasjonelle grensene og den konseptuelle arkitekturen for `release_pathway_shadow_gate_v0_1`.

## 1. Definerte Grenser (Strict Boundaries)
* **Ikke en fysikkmodell:** Systemet verifiserer eller beviser ikke astrofysiske fenomener (ASKAP J1832−0911), molekylærstrukturer (D₂) eller krumningsteori (SICS/UC3). Disse brukes utelukkende som eksterne strukturelle analogier for å illustrere selektive slippveier under geometrisk tvang.
* [cite_start]**Ikke en finansiell utførelsesmotor:** Demonstratoren simulerer rutinglogikk, men utfører ikke reelle pengetransaksjoner[cite: 684, 790].
* [cite_start]**Strukturell port-demonstrator:** Fokus ligger eksklusivt på den formelle adskillelsen mellom generert sårbarhet (energi/kandidat til stede) og autorisert realisering (åpen konsekvensport)[cite: 7, 8, 659].

## 2. Portvaktens Formelle Admisjonslogikk
[cite_start]Konsekvens oppstår ikke fordi systemet har kapasitet eller energi til å handle[cite: 99]. Det må finnes en formelt autorisert og validert slippvei. Porten evaluerer overgangen basert på følgende unike kriteria:

$$OPEN \iff R(c_t) \in R_{\text{allowed}} \land M(c_t) \geq M_{\min} \land S_T(c_t) \leq S_{\max} \land W = \text{READY}$$

* $R(c_t)$: Observert og kartlagt slippvei (Release Pathway).
* [cite_start]$M(c_t)$: Midtbåndsundertrykkelse (Suppressed Leakage) for å hindre uønsket konsekvenslekkasje[cite: 622].
* $S_T(c_t)$: Timing-stabilitet (Jitter/Drift-kontroll).
* $W = \text{READY}$: Witness-forseglingsklarhet. [cite_start]Systemet må beviselig kunne loggføre hendelsen kryptografisk før porten åpnes[cite: 36, 82, 132, 496].

## 3. Konseptuell Bro (External Structural Source)
Vi integrerer Pickard-Jones' kjerne-tese som en konseptuell oversettelsesnøkkel:
> "Energy does not become radiance merely because energy is present; energy becomes radiance when structure permits expression."

I KY-ROX betyr dette:
$$\Phi \neq COMMIT$$
[cite_start]Generert energi (kandidater) mister sin suverenitet i møte med porten[cite: 5, 141]. [cite_start]Kun strukturelt tillatte og bevitnede kanaler konverteres til realisert virkning[cite: 5, 108, 109].
