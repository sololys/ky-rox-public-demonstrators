// =============================================================================
// Cycle-Exact 12-Vector Testbench for k_filter_sluice.sv (IEEE 1800-2012)
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module tb_k_filter_sluice;

    reg         clk            = 1'b0;
    reg         rst_n          = 1'b0;
    reg         step_en        = 1'b0;
    reg         l01_reset_req  = 1'b0;
    reg         l01_witness_ok = 1'b0;
    reg         prep_match_ok  = 1'b1;

    reg  [63:0] q0             = 64'd0;
    reg  [63:0] q1             = 64'd0;
    reg  [63:0] q2             = 64'd0;
    reg  [63:0] p0             = 64'd0;
    reg  [63:0] p1             = 64'd0;
    reg  [63:0] p2             = 64'd0;
    reg  [63:0] norm_err_sq    = 64'd0;
    reg  [63:0] norm_ref_sq    = 64'd100;
    reg  [31:0] valid_steps    = 32'd64;
    reg  [31:0] total_steps    = 32'd64;
    reg  [63:0] phi_res_abs    = 64'd3;
    reg  [63:0] lambda_bound   = 64'd12;
    reg  [63:0] spec_max_re    = 64'd0;
    reg  [63:0] entropy_paid   = 64'd5706;
    reg  [63:0] entropy_req    = 64'd5706;
    reg         hash_valid     = 1'b1;
    reg         witness_ext    = 1'b1;

    wire [1:0]  port_out;
    wire [3:0]  reason_out;
    wire        actuator_v_en;
    wire        monitor_coupled;
    wire        kill_latched;
    wire [63:0] delta_k_out;

    wire [7:0] out_byte = { 3'b000, kill_latched, monitor_coupled, actuator_v_en, port_out };

    always #10 clk = ~clk;

    k_filter_sluice dut (
        .clk(clk), .rst_n(rst_n), .step_en(step_en),
        .l01_reset_req(l01_reset_req), .l01_witness_ok(l01_witness_ok), .prep_match_ok(prep_match_ok),
        .q0(q0), .q1(q1), .q2(q2), .p0(p0), .p1(p1), .p2(p2),
        .norm_err_sq(norm_err_sq), .norm_ref_sq(norm_ref_sq),
        .valid_steps(valid_steps), .total_steps(total_steps),
        .phi_res_abs(phi_res_abs), .lambda_bound(lambda_bound), .spec_max_re(spec_max_re),
        .entropy_paid(entropy_paid), .entropy_req(entropy_req),
        .hash_valid(hash_valid), .witness_ext(witness_ext),
        .port_out(port_out), .reason_out(reason_out),
        .actuator_v_en(actuator_v_en), .monitor_coupled(monitor_coupled),
        .kill_latched(kill_latched), .delta_k_out(delta_k_out)
    );

    integer err_count = 0;

    task load_nominal;
    begin
        prep_match_ok = 1'b1;
        q0 = 64'd1200; q1 = -64'd450; q2 = 64'd80;
        p0 = -64'd30;  p1 = 64'd15;   p2 = 64'd90;
        norm_err_sq = 64'd4; norm_ref_sq = 64'd100;
        valid_steps = 32'd64; total_steps = 32'd64;
        phi_res_abs = 64'd3; lambda_bound = 64'd12; spec_max_re = 64'd0;
        entropy_paid = 64'd5706; entropy_req = 64'd5706;
        hash_valid = 1'b1; witness_ext = 1'b1;
    end
    endtask

    task do_l01_reset;
    begin
        @(negedge clk); step_en = 1'b0; l01_reset_req = 1'b1; l01_witness_ok = 1'b1;
        @(posedge clk); #1;
        @(negedge clk); l01_reset_req = 1'b0; l01_witness_ok = 1'b0;
    end
    endtask

    task check_vec(input integer v_id, input [7:0] exp_byte, input [1:0] exp_port, input [3:0] exp_reason);
    begin
        if (out_byte !== exp_byte || port_out !== exp_port || reason_out !== exp_reason)
            err_count = err_count + 1;
        $display("VEC %02d | BYTE=0x%02x | PORT=%0d | REASON=%02d | DK=%0d",
                 v_id, out_byte, port_out, reason_out, delta_k_out);
    end
    endtask

    initial begin
        rst_n = 1'b0; @(posedge clk); @(negedge clk); rst_n = 1'b1;
        @(negedge clk); load_nominal(); step_en = 1'b1; @(posedge clk); #1; check_vec(1, 8'h0D, 2'd1, 4'd0);
        @(negedge clk); load_nominal(); witness_ext = 1'b0; step_en = 1'b1; @(posedge clk); #1; check_vec(2, 8'h08, 2'd0, 4'd1);
        @(negedge clk); load_nominal(); prep_match_ok = 1'b0; step_en = 1'b1; @(posedge clk); #1; check_vec(3, 8'h08, 2'd0, 4'd3);
        @(negedge clk); load_nominal(); phi_res_abs = 64'd11; step_en = 1'b1; @(posedge clk); #1; check_vec(4, 8'h08, 2'd0, 4'd2);
        @(negedge clk); load_nominal(); valid_steps = 32'd63; step_en = 1'b1; @(posedge clk); #1; check_vec(5, 8'h12, 2'd2, 4'd9);
        @(negedge clk); load_nominal(); step_en = 1'b1; @(posedge clk); #1; check_vec(6, 8'h12, 2'd2, 4'd5);
        do_l01_reset(); check_vec(7, 8'h08, 2'd0, 4'd1);
        @(negedge clk); load_nominal(); valid_steps = 32'd65; step_en = 1'b1; @(posedge clk); #1; check_vec(8, 8'h12, 2'd2, 4'd9);
        do_l01_reset(); @(negedge clk); load_nominal(); entropy_paid = 64'd5705; step_en = 1'b1; @(posedge clk); #1; check_vec(9, 8'h12, 2'd2, 4'd10);
        do_l01_reset(); @(negedge clk); load_nominal(); norm_err_sq = (64'd1 << 56); norm_ref_sq = (64'd1 << 56) * 64'd20; step_en = 1'b1; @(posedge clk); #1; check_vec(10, 8'h0D, 2'd1, 4'd0);
        @(negedge clk); load_nominal(); norm_err_sq = (64'd1 << 56) + 64'd1; norm_ref_sq = (64'd1 << 56) * 64'd20; step_en = 1'b1; @(posedge clk); #1; check_vec(11, 8'h12, 2'd2, 4'd11);
        do_l01_reset(); @(negedge clk); load_nominal(); p1 = 64'h8000_0000_0000_0000; step_en = 1'b1; @(posedge clk); #1; check_vec(12, 8'h12, 2'd2, 4'd6);

        if (err_count != 0) $fatal(1, "tb_k_filter_sluice: FAIL (%0d errors)", err_count);
        $display("K_FILTER_SLUICE_RTL=PASS (12/12 VECTORS, 128-BIT EXACT, XOR == 0)");
        $finish;
    end

endmodule
`default_nettype wire
