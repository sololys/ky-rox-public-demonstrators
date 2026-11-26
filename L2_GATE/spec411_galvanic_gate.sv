// =============================================================================
// SPEC-411 Galvanic Separation Gate RTL (Lattice iCE40UP5K-SG48 / IEEE 1800-2012)
// Module   : spec411_galvanic_gate
// Law      : Psi = [Omega_Y, Omega_T]^T with d(Omega_Y)/d(Omega_T) === 0.
//            - omega_y_en is hardwired 1'b1 (5.00 V Fail-Open existence rail).
//            - omega_t_en is Fail-Closed behind Vektor A, 50/50 bilateral seal,
//              exact integer cross-multiplied semantic divergence Delta_K < eps,
//              and Butterfly Pocket A_5 (rho_N < K_gamma -> d(Omega_T)/dt = 0
//              until Level 01 avg_l01_trigger).
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module spec411_galvanic_gate (
    input  wire        clk_ref,
    input  wire        rst_l01_n,
    input  wire        core_wake_en,
    input  wire        clock_drift_kill,
    input  wire        bilat_50_50_sealed,
    input  wire [31:0] delta_k_num,
    input  wire [31:0] delta_k_den,
    input  wire [31:0] eps_num,
    input  wire [31:0] eps_den,
    input  wire [31:0] rho_n,
    input  wire [31:0] k_gamma,
    input  wire        avg_l01_trigger,
    output wire        omega_y_en,          /* 5.00 V Fail-Open existence rail */
    output reg         omega_t_en,          /* 0.00 V / 5.00 V Fail-Closed rail */
    output reg         omega_t_kill_latch,  /* Isolated sticky KILL on Omega_T */
    output reg         a5_pocket_active     /* Butterfly A_5 stasis latch */
);

    reg [63:0] lhs_delta;
    reg [63:0] rhs_eps;
    reg        semantic_mismatch;
    reg        crisis_condition;
    reg        next_a5_pocket;
    reg        next_kill_latch;
    reg        t_open_valid;

    always @(*) begin
        /* Exact 64-bit integer cross-multiplication (no IEEE-754 FP) */
        lhs_delta = {32'd0, delta_k_num} * {32'd0, eps_den};
        rhs_eps   = {32'd0, eps_num}     * {32'd0, delta_k_den};

        semantic_mismatch = (delta_k_den == 32'd0) || (eps_den == 32'd0) || (lhs_delta >= rhs_eps);
        crisis_condition  = (rho_n < k_gamma);

        if (crisis_condition)
            next_a5_pocket = 1'b1;
        else if (a5_pocket_active && avg_l01_trigger)
            next_a5_pocket = 1'b0;
        else
            next_a5_pocket = a5_pocket_active;

        if (clock_drift_kill || (bilat_50_50_sealed && semantic_mismatch && !next_a5_pocket && !crisis_condition))
            next_kill_latch = 1'b1;
        else
            next_kill_latch = omega_t_kill_latch;

        t_open_valid = core_wake_en
                    && !clock_drift_kill
                    && !next_kill_latch
                    && !next_a5_pocket
                    && !crisis_condition
                    && bilat_50_50_sealed
                    && !semantic_mismatch;
    end

    always @(posedge clk_ref) begin
        if (!rst_l01_n) begin
            omega_t_kill_latch <= 1'b0;
            a5_pocket_active   <= 1'b0;
            omega_t_en         <= 1'b0;
        end else begin
            a5_pocket_active   <= next_a5_pocket;
            omega_t_kill_latch <= next_kill_latch;
            omega_t_en         <= t_open_valid;
        end
    end

    /* Galvanic unconditional existence circuit: d(Omega_Y)/d(Omega_T) === 0 */
    assign omega_y_en = 1'b1;

endmodule
`default_nettype wire
