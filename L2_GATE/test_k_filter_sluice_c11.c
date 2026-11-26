/*
 * C11 Reference Runner & 12-Vector Parity Emitter (no IEEE-754 FP, 0 malloc)
 */
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#include "k_filter_sluice.h"

static uint8_t pack_out_byte(const k_sluice_reg_t *r) {
    return (uint8_t)(
        (((uint8_t)r->last_port & 0x3U)         << 0) |
        ((r->actuator_v_en ? 1U : 0U)           << 2) |
        ((r->monitor_coupled ? 1U : 0U)         << 3) |
        ((r->kill_latched ? 1U : 0U)            << 4)
    );
}

static k_arm_state_t make_nominal_arm(void) {
    k_arm_state_t s;
    memset(&s, 0, sizeof(s));
    s.q[0]         = 1200LL;
    s.q[1]         = -450LL;
    s.q[2]         = 80LL;
    s.p[0]         = -30LL;
    s.p[1]         = 15LL;
    s.p[2]         = 90LL;
    s.norm_err_sq  = 4ULL;
    s.norm_ref_sq  = 100ULL;
    s.valid_steps  = 64U;
    s.total_steps  = 64U;
    s.phi_res_abs  = 3ULL;
    s.lambda_bound = 12ULL;
    s.spec_max_re  = 0LL;
    s.entropy_paid = 5706ULL;
    s.entropy_req  = 5706ULL;
    s.hash_valid   = true;
    s.witness_ext  = true;
    return s;
}

int main(void) {
    const k_gate_cfg_t cfg = {
        .delta_num   = 5ULL,
        .delta_den   = 100ULL,
        .phi_res_max = 10ULL,
        .lambda_max  = 50ULL,
        .w_k         = 10U,
        .w_v         = 1000U,
        .w_phi       = 5U,
        .w_p         = 2U
    };

    if (k_macro_accum_step(k_macro_accum_step(0U, 10), 100) != 100000U ||
        k_macro_accum_step(500U, -1) != 0U) {
        return 1;
    }

    k_sluice_reg_t reg;
    k_sluice_reg_init(&reg);

    struct {
        omega_port_t exp_port;
        k_reason_t   exp_reason;
        uint8_t      exp_byte;
    } expected[12] = {
        { PORT_OPEN, REASON_OPEN_WITNESSED,     0x0DU },
        { PORT_HOLD, REASON_HOLD_NO_WITNESS,    0x08U },
        { PORT_HOLD, REASON_HOLD_PREP_MISMATCH, 0x08U },
        { PORT_HOLD, REASON_HOLD_PHI_RESIDUAL,  0x08U },
        { PORT_KILL, REASON_KILL_CHAIN_STEPS,   0x12U },
        { PORT_KILL, REASON_KILL_LATCHED,       0x12U },
        { PORT_HOLD, REASON_HOLD_NO_WITNESS,    0x08U },
        { PORT_KILL, REASON_KILL_CHAIN_STEPS,   0x12U },
        { PORT_KILL, REASON_KILL_LANDAUER_DEBT, 0x12U },
        { PORT_OPEN, REASON_OPEN_WITNESSED,     0x0DU },
        { PORT_KILL, REASON_KILL_KERNEL_DRIFT,  0x12U },
        { PORT_KILL, REASON_KILL_POISON_MIN,    0x12U }
    };

    for (int v = 1; v <= 12; ++v) {
        k_arm_state_t s = make_nominal_arm();
        bool prep_ok = true;
        if (v == 2) s.witness_ext = false;
        else if (v == 3) prep_ok = false;
        else if (v == 4) s.phi_res_abs = 11ULL;
        else if (v == 5) s.valid_steps = 63U;
        else if (v == 7) (void)k_sluice_l01_reset(&reg, true);
        else if (v == 8) s.valid_steps = 65U;
        else if (v == 9) { (void)k_sluice_l01_reset(&reg, true); s.entropy_paid = 5705ULL; }
        else if (v == 10) { (void)k_sluice_l01_reset(&reg, true); s.norm_err_sq = (1ULL << 56); s.norm_ref_sq = (1ULL << 56) * 20ULL; }
        else if (v == 11) { s.norm_err_sq = (1ULL << 56) + 1ULL; s.norm_ref_sq = (1ULL << 56) * 20ULL; }
        else if (v == 12) { (void)k_sluice_l01_reset(&reg, true); s.p[1] = K_POISON_INT64_MIN; }

        if (v != 7) (void)k_sluice_step(&reg, &s, &cfg, prep_ok);

        uint8_t got_byte = pack_out_byte(&reg);
        if (reg.last_port != expected[v - 1].exp_port ||
            reg.last_reason != expected[v - 1].exp_reason ||
            got_byte != expected[v - 1].exp_byte) {
            return 1;
        }
        printf("VEC %02d | BYTE=0x%02x | PORT=%u | REASON=%02u | DK=%" PRIu64 "\n",
               v, (unsigned)got_byte, (unsigned)reg.last_port,
               (unsigned)reg.last_reason, reg.last_delta_k);
    }
    printf("K_FILTER_SLUICE_C11=PASS (12/12 VECTORS, 128-BIT EXACT, 0 IEEE-754 FP)\n");
    return 0;
}
