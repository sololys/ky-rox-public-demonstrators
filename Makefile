# MORANDI-CORE // FORMAL REALIZATION CONTRACT (ky-rox-public-demonstrators)
# Default target is FAIL-CLOSED (0.00 V DC). Explicit verification is mandatory.

.DEFAULT_GOAL := hold
.PHONY: hold verify

hold:
	@echo "[HOLD] 0.00 V DC. System is at rest. Run 'make verify' to execute L1-L3 proof chains and The Four Monoliths."
	@exit 1

verify:
	@python3 -m unittest -q L1_LAW/invariants_pure.py
	@python3 L2_GATE/evaluate_boundaries.py
	@python3 run_demo.py
	@echo "[L1_VERIFIED // HOLD_READY_FOR_W2] L1 software checks passed (PHYSICAL_AUTHORITY=NONE; W_human required for W2). All 5 Monoliths (30/30) and public surface bounds satisfied."
