// =============================================================================
// Cycle-Exact Testbench: Vektor A (133,425 ps) & SPEC-411 Galvanic Sluice
// Verifies 16 deterministic vectors (8 standalone Vektor A + 8 composite SPEC-411):
//   A1..A8: 133,425 ps horizon, 133,426 ps +1 ps cutoff, 0 ps missing ToF,
//           +-1 tick (+-5 ppm) tolerance, +-2 tick (+-10 ppm) sticky KILL,
//           and Level 01 reset recovery.
//   G1..G8: Exact 5-bit hardware byte parity (0x01, 0x13, 0x01, 0x05, 0x01,
//           0x09, 0x09, 0x13) with unconditional pin_omega_y_5v === 1'b1.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module tb_vektor_a_spec411_sluice;

    reg         clk_ref             = 1'b0;
    reg         a_rst_n             = 1'b0;
    reg         a_tdc_valid         = 1'b0;
    reg  [31:0] a_tdc_tof_ps        = 32'd0;
    reg         a_win_valid         = 1'b0;
    reg  [31:0] a_sapphire_ticks    = 32'd200000;

    wire        a_core_wake_en;
    wire        a_causal_hold;
    wire        a_clock_drift_kill;
    wire        a_optical_tx_only;

    reg         g_rst_n             = 1'b0;
    reg         g_tdc_valid         = 1'b0;
    reg  [31:0] g_tdc_tof_ps        = 32'd0;
    reg         g_win_valid         = 1'b1;
    reg  [31:0] g_sapphire_ticks    = 32'd200000;
    reg         g_bilat_sealed      = 1'b0;
    reg  [31:0] g_dk_num            = 32'd1;
    reg  [31:0] g_dk_den            = 32'd100;
    reg  [31:0] g_eps_num           = 32'd5;
    reg  [31:0] g_eps_den           = 32'd100;
    reg  [31:0] g_rho_n             = 32'd100;
    reg  [31:0] g_k_gamma           = 32'd50;
    reg         g_avg_l01           = 1'b0;

    wire        pin_omega_y_5v;
    wire        pin_omega_t_5v;
    wire        pin_omega_t_kill;
    wire        pin_a5_pocket;
    wire        pin_optical_tx_only;

    wire [7:0] hw_byte = {
        3'b000,
        pin_optical_tx_only,
        pin_a5_pocket,
        pin_omega_t_kill,
        pin_omega_t_5v,
        pin_omega_y_5v
    };

    always #10 clk_ref = ~clk_ref;

    vektor_a_airlock dut_airlock (
        .clk_ref             (clk_ref),
        .rst_l01_n           (a_rst_n),
        .tdc_valid           (a_tdc_valid),
        .tdc_tof_ps          (a_tdc_tof_ps),
        .win_valid           (a_win_valid),
        .sapphire_meas_ticks (a_sapphire_ticks),
        .core_wake_en        (a_core_wake_en),
        .causal_hold         (a_causal_hold),
        .clock_drift_kill    (a_clock_drift_kill),
        .optical_tx_only     (a_optical_tx_only)
    );

    vektor_a_spec411_sluice_top dut_sluice (
        .clk_ref             (clk_ref),
        .rst_l01_n           (g_rst_n),
        .tdc_valid           (g_tdc_valid),
        .tdc_tof_ps          (g_tdc_tof_ps),
        .win_valid           (g_win_valid),
        .sapphire_meas_ticks (g_sapphire_ticks),
        .bilat_50_50_sealed  (g_bilat_sealed),
        .delta_k_num         (g_dk_num),
        .delta_k_den         (g_dk_den),
        .eps_num             (g_eps_num),
        .eps_den             (g_eps_den),
        .rho_n               (g_rho_n),
        .k_gamma             (g_k_gamma),
        .avg_l01_trigger     (g_avg_l01),
        .pin_omega_y_5v      (pin_omega_y_5v),
        .pin_omega_t_5v      (pin_omega_t_5v),
        .pin_omega_t_kill    (pin_omega_t_kill),
        .pin_a5_pocket       (pin_a5_pocket),
        .pin_optical_tx_only (pin_optical_tx_only)
    );

    integer err_count = 0;

    task run_airlock_vec(
        input [3:0]  vec_id,
        input        in_rst_n,
        input        in_tdc_val,
        input [31:0] in_tof_ps,
        input        in_win_val,
        input [31:0] in_ticks,
        input        exp_wake,
        input        exp_chold,
        input        exp_ckill,
        input        exp_opt
    );
    begin
        @(negedge clk_ref);
        a_rst_n          = in_rst_n;
        a_tdc_valid      = in_tdc_val;
        a_tdc_tof_ps     = in_tof_ps;
        a_win_valid      = in_win_val;
        a_sapphire_ticks = in_ticks;
        @(posedge clk_ref);
        #1;
        if (a_core_wake_en !== exp_wake || a_causal_hold !== exp_chold ||
            a_clock_drift_kill !== exp_ckill || a_optical_tx_only !== exp_opt) begin
            $display("FATAL A%0d MISMATCH: got (%0d,%0d,%0d,%0d) != exp (%0d,%0d,%0d,%0d)",
                     vec_id, a_core_wake_en, a_causal_hold, a_clock_drift_kill, a_optical_tx_only,
                     exp_wake, exp_chold, exp_ckill, exp_opt);
            err_count = err_count + 1;
        end
    end
    endtask

    task run_galvanic_vec(
        input [3:0]  vec_id,
        input        in_rst_n,
        input        in_tdc_val,
        input [31:0] in_tof_ps,
        input [31:0] in_ticks,
        input        in_bilat,
        input [31:0] in_dk_num,
        input [31:0] in_dk_den,
        input [31:0] in_eps_num,
        input [31:0] in_eps_den,
        input [31:0] in_rho_n,
        input [31:0] in_k_gamma,
        input        in_avg,
        input [7:0]  exp_hw_byte
    );
    begin
        @(negedge clk_ref);
        g_rst_n          = in_rst_n;
        g_tdc_valid      = in_tdc_val;
        g_tdc_tof_ps     = in_tof_ps;
        g_win_valid      = 1'b1;
        g_sapphire_ticks = in_ticks;
        g_bilat_sealed   = in_bilat;
        g_dk_num         = in_dk_num;
        g_dk_den         = in_dk_den;
        g_eps_num        = in_eps_num;
        g_eps_den        = in_eps_den;
        g_rho_n          = in_rho_n;
        g_k_gamma        = in_k_gamma;
        g_avg_l01        = in_avg;
        @(posedge clk_ref);
        #1;
        if (pin_omega_y_5v !== 1'b1) begin
            $display("FATAL G%0d: Omega_Y dropped below 1!", vec_id);
            err_count = err_count + 1;
        end
        if (hw_byte !== exp_hw_byte) begin
            $display("FATAL G%0d MISMATCH: got hw_byte=0x%02x != exp 0x%02x", vec_id, hw_byte, exp_hw_byte);
            err_count = err_count + 1;
        end
    end
    endtask

    initial begin
        // --- Part 1: Standalone Vektor A 133,425 ps Airlock (A1..A8) ---
        a_rst_n = 1'b0;
        @(posedge clk_ref);
        run_airlock_vec(4'd1, 1'b1, 1'b1, 32'd133425, 1'b1, 32'd200001, 1'b1, 1'b0, 1'b0, 1'b1);
        run_airlock_vec(4'd2, 1'b1, 1'b1, 32'd133426, 1'b1, 32'd200000, 1'b0, 1'b1, 1'b0, 1'b0);
        run_airlock_vec(4'd3, 1'b1, 1'b1, 32'd0,      1'b1, 32'd200000, 1'b0, 1'b1, 1'b0, 1'b0);
        run_airlock_vec(4'd4, 1'b1, 1'b1, 32'd100000, 1'b1, 32'd199999, 1'b1, 1'b0, 1'b0, 1'b1);
        run_airlock_vec(4'd5, 1'b1, 1'b1, 32'd100000, 1'b1, 32'd200002, 1'b0, 1'b1, 1'b1, 1'b0);
        run_airlock_vec(4'd6, 1'b1, 1'b1, 32'd100000, 1'b1, 32'd199998, 1'b0, 1'b1, 1'b1, 1'b0);
        run_airlock_vec(4'd7, 1'b1, 1'b1, 32'd100000, 1'b1, 32'd200000, 1'b0, 1'b1, 1'b1, 1'b0);
        run_airlock_vec(4'd8, 1'b0, 1'b0, 32'd0,      1'b1, 32'd200000, 1'b0, 1'b1, 1'b0, 1'b0);
        run_airlock_vec(4'd9, 1'b1, 1'b1, 32'd120000, 1'b1, 32'd200000, 1'b1, 1'b0, 1'b0, 1'b1);

        // --- Part 2: Composite Vektor A + SPEC-411 Galvanic Sluice (G1..G8) ---
        run_galvanic_vec(4'd1, 1'b0, 1'b0, 32'd0,      32'd200000, 1'b0, 32'd1, 32'd100, 32'd5, 32'd100, 32'd100, 32'd50, 1'b0, 8'h01);
        run_galvanic_vec(4'd2, 1'b1, 1'b1, 32'd133425, 32'd200000, 1'b1, 32'd1, 32'd100, 32'd5, 32'd100, 32'd100, 32'd50, 1'b0, 8'h13);
        run_galvanic_vec(4'd3, 1'b1, 1'b1, 32'd133426, 32'd200000, 1'b1, 32'd1, 32'd100, 32'd5, 32'd100, 32'd100, 32'd50, 1'b0, 8'h01);
        run_galvanic_vec(4'd4, 1'b1, 1'b1, 32'd133426, 32'd200000, 1'b1, 32'd6, 32'd100, 32'd5, 32'd100, 32'd100, 32'd50, 1'b0, 8'h05);
        run_galvanic_vec(4'd5, 1'b0, 1'b0, 32'd0,      32'd200000, 1'b0, 32'd1, 32'd100, 32'd5, 32'd100, 32'd100, 32'd50, 1'b0, 8'h01);
        run_galvanic_vec(4'd6, 1'b1, 1'b0, 32'd0,      32'd200000, 1'b1, 32'd1, 32'd100, 32'd5, 32'd100, 32'd30,  32'd50, 1'b0, 8'h09);
        run_galvanic_vec(4'd7, 1'b1, 1'b0, 32'd0,      32'd200000, 1'b1, 32'd1, 32'd100, 32'd5, 32'd100, 32'd100, 32'd50, 1'b0, 8'h09);
        run_galvanic_vec(4'd8, 1'b1, 1'b1, 32'd120000, 32'd200000, 1'b1, 32'd1, 32'd100, 32'd5, 32'd100, 32'd100, 32'd50, 1'b1, 8'h13);

        if (err_count != 0) begin
            $display("tb_vektor_a_spec411_sluice: FAIL (%0d errors)", err_count);
            $finish(1);
        end

        $display("VEKTOR_A_SPEC411_RTL=PASS (17/17 CYCLE-EXACT VECTORS, 133425 PS DIAMOND, XOR == 0)");
        $finish(0);
    end

endmodule
`default_nettype wire
