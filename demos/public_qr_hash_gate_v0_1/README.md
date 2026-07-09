# Public QR Hash Gate v0.1

Claim-controlled public demonstrator for QR/payload hash verification.

This is the public surface extracted after the private verifier was merged. It does not publish private document names, target artifacts, protected payloads, thresholds, interlock details, or witness internals.

## Gate rule

```text
scan does not authorize; hash match authorizes.
```

A QR scan or decoded payload is only a pointer. The gate opens only when a local target file exists and its SHA-256 digest matches the declared digest in the payload.

## Pipeline

```text
payload text
  -> parse Document + Canonical Entry + SHA-256 + Status
  -> hash target file
  -> compare declared digest with actual digest
  -> OPEN / HOLD / KILL
```

## Semantics

```text
OPEN = structurally complete payload + target exists + SHA-256 matches
HOLD = structurally incomplete payload or target file is absent
KILL = malformed SHA-256 or target hash mismatch
```

## Local use

```bash
python3 public_qr_hash_gate.py --payload-file sample_payload.txt --target example_target.txt
```

Expected behavior when `example_target.txt` is absent:

```text
DECISION=HOLD
REASON=TARGET_MISSING
```

Run tests:

```bash
python3 test_public_qr_hash_gate.py
```

## Boundary

This is not encryption, not certification, not a production safety component, and not a claim that a scanned QR object is itself authoritative. It is a deterministic public demonstration of candidate/consequence separation: decode is not acceptance; hash match is the admissibility event.

FINAL_SEAL=PUBLIC_QR_HASH_GATE_V0_1_CLAIM_CONTROLLED
