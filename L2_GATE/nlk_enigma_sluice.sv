// =============================================================================
// KY-Enigma v1.1 -> NLK Consequence Sluice & Spatial Coordinate Board Gauge
// Module   : nlk_enigma_sluice
// Architecture : 9-stage pipelined mod-26 Enigma permutation core + 22-step
//                shift-add Landauer verifier + 8-slot spatial Coordinate Board
//                gauge + 8-deep reversible LIFO stack (0 SB_MAC16, 0 FP, 0 %).
// Parity       : 100% cycle- and bit-exact with nlk_enigma_sluice.h (C11).
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module nlk_enigma_sluice (
    input  wire        clk,
    input  wire        rst_n,

    // Control strobes
    input  wire        l01_reset_strobe,
    input  wire        l01_witness_ok,
    input  wire        selftest_ok,

    input  wire        board_load_en,
    input  wire [2:0]  board_slot_idx,
    input  wire        board_slot_present,

    input  wire        eval_step_en,
    input  wire        board_eval_en,
    input  wire [3:0]  board_expected_steps,
    input  wire [14:0] board_q0_flat,

    input  wire        lifo_pop_en,
    input  wire        lifo_tamper_inject,

    // Candidate, configuration, and physical guard inputs
    input  wire [14:0] ring_flat,
    input  wire        plug_en,
    input  wire [4:0]  x_in,
    input  wire [4:0]  y_cand,
    input  wire [14:0] q_before_flat,
    input  wire [14:0] q_prop_flat,
    input  wire [31:0] seq_num,
    input  wire        meas_en,
    input  wire        meas_stale,
    input  wire [31:0] e_err,
    input  wire [31:0] sigma_ref,
    input  wire [31:0] bits_erased,
    input  wire [63:0] q_diss_rj,
    input  wire        hash_valid,
    input  wire        wal_ready,
    input  wire        crash_inject,
    input  wire        l2_profile,
    input  wire        hw_verified,
    input  wire        witness_ext,

    // Registered outputs
    output reg         busy_out,
    output reg         eval_done_out,
    output reg  [1:0]  port_out,
    output reg  [3:0]  reason_out,
    output reg         kill_latched_out,
    output reg         outcome_unknown_out,
    output reg         monitor_coupled_out,
    output reg         actuator_v_en_out,
    output wire [7:0]  status_byte_out,
    output reg  [4:0]  y_out,
    output reg  [14:0] q_auth_flat_out,
    output reg  [3:0]  lifo_depth_out,
    output reg  [31:0] seq_prev_out,
    output reg  [31:0] reset_epoch_out,
    output reg  [63:0] cycle_out
);

    localparam [1:0] PORT_HOLD = 2'd0;
    localparam [1:0] PORT_OPEN = 2'd1;
    localparam [1:0] PORT_KILL = 2'd2;

    localparam [3:0] REASON_OPEN_VERIFIED         = 4'd0;
    localparam [3:0] REASON_OPEN_BOARD_GAUGE      = 4'd1;
    localparam [3:0] REASON_OPEN_LIFO_REWIND      = 4'd2;
    localparam [3:0] REASON_HOLD_MEAS_STALE       = 4'd3;
    localparam [3:0] REASON_HOLD_BOUNDARY_BAND    = 4'd4;
    localparam [3:0] REASON_HOLD_OUTCOME_UNKNOWN  = 4'd5;
    localparam [3:0] REASON_HOLD_AUTH_OR_REPLAY   = 4'd6;
    localparam [3:0] REASON_HOLD_UNVERIFIED_HW    = 4'd7;
    localparam [3:0] REASON_HOLD_WAL_FAILURE      = 4'd8;
    localparam [3:0] REASON_HOLD_INCOMPLETE_BOARD = 4'd9;
    localparam [3:0] REASON_HOLD_LIFO_EMPTY       = 4'd10;
    localparam [3:0] REASON_KILL_LATCHED          = 4'd11;
    localparam [3:0] REASON_KILL_WAL_OR_RING      = 4'd12;
    localparam [3:0] REASON_KILL_STATE_OR_INVOL   = 4'd13;
    localparam [3:0] REASON_KILL_FIXED_OR_THERMO  = 4'd14;
    localparam [3:0] REASON_KILL_BOARD_OR_LIFO    = 4'd15;

    localparam [1:0] MODE_STEP  = 2'd0;
    localparam [1:0] MODE_BOARD = 2'd1;
    localparam [1:0] MODE_LIFO  = 2'd2;

    localparam [21:0] LANDAUER_CONST = 22'd2652306;

    assign status_byte_out = {
        1'b0,
        (lifo_depth_out != 4'd0),
        outcome_unknown_out,
        kill_latched_out,
        monitor_coupled_out,
        actuator_v_en_out,
        port_out
    };

    // Pure LUT4 bijective ROMs on 0..25 (zero BRAM/DSP needed)
    function automatic [4:0] r1_fwd_rom(input [4:0] idx);
        case (idx)
            5'd 0: r1_fwd_rom = 5'd4;
            5'd 1: r1_fwd_rom = 5'd10;
            5'd 2: r1_fwd_rom = 5'd12;
            5'd 3: r1_fwd_rom = 5'd5;
            5'd 4: r1_fwd_rom = 5'd11;
            5'd 5: r1_fwd_rom = 5'd6;
            5'd 6: r1_fwd_rom = 5'd3;
            5'd 7: r1_fwd_rom = 5'd16;
            5'd 8: r1_fwd_rom = 5'd21;
            5'd 9: r1_fwd_rom = 5'd25;
            5'd10: r1_fwd_rom = 5'd13;
            5'd11: r1_fwd_rom = 5'd19;
            5'd12: r1_fwd_rom = 5'd14;
            5'd13: r1_fwd_rom = 5'd22;
            5'd14: r1_fwd_rom = 5'd24;
            5'd15: r1_fwd_rom = 5'd7;
            5'd16: r1_fwd_rom = 5'd23;
            5'd17: r1_fwd_rom = 5'd20;
            5'd18: r1_fwd_rom = 5'd18;
            5'd19: r1_fwd_rom = 5'd15;
            5'd20: r1_fwd_rom = 5'd0;
            5'd21: r1_fwd_rom = 5'd8;
            5'd22: r1_fwd_rom = 5'd1;
            5'd23: r1_fwd_rom = 5'd17;
            5'd24: r1_fwd_rom = 5'd2;
            5'd25: r1_fwd_rom = 5'd9;
            default: r1_fwd_rom = 5'd0;
        endcase
    endfunction
    function automatic [4:0] r2_fwd_rom(input [4:0] idx);
        case (idx)
            5'd 0: r2_fwd_rom = 5'd0;
            5'd 1: r2_fwd_rom = 5'd9;
            5'd 2: r2_fwd_rom = 5'd3;
            5'd 3: r2_fwd_rom = 5'd10;
            5'd 4: r2_fwd_rom = 5'd18;
            5'd 5: r2_fwd_rom = 5'd8;
            5'd 6: r2_fwd_rom = 5'd17;
            5'd 7: r2_fwd_rom = 5'd20;
            5'd 8: r2_fwd_rom = 5'd23;
            5'd 9: r2_fwd_rom = 5'd1;
            5'd10: r2_fwd_rom = 5'd11;
            5'd11: r2_fwd_rom = 5'd7;
            5'd12: r2_fwd_rom = 5'd22;
            5'd13: r2_fwd_rom = 5'd19;
            5'd14: r2_fwd_rom = 5'd12;
            5'd15: r2_fwd_rom = 5'd2;
            5'd16: r2_fwd_rom = 5'd16;
            5'd17: r2_fwd_rom = 5'd6;
            5'd18: r2_fwd_rom = 5'd25;
            5'd19: r2_fwd_rom = 5'd13;
            5'd20: r2_fwd_rom = 5'd15;
            5'd21: r2_fwd_rom = 5'd24;
            5'd22: r2_fwd_rom = 5'd5;
            5'd23: r2_fwd_rom = 5'd21;
            5'd24: r2_fwd_rom = 5'd14;
            5'd25: r2_fwd_rom = 5'd4;
            default: r2_fwd_rom = 5'd0;
        endcase
    endfunction
    function automatic [4:0] r3_fwd_rom(input [4:0] idx);
        case (idx)
            5'd 0: r3_fwd_rom = 5'd1;
            5'd 1: r3_fwd_rom = 5'd3;
            5'd 2: r3_fwd_rom = 5'd5;
            5'd 3: r3_fwd_rom = 5'd7;
            5'd 4: r3_fwd_rom = 5'd9;
            5'd 5: r3_fwd_rom = 5'd11;
            5'd 6: r3_fwd_rom = 5'd2;
            5'd 7: r3_fwd_rom = 5'd15;
            5'd 8: r3_fwd_rom = 5'd17;
            5'd 9: r3_fwd_rom = 5'd19;
            5'd10: r3_fwd_rom = 5'd23;
            5'd11: r3_fwd_rom = 5'd21;
            5'd12: r3_fwd_rom = 5'd25;
            5'd13: r3_fwd_rom = 5'd13;
            5'd14: r3_fwd_rom = 5'd24;
            5'd15: r3_fwd_rom = 5'd4;
            5'd16: r3_fwd_rom = 5'd8;
            5'd17: r3_fwd_rom = 5'd22;
            5'd18: r3_fwd_rom = 5'd6;
            5'd19: r3_fwd_rom = 5'd0;
            5'd20: r3_fwd_rom = 5'd10;
            5'd21: r3_fwd_rom = 5'd12;
            5'd22: r3_fwd_rom = 5'd20;
            5'd23: r3_fwd_rom = 5'd18;
            5'd24: r3_fwd_rom = 5'd16;
            5'd25: r3_fwd_rom = 5'd14;
            default: r3_fwd_rom = 5'd0;
        endcase
    endfunction
    function automatic [4:0] r1_inv_rom(input [4:0] idx);
        case (idx)
            5'd 0: r1_inv_rom = 5'd20;
            5'd 1: r1_inv_rom = 5'd22;
            5'd 2: r1_inv_rom = 5'd24;
            5'd 3: r1_inv_rom = 5'd6;
            5'd 4: r1_inv_rom = 5'd0;
            5'd 5: r1_inv_rom = 5'd3;
            5'd 6: r1_inv_rom = 5'd5;
            5'd 7: r1_inv_rom = 5'd15;
            5'd 8: r1_inv_rom = 5'd21;
            5'd 9: r1_inv_rom = 5'd25;
            5'd10: r1_inv_rom = 5'd1;
            5'd11: r1_inv_rom = 5'd4;
            5'd12: r1_inv_rom = 5'd2;
            5'd13: r1_inv_rom = 5'd10;
            5'd14: r1_inv_rom = 5'd12;
            5'd15: r1_inv_rom = 5'd19;
            5'd16: r1_inv_rom = 5'd7;
            5'd17: r1_inv_rom = 5'd23;
            5'd18: r1_inv_rom = 5'd18;
            5'd19: r1_inv_rom = 5'd11;
            5'd20: r1_inv_rom = 5'd17;
            5'd21: r1_inv_rom = 5'd8;
            5'd22: r1_inv_rom = 5'd13;
            5'd23: r1_inv_rom = 5'd16;
            5'd24: r1_inv_rom = 5'd14;
            5'd25: r1_inv_rom = 5'd9;
            default: r1_inv_rom = 5'd0;
        endcase
    endfunction
    function automatic [4:0] r2_inv_rom(input [4:0] idx);
        case (idx)
            5'd 0: r2_inv_rom = 5'd0;
            5'd 1: r2_inv_rom = 5'd9;
            5'd 2: r2_inv_rom = 5'd15;
            5'd 3: r2_inv_rom = 5'd2;
            5'd 4: r2_inv_rom = 5'd25;
            5'd 5: r2_inv_rom = 5'd22;
            5'd 6: r2_inv_rom = 5'd17;
            5'd 7: r2_inv_rom = 5'd11;
            5'd 8: r2_inv_rom = 5'd5;
            5'd 9: r2_inv_rom = 5'd1;
            5'd10: r2_inv_rom = 5'd3;
            5'd11: r2_inv_rom = 5'd10;
            5'd12: r2_inv_rom = 5'd14;
            5'd13: r2_inv_rom = 5'd19;
            5'd14: r2_inv_rom = 5'd24;
            5'd15: r2_inv_rom = 5'd20;
            5'd16: r2_inv_rom = 5'd16;
            5'd17: r2_inv_rom = 5'd6;
            5'd18: r2_inv_rom = 5'd4;
            5'd19: r2_inv_rom = 5'd13;
            5'd20: r2_inv_rom = 5'd7;
            5'd21: r2_inv_rom = 5'd23;
            5'd22: r2_inv_rom = 5'd12;
            5'd23: r2_inv_rom = 5'd8;
            5'd24: r2_inv_rom = 5'd21;
            5'd25: r2_inv_rom = 5'd18;
            default: r2_inv_rom = 5'd0;
        endcase
    endfunction
    function automatic [4:0] r3_inv_rom(input [4:0] idx);
        case (idx)
            5'd 0: r3_inv_rom = 5'd19;
            5'd 1: r3_inv_rom = 5'd0;
            5'd 2: r3_inv_rom = 5'd6;
            5'd 3: r3_inv_rom = 5'd1;
            5'd 4: r3_inv_rom = 5'd15;
            5'd 5: r3_inv_rom = 5'd2;
            5'd 6: r3_inv_rom = 5'd18;
            5'd 7: r3_inv_rom = 5'd3;
            5'd 8: r3_inv_rom = 5'd16;
            5'd 9: r3_inv_rom = 5'd4;
            5'd10: r3_inv_rom = 5'd20;
            5'd11: r3_inv_rom = 5'd5;
            5'd12: r3_inv_rom = 5'd21;
            5'd13: r3_inv_rom = 5'd13;
            5'd14: r3_inv_rom = 5'd25;
            5'd15: r3_inv_rom = 5'd7;
            5'd16: r3_inv_rom = 5'd24;
            5'd17: r3_inv_rom = 5'd8;
            5'd18: r3_inv_rom = 5'd23;
            5'd19: r3_inv_rom = 5'd9;
            5'd20: r3_inv_rom = 5'd22;
            5'd21: r3_inv_rom = 5'd11;
            5'd22: r3_inv_rom = 5'd17;
            5'd23: r3_inv_rom = 5'd10;
            5'd24: r3_inv_rom = 5'd14;
            5'd25: r3_inv_rom = 5'd12;
            default: r3_inv_rom = 5'd0;
        endcase
    endfunction
    function automatic [4:0] ukw_rom(input [4:0] idx);
        case (idx)
            5'd 0: ukw_rom = 5'd24;
            5'd 1: ukw_rom = 5'd17;
            5'd 2: ukw_rom = 5'd20;
            5'd 3: ukw_rom = 5'd7;
            5'd 4: ukw_rom = 5'd16;
            5'd 5: ukw_rom = 5'd18;
            5'd 6: ukw_rom = 5'd11;
            5'd 7: ukw_rom = 5'd3;
            5'd 8: ukw_rom = 5'd15;
            5'd 9: ukw_rom = 5'd23;
            5'd10: ukw_rom = 5'd13;
            5'd11: ukw_rom = 5'd6;
            5'd12: ukw_rom = 5'd14;
            5'd13: ukw_rom = 5'd10;
            5'd14: ukw_rom = 5'd12;
            5'd15: ukw_rom = 5'd8;
            5'd16: ukw_rom = 5'd4;
            5'd17: ukw_rom = 5'd1;
            5'd18: ukw_rom = 5'd5;
            5'd19: ukw_rom = 5'd25;
            5'd20: ukw_rom = 5'd2;
            5'd21: ukw_rom = 5'd22;
            5'd22: ukw_rom = 5'd21;
            5'd23: ukw_rom = 5'd9;
            5'd24: ukw_rom = 5'd0;
            5'd25: ukw_rom = 5'd19;
            default: ukw_rom = 5'd0;
        endcase
    endfunction
    function automatic [4:0] plug_rom(input [4:0] idx);
        case (idx)
            5'd 0: plug_rom = 5'd12;
            5'd 1: plug_rom = 5'd1;
            5'd 2: plug_rom = 5'd2;
            5'd 3: plug_rom = 5'd3;
            5'd 4: plug_rom = 5'd4;
            5'd 5: plug_rom = 5'd8;
            5'd 6: plug_rom = 5'd6;
            5'd 7: plug_rom = 5'd7;
            5'd 8: plug_rom = 5'd5;
            5'd 9: plug_rom = 5'd9;
            5'd10: plug_rom = 5'd10;
            5'd11: plug_rom = 5'd11;
            5'd12: plug_rom = 5'd0;
            5'd13: plug_rom = 5'd21;
            5'd14: plug_rom = 5'd14;
            5'd15: plug_rom = 5'd15;
            5'd16: plug_rom = 5'd16;
            5'd17: plug_rom = 5'd17;
            5'd18: plug_rom = 5'd18;
            5'd19: plug_rom = 5'd19;
            5'd20: plug_rom = 5'd20;
            5'd21: plug_rom = 5'd13;
            5'd22: plug_rom = 5'd22;
            5'd23: plug_rom = 5'd23;
            5'd24: plug_rom = 5'd24;
            5'd25: plug_rom = 5'd25;
            default: plug_rom = 5'd0;
        endcase
    endfunction

    function automatic [4:0] mod26_add(input [4:0] a, input [4:0] b);
        reg [5:0] s;
        begin
            s = {1'b0, a} + {1'b0, b};
            mod26_add = (s >= 6'd26) ? (s[4:0] - 5'd26) : s[4:0];
        end
    endfunction

    function automatic [4:0] mod26_sub(input [4:0] a, input [4:0] b);
        reg [5:0] d;
        begin
            d = (a >= b) ? ({1'b0, a} - {1'b0, b}) : ({1'b0, a} + 6'd26 - {1'b0, b});
            mod26_sub = d[4:0];
        end
    endfunction

    function automatic q_flat_valid(input [14:0] qf);
        begin
            q_flat_valid = (qf[14:10] < 5'd26) && (qf[9:5] < 5'd26) && (qf[4:0] < 5'd26);
        end
    endfunction

    function automatic [14:0] propose_next_q(input [14:0] qf);
        reg [4:0] ql, qm, qr, nl, nm, nr;
        reg       m_notch, r_notch;
        begin
            ql = qf[14:10];
            qm = qf[9:5];
            qr = qf[4:0];
            m_notch = (qm == 5'd4);
            r_notch = (qr == 5'd21);
            nl = m_notch ? ((ql == 5'd25) ? 5'd0 : (ql + 5'd1)) : ql;
            nm = (m_notch || r_notch) ? ((qm == 5'd25) ? 5'd0 : (qm + 5'd1)) : qm;
            nr = (qr == 5'd25) ? 5'd0 : (qr + 5'd1);
            propose_next_q = {nl, nm, nr};
        end
    endfunction

    // Explicit register banks (zero Yosys memory-replacement warnings!)
    reg [7:0]  board_mask;
    reg [3:0]  board_cnt;
    reg        board_seq_err;
    reg [25:0] board_m0, board_m1, board_m2, board_m3;
    reg [25:0] board_m4, board_m5, board_m6, board_m7;

    reg [39:0] lifo_m0, lifo_m1, lifo_m2, lifo_m3;
    reg [39:0] lifo_m4, lifo_m5, lifo_m6, lifo_m7;

    reg [1:0]  op_mode;
    reg [4:0]  step_cnt;
    reg [3:0]  slot_cursor;

    reg [14:0] lat_ring;
    reg        lat_plug_en;
    reg [4:0]  lat_x_in;
    reg [4:0]  lat_y_cand;
    reg [14:0] lat_q_bef;
    reg [14:0] lat_q_prop;
    reg [31:0] lat_seq_num;
    reg        lat_meas_en;
    reg        lat_meas_stale;
    reg [31:0] lat_e_err;
    reg [31:0] lat_sigma;
    reg [63:0] lat_q_diss;
    reg        lat_hash_ok;
    reg        lat_wal_ready;
    reg        lat_crash;
    reg        lat_l2_prof;
    reg        lat_hw_ver;
    reg        lat_wit_ext;
    reg [3:0]  lat_exp_steps;
    reg [14:0] lat_board_q0;
    reg        lat_tamper;
    reg        lat_ring_ok;
    reg        lat_qprop_ok;
    reg        lat_step_pre_err;
    reg        lat_fixed_pt;
    reg        lat_auth_hold;

    // Two-beat Enigma permutation pipeline (address beat -> ROM+sub beat: ~11 LUT levels/cycle!)
    reg [4:0]  perm_c;
    reg [4:0]  rom_idx_r;
    reg [4:0]  cur_sh_r;
    reg [2:0]  rom_sel_r;
    reg [4:0]  sh0, sh1, sh2;
    reg [14:0] exp_q_reg;
    reg        inv_match_ok;
    reg        lifo_ok_flag;

    // Parallel 22-cycle Landauer shift-add & rational 10e / 9s / 15s registers
    reg [21:0] land_op;
    reg [54:0] land_sh;
    reg [54:0] land_acc;
    reg [35:0] ten_e_r;
    reg [35:0] nine_s_r;
    reg [35:0] fifteen_s_r;
    reg        meas_kill_flag;
    reg        meas_hold_band_flag;
    reg        land_kill_flag;

    // Board walker accumulators
    reg [14:0] board_prev_q;
    reg        board_seam_err;
    reg        board_missing_flag;
    reg [4:0]  board_last_y;
    reg [25:0] cur_slot_r;

    reg [25:0] mux_slot_word;
    always @(*) begin
        case (slot_cursor[2:0])
            3'd0: mux_slot_word = board_m0;
            3'd1: mux_slot_word = board_m1;
            3'd2: mux_slot_word = board_m2;
            3'd3: mux_slot_word = board_m3;
            3'd4: mux_slot_word = board_m4;
            3'd5: mux_slot_word = board_m5;
            3'd6: mux_slot_word = board_m6;
            default: mux_slot_word = board_m7;
        endcase
    end

    wire        cur_sl_pres = cur_slot_r[25];
    wire [4:0]  cur_sl_x    = cur_slot_r[24:20];
    wire [4:0]  cur_sl_y    = cur_slot_r[19:15];
    wire [14:0] cur_sl_q    = cur_slot_r[14:0];

    wire [14:0] top_q_bef   = lifo_m0[39:25];
    wire [14:0] top_q_prop  = lifo_m0[24:10];
    wire [4:0]  top_x       = lifo_m0[9:5];
    wire [4:0]  top_y       = lifo_m0[4:0];

    reg [4:0] rom_val;
    always @(*) begin
        case (rom_sel_r)
            3'd0: rom_val = r3_fwd_rom(rom_idx_r);
            3'd1: rom_val = r2_fwd_rom(rom_idx_r);
            3'd2: rom_val = r1_fwd_rom(rom_idx_r);
            3'd3: rom_val = r1_inv_rom(rom_idx_r);
            3'd4: rom_val = r2_inv_rom(rom_idx_r);
            default: rom_val = r3_inv_rom(rom_idx_r);
        endcase
    end
    wire [4:0] rotor_data_out = mod26_sub(rom_val, cur_sh_r);

    wire [7:0]  load_bit  = (8'd1 << board_slot_idx);
    wire [25:0] load_word = {board_slot_present, x_in, y_cand, q_prop_flat};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy_out            <= 1'b0;
            eval_done_out       <= 1'b0;
            port_out            <= PORT_HOLD;
            reason_out          <= REASON_HOLD_AUTH_OR_REPLAY;
            kill_latched_out    <= 1'b0;
            outcome_unknown_out <= 1'b0;
            monitor_coupled_out <= 1'b1;
            actuator_v_en_out   <= 1'b0;
            y_out               <= 5'd0;
            q_auth_flat_out     <= 15'd0;
            lifo_depth_out      <= 4'd0;
            seq_prev_out        <= 32'd0;
            reset_epoch_out     <= 32'd0;
            cycle_out           <= 64'd0;
            board_mask          <= 8'd0;
            board_cnt           <= 4'd0;
            board_seq_err       <= 1'b0;
            board_m0 <= 26'd0; board_m1 <= 26'd0; board_m2 <= 26'd0; board_m3 <= 26'd0;
            board_m4 <= 26'd0; board_m5 <= 26'd0; board_m6 <= 26'd0; board_m7 <= 26'd0;
            lifo_m0  <= 40'd0; lifo_m1  <= 40'd0; lifo_m2  <= 40'd0; lifo_m3  <= 40'd0;
            lifo_m4  <= 40'd0; lifo_m5  <= 40'd0; lifo_m6  <= 40'd0; lifo_m7  <= 40'd0;
        end else begin
            eval_done_out <= 1'b0;
            if (busy_out) begin
                cycle_out <= cycle_out + 64'd1;

                // MODE_STEP: 24 busy cycles (step_cnt 0..23 -> total 25 cycles)
                if (op_mode == MODE_STEP) begin
                    if (step_cnt < 5'd23) begin
                        step_cnt <= step_cnt + 5'd1;
                        if (step_cnt < 5'd22) begin
                            if (land_op[0]) begin
                                land_acc <= land_acc + land_sh;
                            end
                            land_op <= (land_op >> 1);
                            land_sh <= (land_sh << 1);
                        end else begin
                            land_kill_flag <= (lat_q_diss < {9'd0, land_acc});
                        end

                        case (step_cnt)
                            5'd0: begin
                                perm_c           <= lat_plug_en ? plug_rom(lat_y_cand) : lat_y_cand;
                                sh0              <= mod26_sub(lat_q_prop[14:10], lat_ring[14:10]);
                                sh1              <= mod26_sub(lat_q_prop[9:5],   lat_ring[9:5]);
                                sh2              <= mod26_sub(lat_q_prop[4:0],   lat_ring[4:0]);
                                exp_q_reg        <= propose_next_q(q_auth_flat_out);
                                lat_ring_ok      <= q_flat_valid(lat_ring);
                                lat_qprop_ok     <= q_flat_valid(lat_q_prop);
                                lat_step_pre_err <= (lat_q_bef != q_auth_flat_out) || (lat_x_in >= 5'd26) || (lat_y_cand >= 5'd26);
                                lat_fixed_pt     <= (lat_y_cand == lat_x_in);
                                lat_auth_hold    <= (!lat_wit_ext) || (lat_seq_num <= seq_prev_out) || (lat_seq_num == 32'hFFFF_FFFF);
                                ten_e_r          <= ({4'd0, lat_e_err} << 3) + ({4'd0, lat_e_err} << 1);
                                nine_s_r         <= ({4'd0, lat_sigma} << 3) + {4'd0, lat_sigma};
                                fifteen_s_r      <= ({4'd0, lat_sigma} << 4) - {4'd0, lat_sigma};
                            end
                            5'd1:  begin rom_idx_r <= mod26_add(perm_c, sh2); cur_sh_r <= sh2; rom_sel_r <= 3'd0; end
                            5'd2:  begin perm_c <= rotor_data_out; end
                            5'd3:  begin rom_idx_r <= mod26_add(perm_c, sh1); cur_sh_r <= sh1; rom_sel_r <= 3'd1; end
                            5'd4:  begin
                                perm_c              <= rotor_data_out;
                                meas_kill_flag      <= lat_meas_en && (lat_sigma != 32'd0) && (!lat_meas_stale) && (ten_e_r > fifteen_s_r);
                                meas_hold_band_flag <= lat_meas_en && (ten_e_r >= nine_s_r);
                            end
                            5'd5:  begin rom_idx_r <= mod26_add(perm_c, sh0); cur_sh_r <= sh0; rom_sel_r <= 3'd2; end
                            5'd6:  begin perm_c <= rotor_data_out; end
                            5'd7:  begin perm_c <= ukw_rom(perm_c); end
                            5'd8:  begin rom_idx_r <= mod26_add(perm_c, sh0); cur_sh_r <= sh0; rom_sel_r <= 3'd3; end
                            5'd9:  begin perm_c <= rotor_data_out; end
                            5'd10: begin rom_idx_r <= mod26_add(perm_c, sh1); cur_sh_r <= sh1; rom_sel_r <= 3'd4; end
                            5'd11: begin perm_c <= rotor_data_out; end
                            5'd12: begin rom_idx_r <= mod26_add(perm_c, sh2); cur_sh_r <= sh2; rom_sel_r <= 3'd5; end
                            5'd13: begin perm_c <= rotor_data_out; end
                            5'd14: begin perm_c <= lat_plug_en ? plug_rom(perm_c) : perm_c; end
                            5'd15: begin inv_match_ok <= (perm_c == lat_x_in) && (lat_q_prop == exp_q_reg); end
                            default: ;
                        endcase
                    end else begin
                        busy_out      <= 1'b0;
                        eval_done_out <= 1'b1;
                        if (kill_latched_out) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_LATCHED;
                            y_out               <= 5'd0;
                        end else if ((!lat_hash_ok) || (!lat_ring_ok)) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_WAL_OR_RING;
                            y_out               <= 5'd0;
                        end else if (lat_step_pre_err || (!lat_qprop_ok)) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_STATE_OR_INVOL;
                            y_out               <= 5'd0;
                        end else if (lat_fixed_pt) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_FIXED_OR_THERMO;
                            y_out               <= 5'd0;
                        end else if (!inv_match_ok) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_STATE_OR_INVOL;
                            y_out               <= 5'd0;
                        end else if (land_kill_flag || meas_kill_flag) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_FIXED_OR_THERMO;
                            y_out               <= 5'd0;
                        end else if (lat_meas_en && ((lat_sigma == 32'd0) || lat_meas_stale)) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_MEAS_STALE;
                            y_out               <= 5'd0;
                        end else if (meas_hold_band_flag) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_BOUNDARY_BAND;
                            y_out               <= 5'd0;
                        end else if (outcome_unknown_out) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_OUTCOME_UNKNOWN;
                            y_out               <= 5'd0;
                        end else if (lat_auth_hold) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_AUTH_OR_REPLAY;
                            y_out               <= 5'd0;
                        end else if (lat_l2_prof && (!lat_hw_ver)) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_UNVERIFIED_HW;
                            y_out               <= 5'd0;
                        end else if (!lat_wal_ready) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_WAL_FAILURE;
                            y_out               <= 5'd0;
                        end else begin
                            q_auth_flat_out <= lat_q_prop;
                            seq_prev_out    <= lat_seq_num;
                            lifo_m7 <= lifo_m6; lifo_m6 <= lifo_m5; lifo_m5 <= lifo_m4; lifo_m4 <= lifo_m3;
                            lifo_m3 <= lifo_m2; lifo_m2 <= lifo_m1; lifo_m1 <= lifo_m0;
                            lifo_m0 <= {q_auth_flat_out, lat_q_prop, lat_x_in, lat_y_cand};
                            if (lifo_depth_out < 4'd8) begin
                                lifo_depth_out <= lifo_depth_out + 4'd1;
                            end
                            monitor_coupled_out <= 1'b1;
                            if (lat_crash) begin
                                outcome_unknown_out <= 1'b1;
                                actuator_v_en_out   <= 1'b0;
                                port_out            <= PORT_HOLD;
                                reason_out          <= REASON_HOLD_OUTCOME_UNKNOWN;
                                y_out               <= 5'd0;
                            end else begin
                                actuator_v_en_out <= lat_l2_prof;
                                port_out          <= PORT_OPEN;
                                reason_out        <= REASON_OPEN_VERIFIED;
                                y_out             <= lat_y_cand;
                            end
                        end
                    end

                // MODE_BOARD: 129 busy cycles (8 slots x 16 + 1 commit -> total 130 cycles)
                end else if (op_mode == MODE_BOARD) begin
                    if (slot_cursor < 4'd8) begin
                        if (step_cnt < 5'd15) begin
                            step_cnt <= step_cnt + 5'd1;
                            case (step_cnt)
                                5'd0: begin
                                    perm_c        <= lat_plug_en ? plug_rom(cur_sl_y) : cur_sl_y;
                                    sh0           <= mod26_sub(cur_sl_q[14:10], lat_ring[14:10]);
                                    sh1           <= mod26_sub(cur_sl_q[9:5],   lat_ring[9:5]);
                                    sh2           <= mod26_sub(cur_sl_q[4:0],   lat_ring[4:0]);
                                    exp_q_reg     <= propose_next_q(board_prev_q);
                                    lat_ring_ok   <= q_flat_valid(lat_ring);
                                    lat_auth_hold <= (!lat_wit_ext) || (lat_seq_num <= seq_prev_out) || (lat_seq_num == 32'hFFFF_FFFF);
                                end
                                5'd1:  begin rom_idx_r <= mod26_add(perm_c, sh2); cur_sh_r <= sh2; rom_sel_r <= 3'd0; end
                                5'd2:  begin perm_c <= rotor_data_out; end
                                5'd3:  begin rom_idx_r <= mod26_add(perm_c, sh1); cur_sh_r <= sh1; rom_sel_r <= 3'd1; end
                                5'd4:  begin perm_c <= rotor_data_out; end
                                5'd5:  begin rom_idx_r <= mod26_add(perm_c, sh0); cur_sh_r <= sh0; rom_sel_r <= 3'd2; end
                                5'd6:  begin perm_c <= rotor_data_out; end
                                5'd7:  begin perm_c <= ukw_rom(perm_c); end
                                5'd8:  begin rom_idx_r <= mod26_add(perm_c, sh0); cur_sh_r <= sh0; rom_sel_r <= 3'd3; end
                                5'd9:  begin perm_c <= rotor_data_out; end
                                5'd10: begin rom_idx_r <= mod26_add(perm_c, sh1); cur_sh_r <= sh1; rom_sel_r <= 3'd4; end
                                5'd11: begin perm_c <= rotor_data_out; end
                                5'd12: begin rom_idx_r <= mod26_add(perm_c, sh2); cur_sh_r <= sh2; rom_sel_r <= 3'd5; end
                                5'd13: begin perm_c <= rotor_data_out; end
                                5'd14: begin perm_c <= lat_plug_en ? plug_rom(perm_c) : perm_c; end
                                default: ;
                            endcase
                        end else begin
                            step_cnt    <= 5'd0;
                            slot_cursor <= slot_cursor + 4'd1;
                            if (slot_cursor < board_cnt) begin
                                if ((!q_flat_valid(cur_sl_q)) || (cur_sl_q != exp_q_reg)) begin
                                    board_seam_err <= 1'b1;
                                end else if (!cur_sl_pres) begin
                                    board_missing_flag <= 1'b1;
                                    board_prev_q       <= cur_sl_q;
                                end else if ((cur_sl_x >= 5'd26) || (cur_sl_y >= 5'd26) ||
                                             (cur_sl_y == cur_sl_x) || (perm_c != cur_sl_x)) begin
                                    board_seam_err <= 1'b1;
                                end else begin
                                    board_prev_q <= cur_sl_q;
                                    board_last_y <= cur_sl_y;
                                end
                            end
                            // Pre-fetch next slot word into cur_slot_r!
                            case (slot_cursor[2:0])
                                3'd0: cur_slot_r <= board_m1;
                                3'd1: cur_slot_r <= board_m2;
                                3'd2: cur_slot_r <= board_m3;
                                3'd3: cur_slot_r <= board_m4;
                                3'd4: cur_slot_r <= board_m5;
                                3'd5: cur_slot_r <= board_m6;
                                default: cur_slot_r <= board_m7;
                            endcase
                        end
                    end else begin
                        busy_out      <= 1'b0;
                        eval_done_out <= 1'b1;
                        if (kill_latched_out) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_LATCHED;
                            y_out               <= 5'd0;
                        end else if ((!lat_hash_ok) || (!lat_ring_ok)) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_WAL_OR_RING;
                            y_out               <= 5'd0;
                        end else if (board_seq_err || (lat_exp_steps == 4'd0) || (lat_exp_steps > 4'd8) ||
                                     (lat_board_q0 != q_auth_flat_out) || (board_cnt > lat_exp_steps) ||
                                     board_seam_err) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_BOARD_OR_LIFO;
                            y_out               <= 5'd0;
                        end else if (outcome_unknown_out) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_OUTCOME_UNKNOWN;
                            y_out               <= 5'd0;
                        end else if ((board_cnt < lat_exp_steps) || board_missing_flag) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_INCOMPLETE_BOARD;
                            y_out               <= 5'd0;
                        end else if (lat_auth_hold) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_AUTH_OR_REPLAY;
                            y_out               <= 5'd0;
                        end else if (lat_l2_prof && (!lat_hw_ver)) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_UNVERIFIED_HW;
                            y_out               <= 5'd0;
                        end else if (!lat_wal_ready) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_WAL_FAILURE;
                            y_out               <= 5'd0;
                        end else begin
                            q_auth_flat_out     <= board_prev_q;
                            seq_prev_out        <= lat_seq_num;
                            lifo_depth_out      <= 4'd0;
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= lat_l2_prof;
                            port_out            <= PORT_OPEN;
                            reason_out          <= REASON_OPEN_BOARD_GAUGE;
                            y_out               <= board_last_y;
                        end
                    end

                // MODE_LIFO: 17 busy cycles (step_cnt 0..16 -> total 18 cycles)
                end else begin
                    if (step_cnt < 5'd16) begin
                        step_cnt <= step_cnt + 5'd1;
                        case (step_cnt)
                            5'd0: begin
                                perm_c      <= lat_plug_en ? plug_rom(top_y) : top_y;
                                sh0         <= mod26_sub(top_q_prop[14:10], lat_ring[14:10]);
                                sh1         <= mod26_sub(top_q_prop[9:5],   lat_ring[9:5]);
                                sh2         <= mod26_sub(top_q_prop[4:0],   lat_ring[4:0]);
                                lat_ring_ok <= q_flat_valid(lat_ring);
                            end
                            5'd1:  begin rom_idx_r <= mod26_add(perm_c, sh2); cur_sh_r <= sh2; rom_sel_r <= 3'd0; end
                            5'd2:  begin perm_c <= rotor_data_out; end
                            5'd3:  begin rom_idx_r <= mod26_add(perm_c, sh1); cur_sh_r <= sh1; rom_sel_r <= 3'd1; end
                            5'd4:  begin perm_c <= rotor_data_out; end
                            5'd5:  begin rom_idx_r <= mod26_add(perm_c, sh0); cur_sh_r <= sh0; rom_sel_r <= 3'd2; end
                            5'd6:  begin perm_c <= rotor_data_out; end
                            5'd7:  begin perm_c <= ukw_rom(perm_c); end
                            5'd8:  begin rom_idx_r <= mod26_add(perm_c, sh0); cur_sh_r <= sh0; rom_sel_r <= 3'd3; end
                            5'd9:  begin perm_c <= rotor_data_out; end
                            5'd10: begin rom_idx_r <= mod26_add(perm_c, sh1); cur_sh_r <= sh1; rom_sel_r <= 3'd4; end
                            5'd11: begin perm_c <= rotor_data_out; end
                            5'd12: begin rom_idx_r <= mod26_add(perm_c, sh2); cur_sh_r <= sh2; rom_sel_r <= 3'd5; end
                            5'd13: begin perm_c <= rotor_data_out; end
                            5'd14: begin perm_c <= lat_plug_en ? plug_rom(perm_c) : perm_c; end
                            5'd15: begin
                                lifo_ok_flag <= (!lat_tamper) && (top_q_prop == q_auth_flat_out) &&
                                                (top_y != top_x) && (perm_c == top_x);
                            end
                            default: ;
                        endcase
                    end else begin
                        busy_out      <= 1'b0;
                        eval_done_out <= 1'b1;
                        if (kill_latched_out) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_LATCHED;
                            y_out               <= 5'd0;
                        end else if ((!lat_hash_ok) || (!lat_ring_ok)) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_WAL_OR_RING;
                            y_out               <= 5'd0;
                        end else if (outcome_unknown_out) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_OUTCOME_UNKNOWN;
                            y_out               <= 5'd0;
                        end else if (lifo_depth_out == 4'd0) begin
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_HOLD;
                            reason_out          <= REASON_HOLD_LIFO_EMPTY;
                            y_out               <= 5'd0;
                        end else if (!lifo_ok_flag) begin
                            kill_latched_out    <= 1'b1;
                            monitor_coupled_out <= 1'b0;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_KILL;
                            reason_out          <= REASON_KILL_BOARD_OR_LIFO;
                            y_out               <= 5'd0;
                        end else begin
                            q_auth_flat_out     <= top_q_bef;
                            lifo_m0 <= lifo_m1; lifo_m1 <= lifo_m2; lifo_m2 <= lifo_m3; lifo_m3 <= lifo_m4;
                            lifo_m4 <= lifo_m5; lifo_m5 <= lifo_m6; lifo_m6 <= lifo_m7; lifo_m7 <= 40'd0;
                            lifo_depth_out      <= lifo_depth_out - 4'd1;
                            monitor_coupled_out <= 1'b1;
                            actuator_v_en_out   <= 1'b0;
                            port_out            <= PORT_OPEN;
                            reason_out          <= REASON_OPEN_LIFO_REWIND;
                            y_out               <= perm_c;
                        end
                    end
                end

            end else if (l01_reset_strobe) begin
                cycle_out <= cycle_out + 64'd1;
                if ((!l01_witness_ok) || (!selftest_ok)) begin
                    if (kill_latched_out) begin
                        port_out   <= PORT_KILL;
                        reason_out <= REASON_KILL_LATCHED;
                        y_out      <= 5'd0;
                    end else begin
                        actuator_v_en_out <= 1'b0;
                        port_out          <= PORT_HOLD;
                        reason_out        <= REASON_HOLD_AUTH_OR_REPLAY;
                        y_out             <= 5'd0;
                    end
                end else begin
                    reset_epoch_out     <= reset_epoch_out + 32'd1;
                    kill_latched_out    <= 1'b0;
                    outcome_unknown_out <= 1'b0;
                    monitor_coupled_out <= 1'b1;
                    actuator_v_en_out   <= 1'b0;
                    port_out            <= PORT_HOLD;
                    reason_out          <= REASON_HOLD_AUTH_OR_REPLAY;
                    y_out               <= 5'd0;
                    lifo_depth_out      <= 4'd0;
                    board_mask          <= 8'd0;
                    board_cnt           <= 4'd0;
                    board_seq_err       <= 1'b0;
                end

            end else if (board_load_en) begin
                cycle_out <= cycle_out + 64'd1;
                if (board_slot_idx == 3'd0) begin
                    board_mask    <= load_bit;
                    board_cnt     <= 4'd1;
                    board_seq_err <= 1'b0;
                end else begin
                    if (board_mask != (load_bit - 8'd1)) begin
                        board_seq_err <= 1'b1;
                    end
                    board_mask <= board_mask | load_bit;
                    if (board_cnt < 4'd8) begin
                        board_cnt <= board_cnt + 4'd1;
                    end else begin
                        board_seq_err <= 1'b1;
                    end
                end
                case (board_slot_idx)
                    3'd0: board_m0 <= load_word;
                    3'd1: board_m1 <= load_word;
                    3'd2: board_m2 <= load_word;
                    3'd3: board_m3 <= load_word;
                    3'd4: board_m4 <= load_word;
                    3'd5: board_m5 <= load_word;
                    3'd6: board_m6 <= load_word;
                    default: board_m7 <= load_word;
                endcase

            end else if (eval_step_en) begin
                cycle_out      <= cycle_out + 64'd1;
                busy_out       <= 1'b1;
                op_mode        <= MODE_STEP;
                step_cnt       <= 5'd0;
                lat_ring       <= ring_flat;
                lat_plug_en    <= plug_en;
                lat_x_in       <= x_in;
                lat_y_cand     <= y_cand;
                lat_q_bef      <= q_before_flat;
                lat_q_prop     <= q_prop_flat;
                lat_seq_num    <= seq_num;
                lat_meas_en    <= meas_en;
                lat_meas_stale <= meas_stale;
                lat_e_err      <= e_err;
                lat_sigma      <= sigma_ref;
                lat_q_diss     <= q_diss_rj;
                lat_hash_ok    <= hash_valid;
                lat_wal_ready  <= wal_ready;
                lat_crash      <= crash_inject;
                lat_l2_prof    <= l2_profile;
                lat_hw_ver     <= hw_verified;
                lat_wit_ext    <= witness_ext;
                land_op        <= LANDAUER_CONST;
                land_sh        <= {23'd0, bits_erased};
                land_acc       <= 55'd0;

            end else if (board_eval_en) begin
                cycle_out          <= cycle_out + 64'd1;
                busy_out           <= 1'b1;
                op_mode            <= MODE_BOARD;
                step_cnt           <= 5'd0;
                slot_cursor        <= 4'd0;
                cur_slot_r         <= board_m0;
                lat_ring           <= ring_flat;
                lat_plug_en        <= plug_en;
                lat_ring_ok        <= q_flat_valid(ring_flat);
                lat_auth_hold      <= (!witness_ext) || (seq_num <= seq_prev_out) || (seq_num == 32'hFFFF_FFFF);
                lat_exp_steps      <= board_expected_steps;
                lat_board_q0       <= board_q0_flat;
                lat_seq_num        <= seq_num;
                lat_hash_ok        <= hash_valid;
                lat_wal_ready      <= wal_ready;
                lat_l2_prof        <= l2_profile;
                lat_hw_ver         <= hw_verified;
                lat_wit_ext        <= witness_ext;
                board_prev_q       <= q_auth_flat_out;
                board_seam_err     <= 1'b0;
                board_missing_flag <= 1'b0;
                board_last_y       <= 5'd0;

            end else if (lifo_pop_en) begin
                cycle_out   <= cycle_out + 64'd1;
                busy_out    <= 1'b1;
                op_mode     <= MODE_LIFO;
                step_cnt    <= 5'd0;
                lat_ring    <= ring_flat;
                lat_plug_en <= plug_en;
                lat_hash_ok <= hash_valid;
                lat_tamper  <= lifo_tamper_inject;
            end
        end
    end

endmodule
`default_nettype wire
