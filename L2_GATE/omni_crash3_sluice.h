#ifndef OMNI_CRASH3_SLUICE_H
#define OMNI_CRASH3_SLUICE_H

#include <stdbool.h>
#include <stdint.h>

/* ============================================================================
 * L2_GATE :: 25.OMNI Three-Way Crash Sluice (Crash_3: S_1 ^ S_2 ^ S_3 ^ S_R)
 * Arithmetic : Zero-FP exact integer & Z[phi] quadratic ring (phi^2 = phi+1)
 *
 * Six Bench Seals over Legacy 25.OMNI / MillenniumMineHAL:
 *   1. Eliminates IEEE-754 binary32/binary64 NaN bypass (where NaN > threshold
 *      evaluated to false and returned OPEN_5V00 in omni_millennium_hal.hpp).
 *   2. Replaces weighted L_1 crash score C_crash with exact L_inf component
 *      bounds + strict conjunctive priority KILL > HOLD > OPEN, wiring in the
 *      previously disconnected r_dot > delta_r commit-slope guard.
 *   3. Replaces the tautological ((s ^ r) ^ r == s) pseudo-check with genuine
 *      received wire-word involution verification ((m_rx ^ r_mask) == s_phase)
 *      plus INT32_MIN two's-complement symplectic phase-mirror fencing.
 *   4. Computes the golden-ratio Hamiltonian 2*H_phi(x) = A_H + B_H * phi
 *      exactly in Z[phi] without sqrt(5) floating-point approximation:
 *        A_H = q_proj^2 + p_mom^2 - 2*B_A + 2*C_care
 *        B_H = 2*k_defect^2 + 2*B_A
 *   5. Enforces exact SI-2019 Infranett v0.5 causal diamond (dist_mm <= 20,000,
 *      tof_ps <= 133,425, 2e9 * dist_mm <= 299,792,458 * tof_ps => ds^2 <= 0)
 *      and OMNI-QR v0.1 Finder (0x7F415D417F) + Quiet-Zone (Gamma >= 4).
 *   6. Enforces division-free GKO-R time-to-catastrophe (-g < g_dot * tau_hold),
 *      monotonic D2 OR-fuse P_{t+1} = P_t | (M_rx & ~P_t), trajectory classes
 *      O_0 / O_1 / O_2, and sticky DK flip-flop latch until Level 01 reset.
 * ============================================================================ */

#define OMNI_POISON_INT32_MIN     INT32_MIN
#define OMNI_QR_FINDER_K_GAMMA    (0x7F415D417FULL)
#define OMNI_QR_MASK_40           (0xFFFFFFFFFFULL)
#define OMNI_QR_MIN_QUIET_GAMMA   (4U)
#define OMNI_MAX_DIST_MM          (20000U)
#define OMNI_MAX_TOF_PS           (133425U)
#define OMNI_SI_C_M_PER_S         (299792458ULL)
#define OMNI_TWO_E9_PS_MM         (2000000000ULL)

typedef enum {
    OMNI_PORT_HOLD = 0, /* 0.00 V DC reversible stasis (x_{t+1} = x_t) */
    OMNI_PORT_OPEN = 1, /* 5.00 V DC AKUERISAAVOQ commit + OR-fuse */
    OMNI_PORT_KILL = 2  /* 0.00 V DC Guillotine / sticky DK flip-flop (bot) */
} omni_port_t;

typedef enum {
    OMNI_TRAJ_O0_INADMISSIBLE_START = 0,
    OMNI_TRAJ_O1_NON_PERSISTENT     = 1,
    OMNI_TRAJ_O2_PERSISTENT         = 2
} omni_traj_t;

typedef enum {
    OMNI_REASON_OPEN_AKUERISAAVOQ       = 0,
    OMNI_REASON_HOLD_ETOR_PI_GE_TAU     = 1,
    OMNI_REASON_HOLD_RDOT_SLOPE         = 2,
    OMNI_REASON_HOLD_TAU_R_HORIZON      = 3,
    OMNI_REASON_HOLD_EPS_K_NONZERO      = 4,
    OMNI_REASON_HOLD_NO_WITNESS         = 5,
    OMNI_REASON_KILL_DK_LATCHED         = 6,
    OMNI_REASON_KILL_POISON_OR_BARRIER  = 7,
    OMNI_REASON_KILL_ROSETTA_HASH       = 8,
    OMNI_REASON_KILL_INVOLUTION         = 9,
    OMNI_REASON_KILL_OMNI_QR_STRUCT     = 10,
    OMNI_REASON_KILL_EPOCH_REPLAY       = 11,
    OMNI_REASON_KILL_SPACELIKE_DS2      = 12,
    OMNI_REASON_KILL_EPS_K_EXCEEDED     = 13
} omni_reason_t;

