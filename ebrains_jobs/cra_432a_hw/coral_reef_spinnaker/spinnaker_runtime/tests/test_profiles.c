/*
 * Host-side profile tests for the 4.26 four-core distributed runtime.
 *
 * Build with one profile flag at a time:
 *   cc -I stubs -I src -DCRA_RUNTIME_PROFILE_CONTEXT_CORE=1 \
 *      -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=4 \
 *      tests/test_profiles.c src/state_manager.c src/host_interface.c -o test_context_core
 *
 * This file is compiled four times (once per 4.26 profile) by the Makefile
 * test-profiles target.
 */

#include <stdio.h>
#include <string.h>
#include <assert.h>

#include "config.h"
#include "state_manager.h"
#include "host_interface.h"
#include "spin1_api.h"

/* Stub symbols normally defined in main.c */
uint32_t g_timestep = 0;
int32_t  g_dopamine_level = 0;

/* Access last SDP reply constructed by sdp_send_reply */
static sdp_msg_t *_last_reply(void) {
    return spin1_msg_get();
}

/* Global test message to ensure address survives uint truncation on 64-bit hosts */
static sdp_msg_t g_test_msg;

/* Build and dispatch an SDP command, return status byte (0=ack, 0xFF=nak) */
static uint8_t _dispatch(uint8_t cmd, uint32_t arg1, uint32_t arg2, uint32_t arg3) {
    memset(&g_test_msg, 0, sizeof(g_test_msg));
    g_test_msg.cmd_rc = cmd;
    g_test_msg.arg1 = arg1;
    g_test_msg.arg2 = arg2;
    g_test_msg.arg3 = arg3;
    sdp_rx_callback((uint)(uintptr_t)&g_test_msg, 0);
    return (uint8_t)((_last_reply()->cmd_rc >> 8) & 0xFF);
}

/* ------------------------------------------------------------------ */
/* Generic tests (all profiles)                                        */
/* ------------------------------------------------------------------ */

static void test_reset(void) {
    uint8_t status = _dispatch(CMD_RESET, 0, 0, 0);
    assert(status == 0);
    printf("  PASS: RESET ack\n");
}

static void test_read_state_profile_id(void) {
    uint8_t status = _dispatch(CMD_READ_STATE, 0, 0, 0);
    assert(status == 0);
    sdp_msg_t *reply = _last_reply();
    /* reply->data[0..102] maps to payload[2..104] from host_if_pack_state_summary */
    uint8_t packed = reply->data[70];
    uint8_t profile_id = packed & 0x0F;
    uint8_t flags      = (packed >> 4) & 0x0F;
    assert(profile_id == RUNTIME_PROFILE_ID);
    assert(flags == 0);
    printf("  PASS: READ_STATE profile_id=%d flags=%d\n", profile_id, flags);
}

/* ------------------------------------------------------------------ */
/* Profile-specific handler tests                                      */
/* ------------------------------------------------------------------ */

