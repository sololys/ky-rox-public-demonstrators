#ifndef NLK_ENIGMA_SLUICE_H
#define NLK_ENIGMA_SLUICE_H

#include <stdbool.h>
#include <stdint.h>

/* ============================================================================
 * KY-Enigma v1.1 -> NLK Consequence Sluice & Spatial Coordinate Board Gauge
 * Arithmetic : Exact integer mod-26 permutations & cross-multiplied rationals
 *              (0 IEEE-754 FP, 0 modulo/division hardware operators).
 * Architecture:
 *   Layer 1 (Phi, 0.00 V DC) : Stateless KyEnigma proposer (propose_only)
 *   Layer 2 (Pi_K -> Omega)  : NlkEnigmaSluice (KILL > HOLD > OPEN, Ma'ats
 *                              Feather roundtrip, SI-2019 277K Landauer floor
 *                              2,652,306 rJ/bit, 8-slot spatial Coordinate
 *                              Board gauge, and 8-deep LIFO phase rewind).
 * ============================================================================ */

#define NLK_LANDAUER_RJ_PER_BIT  (2652306ULL)
#define NLK_MAX_BOARD_SLOTS      (8U)
#define NLK_LIFO_CAPACITY        (8U)

typedef enum {
    NLK_PORT_HOLD = 0, /* 0.00 V DC reversible stasis (q_auth frozen) */
    NLK_PORT_OPEN = 1, /* Witnessed commit / rewind / spatial gauge fit */
    NLK_PORT_KILL = 2  /* 0.00 V DC sticky latch & monitor detachment */
} nlk_port_t;

typedef enum {
    NLK_REASON_OPEN_VERIFIED         = 0,
    NLK_REASON_OPEN_BOARD_GAUGE      = 1,
    NLK_REASON_OPEN_LIFO_REWIND      = 2,
    NLK_REASON_HOLD_MEAS_STALE       = 3,
    NLK_REASON_HOLD_BOUNDARY_BAND    = 4,
    NLK_REASON_HOLD_OUTCOME_UNKNOWN  = 5,
    NLK_REASON_HOLD_AUTH_OR_REPLAY   = 6,
    NLK_REASON_HOLD_UNVERIFIED_HW    = 7,
    NLK_REASON_HOLD_WAL_FAILURE      = 8,
    NLK_REASON_HOLD_INCOMPLETE_BOARD = 9,
    NLK_REASON_HOLD_LIFO_EMPTY       = 10,
    NLK_REASON_KILL_LATCHED          = 11,
    NLK_REASON_KILL_WAL_OR_RING      = 12,
    NLK_REASON_KILL_STATE_OR_INVOL   = 13,
    NLK_REASON_KILL_FIXED_OR_THERMO  = 14,
    NLK_REASON_KILL_BOARD_OR_LIFO    = 15
} nlk_reason_t;

typedef struct {
    uint16_t ring_flat;   /* {ring_l[4:0], ring_m[4:0], ring_r[4:0]} */
    bool     plug_en;     /* true: standard (A,M),(F,I),(N,V); false: identity */
    uint8_t  x_in;        /* 0..25 ('A'..'Z') */
    uint8_t  y_cand;      /* 0..25 ('A'..'Z') */
    uint16_t q_before_flat;
    uint16_t q_prop_flat;
    uint32_t seq_num;
    bool     meas_en;
    bool     meas_stale;
    uint32_t e_err;
    uint32_t sigma_ref;
    uint32_t bits_erased;
    uint64_t q_diss_rj;
    bool     hash_valid;
    bool     wal_ready;
    bool     crash_inject;
    bool     l2_profile;
    bool     hw_verified;
    bool     witness_ext;
} nlk_step_in_t;

typedef struct {
    uint16_t ring_flat;
    bool     plug_en;
    uint16_t q0_flat;
    uint8_t  expected_steps; /* 1..8 */
    uint32_t seq_num;
    bool     hash_valid;
    bool     wal_ready;
    bool     l2_profile;
    bool     hw_verified;
    bool     witness_ext;
} nlk_board_eval_in_t;

