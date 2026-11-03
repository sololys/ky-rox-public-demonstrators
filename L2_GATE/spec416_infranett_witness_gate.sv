// =============================================================================
// SOLOLYS // SPEC-416 INFRANETT CAUSAL WITNESS (W_pre -> W_post) & GRID GATE
// Standard: IEEE 1800-2012 | State Anchor: 32'hABCDEF00 | Fail-Closed: 0.00V DC
// Enforces:
//   1. Monotonic Sequence C > C_hw (Anti-Replay)
//   2. Causal Witness Binding: H(W_pre)_expected == H(W_pre)_post (TOCTOU Trap)
//   3. Exact Rational Kirchhoff Conservation: delta_r_num_i == 64'sd0
//   4. 1550nm Dark-Fiber OTDR Attenuation (<= 250 mdB/km) & Step Loss (< 1000 mdB)
//   5. IEEE 1588v2 PTP Phase Lock (|ptp_offset_ns| <= 100 ns)
//   6. VSG 50 Hz Grid Envelope [49500..50500 mHz] & BFT Quorum (>= 2f + 1)
//   7. Registry B Physical D-Latch (t_ADC >= t_clk && I_shunt >= 500 uA)
// =============================================================================
`default_nettype none

module spec416_infranett_witness_gate #(
    parameter logic [31:0] EXPECTED_MAGIC        = 32'hABCD_EF00,
    parameter logic [15:0] MAX_OTDR_ATTEN_MDB_KM = 16'd250,   // 0.250 dB/km
    parameter logic [15:0] MAX_OTDR_STEP_HOLD    = 16'd50,    // 0.050 dB tap
    parameter logic [15:0] MAX_OTDR_STEP_KILL    = 16'd1000,  // 1.000 dB fiber cut
    parameter logic [15:0] MIN_GRID_FREQ_MHZ     = 16'd49500, // 49.500 Hz
    parameter logic [15:0] MAX_GRID_FREQ_MHZ     = 16'd50500, // 50.500 Hz
    parameter logic [15:0] MAX_PTP_OFFSET_NS     = 16'd100,   // 100 ns PTP window
    parameter logic [15:0] MIN_SHUNT_UA          = 16'd500    // 500 uA Registry B
) (
    input  wire                clk_sys_i,
    input  wire                rst_n_i,
    input  wire  [31:0]        frame_magic_i,
    input  wire                capsule_crc_ok_i,
    input  wire  [63:0]        seq_c_i,
    input  wire  [63:0]        committed_c_hw_i,
    input  wire  [255:0]       w_pre_hash_computed_i,
    input  wire  [255:0]       w_post_bound_pre_hash_i,
    input  wire  signed [63:0] kirchhoff_delta_r_num_i,
    input  wire  [15:0]        fiber_atten_mdb_km_i,
    input  wire  [15:0]        fiber_step_loss_mdb_i,
    input  wire  [15:0]        grid_freq_mhz_i,
    input  wire  [15:0]        ptp_abs_offset_ns_i,
    input  wire  [7:0]         bft_valid_sigs_i,
    input  wire  [7:0]         bft_fault_f_i,
    input  wire                adc_time_valid_i,
    input  wire  [15:0]        shunt_current_ua_i,
    output logic [1:0]         gate_state_o,    // 2'b00=HOLD, 2'b01=OPEN, 2'b11=KILL
    output logic               breaker_pin_o    // Physical breaker/relay (0 = 0.00V DC)
);

    localparam logic [1:0] STATE_HOLD = 2'b00;
    localparam logic [1:0] STATE_OPEN = 2'b01;
    localparam logic [1:0] STATE_KILL = 2'b11;

    wire [7:0] bft_quorum_min = (bft_fault_f_i << 1) + 8'd1;
    wire       toctou_match   = (w_pre_hash_computed_i == w_post_bound_pre_hash_i);
    wire       monotonic_ok   = (seq_c_i > committed_c_hw_i);
    wire       kirchhoff_ok   = (kirchhoff_delta_r_num_i == 64'sd0);

    logic kill_latched_q;

    always_ff @(posedge clk_sys_i or negedge rst_n_i) begin
        if (!rst_n_i) begin
            kill_latched_q <= 1'b0;
            gate_state_o   <= STATE_HOLD;
            breaker_pin_o  <= 1'b0; // Default rest state: 0.00 V DC
        end else begin
            // Permanent KILL trap: Registry A breach, TOCTOU mismatch, Replay, Kirchhoff != 0, or severed fiber
            if (kill_latched_q ||
                (frame_magic_i != EXPECTED_MAGIC) ||
                !capsule_crc_ok_i ||
                !monotonic_ok ||
                !toctou_match ||
                !kirchhoff_ok ||
                (fiber_step_loss_mdb_i >= MAX_OTDR_STEP_KILL)) begin
                kill_latched_q <= 1'b1;
                gate_state_o   <= STATE_KILL;
                breaker_pin_o  <= 1'b0;
            end
            // HOLD conditions: OTDR tap, PTP drift, Grid freq excursion, BFT quorum < 2f+1, or Registry B
            else if ((fiber_atten_mdb_km_i > MAX_OTDR_ATTEN_MDB_KM) ||
                     (fiber_step_loss_mdb_i > MAX_OTDR_STEP_HOLD) ||
                     (grid_freq_mhz_i < MIN_GRID_FREQ_MHZ) ||
                     (grid_freq_mhz_i > MAX_GRID_FREQ_MHZ) ||
                     (ptp_abs_offset_ns_i > MAX_PTP_OFFSET_NS) ||
                     (bft_valid_sigs_i < bft_quorum_min) ||
                     !adc_time_valid_i ||
                     (shunt_current_ua_i < MIN_SHUNT_UA)) begin
                gate_state_o  <= STATE_HOLD;
                breaker_pin_o <= 1'b0; // Clamped at 0.00 V DC
            end
            // Witnessed L3 Physical Consequence Admitted
            else begin
                gate_state_o  <= STATE_OPEN;
                breaker_pin_o <= 1'b1;
            end
        end
    end

endmodule
`default_nettype wire