typedef struct {
    uint32_t seq_epoch;
    int32_t  q_pos;
    int32_t  p_mom;
    uint32_t q_bound;
    uint32_t eps_k_max;
    int32_t  lambda_spec;
    int32_t  g_barrier;
    int32_t  g_dot;
    uint32_t tau_hold_ticks;
    uint32_t pi_risk;
    uint32_t tau_risk;
    uint32_t r_dot;
    uint32_t delta_r;
    uint32_t k_defect;
    uint32_t b_barrier;
    uint32_t c_care;
    uint32_t dist_mm;
    uint32_t tof_ps;
    uint16_t s_phase_16;
    uint16_t r_mask_16;
    uint16_t m_rx_16;
    uint64_t finder_sig_40;
    uint8_t  quiet_zone;
    bool     hash_valid;
    bool     u_safe_nonempty;
    bool     eta_hw_truth;
    bool     witness_ext;
} omni_crash3_in_t;

typedef struct {
    uint64_t      cycle;
    uint32_t      reset_epoch;
    uint32_t      expected_epoch;
    bool          dk_kill_latched;
    bool          monitor_coupled;
    bool          actuator_v_en;
    bool          has_survived_step;
    omni_port_t   last_port;
    omni_reason_t last_reason;
    omni_traj_t   traj_class;
    uint16_t      p_or_fuse_reg;
    uint32_t      last_linf_excess;
    int64_t       last_h_phi_a;
    uint64_t      last_h_phi_b;
} omni_crash3_reg_t;

static inline uint32_t omni_max_u32(uint32_t a, uint32_t b) {
    return (a >= b) ? a : b;
}

static inline uint32_t omni_abs_i32_safe(int32_t x) {
    return (x >= 0) ? (uint32_t)x : (uint32_t)(-(x + 1)) + 1U;
}

static inline void omni_crash3_init(omni_crash3_reg_t *r) {
    if (r == 0) {
        return;
    }
    r->cycle             = 0ULL;
    r->reset_epoch       = 0U;
    r->expected_epoch    = 1U;
    r->dk_kill_latched   = false;
    r->monitor_coupled   = true;
    r->actuator_v_en     = false;
    r->has_survived_step = false;
    r->last_port         = OMNI_PORT_HOLD;
    r->last_reason       = OMNI_REASON_HOLD_NO_WITNESS;
    r->traj_class        = OMNI_TRAJ_O2_PERSISTENT;
    r->p_or_fuse_reg     = 0U;
    r->last_linf_excess  = 0U;
    r->last_h_phi_a      = 0LL;
    r->last_h_phi_b      = 0ULL;
}

static inline uint8_t omni_status_byte(const omni_crash3_reg_t *r) {
    uint8_t b = (uint8_t)((uint8_t)r->last_port & 0x03U);
    if (r->actuator_v_en)   { b |= 0x04U; }
    if (r->monitor_coupled) { b |= 0x08U; }
    if (r->dk_kill_latched) { b |= 0x10U; }
    b |= (uint8_t)(((uint8_t)r->traj_class & 0x03U) << 5);
    return b;
}

static inline void omni_latch_kill(omni_crash3_reg_t *r, omni_reason_t reason) {
    r->dk_kill_latched  = true;
    r->monitor_coupled  = false;
    r->actuator_v_en    = false;
    r->last_port        = OMNI_PORT_KILL;
    r->last_reason      = reason;
    r->traj_class       = r->has_survived_step
        ? OMNI_TRAJ_O1_NON_PERSISTENT
        : OMNI_TRAJ_O0_INADMISSIBLE_START;
    r->last_linf_excess = 0U;
    r->last_h_phi_a     = 0LL;
    r->last_h_phi_b     = 0ULL;
}

