/*
 * omega_spi_frame_64b.h — Exact 64-Byte (512-bit) SPI Frame Contract (C11, 0 float)
 * =================================================================================
 * Epistemic Tier   : L1 / L1.5 Deterministic Software & RTL Contract
 * Physical Auth    : NONE (0.00 V DC rest state; INSPIRED_BY != IMPLEMENTS != PROVES)
 * Arithmetic       : Exact fixed-width integer arithmetic ONLY (ZERO float/double)
 */
#ifndef OMEGA_SPI_FRAME_64B_H
#define OMEGA_SPI_FRAME_64B_H

#include <stdint.h>
#include <stdbool.h>

#define OMEGA_SPI_MAGIC_SYNC 0x4F4D4547u /* "OMEG" */

typedef struct __attribute__((packed)) {
    uint32_t magic_sync;     /*  4B: 0x4F4D4547 ("OMEG") */
    uint32_t step_counter;   /*  4B: strictly monotonic (+1 per frame) */
    int32_t  q_pos_um[3];    /* 12B: 3D position (x, y, z) in micrometers */
    int32_t  p_mom_fp[3];    /* 12B: 3D momentum (px, py, pz) in fixed-point */
    uint64_t l_now;          /*  8B: current angular-momentum magnitude */
    uint64_t l_heat;         /*  8B: accounted dissipative heat loss */
    uint64_t l_init;         /*  8B: conserved baseline (l_now + l_heat == l_init) */
    uint32_t prev_crc32;     /*  4B: previous frame witness link */
    uint32_t crc32_witness;  /*  4B: current frame checksum */
} omega_spi_frame_64b_t;

_Static_assert(sizeof(omega_spi_frame_64b_t) == 64, "omega_spi_frame_64b_t must be exactly 64 bytes");

/* Overflow-safe exact integer conservation check: l_now + l_heat == l_init */
static inline bool omega_conservation_ok(const omega_spi_frame_64b_t *f) {
    if (!f || f->magic_sync != OMEGA_SPI_MAGIC_SYNC) {
        return false;
    }
    if (f->l_now > UINT64_MAX - f->l_heat) {
        return false; /* overflow => FAIL-CLOSED */
    }
    return (f->l_now + f->l_heat) == f->l_init;
}

#endif /* OMEGA_SPI_FRAME_64B_H */
