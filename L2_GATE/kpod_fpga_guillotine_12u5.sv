// ============================================================================
// MODULE: kpod_fpga_guillotine_12u5.sv
// ARCHITECTURE: KY Rosetta Codex v0.2 + Fase-speil v0.1 + U-GKO-CS v1.1 (L0 RTL)
// CLOCK: 80 kHz Frisch-pulse (dt = 12.5 us)
// LAW: ○ -> ◇ -> □ -> ⟲ (XOR) -> ⬡ (Pi_K) -> # (Witness) -> ! (OR-Fuse) -> ◉ -> ▶ (5000 mV) / ✕ (0 mV)
// ============================================================================

module kpod_fpga_guillotine_12u5 #(
    parameter logic [63:0] RFM_XOR_MASK = 64'hA55A_F00F_CC33_AA55
) (
    input  logic        clk_80khz,              // 12.5 us Frisch-pulse clock
    input  logic        rst_n,                  // Active-low hardware reset
    input  logic        privileged_key_clear,   // Physical key reset for sticky trap

    // D0 / D1 Candidate & RFM XOR Payload
    input  logic        direct_raw_jump_attempt,// Forbidden ○ -> ◉ attempt
    input  logic [7:0]  heartbeat_byte,         // Must be 8'hFF
    input  logic [63:0] payload_in,             // Telemetry / control word
    input  logic [63:0] proposed_fuse_mask,     // Proposed OR-fuse state F_{n+1}

    // POD-MYCELIN Fixed-Point Telemetry (mW, m°C, permille, mg)
    input  logic [31:0] p_myc_mw,               // [49500, 50500] mW (50.0 ± 0.5 W)
    input  logic [31:0] t_myc_mc,               // [24000, 28000] m°C (< 30000 m°C)
    input  logic [15:0] o2_permille,            // > 180 (18.0 %)
    input  logic [15:0] rq_milli,               // [850, 1050] (0.85 .. 1.05)
    input  logic [31:0] m_n_in_mg,              // >= 10000 mg (0.01 kg)

    // K-POD v1.2 Fixed-Point Telemetry (mV, permille, ppm)
    input  logic [15:0] v_cell_mv,              // [993, 1003] mV (0.998 V Modus B UOR)
    input  logic [15:0] eta_fe_permille,        // [891, 893] (89.2 % over [Fe7MoS9C])
    input  logic [15:0] o2_intrusion_ppm,       // Must be 0

    // P-POD & Trinity Lock Noether Charge (milli-units, mg)
    input  logic [15:0] s_struvite_milli,       // [1800, 3200] (1.8 .. 3.2)
    input  logic [31:0] delta_q_mg,             // |m_in - m_out| <= 1 mg (1e-6 kg)
    input  logic [15:0] spectral_rho_milli,     // < 1000 (rho(DF_Sigma) < 1.0)
    input  logic        witness_anchor_valid,   // SHA-256 WORM chain continuity (#)

    // Outputs (D2 Actuation & Audit)
    output logic [3:0]  ky_glyph_stage_out = 4'd0,     // 0=○, 1=◇, 2=□, 3=⟲, 4=⬡, 5=#, 6=!, 7=◉, 8=▶, 15=✕
    output logic [63:0] monotone_fuse_reg_out = 64'd0, // Monotone OR-fuse register F_n
    output logic        trap_latched_out = 1'b0,       // Sticky x_TRAP latch (RC-701 / KILL)
    output logic        interlock_relay_en_out = 1'b0, // 1 = CLOSED (OPEN), 0 = Guillotined (KILL)
    output logic [15:0] voltage_mv_out = 16'd0         // 5000 mV (5.00 V DC) or 0 mV (0.00 V DC)
);
    timeunit 1ns;
    timeprecision 1ps;

    // 1. D1 Reversible RFM/IKS XOR Involution Check: (m ^ k) ^ k == m
    logic [63:0] xor_encoded;
    logic [63:0] xor_roundtrip;
    logic        rfm_xor_ok;

    assign xor_encoded   = payload_in ^ RFM_XOR_MASK;
    assign xor_roundtrip = xor_encoded ^ RFM_XOR_MASK;
    assign rfm_xor_ok    = (payload_in != 64'd0) && (xor_roundtrip == payload_in);

    // 2. Viability Projection Pi_K (Admissible Set A)
    logic mycelin_ok;
    logic kpod_ok;
    logic ppod_ok;
    logic trinity_ok;
    logic viability_ok;

    assign mycelin_ok = (p_myc_mw >= 32'd49500) && (p_myc_mw <= 32'd50500) &&
                        (t_myc_mc >= 32'd24000) && (t_myc_mc <= 32'd28000) &&
                        (o2_permille > 16'd180) &&
                        (rq_milli >= 16'd850)   && (rq_milli <= 16'd1050) &&
                        (m_n_in_mg >= 32'd10000);

    assign kpod_ok    = (heartbeat_byte == 8'hFF) &&
                        (v_cell_mv >= 16'd993)    && (v_cell_mv <= 16'd1003) &&
                        (eta_fe_permille >= 16'd891) && (eta_fe_permille <= 16'd893) &&
                        (o2_intrusion_ppm == 16'd0);

    assign ppod_ok    = (s_struvite_milli >= 16'd1800) && (s_struvite_milli <= 16'd3200);

    assign trinity_ok = (delta_q_mg <= 32'd1) &&
                        (spectral_rho_milli < 16'd1000) &&
                        witness_anchor_valid;

    assign viability_ok = mycelin_ok && kpod_ok && ppod_ok && trinity_ok;

    // 3. Monotone OR-Fuse Invariant: F_n subseteq F_{n+1} <=> (F_n & F_{n+1}) == F_n
    logic monotone_fuse_ok;
    assign monotone_fuse_ok = ((monotone_fuse_reg_out & proposed_fuse_mask) == monotone_fuse_reg_out);

    // 4. Sequential 80 kHz Guillotine State Machine
    always_ff @(posedge clk_80khz or negedge rst_n) begin
        if (!rst_n) begin
            ky_glyph_stage_out     <= 4'd0;
            monotone_fuse_reg_out  <= 64'd0;
            trap_latched_out       <= 1'b0;
            interlock_relay_en_out <= 1'b0;
            voltage_mv_out         <= 16'd0;
        end else if (privileged_key_clear) begin
            ky_glyph_stage_out     <= 4'd0;
            trap_latched_out       <= 1'b0;
            interlock_relay_en_out <= 1'b0;
            voltage_mv_out         <= 16'd0;
        end else if (trap_latched_out || direct_raw_jump_attempt || !rfm_xor_ok || !viability_ok || !monotone_fuse_ok) begin
            // Fail-Closed Guillotine Cut (✕ / 0.00 V DC) within single 12.5 us cycle
            ky_glyph_stage_out     <= 4'd15; // ✕ (KILL)
            trap_latched_out       <= 1'b1;
            interlock_relay_en_out <= 1'b0;
            voltage_mv_out         <= 16'd0;
        end else begin
            // Complete passage: ○ -> ◇ -> □ -> ⟲ -> ⬡ -> # -> ! -> ◉ -> ▶ (5000 mV)
            ky_glyph_stage_out     <= 4'd8;  // ▶ (OPEN)
            monotone_fuse_reg_out  <= monotone_fuse_reg_out | proposed_fuse_mask;
            trap_latched_out       <= 1'b0;
            interlock_relay_en_out <= 1'b1;
            voltage_mv_out         <= 16'd5000;
        end
    end

endmodule
