# KY-ROX Public Demonstrators

This repository contains public-facing demonstrators from the KY-ROX / Realization Grammar architecture.

This is the admitted public surface.

It is not a reduced version of the project.
It is not the protected implementation core.

The purpose is to make the architecture inspectable without making the protected core extractable.

## What this repository shows

- deterministic microtests
- reproducible run logs
- manifest/hash discipline
- high-level realization grammar
- simulated gate behavior
- bounded claim levels

## What this repository does not disclose

- patent claims
- production interlock designs
- deployment thresholds
- hardware safety implementation
- private witness records
- unreleased experimental protocols
- confidential architecture notes
- operational parameters for real systems

## Current public artifact

### CPS Derivative Gate v0.1

Status: SOFTWARE SIMULATION / DETERMINISTIC MICROTEST / PASS / HASH VERIFIED

Core result:

- KY-ROX derivative gate HOLD: 8.7s
- KY-ROX derivative gate KILL: 8.9s
- baseline threshold gate KILL: 9.6s
- observed KILL lead time: 0.7s
- irreversibility budget saved at KY-ROX KILL: 0.468273

Boundary:

This artifact demonstrates simulated gate behavior.
It does not constitute physical validation, hardware enforcement, product certification, or production safety design.

## Claim level

Software simulation unless explicitly stated otherwise.

## Rule

Public enough to be inspected.
Bounded enough to protect the core.

Show the gate.
Do not show the lock.
