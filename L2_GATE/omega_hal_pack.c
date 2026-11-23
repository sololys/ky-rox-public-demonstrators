/*
 * omega_hal_pack.c — Hardened C11 64-Byte SPI Frame Packer (0 float, 0 malloc)
 * ============================================================================
 * Epistemic Tier   : L1 / L1.5 Deterministic Software & RTL HAL
 * Physical Auth    : NONE (0.00 V DC; INSPIRED_BY != IMPLEMENTS != PROVES)
 * Guarantees       : Zero floating-point, zero heap allocation, zero silent
 *                    integer truncation, full 60-byte IEEE 802.3 CRC-32.
 */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include "omega_spi_frame_64b.h"

uint32_t omega_crc32_bytes(const uint8_t *data, size_t len) {
    uint32_t crc = 0xFFFFFFFFU;
    for (size_t i = 0; i < len; ++i) {
        crc ^= (uint32_t)data[i];
        for (int bit = 0; bit < 8; ++bit) {
            uint32_t mask = (uint32_t)(-(int32_t)(crc & 1U));
            crc = (crc >> 1) ^ (0xEDB88320U & mask);
        }
    }
    return ~crc;
}

bool omega_pack_verified_frame_64b(
    omega_spi_frame_64b_t *out_frame,
    uint64_t expected_step,
    uint64_t l_init,
    uint64_t l_now,
    uint64_t l_heat,
    const int64_t q_um[3],
    const int64_t p_fp[3],
    uint32_t prev_crc32
) {
    if (!out_frame || !q_um || !p_fp) {
        return false;
    }

    /* 1. No silent truncation on step_counter (must fit 1..UINT32_MAX) */
    if (expected_step == 0U || expected_step > (uint64_t)UINT32_MAX) {
        return false;
    }

    /* 2. Overflow-safe 64-bit conservation check: l_now + l_heat == l_init */
    if (l_now > UINT64_MAX - l_heat) {
        return false;
    }
    if ((l_now + l_heat) != l_init) {
        return false;
    }

    /* 3. No silent truncation on 3D position/momentum axes */
    for (int i = 0; i < 3; ++i) {
        if (q_um[i] < (int64_t)INT32_MIN || q_um[i] > (int64_t)INT32_MAX) {
            return false;
        }
        if (p_fp[i] < (int64_t)INT32_MIN || p_fp[i] > (int64_t)INT32_MAX) {
            return false;
        }
    }

    /* 4. Zero-initialize full 64B block before packing */
    memset(out_frame, 0, sizeof(*out_frame));

    out_frame->magic_sync   = OMEGA_SPI_MAGIC_SYNC;
    out_frame->step_counter = (uint32_t)expected_step;
    for (int i = 0; i < 3; ++i) {
        out_frame->q_pos_um[i] = (int32_t)q_um[i];
        out_frame->p_mom_fp[i] = (int32_t)p_fp[i];
    }
    out_frame->l_now      = l_now;
    out_frame->l_heat     = l_heat;
    out_frame->l_init     = l_init;
    out_frame->prev_crc32 = prev_crc32;

    /* 5. Full IEEE 802.3 CRC-32 over all 60 preceding bytes */
    const uint8_t *raw = (const uint8_t *)out_frame;
    out_frame->crc32_witness = omega_crc32_bytes(raw, 60U);

    return omega_conservation_ok(out_frame);
}
