#ifndef BELL_KY_SLUICE_H
#define BELL_KY_SLUICE_H

#include <stdbool.h>
#include <stdint.h>

/* ============================================================================
 * L2_GATE :: 29.KY Bell-KY Zero-Float Consequence Sluice (Theta_{Bell-KY})
 * Arithmetic : Pure 64-bit / portable split-128 integer logic (0 IEEE-754 FP)
 * ============================================================================ */

#define BELL_KY_MAX_PULSES      (1ULL << 38)
#define BELL_KY_MASK_40         (0xFFFFFFFFFFULL)
#define BELL_KY_SI_C_M_PER_S    (299792458ULL)
#define BELL_KY_TWO_E9_PS_MM    (2000000000ULL)

typedef enum {
    BKY_PORT_HOLD = 0, /* Inner reversible chamber: 0.00 V DC, monitor coupled */
    BKY_PORT_OPEN = 1, /* Witnessed L3 candidate capsule: 5.00 V DC */
    BKY_PORT_KILL = 2  /* Monitor detachment & hardware latch: 0.00 V air-gap */
} bky_port_t;

typedef enum {
    BKY_REASON_OPEN_L3_WITNESSED      = 0,
    BKY_REASON_HOLD_QM_NULL_CONFIRMED = 1,
    BKY_REASON_HOLD_L1_TOMO_SHIFT     = 2,
    BKY_REASON_HOLD_OPEN_LOOP_L1      = 3,
    BKY_REASON_HOLD_NO_QUORUM_OR_WIT  = 4,
    BKY_REASON_KILL_LATCHED           = 5,
    BKY_REASON_KILL_SHOT_COUNT        = 6,
    BKY_REASON_KILL_HASH_CHAIN        = 7,
    BKY_REASON_KILL_LIGHTCONE         = 8,
    BKY_REASON_KILL_NO_SIGNALLING     = 9,
    BKY_REASON_KILL_SETTING_CORR      = 10
} bky_reason_t;

typedef struct {
    uint64_t hi;
    uint64_t lo;
} bky_u128_t;

typedef struct {
    uint64_t n_pulses; /* Pulses per (m,n) setting in (0, 2^38] */
    uint64_t pp;
    uint64_t pm;
    uint64_t mp;
    uint64_t mm;
} bky_arm_counts_t;

typedef struct {
    uint64_t   n_pulses;
    uint32_t   delta_k_cycles;
    uint32_t   t_clk_ps;
    uint32_t   dist_mm;
    uint64_t   tau_ns;
    uint32_t   setting_corr_abs;
    uint32_t   tau_indep;
    uint32_t   tomo_frob_diff_sq;
    uint32_t   tau_tomo_sq;
    bky_u128_t tau_diff_sq;
    uint16_t   replicated_series;
    uint16_t   min_series;
    bool       hash_valid;
    bool       involution_closed;
    bool       witness_ext;
} bky_eval_in_t;

typedef struct {
    uint64_t     cycle;
    uint32_t     reset_epoch;
    bool         kill_latched;
    bool         monitor_coupled;
    bool         actuator_v_en;
    bky_port_t   last_port;
    bky_reason_t last_reason;
    bool         bell_violated_k1;
    bool         super_tsirelson;
    bky_u128_t   last_s1_sq;
    bky_u128_t   last_s2_sq;

    /* 8-slot streaming accumulators ({arm_idx, mn_idx} in 0..7) */
    uint8_t      loaded_mask;
    bool         shot_err_accum;
    uint64_t     n_pulses_latched;
    int64_t      sigma_k1;
    int64_t      sigma_k2;
    uint64_t     pa;
    uint64_t     pb0;
    uint64_t     pb1;
    uint64_t     max_ns_dev;
} bky_sluice_reg_t;

static inline bky_u128_t bky_u128_mul64(uint64_t a, uint64_t b) {
    uint64_t a_lo = a & 0xFFFFFFFFULL, a_hi = a >> 32;
    uint64_t b_lo = b & 0xFFFFFFFFULL, b_hi = b >> 32;

    uint64_t p0 = a_lo * b_lo;
    uint64_t p1 = a_lo * b_hi;
    uint64_t p2 = a_hi * b_lo;
    uint64_t p3 = a_hi * b_hi;

    uint64_t mid = (p0 >> 32) + (p1 & 0xFFFFFFFFULL) + (p2 & 0xFFFFFFFFULL);
    bky_u128_t out;
    out.hi = p3 + (p1 >> 32) + (p2 >> 32) + (mid >> 32);
    out.lo = (mid << 32) | (p0 & 0xFFFFFFFFULL);
    return out;
}

