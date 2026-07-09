# Commercial Claim Boundary — Public QR Hash Gate v0.1

This demonstrator is safe for the public repository because it contains only generic verification mechanics:

```text
payload -> parse -> hash target -> compare -> OPEN / HOLD / KILL
```

## Commercial positioning

This is a public evaluation pattern for organizations that need a clear separation between a candidate artifact and an accepted consequence.

It can be used to discuss and demonstrate:

- document/package integrity checks before workflow acceptance
- audit-friendly OPEN/HOLD/KILL decision semantics
- fail-closed handling of missing or mismatched evidence
- deterministic verification that can run in CI
- buyer-facing proof-of-concept conversations around artifact gates
- integration patterns for governance, QA, review, or release pipelines

The commercial value is not that a QR scan is trusted. The value is that the scan or payload is treated only as a pointer, and acceptance requires a local hash match against the target artifact.

## Safe buyer-facing claim

```text
A decoded QR or payload can point to a target artifact.
The gate opens only when the local target file hash matches the declared digest.
Missing evidence stays HOLD. Conflicting evidence becomes KILL.
```

## Public surface only

This PR does not include:

- private target documents
- internal payloads
- protected thresholds
- hardware interlock details
- production safety claims
- proprietary witness internals
- certification claims
- customer data
- deployment secrets

## Commercial non-claims

```text
This is not encryption.
This is not a safety-certified component.
This is not proof that any external artifact is authentic.
This is not a complete security product.
This does not certify regulatory compliance.
This does not authorize physical action.
```

## Product boundary

```text
OPEN  = public demonstrator / evaluation pattern
HOLD  = production product, certification, customer deployment, or regulated use
KILL  = claims that QR decode alone proves authenticity or authorizes action
```

FINAL_SEAL=COMMERCIAL_PUBLIC_SURFACE_ONLY
