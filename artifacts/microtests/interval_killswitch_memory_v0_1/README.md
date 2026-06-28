# Interval Kill-Switch with Memory v0.1

This is not a physical safety validation system.
It is a deterministic demonstrator of fail-closed interval gating with memory.

The demonstrator separates:
- candidate action
- interval evaluation
- accumulated stress memory
- consequence authorization

A persistent trajectory is not rejected merely because it persists.
It is rejected only when boundary violation, dangerous drift, or accumulated latent stress breaks admissibility.
