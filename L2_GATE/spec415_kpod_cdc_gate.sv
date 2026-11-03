// =============================================================================
// SOLOLYS // SPEC-415 K-POD (-240m) 5-CDC & REGISTRY B HARDWARE LATCH GATE
// Standard: IEEE 1800-2012 | State Anchor: 32'hABCDEF00 | Fail-Closed: 0.00V DC
// =============================================================================
`default_nettype none

module spec415_kpod_cdc_gate #(
    parameter logic [31:0] EXPECTED_MAGIC     = 32'hABCD_EF00,
    parameter logic [15:0] SPL_HOLD_LIMIT_DBX = 16'd1450, // 145.0 dB (scaled x10)
    parameter logic [15:0] SPL_KILL_LIMIT_DBX = 16'd1600, // 160.0 dB (scaled x10)
    parameter logic [15:0] MAX_TOF_DIFF_MM    = 16'd15,   // 15 mm (0.015 m)
    parameter logic [15:0] MIN_SHUNT_UA       = 16'd500   // 500 uA Registry B threshold
) (
    input  wire         clk_sys_i,          // 100 MHz Master Synchronous Clock
    input  wire         rst_n_i,            // Active-low asynchronous reset
    input  wire  [4:0]  cdc_async_valid_i,  // 5x Async sensor domain health strobes
    input  wire  [31:0] frame_magic_i,      // Decoded from 205B capsule header
    input  wire         capsule_crc_ok_i,   // From fpga_capsule_frame_205b_decoder
    input  wire  [15:0] acoustic_spl_dbx_i, // Hydrophone SPL in 0.1 dB units
    input  wire  [15:0] range_532nm_mm_i,   // 532nm Blue-Green Optical ToF (mm)
    input  wire  [15:0] range_uwb_mm_i,     // UWB Electromagnetic ToF (mm)
    input  wire         adc_time_valid_i,   // (t_ADC >= t_clk)
    input  wire  [15:0] shunt_current_ua_i, // Physical D-Latch shunt current (uA)
    output logic [1:0]  gate_state_o,       // 2'b00=HOLD, 2'b01=OPEN, 2'b11=KILL
    output logic        actuate_pin_o       // Physical output pin (0 = 0.00V DC)
);

    localparam logic [1:0] STATE_HOLD = 2'b00;
    localparam logic [1:0] STATE_OPEN = 2'b01;
    localparam logic [1:0] STATE_KILL = 2'b11;

    // -------------------------------------------------------------------------
    // 1. 5x Asynchronous 2-Stage Flip-Flop CDC Synchronizers
    // -------------------------------------------------------------------------
    logic [4:0] cdc_meta_q;
    logic [4:0] cdc_sync_q;

    always_ff @(posedge clk_sys_i or negedge rst_n_i) begin
        if (!rst_n_i) begin
            cdc_meta_q <= 5'b00000;
            cdc_sync_q <= 5'b00000;
        end else begin
            cdc_meta_q <= cdc_async_valid_i;
            cdc_sync_q <= cdc_meta_q;
        end
    end

    wire all_cdc_locked = &cdc_sync_q;

    // -------------------------------------------------------------------------
    // 2. Dual-Physics ToF Absolute Divergence (|d_532 - d_UWB| <= 15 mm)
    // -------------------------------------------------------------------------
    logic [15:0] tof_abs_diff_mm;
    always_comb begin
        if (range_532nm_mm_i >= range_uwb_mm_i)
            tof_abs_diff_mm = range_532nm_mm_i - range_uwb_mm_i;
        else
            tof_abs_diff_mm = range_uwb_mm_i - range_532nm_mm_i;
    end

    // -------------------------------------------------------------------------
    // 3. Fail-Closed State Machine & Registry A/B Physical Latch
    // -------------------------------------------------------------------------
    logic kill_latched_q;

    always_ff @(posedge clk_sys_i or negedge rst_n_i) begin
        if (!rst_n_i) begin
            kill_latched_q <= 1'b0;
            gate_state_o   <= STATE_HOLD;
            actuate_pin_o  <= 1'b0; // Clamped at 0.00 V DC
        end else begin
            // Permanent KILL trap on Registry A schema breach or >= 160.0 dB shockwave
            if (kill_latched_q || (frame_magic_i != EXPECTED_MAGIC) ||
                !capsule_crc_ok_i || (acoustic_spl_dbx_i >= SPL_KILL_LIMIT_DBX)) begin
                kill_latched_q <= 1'b1;
                gate_state_o   <= STATE_KILL;
                actuate_pin_o  <= 1'b0;
            end
            // HOLD conditions: CDC metastability, >= 145.0 dB sabotage, ToF divergence, or Reg B
            else if (!all_cdc_locked ||
                     (acoustic_spl_dbx_i >= SPL_HOLD_LIMIT_DBX) ||
                     (tof_abs_diff_mm > MAX_TOF_DIFF_MM) ||
                     !adc_time_valid_i ||
                     (shunt_current_ua_i < MIN_SHUNT_UA)) begin
                gate_state_o  <= STATE_HOLD;
                actuate_pin_o <= 1'b0; // Clamped at 0.00 V DC
            end
            // Witnessed L3 Physical Consequence Admitted
            else begin
                gate_state_o  <= STATE_OPEN;
                actuate_pin_o <= 1'b1;
            end
        end
    end

endmodule
`default_nettype wire
