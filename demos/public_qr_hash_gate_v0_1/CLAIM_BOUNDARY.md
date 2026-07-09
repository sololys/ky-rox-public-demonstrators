# Claim Boundary — Public QR Hash Gate v0.1

This demonstrator is safe for the public repository because it contains only generic verification mechanics:

```text
payload -> parse -> hash target -> compare -> OPEN / HOLD / KILL
```

It does not include:

- private target documents
- internal payloads
- protected thresholds
- hardware interlock details
- production safety claims
- proprietary witness internals
- certification claims

## Public claim

```text
A decoded QR or payload can point to a target artifact.
The gate opens only when the local target file hash matches the declared digest.
```

## Non-claims

```text
This is not encryption.
This is not a safety-certified component.
This is not proof that any external artifact is authentic.
This does not authorize physical action.
```

FINAL_SEAL=PUBLIC_SURFACE_ONLY
