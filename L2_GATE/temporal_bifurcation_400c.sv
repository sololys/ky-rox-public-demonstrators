`timescale 1ns / 1ps

// =============================================================================
// Module: temporal_bifurcation_400c
// Specification: Kapittel 3.8 (BAR/NLK 400-Cycle Temporal Bifurcation)
// Clock Domain: 80.0 kHz Frisch Clock (T_clk = 12.5 us -> 400 cycles = 5.00 ms)
// Invariant:
//   - Orthodox Order (odot < 1): Witness sealed before actuation -> A_400 = +1 (OPEN)
//   - Retroactive Order (1 < odot): Actuation before witness -> A_400 = -1 (KILL / Crowbar)
//   - Direct KILL (1 < odot emergency): Immediate 0.00 V DC crowbar on cycle 1
// =============================================================================

module temporal_bifurcation_400c #(
    parameter int WINDOW_CYCLES = 400
) (
    input  wire        clk_80khz,
    input  wire        rst_n,
    input  wire        reset_by_l01,            // Physical Level 01 manual unlock
    input  wire        odot_seal_in,            // Witness W_pre fsync seal bit (odot)
    input  wire        actuate_req_in,          // Physical actuation request bit (1)
    input  wire        belnap_paradox_flag_in,  // Q_LP (1,1) contradiction bit[5]
    output reg  [15:0] cycle_counter_out,
    output reg  signed [15:0] levy_area_400_out,
    output reg         sealed_odot_flag_out,
    output reg         causality_violation_fault_out,
    output reg         v_gate_out_5v,
    output reg  [7:0]  rtl_verdict_code_out
);

    localparam [7:0] VERDICT_OK                    = 8'h01; // 5.00 V DC OPEN
    localparam [7:0] VERDICT_HOLD                  = 8'h02; // 2.50 V DC HOLD
    localparam [7:0] VERDICT_KILL                  = 8'h03; // 0.00 V DC KILL
    localparam [7:0] TRAP_RETROACTIVE_CAUSALITY    = 8'hFD; // 1 < odot violation
    localparam [7:0] TRAP_OMEGA_PARADOX            = 8'hFE; // Belnap (1,1) paradox

    reg prev_odot;
    reg prev_act;

    wire signed [15:0] d_odot = $signed({15'd0, odot_seal_in}) - $signed({15'd0, prev_odot});
    wire signed [15:0] d_act  = $signed({15'd0, actuate_req_in}) - $signed({15'd0, prev_act});
    wire signed [15:0] levy_step = ($signed({15'd0, prev_odot}) * d_act)
                                 - ($signed({15'd0, prev_act})  * d_odot);

    always @(posedge clk_80khz or negedge rst_n) begin
        if (!rst_n) begin
            cycle_counter_out             <= 16'd0;
            levy_area_400_out             <= 16'sd0;
            sealed_odot_flag_out          <= 1'b0;
            causality_violation_fault_out <= 1'b0;
            v_gate_out_5v                 <= 1'b0;
            rtl_verdict_code_out          <= VERDICT_KILL;
            prev_odot                     <= 1'b0;
            prev_act                      <= 1'b0;
        end else if (reset_by_l01) begin
            cycle_counter_out             <= 16'd0;
            levy_area_400_out             <= 16'sd0;
            sealed_odot_flag_out          <= 1'b0;
            causality_violation_fault_out <= 1'b0;
            v_gate_out_5v                 <= 1'b0;
            rtl_verdict_code_out          <= VERDICT_HOLD;
            prev_odot                     <= 1'b0;
            prev_act                      <= 1'b0;
        end else begin
            prev_odot     <= odot_seal_in;
            prev_act      <= actuate_req_in;
            levy_area_400_out <= levy_area_400_out + levy_step;

            if (belnap_paradox_flag_in) begin
                // Quaternary Belnap (1,1) paradox isolation -> immediate 0.00 V DC KILL
                causality_violation_fault_out <= 1'b1;
                v_gate_out_5v                 <= 1'b0;
                rtl_verdict_code_out          <= TRAP_OMEGA_PARADOX;
            end else if (causality_violation_fault_out) begin
                // Sticky Uzzah latch until reset_by_l01
                v_gate_out_5v        <= 1'b0;
                rtl_verdict_code_out <= TRAP_RETROACTIVE_CAUSALITY;
            end else if (actuate_req_in && !odot_seal_in) begin
                // Retroactive causality violation (1 < odot): actuation attempted before witness seal
                causality_violation_fault_out <= 1'b1;
                v_gate_out_5v                 <= 1'b0;
                rtl_verdict_code_out          <= TRAP_RETROACTIVE_CAUSALITY;
            end else begin
                if (odot_seal_in) begin
                    sealed_odot_flag_out <= 1'b1;
                    if (cycle_counter_out < WINDOW_CYCLES[15:0]) begin
                        cycle_counter_out <= cycle_counter_out + 16'd1;
                    end
                end

                if (sealed_odot_flag_out && actuate_req_in &&
                    (cycle_counter_out >= WINDOW_CYCLES[15:0]) &&
                    ((levy_area_400_out + levy_step) > 16'sd0)) begin
                    // Orthodox order (odot < 1) after full 400-cycle fsync hardening & A_400 > 0
                    v_gate_out_5v        <= 1'b1;
                    rtl_verdict_code_out <= VERDICT_OK;
                end else begin
                    // 2.50 V DC HOLD while waiting in the 400-cycle airlock
                    v_gate_out_5v        <= 1'b0;
                    rtl_verdict_code_out <= VERDICT_HOLD;
                end
            end
        end
    end

endmodule