static inline bky_u128_t bky_u128_shl(bky_u128_t x, unsigned int shift) {
    bky_u128_t out;
    if (shift == 0U) {
        return x;
    }
    out.hi = (x.hi << shift) | (x.lo >> (64U - shift));
    out.lo = (x.lo << shift);
    return out;
}

static inline bool bky_u128_lt(bky_u128_t a, bky_u128_t b) {
    return (a.hi < b.hi) || (a.hi == b.hi && a.lo < b.lo);
}

static inline bool bky_u128_gt(bky_u128_t a, bky_u128_t b) {
    return bky_u128_lt(b, a);
}

static inline bky_u128_t bky_u128_abs_diff(bky_u128_t a, bky_u128_t b) {
    bky_u128_t big = bky_u128_lt(a, b) ? b : a;
    bky_u128_t sml = bky_u128_lt(a, b) ? a : b;
    bky_u128_t out;
    out.lo = big.lo - sml.lo;
    out.hi = big.hi - sml.hi - ((big.lo < sml.lo) ? 1ULL : 0ULL);
    return out;
}

static inline uint64_t bky_abs_diff_u64(uint64_t a, uint64_t b) {
    return (a >= b) ? (a - b) : (b - a);
}

static inline uint64_t bky_max_u64(uint64_t a, uint64_t b) {
    return (a >= b) ? a : b;
}

static inline uint64_t bky_abs_i64(int64_t x) {
    return (x >= 0) ? (uint64_t)x : (uint64_t)(-(x + 1)) + 1ULL;
}

static inline void bky_sluice_init(bky_sluice_reg_t *r) {
    if (r == 0) {
        return;
    }
    r->cycle            = 0ULL;
    r->reset_epoch      = 0U;
    r->kill_latched     = false;
    r->monitor_coupled  = true;
    r->actuator_v_en    = false;
    r->last_port        = BKY_PORT_HOLD;
    r->last_reason      = BKY_REASON_HOLD_QM_NULL_CONFIRMED;
    r->bell_violated_k1 = false;
    r->super_tsirelson  = false;
    r->last_s1_sq.hi    = 0ULL;
    r->last_s1_sq.lo    = 0ULL;
    r->last_s2_sq.hi    = 0ULL;
    r->last_s2_sq.lo    = 0ULL;
    r->loaded_mask      = 0U;
    r->shot_err_accum   = false;
    r->n_pulses_latched = 0ULL;
    r->sigma_k1         = 0LL;
    r->sigma_k2         = 0LL;
    r->pa               = 0ULL;
    r->pb0              = 0ULL;
    r->pb1              = 0ULL;
    r->max_ns_dev       = 0ULL;
}

static inline uint8_t bky_status_byte(const bky_sluice_reg_t *r) {
    uint8_t b = (uint8_t)((uint8_t)r->last_port & 0x03U);
    if (r->actuator_v_en)    { b |= 0x04U; }
    if (r->monitor_coupled)  { b |= 0x08U; }
    if (r->kill_latched)     { b |= 0x10U; }
    if (r->bell_violated_k1) { b |= 0x20U; }
    if (r->super_tsirelson)  { b |= 0x40U; }
    return b;
}

static inline bool bky_arm_counts_ok(
    uint64_t n_pulses, uint64_t pp, uint64_t pm, uint64_t mp, uint64_t mm
) {
    if (n_pulses == 0ULL || n_pulses > BELL_KY_MAX_PULSES) {
        return false;
    }
    if (pp > n_pulses || pm > n_pulses || mp > n_pulses || mm > n_pulses) {
        return false;
    }
    return ((pp + pm + mp + mm) == n_pulses);
}

