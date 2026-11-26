/*
 * vektor_a_qnx_resmgr.c — QNX Neutrino 8.0 Vektor A (133,425 ps) & SPEC-411 Cage
 * ==============================================================================
 * Surface          : L2_GATE/vektor_a_qnx_resmgr.c
 * Target           : QNX SDP 8.0 (x86_64 & aarch64le), -std=gnu11 -O2 -Wall -Wextra -Werror
 * Epistemic Tier   : L1.5 QNX 8.0 Cross-Compiled C11 Gate (PHYSICAL_AUTHORITY = NONE)
 * Epistemic Bound  : INSPIRED_BY != IMPLEMENTS != PROVES
 * Guarantees       :
 *   - _NTO_CHF_FIXED_PRIORITY | _NTO_CHF_DISCONNECT (no priority collapse, no _NTO_CHF_UNBLOCK)
 *   - CLOCK_MONOTONIC TimerTimeout + zero timer coalescing tolerance
 *   - mlockall(MCL_CURRENT | MCL_FUTURE) + permanent procmgr_ability lockdown
 *   - Exact integer arithmetic (no IEEE-754 FP, 0 malloc), galvanic Omega_Y == 1
 */
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/neutrino.h>
#include <sys/procmgr.h>

#include "spec411_gate.h"

#define VEKTOR_A_QNX_CMD_STEP      (1U)
#define VEKTOR_A_QNX_CMD_L01_RESET (2U)

typedef struct {
    uint32_t cmd;
    uint8_t  tdc_valid;
    uint32_t tdc_tof_ps;
    uint8_t  win_valid;
    uint32_t sapphire_meas_ticks;
    uint8_t  bilat_50_50_sealed;
    uint32_t delta_k_num;
    uint32_t delta_k_den;
    uint32_t eps_num;
    uint32_t eps_den;
    uint32_t rho_n;
    uint32_t k_gamma;
    uint8_t  avg_l01_trigger;
    uint8_t  l01_reset_seal[32];
} vektor_a_qnx_msg_t;

typedef struct {
    uint64_t step_seq;
    uint32_t reset_epoch;
    uint8_t  hw_port_byte;
    uint8_t  core_wake_en;
    uint8_t  causal_hold;
    uint8_t  clock_drift_kill;
} vektor_a_qnx_reply_t;

static spec411_state_t g_sluice;
static bool            g_initialized = false;

/* Constant-time 32-byte Level 01 reset seal comparison */
static bool vektor_a_qnx_seal_eq(const uint8_t a[32], const uint8_t b[32]) {
    uint8_t diff = 0U;
    for (size_t i = 0U; i < 32U; ++i) {
        diff |= (uint8_t)(a[i] ^ b[i]);
    }
    return (diff == 0U);
}

int vektor_a_qnx_create_fixed_channel(void) {
    spec411_init(&g_sluice);
    g_initialized = true;
    return ChannelCreate(_NTO_CHF_FIXED_PRIORITY | _NTO_CHF_DISCONNECT);
}

int vektor_a_qnx_harden_process(void) {
    uint64_t zero_tol = 0ULL;
    uint64_t old_tol  = 0ULL;

    if (procmgr_timer_tolerance(0, &zero_tol, &old_tol) != EOK) {
        return -1;
    }
    if (mlockall(MCL_CURRENT | MCL_FUTURE) != 0) {
        return -1;
    }

    const uint32_t deny_lock =
        PROCMGR_ADN_ROOT | PROCMGR_ADN_NONROOT | PROCMGR_AOP_DENY | PROCMGR_AOP_LOCK;

    int ret = procmgr_ability(
        0,
        deny_lock | PROCMGR_AID_SPAWN,
        deny_lock | PROCMGR_AID_FORK,
        deny_lock | PROCMGR_AID_PATHSPACE,
        deny_lock | PROCMGR_AID_IO,
        deny_lock | PROCMGR_AID_MEM_PHYS,
        deny_lock | PROCMGR_AID_CLOCKSET,
        deny_lock | PROCMGR_AID_DEFAULT_TIMER_TOLERANCE,
        PROCMGR_AID_EOL
    );
    return (ret == EOK) ? 0 : -1;
}

int vektor_a_qnx_receive_and_gate(
    int                   chid,
    uint64_t              timeout_ns,
    const uint8_t         expected_l01_seal[32],
    vektor_a_qnx_reply_t *out_reply
) {
    if (!out_reply || !expected_l01_seal) {
        return -EINVAL;
    }
    if (!g_initialized) {
        spec411_init(&g_sluice);
        g_initialized = true;
    }

    vektor_a_qnx_msg_t msg;
    struct _msg_info   info;
    struct sigevent    event;
    SIGEV_UNBLOCK_INIT(&event);

    if (TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_RECEIVE, &event, &timeout_ns, NULL) < 0) {
        g_sluice.omega_t_kill_latch = 1U;
        g_sluice.omega_t_en         = 0U;
        return -ETIMEDOUT;
    }

    rcvid_t rcvid = MsgReceive(chid, &msg, sizeof(msg), &info);
    if (rcvid < 0) {
        g_sluice.omega_t_kill_latch = 1U;
        g_sluice.omega_t_en         = 0U;
        return -errno;
    }
    if (rcvid == 0) {
        /* Kernel pulse / client disconnect -> fail-closed KILL on Omega_T; Omega_Y stays 1 */
        g_sluice.omega_t_kill_latch = 1U;
        g_sluice.omega_t_en         = 0U;
        g_sluice.omega_y_en         = 1U;
        return -EPIPE;
    }

    uint8_t hw_byte = 0x01U;
    if (msg.cmd == VEKTOR_A_QNX_CMD_L01_RESET) {
        if (!vektor_a_qnx_seal_eq(msg.l01_reset_seal, expected_l01_seal)) {
            g_sluice.omega_t_kill_latch = 1U;
            g_sluice.omega_t_en         = 0U;
            g_sluice.omega_y_en         = 1U;
            (void)MsgError(rcvid, EPERM);
            return -EPERM;
        }
        spec411_l01_reset(&g_sluice);
        hw_byte = spec411_pack_hw_byte(&g_sluice);
    } else if (msg.cmd == VEKTOR_A_QNX_CMD_STEP) {
        hw_byte = spec411_step(
            &g_sluice,
            msg.tdc_valid,
            msg.tdc_tof_ps,
            msg.win_valid,
            msg.sapphire_meas_ticks,
            msg.bilat_50_50_sealed,
            msg.delta_k_num,
            msg.delta_k_den,
            msg.eps_num,
            msg.eps_den,
            msg.rho_n,
            msg.k_gamma,
            msg.avg_l01_trigger
        );
    } else {
        g_sluice.omega_t_kill_latch = 1U;
        g_sluice.omega_t_en         = 0U;
        (void)MsgError(rcvid, EBADMSG);
        return -EBADMSG;
    }

    out_reply->step_seq         = g_sluice.step_seq;
    out_reply->reset_epoch      = g_sluice.reset_epoch;
    out_reply->hw_port_byte     = hw_byte;
    out_reply->core_wake_en     = g_sluice.airlock.core_wake_en;
    out_reply->causal_hold      = g_sluice.airlock.causal_hold;
    out_reply->clock_drift_kill = g_sluice.airlock.clock_drift_kill;

    if (MsgReply(rcvid, EOK, out_reply, sizeof(*out_reply)) < 0) {
        g_sluice.omega_t_kill_latch = 1U;
        g_sluice.omega_t_en         = 0U;
        return -errno;
    }
    return 0;
}
