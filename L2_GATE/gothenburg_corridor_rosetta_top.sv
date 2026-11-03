// =============================================================================
// SOLOLYS // GOTHENBURG CORRIDOR & ROSETTA D3 (208B <-> 205B) MASTER TOP MODULE
// Standard: IEEE 1800-2012 | State Anchor: 32'hABCDEF00 | Release: v1.5.0-MASTER
// Unifies:
//   1. Rosetta D3 (208B / 1664-bit) Envelope & Registry A/B Header Verifier
//   2. SPEC-213: fpga_capsule_frame_205b_decoder (W_pre 119B + W_post 86B Link)
//   3. SPEC-415: spec415_kpod_cdc_gate (-240m Benthic K-POD 5x CDC & 145dB SPL)
//   4. SPEC-416: spec416_infranett_witness_gate (Infranett 1640-bit W_pre->W_post)
// Default State: FAIL-CLOSED HOLD (0.00 V DC on all physical outputs).
// =============================================================================
`default_nettype none

module gothenburg_corridor_rosetta_top #(
    parameter logic [31:0] EXPECTED_MAGIC   = 32'hABCD_EF00,
    parameter logic [15:0] EXPECTED_VERSION = 16'h0105,
    parameter logic [31:0] MIN_SHUNT_UA     = 32'd500
) (
    input  wire          clk_sys_i,
    input  wire          rst_n_i,
    input  wire          frame_valid_i,

    // -------------------------------------------------------------------------
    // 1. D3: 208-Byte (1664-bit) Rosetta v1.5 Envelope Input (>4sHBBQ32s32s32s32s64s)
    // -------------------------------------------------------------------------
    input  wire [1663:0] rosetta_208b_i,
    input  wire [255:0]  expected_ky_glyph_sha_i,
    input  wire [255:0]  expected_ky_ascii_sha_i,
    input  wire          ed25519_sig_valid_i,     // Hardware/Core RFC 8032 Ed25519 verify strobe

    // -------------------------------------------------------------------------
    // 2. SPEC-213: 205-Byte Little-Endian Capsule Input for fpga_capsule_frame_205b_decoder
    // -------------------------------------------------------------------------
    input  wire [951:0]  spec213_w_pre_le_i,      // 119 bytes LE
    input  wire [687:0]  spec213_w_post_le_i,     //  86 bytes LE

    // -------------------------------------------------------------------------
    // 3. SPEC-415: -240m Benthic K-POD Sensor & CDC Inputs
    // -------------------------------------------------------------------------
    input  wire [4:0]    kpod_cdc_async_valid_i,
    input  wire [15:0]   kpod_acoustic_spl_dbx_i,
    input  wire [15:0]   kpod_range_532nm_mm_i,
    input  wire [15:0]   kpod_range_uwb_mm_i,

    // -------------------------------------------------------------------------
    // 4. SPEC-416: Infranett 1640-bit (205B) Big-Endian Capsule & Grid/OTDR Inputs
    // -------------------------------------------------------------------------
    input  wire [1639:0] infranett_frame_205b_i,
    input  wire [255:0]  infranett_comp_w_pre_sha_i,
    input  wire [255:0]  infranett_exp_post_exec_i,
    input  wire [15:0]   infranett_otdr_step_mdb_i,
    input  wire [15:0]   infranett_rocof_mhz_s_i,
    input  wire          infranett_crc32_valid_i,

    // -------------------------------------------------------------------------
    // 5. Master Physical Consequence & Telemetry Outputs
    // -------------------------------------------------------------------------
    output logic [1:0]   top_gate_state_o,        // 2'b00=HOLD, 2'b01=OPEN, 2'b11=KILL
    output wire  [1:0]   spec415_state_o,
    output wire  [1:0]   spec416_state_o,
    output wire  [7:0]   spec213_verdict_o,
    output logic         kpod_actuate_pin_o,      // 0 = 0.00 V DC
    output logic         infranett_breaker_pin_o, // 0 = 0.00 V DC
    output logic         master_5v_rail_en_o      // 0 = 0.00 V DC, 1 = L3 Witnessed 5.00 V DC
);

    localparam logic [1:0] STATE_HOLD = 2'b00;
    localparam logic [1:0] STATE_OPEN = 2'b01;
    localparam logic [1:0] STATE_KILL = 2'b11;

    // =========================================================================
    // A. ROSETTA D3 (208B / 1664-BIT) BIG-ENDIAN FIELD EXTRACTION
    // =========================================================================
    wire [31:0]  rosetta_magic      = rosetta_208b_i[1663:1632]; // Bytes 0..3
    wire [15:0]  rosetta_version    = rosetta_208b_i[1631:1616]; // Bytes 4..5
    wire [7:0]   rosetta_reg_a      = rosetta_208b_i[1615:1608]; // Byte  6
    wire [7:0]   rosetta_reg_b      = rosetta_208b_i[1607:1600]; // Byte  7
    wire [63:0]  rosetta_seq        = rosetta_208b_i[1599:1536]; // Bytes 8..15
    wire [255:0] rosetta_glyph_sha  = rosetta_208b_i[1279:1024]; // Bytes 48..79
    wire [255:0] rosetta_ascii_sha  = rosetta_208b_i[1023:768];  // Bytes 80..111

    // Extract sequence & Registry B telemetry from SPEC-416 205B frame
    wire [63:0]  infra_seq_c        = infranett_frame_205b_i[1607:1544];
    wire [31:0]  infra_adc_delta_ns = infranett_frame_205b_i[111:80];
    wire [31:0]  infra_shunt_ua     = infranett_frame_205b_i[79:48];

    wire adc_time_valid = (infra_adc_delta_ns > 32'd0);
    wire [15:0] shunt_ua_16b = (infra_shunt_ua > 32'hFFFF) ? 16'hFFFF : infra_shunt_ua[15:0];

    // Registry A (D3) Cryptographic & Bijection Check
    wire rosetta_reg_a_ok = (rosetta_magic     == EXPECTED_MAGIC)          &&
                            (rosetta_version   == EXPECTED_VERSION)        &&
                            (rosetta_reg_a     == 8'h01)                   &&
                            (rosetta_glyph_sha == expected_ky_glyph_sha_i) &&
                            (rosetta_ascii_sha == expected_ky_ascii_sha_i) &&
                            (rosetta_seq       == infra_seq_c)             &&
                            ed25519_sig_valid_i;

    // Registry B (D3 -> L3) Envelope Flag Check
    wire rosetta_reg_b_l3_flag = (rosetta_reg_b == 8'h01);

    // =========================================================================
    // B. SUBSYSTEM 1: SPEC-213 205B CAPSULE DECODER (fpga_capsule_frame_205b_decoder)
    // =========================================================================
    wire [63:0] s213_pre_seq;
    wire [63:0] s213_post_seq;
    wire [7:0]  s213_pre_decision;
    wire [15:0] s213_pre_reason;
    wire [255:0] s213_pre_hash;
    wire [255:0] s213_post_hash;
    wire [7:0]  s213_hpis_latch;
    wire [7:0]  s213_final_status;
    wire        s213_linkage_ok;
    wire        s213_v_gate_5v;

    fpga_capsule_frame_205b_decoder u_capsule_205b_decoder (
        .clk                  (clk_sys_i),
        .rst_n                (rst_n_i),
        .frame_valid          (frame_valid_i),
        .w_pre_frame_le       (spec213_w_pre_le_i),
        .w_post_frame_le      (spec213_w_post_le_i),
        .pre_seq_id           (s213_pre_seq),
        .post_seq_id          (s213_post_seq),
        .pre_gate_decision    (s213_pre_decision),
        .pre_reason_code      (s213_pre_reason),
        .pre_w_pre_hash       (s213_pre_hash),
        .post_w_pre_hash      (s213_post_hash),
        .post_hpis_latch_byte (s213_hpis_latch),
        .post_final_status    (s213_final_status),
        .capsule_linkage_ok   (s213_linkage_ok),
        .v_gate_out_5v        (s213_v_gate_5v),
        .rtl_verdict_code     (spec213_verdict_o)
    );

    // =========================================================================
    // C. SUBSYSTEM 2: SPEC-415 -240m BENTHIC K-POD 5-CDC GATE
    // =========================================================================
    wire kpod_raw_pin;

    spec415_kpod_cdc_gate u_spec415_kpod_gate (
        .clk_sys_i          (clk_sys_i),
        .rst_n_i            (rst_n_i),
        .cdc_async_valid_i  (kpod_cdc_async_valid_i),
        .frame_magic_i      (rosetta_magic),
        .capsule_crc_ok_i   (infranett_crc32_valid_i && rosetta_reg_a_ok),
        .acoustic_spl_dbx_i (kpod_acoustic_spl_dbx_i),
        .range_532nm_mm_i   (kpod_range_532nm_mm_i),
        .range_uwb_mm_i     (kpod_range_uwb_mm_i),
        .adc_time_valid_i   (adc_time_valid && rosetta_reg_b_l3_flag),
        .shunt_current_ua_i (shunt_ua_16b),
        .gate_state_o       (spec415_state_o),
        .actuate_pin_o      (kpod_raw_pin)
    );

    // =========================================================================
    // D. SUBSYSTEM 3: SPEC-416 INFRANETT 1640-BIT CAUSAL WITNESS GATE
    // =========================================================================
    wire infranett_raw_pin;

    spec416_infranett_witness_gate u_spec416_infranett_gate (
        .clk_sys_i            (clk_sys_i),
        .rst_n_i              (rst_n_i),
        .frame_valid_i        (frame_valid_i),
        .frame_205b_i         (infranett_frame_205b_i),
        .computed_w_pre_sha_i (infranett_comp_w_pre_sha_i),
        .expected_post_exec_i (infranett_exp_post_exec_i),
        .otdr_step_loss_mdb_i (infranett_otdr_step_mdb_i),
        .rocof_abs_mhz_s_i    (infranett_rocof_mhz_s_i),
        .crc32_valid_i        (infranett_crc32_valid_i && rosetta_reg_a_ok),
        .gate_state_o         (spec416_state_o),
        .breaker_actuate_o    (infranett_raw_pin)
    );

    // =========================================================================
    // E. MASTER FAIL-CLOSED CONJUNCTION & PERMANENT KILL TRAP
    // =========================================================================
    logic master_kill_latched_q;

    wire any_subsystem_kill = !rosetta_reg_a_ok             ||
                              (spec213_verdict_o == 8'hFF)  ||
                              (spec415_state_o == STATE_KILL) ||
                              (spec416_state_o == STATE_KILL);

    wire all_subsystems_open = rosetta_reg_a_ok              &&
                               rosetta_reg_b_l3_flag         &&
                               s213_linkage_ok               &&
                               s213_v_gate_5v                &&
                               (spec415_state_o == STATE_OPEN) &&
                               (spec416_state_o == STATE_OPEN) &&
                               kpod_raw_pin                  &&
                               infranett_raw_pin;

    always_ff @(posedge clk_sys_i or negedge rst_n_i) begin
        if (!rst_n_i) begin
            master_kill_latched_q   <= 1'b0;
            top_gate_state_o        <= STATE_HOLD;
            kpod_actuate_pin_o      <= 1'b0;
            infranett_breaker_pin_o <= 1'b0;
            master_5v_rail_en_o     <= 1'b0;
        end else begin
            if (master_kill_latched_q || (frame_valid_i && !rosetta_reg_a_ok) ||
                (spec213_verdict_o == 8'hFF) ||
                (spec415_state_o == STATE_KILL) ||
                (spec416_state_o == STATE_KILL)) begin
                master_kill_latched_q   <= 1'b1;
                top_gate_state_o        <= STATE_KILL;
                kpod_actuate_pin_o      <= 1'b0;
                infranett_breaker_pin_o <= 1'b0;
                master_5v_rail_en_o     <= 1'b0;
            end else if (all_subsystems_open) begin
                top_gate_state_o        <= STATE_OPEN;
                kpod_actuate_pin_o      <= 1'b1;
                infranett_breaker_pin_o <= 1'b1;
                master_5v_rail_en_o     <= 1'b1;
            end else begin
                top_gate_state_o        <= STATE_HOLD;
                kpod_actuate_pin_o      <= 1'b0;
                infranett_breaker_pin_o <= 1'b0;
                master_5v_rail_en_o     <= 1'b0;
            end
        end
    end

endmodule
`default_nettype wire
