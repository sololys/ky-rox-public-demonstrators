# LightBridge Consequence Gate — public microtest v0.1

Status: `HOLD`  
Intended repository path: `artifacts/microtests/light_bridge_consequence_gate_v0_1/`

## Scope

This bounded software demonstration exposes the canonical 2D consequence-gate
state machine (`light_bridge.gd` for Godot 4 and its zero-dependency Python
verifier `light_bridge_gate.py`). It verifies seven structural invariants:

1. **No silent `HOLD`:** `set_to_hold()` requires a non-empty `delta_k` rationale; empty rationale is rejected and escalates jurisdiction to `P_EXT` at `0.00 V`.
2. **Dual-Clock Law:** `HOLD` never transitions to `OPEN` merely because time passes (`d/dt HOLD = 0`); stalling past `hold_tau_max` forfeits internal jurisdiction (`P_INT -> P_EXT`), purges any pending clearance warrant, and keeps the gate de-energized (`0.00 V`).
3. **Explicit evidence:** `OPEN` requires a non-empty explicit `evidence_id`.
4. **Occupancy clearance:** An occupied bridge zone defers, rather than bypasses, realization until clearance.
5. **Gate-capture guard:** Asymmetric consequence rules (`Omega_1 != Omega_2`) trigger sticky `KILL_GATE_CAPTURE`, disabling collision immediately and cancelling pending authorization.
6. **Append-only reset:** `reset()` appends to the SHA-256 witness history; it never erases it.
7. **Hash-chain verification:** `verify_witness_chain()` recomputes every SHA-256 link from genesis.

The state-machine verification is `OPEN` when all invariants pass. The
overall claim remains `HOLD`: modeled software states (`0.00 V` / `5.00 V`) and
append-only hash chains do not establish physical hardware interlocks or
physical WORM media.

## Run

```bash
python light_bridge_gate.py
python -m unittest -v test_light_bridge_gate.py
sha256sum -c CHECKSUMS.sha256
```

The first command must match `EXPECTED_OUTPUT.txt`. The tests must report six
passing tests (`6/6 PASS`). Any mismatch is `HOLD`.

## Non-goals

This artifact is not:

- a physical hardware interlock or safety-certified controller;
- physical WORM storage;
- a physical, operational, or commit authority.

`physical_authority=NONE` and `operational_authority=NONE`.
