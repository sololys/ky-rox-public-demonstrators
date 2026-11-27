// =============================================================================
// Physical UPduino v3.1 (Lattice iCE40UP5K-SG48) Top Wrapper for NLK-Enigma
// Module   : nlk_enigma_upduino_top
// Frame    : 256-bit MOSI command / 64-bit MISO post-eval telemetry digest
// Bit Map (zero overlap between coordinates and authorization):
//   [2:0]     cmd_mode (0=NOP/poll, 1=L01_reset, 2=board_load, 3=eval_step,
//                       4=board_eval, 5=lifo_pop)
//   [6:3]     mode subfields (L01 flags / slot_idx+present / expected_steps / tamper)
//   [21:7]    board_q0_flat (15b — dedicated coordinate field)
//   [36:22]   ring_flat (15b)
//   [37]      plug_en
//   [42:38]   x_in (5b)
//   [47:43]   y_cand (5b)
//   [62:48]   q_before_flat (15b)
//   [77:63]   q_prop_flat (15b)
//   [109:78]  seq_num (32b)
//   [110]     meas_en
//   [111]     meas_stale
//   [143:112] e_err (32b)
//   [175:144] sigma_ref (32b)
//   [207:176] bits_erased (32b)
//   [249:208] q_diss_rj[41:0] (42b)
//   [250]     l2_profile (dedicated authorization bit)
//   [251]     hw_verified (dedicated hardware attestation bit)
//   [252]     witness_ext (gated in hardware with SG48 Pin 28 w_ext_hw_pin)
//   [253]     hash_valid
//   [254]     wal_ready
//   [255]     crash_inject
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module nlk_enigma_upduino_top (
    input  wire       clk_12m,
    input  wire       rst_l01_btn_n,
    input  wire       spi_cs_n,
    input  wire       spi_sck,
    input  wire       spi_mosi,
    output wire       spi_miso,
    input  wire       w_ext_hw_pin,

    output wire       actuator_rail_en,
    output wire       killed_latch_pin,
    output wire [1:0] port_pins,
    output wire [2:0] reason_low_pins,
    output wire       monitor_coupled_pin,
    output wire       led_g_n,
    output wire       led_b_n,
    output wire       led_r_n
);

    localparam integer SPI_BITS  = 256;
    localparam integer MISO_BITS = 64;

    reg [2:0] sck_sync;
    reg [2:0] cs_sync;
    reg [1:0] mosi_sync;
    reg [1:0] rst_sync;
    reg [1:0] wext_sync;

    always @(posedge clk_12m) begin
        sck_sync  <= {sck_sync[1:0],  spi_sck};
        cs_sync   <= {cs_sync[1:0],   spi_cs_n};
        mosi_sync <= {mosi_sync[0],   spi_mosi};
        rst_sync  <= {rst_sync[0],    rst_l01_btn_n};
        wext_sync <= {wext_sync[0],   w_ext_hw_pin};
    end

    wire sck_rise        = (sck_sync[2:1] == 2'b01);
    wire cs_active       = ~cs_sync[1];
    wire cs_active_shift = cs_active & sck_rise;
    wire cs_rise         = (cs_sync[2:1] == 2'b01);
    wire rst_n           = rst_sync[1];

    reg [SPI_BITS-1:0]  spi_buf;
    reg [MISO_BITS-1:0] miso_shift;
    reg                 cmd_strobe;

    wire        busy_out;
    wire        eval_done_out;
    wire [1:0]  port_out;
    wire [3:0]  reason_out;
    wire        kill_latched_out;
    wire        outcome_unknown_out;
    wire        monitor_coupled_out;
    wire        actuator_v_en_out;
    wire [7:0]  status_byte_out;
    wire [4:0]  y_out;
    wire [14:0] q_auth_flat_out;
    wire [3:0]  lifo_depth_out;
    wire [31:0] seq_prev_out;
    wire [31:0] reset_epoch_out;
    wire [63:0] cycle_out;

    wire [63:0] telemetry_digest = cycle_out ^ {
        status_byte_out, reason_out, lifo_depth_out,
        1'b0, q_auth_flat_out,
        (seq_prev_out ^ reset_epoch_out ^ {27'd0, y_out})
    };

    wire [2:0] cmd_mode = spi_buf[2:0];

    always @(posedge clk_12m) begin
        if (!rst_n) begin
            spi_buf    <= {SPI_BITS{1'b0}};
            miso_shift <= 64'd0;
            cmd_strobe <= 1'b0;
        end else begin
            if (cs_active_shift) begin
                spi_buf <= {spi_buf[SPI_BITS-2:0], mosi_sync[1]};
            end
            cmd_strobe <= cs_rise && (cmd_mode != 3'd0);
            if (!cs_active) begin
                miso_shift <= telemetry_digest;
            end else if (cs_active_shift) begin
                miso_shift <= {miso_shift[MISO_BITS-2:0], miso_shift[MISO_BITS-1]};
            end
        end
    end

    assign spi_miso = miso_shift[MISO_BITS-1];

    nlk_enigma_sluice u_core (
        .clk                  (clk_12m),
        .rst_n                (rst_n),
        .l01_reset_strobe     (cmd_strobe && (cmd_mode == 3'd1)),
        .l01_witness_ok       (spi_buf[3] & wext_sync[1]),
        .selftest_ok          (spi_buf[4]),
        .board_load_en        (cmd_strobe && (cmd_mode == 3'd2)),
        .board_slot_idx       (spi_buf[5:3]),
        .board_slot_present   (spi_buf[6]),
        .eval_step_en         (cmd_strobe && (cmd_mode == 3'd3)),
        .board_eval_en        (cmd_strobe && (cmd_mode == 3'd4)),
        .board_expected_steps (spi_buf[6:3]),
        .board_q0_flat        (spi_buf[21:7]),
        .lifo_pop_en          (cmd_strobe && (cmd_mode == 3'd5)),
        .lifo_tamper_inject   (spi_buf[3]),
        .ring_flat            (spi_buf[36:22]),
        .plug_en              (spi_buf[37]),
        .x_in                 (spi_buf[42:38]),
        .y_cand               (spi_buf[47:43]),
        .q_before_flat        (spi_buf[62:48]),
        .q_prop_flat          (spi_buf[77:63]),
        .seq_num              (spi_buf[109:78]),
        .meas_en              (spi_buf[110]),
        .meas_stale           (spi_buf[111]),
        .e_err                (spi_buf[143:112]),
        .sigma_ref            (spi_buf[175:144]),
        .bits_erased          (spi_buf[207:176]),
        .q_diss_rj            ({22'd0, spi_buf[249:208]}),
        .l2_profile           (spi_buf[250]),
        .hw_verified          (spi_buf[251]),
        .witness_ext          (spi_buf[252] & wext_sync[1]),
        .hash_valid           (spi_buf[253]),
        .wal_ready            (spi_buf[254]),
        .crash_inject         (spi_buf[255]),
        .busy_out             (busy_out),
        .eval_done_out        (eval_done_out),
        .port_out             (port_out),
        .reason_out           (reason_out),
        .kill_latched_out     (kill_latched_out),
        .outcome_unknown_out  (outcome_unknown_out),
        .monitor_coupled_out  (monitor_coupled_out),
        .actuator_v_en_out    (actuator_v_en_out),
        .status_byte_out      (status_byte_out),
        .y_out                (y_out),
        .q_auth_flat_out      (q_auth_flat_out),
        .lifo_depth_out       (lifo_depth_out),
        .seq_prev_out         (seq_prev_out),
        .reset_epoch_out      (reset_epoch_out),
        .cycle_out            (cycle_out)
    );

    assign actuator_rail_en    = actuator_v_en_out;
    assign killed_latch_pin    = kill_latched_out;
    assign port_pins           = port_out;
    assign reason_low_pins     = reason_out[2:0] ^ {outcome_unknown_out, busy_out, eval_done_out};
    assign monitor_coupled_pin = monitor_coupled_out;

    assign led_g_n = ~(port_out == 2'd1);
    assign led_b_n = ~(port_out == 2'd0);
    assign led_r_n = ~kill_latched_out;

endmodule
`default_nettype wire
