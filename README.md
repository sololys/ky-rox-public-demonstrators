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

KY-ROX is not presented as a certified safety system, SIL-rated component, or production-ready interlock.

Its industrial relevance is narrower and more foundational: it demonstrates deterministic gate behavior before a candidate is allowed to become consequence.

The public demonstrators are relevant to functional-safety questions such as:

- separating prediction from action
- forcing explicit OPEN / HOLD / KILL decisions
- failing closed instead of allowing unsafe continuation
- detecting rate-of-change escalation before accumulated threshold failure
- preserving reproducible logs, hashes, and manifest discipline
- keeping simulation claims separate from hardware or certification claims

These artifacts do not claim IEC 61508 compliance, SIL certification, hardware validation, regulatory approval, or suitability for deployment in a safety-related system without independent hazard analysis, engineering verification, validation, and certification work.

## Current public demonstrator

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

- patent claims
- production interlock designs
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

## Public rule

Public enough to be inspected.
Bounded enough to protect the core.

Show the gate.
Do not show the lock.
