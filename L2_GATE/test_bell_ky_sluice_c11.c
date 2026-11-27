#include "bell_ky_sluice.h"
#include <stdio.h>

static void fill_sym_counts(uint64_t n_pulses, int64_t corr, bky_arm_counts_t *ac) {
    int64_t n_i = (int64_t)n_pulses;
    uint64_t same = (uint64_t)((n_i + corr) / 4LL);
    uint64_t diff = (uint64_t)((n_i - corr) / 4LL);
    ac->n_pulses = n_pulses;
    ac->pp = same;
    ac->mm = same;
    ac->pm = diff;
    ac->mp = diff;
}

static void stream_symmetric_chsh_block(
    bky_sluice_reg_t *r, uint64_t n_pulses,
    int64_t c1_00, int64_t c1_01, int64_t c1_10, int64_t c1_11,
    int64_t c2_00, int64_t c2_01, int64_t c2_10, int64_t c2_11
) {
    int64_t c1[4] = {c1_00, c1_01, c1_10, c1_11};
    int64_t c2[4] = {c2_00, c2_01, c2_10, c2_11};
    for (uint8_t idx = 0U; idx < 4U; ++idx) {
        bky_arm_counts_t ac;
        fill_sym_counts(n_pulses, c1[idx], &ac);
        bky_sluice_load_setting(r, 0U, idx, &ac);
    }
    for (uint8_t idx = 0U; idx < 4U; ++idx) {
        bky_arm_counts_t ac;
        fill_sym_counts(n_pulses, c2[idx], &ac);
        bky_sluice_load_setting(r, 1U, idx, &ac);
    }
}

static bky_eval_in_t nominal_eval_cfg(uint64_t n_pulses) {
    bky_eval_in_t in;
    in.n_pulses          = n_pulses;
    in.delta_k_cycles    = 200U;
    in.t_clk_ps          = 1000U;
    in.dist_mm           = 30000U;
    in.tau_ns            = 50ULL;
    in.setting_corr_abs  = 0U;
    in.tau_indep         = 10U;
    in.tomo_frob_diff_sq = 0U;
    in.tau_tomo_sq       = 100U;
    in.tau_diff_sq.hi    = 0ULL;
    in.tau_diff_sq.lo    = 1000000ULL;
    in.replicated_series = 3U;
    in.min_series        = 3U;
    in.hash_valid        = true;
    in.involution_closed = true;
    in.witness_ext       = true;
    return in;
}

static void print_vec(const char *tag, const bky_sluice_reg_t *r) {
    printf(
        "%s|BYTE=0x%02x|PORT=%u|REASON=%02u|CYC=%llu|EPOCH=%u|"
        "S1SQ=0x%016llx_%016llx|S2SQ=0x%016llx_%016llx\n",
        tag,
        (unsigned int)bky_status_byte(r),
        (unsigned int)r->last_port,
        (unsigned int)r->last_reason,
        (unsigned long long)r->cycle,
        (unsigned int)r->reset_epoch,
        (unsigned long long)r->last_s1_sq.hi,
        (unsigned long long)r->last_s1_sq.lo,
        (unsigned long long)r->last_s2_sq.hi,
        (unsigned long long)r->last_s2_sq.lo
    );
}