/* Stream one (arm_idx in {0,1}, mn_idx in {0..3}) block */
static inline void bky_sluice_load_setting(
    bky_sluice_reg_t *r, uint8_t arm_idx, uint8_t mn_idx, const bky_arm_counts_t *c
) {
    if (r == 0 || c == 0) {
        return;
    }
    r->cycle += 1ULL;
    uint8_t arm  = (uint8_t)(arm_idx & 0x01U);
    uint8_t idx  = (uint8_t)(mn_idx & 0x03U);
    uint8_t slot = (uint8_t)((arm << 2) | idx);
    uint8_t bit  = (uint8_t)(1U << slot);

    uint64_t np = c->n_pulses & BELL_KY_MASK_40;
    uint64_t pp = c->pp & BELL_KY_MASK_40;
    uint64_t pm = c->pm & BELL_KY_MASK_40;
    uint64_t mp = c->mp & BELL_KY_MASK_40;
    uint64_t mm = c->mm & BELL_KY_MASK_40;

    bool ok_arm = bky_arm_counts_ok(np, pp, pm, mp, mm);
    uint64_t cur_pa = pp + pm;
    uint64_t cur_pb = pp + mp;
    int64_t c_val = (idx == 3U)
        ? ((int64_t)(pm + mp) - (int64_t)(pp + mm))
        : ((int64_t)(pp + mm) - (int64_t)(pm + mp));

    if (slot == 0U) {
        r->loaded_mask      = bit;
        r->shot_err_accum   = !ok_arm;
        r->n_pulses_latched = np;
        r->max_ns_dev       = 0ULL;
        r->sigma_k1         = c_val;
        r->pa               = cur_pa;
        r->pb0              = cur_pb;
        return;
    }

    if ((r->loaded_mask != (uint8_t)(bit - 1U)) || (np != r->n_pulses_latched) || (!ok_arm)) {
        r->shot_err_accum = true;
    }
    r->loaded_mask = (uint8_t)(r->loaded_mask | bit);

    if (idx == 0U) {
        r->sigma_k2 = c_val;
        r->pa       = cur_pa;
        r->pb0      = cur_pb;
        return;
    }

    if (arm == 0U) {
        r->sigma_k1 += c_val;
    } else {
        r->sigma_k2 += c_val;
    }

    if (idx == 1U) {
        r->max_ns_dev = bky_max_u64(r->max_ns_dev, bky_abs_diff_u64(r->pa, cur_pa));
        r->pb1        = cur_pb;
    } else if (idx == 2U) {
        r->max_ns_dev = bky_max_u64(r->max_ns_dev, bky_abs_diff_u64(r->pb0, cur_pb));
        r->pa         = cur_pa;
    } else {
        uint64_t da = bky_abs_diff_u64(r->pa, cur_pa);
        uint64_t db = bky_abs_diff_u64(r->pb1, cur_pb);
        r->max_ns_dev = bky_max_u64(r->max_ns_dev, bky_max_u64(da, db));
    }
}

static inline void bky_latch_kill(bky_sluice_reg_t *r, bky_reason_t reason) {
    r->kill_latched     = true;
    r->monitor_coupled  = false;
    r->actuator_v_en    = false;
    r->last_port        = BKY_PORT_KILL;
    r->last_reason      = reason;
    r->bell_violated_k1 = false;
    r->super_tsirelson  = false;
    r->last_s1_sq.hi    = 0ULL;
    r->last_s1_sq.lo    = 0ULL;
    r->last_s2_sq.hi    = 0ULL;
    r->last_s2_sq.lo    = 0ULL;
}

static inline bky_port_t bky_sluice_l01_reset(
    bky_sluice_reg_t *r, bool l01_witness_ok
) {
    if (r == 0) {
        return BKY_PORT_KILL;
    }
    r->cycle += 1ULL;
    if (!l01_witness_ok) {
        if (r->kill_latched) {
            r->last_port   = BKY_PORT_KILL;
            r->last_reason = BKY_REASON_KILL_LATCHED;
            return BKY_PORT_KILL;
        }
        r->actuator_v_en = false;
        r->last_port     = BKY_PORT_HOLD;
        r->last_reason   = BKY_REASON_HOLD_NO_QUORUM_OR_WIT;
        return BKY_PORT_HOLD;
    }
    r->reset_epoch     += 1U;
    r->kill_latched     = false;
    r->monitor_coupled  = true;
    r->actuator_v_en    = false;
    r->last_port        = BKY_PORT_HOLD;
    r->last_reason      = BKY_REASON_HOLD_NO_QUORUM_OR_WIT;
    r->bell_violated_k1 = false;
    r->super_tsirelson  = false;
    r->last_s1_sq.hi    = 0ULL;
    r->last_s1_sq.lo    = 0ULL;
    r->last_s2_sq.hi    = 0ULL;
    r->last_s2_sq.lo    = 0ULL;
    return BKY_PORT_HOLD;
}

