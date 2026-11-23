`timescale 1ns/1ps

module tb_omega_symplectic_watchdog_64b;
    logic        clk = 1'b0;
    logic        hw_reset_n = 1'b0;
    logic        w_ext_arm = 1'b0;
    logic        frame_valid = 1'b0;
    logic [31:0] magic_sync = 32'h4F4D_4547;
    logic [31:0] step_counter = 32'd0;
    logic [63:0] l_now = 64'd0;
    logic [63:0] l_heat = 64'd0;
    logic [63:0] l_init = 64'd0;

    logic        relay_out_5v;
    logic        latched_kill;
    logic        armed_state;

    // Small timeout (20 cycles) for fast deterministic simulation
    omega_symplectic_watchdog_64b #(
        .TIMEOUT_CYCLES(14'd20)
    ) dut (
        .clk(clk),
        .hw_reset_n(hw_reset_n),
        .w_ext_arm(w_ext_arm),
        .frame_valid(frame_valid),
        .magic_sync(magic_sync),
        .step_counter(step_counter),
        .l_now(l_now),
        .l_heat(l_heat),
        .l_init(l_init),
        .relay_out_5v(relay_out_5v),
        .latched_kill(latched_kill),
        .armed_state(armed_state)
    );

    always #5 clk = ~clk;

    task automatic send_frame(
        input logic [31:0] step_v,
        input logic [63:0] now_v,
        input logic [63:0] heat_v,
        input logic [63:0] init_v
    );
        begin
            @(negedge clk);
            magic_sync   = 32'h4F4D_4547;
            step_counter = step_v;
            l_now        = now_v;
            l_heat       = heat_v;
            l_init       = init_v;
            frame_valid  = 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            frame_valid  = 1'b0;
        end
    endtask

    initial begin
        // T1: Reset starts fail-closed in HOLD (0.00 V)
        hw_reset_n = 1'b0;
        repeat (2) @(posedge clk);
        #1;
        if (relay_out_5v !== 1'b0 || latched_kill !== 1'b0) begin
            $fatal(1, "FAIL T1: Reset must be 0V HOLD, not OPEN or KILL");
        end
        hw_reset_n = 1'b1;

        // T2: Valid frame WITHOUT w_ext_arm stays in HOLD (0.00 V)
        w_ext_arm = 1'b0;
        send_frame(32'd1, 64'd900, 64'd100, 64'd1000);
        if (relay_out_5v !== 1'b0 || latched_kill !== 1'b0) begin
            $fatal(1, "FAIL T2: Valid frame without w_ext_arm must stay HOLD (0V)");
        end

        // T3: Valid frame WITH w_ext_arm opens gate (5.00 V modeled)
        w_ext_arm = 1'b1;
        send_frame(32'd1, 64'd900, 64'd100, 64'd1000);
        if (relay_out_5v !== 1'b1 || latched_kill !== 1'b0) begin
            $fatal(1, "FAIL T3: Valid frame + w_ext_arm must OPEN");
        end

        // T4: Conservation breach (900 + 101 != 1000) -> immediate 1-cycle sticky KILL
        send_frame(32'd2, 64'd900, 64'd101, 64'd1000);
        if (relay_out_5v !== 1'b0 || latched_kill !== 1'b1) begin
            $fatal(1, "FAIL T4: Conservation breach must trip sticky KILL (0V)");
        end

        // Verify sticky KILL cannot be cleared by valid SPI frame
        send_frame(32'd3, 64'd900, 64'd100, 64'd1000);
        if (relay_out_5v !== 1'b0 || latched_kill !== 1'b1) begin
            $fatal(1, "FAIL T4b: Sticky KILL must ignore subsequent SPI frames");
        end

        // T5: Physical hw_reset_n clears latch -> re-arm -> watchdog timeout -> sticky KILL
        @(negedge clk); hw_reset_n = 1'b0;
        @(posedge clk); #1;
        @(negedge clk); hw_reset_n = 1'b1;
        send_frame(32'd1, 64'd800, 64'd200, 64'd1000);
        if (relay_out_5v !== 1'b1) begin
            $fatal(1, "FAIL T5a: Re-arm after physical reset failed");
        end
        // Pull cable: wait > 20 cycles with no frames
        repeat (22) @(posedge clk);
        #1;
        if (relay_out_5v !== 1'b0 || latched_kill !== 1'b1) begin
            $fatal(1, "FAIL T5b: Watchdog timeout must trip sticky KILL (0V)");
        end

        $display("OMEGA_SYMPLECTIC_WATCHDOG_64B_TB=PASS (5/5 TESTS PASSED)");
        $finish;
    end
endmodule
