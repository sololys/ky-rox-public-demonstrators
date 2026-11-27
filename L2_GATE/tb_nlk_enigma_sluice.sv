// =============================================================================
// Canonical 24-Vector Testbench for nlk_enigma_sluice (RTL & Yosys cells_sim.v)
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module tb_nlk_enigma_sluice;

    reg         clk = 1'b0;
    reg         rst_n = 1'b0;

    reg         l01_reset_strobe = 1'b0;
    reg         l01_witness_ok = 1'b0;
    reg         selftest_ok = 1'b0;

    reg         board_load_en = 1'b0;
    reg  [2:0]  board_slot_idx = 3'd0;
    reg         board_slot_present = 1'b1;

    reg         eval_step_en = 1'b0;
    reg         board_eval_en = 1'b0;
    reg  [3:0]  board_expected_steps = 4'd4;
    reg  [14:0] board_q0_flat = 15'd0;

    reg         lifo_pop_en = 1'b0;
    reg         lifo_tamper_inject = 1'b0;

    reg  [14:0] ring_flat = 15'd0;
    reg         plug_en = 1'b1;
    reg  [4:0]  x_in = 5'd0;
    reg  [4:0]  y_cand = 5'd0;
    reg  [14:0] q_before_flat = 15'd0;
    reg  [14:0] q_prop_flat = 15'd0;
    reg  [31:0] seq_num = 32'd1;
    reg         meas_en = 1'b0;
    reg         meas_stale = 1'b0;
    reg  [31:0] e_err = 32'd0;
    reg  [31:0] sigma_ref = 32'd10;
    reg  [31:0] bits_erased = 32'd0;
    reg  [63:0] q_diss_rj = 64'd0;
    reg         hash_valid = 1'b1;
    reg         wal_ready = 1'b1;
    reg         crash_inject = 1'b0;
    reg         l2_profile = 1'b0;
    reg         hw_verified = 1'b0;
    reg         witness_ext = 1'b1;

    wire        busy_out;
    wire        eval_done_out;
    wire [1:0]  port_out;
    wire [3:0]  reason_out;
    wire        kill_latched_out;
    wire        outcome_unknown_out;
    wire        monitor_coupled_out;
    wire        actuator_v_en_out;
    wire [7:0]  status_byte_out;
    wire [4:0]  y_out;
    wire [14:0] q_auth_flat_out;
    wire [3:0]  lifo_depth_out;
    wire [31:0] seq_prev_out;
    wire [31:0] reset_epoch_out;
    wire [63:0] cycle_out;

    nlk_enigma_sluice dut (
        .clk                  (clk),
        .rst_n                (rst_n),
        .l01_reset_strobe     (l01_reset_strobe),
        .l01_witness_ok       (l01_witness_ok),
        .selftest_ok          (selftest_ok),
        .board_load_en        (board_load_en),
        .board_slot_idx       (board_slot_idx),
        .board_slot_present   (board_slot_present),
        .eval_step_en         (eval_step_en),
        .board_eval_en        (board_eval_en),
        .board_expected_steps (board_expected_steps),
        .board_q0_flat        (board_q0_flat),
        .lifo_pop_en          (lifo_pop_en),
        .lifo_tamper_inject   (lifo_tamper_inject),
        .ring_flat            (ring_flat),
        .plug_en              (plug_en),
        .x_in                 (x_in),
        .y_cand               (y_cand),
        .q_before_flat        (q_before_flat),
        .q_prop_flat          (q_prop_flat),
        .seq_num              (seq_num),
        .meas_en              (meas_en),
        .meas_stale           (meas_stale),
        .e_err                (e_err),
        .sigma_ref            (sigma_ref),
        .bits_erased          (bits_erased),
        .q_diss_rj            (q_diss_rj),
        .hash_valid           (hash_valid),
        .wal_ready            (wal_ready),
        .crash_inject         (crash_inject),
        .l2_profile           (l2_profile),
        .hw_verified          (hw_verified),
        .witness_ext          (witness_ext),
        .busy_out             (busy_out),
        .eval_done_out        (eval_done_out),
        .port_out             (port_out),
        .reason_out           (reason_out),
        .kill_latched_out     (kill_latched_out),
        .outcome_unknown_out  (outcome_unknown_out),
        .monitor_coupled_out  (monitor_coupled_out),
        .actuator_v_en_out    (actuator_v_en_out),
        .status_byte_out      (status_byte_out),
        .y_out                (y_out),
        .q_auth_flat_out      (q_auth_flat_out),
        .lifo_depth_out       (lifo_depth_out),
        .seq_prev_out         (seq_prev_out),
        .reset_epoch_out      (reset_epoch_out),
        .cycle_out            (cycle_out)
    );

    always #5 clk = ~clk;

    reg [4:0]  m_x  [0:103];
    reg [4:0]  m_y  [0:103];
    reg [14:0] m_qb [0:103];
    reg [14:0] m_qp [0:103];

    task set_nominal_step(
        input [4:0]  in_x,
        input [4:0]  in_y,
        input [14:0] in_qb,
        input [14:0] in_qp,
        input [31:0] in_seq
    );
        begin
            ring_flat     = 15'd0;
            plug_en       = 1'b1;
            x_in          = in_x;
            y_cand        = in_y;
            q_before_flat = in_qb;
            q_prop_flat   = in_qp;
            seq_num       = in_seq;
            meas_en       = 1'b0;
            meas_stale    = 1'b0;
            e_err         = 32'd0;
            sigma_ref     = 32'd10;
            bits_erased   = 32'd0;
            q_diss_rj     = 64'd0;
            hash_valid    = 1'b1;
            wal_ready     = 1'b1;
            crash_inject  = 1'b0;
            l2_profile    = 1'b0;
            hw_verified   = 1'b0;
            witness_ext   = 1'b1;
        end
    endtask

    task pulse_step;
        begin
            @(negedge clk);
            eval_step_en = 1'b1;
            @(posedge clk);
            #1;
            eval_step_en = 1'b0;
            while (!eval_done_out) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    task pulse_lifo(input tamper);
        begin
            @(negedge clk);
            ring_flat          = 15'd0;
            plug_en            = 1'b1;
            hash_valid         = 1'b1;
            lifo_tamper_inject = tamper;
            lifo_pop_en        = 1'b1;
            @(posedge clk);
            #1;
            lifo_pop_en        = 1'b0;
            lifo_tamper_inject = 1'b0;
            while (!eval_done_out) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    task pulse_reset(input wit, input st_ok);
        begin
            @(negedge clk);
            l01_witness_ok   = wit;
            selftest_ok      = st_ok;
            l01_reset_strobe = 1'b1;
            @(posedge clk);
            #1;
            l01_reset_strobe = 1'b0;
        end
    endtask

    task pulse_board_load(
        input [2:0]  idx,
        input        pres,
        input [4:0]  bx,
        input [4:0]  by,
        input [14:0] bq
    );
        begin
            @(negedge clk);
            board_slot_idx     = idx;
            board_slot_present = pres;
            x_in               = bx;
            y_cand             = by;
            q_prop_flat        = bq;
            board_load_en      = 1'b1;
            @(posedge clk);
            #1;
            board_load_en      = 1'b0;
        end
    endtask

    task pulse_board_eval(
        input [14:0] b_ring,
        input [14:0] b_q0,
        input [3:0]  b_exp,
        input [31:0] b_seq,
        input        b_wit
    );
        begin
            @(negedge clk);
            ring_flat            = b_ring;
            plug_en              = 1'b1;
            board_q0_flat        = b_q0;
            board_expected_steps = b_exp;
            seq_num              = b_seq;
            hash_valid           = 1'b1;
            wal_ready            = 1'b1;
            l2_profile           = 1'b0;
            hw_verified          = 1'b0;
            witness_ext          = b_wit;
            board_eval_en        = 1'b1;
            @(posedge clk);
            #1;
            board_eval_en        = 1'b0;
            while (!eval_done_out) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    task print_vec(input [23:0] tag);
        begin
            $display(
                "%s|BYTE=0x%02x|PORT=%0d|REASON=%02d|Y=%02d|Q=0x%04x|LIFO=%0d|SEQ=%0d|CYC=%0d|EPOCH=%0d",
                tag, status_byte_out, port_out, reason_out, y_out,
                q_auth_flat_out, lifo_depth_out, seq_prev_out,
                cycle_out, reset_epoch_out
            );
        end
    endtask

    integer k;
    initial begin
        m_x[0] = 5'd6; m_y[0] = 5'd23; m_qb[0] = 15'd0; m_qp[0] = 15'd1;
        m_x[1] = 5'd17; m_y[1] = 5'd2; m_qb[1] = 15'd1; m_qp[1] = 15'd2;
        m_x[2] = 5'd0; m_y[2] = 5'd10; m_qb[2] = 15'd2; m_qp[2] = 15'd3;
        m_x[3] = 5'd13; m_y[3] = 5'd24; m_qb[3] = 15'd3; m_qp[3] = 15'd4;
        m_x[4] = 5'd8; m_y[4] = 5'd6; m_qb[4] = 15'd4; m_qp[4] = 15'd5;
        m_x[5] = 5'd19; m_y[5] = 5'd17; m_qb[5] = 15'd5; m_qp[5] = 15'd6;
        m_x[6] = 5'd19; m_y[6] = 5'd7; m_qb[6] = 15'd6; m_qp[6] = 15'd7;
        m_x[7] = 5'd1; m_y[7] = 5'd5; m_qb[7] = 15'd7; m_qp[7] = 15'd8;
        m_x[8] = 5'd0; m_y[8] = 5'd14; m_qb[8] = 15'd8; m_qp[8] = 15'd9;
        m_x[9] = 5'd4; m_y[9] = 5'd2; m_qb[9] = 15'd9; m_qp[9] = 15'd10;
        m_x[10] = 5'd17; m_y[10] = 5'd13; m_qb[10] = 15'd10; m_qp[10] = 15'd11;
        m_x[11] = 5'd4; m_y[11] = 5'd19; m_qb[11] = 15'd11; m_qp[11] = 15'd12;
        m_x[12] = 5'd17; m_y[12] = 5'd5; m_qb[12] = 15'd12; m_qp[12] = 15'd13;
        m_x[13] = 5'd8; m_y[13] = 5'd3; m_qb[13] = 15'd13; m_qp[13] = 15'd14;
        m_x[14] = 5'd10; m_y[14] = 5'd16; m_qb[14] = 15'd14; m_qp[14] = 15'd15;
        m_x[15] = 5'd10; m_y[15] = 5'd5; m_qb[15] = 15'd15; m_qp[15] = 15'd16;
        m_x[16] = 5'd4; m_y[16] = 5'd19; m_qb[16] = 15'd16; m_qp[16] = 15'd17;
        m_x[17] = 5'd15; m_y[17] = 5'd10; m_qb[17] = 15'd17; m_qp[17] = 15'd18;
        m_x[18] = 5'd11; m_y[18] = 5'd0; m_qb[18] = 15'd18; m_qp[18] = 15'd19;
        m_x[19] = 5'd0; m_y[19] = 5'd24; m_qb[19] = 15'd19; m_qp[19] = 15'd20;
        m_x[20] = 5'd18; m_y[20] = 5'd10; m_qb[20] = 15'd20; m_qp[20] = 15'd21;
        m_x[21] = 5'd19; m_y[21] = 5'd23; m_qb[21] = 15'd21; m_qp[21] = 15'd54;
        m_x[22] = 5'd8; m_y[22] = 5'd3; m_qb[22] = 15'd54; m_qp[22] = 15'd55;
        m_x[23] = 5'd10; m_y[23] = 5'd24; m_qb[23] = 15'd55; m_qp[23] = 15'd56;
        m_x[24] = 5'd10; m_y[24] = 5'd19; m_qb[24] = 15'd56; m_qp[24] = 15'd57;
        m_x[25] = 5'd6; m_y[25] = 5'd21; m_qb[25] = 15'd57; m_qp[25] = 15'd32;
        m_x[26] = 5'd17; m_y[26] = 5'd18; m_qb[26] = 15'd32; m_qp[26] = 15'd33;
        m_x[27] = 5'd0; m_y[27] = 5'd9; m_qb[27] = 15'd33; m_qp[27] = 15'd34;
        m_x[28] = 5'd13; m_y[28] = 5'd25; m_qb[28] = 15'd34; m_qp[28] = 15'd35;
        m_x[29] = 5'd8; m_y[29] = 5'd13; m_qb[29] = 15'd35; m_qp[29] = 15'd36;
        m_x[30] = 5'd19; m_y[30] = 5'd12; m_qb[30] = 15'd36; m_qp[30] = 15'd37;
        m_x[31] = 5'd19; m_y[31] = 5'd14; m_qb[31] = 15'd37; m_qp[31] = 15'd38;
        m_x[32] = 5'd1; m_y[32] = 5'd10; m_qb[32] = 15'd38; m_qp[32] = 15'd39;
        m_x[33] = 5'd0; m_y[33] = 5'd3; m_qb[33] = 15'd39; m_qp[33] = 15'd40;
        m_x[34] = 5'd4; m_y[34] = 5'd25; m_qb[34] = 15'd40; m_qp[34] = 15'd41;
        m_x[35] = 5'd17; m_y[35] = 5'd5; m_qb[35] = 15'd41; m_qp[35] = 15'd42;
        m_x[36] = 5'd4; m_y[36] = 5'd18; m_qb[36] = 15'd42; m_qp[36] = 15'd43;
        m_x[37] = 5'd17; m_y[37] = 5'd20; m_qb[37] = 15'd43; m_qp[37] = 15'd44;
        m_x[38] = 5'd8; m_y[38] = 5'd17; m_qb[38] = 15'd44; m_qp[38] = 15'd45;
        m_x[39] = 5'd10; m_y[39] = 5'd0; m_qb[39] = 15'd45; m_qp[39] = 15'd46;
        m_x[40] = 5'd10; m_y[40] = 5'd7; m_qb[40] = 15'd46; m_qp[40] = 15'd47;
        m_x[41] = 5'd4; m_y[41] = 5'd20; m_qb[41] = 15'd47; m_qp[41] = 15'd48;
        m_x[42] = 5'd15; m_y[42] = 5'd19; m_qb[42] = 15'd48; m_qp[42] = 15'd49;
        m_x[43] = 5'd11; m_y[43] = 5'd14; m_qb[43] = 15'd49; m_qp[43] = 15'd50;
        m_x[44] = 5'd0; m_y[44] = 5'd3; m_qb[44] = 15'd50; m_qp[44] = 15'd51;
        m_x[45] = 5'd18; m_y[45] = 5'd15; m_qb[45] = 15'd51; m_qp[45] = 15'd52;
        m_x[46] = 5'd19; m_y[46] = 5'd12; m_qb[46] = 15'd52; m_qp[46] = 15'd53;
        m_x[47] = 5'd8; m_y[47] = 5'd18; m_qb[47] = 15'd53; m_qp[47] = 15'd86;
        m_x[48] = 5'd10; m_y[48] = 5'd17; m_qb[48] = 15'd86; m_qp[48] = 15'd87;
        m_x[49] = 5'd10; m_y[49] = 5'd1; m_qb[49] = 15'd87; m_qp[49] = 15'd88;
        m_x[50] = 5'd6; m_y[50] = 5'd21; m_qb[50] = 15'd88; m_qp[50] = 15'd89;
        m_x[51] = 5'd17; m_y[51] = 5'd10; m_qb[51] = 15'd89; m_qp[51] = 15'd64;
        m_x[52] = 5'd0; m_y[52] = 5'd25; m_qb[52] = 15'd64; m_qp[52] = 15'd65;
        m_x[53] = 5'd13; m_y[53] = 5'd9; m_qb[53] = 15'd65; m_qp[53] = 15'd66;
        m_x[54] = 5'd8; m_y[54] = 5'd10; m_qb[54] = 15'd66; m_qp[54] = 15'd67;
        m_x[55] = 5'd19; m_y[55] = 5'd13; m_qb[55] = 15'd67; m_qp[55] = 15'd68;
        m_x[56] = 5'd19; m_y[56] = 5'd22; m_qb[56] = 15'd68; m_qp[56] = 15'd69;
        m_x[57] = 5'd1; m_y[57] = 5'd8; m_qb[57] = 15'd69; m_qp[57] = 15'd70;
        m_x[58] = 5'd0; m_y[58] = 5'd3; m_qb[58] = 15'd70; m_qp[58] = 15'd71;
        m_x[59] = 5'd4; m_y[59] = 5'd16; m_qb[59] = 15'd71; m_qp[59] = 15'd72;
        m_x[60] = 5'd17; m_y[60] = 5'd11; m_qb[60] = 15'd72; m_qp[60] = 15'd73;
        m_x[61] = 5'd4; m_y[61] = 5'd0; m_qb[61] = 15'd73; m_qp[61] = 15'd74;
        m_x[62] = 5'd17; m_y[62] = 5'd21; m_qb[62] = 15'd74; m_qp[62] = 15'd75;
        m_x[63] = 5'd8; m_y[63] = 5'd7; m_qb[63] = 15'd75; m_qp[63] = 15'd76;
        m_x[64] = 5'd10; m_y[64] = 5'd16; m_qb[64] = 15'd76; m_qp[64] = 15'd77;
        m_x[65] = 5'd10; m_y[65] = 5'd23; m_qb[65] = 15'd77; m_qp[65] = 15'd78;
        m_x[66] = 5'd4; m_y[66] = 5'd24; m_qb[66] = 15'd78; m_qp[66] = 15'd79;
        m_x[67] = 5'd15; m_y[67] = 5'd1; m_qb[67] = 15'd79; m_qp[67] = 15'd80;
        m_x[68] = 5'd11; m_y[68] = 5'd9; m_qb[68] = 15'd80; m_qp[68] = 15'd81;
        m_x[69] = 5'd0; m_y[69] = 5'd1; m_qb[69] = 15'd81; m_qp[69] = 15'd82;
        m_x[70] = 5'd18; m_y[70] = 5'd12; m_qb[70] = 15'd82; m_qp[70] = 15'd83;
        m_x[71] = 5'd19; m_y[71] = 5'd12; m_qb[71] = 15'd83; m_qp[71] = 15'd84;
        m_x[72] = 5'd8; m_y[72] = 5'd3; m_qb[72] = 15'd84; m_qp[72] = 15'd85;
        m_x[73] = 5'd10; m_y[73] = 5'd23; m_qb[73] = 15'd85; m_qp[73] = 15'd118;
        m_x[74] = 5'd10; m_y[74] = 5'd13; m_qb[74] = 15'd118; m_qp[74] = 15'd119;
        m_x[75] = 5'd6; m_y[75] = 5'd11; m_qb[75] = 15'd119; m_qp[75] = 15'd120;
        m_x[76] = 5'd17; m_y[76] = 5'd9; m_qb[76] = 15'd120; m_qp[76] = 15'd121;
        m_x[77] = 5'd0; m_y[77] = 5'd19; m_qb[77] = 15'd121; m_qp[77] = 15'd96;
        m_x[78] = 5'd13; m_y[78] = 5'd22; m_qb[78] = 15'd96; m_qp[78] = 15'd97;
        m_x[79] = 5'd8; m_y[79] = 5'd2; m_qb[79] = 15'd97; m_qp[79] = 15'd98;
        m_x[80] = 5'd19; m_y[80] = 5'd14; m_qb[80] = 15'd98; m_qp[80] = 15'd99;
        m_x[81] = 5'd19; m_y[81] = 5'd10; m_qb[81] = 15'd99; m_qp[81] = 15'd100;
        m_x[82] = 5'd1; m_y[82] = 5'd17; m_qb[82] = 15'd100; m_qp[82] = 15'd101;
        m_x[83] = 5'd0; m_y[83] = 5'd22; m_qb[83] = 15'd101; m_qp[83] = 15'd102;
        m_x[84] = 5'd4; m_y[84] = 5'd19; m_qb[84] = 15'd102; m_qp[84] = 15'd103;
        m_x[85] = 5'd17; m_y[85] = 5'd21; m_qb[85] = 15'd103; m_qp[85] = 15'd104;
        m_x[86] = 5'd4; m_y[86] = 5'd24; m_qb[86] = 15'd104; m_qp[86] = 15'd105;
        m_x[87] = 5'd17; m_y[87] = 5'd16; m_qb[87] = 15'd105; m_qp[87] = 15'd106;
        m_x[88] = 5'd8; m_y[88] = 5'd5; m_qb[88] = 15'd106; m_qp[88] = 15'd107;
        m_x[89] = 5'd10; m_y[89] = 5'd21; m_qb[89] = 15'd107; m_qp[89] = 15'd108;
        m_x[90] = 5'd10; m_y[90] = 5'd11; m_qb[90] = 15'd108; m_qp[90] = 15'd109;
        m_x[91] = 5'd4; m_y[91] = 5'd22; m_qb[91] = 15'd109; m_qp[91] = 15'd110;
        m_x[92] = 5'd15; m_y[92] = 5'd0; m_qb[92] = 15'd110; m_qp[92] = 15'd111;
        m_x[93] = 5'd11; m_y[93] = 5'd20; m_qb[93] = 15'd111; m_qp[93] = 15'd112;
        m_x[94] = 5'd0; m_y[94] = 5'd22; m_qb[94] = 15'd112; m_qp[94] = 15'd113;
        m_x[95] = 5'd18; m_y[95] = 5'd19; m_qb[95] = 15'd113; m_qp[95] = 15'd114;
        m_x[96] = 5'd19; m_y[96] = 5'd17; m_qb[96] = 15'd114; m_qp[96] = 15'd115;
        m_x[97] = 5'd8; m_y[97] = 5'd22; m_qb[97] = 15'd115; m_qp[97] = 15'd116;
        m_x[98] = 5'd10; m_y[98] = 5'd21; m_qb[98] = 15'd116; m_qp[98] = 15'd117;
        m_x[99] = 5'd10; m_y[99] = 5'd0; m_qb[99] = 15'd117; m_qp[99] = 15'd150;
        m_x[100] = 5'd18; m_y[100] = 5'd6; m_qb[100] = 15'd150; m_qp[100] = 15'd1207;
        m_x[101] = 5'd19; m_y[101] = 5'd8; m_qb[101] = 15'd1207; m_qp[101] = 15'd1208;
        m_x[102] = 5'd0; m_y[102] = 5'd12; m_qb[102] = 15'd1208; m_qp[102] = 15'd1209;
        m_x[103] = 5'd11; m_y[103] = 5'd25; m_qb[103] = 15'd1209; m_qp[103] = 15'd1184;

        rst_n = 1'b0;
        #20;
        rst_n = 1'b1;
        #10;

        // V01: 104-step marathon crossing 3-rotor notch cascade
        for (k = 0; k < 104; k = k + 1) begin
            set_nominal_step(m_x[k], m_y[k], m_qb[k], m_qp[k], k + 1);
            pulse_step();
        end
        print_vec("V01");

        // V02..V04: 4 LIFO reversible pops rewinding across 3-rotor notch cascade
        pulse_lifo(1'b0); print_vec("V02");
        pulse_lifo(1'b0); print_vec("V03");
        pulse_lifo(1'b0); pulse_lifo(1'b0); print_vec("V04");

        // V05: Exact 9/10*sigma lower boundary -> HOLD
        set_nominal_step(5'd0, 5'd24, 15'd150, 15'd1207, 32'd105);
        meas_en = 1'b1; e_err = 32'd9; sigma_ref = 32'd10;
        pulse_step(); print_vec("V05");

        // V06: -1 LSB below 9/10*sigma -> OPEN
        set_nominal_step(5'd0, 5'd24, 15'd150, 15'd1207, 32'd105);
        meas_en = 1'b1; e_err = 32'd8999; sigma_ref = 32'd10000;
        pulse_step(); print_vec("V06");

        // V07: Exact 3/2*sigma upper boundary -> HOLD
        set_nominal_step(5'd1, 5'd12, 15'd1207, 15'd1208, 32'd106);
        meas_en = 1'b1; e_err = 32'd15; sigma_ref = 32'd10;
        pulse_step(); print_vec("V07");

        // V08: +1 LSB over 3/2*sigma -> KILL
        set_nominal_step(5'd1, 5'd12, 15'd1207, 15'd1208, 32'd106);
        meas_en = 1'b1; e_err = 32'd15001; sigma_ref = 32'd10000;
        pulse_step(); print_vec("V08");

        // V09: Sticky KILL latch
        set_nominal_step(5'd2, 5'd10, 15'd1207, 15'd1208, 32'd106);
        pulse_step(); print_vec("V09");

        // V10: Reset denied when selftest_ok == 0
        pulse_reset(1'b1, 1'b0); print_vec("V10");

        // V11: Reset OK + Ma'ats Feather involution sabotage -> KILL
        pulse_reset(1'b1, 1'b1);
        set_nominal_step(5'd0, 5'd1, 15'd1207, 15'd1208, 32'd106);
        pulse_step(); print_vec("V11");

        // V12: Reset OK + Fixed-Point sabotage -> KILL
        pulse_reset(1'b1, 1'b1);
        set_nominal_step(5'd10, 5'd10, 15'd1207, 15'd1208, 32'd106);
        pulse_step(); print_vec("V12");

        // V13: Reset OK + Landauer -1 rJ violation -> KILL
        pulse_reset(1'b1, 1'b1);
        set_nominal_step(5'd3, 5'd21, 15'd1207, 15'd1208, 32'd106);
        bits_erased = 32'd3; q_diss_rj = 64'd7956917;
        pulse_step(); print_vec("V13");

        // V14: Reset OK + Unverified L2_PHYSICAL -> HOLD
        pulse_reset(1'b1, 1'b1);
        set_nominal_step(5'd3, 5'd21, 15'd1207, 15'd1208, 32'd106);
        bits_erased = 32'd3; q_diss_rj = 64'd7956918; l2_profile = 1'b1; hw_verified = 1'b0;
        pulse_step(); print_vec("V14");

        // V15: Exact Landauer + Verified L2_PHYSICAL -> OPEN (actuator_v_en = 1)
        set_nominal_step(5'd3, 5'd21, 15'd1207, 15'd1208, 32'd106);
        bits_erased = 32'd3; q_diss_rj = 64'd7956918; l2_profile = 1'b1; hw_verified = 1'b1;
        pulse_step(); print_vec("V15");

        // V16: Sequence replay (seq == seq_prev == 106) -> HOLD
        set_nominal_step(5'd4, 5'd6, 15'd1208, 15'd1209, 32'd106);
        pulse_step(); print_vec("V16");

        // V17: Durable-first WAL failure (!wal_ready) -> HOLD
        set_nominal_step(5'd4, 5'd6, 15'd1208, 15'd1209, 32'd107);
        wal_ready = 1'b0;
        pulse_step(); print_vec("V17");

        // V18: Crash window between commit and observe -> OUTCOME_UNKNOWN HOLD (actuator_v_en == 0!)
        set_nominal_step(5'd4, 5'd6, 15'd1208, 15'd1209, 32'd107);
        l2_profile = 1'b1; hw_verified = 1'b1; crash_inject = 1'b1;
        pulse_step(); print_vec("V18");

        // V19: Coordinate Board blocked by OUTCOME_UNKNOWN -> HOLD
        pulse_board_load(3'd0, 1'b1, 5'd18, 5'd12, 15'd1184);
        pulse_board_load(3'd1, 1'b1, 5'd19, 5'd18, 15'd1185);
        pulse_board_load(3'd2, 1'b1, 5'd0, 5'd10, 15'd1186);
        pulse_board_load(3'd3, 1'b1, 5'd11, 5'd7, 15'd1187);
        pulse_board_eval(15'd3446, 15'd1209, 4'd4, 32'd108, 1'b1);
        print_vec("V19");

        // V20: L01 Reset + Incomplete 3-of-4 Coordinate Board -> HOLD
        pulse_reset(1'b1, 1'b1);
        pulse_board_load(3'd0, 1'b1, 5'd18, 5'd12, 15'd1184);
        pulse_board_load(3'd1, 1'b1, 5'd19, 5'd18, 15'd1185);
        pulse_board_load(3'd2, 1'b1, 5'd0, 5'd10, 15'd1186);
        pulse_board_eval(15'd3446, 15'd1209, 4'd4, 32'd108, 1'b1);
        print_vec("V20");

        // V21: Complete 4-of-4 Coordinate Board without W_ext -> HOLD
        pulse_board_load(3'd0, 1'b1, 5'd18, 5'd12, 15'd1184);
        pulse_board_load(3'd1, 1'b1, 5'd19, 5'd18, 15'd1185);
        pulse_board_load(3'd2, 1'b1, 5'd0, 5'd10, 15'd1186);
        pulse_board_load(3'd3, 1'b1, 5'd11, 5'd7, 15'd1187);
        pulse_board_eval(15'd3446, 15'd1209, 4'd4, 32'd108, 1'b0);
        print_vec("V21");

        // V22: Complete 4-of-4 Coordinate Board with W_ext -> OPEN (jumps q_auth!)
        pulse_board_eval(15'd3446, 15'd1209, 4'd4, 32'd108, 1'b1);
        print_vec("V22");

        // V23: Coordinate Board Seam Break on Slot 1 with Slot 3 Missing (KILL > HOLD) -> KILL
        pulse_board_load(3'd0, 1'b1, 5'd18, 5'd21, 15'd1188);
        pulse_board_load(3'd1, 1'b1, 5'd19, 5'd23, 15'd9513);
        pulse_board_load(3'd2, 1'b1, 5'd0, 5'd2, 15'd1190);
        pulse_board_eval(15'd0, 15'd1187, 4'd4, 32'd109, 1'b1);
        print_vec("V23");

        // V24: L01 Reset + Commit 'Q' + Corrupted LIFO Uncompute -> KILL
        pulse_reset(1'b1, 1'b1);
        set_nominal_step(5'd16, 5'd0, 15'd1187, 15'd1188, 32'd109);
        pulse_step();
        pulse_lifo(1'b1);
        print_vec("V24");

        $finish;
    end

endmodule
`default_nettype wire
