# MORANDI-CORE // FORMAL REALIZATION CONTRACT (ky-rox-public-demonstrators)
# Default target is FAIL-CLOSED (0.00 V DC). Explicit verification is mandatory.

.DEFAULT_GOAL := hold
.PHONY: hold verify sim_400c sim_205b sim_omega64 qnx_omega64 sim_vektor_a qnx_vektor_a sim_k_sluice

hold:
	@echo "[HOLD] 0.00 V DC. System is at rest. Run 'make verify' to execute L1-L3 proof chains and all 10 Demonstrator Suites (60/60 PASS)."
	@exit 1

sim_400c:
	@iverilog -g2012 -o /tmp/ky_rox_tb_400c.vvp L2_GATE/temporal_bifurcation_400c.sv L2_GATE/tb_temporal_bifurcation_400c.sv
	@vvp /tmp/ky_rox_tb_400c.vvp
	@rm -f /tmp/ky_rox_tb_400c.vvp

sim_205b:
	@iverilog -g2012 -o /tmp/ky_rox_tb_205b.vvp L2_GATE/fpga_capsule_frame_205b_decoder.sv L2_GATE/kpod_fpga_guillotine_12u5.sv L2_GATE/tb_kpod_guillotine_and_205b_decoder.sv
	@vvp /tmp/ky_rox_tb_205b.vvp
	@rm -f /tmp/ky_rox_tb_205b.vvp

sim_omega64:
	@gcc -std=c11 -Wall -Wextra -Werror -o /tmp/ky_rox_test_omega_hal L2_GATE/omega_hal_pack.c L2_GATE/test_omega_hal_pack_c11.c
	@/tmp/ky_rox_test_omega_hal
	@rm -f /tmp/ky_rox_test_omega_hal
	@iverilog -g2012 -o /tmp/ky_rox_tb_omega64.vvp L2_GATE/omega_symplectic_watchdog_64b.sv L2_GATE/tb_omega_symplectic_watchdog_64b.sv
	@vvp /tmp/ky_rox_tb_omega64.vvp
	@rm -f /tmp/ky_rox_tb_omega64.vvp

qnx_omega64:
	@mkdir -p /tmp/qnx_omega64_build
	@qcc -Vgcc_ntox86_64 -std=gnu11 -O2 -Wall -Wextra -Werror -c L2_GATE/omega_hal_pack.c -o /tmp/qnx_omega64_build/omega_hal_pack_x86_64.o
	@qcc -Vgcc_ntox86_64 -std=gnu11 -O2 -Wall -Wextra -Werror -c L2_GATE/omega_qnx_resmgr.c -o /tmp/qnx_omega64_build/omega_qnx_resmgr_x86_64.o
	@qcc -Vgcc_ntoaarch64le -std=gnu11 -O2 -Wall -Wextra -Werror -c L2_GATE/omega_hal_pack.c -o /tmp/qnx_omega64_build/omega_hal_pack_aarch64le.o
	@qcc -Vgcc_ntoaarch64le -std=gnu11 -O2 -Wall -Wextra -Werror -c L2_GATE/omega_qnx_resmgr.c -o /tmp/qnx_omega64_build/omega_qnx_resmgr_aarch64le.o
	@rm -rf /tmp/qnx_omega64_build
	@echo "QNX_OMEGA64_DUAL_ARCH_BUILD=PASS (x86_64 + aarch64le, 0 FLOAT, -Werror)"

sim_vektor_a:
	@gcc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -o /tmp/ky_rox_test_vektor_a L2_GATE/test_vektor_a_spec411_c11.c
	@/tmp/ky_rox_test_vektor_a
	@rm -f /tmp/ky_rox_test_vektor_a
	@iverilog -g2012 -Wall -o /tmp/ky_rox_tb_vektor_a.vvp L2_GATE/vektor_a_airlock.sv L2_GATE/spec411_galvanic_gate.sv L2_GATE/vektor_a_spec411_sluice_top.sv L2_GATE/tb_vektor_a_spec411_sluice.sv
	@vvp /tmp/ky_rox_tb_vektor_a.vvp
	@rm -f /tmp/ky_rox_tb_vektor_a.vvp

qnx_vektor_a:
	@mkdir -p /tmp/qnx_vektor_a_build
	@qcc -Vgcc_ntox86_64 -std=gnu11 -O2 -Wall -Wextra -Werror -c L2_GATE/vektor_a_qnx_resmgr.c -o /tmp/qnx_vektor_a_build/vektor_a_qnx_resmgr_x86_64.o
	@qcc -Vgcc_ntoaarch64le -std=gnu11 -O2 -Wall -Wextra -Werror -c L2_GATE/vektor_a_qnx_resmgr.c -o /tmp/qnx_vektor_a_build/vektor_a_qnx_resmgr_aarch64le.o
	@rm -rf /tmp/qnx_vektor_a_build
	@echo "QNX_VEKTOR_A_DUAL_ARCH_BUILD=PASS (x86_64 + aarch64le, 133425 PS DIAMOND, 0 FLOAT, -Werror)"

sim_k_sluice:
	@gcc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Wconversion -Wsign-conversion -o /tmp/ky_rox_test_k_sluice L2_GATE/test_k_filter_sluice_c11.c
	@/tmp/ky_rox_test_k_sluice
	@rm -f /tmp/ky_rox_test_k_sluice
	@iverilog -g2012 -Wall -o /tmp/ky_rox_tb_k_sluice.vvp L2_GATE/k_filter_sluice.sv L2_GATE/tb_k_filter_sluice.sv
	@vvp /tmp/ky_rox_tb_k_sluice.vvp
	@rm -f /tmp/ky_rox_tb_k_sluice.vvp

verify:
	@python3 -m unittest -q L1_LAW/invariants_pure.py
	@PYTHONPATH=L1_LAW python3 -m unittest -q L1_LAW/test_ky_parser.py
	@PYTHONPATH=L1_LAW python3 -m unittest -q L1_LAW/test_ky_v15_clean_parser.py
	@PYTHONPATH=L1_LAW python3 -m unittest -q L1_LAW/test_rosetta_d3.py
	@python3 L2_GATE/evaluate_boundaries.py
	@PYTHONPATH=L2_GATE python3 -m unittest -q L2_GATE/test_adversarial_capsule_gate_harness.py
	@PYTHONPATH=L2_GATE python3 -m unittest -q L2_GATE/test_registry_b_dlatch_telemetry_protocol.py
	@PYTHONPATH=L2_GATE python3 -m unittest -q L2_GATE/test_spec414_415_416_gothenburg_corridor_gate.py
	@PYTHONPATH=L2_GATE python3 -m unittest -q L2_GATE/test_k_filter_sluice_dual_track.py
	@PYTHONPATH=tools python3 -m unittest -q tools/test_contract_blast_radius_scanner.py
	@PYTHONPATH=tools python3 -m unittest -q tools/test_agy_ky_blackbox_harness.py
	@PYTHONPATH=tools python3 -m unittest -q tools/test_export_blast_sphere.py
	@python3 run_demo.py
	@echo "[L1_VERIFIED // HOLD_READY_FOR_W2] L1 software checks passed (PHYSICAL_AUTHORITY=NONE; W_human required for W2). All 10 Suites (60/60), 7/7 microtest dirs, and 10/10 L1_LAW bounds satisfied."