typedef struct {
    bool     present;
    uint8_t  x_in;
    uint8_t  y_cand;
    uint16_t q_coord_flat;
} nlk_board_slot_t;

typedef struct {
    uint16_t q_bef;
    uint16_t q_prop;
    uint8_t  x_in;
    uint8_t  y_cand;
} nlk_lifo_entry_t;

typedef struct {
    uint64_t         cycle;
    uint32_t         reset_epoch;
    uint32_t         seq_prev;
    uint16_t         q_auth_flat;
    bool             kill_latched;
    bool             outcome_unknown_hold;
    bool             monitor_coupled;
    bool             actuator_v_en;
    nlk_port_t       last_port;
    nlk_reason_t     last_reason;
    uint8_t          last_y_out;

    /* 8-slot spatial Coordinate Board staging registers */
    uint8_t          board_mask;
    uint8_t          board_cnt;
    bool             board_seq_err;
    nlk_board_slot_t board_slots[NLK_MAX_BOARD_SLOTS];

    /* 8-deep reversible phase-memory LIFO stack */
    uint8_t          lifo_depth;
    nlk_lifo_entry_t lifo[NLK_LIFO_CAPACITY];
} nlk_sluice_reg_t;

static inline uint16_t nlk_pack_q(uint8_t ql, uint8_t qm, uint8_t qr) {
    return (uint16_t)((((uint16_t)(ql & 0x1FU)) << 10) |
                      (((uint16_t)(qm & 0x1FU)) << 5)  |
                      ((uint16_t)(qr & 0x1FU)));
}

static inline void nlk_unpack_q(uint16_t flat, uint8_t *ql, uint8_t *qm, uint8_t *qr) {
    *ql = (uint8_t)((flat >> 10) & 0x1FU);
    *qm = (uint8_t)((flat >> 5)  & 0x1FU);
    *qr = (uint8_t)(flat & 0x1FU);
}

static inline bool nlk_q_valid(uint16_t flat) {
    uint8_t ql, qm, qr;
    nlk_unpack_q(flat, &ql, &qm, &qr);
    return (flat <= 0x7FFFU) && (ql < 26U) && (qm < 26U) && (qr < 26U);
}

static inline uint8_t nlk_mod26_add(uint8_t a, uint8_t b) {
    uint8_t s = (uint8_t)(a + b);
    return (s >= 26U) ? (uint8_t)(s - 26U) : s;
}

static inline uint8_t nlk_mod26_sub(uint8_t a, uint8_t b) {
    return (a >= b) ? (uint8_t)(a - b) : (uint8_t)(a + 26U - b);
}

/* Notch-cascade stepping (notches: Rotor I='Q'(16), Rotor II='E'(4), Rotor III='V'(21)) */
static inline uint16_t nlk_propose_next_q(uint16_t q_flat) {
    uint8_t ql, qm, qr;
    nlk_unpack_q(q_flat, &ql, &qm, &qr);
    bool mid_notch   = (qm == 4U);
    bool right_notch = (qr == 21U);

    uint8_t nl = mid_notch ? ((ql == 25U) ? 0U : (uint8_t)(ql + 1U)) : ql;
    uint8_t nm = (mid_notch || right_notch) ? ((qm == 25U) ? 0U : (uint8_t)(qm + 1U)) : qm;
    uint8_t nr = (qr == 25U) ? 0U : (uint8_t)(qr + 1U);
    return nlk_pack_q(nl, nm, nr);
}

