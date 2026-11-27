// =============================================================================
// L2_GATE — Canonical 12-Vector Testbench for bell_ky_sluice (RTL & cells_sim)
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module tb_bell_ky_sluice;

    reg         clk = 1'b0;
    reg         rst_n = 1'b0;
    reg         l01_reset_strobe = 1'b0;
    reg         l01_witness_ok = 1'b0;
    reg         load_en = 1'b0;
    reg         arm_idx = 1'b0;
    reg  [1:0]  mn_idx = 2'd0;
    reg         eval_en = 1'b0;

    reg  [39:0] n_pulses_in = 40'd0;
    reg  [39:0] cnt_pp = 40'd0, cnt_pm = 40'd0, cnt_mp = 40'd0, cnt_mm = 40'd0;

    reg  [31:0]  delta_k_cycles = 32'd200;
    reg  [31:0]  t_clk_ps = 32'd1000;
    reg  [31:0]  dist_mm = 32'd30000;
    reg  [39:0]  tau_ns = 40'd50;
    reg  [31:0]  setting_corr_abs = 32'd0;
    reg  [31:0]  tau_indep = 32'd10;
    reg  [31:0]  tomo_frob_diff_sq = 32'd0;
    reg  [31:0]  tau_tomo_sq = 32'd100;
    reg  [127:0] tau_diff_sq = 128'd1000000;
    reg  [15:0]  replicated_series = 16'd3;
    reg  [15:0]  min_series = 16'd3;
    reg          hash_valid = 1'b1;
    reg          involution_closed = 1'b1;
    reg          witness_ext = 1'b1;

    wire         busy_out;
    wire         eval_done_out;
    wire [1:0]   port_out;
    wire [3:0]   reason_out;
    wire         kill_latched_out;
    wire         monitor_coupled_out;
    wire         actuator_v_en_out;
    wire         bell_violated_k1_out;
    wire         super_tsirelson_out;
    wire [7:0]   status_byte_out;
    wire [63:0]  cycle_out;
    wire [31:0]  reset_epoch_out;
    wire [127:0] s1_sq_out;
    wire [127:0] s2_sq_out;

    bell_ky_sluice dut (
        .clk                  (clk),
        .rst_n                (rst_n),
        .l01_reset_strobe     (l01_reset_strobe),
        .l01_witness_ok       (l01_witness_ok),
        .load_en              (load_en),
        .arm_idx              (arm_idx),
        .mn_idx               (mn_idx),
        .eval_en              (eval_en),
        .n_pulses_in          (n_pulses_in),
        .cnt_pp               (cnt_pp),
        .cnt_pm               (cnt_pm),
        .cnt_mp               (cnt_mp),
        .cnt_mm               (cnt_mm),
        .delta_k_cycles       (delta_k_cycles),
        .t_clk_ps             (t_clk_ps),
        .dist_mm              (dist_mm),
        .tau_ns               (tau_ns),
        .setting_corr_abs     (setting_corr_abs),
        .tau_indep            (tau_indep),
        .tomo_frob_diff_sq    (tomo_frob_diff_sq),
        .tau_tomo_sq          (tau_tomo_sq),
        .tau_diff_sq          (tau_diff_sq),
        .replicated_series    (replicated_series),
        .min_series           (min_series),
        .hash_valid           (hash_valid),
        .involution_closed    (involution_closed),
        .witness_ext          (witness_ext),
        .busy_out             (busy_out),
        .eval_done_out        (eval_done_out),
        .port_out             (port_out),
        .reason_out           (reason_out),
        .kill_latched_out     (kill_latched_out),
        .monitor_coupled_out  (monitor_coupled_out),
        .actuator_v_en_out    (actuator_v_en_out),
        .bell_violated_k1_out (bell_violated_k1_out),
        .super_tsirelson_out  (super_tsirelson_out),
        .status_byte_out      (status_byte_out),
        .cycle_out            (cycle_out),
        .reset_epoch_out      (reset_epoch_out),
        .s1_sq_out            (s1_sq_out),
        .s2_sq_out            (s2_sq_out)
    );

    always #5 clk = ~clk;

    task set_nominal_cfg(input [39:0] np);
        begin
            n_pulses_in       = np;
            delta_k_cycles    = 32'd200;
            t_clk_ps          = 32'd1000;
            dist_mm           = 32'd30000;
            tau_ns            = 40'd50;
            setting_corr_abs  = 32'd0;
            tau_indep         = 32'd10;
            tomo_frob_diff_sq = 32'd0;
            tau_tomo_sq       = 32'd100;
            tau_diff_sq       = 128'd1000000;
            replicated_series = 16'd3;
            min_series        = 16'd3;
            hash_valid        = 1'b1;
            involution_closed = 1'b1;
            witness_ext       = 1'b1;
        end
    endtask

    task load_one_arm_sym(
        input       arm,
        input [1:0] idx,
        input [39:0] np,
        input signed [44:0] c_val,
        input [39:0] drop_pp,
        input [39:0] ns_shift
    );
        reg signed [44:0] n_s;
        reg [39:0] s_v, d_v;
        begin
            n_s = $signed({5'd0, np});
            s_v = (n_s + c_val) >>> 2;
            d_v = (n_s - c_val) >>> 2;
            @(negedge clk);
            l01_reset_strobe = 1'b0;
            eval_en          = 1'b0;
            load_en          = 1'b1;
            arm_idx          = arm;
            mn_idx           = idx;
            n_pulses_in      = np;
            cnt_pp           = s_v - drop_pp;
            cnt_pm           = d_v + ns_shift;
            cnt_mp           = d_v;
            cnt_mm           = s_v - ns_shift;
            @(posedge clk);
            #1;
            load_en = 1'b0;
        end
    endtask

    task stream_block(
        input [39:0] np,
        input signed [44:0] c1_0, input signed [44:0] c1_1,
        input signed [44:0] c1_2, input signed [44:0] c1_3,
        input signed [44:0] c2_0, input signed [44:0] c2_1,
        input signed [44:0] c2_2, input signed [44:0] c2_3
    );
        begin
            load_one_arm_sym(1'b0, 2'd0, np, c1_0, 40'd0, 40'd0);
            load_one_arm_sym(1'b0, 2'd1, np, c1_1, 40'd0, 40'd0);
            load_one_arm_sym(1'b0, 2'd2, np, c1_2, 40'd0, 40'd0);
            load_one_arm_sym(1'b0, 2'd3, np, c1_3, 40'd0, 40'd0);
            load_one_arm_sym(1'b1, 2'd0, np, c2_0, 40'd0, 40'd0);
            load_one_arm_sym(1'b1, 2'd1, np, c2_1, 40'd0, 40'd0);
            load_one_arm_sym(1'b1, 2'd2, np, c2_2, 40'd0, 40'd0);
            load_one_arm_sym(1'b1, 2'd3, np, c2_3, 40'd0, 40'd0);
        end
    endtask

    task pulse_eval;
        begin
            @(negedge clk);
            load_en          = 1'b0;
            l01_reset_strobe = 1'b0;
            eval_en          = 1'b1;
            @(posedge clk);
            #1;
            eval_en = 1'b0;
            while (!eval_done_out) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    task pulse_l01_reset(input wit);
        begin
            @(negedge clk);
            load_en          = 1'b0;
            eval_en          = 1'b0;
            l01_reset_strobe = 1'b1;
            l01_witness_ok   = wit;
            @(posedge clk);
            #1;
            l01_reset_strobe = 1'b0;
        end
    endtask

    task print_vec(input [23:0] tag);
        begin
            $display(
                "%s|BYTE=0x%02x|PORT=%0d|REASON=%02d|CYC=%0d|EPOCH=%0d|S1SQ=0x%016x_%016x|S2SQ=0x%016x_%016x",
                tag, status_byte_out, port_out, reason_out,
                cycle_out, reset_epoch_out,
                s1_sq_out[127:64], s1_sq_out[63:0],
                s2_sq_out[127:64], s2_sq_out[63:0]
            );
        end
    endtask

    initial begin
        rst_n = 1'b0;
        #20;
        rst_n = 1'b1;
        #10;

        // V01
        stream_block(40'd10000,
            45'sd7072, 45'sd7072, 45'sd7072, -45'sd7072,
            45'sd7072, 45'sd7072, 45'sd7072, -45'sd7072);
        set_nominal_cfg(40'd10000);
        pulse_eval();
        print_vec("V01");

        // V02
        stream_block(40'd10000,
            45'sd7072, 45'sd7072, 45'sd7068, -45'sd7068,
            45'sd7072, 45'sd7072, 45'sd4240, -45'sd4240);
        set_nominal_cfg(40'd10000);
        tomo_frob_diff_sq = 32'd1600;
        pulse_eval();
        print_vec("V02");

        // V03
        stream_block(40'd10000,
            45'sd7072, 45'sd7072, 45'sd2828, -45'sd2828,
            45'sd7072, 45'sd7072, 45'sd0, 45'sd0);
        set_nominal_cfg(40'd10000);
        involution_closed = 1'b0;
        pulse_eval();
        print_vec("V03");

        // V04
        stream_block(40'd10000,
            45'sd7072, 45'sd7072, 45'sd7068, -45'sd7068,
            45'sd6200, 45'sd6200, 45'sd6200, -45'sd6200);
        set_nominal_cfg(40'd10000);
        witness_ext = 1'b0;
        pulse_eval();
        print_vec("V04");

        // V05
        stream_block(40'd10000,
            45'sd7072, 45'sd7072, 45'sd7068, -45'sd7068,
            45'sd6200, 45'sd6200, 45'sd6200, -45'sd6200);
        set_nominal_cfg(40'd10000);
        pulse_eval();
        print_vec("V05");

        // V06
        stream_block(40'd10000,
            45'sd7000, 45'sd7000, 45'sd7000, -45'sd7000,
            -45'sd7000, -45'sd7000, -45'sd7000, 45'sd7000);
        set_nominal_cfg(40'd10000);
        pulse_eval();
        print_vec("V06");

        // V07
        stream_block(40'd10000,
            45'sd7000, 45'sd7000, 45'sd7000, -45'sd7000,
            45'sd6000, 45'sd6000, 45'sd6000, -45'sd6000);
        set_nominal_cfg(40'd10000);
        delta_k_cycles = 32'd201;
        pulse_eval();
        print_vec("V07");

        // V08
        stream_block(40'd10000,
            45'sd7072, 45'sd7072, 45'sd7068, -45'sd7068,
            45'sd6200, 45'sd6200, 45'sd6200, -45'sd6200);
        set_nominal_cfg(40'd10000);
        pulse_eval();
        print_vec("V08");

        // V09
        pulse_l01_reset(1'b1);
        load_one_arm_sym(1'b0, 2'd0, 40'd10000, 45'sd7000, 40'd1, 40'd0);
        load_one_arm_sym(1'b0, 2'd1, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b0, 2'd2, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b0, 2'd3, 40'd10000, -45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd0, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd1, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd2, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd3, 40'd10000, -45'sd7000, 40'd0, 40'd0);
        set_nominal_cfg(40'd10000);
        pulse_eval();
        print_vec("V09");

        // V10
        pulse_l01_reset(1'b1);
        load_one_arm_sym(1'b0, 2'd0, 40'd10000, 45'sd6000, 40'd0, 40'd0);
        load_one_arm_sym(1'b0, 2'd1, 40'd10000, 45'sd6000, 40'd0, 40'd80);
        load_one_arm_sym(1'b0, 2'd2, 40'd10000, 45'sd6000, 40'd0, 40'd0);
        load_one_arm_sym(1'b0, 2'd3, 40'd10000, -45'sd6000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd0, 40'd10000, 45'sd6000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd1, 40'd10000, 45'sd6000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd2, 40'd10000, 45'sd6000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd3, 40'd10000, -45'sd6000, 40'd0, 40'd0);
        set_nominal_cfg(40'd10000);
        pulse_eval();
        print_vec("V10");

        // V11
        pulse_l01_reset(1'b1);
        stream_block(40'd10000,
            45'sd7000, 45'sd7000, 45'sd7000, -45'sd7000,
            45'sd6000, 45'sd6000, 45'sd6000, -45'sd6000);
        set_nominal_cfg(40'd10000);
        setting_corr_abs = 32'd25;
        pulse_eval();
        print_vec("V11");

        // V12
        pulse_l01_reset(1'b1);
        stream_block(40'h1_0000_0000,
            45'sd3000000000, 45'sd3000000000, 45'sd3000000000, -45'sd3000000000,
            45'sd2500000000, 45'sd2500000000, 45'sd2500000000, -45'sd2500000000);
        set_nominal_cfg(40'h1_0000_0000);
        tau_ns      = 40'd100000;
        tau_diff_sq = 128'd1000000000000;
        pulse_eval();
        print_vec("V12");

        // V13: Exact Classical Bell Boundary (S1^2 == 4*N^2) -> bell_violated_k1=0, OPEN
        stream_block(40'd10000,
            45'sd5000, 45'sd5000, 45'sd5000, -45'sd5000,
            45'sd4000, 45'sd4000, 45'sd4000, -45'sd4000);
        set_nominal_cfg(40'd10000);
        pulse_eval();
        print_vec("V13");

        // V14: +1 Physical Shot Step Over Bell Boundary (Sigma_1 = 20002)
        @(negedge clk);
        l01_reset_strobe = 1'b0; eval_en = 1'b0; load_en = 1'b1;
        arm_idx = 1'b0; mn_idx = 2'd0; n_pulses_in = 40'd10000;
        cnt_pp = 40'd3751; cnt_pm = 40'd1250; cnt_mp = 40'd1249; cnt_mm = 40'd3750;
        @(posedge clk); #1; load_en = 1'b0;
        load_one_arm_sym(1'b0, 2'd1, 40'd10000, 45'sd5000, 40'd0, 40'd0);
        load_one_arm_sym(1'b0, 2'd2, 40'd10000, 45'sd5000, 40'd0, 40'd0);
        load_one_arm_sym(1'b0, 2'd3, 40'd10000, -45'sd5000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd0, 40'd10000, 45'sd4000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd1, 40'd10000, 45'sd4000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd2, 40'd10000, 45'sd4000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd3, 40'd10000, -45'sd4000, 40'd0, 40'd0);
        set_nominal_cfg(40'd10000);
        pulse_eval();
        print_vec("V14");

        // V15: 128-Bit Seam Exact Equality (ds_sq == 2^68 == tau_diff_sq) -> HOLD
        stream_block(40'h1_0000_0000,
            45'sd2147483648, 45'sd2147483648, 45'sd2147483648, -45'sd2147483648,
            -45'sd2147483648, -45'sd2147483648, -45'sd2147483648, 45'sd2147483648);
        set_nominal_cfg(40'h1_0000_0000);
        tau_diff_sq = {64'h0000_0000_0000_0010, 64'h0000_0000_0000_0000};
        pulse_eval();
        print_vec("V15");

        // V16: 128-Bit Seam -1 LSB Borrow (tau_diff_sq = 2^68 - 1) -> OPEN
        stream_block(40'h1_0000_0000,
            45'sd2147483648, 45'sd2147483648, 45'sd2147483648, -45'sd2147483648,
            -45'sd2147483648, -45'sd2147483648, -45'sd2147483648, 45'sd2147483648);
        set_nominal_cfg(40'h1_0000_0000);
        tau_diff_sq = {64'h0000_0000_0000_000F, 64'hFFFF_FFFF_FFFF_FFFF};
        pulse_eval();
        print_vec("V16");

        // V17: MAX_PULSES = 2^38 Saturated Ceiling + +1mm Light-Cone Margin -> OPEN
        stream_block(40'h40_0000_0000,
            45'sd274877906944, 45'sd274877906944, 45'sd274877906944, -45'sd274877906944,
            -45'sd274877906944, -45'sd274877906944, -45'sd274877906944, 45'sd274877906944);
        set_nominal_cfg(40'h40_0000_0000);
        delta_k_cycles = 32'd1000;
        t_clk_ps       = 32'd1000000;
        dist_mm        = 32'd149896230;
        tau_diff_sq    = {64'h0000_0000_0003_FFFF, 64'hFFFF_FFFF_FFFF_FFFF};
        pulse_eval();
        print_vec("V17");

        // V18: MAX_PULSES + 1 Over-Ceiling -> KILL
        begin : blk_v18
            integer a_i, m_i;
            for (a_i = 0; a_i < 2; a_i = a_i + 1) begin
                for (m_i = 0; m_i < 4; m_i = m_i + 1) begin
                    @(negedge clk);
                    l01_reset_strobe = 1'b0; eval_en = 1'b0; load_en = 1'b1;
                    arm_idx = a_i[0]; mn_idx = m_i[1:0];
                    n_pulses_in = 40'h40_0000_0001;
                    cnt_pp = 40'h40_0000_0001; cnt_pm = 40'd0; cnt_mp = 40'd0; cnt_mm = 40'd0;
                    @(posedge clk); #1; load_en = 1'b0;
                end
            end
        end
        set_nominal_cfg(40'h40_0000_0001);
        pulse_eval();
        print_vec("V18");

        // V19: L01 Reset + Out-of-Order Interleaved Slot Attack -> KILL
        pulse_l01_reset(1'b1);
        load_one_arm_sym(1'b0, 2'd0, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd0, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b0, 2'd1, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b0, 2'd2, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b0, 2'd3, 40'd10000, -45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd1, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd2, 40'd10000, 45'sd7000, 40'd0, 40'd0);
        load_one_arm_sym(1'b1, 2'd3, 40'd10000, -45'sd7000, 40'd0, 40'd0);
        set_nominal_cfg(40'd10000);
        pulse_eval();
        print_vec("V19");

        // V20: L01 Reset + Exact Lightlike Boundary (lc_lhs == lc_rhs) -> KILL
        pulse_l01_reset(1'b1);
        stream_block(40'd10000,
            45'sd7000, 45'sd7000, 45'sd7000, -45'sd7000,
            45'sd6000, 45'sd6000, 45'sd6000, -45'sd6000);
        set_nominal_cfg(40'd10000);
        delta_k_cycles = 32'd1000;
        t_clk_ps       = 32'd1000000;
        dist_mm        = 32'd149896229;
        pulse_eval();
        print_vec("V20");

        // V21: L01 Reset + Cross-Word Borrow OPEN (ds_sq > tau while ds_lo < tau_lo across bit 47 & 64)
        pulse_l01_reset(1'b1);
        stream_block(40'h1_0000_0000,
            45'sd2147483652, 45'sd2147483652, 45'sd2147483652, -45'sd2147483652,
            -45'sd2147483652, -45'sd2147483652, -45'sd2147483652, 45'sd2147483652);
        set_nominal_cfg(40'h1_0000_0000);
        tau_diff_sq = {64'h0000_0000_0000_000F, 64'h0000_0200_0000_0800};
        pulse_eval();
        print_vec("V21");

        // V22: Cross-Word Borrow HOLD (ds_sq < tau while ds_lo > tau_lo across bit 47 & 64)
        stream_block(40'h1_0000_0000,
            45'sd2147483652, 45'sd2147483652, 45'sd2147483652, -45'sd2147483652,
            -45'sd2147483652, -45'sd2147483652, -45'sd2147483652, 45'sd2147483652);
        set_nominal_cfg(40'h1_0000_0000);
        tau_diff_sq = {64'h0000_0000_0000_0011, 64'h0000_0000_0000_0000};
        pulse_eval();
        print_vec("V22");

        $finish;
    end

endmodule
`default_nettype wire
