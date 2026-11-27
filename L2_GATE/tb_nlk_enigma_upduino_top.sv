// =============================================================================
// Dedicated SPI Top-Wrapper Testbench for nlk_enigma_upduino_top (UPduino v3.1)
// Verifies:
//   1. Non-overlapping SPI bitfields: q_auth == 0 AND q_auth == 1188 = (0,4,22)
//      both reach PORT_OPEN (Pin 31 actuator_rail_en = 1, 3.30 V, GREEN LED).
//   2. Zero-lag MISO telemetry: polling right after 18/22/130-cycle execution
//      returns the exact post-evaluation 64-bit telemetry_digest.
//   3. 18-cycle hardware LIFO rewind, physical SG48 Pin 28 (w_ext_hw_pin) cut,
//      and 1-bit LIFO tamper sticky KILL + L01 recovery.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module tb_nlk_enigma_upduino_top;
    reg        clk_12m = 1'b0;
    reg        rst_l01_btn_n = 1'b0;
    reg        spi_cs_n = 1'b1;
    reg        spi_sck = 1'b0;
    reg        spi_mosi = 1'b0;
    reg        w_ext_hw_pin = 1'b1;

    wire       spi_miso;
    wire       actuator_rail_en;
    wire       killed_latch_pin;
    wire [1:0] port_pins;
    wire [2:0] reason_low_pins;
    wire       monitor_coupled_pin;
    wire       led_g_n;
    wire       led_b_n;
    wire       led_r_n;

    nlk_enigma_upduino_top dut (
        .clk_12m             (clk_12m),
        .rst_l01_btn_n       (rst_l01_btn_n),
        .spi_cs_n            (spi_cs_n),
        .spi_sck             (spi_sck),
        .spi_mosi            (spi_mosi),
        .spi_miso            (spi_miso),
        .w_ext_hw_pin        (w_ext_hw_pin),
        .actuator_rail_en    (actuator_rail_en),
        .killed_latch_pin    (killed_latch_pin),
        .port_pins           (port_pins),
        .reason_low_pins     (reason_low_pins),
        .monitor_coupled_pin (monitor_coupled_pin),
        .led_g_n             (led_g_n),
        .led_b_n             (led_b_n),
        .led_r_n             (led_r_n)
    );

    always #5 clk_12m = ~clk_12m;

    reg [63:0] last_miso_word;

    task send_spi_256(input [255:0] tx_frame, input integer settle_cycles);
        integer bit_idx;
        reg [63:0] rx_shift;
        begin
            rx_shift = 64'd0;
            spi_sck  = 1'b0;
            spi_cs_n = 1'b0;
            repeat (4) @(posedge clk_12m);
            for (bit_idx = 255; bit_idx >= 0; bit_idx = bit_idx - 1) begin
                spi_mosi = tx_frame[bit_idx];
                spi_sck  = 1'b0;
                repeat (4) @(posedge clk_12m);
                if (bit_idx >= 192) begin
                    rx_shift = {rx_shift[62:0], spi_miso};
                end
                spi_sck  = 1'b1;
                repeat (4) @(posedge clk_12m);
            end
            spi_sck  = 1'b0;
            repeat (4) @(posedge clk_12m);
            spi_cs_n = 1'b1;
            last_miso_word = rx_shift;
            repeat (settle_cycles) @(posedge clk_12m);
        end
    endtask

    task spi_nop_poll;
        begin
            send_spi_256(256'd0, 8);
        end
    endtask

    task spi_board_load(
        input [2:0]  slot_idx,
        input        present,
        input [4:0]  bx,
        input [4:0]  by,
        input [14:0] bq
    );
        reg [255:0] f;
        begin
            f          = 256'd0;
            f[2:0]     = 3'd2;
            f[5:3]     = slot_idx;
            f[6]       = present;
            f[42:38]   = bx;
            f[47:43]   = by;
            f[77:63]   = bq;
            send_spi_256(f, 12);
        end
    endtask

    task spi_board_eval(
        input [14:0] b_ring,
        input [14:0] b_q0,
        input [3:0]  b_steps,
        input [31:0] b_seq,
        input [2:0]  auth_bits // {witness_ext, hw_verified, l2_profile} -> [252:250]
    );
        reg [255:0] f;
        begin
            f            = 256'd0;
            f[2:0]       = 3'd4;
            f[6:3]       = b_steps;
            f[21:7]      = b_q0;
            f[36:22]     = b_ring;
            f[37]        = 1'b1;
            f[109:78]    = b_seq;
            f[252:250]   = auth_bits;
            f[253]       = 1'b1;
            f[254]       = 1'b1;
            send_spi_256(f, 160);
        end
    endtask

    task spi_eval_step(
        input [14:0] s_ring,
        input [4:0]  sx,
        input [4:0]  sy,
        input [14:0] sq_bef,
        input [14:0] sq_prop,
        input [31:0] s_seq
    );
        reg [255:0] f;
        begin
            f            = 256'd0;
            f[2:0]       = 3'd3;
            f[36:22]     = s_ring;
            f[37]        = 1'b1;
            f[42:38]     = sx;
            f[47:43]     = sy;
            f[62:48]     = sq_bef;
            f[77:63]     = sq_prop;
            f[109:78]    = s_seq;
            f[207:176]   = 32'd1;
            f[249:208]   = 42'd2652306;
            f[252:250]   = 3'b111;
            f[253]       = 1'b1;
            f[254]       = 1'b1;
            send_spi_256(f, 40);
        end
    endtask

    task spi_lifo_pop(input tamper_bit);
        reg [255:0] f;
        begin
            f        = 256'd0;
            f[2:0]   = 3'd5;
            f[3]     = tamper_bit;
            f[36:22] = 15'd3446;
            f[37]    = 1'b1;
            f[253]   = 1'b1;
            f[254]   = 1'b1;
            send_spi_256(f, 35);
        end
    endtask

    task spi_l01_reset;
        reg [255:0] f;
        begin
            f      = 256'd0;
            f[2:0] = 3'd1;
            f[3]   = 1'b1;
            f[4]   = 1'b1;
            send_spi_256(f, 12);
        end
    endtask

    reg [63:0] expected_digest;

    initial begin
        rst_l01_btn_n = 1'b0;
        repeat (8) @(posedge clk_12m);
        rst_l01_btn_n = 1'b1;
        repeat (8) @(posedge clk_12m);

        // 1. Power-on rest state: HOLD (0.00 V DC on Pin 31, BLUE LED active)
        if (port_pins !== 2'd0 || actuator_rail_en !== 1'b0 || killed_latch_pin !== 1'b0 || led_b_n !== 1'b0) begin
            $fatal(1, "FAIL T0: Expected power-on HOLD (0V, BLUE LED)");
        end

        // 2. Coordinate Board OPEN from q_auth == 0 (verifies zero collision with [252:250] = 3'b111!)
        spi_board_load(3'd0, 1'b1, 5'd6, 5'd19, 15'd1);
        spi_board_eval(15'd3446, 15'd0, 4'd1, 32'd1, 3'b111);
        if (port_pins !== 2'd1 || actuator_rail_en !== 1'b1 || killed_latch_pin !== 1'b0 ||
            led_g_n !== 1'b0 || dut.q_auth_flat_out !== 15'd1) begin
            $fatal(1, "FAIL T1: q_auth==0 board_eval failed OPEN (port=%0d act=%0d kill=%0d)",
                   port_pins, actuator_rail_en, killed_latch_pin);
        end
        expected_digest = dut.telemetry_digest;
        spi_nop_poll();
        if (last_miso_word !== expected_digest) begin
            $fatal(1, "FAIL T1_MISO: Stale MISO digest (got 0x%016h, expected 0x%016h)",
                   last_miso_word, expected_digest);
        end

        // 3. Advance rotor state via verified SPI board leaps to q_auth == 1188 = (0, 4, 22)
        spi_board_load(3'd0, 1'b1, 5'd3, 5'd16, 15'd2);
        spi_board_load(3'd1, 1'b1, 5'd10, 5'd11, 15'd3);
        spi_board_load(3'd2, 1'b1, 5'd17, 5'd21, 15'd4);
        spi_board_load(3'd3, 1'b1, 5'd24, 5'd4, 15'd5);
        spi_board_load(3'd4, 1'b1, 5'd5, 5'd6, 15'd6);
        spi_board_load(3'd5, 1'b1, 5'd12, 5'd2, 15'd7);
        spi_board_load(3'd6, 1'b1, 5'd19, 5'd14, 15'd8);
        spi_board_load(3'd7, 1'b1, 5'd0, 5'd3, 15'd9);
        spi_board_eval(15'd3446, 15'd1, 4'd8, 32'd2, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd7, 5'd6, 15'd10);
        spi_board_load(3'd1, 1'b1, 5'd14, 5'd13, 15'd11);
        spi_board_load(3'd2, 1'b1, 5'd21, 5'd23, 15'd12);
        spi_board_load(3'd3, 1'b1, 5'd2, 5'd17, 15'd13);
        spi_board_load(3'd4, 1'b1, 5'd9, 5'd24, 15'd14);
        spi_board_load(3'd5, 1'b1, 5'd16, 5'd21, 15'd15);
        spi_board_load(3'd6, 1'b1, 5'd23, 5'd13, 15'd16);
        spi_board_load(3'd7, 1'b1, 5'd4, 5'd5, 15'd17);
        spi_board_eval(15'd3446, 15'd9, 4'd8, 32'd3, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd11, 5'd20, 15'd18);
        spi_board_load(3'd1, 1'b1, 5'd18, 5'd22, 15'd19);
        spi_board_load(3'd2, 1'b1, 5'd25, 5'd3, 15'd20);
        spi_board_load(3'd3, 1'b1, 5'd6, 5'd24, 15'd21);
        spi_board_load(3'd4, 1'b1, 5'd13, 5'd15, 15'd54);
        spi_board_load(3'd5, 1'b1, 5'd20, 5'd13, 15'd55);
        spi_board_load(3'd6, 1'b1, 5'd1, 5'd8, 15'd56);
        spi_board_load(3'd7, 1'b1, 5'd8, 5'd5, 15'd57);
        spi_board_eval(15'd3446, 15'd17, 4'd8, 32'd4, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd15, 5'd1, 15'd32);
        spi_board_load(3'd1, 1'b1, 5'd22, 5'd6, 15'd33);
        spi_board_load(3'd2, 1'b1, 5'd3, 5'd25, 15'd34);
        spi_board_load(3'd3, 1'b1, 5'd10, 5'd7, 15'd35);
        spi_board_load(3'd4, 1'b1, 5'd17, 5'd19, 15'd36);
        spi_board_load(3'd5, 1'b1, 5'd24, 5'd6, 15'd37);
        spi_board_load(3'd6, 1'b1, 5'd5, 5'd24, 15'd38);
        spi_board_load(3'd7, 1'b1, 5'd12, 5'd10, 15'd39);
        spi_board_eval(15'd3446, 15'd57, 4'd8, 32'd5, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd19, 5'd9, 15'd40);
        spi_board_load(3'd1, 1'b1, 5'd0, 5'd23, 15'd41);
        spi_board_load(3'd2, 1'b1, 5'd7, 5'd1, 15'd42);
        spi_board_load(3'd3, 1'b1, 5'd14, 5'd0, 15'd43);
        spi_board_load(3'd4, 1'b1, 5'd21, 5'd0, 15'd44);
        spi_board_load(3'd5, 1'b1, 5'd2, 5'd14, 15'd45);
        spi_board_load(3'd6, 1'b1, 5'd9, 5'd21, 15'd46);
        spi_board_load(3'd7, 1'b1, 5'd16, 5'd4, 15'd47);
        spi_board_eval(15'd3446, 15'd39, 4'd8, 32'd6, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd23, 5'd0, 15'd48);
        spi_board_load(3'd1, 1'b1, 5'd4, 5'd23, 15'd49);
        spi_board_load(3'd2, 1'b1, 5'd11, 5'd7, 15'd50);
        spi_board_load(3'd3, 1'b1, 5'd18, 5'd0, 15'd51);
        spi_board_load(3'd4, 1'b1, 5'd25, 5'd8, 15'd52);
        spi_board_load(3'd5, 1'b1, 5'd6, 5'd2, 15'd53);
        spi_board_load(3'd6, 1'b1, 5'd13, 5'd14, 15'd86);
        spi_board_load(3'd7, 1'b1, 5'd20, 5'd23, 15'd87);
        spi_board_eval(15'd3446, 15'd47, 4'd8, 32'd7, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd1, 5'd10, 15'd88);
        spi_board_load(3'd1, 1'b1, 5'd8, 5'd24, 15'd89);
        spi_board_load(3'd2, 1'b1, 5'd15, 5'd0, 15'd64);
        spi_board_load(3'd3, 1'b1, 5'd22, 5'd3, 15'd65);
        spi_board_load(3'd4, 1'b1, 5'd3, 5'd10, 15'd66);
        spi_board_load(3'd5, 1'b1, 5'd10, 5'd16, 15'd67);
        spi_board_load(3'd6, 1'b1, 5'd17, 5'd15, 15'd68);
        spi_board_load(3'd7, 1'b1, 5'd24, 5'd12, 15'd69);
        spi_board_eval(15'd3446, 15'd87, 4'd8, 32'd8, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd5, 5'd15, 15'd70);
        spi_board_load(3'd1, 1'b1, 5'd12, 5'd23, 15'd71);
        spi_board_load(3'd2, 1'b1, 5'd19, 5'd10, 15'd72);
        spi_board_load(3'd3, 1'b1, 5'd0, 5'd8, 15'd73);
        spi_board_load(3'd4, 1'b1, 5'd7, 5'd8, 15'd74);
        spi_board_load(3'd5, 1'b1, 5'd14, 5'd15, 15'd75);
        spi_board_load(3'd6, 1'b1, 5'd21, 5'd15, 15'd76);
        spi_board_load(3'd7, 1'b1, 5'd2, 5'd8, 15'd77);
        spi_board_eval(15'd3446, 15'd69, 4'd8, 32'd9, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd9, 5'd11, 15'd78);
        spi_board_load(3'd1, 1'b1, 5'd16, 5'd10, 15'd79);
        spi_board_load(3'd2, 1'b1, 5'd23, 5'd9, 15'd80);
        spi_board_load(3'd3, 1'b1, 5'd4, 5'd22, 15'd81);
        spi_board_load(3'd4, 1'b1, 5'd11, 5'd14, 15'd82);
        spi_board_load(3'd5, 1'b1, 5'd18, 5'd16, 15'd83);
        spi_board_load(3'd6, 1'b1, 5'd25, 5'd12, 15'd84);
        spi_board_load(3'd7, 1'b1, 5'd6, 5'd11, 15'd85);
        spi_board_eval(15'd3446, 15'd77, 4'd8, 32'd10, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd13, 5'd3, 15'd118);
        spi_board_load(3'd1, 1'b1, 5'd20, 5'd10, 15'd119);
        spi_board_load(3'd2, 1'b1, 5'd1, 5'd21, 15'd120);
        spi_board_load(3'd3, 1'b1, 5'd8, 5'd12, 15'd121);
        spi_board_load(3'd4, 1'b1, 5'd15, 5'd17, 15'd96);
        spi_board_load(3'd5, 1'b1, 5'd22, 5'd0, 15'd97);
        spi_board_load(3'd6, 1'b1, 5'd3, 5'd13, 15'd98);
        spi_board_load(3'd7, 1'b1, 5'd10, 5'd22, 15'd99);
        spi_board_eval(15'd3446, 15'd85, 4'd8, 32'd11, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd17, 5'd19, 15'd100);
        spi_board_load(3'd1, 1'b1, 5'd24, 5'd6, 15'd101);
        spi_board_load(3'd2, 1'b1, 5'd5, 5'd21, 15'd102);
        spi_board_load(3'd3, 1'b1, 5'd12, 5'd16, 15'd103);
        spi_board_load(3'd4, 1'b1, 5'd19, 5'd1, 15'd104);
        spi_board_load(3'd5, 1'b1, 5'd0, 5'd5, 15'd105);
        spi_board_load(3'd6, 1'b1, 5'd7, 5'd14, 15'd106);
        spi_board_load(3'd7, 1'b1, 5'd14, 5'd23, 15'd107);
        spi_board_eval(15'd3446, 15'd99, 4'd8, 32'd12, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd21, 5'd9, 15'd108);
        spi_board_load(3'd1, 1'b1, 5'd2, 5'd3, 15'd109);
        spi_board_load(3'd2, 1'b1, 5'd9, 5'd3, 15'd110);
        spi_board_load(3'd3, 1'b1, 5'd16, 5'd23, 15'd111);
        spi_board_load(3'd4, 1'b1, 5'd23, 5'd18, 15'd112);
        spi_board_load(3'd5, 1'b1, 5'd4, 5'd20, 15'd113);
        spi_board_load(3'd6, 1'b1, 5'd11, 5'd6, 15'd114);
        spi_board_load(3'd7, 1'b1, 5'd18, 5'd7, 15'd115);
        spi_board_eval(15'd3446, 15'd107, 4'd8, 32'd13, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd25, 5'd6, 15'd116);
        spi_board_load(3'd1, 1'b1, 5'd6, 5'd19, 15'd117);
        spi_board_load(3'd2, 1'b1, 5'd13, 5'd20, 15'd150);
        spi_board_load(3'd3, 1'b1, 5'd20, 5'd24, 15'd1207);
        spi_board_load(3'd4, 1'b1, 5'd1, 5'd13, 15'd1208);
        spi_board_load(3'd5, 1'b1, 5'd8, 5'd0, 15'd1209);
        spi_board_load(3'd6, 1'b1, 5'd15, 5'd0, 15'd1184);
        spi_board_load(3'd7, 1'b1, 5'd22, 5'd2, 15'd1185);
        spi_board_eval(15'd3446, 15'd115, 4'd8, 32'd14, 3'b111);
        spi_board_load(3'd0, 1'b1, 5'd3, 5'd2, 15'd1186);
        spi_board_load(3'd1, 1'b1, 5'd10, 5'd5, 15'd1187);
        spi_board_load(3'd2, 1'b1, 5'd17, 5'd14, 15'd1188);
        spi_board_eval(15'd3446, 15'd1185, 4'd3, 32'd15, 3'b111);
        if (dut.q_auth_flat_out !== 15'd1188) begin
            $fatal(1, "FAIL T2_PREP: Expected q_auth==1188, got %0d", dut.q_auth_flat_out);
        end

        // 4. Coordinate Board 4-slot OPEN from q_auth == 1188 = (0, 4, 22) -> Pin 31 = 3.30V!
        spi_board_load(3'd0, 1'b1, 5'd18, 5'd23, 15'd1189);
        spi_board_load(3'd1, 1'b1, 5'd19, 5'd2, 15'd1190);
        spi_board_load(3'd2, 1'b1, 5'd0, 5'd11, 15'd1191);
        spi_board_load(3'd3, 1'b1, 5'd11, 5'd2, 15'd1192);
        spi_board_eval(15'd3446, 15'd1188, 4'd4, 32'd16, 3'b111);
        if (port_pins !== 2'd1 || actuator_rail_en !== 1'b1 || killed_latch_pin !== 1'b0 ||
            led_g_n !== 1'b0 || dut.q_auth_flat_out !== 15'd1192) begin
            $fatal(1, "FAIL T2: q_auth==1188 4-slot board_eval failed OPEN (port=%0d act=%0d kill=%0d q=%0d)",
                   port_pins, actuator_rail_en, killed_latch_pin, dut.q_auth_flat_out);
        end
        expected_digest = dut.telemetry_digest;
        spi_nop_poll();
        if (last_miso_word !== expected_digest) begin
            $fatal(1, "FAIL T2_MISO: MISO digest mismatch after q=1188 OPEN");
        end

        // 5. Speculative step + 18-cycle hardware LIFO rewind back to 1192
        spi_eval_step(15'd3446, 5'd2, 5'd5, 15'd1192, 15'd1193, 32'd17);
        if (dut.q_auth_flat_out !== 15'd1193 || dut.lifo_depth_out !== 4'd1 || actuator_rail_en !== 1'b1) begin
            $fatal(1, "FAIL T3A: Speculative eval_step failed");
        end
        spi_lifo_pop(1'b0);
        if (port_pins !== 2'd1 || actuator_rail_en !== 1'b0 || dut.q_auth_flat_out !== 15'd1192 ||
            dut.lifo_depth_out !== 4'd0) begin
            $fatal(1, "FAIL T3B: 18-cycle LIFO rewind failed to restore q_auth=%0d", dut.q_auth_flat_out);
        end

        // 6. Physical Pin 28 (w_ext_hw_pin = 0) wire-pull blocks OPEN -> 0.00V HOLD
        w_ext_hw_pin = 1'b0;
        repeat (4) @(posedge clk_12m);
        spi_eval_step(15'd3446, 5'd2, 5'd5, 15'd1192, 15'd1193, 32'd18);
        if (port_pins !== 2'd0 || actuator_rail_en !== 1'b0 || led_b_n !== 1'b0) begin
            $fatal(1, "FAIL T4: Pulling physical w_ext_hw_pin failed to force 0.00V HOLD");
        end
        w_ext_hw_pin = 1'b1;
        repeat (4) @(posedge clk_12m);

        // 7. 1-bit LIFO tamper -> sticky hardware KILL (Pin 34 = 1, Pin 46 monitor_coupled = 0, RED LED)
        spi_eval_step(15'd3446, 5'd2, 5'd5, 15'd1192, 15'd1193, 32'd19);
        spi_lifo_pop(1'b1);
        if (port_pins !== 2'd2 || killed_latch_pin !== 1'b1 || monitor_coupled_pin !== 1'b0 ||
            actuator_rail_en !== 1'b0 || led_r_n !== 1'b0) begin
            $fatal(1, "FAIL T5: 1-bit LIFO tamper failed to trip sticky KILL");
        end

        // 8. Verified L01 reset restores HOLD (0.00V, monitor_coupled = 1)
        spi_l01_reset();
        if (port_pins !== 2'd0 || killed_latch_pin !== 1'b0 || monitor_coupled_pin !== 1'b1 ||
            actuator_rail_en !== 1'b0) begin
            $fatal(1, "FAIL T6: Verified L01 reset failed to restore HOLD");
        end

        $display("UPDUINO_SPI_TOP=PASS (q0=0 OPEN 3.3V, q0=1188 OPEN 3.3V, 0-LAG MISO, 18-CYC LIFO, W_EXT CUT & TAMPER KILL)");
        $finish;
    end
endmodule
`default_nettype wire