static inline omni_port_t omni_crash3_l01_reset(
    omni_crash3_reg_t *r, bool l01_witness_ok
) {
    if (r == 0) {
        return OMNI_PORT_KILL;
    }
    r->cycle += 1ULL;
    if (!l01_witness_ok) {
        if (r->dk_kill_latched) {
            r->last_port   = OMNI_PORT_KILL;
            r->last_reason = OMNI_REASON_KILL_DK_LATCHED;
            return OMNI_PORT_KILL;
        }
        r->actuator_v_en = false;
        r->last_port     = OMNI_PORT_HOLD;
        r->last_reason   = OMNI_REASON_HOLD_NO_WITNESS;
        return OMNI_PORT_HOLD;
    }
    /* Non-erasing Level 01 recovery: preserves cycle, reset_epoch, expected_epoch,
     * and monotonic D2 p_or_fuse_reg while re-arming chamber M in HOLD (0.00 V). */
    r->reset_epoch       += 1U;
    r->dk_kill_latched    = false;
    r->monitor_coupled    = true;
    r->actuator_v_en      = false;
    r->has_survived_step  = false;
    r->last_port          = OMNI_PORT_HOLD;
    r->last_reason        = OMNI_REASON_HOLD_NO_WITNESS;
    r->traj_class         = OMNI_TRAJ_O2_PERSISTENT;
    r->last_linf_excess   = 0U;
    r->last_h_phi_a       = 0LL;
    r->last_h_phi_b       = 0ULL;
    return OMNI_PORT_HOLD;
}