/* Exact fixed-state conjugated involution E_q(x) = A_q^-1(R(A_q(x))) on 0..25 */
static inline uint8_t nlk_eval_enigma_fixed(
    uint8_t x_idx, uint16_t q_flat, uint16_t ring_flat, bool plug_en
) {
    static const uint8_t r1_fwd[26] = { 4U, 10U, 12U, 5U, 11U, 6U, 3U, 16U, 21U, 25U, 13U, 19U, 14U, 22U, 24U, 7U, 23U, 20U, 18U, 15U, 0U, 8U, 1U, 17U, 2U, 9U };
    static const uint8_t r2_fwd[26] = { 0U, 9U, 3U, 10U, 18U, 8U, 17U, 20U, 23U, 1U, 11U, 7U, 22U, 19U, 12U, 2U, 16U, 6U, 25U, 13U, 15U, 24U, 5U, 21U, 14U, 4U };
    static const uint8_t r3_fwd[26] = { 1U, 3U, 5U, 7U, 9U, 11U, 2U, 15U, 17U, 19U, 23U, 21U, 25U, 13U, 24U, 4U, 8U, 22U, 6U, 0U, 10U, 12U, 20U, 18U, 16U, 14U };
    static const uint8_t r1_inv[26] = { 20U, 22U, 24U, 6U, 0U, 3U, 5U, 15U, 21U, 25U, 1U, 4U, 2U, 10U, 12U, 19U, 7U, 23U, 18U, 11U, 17U, 8U, 13U, 16U, 14U, 9U };
    static const uint8_t r2_inv[26] = { 0U, 9U, 15U, 2U, 25U, 22U, 17U, 11U, 5U, 1U, 3U, 10U, 14U, 19U, 24U, 20U, 16U, 6U, 4U, 13U, 7U, 23U, 12U, 8U, 21U, 18U };
    static const uint8_t r3_inv[26] = { 19U, 0U, 6U, 1U, 15U, 2U, 18U, 3U, 16U, 4U, 20U, 5U, 21U, 13U, 25U, 7U, 24U, 8U, 23U, 9U, 22U, 11U, 17U, 10U, 14U, 12U };
    static const uint8_t ukw_t[26]  = { 24U, 17U, 20U, 7U, 16U, 18U, 11U, 3U, 15U, 23U, 13U, 6U, 14U, 10U, 12U, 8U, 4U, 1U, 5U, 25U, 2U, 22U, 21U, 9U, 0U, 19U };
    static const uint8_t plug_t[26] = { 12U, 1U, 2U, 3U, 4U, 8U, 6U, 7U, 5U, 9U, 10U, 11U, 0U, 21U, 14U, 15U, 16U, 17U, 18U, 19U, 20U, 13U, 22U, 23U, 24U, 25U };

    uint8_t ql, qm, qr, rl, rm, rr;
    nlk_unpack_q(q_flat, &ql, &qm, &qr);
    nlk_unpack_q(ring_flat, &rl, &rm, &rr);

    uint8_t sh0 = nlk_mod26_sub(ql, rl);
    uint8_t sh1 = nlk_mod26_sub(qm, rm);
    uint8_t sh2 = nlk_mod26_sub(qr, rr);

    uint8_t c = (uint8_t)(x_idx & 0x1FU);
    if (plug_en) { c = plug_t[c]; }

    c = nlk_mod26_sub(r3_fwd[nlk_mod26_add(c, sh2)], sh2);
    c = nlk_mod26_sub(r2_fwd[nlk_mod26_add(c, sh1)], sh1);
    c = nlk_mod26_sub(r1_fwd[nlk_mod26_add(c, sh0)], sh0);

    c = ukw_t[c];

    c = nlk_mod26_sub(r1_inv[nlk_mod26_add(c, sh0)], sh0);
    c = nlk_mod26_sub(r2_inv[nlk_mod26_add(c, sh1)], sh1);
    c = nlk_mod26_sub(r3_inv[nlk_mod26_add(c, sh2)], sh2);

    if (plug_en) { c = plug_t[c]; }
    return c;
}

/* Stateless Layer-1 proposer (Phi, 0.00 V DC — zero write access to nlk_sluice_reg_t) */
static inline void nlk_layer1_propose(
    uint8_t x_in, uint16_t q_auth_flat, uint16_t ring_flat, bool plug_en,
    uint16_t *q_prop_out, uint8_t *y_cand_out
) {
    uint16_t qp = nlk_propose_next_q(q_auth_flat);
    *q_prop_out = qp;
    *y_cand_out = nlk_eval_enigma_fixed(x_in, qp, ring_flat, plug_en);
}

