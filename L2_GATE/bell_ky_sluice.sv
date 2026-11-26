// =============================================================================
// L2_GATE — 29.KY Bell-KY Zero-Float Consequence Sluice (SystemVerilog RTL)
// Module   : bell_ky_sluice
// Architecture : Single-arm-channel 8-slot streaming + shared 96-bit MAC +
//                shared 95-bit borrow-comparator (0 SB_MAC16, 0 FP, fits
//                comfortably inside a single Lattice iCE40UP5K-SG48).
// Parity       : 100% cycle- and bit-exact with bell_ky_sluice.h (C11).
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module bell_ky_sluice (
    input  wire         clk,
    input  wire         rst_n,

    // Control strobes
    input  wire         l01_reset_strobe,
    input  wire         l01_witness_ok,
    input  wire         load_en,
    input  wire         arm_idx,
    input  wire [1:0]   mn_idx,
    input  wire         eval_en,

    // Single-channel 40-bit shot-count streaming inputs (shared across K1, K2)
    input  wire [39:0]  n_pulses_in,
    input  wire [39:0]  cnt_pp,
    input  wire [39:0]  cnt_pm,
    input  wire [39:0]  cnt_mp,
    input  wire [39:0]  cnt_mm,

    // Consequence gate evaluation inputs
    input  wire [31:0]  delta_k_cycles,
    input  wire [31:0]  t_clk_ps,
    input  wire [31:0]  dist_mm,
    input  wire [39:0]  tau_ns,
    input  wire [31:0]  setting_corr_abs,
    input  wire [31:0]  tau_indep,
    input  wire [31:0]  tomo_frob_diff_sq,
    input  wire [31:0]  tau_tomo_sq,
    input  wire [127:0] tau_diff_sq,
    input  wire [15:0]  replicated_series,
    input  wire [15:0]  min_series,
    input  wire         hash_valid,
    input  wire         involution_closed,
    input  wire         witness_ext,

    // Registered outputs
    output reg          busy_out,
    output reg          eval_done_out,
    output reg  [1:0]   port_out,
    output reg  [3:0]   reason_out,
    output reg          kill_latched_out,
    output reg          monitor_coupled_out,
    output reg          actuator_v_en_out,
    output reg          bell_violated_k1_out,
    output reg          super_tsirelson_out,
    output wire [7:0]   status_byte_out,
    output reg  [63:0]  cycle_out,
    output reg  [31:0]  reset_epoch_out,
    output wire [127:0] s1_sq_out,
    output wire [127:0] s2_sq_out
);

    localparam [1:0] PORT_HOLD = 2'd0;
    localparam [1:0] PORT_OPEN = 2'd1;
    localparam [1:0] PORT_KILL = 2'd2;

    localparam [3:0] REASON_OPEN_L3_WITNESSED      = 4'd0;
    localparam [3:0] REASON_HOLD_QM_NULL_CONFIRMED = 4'd1;
    localparam [3:0] REASON_HOLD_L1_TOMO_SHIFT     = 4'd2;
    localparam [3:0] REASON_HOLD_OPEN_LOOP_L1      = 4'd3;
    localparam [3:0] REASON_HOLD_NO_QUORUM_OR_WIT  = 4'd4;
    localparam [3:0] REASON_KILL_LATCHED           = 4'd5;
    localparam [3:0] REASON_KILL_SHOT_COUNT        = 4'd6;
    localparam [3:0] REASON_KILL_HASH_CHAIN        = 4'd7;
    localparam [3:0] REASON_KILL_LIGHTCONE         = 4'd8;
    localparam [3:0] REASON_KILL_NO_SIGNALLING     = 4'd9;
    localparam [3:0] REASON_KILL_SETTING_CORR      = 4'd10;

    localparam [39:0] MAX_PULSES = 40'h40_0000_0000; // 1 << 38
    localparam [28:0] SI_C_29    = 29'd299792458;
    localparam [30:0] TWO_E9_31  = 31'd2000000000;

    reg [83:0] s1_sq_r;
    reg [83:0] s2_sq_r;
    assign s1_sq_out = {44'd0, s1_sq_r};
    assign s2_sq_out = {44'd0, s2_sq_r};

    assign status_byte_out = {
        1'b0,
        super_tsirelson_out,
        bell_violated_k1_out,
        kill_latched_out,
        monitor_coupled_out,
        actuator_v_en_out,
        port_out
    };

    // Resettable control state
    reg [7:0] loaded_mask;
    reg       shot_err_accum;

    // Synchronous scratchpad registers
    reg [39:0]        n_pulses_latched;
    reg signed [42:0] sigma_k1;
    reg signed [42:0] sigma_k2;
    reg [40:0]        pa_reg, pb0_reg, pb1_reg;
    reg [40:0]        max_ns_dev;
    reg               ns_pipe_vld;
    reg               ns_pipe_clr;
    reg signed [41:0] ns_d1, ns_d2;
    reg [39:0]        lat_tau_ns;

    reg [2:0]  mac_phase;
    reg [5:0]  bit_cnt;
    reg [47:0] mul_op;
    reg [95:0] mul_sh;
    reg [95:0] mul_acc;

    reg        lat_shot_bad;
    reg        lat_lc_zero;
    reg        lat_ns_breach;
    reg        lat_corr_bad;
    reg        lat_hash_ok;
    reg        lat_inv_closed;
    reg        lat_wit_ext;
    reg        lat_tomo_bad;
    reg        lat_quorum_ok;
    reg [41:0] lat_abs_s2;
    reg [42:0] lat_abs_ds;
    reg [39:0] lat_np;
    reg [31:0] lat_dk, lat_tclk, lat_dist;
    reg [85:0] lat_tau_lo86;
    reg        lat_tau_hi_nz;

    reg [92:0] scratch_93;
    reg        s1_gt_s2;
    reg        flag_sig_shift;
    reg        flag_bell_viol;
    reg        flag_super_ts;
    reg        flag_lc_bad;

    // Single-channel load sums (half the adders & comparators!)
    wire [40:0] cur_pa   = {1'b0, cnt_pp} + {1'b0, cnt_pm};
    wire [40:0] cur_pb   = {1'b0, cnt_pp} + {1'b0, cnt_mp};
    wire [40:0] cnt_same = {1'b0, cnt_pp} + {1'b0, cnt_mm};
    wire [40:0] cnt_diff = {1'b0, cnt_pm} + {1'b0, cnt_mp};
    wire [41:0] sum_all  = {1'b0, cnt_same} + {1'b0, cnt_diff};

    wire np_valid = (n_pulses_in != 40'd0) && (n_pulses_in <= MAX_PULSES);
    wire ok_arm   = np_valid && (sum_all == {2'b00, n_pulses_in});

    wire is_idx3 = (mn_idx == 2'd3);
    wire signed [42:0] c_signed = $signed({2'd0, is_idx3 ? cnt_diff : cnt_same}) -
                                  $signed({2'd0, is_idx3 ? cnt_same : cnt_diff});

    wire [2:0] slot_idx = {arm_idx, mn_idx};
    wire [7:0] slot_bit = (8'd1 << slot_idx);

    wire [40:0] ref_main = (mn_idx == 2'd2) ? pb0_reg : pa_reg;
    wire [40:0] cur_main = (mn_idx == 2'd2) ? cur_pb  : cur_pa;
    wire signed [41:0] sub_main = $signed({1'b0, ref_main}) - $signed({1'b0, cur_main});
    wire signed [41:0] sub_b1   = $signed({1'b0, pb1_reg})  - $signed({1'b0, cur_pb});

    // Stage-B pipelined absolute value & max (decoupled from cur_pa/cur_pb adders)
    wire [40:0] abs_d1   = ns_d1[41] ? (-ns_d1[40:0]) : ns_d1[40:0];
    wire [40:0] abs_d2   = ns_d2[41] ? (-ns_d2[40:0]) : ns_d2[40:0];
    wire [40:0] pipe_dev = (abs_d1 >= abs_d2) ? abs_d1 : abs_d2;
    wire [40:0] base_ns  = ns_pipe_clr ? 41'd0 : max_ns_dev;

    // Eval start helpers
    wire signed [43:0] diff_sigma = $signed({sigma_k1[42], sigma_k1}) -
                                    $signed({sigma_k2[42], sigma_k2});
    wire [41:0] abs_s1_now = sigma_k1[42] ? (-sigma_k1[41:0]) : sigma_k1[41:0];
    wire [41:0] abs_s2_now = sigma_k2[42] ? (-sigma_k2[41:0]) : sigma_k2[41:0];
    wire [42:0] abs_ds_now = diff_sigma[43] ? (-diff_sigma[42:0]) : diff_sigma[42:0];

    wire shot_bad_now = (!np_valid) || (min_series == 16'd0) ||
                        (loaded_mask != 8'hFF) || shot_err_accum ||
                        (n_pulses_in != n_pulses_latched);

    wire [95:0] next_acc = mul_acc + (mul_op[0] ? mul_sh : 96'd0);

    // Pre-registered 3-bit comparator mode + single shared 94-bit borrow-subtractor
    reg [2:0]  cmp_mode;
    reg [93:0] cmp_a;
    reg [93:0] cmp_b;
    always @(*) begin
        case (cmp_mode)
            3'd0: begin cmp_a = {10'd0, s1_sq_r};           cmp_b = {10'd0, s2_sq_r};                 end
            3'd1: begin cmp_a = {10'd0, s2_sq_r};           cmp_b = {10'd0, s1_sq_r};                 end
            3'd2: begin cmp_a = {10'd0, scratch_93[83:0]};  cmp_b = {8'd0, lat_tau_lo86};             end
            3'd3: begin cmp_a = {8'd0, mul_acc[85:0]};      cmp_b = {8'd0, lat_tau_lo86};             end
            3'd4: begin cmp_a = {10'd0, s1_sq_r};           cmp_b = {12'd0, scratch_93[79:0], 2'b00}; end
            3'd5: begin cmp_a = {10'd0, s1_sq_r};           cmp_b = {11'd0, scratch_93[79:0], 3'b000};end
            3'd6: begin cmp_a = {10'd0, s2_sq_r};           cmp_b = {11'd0, scratch_93[79:0], 3'b000};end
            default: begin cmp_a = {31'd0, mul_acc[62:0]};  cmp_b = {1'b0, scratch_93};               end
        endcase
    end

    wire [94:0] diff_ba = {1'b0, cmp_b} - {1'b0, cmp_a};
    wire        a_gt_b  = diff_ba[94];

    reg [47:0] next_mul_op;
    reg [60:0] next_mul_sh61;
    always @(*) begin
        case (mac_phase)
            3'd0: begin next_mul_op = {6'd0, lat_abs_s2}; next_mul_sh61 = {19'd0, lat_abs_s2}; end
            3'd1: begin next_mul_op = {5'd0, lat_abs_ds}; next_mul_sh61 = {18'd0, lat_abs_ds}; end
            3'd2: begin next_mul_op = {8'd0, lat_np};     next_mul_sh61 = {21'd0, lat_np};     end
            3'd3: begin next_mul_op = {16'd0, lat_dk};    next_mul_sh61 = {32'd0, SI_C_29};    end
            3'd4: begin next_mul_op = {16'd0, lat_tclk};  next_mul_sh61 = mul_acc[60:0];       end
            default: begin next_mul_op = {16'd0, lat_dist}; next_mul_sh61 = {30'd0, TWO_E9_31}; end
        endcase
    end

    wire any_kill_commit = kill_latched_out || lat_shot_bad || (!lat_hash_ok) ||
                           flag_lc_bad || lat_ns_breach || lat_corr_bad;

    reg [3:0] commit_reason_kill;
    always @(*) begin
        if (kill_latched_out)   commit_reason_kill = REASON_KILL_LATCHED;
        else if (lat_shot_bad)  commit_reason_kill = REASON_KILL_SHOT_COUNT;
        else if (!lat_hash_ok)  commit_reason_kill = REASON_KILL_HASH_CHAIN;
        else if (flag_lc_bad)   commit_reason_kill = REASON_KILL_LIGHTCONE;
        else if (lat_ns_breach) commit_reason_kill = REASON_KILL_NO_SIGNALLING;
        else                    commit_reason_kill = REASON_KILL_SETTING_CORR;
    end

    reg [1:0] commit_port_ok;
    reg [3:0] commit_reason_ok;
    reg       commit_act_ok;
    always @(*) begin
        commit_act_ok = 1'b0;
        if (!lat_inv_closed) begin
            commit_port_ok   = PORT_HOLD;
            commit_reason_ok = REASON_HOLD_OPEN_LOOP_L1;
        end else if (lat_tomo_bad) begin
            commit_port_ok   = PORT_HOLD;
            commit_reason_ok = REASON_HOLD_L1_TOMO_SHIFT;
        end else if (!flag_sig_shift) begin
            commit_port_ok   = PORT_HOLD;
            commit_reason_ok = REASON_HOLD_QM_NULL_CONFIRMED;
        end else if ((!lat_quorum_ok) || (!lat_wit_ext)) begin
            commit_port_ok   = PORT_HOLD;
            commit_reason_ok = REASON_HOLD_NO_QUORUM_OR_WIT;
        end else begin
            commit_act_ok    = 1'b1;
            commit_port_ok   = PORT_OPEN;
            commit_reason_ok = REASON_OPEN_L3_WITNESSED;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy_out             <= 1'b0;
            eval_done_out        <= 1'b0;
            port_out             <= PORT_HOLD;
            reason_out           <= REASON_HOLD_QM_NULL_CONFIRMED;
            kill_latched_out     <= 1'b0;
            monitor_coupled_out  <= 1'b1;
            actuator_v_en_out    <= 1'b0;
            bell_violated_k1_out <= 1'b0;
            super_tsirelson_out  <= 1'b0;
            cycle_out            <= 64'd0;
            reset_epoch_out      <= 32'd0;
            s1_sq_r              <= 84'd0;
            s2_sq_r              <= 84'd0;
            loaded_mask          <= 8'd0;
            shot_err_accum       <= 1'b0;
        end else begin
            eval_done_out <= 1'b0;
            if (busy_out) begin
                cycle_out <= cycle_out + 64'd1;
                if (mac_phase < 3'd7) begin
                    if ((bit_cnt == 6'd47) && (mac_phase == 3'd0) && (!kill_latched_out)) begin
                        s1_sq_r <= mul_acc[83:0];
                    end
                    if ((bit_cnt == 6'd47) && (mac_phase == 3'd1) && (!kill_latched_out)) begin
                        s2_sq_r <= mul_acc[83:0];
                    end
                end else begin
                    busy_out             <= 1'b0;
                    eval_done_out        <= 1'b1;
                    kill_latched_out     <= any_kill_commit ? 1'b1 : 1'b0;
                    monitor_coupled_out  <= any_kill_commit ? 1'b0 : 1'b1;
                    actuator_v_en_out    <= any_kill_commit ? 1'b0 : commit_act_ok;
                    port_out             <= any_kill_commit ? PORT_KILL : commit_port_ok;
                    reason_out           <= any_kill_commit ? commit_reason_kill : commit_reason_ok;
                    bell_violated_k1_out <= any_kill_commit ? 1'b0 : flag_bell_viol;
                    super_tsirelson_out  <= any_kill_commit ? 1'b0 : flag_super_ts;
                    if (any_kill_commit) begin
                        s1_sq_r <= 84'd0;
                        s2_sq_r <= 84'd0;
                    end
                end
            end else if (l01_reset_strobe) begin
                cycle_out <= cycle_out + 64'd1;
                if (!l01_witness_ok) begin
                    if (kill_latched_out) begin
                        port_out   <= PORT_KILL;
                        reason_out <= REASON_KILL_LATCHED;
                    end else begin
                        actuator_v_en_out <= 1'b0;
                        port_out          <= PORT_HOLD;
                        reason_out        <= REASON_HOLD_NO_QUORUM_OR_WIT;
                    end
                end else begin
                    reset_epoch_out      <= reset_epoch_out + 32'd1;
                    kill_latched_out     <= 1'b0;
                    monitor_coupled_out  <= 1'b1;
                    actuator_v_en_out    <= 1'b0;
                    port_out             <= PORT_HOLD;
                    reason_out           <= REASON_HOLD_NO_QUORUM_OR_WIT;
                    bell_violated_k1_out <= 1'b0;
                    super_tsirelson_out  <= 1'b0;
                    s1_sq_r              <= 84'd0;
                    s2_sq_r              <= 84'd0;
                end
            end else if (load_en) begin
                cycle_out <= cycle_out + 64'd1;
                if (slot_idx == 3'd0) begin
                    loaded_mask    <= slot_bit;
                    shot_err_accum <= (!ok_arm);
                end else begin
                    loaded_mask <= loaded_mask | slot_bit;
                    if ((loaded_mask != (slot_bit - 8'd1)) ||
                        (n_pulses_in != n_pulses_latched) || (!ok_arm)) begin
                        shot_err_accum <= 1'b1;
                    end
                end
            end else if (eval_en) begin
                cycle_out <= cycle_out + 64'd1;
                busy_out  <= 1'b1;
            end
        end
    end

    always @(posedge clk) begin
        // Stage-B pipelined No-Signalling accumulator (runs 1 cycle after load_en)
        if (ns_pipe_vld) begin
            max_ns_dev <= (pipe_dev >= base_ns) ? pipe_dev : base_ns;
        end else if (ns_pipe_clr) begin
            max_ns_dev <= 41'd0;
        end
        ns_pipe_vld <= 1'b0;
        ns_pipe_clr <= 1'b0;

        if (busy_out) begin
            if ((mac_phase == 3'd0) && (bit_cnt == 6'd1)) begin
                lat_ns_breach <= (max_ns_dev > {1'b0, lat_tau_ns});
            end
            if (mac_phase < 3'd7) begin
                if (mac_phase == 3'd2) begin
                    if (bit_cnt == 6'd0) begin
                        s1_gt_s2   <= a_gt_b;
                        scratch_93 <= {9'd0, diff_ba[83:0]};
                        cmp_mode   <= 3'd1;
                    end else if (bit_cnt == 6'd1) begin
                        if (s1_gt_s2) scratch_93 <= {9'd0, diff_ba[83:0]};
                        cmp_mode <= 3'd2;
                    end else if (bit_cnt == 6'd2) begin
                        flag_sig_shift <= (!lat_tau_hi_nz) && a_gt_b;
                        cmp_mode       <= 3'd3;
                    end
                end else if (mac_phase == 3'd4) begin
                    if (bit_cnt == 6'd0) begin
                        flag_bell_viol <= a_gt_b;
                        cmp_mode       <= 3'd5;
                    end else if (bit_cnt == 6'd1) begin
                        flag_super_ts <= a_gt_b;
                        cmp_mode      <= 3'd6;
                    end else if (bit_cnt == 6'd2) begin
                        if (a_gt_b) flag_super_ts <= 1'b1;
                        cmp_mode <= 3'd7;
                    end
                end

                if (bit_cnt < 6'd47) begin
                    bit_cnt <= bit_cnt + 6'd1;
                    mul_acc <= next_acc;
                    mul_op  <= (mul_op >> 1);
                    mul_sh  <= (mul_sh << 1);
                end else begin
                    bit_cnt   <= 6'd0;
                    mac_phase <= mac_phase + 3'd1;
                    mul_acc   <= 96'd0;
                    mul_op    <= next_mul_op;
                    mul_sh    <= {35'd0, next_mul_sh61};
                    if (mac_phase == 3'd1) begin
                        cmp_mode <= 3'd0;
                    end else if (mac_phase == 3'd2) begin
                        if ((!lat_tau_hi_nz) && a_gt_b) flag_sig_shift <= 1'b1;
                    end else if (mac_phase == 3'd3) begin
                        scratch_93 <= {13'd0, mul_acc[79:0]};
                        cmp_mode   <= 3'd4;
                    end else if (mac_phase == 3'd5) begin
                        scratch_93 <= mul_acc[92:0];
                    end else if (mac_phase == 3'd6) begin
                        flag_lc_bad <= lat_lc_zero || (!a_gt_b);
                    end
                end
            end
        end else if ((!l01_reset_strobe) && load_en) begin
            if (slot_idx == 3'd0) begin
                n_pulses_latched <= n_pulses_in;
                ns_pipe_clr      <= 1'b1;
            end
            if (mn_idx == 2'd0) begin
                if (!arm_idx) sigma_k1 <= c_signed;
                else          sigma_k2 <= c_signed;
                pa_reg  <= cur_pa;
                pb0_reg <= cur_pb;
            end else begin
                if (!arm_idx) sigma_k1 <= sigma_k1 + c_signed;
                else          sigma_k2 <= sigma_k2 + c_signed;
                ns_pipe_vld <= 1'b1;
                ns_d1       <= sub_main;
                ns_d2       <= is_idx3 ? sub_b1 : 42'sd0;
                if (mn_idx == 2'd1) begin
                    pb1_reg <= cur_pb;
                end else if (mn_idx == 2'd2) begin
                    pa_reg  <= cur_pa;
                end
            end
        end else if ((!l01_reset_strobe) && (!load_en) && eval_en) begin
            mac_phase      <= 3'd0;
            cmp_mode       <= 3'd0;
            bit_cnt        <= 6'd0;
            mul_op         <= {6'd0, abs_s1_now};
            mul_sh         <= {54'd0, abs_s1_now};
            mul_acc        <= 96'd0;
            flag_sig_shift <= 1'b0;
            flag_bell_viol <= 1'b0;
            flag_super_ts  <= 1'b0;
            flag_lc_bad    <= 1'b0;

            lat_shot_bad   <= shot_bad_now;
            lat_lc_zero    <= (delta_k_cycles == 32'd0) || (t_clk_ps == 32'd0) || (dist_mm == 32'd0);
            lat_tau_ns     <= tau_ns;
            lat_corr_bad   <= (setting_corr_abs > tau_indep);
            lat_hash_ok    <= hash_valid;
            lat_inv_closed <= involution_closed;
            lat_wit_ext    <= witness_ext;
            lat_tomo_bad   <= (tomo_frob_diff_sq > tau_tomo_sq);
            lat_quorum_ok  <= (replicated_series >= min_series);
            lat_abs_s2     <= abs_s2_now;
            lat_abs_ds     <= abs_ds_now;
            lat_np         <= n_pulses_in;
            lat_dk         <= delta_k_cycles;
            lat_tclk       <= t_clk_ps;
            lat_dist       <= dist_mm;
            lat_tau_lo86   <= tau_diff_sq[85:0];
            lat_tau_hi_nz  <= (|tau_diff_sq[127:86]);
        end
    end

endmodule
`default_nettype wire
