/*
 * Tier 4.30d local C tests for the multi-core lifecycle split.
 *
 * This is a source/local-host gate only. It proves that the dedicated
 * lifecycle_core profile owns direct lifecycle mutation, that duplicate/stale
 * lifecycle events are counted, and that active-mask synchronization has an
 * explicit MCPL/multicast-target stub before any EBRAINS package.
 */

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "config.h"
#include "host_interface.h"
#include "spin1_api.h"
#include "state_manager.h"

uint32_t g_timestep = 0;
int32_t g_dopamine_level = 0;

static sdp_msg_t g_test_msg;

static uint8_t _dispatch(uint8_t cmd, uint32_t arg1, uint32_t arg2, uint32_t arg3) {
    memset(&g_test_msg, 0, sizeof(g_test_msg));
    g_test_msg.cmd_rc = cmd;
    g_test_msg.arg1 = arg1;
    g_test_msg.arg2 = arg2;
    g_test_msg.arg3 = arg3;
    sdp_rx_callback((uint)(uintptr_t)&g_test_msg, 0);
    return (uint8_t)((g_test_last_sdp_msg.cmd_rc >> 8) & 0xFF);
}

static void test_lifecycle_core_profile_host_surface(void) {
    cra_state_init();
    assert(_dispatch(CMD_READ_STATE, 0, 0, 0) == 0);
    assert((g_test_last_sdp_msg.data[70] & 0x0F) == PROFILE_LIFECYCLE_CORE);

    assert(_dispatch(CMD_LIFECYCLE_INIT, MAX_LIFECYCLE_SLOTS, 2, 42) == 0);
    assert(_dispatch(CMD_LIFECYCLE_READ_STATE, 0, 0, 0) == 0);
    assert(g_test_last_sdp_msg.data[0] == LIFECYCLE_SCHEMA_VERSION);
    assert(_dispatch(CMD_WRITE_CONTEXT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_WRITE_ROUTE_SLOT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_WRITE_MEMORY_SLOT, 1, FP_ONE, FP_ONE) == 0xFF);
    assert(_dispatch(CMD_WRITE_SCHEDULE_ENTRY, 0, 0, 0) == 0xFF);
    printf("  PASS: lifecycle_core direct host surface is isolated\n");
}

static void test_event_request_duplicate_stale_guards(void) {
    cra_state_init();
    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);

    assert(cra_lifecycle_handle_trophic_request(0, 0, FP_ONE / 8, 0) == 0);
    assert(cra_lifecycle_handle_trophic_request(0, 0, FP_ONE / 8, 0) == -1);
    assert(cra_lifecycle_handle_trophic_request(2, 0, FP_ONE / 8, 0) == 0);
    assert(cra_lifecycle_handle_trophic_request(1, 0, FP_ONE / 8, 0) == -1);

    cra_state_summary_t runtime_summary;
    cra_lifecycle_summary_t lifecycle_summary;
    cra_state_get_summary(&runtime_summary);
    cra_lifecycle_get_summary(&lifecycle_summary);
    assert(runtime_summary.lifecycle_event_acks_received == 2);
    assert(runtime_summary.lifecycle_duplicate_events == 1);
    assert(runtime_summary.lifecycle_stale_events == 1);
    assert(lifecycle_summary.invalid_event_count == 2);
    printf("  PASS: lifecycle duplicate/stale guards are explicit\n");
}