#ifdef CRA_RUNTIME_PROFILE_CONTEXT_CORE
static void test_expected_handlers(void) {
    assert(_dispatch(CMD_WRITE_CONTEXT, 1, FP_ONE, FP_ONE) == 0);
    assert(_dispatch(CMD_READ_CONTEXT, 1, 0, 0) == 0);
    assert(_dispatch(CMD_RUN_CONTINUOUS, 0, 0, 0) == 0);
    assert(_dispatch(CMD_PAUSE, 0, 0, 0) == 0);
    printf("  PASS: context_core expected commands ack\n");
}
static void test_unexpected_handlers(void) {
    assert(_dispatch(CMD_WRITE_ROUTE_SLOT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_ROUTE_SLOT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_MEMORY_SLOT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_MEMORY_SLOT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_SCHEDULE_ENTRY, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_MATURE_PENDING, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_LIFECYCLE_INIT, MAX_LIFECYCLE_SLOTS, 2, 42) == 0xFF);
    assert(_dispatch(CMD_LIFECYCLE_READ_STATE, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_INIT, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_UPDATE, FP_ONE, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_READ_STATE, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_SHAM_MODE, TEMPORAL_SHAM_ZERO_STATE, 0, 0) == 0xFF);
    printf("  PASS: context_core unexpected commands nak\n");
}
static void test_lookup_request(void) {
    /* Write a context slot and verify lookup returns correct value */
    _dispatch(CMD_WRITE_CONTEXT, 42, FP_ONE, FP_HALF);
    g_test_last_sdp_msg_valid = 0;
    _dispatch(CMD_LOOKUP_REQUEST, 100, 42, LOOKUP_TYPE_CONTEXT);
    assert(g_test_last_sdp_msg_valid == 1);
    assert(g_test_last_sdp_msg.cmd_rc == CMD_LOOKUP_REPLY);
    assert(g_test_last_sdp_msg.arg1 == 100);               /* seq_id */
    assert((int32_t)g_test_last_sdp_msg.arg2 == FP_ONE);    /* value */
    assert((int32_t)g_test_last_sdp_msg.arg3 == FP_HALF);   /* confidence */
    assert(g_test_last_sdp_msg.data[0] == 1);               /* hit */
    assert(g_test_last_sdp_msg.data[1] == 0);               /* status ok */
    printf("  PASS: lookup request/reply format\n");
}
static void test_lookup_wrong_type(void) {
    /* Wrong-profile lookup should return error status, not crash */
    g_test_last_sdp_msg_valid = 0;
    _dispatch(CMD_LOOKUP_REQUEST, 101, 1, LOOKUP_TYPE_ROUTE);
    assert(g_test_last_sdp_msg_valid == 1);
    assert(g_test_last_sdp_msg.data[1] == 1); /* error status */
    assert(g_test_last_sdp_msg.data[0] == 0); /* miss */
    printf("  PASS: wrong-type lookup rejected safely\n");
}
#elif CRA_RUNTIME_PROFILE_ROUTE_CORE
static void test_expected_handlers(void) {
    assert(_dispatch(CMD_WRITE_ROUTE_SLOT, 1, FP_ONE, FP_ONE) == 0);
    assert(_dispatch(CMD_READ_ROUTE_SLOT, 1, 0, 0) == 0);
    assert(_dispatch(CMD_RUN_CONTINUOUS, 0, 0, 0) == 0);
    assert(_dispatch(CMD_PAUSE, 0, 0, 0) == 0);
    printf("  PASS: route_core expected commands ack\n");
}
static void test_unexpected_handlers(void) {
    assert(_dispatch(CMD_WRITE_CONTEXT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_CONTEXT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_MEMORY_SLOT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_MEMORY_SLOT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_SCHEDULE_ENTRY, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_MATURE_PENDING, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_LIFECYCLE_INIT, MAX_LIFECYCLE_SLOTS, 2, 42) == 0xFF);
    assert(_dispatch(CMD_LIFECYCLE_READ_STATE, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_INIT, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_UPDATE, FP_ONE, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_READ_STATE, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_SHAM_MODE, TEMPORAL_SHAM_ZERO_STATE, 0, 0) == 0xFF);
    printf("  PASS: route_core unexpected commands nak\n");
}
static void test_lookup_request(void) {
    _dispatch(CMD_WRITE_ROUTE_SLOT, 7, FP_ONE, FP_HALF);
    g_test_last_sdp_msg_valid = 0;
    _dispatch(CMD_LOOKUP_REQUEST, 200, 7, LOOKUP_TYPE_ROUTE);
    assert(g_test_last_sdp_msg_valid == 1);
    assert(g_test_last_sdp_msg.cmd_rc == CMD_LOOKUP_REPLY);
    assert(g_test_last_sdp_msg.arg1 == 200);
    assert((int32_t)g_test_last_sdp_msg.arg2 == FP_ONE);
    assert((int32_t)g_test_last_sdp_msg.arg3 == FP_HALF);
    assert(g_test_last_sdp_msg.data[0] == 1);
    assert(g_test_last_sdp_msg.data[1] == 0);
    printf("  PASS: lookup request/reply format\n");
}
static void test_lookup_wrong_type(void) {
    g_test_last_sdp_msg_valid = 0;
    _dispatch(CMD_LOOKUP_REQUEST, 201, 1, LOOKUP_TYPE_MEMORY);
    assert(g_test_last_sdp_msg_valid == 1);
    assert(g_test_last_sdp_msg.data[1] == 1);
    assert(g_test_last_sdp_msg.data[0] == 0);
    printf("  PASS: wrong-type lookup rejected safely\n");
}
#elif CRA_RUNTIME_PROFILE_MEMORY_CORE
static void test_expected_handlers(void) {
    assert(_dispatch(CMD_WRITE_MEMORY_SLOT, 1, FP_ONE, FP_ONE) == 0);
    assert(_dispatch(CMD_READ_MEMORY_SLOT, 1, 0, 0) == 0);
    assert(_dispatch(CMD_RUN_CONTINUOUS, 0, 0, 0) == 0);
    assert(_dispatch(CMD_PAUSE, 0, 0, 0) == 0);
    printf("  PASS: memory_core expected commands ack\n");
}
static void test_unexpected_handlers(void) {
    assert(_dispatch(CMD_WRITE_CONTEXT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_CONTEXT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_ROUTE_SLOT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_ROUTE_SLOT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_SCHEDULE_ENTRY, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_MATURE_PENDING, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_LIFECYCLE_INIT, MAX_LIFECYCLE_SLOTS, 2, 42) == 0xFF);
    assert(_dispatch(CMD_LIFECYCLE_READ_STATE, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_INIT, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_UPDATE, FP_ONE, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_READ_STATE, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_SHAM_MODE, TEMPORAL_SHAM_ZERO_STATE, 0, 0) == 0xFF);
    printf("  PASS: memory_core unexpected commands nak\n");
}
static void test_lookup_request(void) {
    _dispatch(CMD_WRITE_MEMORY_SLOT, 9, FP_ONE, FP_HALF);
    g_test_last_sdp_msg_valid = 0;
    _dispatch(CMD_LOOKUP_REQUEST, 300, 9, LOOKUP_TYPE_MEMORY);
    assert(g_test_last_sdp_msg_valid == 1);
    assert(g_test_last_sdp_msg.cmd_rc == CMD_LOOKUP_REPLY);
    assert(g_test_last_sdp_msg.arg1 == 300);
    assert((int32_t)g_test_last_sdp_msg.arg2 == FP_ONE);
    assert((int32_t)g_test_last_sdp_msg.arg3 == FP_HALF);
    assert(g_test_last_sdp_msg.data[0] == 1);
    assert(g_test_last_sdp_msg.data[1] == 0);
    printf("  PASS: lookup request/reply format\n");
}
static void test_lookup_wrong_type(void) {
    g_test_last_sdp_msg_valid = 0;
    _dispatch(CMD_LOOKUP_REQUEST, 301, 1, LOOKUP_TYPE_CONTEXT);
    assert(g_test_last_sdp_msg_valid == 1);
    assert(g_test_last_sdp_msg.data[1] == 1);
    assert(g_test_last_sdp_msg.data[0] == 0);
    printf("  PASS: wrong-type lookup rejected safely\n");
}
#elif CRA_RUNTIME_PROFILE_LEARNING_CORE
static void test_expected_handlers(void) {
    assert(_dispatch(CMD_WRITE_SCHEDULE_ENTRY, 0, 0, 0) == 0);
    assert(_dispatch(CMD_RUN_CONTINUOUS, 0, 0, 0) == 0);
    assert(_dispatch(CMD_PAUSE, 0, 0, 0) == 0);
    /* CMD_MATURE_PENDING returns status 1 when no pending exists (not NAK) */
    assert(_dispatch(CMD_MATURE_PENDING, 0, 0, 0) != 0xFF);
    assert(_dispatch(CMD_TEMPORAL_INIT, 0, 0, 0) == 0);
    assert(_dispatch(CMD_TEMPORAL_UPDATE, FP_ONE, 0, 0) == 0);
    assert(_dispatch(CMD_TEMPORAL_READ_STATE, 0, 0, 0) == 0);
    assert(_dispatch(CMD_TEMPORAL_SHAM_MODE, TEMPORAL_SHAM_ZERO_STATE, 0, 0) == 0);
    printf("  PASS: learning_core expected commands ack\n");
}
static void test_unexpected_handlers(void) {
    assert(_dispatch(CMD_WRITE_CONTEXT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_CONTEXT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_ROUTE_SLOT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_ROUTE_SLOT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_MEMORY_SLOT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_MEMORY_SLOT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_LIFECYCLE_INIT, MAX_LIFECYCLE_SLOTS, 2, 42) == 0xFF);
    assert(_dispatch(CMD_LIFECYCLE_READ_STATE, 0, 0, 0) == 0xFF);
    printf("  PASS: learning_core unexpected commands nak\n");
}
static void test_lookup_state_machine(void) {
    /* Send 3 parallel lookups for one event */
    assert(cra_state_lookup_send(10, 1, LOOKUP_TYPE_CONTEXT, 0) == 0);
    assert(cra_state_lookup_send(11, 2, LOOKUP_TYPE_ROUTE,   0) == 0);
    assert(cra_state_lookup_send(12, 3, LOOKUP_TYPE_MEMORY,  0) == 0);

    /* Receive all 3 replies */
    assert(cra_state_lookup_receive(10, FP_ONE, FP_HALF, 1) == 0);
    assert(cra_state_lookup_receive(11, FP_ONE, FP_HALF, 1) == 0);
    assert(cra_state_lookup_receive(12, FP_ONE, FP_HALF, 1) == 0);

    /* Verify all marked received */
    assert(cra_state_lookup_is_received(10) == 1);
    assert(cra_state_lookup_is_received(11) == 1);
    assert(cra_state_lookup_is_received(12) == 1);

    /* Verify stored results */
    int32_t v, c;
    uint8_t h;
    assert(cra_state_lookup_get_result(10, &v, &c, &h) == 0);
    assert(v == FP_ONE && c == FP_HALF && h == 1);
    assert(cra_state_lookup_get_result(11, &v, &c, &h) == 0);
    assert(v == FP_ONE && c == FP_HALF && h == 1);
    assert(cra_state_lookup_get_result(12, &v, &c, &h) == 0);
    assert(v == FP_ONE && c == FP_HALF && h == 1);

    printf("  PASS: lookup state machine (3 replies stored)\n");
}
static void test_stale_reply(void) {
    assert(cra_state_lookup_send(20, 1, LOOKUP_TYPE_CONTEXT, 0) == 0);
    assert(cra_state_lookup_receive(20, FP_ONE, FP_HALF, 1) == 0);
    /* Duplicate reply with same seq_id -> stale */
    assert(cra_state_lookup_receive(20, FP_ONE, FP_HALF, 1) == -1);
    /* Unknown seq_id -> stale */
    assert(cra_state_lookup_receive(99, FP_ONE, FP_HALF, 1) == -1);
    assert(cra_state_lookup_is_stale(99) == 1);
    assert(cra_state_lookup_is_stale(20) == 0); /* known, just received */
    printf("  PASS: stale reply detection\n");
}
static void test_timeout(void) {
    assert(cra_state_lookup_send(30, 1, LOOKUP_TYPE_CONTEXT, 0) == 0);
    uint32_t timed_out[4];
    assert(cra_state_lookup_check_timeout(5, timed_out, 4) == 0);  /* not yet */
    assert(cra_state_lookup_check_timeout(15, timed_out, 4) == 1); /* timed out */
    assert(timed_out[0] == 30);
    printf("  PASS: timeout detection\n");
}
#elif CRA_RUNTIME_PROFILE_LIFECYCLE_CORE
static void test_expected_handlers(void) {
    assert(_dispatch(CMD_LIFECYCLE_INIT, MAX_LIFECYCLE_SLOTS, 2, 42) == 0);
    assert(_dispatch(CMD_LIFECYCLE_READ_STATE, 0, 0, 0) == 0);
    assert(_dispatch(CMD_LIFECYCLE_SHAM_MODE, LIFECYCLE_SHAM_FIXED_POOL, 0, 0) == 0);
    printf("  PASS: lifecycle_core expected commands ack\n");
}
static void test_unexpected_handlers(void) {
    assert(_dispatch(CMD_WRITE_CONTEXT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_CONTEXT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_ROUTE_SLOT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_ROUTE_SLOT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_MEMORY_SLOT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_READ_MEMORY_SLOT, 1, 0, 0) == 0xFF);
    assert(_dispatch(CMD_WRITE_SCHEDULE_ENTRY, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_MATURE_PENDING, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_RUN_CONTINUOUS, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_PAUSE, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_INIT, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_UPDATE, FP_ONE, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_READ_STATE, 0, 0, 0) == 0xFF);
    assert(_dispatch(CMD_TEMPORAL_SHAM_MODE, TEMPORAL_SHAM_ZERO_STATE, 0, 0) == 0xFF);
    printf("  PASS: lifecycle_core unexpected commands nak\n");
}
#else
static void test_expected_handlers(void) {
    printf("  SKIP: no profile-specific handler tests for this profile\n");
}
static void test_unexpected_handlers(void) {
    printf("  SKIP: no profile-specific handler tests for this profile\n");
}
static void test_lookup_request(void) {
    printf("  SKIP: no lookup tests for this profile\n");
}
static void test_lookup_wrong_type(void) {
    printf("  SKIP: no lookup tests for this profile\n");
}
#endif

/* ------------------------------------------------------------------ */
/* Main                                                                */
/* ------------------------------------------------------------------ */

int main(void) {
    printf("Profile test (RUNTIME_PROFILE_ID=%d)\n", RUNTIME_PROFILE_ID);
    cra_state_init();
    host_if_init();
    test_reset();
    test_read_state_profile_id();
    test_expected_handlers();
    test_unexpected_handlers();
#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
    test_lookup_request();
    test_lookup_wrong_type();
#endif
#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
    test_lookup_state_machine();
    test_stale_reply();
    test_timeout();
#endif
    printf("All tests passed.\n");
    return 0;
}
