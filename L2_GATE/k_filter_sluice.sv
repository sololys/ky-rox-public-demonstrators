// =============================================================================
// Synthesizable K-Filter Sluice RTL for Lattice iCE40UP5K-SG48 (IEEE 1800-2012)
// Module    : k_filter_sluice
// Parity    : Cycle-exact bit-for-bit XOR == 0 against k_filter_sluice.h (C11)
// Arithmetic: Exact 64-bit / 128-bit integer logic (no IEEE-754 FP, 0 SB_MAC16)
// Authority : NONE (0.00 V DC L1.5 synthesis/simulation reference)
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module k_filter_sluice #(
    parameter [63:0] DELTA_NUM   = 64'd5,
    parameter [63:0] DELTA_DEN   = 64'd100,
    parameter [63:0] PHI_RES_MAX = 64'd10,
    parameter [63:0] LAMBDA_MAX  = 64'd50,
    parameter [31:0] W_K         = 32'd10,
    parameter [31:0] W_V         = 32'd1000,
    parameter [31:0] W_PHI       = 32'd5,
    parameter [31:0] W_P         = 32'd2
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        step_en,
    input  wire        l01_reset_req,
    input  wire        l01_witness_ok,
    input  wire        prep_match_ok,

    input  wire [63:0] q0,
    input  wire [63:0] q1,
    input  wire [63:0] q2,
    input  wire [63:0] p0,
    input  wire [63:0] p1,
    input  wire [63:0] p2,
    input  wire [63:0] norm_err_sq,
    input  wire [63:0] norm_ref_sq,
    input  wire [31:0] valid_steps,
    input  wire [31:0] total_steps,
    input  wire [63:0] phi_res_abs,
    input  wire [63:0] lambda_bound,
    input  wire [63:0] spec_max_re,
    input  wire [63:0] entropy_paid,
    input  wire [63:0] entropy_req,
    input  wire        hash_valid,
    input  wire        witness_ext,

    output reg  [1:0]  port_out,
    output reg  [3:0]  reason_out,
    output reg         actuator_v_en,
    output reg         monitor_coupled,
    output reg         kill_latched,
    output reg  [63:0] delta_k_out
);

    localparam [1:0] PORT_HOLD = 2'd0;
    localparam [1:0] PORT_OPEN = 2'd1;
    localparam [1:0] PORT_KILL = 2'd2;

    localparam [3:0] REASON_OPEN_WITNESSED     = 4'd0;
    localparam [3:0] REASON_HOLD_NO_WITNESS    = 4'd1;
    localparam [3:0] REASON_HOLD_PHI_RESIDUAL  = 4'd2;
    localparam [3:0] REASON_HOLD_PREP_MISMATCH = 4'd3;
    localparam [3:0] REASON_KILL_NULL_OR_ZERO  = 4'd4;
    localparam [3:0] REASON_KILL_LATCHED       = 4'd5;
    localparam [3:0] REASON_KILL_POISON_MIN    = 4'd6;
    localparam [3:0] REASON_KILL_SPECTRAL_RE   = 4'd7;
    localparam [3:0] REASON_KILL_HASH_CHAIN    = 4'd8;
    localparam [3:0] REASON_KILL_CHAIN_STEPS   = 4'd9;
    localparam [3:0] REASON_KILL_LANDAUER_DEBT = 4'd10;
    localparam [3:0] REASON_KILL_KERNEL_DRIFT  = 4'd11;
    localparam [3:0] REASON_KILL_COV_BOUND     = 4'd12;
    localparam [3:0] REASON_KILL_SCORE_OVF     = 4'd13;

    localparam [63:0] POISON_MIN = 64'h8000_0000_0000_0000;

    wire [31:0] a_lo = norm_err_sq[31:0];
    wire [31:0] a_hi = norm_err_sq[63:32];
    wire [31:0] b_lo = DELTA_DEN[31:0];
    wire [31:0] b_hi = DELTA_DEN[63:32];
    wire [31:0] c_lo = DELTA_NUM[31:0];
    wire [31:0] c_hi = DELTA_NUM[63:32];
    wire [31:0] d_lo = norm_ref_sq[31:0];
    wire [31:0] d_hi = norm_ref_sq[63:32];

    wire [63:0] ab_p0  = {32'd0, a_lo} * {32'd0, b_lo};
    wire [63:0] ab_p1  = {32'd0, a_lo} * {32'd0, b_hi};
    wire [63:0] ab_p2  = {32'd0, a_hi} * {32'd0, b_lo};
    wire [63:0] ab_p3  = {32'd0, a_hi} * {32'd0, b_hi};
    wire [63:0] ab_mid = {32'd0, ab_p0[63:32]} + {32'd0, ab_p1[31:0]} + {32'd0, ab_p2[31:0]};
    wire [63:0] ab_hi  = ab_p3 + {32'd0, ab_p1[63:32]} + {32'd0, ab_p2[63:32]} + {32'd0, ab_mid[63:32]};
    wire [63:0] ab_lo  = {ab_mid[31:0], ab_p0[31:0]};

    wire [63:0] cd_p0  = {32'd0, c_lo} * {32'd0, d_lo};
    wire [63:0] cd_p1  = {32'd0, c_lo} * {32'd0, d_hi};
    wire [63:0] cd_p2  = {32'd0, c_hi} * {32'd0, d_lo};
    wire [63:0] cd_p3  = {32'd0, c_hi} * {32'd0, d_hi};
    wire [63:0] cd_mid = {32'd0, cd_p0[63:32]} + {32'd0, cd_p1[31:0]} + {32'd0, cd_p2[31:0]};
    wire [63:0] cd_hi  = cd_p3 + {32'd0, cd_p1[63:32]} + {32'd0, cd_p2[63:32]} + {32'd0, cd_mid[63:32]};
    wire [63:0] cd_lo  = {cd_mid[31:0], cd_p0[31:0]};

    wire drift_ok = (ab_hi < cd_hi) || ((ab_hi == cd_hi) && (ab_lo <= cd_lo));

    wire poison_hit = (q0 == POISON_MIN) || (q1 == POISON_MIN) || (q2 == POISON_MIN) ||
                      (p0 == POISON_MIN) || (p1 == POISON_MIN) || (p2 == POISON_MIN) ||
                      (spec_max_re == POISON_MIN);

    wire spec_pos = (!spec_max_re[63]) && (spec_max_re != 64'd0);

    wire [95:0] term_k   = {64'd0, W_K}   * {32'd0, norm_err_sq};
    wire [95:0] term_phi = {64'd0, W_PHI} * {32'd0, phi_res_abs};
    wire [95:0] term_p   = {64'd0, W_P}   * {32'd0, lambda_bound};
    wire [95:0] sum_96   = term_k + term_phi + term_p;
    wire        score_ovf = (term_k[95:64] != 32'd0) ||
                            (term_phi[95:64] != 32'd0) ||
                            (term_p[95:64] != 32'd0) ||
                            (sum_96[95:64] != 32'd0);

    reg [1:0]  comb_port;
    reg [3:0]  comb_reason;
    reg [63:0] comb_dk;

    always @(*) begin
        comb_dk = 64'd0;
        if (kill_latched) begin
            comb_port   = PORT_KILL;
            comb_reason = REASON_KILL_LATCHED;
        end else if ((norm_ref_sq == 64'd0) || (DELTA_DEN == 64'd0) || (total_steps == 32'd0) ||
                     (W_K == 32'd0) || (W_V == 32'd0) || (W_PHI == 32'd0) || (W_P == 32'd0)) begin
            comb_port   = PORT_KILL;
            comb_reason = REASON_KILL_NULL_OR_ZERO;
        end else if (poison_hit) begin
            comb_port   = PORT_KILL;
            comb_reason = REASON_KILL_POISON_MIN;
        end else if (valid_steps != total_steps) begin
            comb_port   = PORT_KILL;
            comb_reason = REASON_KILL_CHAIN_STEPS;
        end else if (score_ovf) begin
            comb_port   = PORT_KILL;
            comb_reason = REASON_KILL_SCORE_OVF;
        end else begin
            comb_dk = sum_96[63:0];
            if (spec_pos) begin
                comb_port   = PORT_KILL;
                comb_reason = REASON_KILL_SPECTRAL_RE;
            end else if (!hash_valid) begin
                comb_port   = PORT_KILL;
                comb_reason = REASON_KILL_HASH_CHAIN;
            end else if (entropy_paid < entropy_req) begin
                comb_port   = PORT_KILL;
                comb_reason = REASON_KILL_LANDAUER_DEBT;
            end else if (!drift_ok) begin
                comb_port   = PORT_KILL;
                comb_reason = REASON_KILL_KERNEL_DRIFT;
            end else if (lambda_bound > LAMBDA_MAX) begin
                comb_port   = PORT_KILL;
                comb_reason = REASON_KILL_COV_BOUND;
            end else if (!prep_match_ok) begin
                comb_port   = PORT_HOLD;
                comb_reason = REASON_HOLD_PREP_MISMATCH;
            end else if (phi_res_abs > PHI_RES_MAX) begin
                comb_port   = PORT_HOLD;
                comb_reason = REASON_HOLD_PHI_RESIDUAL;
            end else if (!witness_ext) begin
                comb_port   = PORT_HOLD;
                comb_reason = REASON_HOLD_NO_WITNESS;
            end else begin
                comb_port   = PORT_OPEN;
                comb_reason = REASON_OPEN_WITNESSED;
            end
        end
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            port_out        <= PORT_HOLD;
            reason_out      <= REASON_HOLD_NO_WITNESS;
            actuator_v_en   <= 1'b0;
            monitor_coupled <= 1'b1;
            kill_latched    <= 1'b0;
            delta_k_out     <= 64'd0;
        end else if (l01_reset_req) begin
            if (l01_witness_ok) begin
                port_out        <= PORT_HOLD;
                reason_out      <= REASON_HOLD_NO_WITNESS;
                actuator_v_en   <= 1'b0;
                monitor_coupled <= 1'b1;
                kill_latched    <= 1'b0;
            end else begin
                port_out        <= PORT_KILL;
                reason_out      <= REASON_KILL_LATCHED;
                actuator_v_en   <= 1'b0;
                monitor_coupled <= 1'b0;
                kill_latched    <= 1'b1;
            end
        end else if (step_en) begin
            port_out    <= comb_port;
            reason_out  <= comb_reason;
            delta_k_out <= comb_dk;
            if (comb_port == PORT_KILL) begin
                kill_latched    <= 1'b1;
                monitor_coupled <= 1'b0;
                actuator_v_en   <= 1'b0;
            end else if (comb_port == PORT_OPEN) begin
                monitor_coupled <= 1'b1;
                actuator_v_en   <= 1'b1;
            end else begin
                monitor_coupled <= 1'b1;
                actuator_v_en   <= 1'b0;
            end
        end
    end

endmodule
`default_nettype wire
