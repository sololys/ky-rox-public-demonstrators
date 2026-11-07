`timescale 1ns / 1ps

module tb_temporal_bifurcation_400c;

    reg         clk_80khz = 1'b0;
    reg         rst_n = 1'b0;
    reg         reset_by_l01 = 1'b0;
    reg         odot_seal_in = 1'b0;
    reg         actuate_req_in = 1'b0;
    reg         belnap_paradox_flag_in = 1'b0;

    wire [15:0] cycle_counter_out;
    wire signed [15:0] levy_area_400_out;
    wire        sealed_odot_flag_out;
    wire        causality_violation_fault_out;
    wire        v_gate_out_5v;
    wire [7:0]  rtl_verdict_code_out;

    // 80 kHz clock -> period = 12,500 ns (12.5 us)
    always #6250 clk_80khz = ~clk_80khz;

    temporal_bifurcation_400c #(
        .WINDOW_CYCLES(400)
    ) dut (
        .clk_80khz(clk_80khz),
        .rst_n(rst_n),
        .reset_by_l01(reset_by_l01),
        .odot_seal_in(odot_seal_in),
        .actuate_req_in(actuate_req_in),
        .belnap_paradox_flag_in(belnap_paradox_flag_in),
        .cycle_counter_out(cycle_counter_out),
        .levy_area_400_out(levy_area_400_out),
        .sealed_odot_flag_out(sealed_odot_flag_out),
        .causality_violation_fault_out(causality_violation_fault_out),
        .v_gate_out_5v(v_gate_out_5v),
        .rtl_verdict_code_out(rtl_verdict_code_out)
    );

    integer i;
    integer errors = 0;

    initial begin
        $display("=== [TB_400C] Starting 400-Cycle Temporal Bifurcation & Levy Area RTL Verification ===");

        // Reset
        rst_n = 1'b0;
        @(posedge clk_80khz);
        @(posedge clk_80khz);
        rst_n = 1'b1;
        @(posedge clk_80khz);

        // ---------------------------------------------------------------------
        // Vector 1: Orthodox Causal Order (odot < 1) over 400 clock cycles
        // ---------------------------------------------------------------------
        odot_seal_in   = 1'b1;
        actuate_req_in = 1'b0;

        for (i = 0; i < 400; i = i + 1) begin
            @(posedge clk_80khz);
        end

        // Now assert actuation after 400 cycles of sealed witness
        actuate_req_in = 1'b1;
        @(posedge clk_80khz);
        #1;

        if (v_gate_out_5v !== 1'b1 || rtl_verdict_code_out !== 8'h01 || levy_area_400_out !== 16'sd1) begin
            $display("FAIL [Vector 1]: Expected OPEN (5V), code=0x01, A_400=+1; got v=%b, code=0x%02h, A_400=%0d",
                     v_gate_out_5v, rtl_verdict_code_out, levy_area_400_out);
            errors = errors + 1;
        end else begin
            $display("[PASS] Vector 1 (Orthodox odot < 1): 400 cycles (5.00 ms) verified -> A_400 = +1, v_gate_out_5v = 1 (5.00 V DC OPEN)");
        end

        // ---------------------------------------------------------------------
        // Vector 2: Reset by L01, then Retroactive Rationalization (1 < odot)
        // ---------------------------------------------------------------------
        odot_seal_in   = 1'b0;
        actuate_req_in = 1'b0;
        reset_by_l01   = 1'b1;
        @(posedge clk_80khz);
        #1;
        reset_by_l01   = 1'b0;
        @(posedge clk_80khz);
        #1;

        // Fire actuation BEFORE witness is sealed (1 < odot)
        actuate_req_in = 1'b1;
        odot_seal_in   = 1'b0;
        @(posedge clk_80khz);
        #1;

        // Attempt to patch witness retroactively
        odot_seal_in   = 1'b1;
        @(posedge clk_80khz);
        #1;

        if (v_gate_out_5v !== 1'b0 || causality_violation_fault_out !== 1'b1 ||
            rtl_verdict_code_out !== 8'hFD || levy_area_400_out !== -16'sd1) begin
            $display("FAIL [Vector 2]: Expected KILL (0V), fault=1, code=0xFD, A_400=-1; got v=%b, fault=%b, code=0x%02h, A_400=%0d",
                     v_gate_out_5v, causality_violation_fault_out, rtl_verdict_code_out, levy_area_400_out);
            errors = errors + 1;
        end else begin
            $display("[PASS] Vector 2 (Retroactive 1 < odot): Post-hoc witness rejected -> A_400 = -1, v_gate_out_5v = 0 (0.00 V DC KILL, 0xFD)");
        end

        // ---------------------------------------------------------------------
        // Vector 3: Reset by L01, then Belnap Quaternary Paradox (1,1)
        // ---------------------------------------------------------------------
        odot_seal_in   = 1'b0;
        actuate_req_in = 1'b0;
        reset_by_l01   = 1'b1;
        @(posedge clk_80khz);
        reset_by_l01   = 1'b0;
        @(posedge clk_80khz);

        belnap_paradox_flag_in = 1'b1;
        @(posedge clk_80khz);
        #1;

        if (v_gate_out_5v !== 1'b0 || rtl_verdict_code_out !== 8'hFE) begin
            $display("FAIL [Vector 3]: Expected KILL (0V), code=0xFE; got v=%b, code=0x%02h",
                     v_gate_out_5v, rtl_verdict_code_out);
            errors = errors + 1;
        end else begin
            $display("[PASS] Vector 3 (Belnap Q_LP (1,1) Paradox): Isolated to empty set -> v_gate_out_5v = 0 (0.00 V DC KILL, 0xFE)");
        end

        if (errors == 0) begin
            $display("=== [TB_400C] ALL 3/3 RTL VECTORS PASSED (0 ERRORS) ===");
            $finish;
        end else begin
            $display("=== [TB_400C] FAILED WITH %0d ERRORS ===", errors);
            $fatal(1);
        end
    end

endmodule
