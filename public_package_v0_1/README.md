# KY–ROX Public Demonstrator Package v0.1

This package presents the public surface of KY–ROX: a deterministic demonstrator for separating candidates from consequences in fail-closed control architecture.

The package is built around one rule:

> A generated candidate must not become a realized consequence without passing through an explicit gate.

The gate has three public outcomes:

- OPEN: the candidate is admissible and may proceed
- HOLD: the candidate is not authorized, but not terminated
- KILL: the candidate violates a boundary and must be stopped

The purpose of this package is to make the architecture inspectable without exposing private implementation details, patent-sensitive material, hardware thresholds, or production interlock design.

See:

- WHAT_THIS_IS_NOT.md
- NEXT_VERIFICATION_STEPS.md
- ../CLAIM_LEVELS.md
- ../STATUS_PUBLIC.md
