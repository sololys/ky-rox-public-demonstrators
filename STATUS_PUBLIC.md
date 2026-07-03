# KY–ROX Public Demonstrator Status

Status: PUBLIC DEMONSTRATOR / NOT PRODUCTION SAFETY SYSTEM

KY–ROX is a public demonstrator package for a fail-closed control architecture.

The core distinction is:

- candidate generation is not consequence
- analysis is not authorization
- OPEN requires explicit admissibility
- HOLD preserves non-action
- KILL terminates unsafe paths
- witness records preserve decision history

This repository demonstrates the structural separation between:

1. candidate generation
2. admissibility projection
3. consequence gating
4. witness logging

It does not claim to be a safety certification system, a deployment boundary, a hardware design, or a validated physical control product.

The current package is suitable for public review, architectural discussion, software demonstration, and early-stage verification planning.
