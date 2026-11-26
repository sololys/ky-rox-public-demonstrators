#ifndef SPEC411_GATE_H
#define SPEC411_GATE_H

#include <stdint.h>
#include "vektor_a_gate.h"

/* ============================================================================
 * SPEC-411 Galvanic Separation Gate behind Vektor A 133,425 ps Airlock
 * ============================================================================
 * Surface        : L2_GATE/spec411_gate.h
 * Arithmetic     : Exact integer rational cross-multiplication (no IEEE-754 FP)
 * Epistemic Tier : L1 / L1.5 Deterministic Reference Gate (0.00 V DC authority)
 *
 * Dual-Rail Law  : Psi = [Omega_Y, Omega_T]^T with d(Omega_Y) / d(Omega_T) == 0
 *   - Omega_Y (Bit 0, 0x01): 5.00 V Fail-Open unconditional existence rail
 *   - Omega_T (Bit 1, 0x02): 0.00 V / 5.00 V Fail-Closed actuation rail
 *   - KILL_T  (Bit 2, 0x04): Isolated sticky KILL latch on Omega_T only
 *   - A5_POCK (Bit 3, 0x08): Butterfly Pocket A_5 stasis latch (d(Omega_T)/dt = 0)
 *   - OPT_TX  (Bit 4, 0x10): One-way optical telemetry diode from Vektor A
 * ============================================================================ */

typedef struct {
    vektor_a_state_t airlock;
    uint32_t         reset_epoch;
    uint64_t         step_seq;
    uint8_t          omega_y_en;         /* Bit 0 (0x01): Always 1 (5.00 V) */
    uint8_t          omega_t_en;         /* Bit 1 (0x02): 0 (0.00 V) / 1 (5.00 V) */
    uint8_t          omega_t_kill_latch; /* Bit 2 (0x04): Isolated KILL on Omega_T */
    uint8_t          a5_pocket_active;   /* Bit 3 (0x08): Butterfly Pocket A_5 */
} spec411_state_t;

static inline void spec411_init(spec411_state_t *st) {
    vektor_a_init(&st->airlock);
    st->reset_epoch        = 0U;
    st->step_seq           = 0ULL;
    st->omega_y_en         = 1U;
    st->omega_t_en         = 0U;
    st->omega_t_kill_latch = 0U;
    st->a5_pocket_active   = 0U;
}

/* Non-erasing Level 01 recovery reset: preserves step_seq & advances reset_epoch */
static inline void spec411_l01_reset(spec411_state_t *st) {
    vektor_a_init(&st->airlock);
    st->reset_epoch       += 1U;
    st->omega_y_en         = 1U;
    st->omega_t_en         = 0U;
    st->omega_t_kill_latch = 0U;
    st->a5_pocket_active   = 0U;
}

static inline uint8_t spec411_pack_hw_byte(const spec411_state_t *st) {
    return (uint8_t)(
        ((st->omega_y_en & 1U)                << 0) |
        ((st->omega_t_en & 1U)                << 1) |
        ((st->omega_t_kill_latch & 1U)        << 2) |
        ((st->a5_pocket_active & 1U)          << 3) |
        ((st->airlock.optical_tx_only & 1U)   << 4)
    );
}

static inline uint8_t spec411_step(
    spec411_state_t *st,
    uint8_t          tdc_valid,
    uint32_t         tdc_tof_ps,
    uint8_t          win_valid,
    uint32_t         sapphire_meas_ticks,
    uint8_t          bilat_50_50_sealed,
    uint32_t         delta_k_num,
    uint32_t         delta_k_den,
    uint32_t         eps_num,
    uint32_t         eps_den,
    uint32_t         rho_n,
    uint32_t         k_gamma,
    uint8_t          avg_l01_trigger
) {
    vektor_a_step(&st->airlock, tdc_valid, tdc_tof_ps, win_valid, sapphire_meas_ticks, 0U);
    st->step_seq += 1ULL;

    uint64_t lhs_delta = (uint64_t)delta_k_num * (uint64_t)eps_den;
    uint64_t rhs_eps   = (uint64_t)eps_num     * (uint64_t)delta_k_den;

    uint8_t semantic_mismatch = (delta_k_den == 0U) || (eps_den == 0U) || (lhs_delta >= rhs_eps);
    uint8_t crisis_condition  = (rho_n < k_gamma) ? 1U : 0U;

    if (crisis_condition) {
        st->a5_pocket_active = 1U;
    } else if (st->a5_pocket_active && avg_l01_trigger) {
        st->a5_pocket_active = 0U;
    }

    if (st->airlock.clock_drift_kill ||
        (bilat_50_50_sealed && semantic_mismatch && !st->a5_pocket_active && !crisis_condition)) {
        st->omega_t_kill_latch = 1U;
        st->omega_t_en         = 0U;
    } else if (st->omega_t_kill_latch || st->a5_pocket_active || crisis_condition) {
        st->omega_t_en = 0U;
    } else {
        st->omega_t_en = (st->airlock.core_wake_en && bilat_50_50_sealed && !semantic_mismatch) ? 1U : 0U;
    }

    /* Galvanic invariant: Omega_Y remains 1 (5.00 V) unconditionally */
    st->omega_y_en = 1U;

    return spec411_pack_hw_byte(st);
}

#endif /* SPEC411_GATE_H */
