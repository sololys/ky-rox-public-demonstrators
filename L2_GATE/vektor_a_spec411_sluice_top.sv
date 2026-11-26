// =============================================================================
// Composite Vektor A (133,425 ps) + SPEC-411 Galvanic Sluice Top (iCE40UP5K-SG48)
// Outputs  : 5-bit physical status bus:
//            [0] pin_omega_y_5v      (0x01) — Always 5.00 V Fail-Open rail
//            [1] pin_omega_t_5v      (0x02) — 0.00 V / 5.00 V Fail-Closed rail
//            [2] pin_omega_t_kill    (0x04) — Isolated sticky KILL on Omega_T
//            [3] pin_a5_pocket       (0x08) — Butterfly Pocket A_5 stasis
//            [4] pin_optical_tx_only (0x10) — One-way optical telemetry diode
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module vektor_a_spec411_sluice_top (
    input  wire        clk_ref,
    input  wire        rst_l01_n,
    input  wire        tdc_valid,
    input  wire [31:0] tdc_tof_ps,
    input  wire        win_valid,
    input  wire [31:0] sapphire_meas_ticks,
    input  wire        bilat_50_50_sealed,
    input  wire [31:0] delta_k_num,
    input  wire [31:0] delta_k_den,
    input  wire [31:0] eps_num,
    input  wire [31:0] eps_den,
    input  wire [31:0] rho_n,
    input  wire [31:0] k_gamma,
    input  wire        avg_l01_trigger,
    output wire        pin_omega_y_5v,
    output wire        pin_omega_t_5v,
    output wire        pin_omega_t_kill,
    output wire        pin_a5_pocket,
    output wire        pin_optical_tx_only
);

    wire core_wake_reg;
    wire causal_hold_reg;
    wire clock_drift_kill_reg;

    vektor_a_airlock u_airlock (
        .clk_ref             (clk_ref),
        .rst_l01_n           (rst_l01_n),
        .tdc_valid           (tdc_valid),
        .tdc_tof_ps          (tdc_tof_ps),
        .win_valid           (win_valid),
        .sapphire_meas_ticks (sapphire_meas_ticks),
        .core_wake_en        (core_wake_reg),
        .causal_hold         (causal_hold_reg),
        .clock_drift_kill    (clock_drift_kill_reg),
        .optical_tx_only     (pin_optical_tx_only)
    );

    /* Synchronous single-cycle wake/kill evaluation matching C11 spec411_step */
    wire [31:0] tick_diff = (sapphire_meas_ticks >= 32'd200000)
                          ? (sapphire_meas_ticks - 32'd200000)
                          : (32'd200000 - sapphire_meas_ticks);
    wire next_clock_drift_kill = clock_drift_kill_reg || (win_valid && (tick_diff > 32'd1));
    wire next_core_wake_en     = (!next_clock_drift_kill) &&
                                 tdc_valid && (tdc_tof_ps > 32'd0) && (tdc_tof_ps <= 32'd133425);

    spec411_galvanic_gate u_spec411 (
        .clk_ref             (clk_ref),
        .rst_l01_n           (rst_l01_n),
        .core_wake_en        (next_core_wake_en),
        .clock_drift_kill    (next_clock_drift_kill),
        .bilat_50_50_sealed  (bilat_50_50_sealed),
        .delta_k_num         (delta_k_num),
        .delta_k_den         (delta_k_den),
        .eps_num             (eps_num),
        .eps_den             (eps_den),
        .rho_n               (rho_n),
        .k_gamma             (k_gamma),
        .avg_l01_trigger     (avg_l01_trigger),
        .omega_y_en          (pin_omega_y_5v),
        .omega_t_en          (pin_omega_t_5v),
        .omega_t_kill_latch  (pin_omega_t_kill),
        .a5_pocket_active    (pin_a5_pocket)
    );

endmodule
`default_nettype wire
