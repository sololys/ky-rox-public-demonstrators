#include "omni_crash3_sluice.h"
#include <stdio.h>

static omni_crash3_in_t nominal_in(uint32_t seq_epoch) {
    omni_crash3_in_t in;
    in.seq_epoch       = seq_epoch;
    in.q_pos           = 480;
    in.p_mom           = 80;
    in.q_bound         = 1000U;
    in.eps_k_max       = 250U;
    in.lambda_spec     = -250;
    in.g_barrier       = -500;
    in.g_dot           = 10;
    in.tau_hold_ticks  = 20U;
    in.pi_risk         = 50U;
    in.tau_risk        = 200U;
    in.r_dot           = 100U;
    in.delta_r         = 500U;
    in.k_defect        = 15U;
    in.b_barrier       = 100U;
    in.c_care          = 250U;
    in.dist_mm         = 12000U;
    in.tof_ps          = 80100U;
    in.s_phase_16      = 0x05A5U;
    in.r_mask_16       = 0xF00FU;
    in.m_rx_16         = (uint16_t)(0x05A5U ^ 0xF00FU); /* 0xF5AA */
    in.finder_sig_40   = OMNI_QR_FINDER_K_GAMMA;
    in.quiet_zone      = 4U;
    in.hash_valid      = true;
    in.u_safe_nonempty = true;
    in.eta_hw_truth    = true;
    in.witness_ext     = true;
    return in;
}

static void print_vec(const char *tag, const omni_crash3_reg_t *r) {
    printf(
        "%s|BYTE=0x%02x|PORT=%u|REASON=%02u|TRAJ=%u|FUSE=0x%04x|LINF=%u|"
        "CYC=%llu|EPOCH=%u|HPHIA=%lld|HPHIB=%llu\n",
        tag,
        (unsigned int)omni_status_byte(r),
        (unsigned int)r->last_port,
        (unsigned int)r->last_reason,
        (unsigned int)r->traj_class,
        (unsigned int)r->p_or_fuse_reg,
        (unsigned int)r->last_linf_excess,
        (unsigned long long)r->cycle,
        (unsigned int)r->reset_epoch,
        (long long)r->last_h_phi_a,
        (unsigned long long)r->last_h_phi_b
    );
}

int main(void) {
    omni_crash3_reg_t r;
    omni_crash3_init(&r);

    /* V01: Nominal Test A (25.OMNI) -> OPEN (5.00 V, O_2, OR-fuse=0xF5AA) */
    omni_crash3_in_t in = nominal_in(r.expected_epoch);
    omni_crash3_eval(&r, &in);
    print_vec("V01", &r);

    /* V02: Test C — E-TOR Supervisor Override (pi_risk=350 >= tau_risk=200) -> HOLD */
    in = nominal_in(r.expected_epoch);
    in.pi_risk = 350U;
    omni_crash3_eval(&r, &in);
    print_vec("V02", &r);

    /* V03: Commit-Slope Breach (r_dot=620 > delta_r=500, previously missed!) -> HOLD */
    in = nominal_in(r.expected_epoch);
    in.r_dot = 620U;
    omni_crash3_eval(&r, &in);
    print_vec("V03", &r);

    /* V04: Division-Free GKO-R Horizon (-g_barrier=150 < g_dot*tau_hold=200) -> HOLD */
    in = nominal_in(r.expected_epoch);
    in.g_barrier = -150;
    omni_crash3_eval(&r, &in);
    print_vec("V04", &r);

    /* V05: Tangential CPCA-B Deflection (q_pos=1150 -> eps_k=150 <= 250) -> HOLD */
    in = nominal_in(r.expected_epoch);
    in.q_pos = 1150;
    omni_crash3_eval(&r, &in);
    print_vec("V05", &r);

    /* V06: One-Way Law (witness_ext=false) -> HOLD at 0.00 V DC */
    in = nominal_in(r.expected_epoch);
    in.witness_ext = false;
    omni_crash3_eval(&r, &in);
    print_vec("V06", &r);

    /* V07: Crash_3 Master Three-Way Collision:
     * S_1=PASS (eps_k=0), S_2=HOLD (pi=400>=200, r_dot=850>500), S_3=KILL (hash_valid=0)
     * Priority KILL > HOLD > OPEN -> PORT_KILL, traj O_2 -> O_1_NON_PERSISTENT! */
    in = nominal_in(r.expected_epoch);
    in.pi_risk    = 400U;
    in.r_dot      = 850U;
    in.hash_valid = false;
    omni_crash3_eval(&r, &in);
    print_vec("V07", &r);

    /* V08: Sticky DK Flip-Flop — nominal V01 presented while dk_kill_latched==1 -> KILL */
    in = nominal_in(r.expected_epoch);
    omni_crash3_eval(&r, &in);
    print_vec("V08", &r);

    /* V09: L01 Reset + Real Wire Involution Breach (1-bit flip in m_rx_16) -> KILL (O_0!) */
    omni_crash3_l01_reset(&r, true);
    in = nominal_in(r.expected_epoch);
    in.m_rx_16 = (uint16_t)(in.m_rx_16 ^ 0x0001U);
    omni_crash3_eval(&r, &in);
    print_vec("V09", &r);

    /* V10: L01 Reset + Infranett v0.5 500m Relay Attack in 133,420 ps -> KILL */
    omni_crash3_l01_reset(&r, true);
    in = nominal_in(r.expected_epoch);
    in.dist_mm = 500000U;
    in.tof_ps  = 133420U;
    omni_crash3_eval(&r, &in);
    print_vec("V10", &r);

    /* V11: L01 Reset + OMNI-QR v0.1 Quiet-Zone Breach (quiet_zone=2 < 4) -> KILL */
    omni_crash3_l01_reset(&r, true);
    in = nominal_in(r.expected_epoch);
    in.quiet_zone = 2U;
    omni_crash3_eval(&r, &in);
    print_vec("V11", &r);

    /* V12: L01 Reset + INT32_MIN Symplectic Mirror Singularity + Re-Open Recovery Check
     * First trip INT32_MIN -> KILL; Wait: let V12 test INT32_MIN directly -> KILL! */
    omni_crash3_l01_reset(&r, true);
    in = nominal_in(r.expected_epoch);
    in.p_mom = OMNI_POISON_INT32_MIN;
    omni_crash3_eval(&r, &in);
    print_vec("V12", &r);

    return 0;
}
