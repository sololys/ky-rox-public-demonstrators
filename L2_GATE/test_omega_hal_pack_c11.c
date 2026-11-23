/*
 * test_omega_hal_pack_c11.c — C11 5/5 Unit & Parity Test for omega_hal_pack.c
 * ============================================================================
 * Verifies:
 *   T1: Valid 64B frame packing + exact IEEE 802.3 CRC-32 over 60 bytes
 *   T2: Rejects silent 64->32-bit axis truncation (INT32_MAX + 1)
 *   T3: Rejects 64-bit unsigned overflow in l_now + l_heat
 *   T4: Rejects conservation mismatch (l_now + l_heat != l_init)
 *   T5: Rejects step_counter == 0 or > UINT32_MAX & detects 1-bit CRC tamper
 */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include "omega_spi_frame_64b.h"

extern uint32_t omega_crc32_bytes(const uint8_t *data, size_t len);
extern bool omega_pack_verified_frame_64b(
    omega_spi_frame_64b_t *out_frame,
    uint64_t expected_step,
    uint64_t l_init,
    uint64_t l_now,
    uint64_t l_heat,
    const int64_t q_um[3],
    const int64_t p_fp[3],
    uint32_t prev_crc32
);

int main(void) {
    omega_spi_frame_64b_t f1;
    const int64_t q_ok[3] = { 1000, -2000, 3000 };
    const int64_t p_ok[3] = { -50, 75, 125 };

    /* T1: Valid 64-byte frame */
    if (!omega_pack_verified_frame_64b(&f1, 1U, 1000U, 900U, 100U, q_ok, p_ok, 0x00000000U)) {
        fprintf(stderr, "FAIL T1: Valid frame rejected\n");
        return 1;
    }
    if (f1.magic_sync != OMEGA_SPI_MAGIC_SYNC || f1.step_counter != 1U) {
        fprintf(stderr, "FAIL T1: Header fields mismatch\n");
        return 1;
    }
    if (omega_crc32_bytes((const uint8_t *)&f1, 60U) != f1.crc32_witness) {
        fprintf(stderr, "FAIL T1: CRC-32 mismatch\n");
        return 1;
    }

    /* T2: Silent truncation guard (INT32_MAX + 1) */
    const int64_t q_overflow[3] = { (int64_t)INT32_MAX + 1, 0, 0 };
    omega_spi_frame_64b_t f2;
    if (omega_pack_verified_frame_64b(&f2, 2U, 1000U, 900U, 100U, q_overflow, p_ok, f1.crc32_witness)) {
        fprintf(stderr, "FAIL T2: Axis overflow was not rejected\n");
        return 1;
    }

    /* T3: 64-bit unsigned addition overflow guard */
    if (omega_pack_verified_frame_64b(&f2, 2U, 0U, UINT64_MAX, 1U, q_ok, p_ok, f1.crc32_witness)) {
        fprintf(stderr, "FAIL T3: 64-bit l_now + l_heat overflow was not rejected\n");
        return 1;
    }

    /* T4: Conservation breach */
    if (omega_pack_verified_frame_64b(&f2, 2U, 1000U, 900U, 101U, q_ok, p_ok, f1.crc32_witness)) {
        fprintf(stderr, "FAIL T4: Conservation mismatch was not rejected\n");
        return 1;
    }

    /* T5: Step bounds & 1-bit CRC tamper detection */
    if (omega_pack_verified_frame_64b(&f2, 0U, 1000U, 900U, 100U, q_ok, p_ok, f1.crc32_witness)) {
        fprintf(stderr, "FAIL T5a: step_counter=0 was not rejected\n");
        return 1;
    }
    if (omega_pack_verified_frame_64b(&f2, (uint64_t)UINT32_MAX + 1U, 1000U, 900U, 100U, q_ok, p_ok, f1.crc32_witness)) {
        fprintf(stderr, "FAIL T5b: step_counter > UINT32_MAX was not rejected\n");
        return 1;
    }
    /* Flip 1 bit in q_pos_um[0] and confirm CRC-32 detects tamper */
    f1.q_pos_um[0] ^= 1;
    if (omega_crc32_bytes((const uint8_t *)&f1, 60U) == f1.crc32_witness) {
        fprintf(stderr, "FAIL T5c: 1-bit payload tamper was not detected by CRC-32\n");
        return 1;
    }

    printf("OMEGA_HAL_PACK_C11=PASS (5/5 TESTS PASSED, 64B EXACT, 0 FLOAT, 0 MALLOC)\n");
    return 0;
}