static inline void nlk_sluice_init(nlk_sluice_reg_t *r) {
    if (r == 0) { return; }
    r->cycle                = 0ULL;
    r->reset_epoch          = 0U;
    r->seq_prev             = 0U;
    r->q_auth_flat          = 0U;
    r->kill_latched         = false;
    r->outcome_unknown_hold = false;
    r->monitor_coupled      = true;
    r->actuator_v_en        = false;
    r->last_port            = NLK_PORT_HOLD;
    r->last_reason          = NLK_REASON_HOLD_AUTH_OR_REPLAY;
    r->last_y_out           = 0U;
    r->board_mask           = 0U;
    r->board_cnt            = 0U;
    r->board_seq_err        = false;
    r->lifo_depth           = 0U;
    for (uint8_t i = 0U; i < NLK_MAX_BOARD_SLOTS; ++i) {
        r->board_slots[i].present      = false;
        r->board_slots[i].x_in         = 0U;
        r->board_slots[i].y_cand       = 0U;
        r->board_slots[i].q_coord_flat = 0U;
    }
    for (uint8_t i = 0U; i < NLK_LIFO_CAPACITY; ++i) {
        r->lifo[i].q_bef  = 0U;
        r->lifo[i].q_prop = 0U;
        r->lifo[i].x_in   = 0U;
        r->lifo[i].y_cand = 0U;
    }
}

static inline uint8_t nlk_status_byte(const nlk_sluice_reg_t *r) {
    uint8_t b = (uint8_t)((uint8_t)r->last_port & 0x03U);
    if (r->actuator_v_en)        { b |= 0x04U; }
    if (r->monitor_coupled)      { b |= 0x08U; }
    if (r->kill_latched)         { b |= 0x10U; }
    if (r->outcome_unknown_hold) { b |= 0x20U; }
    if (r->lifo_depth > 0U)      { b |= 0x40U; }
    return b;
}

static inline void nlk_push_lifo(
    nlk_sluice_reg_t *r, uint16_t q_bef, uint16_t q_prop, uint8_t x_in, uint8_t y_cand
) {
    for (int i = (int)NLK_LIFO_CAPACITY - 1; i > 0; --i) {
        r->lifo[i] = r->lifo[i - 1];
    }
    r->lifo[0].q_bef  = q_bef;
    r->lifo[0].q_prop = q_prop;
    r->lifo[0].x_in   = x_in;
    r->lifo[0].y_cand = y_cand;
    if (r->lifo_depth < NLK_LIFO_CAPACITY) {
        r->lifo_depth = (uint8_t)(r->lifo_depth + 1U);
    }
}

static inline nlk_port_t nlk_latch_kill(nlk_sluice_reg_t *r, nlk_reason_t reason) {
    r->kill_latched    = true;
    r->monitor_coupled = false;
    r->actuator_v_en   = false;
    r->last_port       = NLK_PORT_KILL;
    r->last_reason     = reason;
    r->last_y_out      = 0U;
    return NLK_PORT_KILL;
}

static inline nlk_port_t nlk_emit_hold(nlk_sluice_reg_t *r, nlk_reason_t reason) {
    r->monitor_coupled = true;
    r->actuator_v_en   = false;
    r->last_port       = NLK_PORT_HOLD;
    r->last_reason     = reason;
    r->last_y_out      = 0U;
    return NLK_PORT_HOLD;
}

