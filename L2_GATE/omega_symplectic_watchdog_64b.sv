// =============================================================================
// omega_symplectic_watchdog_64b.sv — Synthesizable Fail-Closed RTL Watchdog
// =============================================================================
// Standard       : IEEE 1800-2012 (SystemVerilog), 0 float, integer-only
// Epistemic Tier : L1.5 RTL Simulation Model (PHYSICAL_AUTHORITY = NONE)
// Invariants:
//   1. Reset always enters safe HOLD (relay_out_5v = 0, armed = 0, latched_kill = 0).
//   2. OPEN requires explicit external human arm (w_ext_arm) + valid frame +
//      exact conservation (l_now + l_heat == l_init, no 64-bit overflow) +
//      strictly monotonic step_counter == prev_step + 1.
//   3. Any invariant/sequence breach on frame_valid OR watchdog timeout trips
//      sticky latched_kill = 1 and forces relay_out_5v = 0 in 1 clock cycle.
//   4. Sticky latched_kill can ONLY be cleared by physical hw_reset_n == 0.
// =============================================================================
`timescale 1ns/1ps

module omega_symplectic_watchdog_64b #(
    parameter logic [13:0] TIMEOUT_CYCLES = 14'd12000  // 1.00 ms @ 12 MHz
) (
    input  logic        clk,
    input  logic        hw_reset_n,
    input  logic        w_ext_arm,      // External Level-01 arm enable
    input  logic        frame_valid,    // 1-cycle strobe when 64B SPI frame arrives
    input  logic [31:0] magic_sync,
    input  logic [31:0] step_counter,
    input  logic [63:0] l_now,
    input  logic [63:0] l_heat,
    input  logic [63:0] l_init,
    output logic        relay_out_5v,   // 1 = OPEN (L1.5 modeled 5V), 0 = 0.00V
    output logic        latched_kill,   // Sticky KILL latch
    output logic        armed_state     // 1 when armed and tracking frames
);

    localparam logic [31:0] MAGIC_OMEG = 32'h4F4D_4547;

    logic [13:0] watchdog_timer;
    logic [31:0] prev_step;
    logic        has_first_frame;

    // 65-bit exact sum to detect 64-bit overflow without wrap-around
    logic [64:0] l_sum_ext;
    logic        conservation_ok;
    logic        sequence_ok;
    logic        frame_ok;

    always_comb begin
        l_sum_ext       = {1'b0, l_now} + {1'b0, l_heat};
        conservation_ok = (magic_sync == MAGIC_OMEG) &&
                          (l_sum_ext[64] == 1'b0) &&
                          (l_sum_ext[63:0] == l_init);
        sequence_ok     = (!has_first_frame) ? (step_counter == 32'd1)
                                             : (step_counter == (prev_step + 32'd1));
        frame_ok        = conservation_ok && sequence_ok;
    end

    always_ff @(posedge clk or negedge hw_reset_n) begin
        if (!hw_reset_n) begin
            watchdog_timer  <= 14'd0;
            prev_step       <= 32'd0;
            has_first_frame <= 1'b0;
            armed_state     <= 1'b0;
            latched_kill    <= 1'b0;
            relay_out_5v    <= 1'b0; // Fail-closed HOLD at 0.00 V
        end else if (latched_kill) begin
            // Sticky KILL: ignore all SPI traffic until physical hw_reset_n
            relay_out_5v    <= 1'b0;
            armed_state     <= 1'b0;
        end else if (frame_valid) begin
            if (!frame_ok) begin
                // Immediate 1-cycle KILL on conservation, magic, overflow, or sequence breach
                latched_kill <= 1'b1;
                relay_out_5v <= 1'b0;
                armed_state  <= 1'b0;
            end else if (!w_ext_arm) begin
                // Valid frame without external human witness -> remain in HOLD (0.00 V)
                relay_out_5v <= 1'b0;
                armed_state  <= 1'b0;
            end else begin
                // Valid frame + external arm -> OPEN and reset watchdog
                watchdog_timer  <= 14'd0;
                prev_step       <= step_counter;
                has_first_frame <= 1'b1;
                armed_state     <= 1'b1;
                relay_out_5v    <= 1'b1;
            end
        end else if (armed_state) begin
            if (watchdog_timer >= TIMEOUT_CYCLES) begin
                // Cable cut / deadline missed -> 1-cycle sticky KILL
                latched_kill <= 1'b1;
                relay_out_5v <= 1'b0;
                armed_state  <= 1'b0;
            end else begin
                watchdog_timer <= watchdog_timer + 14'd1;
            end
        end
    end

endmodule
