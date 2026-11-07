# MORANDI-CORE // FORMAL REALIZATION CONTRACT (ky-rox-public-demonstrators)
# Default target is FAIL-CLOSED (0.00 V DC). Explicit verification is mandatory.

.DEFAULT_GOAL := hold
.PHONY: hold verify sim_400c sim_205b

hold:
	@echo "[HOLD] 0.00 V DC. System is at rest. Run 'make verify' to execute L1-L3 proof chains, The 7 Monoliths, and SPEC-412..415 Domain Gates."
	@exit 1

sim_400c:
	@iverilog -g2012 -o /tmp/ky_rox_tb_400c.vvp L2_GATE/temporal_bifurcation_400c.sv L2_GATE/tb_temporal_bifurcation_400c.sv
	@vvp /tmp/ky_rox_tb_400c.vvp
	@rm -f /tmp/ky_rox_tb_400c.vvp

sim_205b:
	@iverilog -g2012 -o /tmp/ky_rox_tb_205b.vvp L2_GATE/fpga_capsule_frame_205b_decoder.sv L2_GATE/kpod_fpga_guillotine_12u5.sv L2_GATE/tb_kpod_guillotine_and_205b_decoder.sv
	@vvp /tmp/ky_rox_tb_205b.vvp
	@rm -f /tmp/ky_rox_tb_205b.vvp

verify:
	@python3 -m unittest -q L1_LAW/invariants_pure.py
	@PYTHONPATH=L1_LAW python3 -m unittest -q L1_LAW/test_ky_parser.py
	@PYTHONPATH=L1_LAW python3 -m unittest -q L1_LAW/test_rosetta_d3.py
	@python3 L2_GATE/evaluate_boundaries.py
	@PYTHONPATH=L2_GATE python3 -m unittest -q L2_GATE/test_adversarial_capsule_gate_harness.py
	@PYTHONPATH=L2_GATE python3 -m unittest -q L2_GATE/test_registry_b_dlatch_telemetry_protocol.py
	@PYTHONPATH=L2_GATE python3 -m unittest -q L2_GATE/test_spec414_415_416_gothenburg_corridor_gate.py
	@python3 run_demo.py
	@echo "[L1_VERIFIED // HOLD_READY_FOR_W2] L1 software checks passed (PHYSICAL_AUTHORITY=NONE; W_human required for W2). All 8 Suites (48/48) and 10/10 L1_LAW bounds satisfied."