/* Mode 4: Audited Level 01 recovery (requires both l01_witness_ok and selftest_ok) */
static inline nlk_port_t nlk_sluice_l01_reset(
    nlk_sluice_reg_t *r, bool l01_witness_ok, bool selftest_ok
) {
    if (r == 0) { return NLK_PORT_KILL; }
    r->cycle += 1ULL;
    if (!l01_witness_ok || !selftest_ok) {
        if (r->kill_latched) {
            return nlk_latch_kill(r, NLK_REASON_KILL_LATCHED);
        }
        return nlk_emit_hold(r, NLK_REASON_HOLD_AUTH_OR_REPLAY);
    }
    r->reset_epoch          += 1U;
    r->kill_latched          = false;
    r->outcome_unknown_hold  = false;
    r->monitor_coupled       = true;
    r->actuator_v_en         = false;
    r->last_port             = NLK_PORT_HOLD;
    r->last_reason           = NLK_REASON_HOLD_AUTH_OR_REPLAY;
    r->last_y_out            = 0U;
    r->lifo_depth            = 0U;
    r->board_mask            = 0U;
    r->board_cnt             = 0U;
    r->board_seq_err         = false;
    return NLK_PORT_HOLD;
}

/* Mode 1: Single-step evaluation at cut ⬡ -> ◉ -> 1 (constant 24 cycles) */
static inline nlk_port_t nlk_sluice_eval_step(
    nlk_sluice_reg_t *r, const nlk_step_in_t *in
) {
    if (r == 0 || in == 0) { return NLK_PORT_KILL; }
    r->cycle += 25ULL;

    if (r->kill_latched) {
        return nlk_latch_kill(r, NLK_REASON_KILL_LATCHED);
    }
    if (!in->hash_valid || !nlk_q_valid(in->ring_flat)) {
        return nlk_latch_kill(r, NLK_REASON_KILL_WAL_OR_RING);
    }
    if ((in->q_before_flat & 0x7FFFU) != r->q_auth_flat) {
        return nlk_latch_kill(r, NLK_REASON_KILL_STATE_OR_INVOL);
    }
    if (in->x_in >= 26U || in->y_cand >= 26U || !nlk_q_valid(in->q_prop_flat)) {
        return nlk_latch_kill(r, NLK_REASON_KILL_STATE_OR_INVOL);
    }
    if (in->y_cand == in->x_in) {
        return nlk_latch_kill(r, NLK_REASON_KILL_FIXED_OR_THERMO);
    }

    uint16_t exp_q = nlk_propose_next_q(r->q_auth_flat);
    uint8_t  rt_x  = nlk_eval_enigma_fixed(in->y_cand, in->q_prop_flat, in->ring_flat, in->plug_en);
    if ((in->q_prop_flat != exp_q) || (rt_x != in->x_in)) {
        return nlk_latch_kill(r, NLK_REASON_KILL_STATE_OR_INVOL);
    }

    uint64_t landauer_req = (uint64_t)in->bits_erased * NLK_LANDAUER_RJ_PER_BIT;
    if (in->q_diss_rj < landauer_req) {
        return nlk_latch_kill(r, NLK_REASON_KILL_FIXED_OR_THERMO);
    }

    if (in->meas_en && (in->sigma_ref > 0U) && (!in->meas_stale)) {
        if ((10ULL * (uint64_t)in->e_err) > (15ULL * (uint64_t)in->sigma_ref)) {
            return nlk_latch_kill(r, NLK_REASON_KILL_FIXED_OR_THERMO);
        }
    }

    if (in->meas_en) {
        if ((in->sigma_ref == 0U) || in->meas_stale) {
            return nlk_emit_hold(r, NLK_REASON_HOLD_MEAS_STALE);
        }
        if ((10ULL * (uint64_t)in->e_err) >= (9ULL * (uint64_t)in->sigma_ref)) {
            return nlk_emit_hold(r, NLK_REASON_HOLD_BOUNDARY_BAND);
        }
    }

    if (r->outcome_unknown_hold) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_OUTCOME_UNKNOWN);
    }

    if (!in->witness_ext || (in->seq_num <= r->seq_prev) || (in->seq_num == 0xFFFFFFFFU)) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_AUTH_OR_REPLAY);
    }

    if (in->l2_profile && !in->hw_verified) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_UNVERIFIED_HW);
    }

    if (!in->wal_ready) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_WAL_FAILURE);
    }

    /* Step ◉ committed durably */
    uint16_t prev_q = r->q_auth_flat;
    r->q_auth_flat  = in->q_prop_flat;
    r->seq_prev     = in->seq_num;
    nlk_push_lifo(r, prev_q, in->q_prop_flat, in->x_in, in->y_cand);

    if (in->crash_inject) {
        r->outcome_unknown_hold = true;
        return nlk_emit_hold(r, NLK_REASON_HOLD_OUTCOME_UNKNOWN);
    }

    r->monitor_coupled = true;
    r->actuator_v_en   = in->l2_profile ? true : false;
    r->last_port       = NLK_PORT_OPEN;
    r->last_reason     = NLK_REASON_OPEN_VERIFIED;
    r->last_y_out      = in->y_cand;
    return NLK_PORT_OPEN;
}

