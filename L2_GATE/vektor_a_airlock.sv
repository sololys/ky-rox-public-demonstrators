// =============================================================================
// Vektor A Outer Airlock RTL (Lattice iCE40UP5K-SG48 / IEEE 1800-2012)
// Module   : vektor_a_airlock
// Purpose  : Gates core_wake_en using discrete crystal clock ticks and
//            picosecond TDC Time-of-Flight (no IEEE-754 FP, 0 SB_MAC16):
//              1) Alexandrov 20.0 m diamond: 0 < tdc_tof_ps <= 133,425 ps
//              2) Sapphire +-5.0 ppm lock: |sapphire_meas_ticks - 200,000| <= 1
//              3) One-way optical data diode: optical_tx_only (no RX return wire)
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module vektor_a_airlock #(
    parameter [31:0] TAU_MAX_PS      = 32'd133425,
    parameter [31:0] SAPPHIRE_N_REF  = 32'd200000,
    parameter [31:0] MAX_DRIFT_TICKS = 32'd1
) (
    input  wire        clk_ref,
    input  wire        rst_l01_n,
    input  wire        tdc_valid,
    input  wire [31:0] tdc_tof_ps,
    input  wire        win_valid,
    input  wire [31:0] sapphire_meas_ticks,
    output reg         core_wake_en,
    output reg         causal_hold,
    output reg         clock_drift_kill,
    output wire        optical_tx_only
);

    reg [31:0] tick_diff;
    reg        drift_fault_comb;
    reg        tof_ok_comb;

    always @(*) begin
        if (sapphire_meas_ticks >= SAPPHIRE_N_REF)
            tick_diff = sapphire_meas_ticks - SAPPHIRE_N_REF;
        else
            tick_diff = SAPPHIRE_N_REF - sapphire_meas_ticks;

        drift_fault_comb = win_valid && (tick_diff > MAX_DRIFT_TICKS);
        tof_ok_comb      = tdc_valid && (tdc_tof_ps > 32'd0) && (tdc_tof_ps <= TAU_MAX_PS);
    end

    always @(posedge clk_ref) begin
        if (!rst_l01_n) begin
            clock_drift_kill <= 1'b0;
            causal_hold      <= 1'b1;
            core_wake_en     <= 1'b0;
        end else begin
            if (drift_fault_comb) begin
                clock_drift_kill <= 1'b1;
                causal_hold      <= 1'b1;
                core_wake_en     <= 1'b0;
            end else if (clock_drift_kill) begin
                causal_hold      <= 1'b1;
                core_wake_en     <= 1'b0;
            end else if (tof_ok_comb) begin
                causal_hold      <= 1'b0;
                core_wake_en     <= 1'b1;
            end else begin
                causal_hold      <= 1'b1;
                core_wake_en     <= 1'b0;
            end
        end
    end

    /* One-way optical telemetry diode: output only, no silicon return path */
    assign optical_tx_only = core_wake_en && !clock_drift_kill;

endmodule
`default_nettype wire