int main(void) {
    bky_sluice_reg_t r;
    bky_sluice_init(&r);

    /* V01: Standard QM closed involution null test */
    stream_symmetric_chsh_block(&r, 10000ULL,
        7072LL, 7072LL, 7072LL, -7072LL,
        7072LL, 7072LL, 7072LL, -7072LL);
    bky_eval_in_t in = nominal_eval_cfg(10000ULL);
    bky_sluice_eval(&r, &in);
    print_vec("V01", &r);

    /* V02: L1 Bluff Scraper — w=0 vs w=2 local tomography shift */
    stream_symmetric_chsh_block(&r, 10000ULL,
        7072LL, 7072LL, 7068LL, -7068LL,
        7072LL, 7072LL, 4240LL, -4240LL);
    in = nominal_eval_cfg(10000ULL);
    in.tomo_frob_diff_sq = 1600U;
    bky_sluice_eval(&r, &in);
    print_vec("V02", &r);

    /* V03: w=3 (<4) vs w=5, open loop L1 */
    stream_symmetric_chsh_block(&r, 10000ULL,
        7072LL, 7072LL, 2828LL, -2828LL,
        7072LL, 7072LL, 0LL, 0LL);
    in = nominal_eval_cfg(10000ULL);
    in.involution_closed = false;
    bky_sluice_eval(&r, &in);
    print_vec("V03", &r);

    /* V04: Unwitnessed L3 candidate stays in HOLD */
    stream_symmetric_chsh_block(&r, 10000ULL,
        7072LL, 7072LL, 7068LL, -7068LL,
        6200LL, 6200LL, 6200LL, -6200LL);
    in = nominal_eval_cfg(10000ULL);
    in.witness_ext = false;
    bky_sluice_eval(&r, &in);
    print_vec("V04", &r);

    /* V05: Full L3 Candidate Pass -> PORT_OPEN */
    stream_symmetric_chsh_block(&r, 10000ULL,
        7072LL, 7072LL, 7068LL, -7068LL,
        6200LL, 6200LL, 6200LL, -6200LL);
    in = nominal_eval_cfg(10000ULL);
    bky_sluice_eval(&r, &in);
    print_vec("V05", &r);

    /* V06: Sign-Inversion Seal (+28,000 vs -28,000) -> PORT_OPEN */
    stream_symmetric_chsh_block(&r, 10000ULL,
        7000LL, 7000LL, 7000LL, -7000LL,
        -7000LL, -7000LL, -7000LL, 7000LL);
    in = nominal_eval_cfg(10000ULL);
    bky_sluice_eval(&r, &in);
    print_vec("V06", &r);

    /* V07: Light-Cone Breach (201 cycles >= 2L/c) -> PORT_KILL */
    stream_symmetric_chsh_block(&r, 10000ULL,
        7000LL, 7000LL, 7000LL, -7000LL,
        6000LL, 6000LL, 6000LL, -6000LL);
    in = nominal_eval_cfg(10000ULL);
    in.delta_k_cycles = 201U;
    bky_sluice_eval(&r, &in);
    print_vec("V07", &r);

    /* V08: Sticky Latch -> remains PORT_KILL */
    stream_symmetric_chsh_block(&r, 10000ULL,
        7072LL, 7072LL, 7068LL, -7068LL,
        6200LL, 6200LL, 6200LL, -6200LL);
    in = nominal_eval_cfg(10000ULL);
    bky_sluice_eval(&r, &in);
    print_vec("V08", &r);

    /* V09: L01 Reset + 1 Dropped Pulse -> PORT_KILL */
    bky_sluice_l01_reset(&r, true);
    for (uint8_t arm = 0U; arm < 2U; ++arm) {
        for (uint8_t idx = 0U; idx < 4U; ++idx) {
            bky_arm_counts_t ac;
            int64_t corr = (idx == 3U) ? -7000LL : 7000LL;
            fill_sym_counts(10000ULL, corr, &ac);
            if (arm == 0U && idx == 0U) {
                ac.pp -= 1ULL;
            }
            bky_sluice_load_setting(&r, arm, idx, &ac);
        }
    }
    in = nominal_eval_cfg(10000ULL);
    bky_sluice_eval(&r, &in);
    print_vec("V09", &r);

    /* V10: L01 Reset + No-Signalling Marginal Breach -> PORT_KILL */
    bky_sluice_l01_reset(&r, true);
    for (uint8_t arm = 0U; arm < 2U; ++arm) {
        for (uint8_t idx = 0U; idx < 4U; ++idx) {
            bky_arm_counts_t ac;
            int64_t corr = (idx == 3U) ? -6000LL : 6000LL;
            fill_sym_counts(10000ULL, corr, &ac);
            if (arm == 0U && idx == 1U) {
                ac.pm += 80ULL;
                ac.mm -= 80ULL;
            }
            bky_sluice_load_setting(&r, arm, idx, &ac);
        }
    }
    in = nominal_eval_cfg(10000ULL);
    bky_sluice_eval(&r, &in);
    print_vec("V10", &r);

    /* V11: L01 Reset + Setting-Correlation Breach -> PORT_KILL */
    bky_sluice_l01_reset(&r, true);
    stream_symmetric_chsh_block(&r, 10000ULL,
        7000LL, 7000LL, 7000LL, -7000LL,
        6000LL, 6000LL, 6000LL, -6000LL);
    in = nominal_eval_cfg(10000ULL);
    in.setting_corr_abs = 25U;
    bky_sluice_eval(&r, &in);
    print_vec("V11", &r);

    /* V12: L01 Reset + >64-Bit 128-Bit Shot Scale (N = 2^32) -> PORT_OPEN */
    bky_sluice_l01_reset(&r, true);
    uint64_t big_n = (1ULL << 32);
    stream_symmetric_chsh_block(&r, big_n,
        3000000000LL, 3000000000LL, 3000000000LL, -3000000000LL,
        2500000000LL, 2500000000LL, 2500000000LL, -2500000000LL);
    in = nominal_eval_cfg(big_n);
    in.tau_ns = 100000ULL;
    in.tau_diff_sq.hi = 0ULL;
    in.tau_diff_sq.lo = 1000000000000ULL;
    bky_sluice_eval(&r, &in);
    print_vec("V12", &r);

    /* V13: Exact Classical Bell Boundary (Sigma_1 = 20000 -> S1^2 == 4*N^2) -> bell_violated_k1=0, OPEN */
    stream_symmetric_chsh_block(&r, 10000ULL,
        5000LL, 5000LL, 5000LL, -5000LL,
        4000LL, 4000LL, 4000LL, -4000LL);
    in = nominal_eval_cfg(10000ULL);
    bky_sluice_eval(&r, &in);
    print_vec("V13", &r);

    /* V14: Minimum Physical +1-Shot Quantum Above Bell Boundary (Sigma_1 = 20002 -> S1^2 = 400080004 > 4*N^2) */
    {
        bky_arm_counts_t ac0 = {10000ULL, 3751ULL, 1250ULL, 1249ULL, 3750ULL};
        bky_sluice_load_setting(&r, 0U, 0U, &ac0);
        for (uint8_t idx = 1U; idx < 4U; ++idx) {
            bky_arm_counts_t ac;
            fill_sym_counts(10000ULL, (idx == 3U) ? -5000LL : 5000LL, &ac);
            bky_sluice_load_setting(&r, 0U, idx, &ac);
        }
        for (uint8_t idx = 0U; idx < 4U; ++idx) {
            bky_arm_counts_t ac;
            fill_sym_counts(10000ULL, (idx == 3U) ? -4000LL : 4000LL, &ac);
            bky_sluice_load_setting(&r, 1U, idx, &ac);
        }
        in = nominal_eval_cfg(10000ULL);
        bky_sluice_eval(&r, &in);
        print_vec("V14", &r);
    }

    /* V15: 128-Bit Word-Seam Exact Equality (ds_sq == 2^68 == tau_diff_sq) -> PORT_HOLD */
    {
        uint64_t n32 = (1ULL << 32);
        int64_t  c31 = (int64_t)(1ULL << 31);
        stream_symmetric_chsh_block(&r, n32,
            c31, c31, c31, -c31,
            -c31, -c31, -c31, c31);
        in = nominal_eval_cfg(n32);
        in.tau_diff_sq.hi = 0x10ULL;
        in.tau_diff_sq.lo = 0x0ULL;
        bky_sluice_eval(&r, &in);
        print_vec("V15", &r);
    }

    /* V16: 128-Bit Word-Seam -1 LSB Borrow (tau_diff_sq = 2^68 - 1 = 0x0F_FFFFFFFFFFFFFFFF) -> PORT_OPEN */
    {
        uint64_t n32 = (1ULL << 32);
        int64_t  c31 = (int64_t)(1ULL << 31);
        stream_symmetric_chsh_block(&r, n32,
            c31, c31, c31, -c31,
            -c31, -c31, -c31, c31);
        in = nominal_eval_cfg(n32);
        in.tau_diff_sq.hi = 0x0FULL;
        in.tau_diff_sq.lo = 0xFFFFFFFFFFFFFFFFULL;
        bky_sluice_eval(&r, &in);
        print_vec("V16", &r);
    }

    /* V17: Absolute MAX_PULSES = 2^38 Saturated Ceiling (S1^2 = 2^80, ds_sq = 2^82) + +1mm Light-Cone Margin -> OPEN */
    {
        uint64_t nmax = (1ULL << 38);
        int64_t  cmax = (int64_t)nmax;
        stream_symmetric_chsh_block(&r, nmax,
            cmax, cmax, cmax, -cmax,
            -cmax, -cmax, -cmax, cmax);
        in = nominal_eval_cfg(nmax);
        in.delta_k_cycles = 1000U;
        in.t_clk_ps       = 1000000U;
        in.dist_mm        = 149896230U; /* 2e9 * 149896230 > 299792458 * 1e9 by +2e9 */
        in.tau_diff_sq.hi = 0x0003FFFFULL;
        in.tau_diff_sq.lo = 0xFFFFFFFFFFFFFFFFULL;
        bky_sluice_eval(&r, &in);
        print_vec("V17", &r);
    }

    /* V18: MAX_PULSES + 1 = (1ULL << 38) + 1 Over-Ceiling -> PORT_KILL */
    {
        uint64_t nover = (1ULL << 38) + 1ULL;
        bky_arm_counts_t ac = {nover, nover, 0ULL, 0ULL, 0ULL};
        for (uint8_t arm = 0U; arm < 2U; ++arm) {
            for (uint8_t idx = 0U; idx < 4U; ++idx) {
                bky_sluice_load_setting(&r, arm, idx, &ac);
            }
        }
        in = nominal_eval_cfg(nover);
        bky_sluice_eval(&r, &in);
        print_vec("V18", &r);
    }

    /* V19: L01 Reset + Out-of-Order Interleaved Slot Attack (0 -> 4 -> 1..3 -> 5..7) -> PORT_KILL */
    bky_sluice_l01_reset(&r, true);
    {
        bky_arm_counts_t ac_pos, ac_neg;
        fill_sym_counts(10000ULL, 7000LL, &ac_pos);
        fill_sym_counts(10000ULL, -7000LL, &ac_neg);
        bky_sluice_load_setting(&r, 0U, 0U, &ac_pos);
        bky_sluice_load_setting(&r, 1U, 0U, &ac_pos); /* Interleaved arm 1 before arm 0 finished! */
        bky_sluice_load_setting(&r, 0U, 1U, &ac_pos);
        bky_sluice_load_setting(&r, 0U, 2U, &ac_pos);
        bky_sluice_load_setting(&r, 0U, 3U, &ac_neg);
        bky_sluice_load_setting(&r, 1U, 1U, &ac_pos);
        bky_sluice_load_setting(&r, 1U, 2U, &ac_pos);
        bky_sluice_load_setting(&r, 1U, 3U, &ac_neg);
        in = nominal_eval_cfg(10000ULL);
        bky_sluice_eval(&r, &in);
        print_vec("V19", &r);
    }

    /* V20: L01 Reset + Exact Lightlike Boundary (299792458 * 10^9 == 2e9 * 149896229, diff == 0) -> PORT_KILL */
    bky_sluice_l01_reset(&r, true);
    stream_symmetric_chsh_block(&r, 10000ULL,
        7000LL, 7000LL, 7000LL, -7000LL,
        6000LL, 6000LL, 6000LL, -6000LL);
    in = nominal_eval_cfg(10000ULL);
    in.delta_k_cycles = 1000U;
    in.t_clk_ps       = 1000000U;
    in.dist_mm        = 149896229U;
    bky_sluice_eval(&r, &in);
    print_vec("V20", &r);

    /* V21: L01 Reset + Cross-Word Borrow OPEN (ds_sq = 0x10_0000010000000400 > tau = 0x0F_0000020000000800,
     *      where ds_lo < tau_lo across BOTH bit 47 and bit 64 -> must OPEN, never false HOLD!) */
    bky_sluice_l01_reset(&r, true);
    {
        uint64_t n32 = (1ULL << 32);
        int64_t  c_b = (int64_t)(1ULL << 31) + 4LL;
        stream_symmetric_chsh_block(&r, n32,
            c_b, c_b, c_b, -c_b,
            -c_b, -c_b, -c_b, c_b);
        in = nominal_eval_cfg(n32);
        in.tau_diff_sq.hi = 0x0FULL;
        in.tau_diff_sq.lo = 0x0000020000000800ULL;
        bky_sluice_eval(&r, &in);
        print_vec("V21", &r);
    }

    /* V22: Cross-Word Borrow HOLD (ds_sq = 0x10_0000010000000400 < tau = 0x11_0000000000000000,
     *      where ds_lo > tau_lo forces low-half borrow = 1 absorbed by hi-word +1 -> HOLD!) */
    {
        uint64_t n32 = (1ULL << 32);
        int64_t  c_b = (int64_t)(1ULL << 31) + 4LL;
        stream_symmetric_chsh_block(&r, n32,
            c_b, c_b, c_b, -c_b,
            -c_b, -c_b, -c_b, c_b);
        in = nominal_eval_cfg(n32);
        in.tau_diff_sq.hi = 0x11ULL;
        in.tau_diff_sq.lo = 0x0000000000000000ULL;
        bky_sluice_eval(&r, &in);
        print_vec("V22", &r);
    }

    return 0;
}
