#ifndef VEKTOR_A_GATE_H
#define VEKTOR_A_GATE_H

#include <stdbool.h>
#include <stdint.h>

/* ============================================================================
 * Vektor A Outer Airlock — 133,425 ps (20.0 m Alexandrov Light-Cone),
 * Sapphire +-5.0 ppm Clock-Drift Lock & One-Way Optical Data Diode
 * ============================================================================
 * Surface        : L2_GATE/vektor_a_gate.h
 * Arithmetic     : Exact 64-bit / 128-bit integer picoseconds & crystal ticks
 *                  (zero IEEE-754 FP types or operations)
 * Epistemic Tier : L1 / L1.5 Deterministic Reference Gate (0.00 V DC authority)
 *
 * Physical Constants:
 *   - c         = 299,792,458 m/s (SI exact)
 *   - R_max     = 20.0 m (20,000 mm) => round-trip 2 * R_max = 40.0 m
 *   - tau_max   = floor(40.0 m / c in ps) = 133,425 ps (133.4256 ns truncated)
 *   - N_ref     = 200,000 ticks @ +-5.0 ppm => +-1 discrete crystal tick
 * ============================================================================ */

#define VEKTOR_A_C_MPS           (299792458ULL)
#define VEKTOR_A_R_MAX_MM        (20000ULL)
#define VEKTOR_A_TAU_MAX_PS      (133425U)
#define VEKTOR_A_SAPPHIRE_N_REF  (200000U)
#define VEKTOR_A_MAX_DRIFT_TICKS (1U)

typedef enum {
    VEKTOR_A_WAKE_OPEN        = 0, /* Inside 133,425 ps diamond & clock locked */
    VEKTOR_A_CAUSAL_HOLD      = 1, /* Outside light-cone -> core asleep (0.00 V) */
    VEKTOR_A_CLOCK_DRIFT_KILL = 2, /* |Delta N| >= 2 ticks (> 5 ppm) -> sticky KILL */
    VEKTOR_A_DIODE_KILL       = 3  /* Reverse write on optical TX diode -> sticky KILL */
} vektor_a_verdict_t;

typedef struct {
    uint8_t            clock_drift_kill;
    uint8_t            causal_hold;
    uint8_t            core_wake_en;
    uint8_t            optical_tx_only;
    vektor_a_verdict_t last_verdict;
} vektor_a_state_t;

static inline void vektor_a_init(vektor_a_state_t *st) {
    st->clock_drift_kill = 0U;
    st->causal_hold      = 1U;
    st->core_wake_en     = 0U;
    st->optical_tx_only  = 0U;
    st->last_verdict     = VEKTOR_A_CAUSAL_HOLD;
}

/* Exact integer Alexandrov light-cone check for radius r_mm <= 20,000 mm:
 *   c * tau_ps <= 2 * r_mm * 10^9
 * At r_mm = 20,000 mm:
 *   tau_ps = 133,425 ps -> 39,999,808,708,650 <= 40,000,000,000,000 (PASS)
 *   tau_ps = 133,426 ps -> 40,000,108,501,108 >  40,000,000,000,000 (CAUSAL_HOLD)
 */
static inline bool vektor_a_alexandrov_cone_ok(uint32_t r_mm, uint32_t tau_ps) {
    if (r_mm == 0U || r_mm > VEKTOR_A_R_MAX_MM) {
        return false;
    }
    if (tau_ps == 0U || tau_ps > VEKTOR_A_TAU_MAX_PS) {
        return false;
    }
#ifdef __SIZEOF_INT128__
    __extension__ typedef unsigned __int128 vektor_a_u128_t;
    vektor_a_u128_t dist_scaled = (vektor_a_u128_t)(2ULL * (uint64_t)r_mm) * 1000000000ULL;
    vektor_a_u128_t ct_scaled   = (vektor_a_u128_t)VEKTOR_A_C_MPS * (vektor_a_u128_t)tau_ps;
    return (ct_scaled * ct_scaled) <= (dist_scaled * dist_scaled);
#else
    uint64_t dist_scaled = (2ULL * (uint64_t)r_mm) * 1000000000ULL;
    uint64_t ct_scaled   = VEKTOR_A_C_MPS * (uint64_t)tau_ps;
    return ct_scaled <= dist_scaled;
#endif
}

static inline void vektor_a_step(
    vektor_a_state_t *st,
    uint8_t           tdc_valid,
    uint32_t          tdc_tof_ps,
    uint8_t           win_valid,
    uint32_t          sapphire_meas_ticks,
    uint8_t           reverse_write_attempt
) {
    uint32_t diff = (sapphire_meas_ticks >= VEKTOR_A_SAPPHIRE_N_REF)
        ? (sapphire_meas_ticks - VEKTOR_A_SAPPHIRE_N_REF)
        : (VEKTOR_A_SAPPHIRE_N_REF - sapphire_meas_ticks);

    if (reverse_write_attempt != 0U) {
        st->clock_drift_kill = 1U;
        st->causal_hold      = 1U;
        st->core_wake_en     = 0U;
        st->optical_tx_only  = 0U;
        st->last_verdict     = VEKTOR_A_DIODE_KILL;
        return;
    }

    if (win_valid && (diff > VEKTOR_A_MAX_DRIFT_TICKS)) {
        st->clock_drift_kill = 1U;
    }

    if (st->clock_drift_kill) {
        st->causal_hold     = 1U;
        st->core_wake_en    = 0U;
        st->optical_tx_only = 0U;
        if (st->last_verdict != VEKTOR_A_DIODE_KILL) {
            st->last_verdict = VEKTOR_A_CLOCK_DRIFT_KILL;
        }
        return;
    }

    if (tdc_valid && (tdc_tof_ps > 0U) && (tdc_tof_ps <= VEKTOR_A_TAU_MAX_PS)) {
        st->causal_hold     = 0U;
        st->core_wake_en    = 1U;
        st->optical_tx_only = 1U;
        st->last_verdict    = VEKTOR_A_WAKE_OPEN;
    } else {
        st->causal_hold     = 1U;
        st->core_wake_en    = 0U;
        st->optical_tx_only = 0U;
        st->last_verdict    = VEKTOR_A_CAUSAL_HOLD;
    }
}

#endif /* VEKTOR_A_GATE_H */
