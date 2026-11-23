/*
 * omega_qnx_resmgr.c — QNX Neutrino 8.0 Fixed-Priority Safety Cage (0 float, 0 malloc)
 * ====================================================================================
 * Surface          : L2_GATE/omega_qnx_resmgr.c
 * Target           : QNX SDP 8.0 (x86_64 & aarch64le), -std=gnu11 -O2 -Wall -Wextra -Werror
 * Epistemic Tier   : L1.5 QNX 8.0 Cross-Compiled C11 Gate (PHYSICAL_AUTHORITY = NONE)
 * Epistemic Bound  : INSPIRED_BY != IMPLEMENTS != PROVES
 * Guarantees       :
 *   - _NTO_CHF_FIXED_PRIORITY | _NTO_CHF_DISCONNECT (no priority collapse, no _NTO_CHF_UNBLOCK)
 *   - CLOCK_MONOTONIC TimerTimeout + zero timer coalescing tolerance
 *   - mlockall(MCL_CURRENT | MCL_FUTURE) + permanent procmgr_ability lockdown
 *   - 0 float, 0 malloc, sticky KILL on timeout, disconnect, or conservation breach
 */
#include <errno.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/neutrino.h>
#include <sys/procmgr.h>

#include "omega_spi_frame_64b.h"

extern bool omega_pack_verified_frame_64b(
    omega_spi_frame_64b_t *out_frame,
    uint64_t expected_step,
    uint64_t l_init,
    uint64_t l_now,
    uint64_t l_heat,
    const int64_t q_um[3],
    const int64_t p_fp[3],
    uint32_t prev_crc32
);

typedef struct {
    uint64_t step_counter;
    uint32_t last_valid_crc32;
    bool     sticky_kill;
} omega_qnx_cage_state_t;

typedef struct {
    uint64_t l_init;
    uint64_t l_now;
    uint64_t l_heat;
    int64_t  q_um[3];
    int64_t  p_fp[3];
} omega_qnx_candidate_msg_t;

static omega_qnx_cage_state_t g_cage = {
    .step_counter     = 1ULL,
    .last_valid_crc32 = 0U,
    .sticky_kill      = false
};

/* Create fixed-priority synchronous channel (omits _NTO_CHF_UNBLOCK by design) */
int omega_qnx_create_fixed_channel(void) {
    return ChannelCreate(_NTO_CHF_FIXED_PRIORITY | _NTO_CHF_DISCONNECT);
}

/* Lock zero timer coalescing, lock RAM, and permanently drop OS abilities */
int omega_qnx_harden_process(void) {
    uint64_t zero_tol = 0ULL;
    uint64_t old_tol = 0ULL;

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

/* Deterministic message receive with hard CLOCK_MONOTONIC deadline */
int omega_qnx_receive_and_gate(
    int chid,
    uint64_t timeout_ns,
    omega_spi_frame_64b_t *out_verified_frame
) {
    if (!out_verified_frame || g_cage.sticky_kill) {
        return -EPERM; /* Latched in 0.00 V DC KILL */
    }

    omega_qnx_candidate_msg_t candidate_msg;
    struct _msg_info info;
    struct sigevent event;
    SIGEV_UNBLOCK_INIT(&event);

    if (TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_RECEIVE, &event, &timeout_ns, NULL) < 0) {
        g_cage.sticky_kill = true;
        return -ETIMEDOUT;
    }

    rcvid_t rcvid = MsgReceive(chid, &candidate_msg, sizeof(candidate_msg), &info);
    if (rcvid < 0) {
        g_cage.sticky_kill = true;
        return -errno;
    }
    if (rcvid == 0) {
        /* Kernel pulse (e.g. client disconnect) -> fail-closed sticky KILL */
        g_cage.sticky_kill = true;
        return -EPIPE;
    }

    bool ok = omega_pack_verified_frame_64b(
        out_verified_frame,
        g_cage.step_counter,
        candidate_msg.l_init,
        candidate_msg.l_now,
        candidate_msg.l_heat,
        candidate_msg.q_um,
        candidate_msg.p_fp,
        g_cage.last_valid_crc32
    );

    if (!ok) {
        g_cage.sticky_kill = true;
        (void)MsgError(rcvid, EBADMSG);
        return -EBADMSG;
    }

    if (MsgReply(rcvid, EOK, NULL, 0) < 0) {
        g_cage.sticky_kill = true;
        return -errno;
    }

    g_cage.step_counter += 1ULL;
    g_cage.last_valid_crc32 = out_verified_frame->crc32_witness;
    return 0;
}