static inline bky_port_t bky_sluice_eval(
    bky_sluice_reg_t *r, const bky_eval_in_t *in
) {
    if (r == 0 || in == 0) {
        return BKY_PORT_KILL;
    }
    /* Constant-time 338-cycle hardware evaluation (1 start + 7x48 serial MAC + 1 commit) */
    r->cycle += 338ULL;

    if (r->kill_latched) {
        bky_latch_kill(r, BKY_REASON_KILL_LATCHED);
        return BKY_PORT_KILL;
    }

    uint64_t np     = in->n_pulses & BELL_KY_MASK_40;
    uint64_t tau_ns = in->tau_ns & BELL_KY_MASK_40;

    if (np == 0ULL || np > BELL_KY_MAX_PULSES || in->min_series == 0U ||
        r->loaded_mask != 0xFFU || r->shot_err_accum || np != r->n_pulses_latched) {
        bky_latch_kill(r, BKY_REASON_KILL_SHOT_COUNT);
        return BKY_PORT_KILL;
    }

    if (!in->hash_valid) {
        bky_latch_kill(r, BKY_REASON_KILL_HASH_CHAIN);
        return BKY_PORT_KILL;
    }

    if (in->delta_k_cycles == 0U || in->t_clk_ps == 0U || in->dist_mm == 0U) {
        bky_latch_kill(r, BKY_REASON_KILL_LIGHTCONE);
        return BKY_PORT_KILL;
    }
    uint64_t dt_ps = (uint64_t)in->delta_k_cycles * (uint64_t)in->t_clk_ps;
    bky_u128_t lc_lhs = bky_u128_mul64(BELL_KY_SI_C_M_PER_S, dt_ps);
    bky_u128_t lc_rhs = bky_u128_mul64(BELL_KY_TWO_E9_PS_MM, (uint64_t)in->dist_mm);
    if (!bky_u128_lt(lc_lhs, lc_rhs)) {
        bky_latch_kill(r, BKY_REASON_KILL_LIGHTCONE);
        return BKY_PORT_KILL;
    }

    if (r->max_ns_dev > tau_ns) {
        bky_latch_kill(r, BKY_REASON_KILL_NO_SIGNALLING);
        return BKY_PORT_KILL;
    }

    if (in->setting_corr_abs > in->tau_indep) {
        bky_latch_kill(r, BKY_REASON_KILL_SETTING_CORR);
        return BKY_PORT_KILL;
    }

    uint64_t abs_s1 = bky_abs_i64(r->sigma_k1);
    uint64_t abs_s2 = bky_abs_i64(r->sigma_k2);
    uint64_t abs_ds = bky_abs_i64(r->sigma_k1 - r->sigma_k2);

    bky_u128_t s1_sq = bky_u128_mul64(abs_s1, abs_s1);
    bky_u128_t s2_sq = bky_u128_mul64(abs_s2, abs_s2);
    bky_u128_t ds_sq = bky_u128_mul64(abs_ds, abs_ds);
    bky_u128_t diff_s_sq = bky_u128_abs_diff(s1_sq, s2_sq);

    bky_u128_t n_sq   = bky_u128_mul64(np, np);
    bky_u128_t bell_w = bky_u128_shl(n_sq, 2U);
    bky_u128_t tsir_w = bky_u128_shl(n_sq, 3U);

    r->last_s1_sq       = s1_sq;
    r->last_s2_sq       = s2_sq;
    r->bell_violated_k1 = bky_u128_gt(s1_sq, bell_w);
    r->super_tsirelson  = bky_u128_gt(s1_sq, tsir_w) || bky_u128_gt(s2_sq, tsir_w);
    r->monitor_coupled  = true;

    if (!in->involution_closed) {
        r->actuator_v_en = false;
        r->last_port     = BKY_PORT_HOLD;
        r->last_reason   = BKY_REASON_HOLD_OPEN_LOOP_L1;
        return BKY_PORT_HOLD;
    }

    if (in->tomo_frob_diff_sq > in->tau_tomo_sq) {
        r->actuator_v_en = false;
        r->last_port     = BKY_PORT_HOLD;
        r->last_reason   = BKY_REASON_HOLD_L1_TOMO_SHIFT;
        return BKY_PORT_HOLD;
    }

    bool sig_shift = bky_u128_gt(diff_s_sq, in->tau_diff_sq) ||
                     bky_u128_gt(ds_sq, in->tau_diff_sq);
    if (!sig_shift) {
        r->actuator_v_en = false;
        r->last_port     = BKY_PORT_HOLD;
        r->last_reason   = BKY_REASON_HOLD_QM_NULL_CONFIRMED;
        return BKY_PORT_HOLD;
    }

    if (in->replicated_series < in->min_series || !in->witness_ext) {
        r->actuator_v_en = false;
        r->last_port     = BKY_PORT_HOLD;
        r->last_reason   = BKY_REASON_HOLD_NO_QUORUM_OR_WIT;
        return BKY_PORT_HOLD;
    }

    r->actuator_v_en = true;
    r->last_port     = BKY_PORT_OPEN;
    r->last_reason   = BKY_REASON_OPEN_L3_WITNESSED;
    return BKY_PORT_OPEN;
}

#endif /* BELL_KY_SLUICE_H */
