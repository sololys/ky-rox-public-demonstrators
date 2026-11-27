#include "nlk_enigma_sluice.h"
#include <stdio.h>

static nlk_step_in_t nominal_step(const nlk_sluice_reg_t *r, uint8_t x_in, uint32_t seq) {
    nlk_step_in_t in;
    uint16_t qp = 0U;
    uint8_t  yc = 0U;
    nlk_layer1_propose(x_in, r->q_auth_flat, 0U, true, &qp, &yc);
    in.ring_flat     = 0U;
    in.plug_en       = true;
    in.x_in          = x_in;
    in.y_cand        = yc;
    in.q_before_flat = r->q_auth_flat;
    in.q_prop_flat   = qp;
    in.seq_num       = seq;
    in.meas_en       = false;
    in.meas_stale    = false;
    in.e_err         = 0U;
    in.sigma_ref     = 10U;
    in.bits_erased   = 0U;
    in.q_diss_rj     = 0ULL;
    in.hash_valid    = true;
    in.wal_ready     = true;
    in.crash_inject  = false;
    in.l2_profile    = false;
    in.hw_verified   = false;
    in.witness_ext   = true;
    return in;
}

static void print_vec(const char *tag, const nlk_sluice_reg_t *r) {
    printf(
        "%s|BYTE=0x%02x|PORT=%u|REASON=%02u|Y=%02u|Q=0x%04x|LIFO=%u|"
        "SEQ=%u|CYC=%llu|EPOCH=%u\n",
        tag,
        (unsigned int)nlk_status_byte(r),
        (unsigned int)r->last_port,
        (unsigned int)r->last_reason,
        (unsigned int)r->last_y_out,
        (unsigned int)r->q_auth_flat,
        (unsigned int)r->lifo_depth,
        (unsigned int)r->seq_prev,
        (unsigned long long)r->cycle,
        (unsigned int)r->reset_epoch
    );
}

