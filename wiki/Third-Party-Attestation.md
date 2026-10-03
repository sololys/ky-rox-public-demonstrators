# 📜 Third-Party Evaluator Attestation

Reference Template: [`DEMO_ATTEST_MAL.md`](https://github.com/sololys/ky-rox-public-demonstrators/blob/main/DEMO_ATTEST_MAL.md)

---

## 🎯 Purpose of Independent Attestation

This attestation provides formal documentation of **independent, third-party verified software behavior on the evaluator's own compute environment**. It establishes an empirical witness that the software invariants hold deterministically without relying on remote network claims.

> [!NOTE]
> This attestation establishes one local reproduction of the L1 software demonstrator. It does not establish general correctness, production readiness, physical interlocks, or physical immunity outside the declared software model.

---

## 📋 Evaluation Checklist

When evaluating `run_demo.py`, record observations against the four canonical invariants:

| # | Invariant | Required Terminal Observation | Verification Status |
| :-: | :--- | :--- | :-: |
| **1** | **Rejection of Last-Write-Wins (LWW)** | Both disconnected nodes record distinct local events without data loss or clock-based overwriting. | `[x] PASS` |
| **2** | **Logarithmic Merkle-LCA Search** | Lowest Common Ancestor is located deterministically in $\mathcal{O}(\log N)$ rounds without transmitting full histories. | `[x] PASS` |
| **3** | **Fail-Closed Consequence Gate (HOLD ➔ OPEN)** | Legitimate divergence clamps to `GATE::HOLD (0.00 V)` until bilateral signed merge authorizes `GATE::OPEN (5.00 V)`. | `[x] PASS` |
| **4** | **Tamper & Fork Rejection (KILL)** | Invalid hash linkage or corrupted signature triggers `GATE::KILL (0.00 V)` with exactly 0 bytes committed to the canonical ledger. | `[x] PASS` |

---

## ✍️ Attestation Statement Template

Evaluators may copy and fill out this declaration:

```markdown
### DECLARATION OF THIRD-PARTY REPRODUCTION

I hereby confirm that I have cloned the source repository, executed `python3 run_demo.py`
on my own isolated environment, and observed that the four fail-closed invariants
executed deterministically as specified.

* Evaluator Name: __________________________________________________
* Title / Role: __________________________________________________
* Institution / Organization: __________________________________________________
* Verification Date: __________________________________________________
* OS & Python Version: __________________________________________________
* Overall Verdict: [ ] PASS (100% Deterministic)   [ ] FAIL

Evaluator Observation Notes:
> __________________________________________________________________________________________
> __________________________________________________________________________________________

Signature: ______________________________________
```