static inline omni_port_t omni_crash3_eval(
    omni_crash3_reg_t *r, const omni_crash3_in_t *in
) {
    if (r == 0 || in == 0) {
        return OMNI_PORT_KILL;
    }
    /* Constant-time 194-cycle hardware evaluation (1 start + 6x32 MAC + 1 commit) */
    r->cycle += 194ULL;

    if (r->dk_kill_latched) {
        omni_latch_kill(r, OMNI_REASON_KILL_DK_LATCHED);
        return OMNI_PORT_KILL;
    }

    if (in->q_pos == OMNI_POISON_INT32_MIN ||
        in->p_mom == OMNI_POISON_INT32_MIN ||
        in->g_barrier == OMNI_POISON_INT32_MIN ||
        in->g_dot == OMNI_POISON_INT32_MIN ||
        in->q_bound == 0U || in->q_bound > 0x7FFFFFFFU ||
        in->k_defect > 0x7FFFFFFFU || in->b_barrier > 0x7FFFFFFFU ||
        in->c_care > 0x7FFFFFFFU ||
        in->tau_risk == 0U || !in->u_safe_nonempty ||
        in->g_barrier >= 0 || in->lambda_spec > 0) {
        omni_latch_kill(r, OMNI_REASON_KILL_POISON_OR_BARRIER);
        return OMNI_PORT_KILL;
    }

    if (!in->hash_valid) {
        omni_latch_kill(r, OMNI_REASON_KILL_ROSETTA_HASH);
        return OMNI_PORT_KILL;
    }

    uint16_t decoded_s = (uint16_t)(in->m_rx_16 ^ in->r_mask_16);
    if (decoded_s != in->s_phase_16) {
        omni_latch_kill(r, OMNI_REASON_KILL_INVOLUTION);
        return OMNI_PORT_KILL;
    }

    if (((in->finder_sig_40 & OMNI_QR_MASK_40) != OMNI_QR_FINDER_K_GAMMA) ||
        (in->quiet_zone < OMNI_QR_MIN_QUIET_GAMMA)) {
        omni_latch_kill(r, OMNI_REASON_KILL_OMNI_QR_STRUCT);
        return OMNI_PORT_KILL;
    }

    if (in->seq_epoch < r->expected_epoch) {
        omni_latch_kill(r, OMNI_REASON_KILL_EPOCH_REPLAY);
        return OMNI_PORT_KILL;
    }

    if (in->dist_mm == 0U || in->dist_mm > OMNI_MAX_DIST_MM ||
        in->tof_ps == 0U || in->tof_ps > OMNI_MAX_TOF_PS) {
        omni_latch_kill(r, OMNI_REASON_KILL_SPACELIKE_DS2);
        return OMNI_PORT_KILL;
    }
    uint64_t lc_lhs = OMNI_TWO_E9_PS_MM * (uint64_t)in->dist_mm;
    uint64_t lc_rhs = OMNI_SI_C_M_PER_S * (uint64_t)in->tof_ps;
    if (lc_lhs > lc_rhs) {
        omni_latch_kill(r, OMNI_REASON_KILL_SPACELIKE_DS2);
        return OMNI_PORT_KILL;
    }

    /* S_1: CPCA-B interval projection onto [-q_bound, +q_bound] */
    int32_t qb_i = (int32_t)in->q_bound;
    int32_t q_proj = in->q_pos;
    if (q_proj > qb_i) {
        q_proj = qb_i;
    } else if (q_proj < -qb_i) {
        q_proj = -qb_i;
    }
    uint32_t eps_k = (in->q_pos >= q_proj)
        ? (uint32_t)((int64_t)in->q_pos - (int64_t)q_proj)
        : (uint32_t)((int64_t)q_proj - (int64_t)in->q_pos);

    if (eps_k > in->eps_k_max) {
        omni_latch_kill(r, OMNI_REASON_KILL_EPS_K_EXCEEDED);
        return OMNI_PORT_KILL;
    }

    /* Exact Z[phi] Hamiltonian: 2*H_phi = A_H + B_H * phi */
    uint64_t abs_qp = (uint64_t)omni_abs_i32_safe(q_proj);
    uint64_t abs_pm = (uint64_t)omni_abs_i32_safe(in->p_mom);
    uint64_t q_sq   = abs_qp * abs_qp;
    uint64_t p_sq   = abs_pm * abs_pm;
    uint64_t k_sq   = (uint64_t)in->k_defect * (uint64_t)in->k_defect;

    uint64_t h_pos = q_sq + p_sq + 2ULL * (uint64_t)in->c_care;
    uint64_t h_neg = 2ULL * (uint64_t)in->b_barrier;
    int64_t  a_h   = (h_pos >= h_neg)
                   ? (int64_t)(h_pos - h_neg)
                   : -(int64_t)(h_neg - h_pos);
    uint64_t b_h = 2ULL * k_sq + 2ULL * (uint64_t)in->b_barrier;

    /* Exact L_inf soft-channel excess (replaces weighted L_1 C_crash) */
    uint32_t pi_exc   = (in->pi_risk >= in->tau_risk) ? (in->pi_risk - in->tau_risk + 1U) : 0U;
    uint32_t rdot_exc = (in->r_dot > in->delta_r) ? (in->r_dot - in->delta_r) : 0U;
    uint32_t linf_exc = omni_max_u32(eps_k, omni_max_u32(pi_exc, rdot_exc));

    uint64_t g_margin = (uint64_t)omni_abs_i32_safe(in->g_barrier);
    bool tau_r_short = (in->g_dot > 0) &&
                       (g_margin < ((uint64_t)(uint32_t)in->g_dot * (uint64_t)in->tau_hold_ticks));

    r->has_survived_step = true;
    r->monitor_coupled   = true;
    r->traj_class        = OMNI_TRAJ_O2_PERSISTENT;
    r->last_linf_excess  = linf_exc;
    r->last_h_phi_a      = a_h;
    r->last_h_phi_b      = b_h;

    if (in->pi_risk >= in->tau_risk) {
        r->actuator_v_en = false;
        r->last_port     = OMNI_PORT_HOLD;
        r->last_reason   = OMNI_REASON_HOLD_ETOR_PI_GE_TAU;
        return OMNI_PORT_HOLD;
    }

    if (in->r_dot > in->delta_r) {
        r->actuator_v_en = false;
        r->last_port     = OMNI_PORT_HOLD;
        r->last_reason   = OMNI_REASON_HOLD_RDOT_SLOPE;
        return OMNI_PORT_HOLD;
    }

    if (tau_r_short) {
        r->actuator_v_en = false;
        r->last_port     = OMNI_PORT_HOLD;
        r->last_reason   = OMNI_REASON_HOLD_TAU_R_HORIZON;
        return OMNI_PORT_HOLD;
    }

    if (eps_k > 0U) {
        r->actuator_v_en = false;
        r->last_port     = OMNI_PORT_HOLD;
        r->last_reason   = OMNI_REASON_HOLD_EPS_K_NONZERO;
        return OMNI_PORT_HOLD;
    }

    if (!in->eta_hw_truth || !in->witness_ext || (in->seq_epoch != r->expected_epoch) || (in->seq_epoch == 0xFFFFFFFFU)) {
        r->actuator_v_en = false;
        r->last_port     = OMNI_PORT_HOLD;
        r->last_reason   = OMNI_REASON_HOLD_NO_WITNESS;
        return OMNI_PORT_HOLD;
    }

    /* S_1 ^ S_2 ^ S_3 ^ S_R ^ W_ext all 100% green -> AKUERISAAVOQ OPEN */
    r->actuator_v_en  = true;
    r->last_port      = OMNI_PORT_OPEN;
    r->last_reason    = OMNI_REASON_OPEN_AKUERISAAVOQ;
    r->p_or_fuse_reg  = (uint16_t)(r->p_or_fuse_reg | (in->m_rx_16 & (uint16_t)(~r->p_or_fuse_reg)));
    r->expected_epoch += 1U;
    return OMNI_PORT_OPEN;
}

#endif /* OMNI_CRASH3_SLUICE_H */