/* Mode 2a: Load one slot (0..7) onto the spatial steel Coordinate Board (1 cycle) */
static inline void nlk_sluice_board_load(
    nlk_sluice_reg_t *r, uint8_t slot_idx, bool present,
    uint8_t x_in, uint8_t y_cand, uint16_t q_coord_flat
) {
    if (r == 0) { return; }
    r->cycle += 1ULL;
    uint8_t idx = (uint8_t)(slot_idx & 0x07U);
    uint8_t bit = (uint8_t)(1U << idx);
    if (idx == 0U) {
        r->board_mask    = bit;
        r->board_cnt     = 1U;
        r->board_seq_err = false;
    } else {
        if (r->board_mask != (uint8_t)(bit - 1U)) {
            r->board_seq_err = true;
        }
        r->board_mask = (uint8_t)(r->board_mask | bit);
        if (r->board_cnt < NLK_MAX_BOARD_SLOTS) {
            r->board_cnt = (uint8_t)(r->board_cnt + 1U);
        } else {
            r->board_seq_err = true;
        }
    }
    r->board_slots[idx].present      = present;
    r->board_slots[idx].x_in         = (uint8_t)(x_in & 0x1FU);
    r->board_slots[idx].y_cand       = (uint8_t)(y_cand & 0x1FU);
    r->board_slots[idx].q_coord_flat = (uint16_t)(q_coord_flat & 0x7FFFU);
}

/* Mode 2b: Evaluate the spatial Coordinate Board gauge (constant 82 cycles) */
static inline nlk_port_t nlk_sluice_board_eval(
    nlk_sluice_reg_t *r, const nlk_board_eval_in_t *in
) {
    if (r == 0 || in == 0) { return NLK_PORT_KILL; }
    r->cycle += 130ULL;

    if (r->kill_latched) {
        return nlk_latch_kill(r, NLK_REASON_KILL_LATCHED);
    }
    if (!in->hash_valid || !nlk_q_valid(in->ring_flat)) {
        return nlk_latch_kill(r, NLK_REASON_KILL_WAL_OR_RING);
    }
    if (r->board_seq_err || (in->expected_steps == 0U) ||
        (in->expected_steps > NLK_MAX_BOARD_SLOTS) ||
        ((in->q0_flat & 0x7FFFU) != r->q_auth_flat) ||
        (r->board_cnt > in->expected_steps)) {
        return nlk_latch_kill(r, NLK_REASON_KILL_BOARD_OR_LIFO);
    }

    uint16_t prev_q        = r->q_auth_flat;
    bool     missing_piece = (r->board_cnt < in->expected_steps);
    uint8_t  last_y        = 0U;

    for (uint8_t i = 0U; i < r->board_cnt; ++i) {
        const nlk_board_slot_t *sl = &r->board_slots[i];
        uint16_t exp_q = nlk_propose_next_q(prev_q);
        if (!nlk_q_valid(sl->q_coord_flat) || (sl->q_coord_flat != exp_q)) {
            return nlk_latch_kill(r, NLK_REASON_KILL_BOARD_OR_LIFO);
        }
        if (!sl->present) {
            missing_piece = true;
            prev_q = sl->q_coord_flat;
            continue;
        }
        if (sl->x_in >= 26U || sl->y_cand >= 26U || sl->y_cand == sl->x_in) {
            return nlk_latch_kill(r, NLK_REASON_KILL_BOARD_OR_LIFO);
        }
        uint8_t rt_x = nlk_eval_enigma_fixed(sl->y_cand, sl->q_coord_flat, in->ring_flat, in->plug_en);
        if (rt_x != sl->x_in) {
            return nlk_latch_kill(r, NLK_REASON_KILL_BOARD_OR_LIFO);
        }
        prev_q = sl->q_coord_flat;
        last_y = sl->y_cand;
    }

    if (r->outcome_unknown_hold) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_OUTCOME_UNKNOWN);
    }
    if (missing_piece) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_INCOMPLETE_BOARD);
    }
    if (!in->witness_ext || (in->seq_num <= r->seq_prev) || (in->seq_num == 0xFFFFFFFFU)) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_AUTH_OR_REPLAY);
    }
    if (in->l2_profile && !in->hw_verified) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_UNVERIFIED_HW);
    }
    if (!in->wal_ready) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_WAL_FAILURE);
    }

    r->q_auth_flat     = prev_q;
    r->seq_prev        = in->seq_num;
    r->lifo_depth      = 0U;
    r->monitor_coupled = true;
    r->actuator_v_en   = in->l2_profile ? true : false;
    r->last_port       = NLK_PORT_OPEN;
    r->last_reason     = NLK_REASON_OPEN_BOARD_GAUGE;
    r->last_y_out      = last_y;
    return NLK_PORT_OPEN;
}