static void test_active_mask_sync_send_and_receive(void) {
    cra_state_init();
    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);

    g_test_last_mc_key = 0;
    g_test_last_mc_payload = 0;
    g_test_last_mc_with_payload = 0;
    g_test_mc_packet_count = 0;
    memset(g_test_mc_keys, 0, sizeof(g_test_mc_keys));
    memset(g_test_mc_payloads, 0, sizeof(g_test_mc_payloads));
    memset(g_test_mc_with_payloads, 0, sizeof(g_test_mc_with_payloads));
    assert(cra_lifecycle_handle_event_request(
        0,
        LIFECYCLE_EVENT_CLEAVAGE,
        0,
        0,
        2,
        0,
        0) == 0);

    cra_state_summary_t summary;
    cra_state_get_summary(&summary);
    assert(summary.lifecycle_event_acks_received == 1);
    assert(summary.lifecycle_mask_syncs_sent == 1);
    assert(g_test_mc_packet_count == 2);
    assert(EXTRACT_MCPL_MSG_TYPE(g_test_mc_keys[0]) == MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC);
    assert(EXTRACT_MCPL_LOOKUP_TYPE(g_test_mc_keys[0]) == MCPL_LIFECYCLE_SYNC_MASK);
    assert((g_test_mc_payloads[0] & 0xFFFF) == 7);
    assert(((g_test_mc_payloads[0] >> 16) & 0xFF) == 3);
    assert(g_test_mc_with_payloads[0] == WITH_PAYLOAD);

    cra_lifecycle_summary_t lifecycle_summary;
    cra_lifecycle_get_summary(&lifecycle_summary);
    assert(EXTRACT_MCPL_MSG_TYPE(g_test_mc_keys[1]) == MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC);
    assert(EXTRACT_MCPL_LOOKUP_TYPE(g_test_mc_keys[1]) == MCPL_LIFECYCLE_SYNC_LINEAGE);
    assert(g_test_mc_payloads[1] == lifecycle_summary.lineage_checksum);
    assert(g_test_mc_with_payloads[1] == WITH_PAYLOAD);

    cra_lifecycle_receive_active_mask_sync(12, 63, 105428);
    cra_state_get_summary(&summary);
    assert(summary.lifecycle_mask_syncs_received == 1);
    assert(summary.lifecycle_last_seen_event_count == 12);
    assert(summary.lifecycle_last_seen_active_mask_bits == 63);
    assert(summary.lifecycle_last_seen_lineage_checksum == 105428);
    printf("  PASS: active-mask/count/lineage sync send/receive bookkeeping\n");
}

static void test_learning_side_request_stubs(void) {
    cra_state_init();
    g_test_last_mc_key = 0;
    g_test_last_mc_payload = 0;
    g_test_last_mc_with_payload = 0;
    g_test_mc_packet_count = 0;

    cra_lifecycle_send_event_request_stub(5, LIFECYCLE_EVENT_DEATH, 3);
    assert(EXTRACT_MCPL_MSG_TYPE(g_test_last_mc_key) == MCPL_MSG_LIFECYCLE_EVENT_REQUEST);
    assert(EXTRACT_MCPL_LOOKUP_TYPE(g_test_last_mc_key) == LIFECYCLE_EVENT_DEATH);
    assert(EXTRACT_MCPL_SEQ_ID(g_test_last_mc_key) == 5);
    assert(g_test_last_mc_payload == 3);

    cra_lifecycle_send_trophic_update_stub(4, FP_ONE / 4);
    assert(EXTRACT_MCPL_MSG_TYPE(g_test_last_mc_key) == MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE);
    assert(EXTRACT_MCPL_SEQ_ID(g_test_last_mc_key) == 4);
    assert((int32_t)g_test_last_mc_payload == FP_ONE / 4);

    cra_lifecycle_record_missing_ack();
    cra_state_summary_t summary;
    cra_state_get_summary(&summary);
    assert(summary.lifecycle_event_requests_sent == 1);
    assert(summary.lifecycle_trophic_requests_sent == 1);
    assert(summary.lifecycle_missing_acks == 1);
    printf("  PASS: learning-side lifecycle request stubs\n");
}

int main(void) {
    printf("Running Tier 4.30d lifecycle split tests...\n");
    test_lifecycle_core_profile_host_surface();
    test_event_request_duplicate_stale_guards();
    test_active_mask_sync_send_and_receive();
    test_learning_side_request_stubs();
    printf("All lifecycle split tests passed.\n");
    return 0;
}
