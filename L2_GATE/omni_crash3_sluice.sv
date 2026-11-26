// =============================================================================
// L2_GATE — 25.OMNI Three-Way Crash Sluice (Crash_3, SystemVerilog RTL)
// Module   : omni_crash3_sluice
// Architecture : Constant-time 194-cycle shared 64-bit MAC & Z[phi] Hamiltonian
//                consequence sluice (0 SB_MAC16, 0 FP, stationary MSB=0 MAC).
// Parity       : 100% cycle- and bit-exact with omni_crash3_sluice.h (C11).
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module omni_crash3_sluice (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         l01_reset_strobe,
    input  wire         l01_witness_ok,
    input  wire         eval_en,

    input  wire [31:0]  seq_epoch,
    input  wire signed [31:0] q_pos,
    input  wire signed [31:0] p_mom,
    input  wire [31:0]  q_bound,
    input  wire [31:0]  eps_k_max,
    input  wire signed [31:0] lambda_spec,
    input  wire signed [31:0] g_barrier,
    input  wire signed [31:0] g_dot,
    input  wire [31:0]  tau_hold_ticks,
    input  wire [31:0]  pi_risk,
    input  wire [31:0]  tau_risk,
    input  wire [31:0]  r_dot,
    input  wire [31:0]  delta_r,
    input  wire [31:0]  k_defect,
    input  wire [31:0]  b_barrier,
    input  wire [31:0]  c_care,
    input  wire [31:0]  dist_mm,
    input  wire [31:0]  tof_ps,
    input  wire [15:0]  s_phase_16,
    input  wire [15:0]  r_mask_16,
    input  wire [15:0]  m_rx_16,
    input  wire [39:0]  finder_sig_40,
    input  wire [7:0]   quiet_zone,
    input  wire         hash_valid,
    input  wire         u_safe_nonempty,
    input  wire         eta_hw_truth,
    input  wire         witness_ext,

    output reg          busy_out,
    output reg          eval_done_out,
    output reg  [1:0]   port_out,
    output reg  [3:0]   reason_out,
    output reg  [1:0]   traj_class_out,
    output reg          dk_kill_latched_out,
    output reg          monitor_coupled_out,
    output reg          actuator_v_en_out,
    output wire [7:0]   status_byte_out,
    output reg  [15:0]  p_or_fuse_out,
    output reg  [31:0]  expected_epoch_out,
    output reg  [31:0]  linf_excess_out,
    output reg  [63:0]  cycle_out,
    output reg  [31:0]  reset_epoch_out,
    output reg  signed [63:0] h_phi_a_out,
    output reg  [63:0]  h_phi_b_out
);

    localparam [1:0] PORT_HOLD = 2'd0;
    localparam [1:0] PORT_OPEN = 2'd1;
    localparam [1:0] PORT_KILL = 2'd2;

    localparam [1:0] TRAJ_O0 = 2'd0;
    localparam [1:0] TRAJ_O1 = 2'd1;
    localparam [1:0] TRAJ_O2 = 2'd2;

    localparam [3:0] REASON_OPEN_AKUERISAAVOQ      = 4'd0;
    localparam [3:0] REASON_HOLD_ETOR_PI_GE_TAU    = 4'd1;
    localparam [3:0] REASON_HOLD_RDOT_SLOPE        = 4'd2;
    localparam [3:0] REASON_HOLD_TAU_R_HORIZON     = 4'd3;
    localparam [3:0] REASON_HOLD_EPS_K_NONZERO     = 4'd4;
    localparam [3:0] REASON_HOLD_NO_WITNESS        = 4'd5;
    localparam [3:0] REASON_KILL_DK_LATCHED        = 4'd6;
    localparam [3:0] REASON_KILL_POISON_OR_BARRIER = 4'd7;
    localparam [3:0] REASON_KILL_ROSETTA_HASH      = 4'd8;
    localparam [3:0] REASON_KILL_INVOLUTION        = 4'd9;
    localparam [3:0] REASON_KILL_OMNI_QR_STRUCT    = 4'd10;
    localparam [3:0] REASON_KILL_EPOCH_REPLAY      = 4'd11;
    localparam [3:0] REASON_KILL_SPACELIKE_DS2     = 4'd12;
    localparam [3:0] REASON_KILL_EPS_K_EXCEEDED    = 4'd13;

    localparam [31:0] POISON_MIN       = 32'h8000_0000;
    localparam [39:0] FINDER_K_GAMMA   = 40'h7F_415D_417F;
    localparam [31:0] MAX_DIST_MM      = 32'd20000;
    localparam [31:0] MAX_TOF_PS       = 32'd133425;
    localparam [31:0] SI_C_M_PER_S     = 32'd299792458;
    localparam [31:0] TWO_E9_PS_MM     = 32'd2000000000;

    assign status_byte_out = {
        1'b0,
        traj_class_out,
        dk_kill_latched_out,
        monitor_coupled_out,
        actuator_v_en_out,
        port_out
    };

    reg has_survived_step;

    wire poison_or_bar = (q_pos == $signed(POISON_MIN)) ||
                         (p_mom == $signed(POISON_MIN)) ||
                         (g_barrier == $signed(POISON_MIN)) ||
                         (g_dot == $signed(POISON_MIN)) ||
                         (q_bound == 32'd0) || q_bound[31] ||
                         k_defect[31] || b_barrier[31] || c_care[31] ||
                         (tau_risk == 32'd0) || (!u_safe_nonempty) ||
                         (g_barrier >= 32'sd0) || (lambda_spec > 32'sd0);

    wire inv_bad       = ((m_rx_16 ^ r_mask_16) != s_phase_16);
    wire qr_bad        = (finder_sig_40 != FINDER_K_GAMMA) || (quiet_zone < 8'd4);
    wire replay_bad    = (seq_epoch < expected_epoch_out);
    wire lc_bounds_bad = (dist_mm == 32'd0) || (dist_mm > MAX_DIST_MM) ||
                         (tof_ps == 32'd0)  || (tof_ps > MAX_TOF_PS);

    wire [31:0] abs_qpos_now = q_pos[31] ? (-q_pos) : q_pos;
    wire [30:0] abs_qp31_now = (abs_qpos_now[30:0] > q_bound[30:0]) ? q_bound[30:0] : abs_qpos_now[30:0];
    wire [31:0] abs_pm_now   = p_mom[31] ? (-p_mom) : p_mom;
    wire [31:0] g_marg_now   = g_barrier[31] ? (-g_barrier) : 32'd0;
    wire [30:0] g_dot_pos    = (g_dot > 32'sd0) ? g_dot[30:0] : 31'd0;

    wire signed [32:0] two_c_minus_b = $signed({1'b0, c_care[30:0], 1'b0}) -
                                       $signed({1'b0, b_barrier[30:0], 1'b0});

    wire [31:0] pi_exc_now   = (pi_risk >= tau_risk) ? (pi_risk - tau_risk + 32'd1) : 32'd0;
    wire [31:0] rdot_exc_now = (r_dot > delta_r) ? (r_dot - delta_r) : 32'd0;

    // Stationary MSB=0 6x32 serial MAC: mul_op[31] == 0 in all 6 phases, so
    // mul_acc is already final at bit_cnt == 31 with zero series post-adders!
    reg [2:0]  mac_phase;
    reg [4:0]  bit_cnt;
    reg [31:0] mul_op;
    reg [63:0] mul_sh;
    reg [63:0] mul_acc;

    reg        lat_poison_bar;
    reg        lat_hash_bad;
    reg        lat_inv_bad;
    reg        lat_qr_bad;
    reg        lat_replay_bad;
    reg        lat_lc_bounds_bad;
    reg        lat_eps_kill;
    reg        lat_pi_hold;
    reg        lat_rdot_hold;
    reg        lat_eps_hold;
    reg        lat_nowit_hold;
    reg        lat_gdot_pos;
    reg [15:0] lat_m_rx_16;
    reg [30:0] lat_abs_pm31;
    reg [30:0] lat_k_defect31;
    reg [30:0] lat_b_barrier31;
    reg [31:0] lat_dist_mm;
    reg [31:0] lat_tof_ps;
    reg [30:0] lat_g_dot_pos31;
    reg [31:0] lat_tau_hold;
    reg [31:0] lat_g_margin;
    reg [30:0] lat_abs_qpos31;
    reg [30:0] lat_q_bound31;
    reg [31:0] lat_eps_k_max;
    reg [31:0] lat_eps_k;
    reg [31:0] lat_pi_exc;
    reg [31:0] lat_rdot_exc;
    reg [31:0] lat_max_pr;
    reg [31:0] lat_linf;

    reg signed [63:0] tmp_h_a;
    reg [63:0]        tmp_h_b;
    reg [63:0]        tmp_lc_lhs;
    reg               flag_lc_ds2_bad;
    reg               flag_tau_r_short;

    wire [63:0] next_acc = mul_acc + (mul_op[0] ? mul_sh : 64'd0);

    reg [31:0] next_mul_op;
    reg [32:0] next_mul_sh33;
    reg [63:0] next_mul_acc_init;
    always @(*) begin
        case (mac_phase)
            3'd0: begin
                next_mul_op       = {1'b0, lat_abs_pm31};
                next_mul_sh33     = {2'b00, lat_abs_pm31};
                next_mul_acc_init = mul_acc; // Continues accumulating q_sq + (2c - 2b) + p_sq!
            end
            3'd1: begin
                next_mul_op       = {1'b0, lat_k_defect31};
                next_mul_sh33     = {1'b0, lat_k_defect31, 1'b0}; // 2 * k_defect
                next_mul_acc_init = {32'd0, lat_b_barrier31, 1'b0}; // 2 * b_barrier
            end
            3'd2: begin
                next_mul_op       = TWO_E9_PS_MM; // 0x7735_9400 (bit 31 == 0)
                next_mul_sh33     = {1'b0, lat_dist_mm};
                next_mul_acc_init = 64'd0;
            end
            3'd3: begin
                next_mul_op       = SI_C_M_PER_S; // 0x11DE_784A (bits 31:29 == 0)
                next_mul_sh33     = {1'b0, lat_tof_ps};
                next_mul_acc_init = 64'd0;
            end
            default: begin
                next_mul_op       = {1'b0, lat_g_dot_pos31}; // bit 31 == 0
                next_mul_sh33     = {1'b0, lat_tau_hold};
                next_mul_acc_init = 64'd0;
            end
        endcase
    end

    wire lc_any_bad = lat_lc_bounds_bad || flag_lc_ds2_bad;
    wire any_kill = dk_kill_latched_out || lat_poison_bar || lat_hash_bad ||
                    lat_inv_bad || lat_qr_bad || lat_replay_bad ||
                    lc_any_bad || lat_eps_kill;

    reg [3:0] commit_reason_kill;
    always @(*) begin
        if (dk_kill_latched_out) commit_reason_kill = REASON_KILL_DK_LATCHED;
        else if (lat_poison_bar) commit_reason_kill = REASON_KILL_POISON_OR_BARRIER;
        else if (lat_hash_bad)   commit_reason_kill = REASON_KILL_ROSETTA_HASH;
        else if (lat_inv_bad)    commit_reason_kill = REASON_KILL_INVOLUTION;
        else if (lat_qr_bad)     commit_reason_kill = REASON_KILL_OMNI_QR_STRUCT;
        else if (lat_replay_bad) commit_reason_kill = REASON_KILL_EPOCH_REPLAY;
        else if (lc_any_bad)     commit_reason_kill = REASON_KILL_SPACELIKE_DS2;
        else                     commit_reason_kill = REASON_KILL_EPS_K_EXCEEDED;
    end

    reg [1:0] commit_port_ok;
    reg [3:0] commit_reason_ok;
    reg       commit_open_ok;
    always @(*) begin
        commit_open_ok = 1'b0;
        if (lat_pi_hold) begin
            commit_port_ok   = PORT_HOLD;
            commit_reason_ok = REASON_HOLD_ETOR_PI_GE_TAU;
        end else if (lat_rdot_hold) begin
            commit_port_ok   = PORT_HOLD;
            commit_reason_ok = REASON_HOLD_RDOT_SLOPE;
        end else if (flag_tau_r_short) begin
            commit_port_ok   = PORT_HOLD;
            commit_reason_ok = REASON_HOLD_TAU_R_HORIZON;
        end else if (lat_eps_hold) begin
            commit_port_ok   = PORT_HOLD;
            commit_reason_ok = REASON_HOLD_EPS_K_NONZERO;
        end else if (lat_nowit_hold) begin
            commit_port_ok   = PORT_HOLD;
            commit_reason_ok = REASON_HOLD_NO_WITNESS;
        end else begin
            commit_open_ok   = 1'b1;
            commit_port_ok   = PORT_OPEN;
            commit_reason_ok = REASON_OPEN_AKUERISAAVOQ;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy_out            <= 1'b0;
            eval_done_out       <= 1'b0;
            port_out            <= PORT_HOLD;
            reason_out          <= REASON_HOLD_NO_WITNESS;
            traj_class_out      <= TRAJ_O2;
            dk_kill_latched_out <= 1'b0;
            monitor_coupled_out <= 1'b1;
            actuator_v_en_out   <= 1'b0;
            has_survived_step   <= 1'b0;
            p_or_fuse_out       <= 16'd0;
            expected_epoch_out  <= 32'd1;
            linf_excess_out     <= 32'd0;
            cycle_out           <= 64'd0;
            reset_epoch_out     <= 32'd0;
            h_phi_a_out         <= 64'sd0;
            h_phi_b_out         <= 64'd0;
        end else begin
            eval_done_out <= 1'b0;
            if (busy_out) begin
                cycle_out <= cycle_out + 64'd1;
                if (mac_phase == 3'd6) begin
                    busy_out            <= 1'b0;
                    eval_done_out       <= 1'b1;
                    dk_kill_latched_out <= any_kill ? 1'b1 : 1'b0;
                    monitor_coupled_out <= any_kill ? 1'b0 : 1'b1;
                    actuator_v_en_out   <= (!any_kill) && commit_open_ok;
                    port_out            <= any_kill ? PORT_KILL : commit_port_ok;
                    reason_out          <= any_kill ? commit_reason_kill : commit_reason_ok;
                    if (any_kill) begin
                        traj_class_out  <= has_survived_step ? TRAJ_O1 : TRAJ_O0;
                        linf_excess_out <= 32'd0;
                        h_phi_a_out     <= 64'sd0;
                        h_phi_b_out     <= 64'd0;
                    end else begin
                        has_survived_step <= 1'b1;
                        traj_class_out    <= TRAJ_O2;
                        linf_excess_out   <= lat_linf;
                        h_phi_a_out       <= tmp_h_a;
                        h_phi_b_out       <= tmp_h_b;
                        if (commit_open_ok) begin
                            p_or_fuse_out      <= p_or_fuse_out | (lat_m_rx_16 & (~p_or_fuse_out));
                            expected_epoch_out <= expected_epoch_out + 32'd1;
                        end
                    end
                end
            end else if (l01_reset_strobe) begin
                cycle_out <= cycle_out + 64'd1;
                if (!l01_witness_ok) begin
                    if (dk_kill_latched_out) begin
                        port_out   <= PORT_KILL;
                        reason_out <= REASON_KILL_DK_LATCHED;
                    end else begin
                        actuator_v_en_out <= 1'b0;
                        port_out          <= PORT_HOLD;
                        reason_out        <= REASON_HOLD_NO_WITNESS;
                    end
                end else begin
                    reset_epoch_out     <= reset_epoch_out + 32'd1;
                    dk_kill_latched_out <= 1'b0;
                    monitor_coupled_out <= 1'b1;
                    actuator_v_en_out   <= 1'b0;
                    has_survived_step   <= 1'b0;
                    port_out            <= PORT_HOLD;
                    reason_out          <= REASON_HOLD_NO_WITNESS;
                    traj_class_out      <= TRAJ_O2;
                    linf_excess_out     <= 32'd0;
                    h_phi_a_out         <= 64'sd0;
                    h_phi_b_out         <= 64'd0;
                end
            end else if (eval_en) begin
                cycle_out <= cycle_out + 64'd1;
                busy_out  <= 1'b1;
            end
        end
    end

    always @(posedge clk) begin
        if (busy_out) begin
            if (mac_phase == 3'd0) begin
                if (bit_cnt == 5'd0) begin
                    lat_eps_k  <= (lat_abs_qpos31 > lat_q_bound31) ? {1'b0, (lat_abs_qpos31 - lat_q_bound31)} : 32'd0;
                    lat_max_pr <= (lat_pi_exc >= lat_rdot_exc) ? lat_pi_exc : lat_rdot_exc;
                end else if (bit_cnt == 5'd1) begin
                    lat_eps_kill <= (lat_eps_k > lat_eps_k_max);
                    lat_eps_hold <= (lat_eps_k != 32'd0);
                    lat_linf     <= (lat_eps_k >= lat_max_pr) ? lat_eps_k : lat_max_pr;
                end
            end
            if (mac_phase < 3'd6) begin
                if (bit_cnt < 5'd31) begin
                    bit_cnt <= bit_cnt + 5'd1;
                    mul_acc <= next_acc;
                    mul_op  <= (mul_op >> 1);
                    mul_sh  <= (mul_sh << 1);
                end else begin
                    bit_cnt   <= 5'd0;
                    mac_phase <= mac_phase + 3'd1;
                    mul_acc   <= next_mul_acc_init;
                    mul_op    <= next_mul_op;
                    mul_sh    <= {31'd0, next_mul_sh33};
                    case (mac_phase)
                        3'd1: tmp_h_a          <= $signed(mul_acc);
                        3'd2: tmp_h_b          <= mul_acc;
                        3'd3: tmp_lc_lhs       <= mul_acc;
                        3'd4: flag_lc_ds2_bad  <= (tmp_lc_lhs > mul_acc);
                        3'd5: flag_tau_r_short <= lat_gdot_pos && ({32'd0, lat_g_margin} < mul_acc);
                        default: ;
                    endcase
                end
            end
        end else if ((!l01_reset_strobe) && eval_en) begin
            mac_phase         <= 3'd0;
            bit_cnt           <= 5'd0;
            mul_op            <= {1'b0, abs_qp31_now};
            mul_sh            <= {33'd0, abs_qp31_now};
            mul_acc           <= {{31{two_c_minus_b[32]}}, two_c_minus_b};
            flag_lc_ds2_bad   <= 1'b0;
            flag_tau_r_short  <= 1'b0;

            lat_poison_bar    <= poison_or_bar;
            lat_hash_bad      <= (!hash_valid);
            lat_inv_bad       <= inv_bad;
            lat_qr_bad        <= qr_bad;
            lat_replay_bad    <= replay_bad;
            lat_lc_bounds_bad <= lc_bounds_bad;
            lat_abs_qpos31    <= abs_qpos_now[30:0];
            lat_q_bound31     <= q_bound[30:0];
            lat_eps_k_max     <= eps_k_max;
            lat_pi_exc        <= pi_exc_now;
            lat_rdot_exc      <= rdot_exc_now;
            lat_pi_hold       <= (pi_risk >= tau_risk);
            lat_rdot_hold     <= (r_dot > delta_r);
            lat_nowit_hold    <= (!eta_hw_truth) || (!witness_ext) ||
                                 (seq_epoch != expected_epoch_out) || (seq_epoch == 32'hFFFF_FFFF);
            lat_gdot_pos      <= (g_dot > 32'sd0);
            lat_m_rx_16       <= m_rx_16;
            lat_abs_pm31      <= abs_pm_now[30:0];
            lat_k_defect31    <= k_defect[30:0];
            lat_b_barrier31   <= b_barrier[30:0];
            lat_dist_mm       <= dist_mm;
            lat_tof_ps        <= tof_ps;
            lat_g_dot_pos31   <= g_dot_pos;
            lat_tau_hold      <= tau_hold_ticks;
            lat_g_margin      <= g_marg_now;
        end
    end

endmodule
`default_nettype wire
