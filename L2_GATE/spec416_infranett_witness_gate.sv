// =============================================================================
// SOLOLYS // SPEC-416 INFRANETT CAUSAL WITNESS & MICROGRID INTERLOCK GATE
// Standard: IEEE 1800-2012 | State Anchor: 32'hABCDEF00 | Frame: 205B (1640b)
// Enforces: W_pre -> W_post TOCTOU Lock, Kirchhoff dR=0/1, 1550nm OTDR, Reg B
// =============================================================================
`default_nettype none

module spec416_infranett_witness_gate #(
    parameter logic [31:0] EXPECTED_MAGIC     = 32'hABCD_EF00,
    parameter logic [31:0] MAX_OTDR_ATTEN_MDB = 32'd250,   // 0.250 dB/km
    parameter logic [15:0] MAX_OTDR_STEP_MDB  = 16'd50,    // 0.050 dB HOLD limit
    parameter logic [15:0] KILL_OTDR_STEP_MDB = 16'd1000,  // 1.000 dB KILL limit
    parameter signed [31:0] MIN_FREQ_MHZ      = 32'sd49500,// 49.500 Hz
    parameter signed [31:0] MAX_FREQ_MHZ      = 32'sd50500,// 50.500 Hz
    parameter logic [15:0] MAX_ROCOF_MHZ_S    = 16'd2000,  // 2.000 Hz/s KILL limit
    parameter logic [63:0] MAX_PTP_OFFSET_NS  = 64'd100,   // 100 ns IEEE 1588v2
    parameter logic [31:0] MIN_SHUNT_UA       = 32'd500    // 500 uA Registry B
) (
    input  wire          clk_sys_i,
    input  wire          rst_n_i,
    input  wire          frame_valid_i,
    input  wire [1639:0] frame_205b_i,          // 119B W_pre [1639:688] + 86B W_post [687:0]
    input  wire [255:0]  computed_w_pre_sha_i,  // Hardware SHA-256 over W_pre[0..118]
    input  wire [255:0]  expected_post_exec_i,  // H(H(W_pre) || M || L || Exec)
    input  wire [15:0]   otdr_step_loss_mdb_i,  // Local splice/bend step loss (mdB)
    input  wire [15:0]   rocof_abs_mhz_s_i,     // |df/dt| in mHz/s
    input  wire          crc32_valid_i,         // IEEE 802.3 CRC-32 check over 0..200
    output logic [1:0]   gate_state_o,          // 2'b00=HOLD, 2'b01=OPEN, 2'b11=KILL
    output logic         breaker_actuate_o      // 1'b0 = 0.00V DC Safe Rest State
);

    localparam logic [1:0] STATE_HOLD = 2'b00;
    localparam logic [1:0] STATE_OPEN = 2'b01;
    localparam logic [1:0] STATE_KILL = 2'b11;

    // -------------------------------------------------------------------------
    // 1. Exact Big-Endian Field Extraction from 205B Capsule (1640 bits)
    // -------------------------------------------------------------------------
    // W_pre (Bytes 0..118 -> Bits 1639..688)
    wire [31:0]  w_pre_magic       = frame_205b_i[1639:1608]; // Offset 0..3
    wire [63:0]  w_pre_seq_c       = frame_205b_i[1607:1544]; // Offset 4..11
    wire [7:0]   w_pre_valid_sigs  = frame_205b_i[1503:1496]; // Offset 17
    wire [7:0]   w_pre_fault_f     = frame_205b_i[1495:1488]; // Offset 18
    wire signed [63:0] delta_r_num = frame_205b_i[1487:1424]; // Offset 19..26
    wire signed [63:0] delta_r_den = frame_205b_i[1423:1360]; // Offset 27..34
    wire [31:0]  atten_mdb         = frame_205b_i[1359:1328]; // Offset 35..38
    wire signed [31:0] freq_mhz    = frame_205b_i[1327:1296]; // Offset 39..42
    wire [63:0]  ptp_offset_ns     = frame_205b_i[1295:1232]; // Offset 43..50

    // W_post (Bytes 119..204 -> Bits 687..0)
    wire [63:0]  w_post_seq_c      = frame_205b_i[687:624];   // Offset 119..126
    wire [255:0] w_post_pre_sha256 = frame_205b_i[623:368];   // Offset 127..158
    wire [255:0] w_post_exec_dig   = frame_205b_i[367:112];   // Offset 159..190
    wire [31:0]  adc_delta_ns      = frame_205b_i[111:80];    // Offset 191..194
    wire [31:0]  shunt_ua          = frame_205b_i[79:48];     // Offset 195..198
    wire [15:0]  w_post_gate_code  = frame_205b_i[47:32];     // Offset 199..200

    // -------------------------------------------------------------------------
    // 2. Cryptographic TOCTOU & Physical Invariant Comparators
    // -------------------------------------------------------------------------
    wire toctou_match = (w_pre_seq_c == w_post_seq_c) &&
                        (w_post_pre_sha256 == computed_w_pre_sha_i) &&
                        (w_post_exec_dig   == expected_post_exec_i);

    wire kirchhoff_exact_zero = (delta_r_num == 64'sd0) && (delta_r_den == 64'sd1);
    wire bft_quorum_ok        = (w_pre_valid_sigs >= ((w_pre_fault_f << 1) + 8'd1));
    wire otdr_kill            = (otdr_step_loss_mdb_i >= KILL_OTDR_STEP_MDB);
    wire otdr_hold            = (atten_mdb > MAX_OTDR_ATTEN_MDB) ||
                                (otdr_step_loss_mdb_i > MAX_OTDR_STEP_MDB);
    wire vsg_rocof_kill       = (rocof_abs_mhz_s_i > MAX_ROCOF_MHZ_S);
    wire vsg_freq_hold        = (freq_mhz < MIN_FREQ_MHZ) || (freq_mhz > MAX_FREQ_MHZ);
    wire ptp_sync_hold        = (ptp_offset_ns > MAX_PTP_OFFSET_NS);
    wire registry_b_l3_ok     = (adc_delta_ns > 32'd0) && (shunt_ua >= MIN_SHUNT_UA) &&
                                (w_post_gate_code == 16'h0001);

    // -------------------------------------------------------------------------
    // 3. Monotonic Sequence Tracker & Fail-Closed Latch (0.00 V DC)
    // -------------------------------------------------------------------------
    logic [63:0] hw_seq_q;
    logic        kill_latched_q;

    always_ff @(posedge clk_sys_i or negedge rst_n_i) begin
        if (!rst_n_i) begin
            hw_seq_q          <= 64'd0;
            kill_latched_q    <= 1'b0;
            gate_state_o      <= STATE_HOLD;
            breaker_actuate_o <= 1'b0; // Clamped at 0.00 V DC
        end else if (frame_valid_i) begin
            // Permanent KILL trap on TOCTOU mutation, Kirchhoff violation, fiber cut, or RoCoF collapse
            if (kill_latched_q ||
                (w_pre_magic != EXPECTED_MAGIC) ||
                !crc32_valid_i ||
                (w_pre_seq_c <= hw_seq_q) ||
                !toctou_match ||
                !kirchhoff_exact_zero ||
                otdr_kill ||
                vsg_rocof_kill ||
                (w_post_gate_code == 16'h00FF)) begin
                kill_latched_q    <= 1'b1;
                gate_state_o      <= STATE_KILL;
                breaker_actuate_o <= 1'b0;
            end
            // HOLD on OTDR bend intrusion, PTP drift, VSG frequency excursion, BFT quorum, or Reg B
            else if (!bft_quorum_ok || otdr_hold || vsg_freq_hold || ptp_sync_hold || !registry_b_l3_ok) begin
                hw_seq_q          <= w_pre_seq_c;
                gate_state_o      <= STATE_HOLD;
                breaker_actuate_o <= 1'b0; // Clamped at 0.00 V DC
            end
            // Witnessed L3 Consequence Admitted
            else begin
                hw_seq_q          <= w_pre_seq_c;
                gate_state_o      <= STATE_OPEN;
                breaker_actuate_o <= 1'b1;
            end
        end
    end

endmodule
`default_nettype wire
