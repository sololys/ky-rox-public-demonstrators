# Sosionomos XOR/ROX Consequence Gate — public microtest v0.1

Status: `HOLD`  
Intended repository path: `artifacts/microtests/sosionomos_xor_rox_gate_v0_1/`  
Formal specification (`3 · Rule`): [`OMNI_KY_SUSY2_SOSIONOMOS_BRIDGE_SPEC_v1.0.md`](https://github.com/sololys/epistemic-architectures/blob/main/L1_LAW/OMNI_KY_SUSY2_SOSIONOMOS_BRIDGE_SPEC_v1.0.md)

## Scope

This bounded `0 float` software demonstrator implements the **OMNI-KY / Sosionomos XOR-ROX Consequence Gate** using only the Python 3.10+ standard library. It verifies six structural invariants:

1. **Ontological XOR lock:** Active nodes must satisfy `StateCandidate (0x01) ^ RealizedConsequence (0x02) == 1`; illegal superpositions (`0x00`, `0x03`) trigger `KILL`.
2. **Double-pulse XOR involution (`OMNI-KY 4.1`):** Reversible pre-gate testing satisfies `xor64(xor64(w, k), k) == w`; any mutated return mask (`MASK_MUTATED`) triggers `KILL`.
3. **Non-involutive ROX directional seal:** `OPEN` breaks reversibility via `rox64(w, k, r) = ROTL_64(w ^ k, r)`, promoting `0x01 -> 0x02` into `PublicDAG` and the append-only SHA-256 `WitnessLedger`.
4. **Agency-preserving `HOLD`:** High excitation triggers an exact integer LUT delay (`0 float`) without advancing `sequence_counter`, allowing `wait`, `revise`, or `narrow` without head-of-line deadlock.
5. **Mechanical backpressure & `TRAP` isolation:** Saturated arenas (`rho >= 3/4` -> `read_permit = 0`; `rho >= 9/10` -> `TRAP`) route adversarial actors silently into an isolated `ShadowDAG` (`local ACK != public consequence`).
6. **Thermodynamic cooling (`HOT -> WARM -> COLD`):** Payload cools while hash and `O(1)` `AnchorIndex` survive intact for future children.

## Run

```bash
python3 sosionomos_xor_rox_gate.py
python3 -m unittest -v test_sosionomos_xor_rox_gate.py
sha256sum -c CHECKSUMS.sha256
```

The first command must match `EXPECTED_OUTPUT.txt`. The tests must report six passing tests (`6/6 PASS`). Any mismatch is `HOLD`.

## Non-goals

This artifact is not:

- a production social network or moderation service;
- physical WORM storage or hardware interlock;
- a physical, operational, or commit authority.

`physical_authority=NONE` and `operational_authority=NONE`.
