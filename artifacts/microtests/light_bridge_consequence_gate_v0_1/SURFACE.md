# LightBridge Consequence Gate — public microtest v0.1

Status: `HOLD`  
Intended repository path: `artifacts/microtests/light_bridge_consequence_gate_v0_1/`

## Scope

This bounded software demonstration exposes the canonical 2D consequence-gate
state machine (`light_bridge.gd` for Godot 4 and its zero-dependency Python
verifier `light_bridge_gate.py`). It verifies five structural invariants:

1. `HOLD` never transitions to `OPEN` merely because time passes.
2. `OPEN` requires a non-empty explicit `evidence_id`.
3. An occupied bridge zone defers, rather than bypasses, realization until clearance.
4. `KILL` disables collision immediately and cancels pending authorization.
5. `reset()` appends to the SHA-256 witness history; it never erases it.

The state-machine verification is `OPEN` when all five invariants pass. The
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
passing tests. Any mismatch is `HOLD`.

## Non-goals

This artifact is not:

- a physical hardware interlock or safety-certified controller;
- physical WORM storage;
- a physical, operational, or commit authority.

`physical_authority=NONE` and `operational_authority=NONE`.
