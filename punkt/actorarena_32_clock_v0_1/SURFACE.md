# Public surface

## Included

- 32 integer actor positions;
- exact-position zero-window admission;
- visible `OPEN`, `HOLD`, `KILL`, and terminal `REJECTED` outcomes;
- fail-closed state behavior;
- a local append-only SHA-256 witness chain for realized demo events;
- deterministic tests and expected output.

## Excluded

- protected architecture and production decision logic;
- operational thresholds, identity policy, authorization policy, or credentials;
- hardware mappings, interlocks, networking, persistence, or deployment;
- patent-sensitive mechanisms and private witness formats;
- claims of safety certification or physical validation.

The clock is a public explanatory geometry. It is not a scheduler, access-control
system, or authorization service.
