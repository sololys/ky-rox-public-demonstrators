// =============================================================================
// L2_GATE — Canonical 12-Vector Testbench for omni_crash3_sluice
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module tb_omni_crash3_sluice;

    reg         clk = 1'b0;
    reg         rst_n = 1'b0;
    reg         l01_reset_strobe = 1'b0;
    reg         l01_witness_ok = 1'b0;
    reg         eval_en = 1'b0;

    reg  [31:0] seq_epoch = 32'd1;
    reg  signed [31:0] q_pos = 32'sd480;
    reg  signed [31:0] p_mom = 32'sd80;
    reg  [31:0] q_bound = 32'd1000;
    reg  [31:0] eps_k_max = 32'd250;
    reg  signed [31:0] lambda_spec = -32'sd250;
    reg  signed [31:0] g_barrier = -32'sd500;
    reg  signed [31:0] g_dot = 32'sd10;
    reg  [31:0] tau_hold_ticks = 32'd20;
    reg  [31:0] pi_risk = 32'd50;
    reg  [31:0] tau_risk = 32'd200;
    reg  [31:0] r_dot = 32'd100;
    reg  [31:0] delta_r = 32'd500;
    reg  [31:0] k_defect = 32'd15;
    reg  [31:0] b_barrier = 32'd100;
    reg  [31:0] c_care = 32'd250;
    reg  [31:0] dist_mm = 32'd12000;
    reg  [31:0] tof_ps = 32'd80100;
    reg  [15:0] s_phase_16 = 16'h05A5;
    reg  [15:0] r_mask_16 = 16'hF00F;
    reg  [15:0] m_rx_16 = 16'hF5AA;
    reg  [39:0] finder_sig_40 = 40'h7F_415D_417F;
    reg  [7:0]  quiet_zone = 8'd4;
    reg         hash_valid = 1'b1;
    reg         u_safe_nonempty = 1'b1;
    reg         eta_hw_truth = 1'b1;
    reg         witness_ext = 1'b1;

    wire         busy_out;
    wire         eval_done_out;
    wire [1:0]   port_out;
    wire [3:0]   reason_out;
    wire [1:0]   traj_class_out;
    wire         dk_kill_latched_out;
    wire         monitor_coupled_out;
    wire         actuator_v_en_out;
    wire [7:0]   status_byte_out;
    wire [15:0]  p_or_fuse_out;
    wire [31:0]  expected_epoch_out;
    wire [31:0]  linf_excess_out;
    wire [63:0]  cycle_out;
    wire [31:0]  reset_epoch_out;
    wire signed [63:0] h_phi_a_out;
    wire [63:0]  h_phi_b_out;

    omni_crash3_sluice dut (
        .clk                 (clk),
        .rst_n               (rst_n),
        .l01_reset_strobe    (l01_reset_strobe),
        .l01_witness_ok      (l01_witness_ok),
        .eval_en             (eval_en),
        .seq_epoch           (seq_epoch),
        .q_pos               (q_pos),
        .p_mom               (p_mom),
        .q_bound             (q_bound),
        .eps_k_max           (eps_k_max),
        .lambda_spec         (lambda_spec),
        .g_barrier           (g_barrier),
        .g_dot               (g_dot),
        .tau_hold_ticks      (tau_hold_ticks),
        .pi_risk             (pi_risk),
        .tau_risk            (tau_risk),
        .r_dot               (r_dot),
        .delta_r             (delta_r),
        .k_defect            (k_defect),
        .b_barrier           (b_barrier),
        .c_care              (c_care),
        .dist_mm             (dist_mm),
        .tof_ps              (tof_ps),
        .s_phase_16          (s_phase_16),
        .r_mask_16           (r_mask_16),
        .m_rx_16             (m_rx_16),
        .finder_sig_40       (finder_sig_40),
        .quiet_zone          (quiet_zone),
        .hash_valid          (hash_valid),
        .u_safe_nonempty     (u_safe_nonempty),
        .eta_hw_truth        (eta_hw_truth),
        .witness_ext         (witness_ext),
        .busy_out            (busy_out),
        .eval_done_out       (eval_done_out),
        .port_out            (port_out),
        .reason_out          (reason_out),
        .traj_class_out      (traj_class_out),
        .dk_kill_latched_out (dk_kill_latched_out),
        .monitor_coupled_out (monitor_coupled_out),
        .actuator_v_en_out   (actuator_v_en_out),
        .status_byte_out     (status_byte_out),
        .p_or_fuse_out       (p_or_fuse_out),
        .expected_epoch_out  (expected_epoch_out),
        .linf_excess_out     (linf_excess_out),
        .cycle_out           (cycle_out),
        .reset_epoch_out     (reset_epoch_out),
        .h_phi_a_out         (h_phi_a_out),
        .h_phi_b_out         (h_phi_b_out)
    );

    always #5 clk = ~clk;

    task set_nominal(input [31:0] ep);
        begin
            seq_epoch       = ep;
            q_pos           = 32'sd480;
            p_mom           = 32'sd80;
            q_bound         = 32'd1000;
            eps_k_max       = 32'd250;
            lambda_spec     = -32'sd250;
            g_barrier       = -32'sd500;
            g_dot           = 32'sd10;
            tau_hold_ticks  = 32'd20;
            pi_risk         = 32'd50;
            tau_risk        = 32'd200;
            r_dot           = 32'd100;
            delta_r         = 32'd500;
            k_defect        = 32'd15;
            b_barrier       = 32'd100;
            c_care          = 32'd250;
            dist_mm         = 32'd12000;
            tof_ps          = 32'd80100;
            s_phase_16      = 16'h05A5;
            r_mask_16       = 16'hF00F;
            m_rx_16         = 16'hF5AA;
            finder_sig_40   = 40'h7F_415D_417F;
            quiet_zone      = 8'd4;
            hash_valid      = 1'b1;
            u_safe_nonempty = 1'b1;
            eta_hw_truth    = 1'b1;
            witness_ext     = 1'b1;
        end
    endtask

    task pulse_eval;
        begin
            @(negedge clk);
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
                "%s|BYTE=0x%02x|PORT=%0d|REASON=%02d|TRAJ=%0d|FUSE=0x%04x|LINF=%0d|CYC=%0d|EPOCH=%0d|HPHIA=%0d|HPHIB=%0d",
                tag, status_byte_out, port_out, reason_out,
                traj_class_out, p_or_fuse_out, linf_excess_out,
                cycle_out, reset_epoch_out, h_phi_a_out, h_phi_b_out
            );
        end
    endtask

    initial begin
        rst_n = 1'b0;
        #20;
        rst_n = 1'b1;
        #10;

        // V01
        set_nominal(expected_epoch_out);
        pulse_eval();
        print_vec("V01");

        // V02
        set_nominal(expected_epoch_out);
        pi_risk = 32'd350;
        pulse_eval();
        print_vec("V02");

        // V03
        set_nominal(expected_epoch_out);
        r_dot = 32'd620;
        pulse_eval();
        print_vec("V03");

        // V04
        set_nominal(expected_epoch_out);
        g_barrier = -32'sd150;
        pulse_eval();
        print_vec("V04");

        // V05
        set_nominal(expected_epoch_out);
        q_pos = 32'sd1150;
        pulse_eval();
        print_vec("V05");

        // V06
        set_nominal(expected_epoch_out);
        witness_ext = 1'b0;
        pulse_eval();
        print_vec("V06");

        // V07
        set_nominal(expected_epoch_out);
        pi_risk    = 32'd400;
        r_dot      = 32'd850;
        hash_valid = 1'b0;
        pulse_eval();
        print_vec("V07");

        // V08
        set_nominal(expected_epoch_out);
        pulse_eval();
        print_vec("V08");

        // V09
        pulse_l01_reset(1'b1);
        set_nominal(expected_epoch_out);
        m_rx_16 = 16'hF5AB;
        pulse_eval();
        print_vec("V09");

        // V10
        pulse_l01_reset(1'b1);
        set_nominal(expected_epoch_out);
        dist_mm = 32'd500000;
        tof_ps  = 32'd133420;
        pulse_eval();
        print_vec("V10");

        // V11
        pulse_l01_reset(1'b1);
        set_nominal(expected_epoch_out);
        quiet_zone = 8'd2;
        pulse_eval();
        print_vec("V11");

        // V12
        pulse_l01_reset(1'b1);
        set_nominal(expected_epoch_out);
        p_mom = $signed(32'h8000_0000);
        pulse_eval();
        print_vec("V12");

        $finish;
    end

endmodule
`default_nettype wire
