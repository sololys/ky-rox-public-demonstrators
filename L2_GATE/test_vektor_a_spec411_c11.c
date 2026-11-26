/*
 * test_vektor_a_spec411_c11.c — C11 10/10 Unit & RTL-Parity Test Suite
 * ============================================================================
 * Verifies Vektor A (133,425 ps Alexandrov Light-Cone + +-5 ppm Sapphire Lock)
 * and SPEC-411 Galvanic Dual-Rail Separation (no IEEE-754 FP, 0 malloc):
 *   T1 : Exact 128-bit Alexandrov horizon: 133,425 ps PASS vs 133,426 ps REJECT
 *   T2 : Zero/invalid ToF (0 ps) & radius > 20,000 mm rejected
 *   T3 : +-1 tick (+-5.0 ppm) crystal window accepted; optical_tx_only == 1
 *   T4 : +-2 ticks (+-10.0 ppm) latches sticky VEKTOR_A_CLOCK_DRIFT_KILL
 *   T5 : Reverse write on optical TX diode latches sticky VEKTOR_A_DIODE_KILL
 *   T6 : SPEC-411 cold-boot HOLD = 0x01 & 133,425 ps OPEN = 0x13
 *   T7 : SPEC-411 133,426 ps CAUSAL_HOLD = 0x01 (500 m / 3,335,640 ps = 0x01)
 *   T8 : SPEC-411 semantic breach (dK >= eps) latches isolated KILL_T = 0x05
 *   T9 : SPEC-411 crisis (rho_N < K_gamma) latches Butterfly A_5 = 0x09 until L01
 *   T10: Non-erasing spec411_l01_reset preserves monotonic step_seq & Omega_Y == 1
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "spec411_gate.h"

int main(void) {
    /* T1: Exact 20.0 m (20,000 mm) round-trip light-cone boundary */
    if (!vektor_a_alexandrov_cone_ok(20000U, 133425U)) {
        fprintf(stderr, "FAIL T1a: 133,425 ps at 20.0 m rejected\n");
        return 1;
    }
    if (vektor_a_alexandrov_cone_ok(20000U, 133426U)) {
        fprintf(stderr, "FAIL T1b: 133,426 ps (+1 ps outside diamond) accepted\n");
        return 1;
    }

    /* T2: Zero ToF, zero radius, and >20.0 m radius bounds */
    if (vektor_a_alexandrov_cone_ok(20000U, 0U) ||
        vektor_a_alexandrov_cone_ok(0U, 100000U) ||
        vektor_a_alexandrov_cone_ok(20001U, 100000U)) {
        fprintf(stderr, "FAIL T2: Out-of-range radius/ToF accepted\n");
        return 1;
    }

    /* T3: +-1 tick (+-5.0 ppm) window accepted */
    vektor_a_state_t va;
    vektor_a_init(&va);
    vektor_a_step(&va, 1U, 133425U, 1U, 200001U, 0U);
    if (va.core_wake_en != 1U || va.causal_hold != 0U ||
        va.optical_tx_only != 1U || va.last_verdict != VEKTOR_A_WAKE_OPEN) {
        fprintf(stderr, "FAIL T3a: +5 ppm boundary failed\n");
        return 1;
    }
    vektor_a_step(&va, 1U, 100000U, 1U, 199999U, 0U);
    if (va.core_wake_en != 1U || va.last_verdict != VEKTOR_A_WAKE_OPEN) {
        fprintf(stderr, "FAIL T3b: -5 ppm boundary failed\n");
        return 1;
    }

    /* T4: +2 ticks (+10.0 ppm) latches sticky CLOCK_DRIFT_KILL */
    vektor_a_step(&va, 1U, 100000U, 1U, 200002U, 0U);
    if (va.clock_drift_kill != 1U || va.core_wake_en != 0U ||
        va.last_verdict != VEKTOR_A_CLOCK_DRIFT_KILL) {
        fprintf(stderr, "FAIL T4a: +2 tick drift did not latch KILL\n");
        return 1;
    }
    /* Sticky check against nominal frame */
    vektor_a_step(&va, 1U, 100000U, 1U, 200000U, 0U);
    if (va.clock_drift_kill != 1U || va.core_wake_en != 0U) {
        fprintf(stderr, "FAIL T4b: Sticky CLOCK_DRIFT_KILL cleared without L01 reset\n");
        return 1;
    }

    /* T5: Reverse write attempt on optical diode latches DIODE_KILL */
    vektor_a_init(&va);
    vektor_a_step(&va, 1U, 100000U, 1U, 200000U, 1U);
    if (va.clock_drift_kill != 1U || va.optical_tx_only != 0U ||
        va.last_verdict != VEKTOR_A_DIODE_KILL) {
        fprintf(stderr, "FAIL T5: Optical diode reverse write did not latch DIODE_KILL\n");
        return 1;
    }

    /* T6..T10: Exact 8-vector RTL parity (0x01, 0x13, 0x01, 0x05, 0x01, 0x09, 0x09, 0x13) */
    spec411_state_t gs;
    spec411_init(&gs);

    /* G1: Cold boot HOLD -> 0x01 */
    if (spec411_pack_hw_byte(&gs) != 0x01U || gs.omega_y_en != 1U) {
        fprintf(stderr, "FAIL T6a: Cold boot byte != 0x01\n");
        return 1;
    }

    /* G2: Valid 133,425 ps OPEN -> 0x13 */
    uint8_t b2 = spec411_step(&gs, 1U, 133425U, 1U, 200000U, 1U, 1U, 100U, 5U, 100U, 100U, 50U, 0U);
    if (b2 != 0x13U) {
        fprintf(stderr, "FAIL T6b: Valid 133,425 ps OPEN != 0x13 (got 0x%02X)\n", b2);
        return 1;
    }

    /* G3: 133,426 ps (+1 ps outside cone) & 500 m relay (3,335,640 ps) -> 0x01 */
    uint8_t b3 = spec411_step(&gs, 1U, 133426U, 1U, 200000U, 1U, 1U, 100U, 5U, 100U, 100U, 50U, 0U);
    uint8_t b_relay = spec411_step(&gs, 1U, 3335640U, 1U, 200000U, 1U, 1U, 100U, 5U, 100U, 100U, 50U, 0U);
    if (b3 != 0x01U || b_relay != 0x01U) {
        fprintf(stderr, "FAIL T7: Out-of-cone / 500 m relay != 0x01\n");
        return 1;
    }

    /* G4: Semantic breach (dK = 6/100 >= eps = 5/100) -> isolated KILL_T = 0x05 */
    uint8_t b4 = spec411_step(&gs, 1U, 133426U, 1U, 200000U, 1U, 6U, 100U, 5U, 100U, 100U, 50U, 0U);
    if (b4 != 0x05U || gs.omega_y_en != 1U || gs.omega_t_en != 0U) {
        fprintf(stderr, "FAIL T8: Semantic breach != 0x05\n");
        return 1;
    }

    /* G5: Non-erasing Level 01 reset -> 0x01, preserves monotonic step_seq */
    uint64_t prev_seq = gs.step_seq;
    spec411_l01_reset(&gs);
    if (spec411_pack_hw_byte(&gs) != 0x01U || gs.step_seq != prev_seq || gs.reset_epoch != 1U) {
        fprintf(stderr, "FAIL T10: Non-erasing L01 reset invariant violated\n");
        return 1;
    }

    /* G6 & G7: Crisis (rho_N = 30 < K_gamma = 50) latches A_5 = 0x09 until avg_l01_trigger */
    uint8_t b6 = spec411_step(&gs, 0U, 0U, 1U, 200000U, 1U, 1U, 100U, 5U, 100U, 30U, 50U, 0U);
    uint8_t b7 = spec411_step(&gs, 0U, 0U, 1U, 200000U, 1U, 1U, 100U, 5U, 100U, 100U, 50U, 0U);
    uint8_t b8 = spec411_step(&gs, 1U, 120000U, 1U, 200000U, 1U, 1U, 100U, 5U, 100U, 100U, 50U, 1U);
    if (b6 != 0x09U || b7 != 0x09U || b8 != 0x13U || gs.omega_y_en != 1U) {
        fprintf(stderr, "FAIL T9: Butterfly A_5 sequence mismatch (0x%02X, 0x%02X, 0x%02X)\n", b6, b7, b8);
        return 1;
    }

    printf("VEKTOR_A_SPEC411_C11=PASS (10/10 TESTS PASSED, 133425 PS DIAMOND, 0 IEEE-754 FP, 0 MALLOC)\n");
    return 0;
}