/* Mode 3: Reversible LIFO phase-memory uncompute & q_auth rewind (constant 12 cycles) */
static inline nlk_port_t nlk_sluice_lifo_pop(
    nlk_sluice_reg_t *r, uint16_t ring_flat, bool plug_en,
    bool hash_valid, bool lifo_tamper_inject
) {
    if (r == 0) { return NLK_PORT_KILL; }
    r->cycle += 18ULL;

    if (r->kill_latched) {
        return nlk_latch_kill(r, NLK_REASON_KILL_LATCHED);
    }
    if (!hash_valid || !nlk_q_valid(ring_flat)) {
        return nlk_latch_kill(r, NLK_REASON_KILL_WAL_OR_RING);
    }
    if (r->outcome_unknown_hold) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_OUTCOME_UNKNOWN);
    }
    if (r->lifo_depth == 0U) {
        return nlk_emit_hold(r, NLK_REASON_HOLD_LIFO_EMPTY);
    }

    nlk_lifo_entry_t top = r->lifo[0];
    uint8_t rec_x = nlk_eval_enigma_fixed(top.y_cand, top.q_prop, ring_flat, plug_en);
    if (lifo_tamper_inject || (top.q_prop != r->q_auth_flat) ||
        (top.y_cand == top.x_in) || (rec_x != top.x_in)) {
        return nlk_latch_kill(r, NLK_REASON_KILL_BOARD_OR_LIFO);
    }

    /* Exact reversible rewind: q_auth steps back to top.q_bef at 0.00 V DC */
    r->q_auth_flat = top.q_bef;
    for (uint8_t i = 0U; i + 1U < NLK_LIFO_CAPACITY; ++i) {
        r->lifo[i] = r->lifo[i + 1U];
    }
    r->lifo[NLK_LIFO_CAPACITY - 1U].q_bef  = 0U;
    r->lifo[NLK_LIFO_CAPACITY - 1U].q_prop = 0U;
    r->lifo[NLK_LIFO_CAPACITY - 1U].x_in   = 0U;
    r->lifo[NLK_LIFO_CAPACITY - 1U].y_cand = 0U;
    r->lifo_depth      = (uint8_t)(r->lifo_depth - 1U);
    r->monitor_coupled = true;
    r->actuator_v_en   = false;
    r->last_port       = NLK_PORT_OPEN;
    r->last_reason     = NLK_REASON_OPEN_LIFO_REWIND;
    r->last_y_out      = rec_x;
    return NLK_PORT_OPEN;
}

#endif /* NLK_ENIGMA_SLUICE_H */
