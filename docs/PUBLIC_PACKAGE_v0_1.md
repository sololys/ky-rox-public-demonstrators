# KY–ROX Public Demonstrator Package v0.1

This document presents the public surface of KY–ROX: a deterministic demonstrator for separating candidates from consequences in fail-closed control architecture.

The package is built around one rule:

> A generated candidate must not become a realized consequence without passing through an explicit gate.

The gate has three public outcomes:

- OPEN: the candidate is admissible and may proceed
- HOLD: the candidate is not authorized, but not terminated
- KILL: the candidate violates a boundary and must be stopped

The purpose of this public package is to make the architecture inspectable without exposing private implementation details, patent-sensitive material, hardware thresholds, or deployment boundary design.

## What this is not

This public package is not a safety certification system.

It is not a deployment boundary.

It is not a hardware validation report.

It is not a protected claim material.

It is not a claim that the demonstrated software alone can safely control physical infrastructure.

It is not a replacement for laboratory testing, regulatory review, hardware redundancy, formal verification, or independent safety assessment.

The package should be read as an architectural and deterministic software demonstrator.

Its purpose is to show the separation between candidate generation, admissibility checking, consequence gating, and witness logging.

## Next verification steps

The next verification steps are intentionally narrow.

### 1. Public software consistency

Verify that each demonstrator:

- runs deterministically
- has clear OPEN / HOLD / KILL semantics
- produces inspectable output
- does not claim physical safety validation

### 2. Witness discipline

Verify that decision records are append-only in spirit, reproducible, and separated from the candidate generator.

### 3. Claim boundary review

Review all public language to ensure the package is framed as a demonstrator, not as a production system.

### 4. External review preparation

Prepare a short external note for technical reviewers explaining:

- what the package demonstrates
- what it does not demonstrate
- what kind of review is requested

### 5. Later-stage hardware path

Only after software and claim boundaries are stable should the architecture be mapped toward hardware interlock design, lab testing, FPGA/PLC constraints, or safety certification processes.

## Related files

- `../STATUS_PUBLIC.md`
- `../CLAIM_LEVELS.md`
