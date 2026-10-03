# 🧪 Public Microtests

Location: [`artifacts/microtests/`](https://github.com/sololys/ky-rox-public-demonstrators/tree/main/artifacts/microtests)

Public microtests are small, self-contained, reproducible test surfaces designed to demonstrate deterministic software behavior with zero external dependencies.

---

## 🔬 Microtest 1: Kernel Drift Observable v0.1

* **Artifact Path:** `artifacts/microtests/kernel_drift_observable_v0_1/`
* **Specification:** [`SURFACE.md`](https://github.com/sololys/ky-rox-public-demonstrators/blob/main/artifacts/microtests/kernel_drift_observable_v0_1/SURFACE.md)
* **Scope:** Deterministic synthetic measurement of kernel drift.
* **Status:** Measurement `OPEN`, Research claim `HOLD`, Physical and operational authority `NONE`.

### Execution Command:
```bash
python3 artifacts/microtests/kernel_drift_observable_v0_1/test_kernel_drift.py
```

### Reproducing a Release:
1. Read the artifact's `SURFACE.md`.
2. Run its documented test command.
3. Compare the terminal output against `EXPECTED_OUTPUT.txt`.
4. Verify checksums against `CHECKSUMS.sha256`.
5. Treat any mismatch as `HOLD`.

---

## 🛠️ Automated Surface Verification Tool

Run the repository-level integrity scanner to verify that all tracked files satisfy the public boundary:

```bash
python3 tools/verify_public_surface.py
```

### Expected Output:
```text
PUBLIC_TREE_GATE=PASS
MICROTEST_GATE=PASS
TRACKED_FILES=25
SCOPE=EXACT_CHECKED_TREE_ONLY
RELEASE_GATE_STATUS=OPEN
ARTIFACT_STATUS=RELEASE_CANDIDATE
CLAIM_STATUS=HOLD
REPOSITORY_STATUS=HOLD
PHYSICAL_AUTHORITY=NONE
OPERATIONAL_AUTHORITY=NONE
```