int main(void) {
    static const char *msg = "GRANITTBAERERIKKEPLASTIKKGRANITTBAERERIKKEPLASTIKK"
                             "GRANITTBAERERIKKEPLASTIKKGRANITTBAERERIKKEPLASTIKKSTAL";
    nlk_sluice_reg_t r;
    nlk_sluice_init(&r);
    uint32_t seq = 1U;

    /* V01: 104-step marathon from (0,0,0) crossing Rotor III/II/I notch cascade -> (1,5,25) OPEN */
    for (uint32_t i = 0U; i < 104U; ++i) {
        uint8_t x_ch = (uint8_t)(msg[i] - 'A');
        nlk_step_in_t st = nominal_step(&r, x_ch, seq++);
        nlk_sluice_eval_step(&r, &st);
    }
    print_vec("V01", &r);

    /* V02: LIFO Reversible Uncompute #1 — pops 'L' (11) and rewinds q_auth 1 step at 0.00 V */
    nlk_sluice_lifo_pop(&r, 0U, true, true, false);
    print_vec("V02", &r);

    /* V03: LIFO Reversible Uncompute #2 — pops 'A' (0) and rewinds q_auth 1 step */
    nlk_sluice_lifo_pop(&r, 0U, true, true, false);
    print_vec("V03", &r);

    /* V04: LIFO Reversible Uncompute #3 & #4 — pops 'T' then 'S' across 3-rotor notch cascade back to ql=0! */
    nlk_sluice_lifo_pop(&r, 0U, true, true, false);
    nlk_sluice_lifo_pop(&r, 0U, true, true, false);
    print_vec("V04", &r);

    /* V05: Exact Rational Lower Knife-Edge (10*e == 9*sigma: e=9, sigma=10) -> HOLD */
    nlk_step_in_t in = nominal_step(&r, 0U, seq);
    in.meas_en   = true;
    in.e_err     = 9U;
    in.sigma_ref = 10U;
    nlk_sluice_eval_step(&r, &in);
    print_vec("V05", &r);

    /* V06: Rational -1 LSB Below Lower Boundary (e=8999, sigma=10000) -> OPEN */
    in = nominal_step(&r, 0U, seq++);
    in.meas_en   = true;
    in.e_err     = 8999U;
    in.sigma_ref = 10000U;
    nlk_sluice_eval_step(&r, &in);
    print_vec("V06", &r);

    /* V07: Exact Rational Upper Knife-Edge (10*e == 15*sigma: e=15, sigma=10) -> HOLD */
    in = nominal_step(&r, 1U, seq);
    in.meas_en   = true;
    in.e_err     = 15U;
    in.sigma_ref = 10U;
    nlk_sluice_eval_step(&r, &in);
    print_vec("V07", &r);

    /* V08: Rational +1 LSB Over Upper Boundary (e=15001, sigma=10000) -> KILL (sticky!) */
    in = nominal_step(&r, 1U, seq);
    in.meas_en   = true;
    in.e_err     = 15001U;
    in.sigma_ref = 10000U;
    nlk_sluice_eval_step(&r, &in);
    print_vec("V08", &r);

    /* V09: Sticky KILL Latch Blocks Subsequent Valid Step -> KILL */
    in = nominal_step(&r, 2U, seq);
    nlk_sluice_eval_step(&r, &in);
    print_vec("V09", &r);

    /* V10: Audited L01 Reset Denied When Self-Test Fails -> Remains KILL */
    nlk_sluice_l01_reset(&r, true, false);
    print_vec("V10", &r);

    /* V11: L01 Reset (Self-Test PASS) + Ma'ats Feather Involution Sabotage -> KILL */
    nlk_sluice_l01_reset(&r, true, true);
    in = nominal_step(&r, 0U, seq);
    in.y_cand = (in.y_cand != 1U) ? 1U : 2U; /* != x_in(0), yet breaks E_q(y)==x */
    nlk_sluice_eval_step(&r, &in);
    print_vec("V11", &r);

    /* V12: L01 Reset + Fixed-Point Sabotage (y_cand == x_in == 'K') -> KILL */
    nlk_sluice_l01_reset(&r, true, true);
    in = nominal_step(&r, 10U, seq);
    in.y_cand = 10U;
    nlk_sluice_eval_step(&r, &in);
    print_vec("V12", &r);

    /* V13: L01 Reset + Landauer Floor -1 rJ Violation (3 bits -> 7,956,917 < 7,956,918 rJ) -> KILL */
    nlk_sluice_l01_reset(&r, true, true);
    in = nominal_step(&r, 3U, seq);
    in.bits_erased = 3U;
    in.q_diss_rj   = 3ULL * NLK_LANDAUER_RJ_PER_BIT - 1ULL;
    nlk_sluice_eval_step(&r, &in);
    print_vec("V13", &r);

    /* V14: L01 Reset + Unverified L2_PHYSICAL Profile -> HOLD (0.00 V DC) */
    nlk_sluice_l01_reset(&r, true, true);
    in = nominal_step(&r, 3U, seq);
    in.bits_erased = 3U;
    in.q_diss_rj   = 3ULL * NLK_LANDAUER_RJ_PER_BIT;
    in.l2_profile  = true;
    in.hw_verified = false;
    nlk_sluice_eval_step(&r, &in);
    print_vec("V14", &r);

    /* V15: Exact Landauer Floor + Verified L2_PHYSICAL + W_ext -> OPEN (5.00 V rail_en=1) */
    in = nominal_step(&r, 3U, seq++);
    in.bits_erased = 3U;
    in.q_diss_rj   = 3ULL * NLK_LANDAUER_RJ_PER_BIT;
    in.l2_profile  = true;
    in.hw_verified = true;
    nlk_sluice_eval_step(&r, &in);
    print_vec("V15", &r);

    /* V16: Non-Monotonic Sequence Replay (seq == seq_prev) -> HOLD */
    in = nominal_step(&r, 4U, r.seq_prev);
    nlk_sluice_eval_step(&r, &in);
    print_vec("V16", &r);

    /* V17: Durable-First WAL Failure (!wal_ready) -> HOLD Before Dispatch (q_auth untouched) */
    in = nominal_step(&r, 4U, seq);
    in.wal_ready = false;
    nlk_sluice_eval_step(&r, &in);
    print_vec("V17", &r);

    /* V18: Crash Window Between Commit and Observe (crash_inject=1, l2_profile=1) ->
     *      OUTCOME_UNKNOWN HOLD with actuator_v_en == 0 (never claims 5.00 V!) */
    in = nominal_step(&r, 4U, seq++);
    in.l2_profile   = true;
    in.hw_verified  = true;
    in.crash_inject = true;
    nlk_sluice_eval_step(&r, &in);
    print_vec("V18", &r);

    /* V19: Spatial Coordinate Board Blocked by OUTCOME_UNKNOWN Lock -> HOLD (Seal #2!) */
    {
        uint16_t q0 = r.q_auth_flat;
        uint16_t qc = q0;
        const uint8_t word4[4] = {18U, 19U, 0U, 11U}; /* "STAL" */
        for (uint8_t k = 0U; k < 4U; ++k) {
            uint16_t qp = 0U;
            uint8_t  yc = 0U;
            nlk_layer1_propose(word4[k], qc, nlk_pack_q(3U, 11U, 22U), true, &qp, &yc);
            nlk_sluice_board_load(&r, k, true, word4[k], yc, qp);
            qc = qp;
        }
        nlk_board_eval_in_t bev = {
            nlk_pack_q(3U, 11U, 22U), true, q0, 4U, seq, true, true, false, false, true
        };
        nlk_sluice_board_eval(&r, &bev);
        print_vec("V19", &r);
    }

    /* V20: L01 Reset Clears OUTCOME_UNKNOWN + Incomplete 3-of-4 Coordinate Board -> HOLD */
    nlk_sluice_l01_reset(&r, true, true);
    {
        uint16_t q0 = r.q_auth_flat;
        uint16_t qc = q0;
        const uint8_t word4[4] = {18U, 19U, 0U, 11U};
        for (uint8_t k = 0U; k < 3U; ++k) {
            uint16_t qp = 0U;
            uint8_t  yc = 0U;
            nlk_layer1_propose(word4[k], qc, nlk_pack_q(3U, 11U, 22U), true, &qp, &yc);
            nlk_sluice_board_load(&r, k, true, word4[k], yc, qp);
            qc = qp;
        }
        nlk_board_eval_in_t bev = {
            nlk_pack_q(3U, 11U, 22U), true, q0, 4U, seq, true, true, false, false, true
        };
        nlk_sluice_board_eval(&r, &bev);
        print_vec("V20", &r);
    }

    /* V21: Complete 4-Slot Coordinate Board Without W_ext -> HOLD (One-Way Law!) */
    {
        uint16_t q0 = r.q_auth_flat;
        uint16_t qc = q0;
        const uint8_t word4[4] = {18U, 19U, 0U, 11U};
        for (uint8_t k = 0U; k < 4U; ++k) {
            uint16_t qp = 0U;
            uint8_t  yc = 0U;
            nlk_layer1_propose(word4[k], qc, nlk_pack_q(3U, 11U, 22U), true, &qp, &yc);
            nlk_sluice_board_load(&r, k, true, word4[k], yc, qp);
            qc = qp;
        }
        nlk_board_eval_in_t bev = {
            nlk_pack_q(3U, 11U, 22U), true, q0, 4U, seq, true, true, false, false, false
        };
        nlk_sluice_board_eval(&r, &bev);
        print_vec("V21", &r);
    }

    /* V22: Complete 4-Slot Coordinate Board With W_ext Fits Gauge -> OPEN (q_auth jumps q0->q4!) */
    {
        nlk_board_eval_in_t bev = {
            nlk_pack_q(3U, 11U, 22U), true, r.q_auth_flat, 4U, seq++, true, true, false, false, true
        };
        nlk_sluice_board_eval(&r, &bev);
        print_vec("V22", &r);
    }

    /* V23: Coordinate Board Seam Break on Slot 1 Even With Slot 3 Missing (KILL > HOLD!) -> KILL */
    {
        uint16_t q0 = r.q_auth_flat;
        uint16_t qc = q0;
        const uint8_t word4[4] = {18U, 19U, 0U, 11U};
        for (uint8_t k = 0U; k < 3U; ++k) {
            uint16_t qp = 0U;
            uint8_t  yc = 0U;
            nlk_layer1_propose(word4[k], qc, 0U, true, &qp, &yc);
            uint16_t q_load = (k == 1U) ? nlk_pack_q(9U, 9U, 9U) : qp;
            nlk_sluice_board_load(&r, k, true, word4[k], yc, q_load);
            qc = qp;
        }
        nlk_board_eval_in_t bev = {
            0U, true, q0, 4U, seq, true, true, false, false, true
        };
        nlk_sluice_board_eval(&r, &bev);
        print_vec("V23", &r);
    }

    /* V24: L01 Reset + Valid Commit + Corrupted LIFO Uncompute -> KILL (T12!) */
    nlk_sluice_l01_reset(&r, true, true);
    in = nominal_step(&r, 16U, seq++); /* 'Q' */
    nlk_sluice_eval_step(&r, &in);
    nlk_sluice_lifo_pop(&r, 0U, true, true, true);
    print_vec("V24", &r);

    return 0;
}
