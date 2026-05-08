/*
 * Tier 4.32g local C tests for lifecycle MCPL receive semantics.
 *
 * Tier 4.32g hardware evidence requires more than route entries: the callback
 * must decode lifecycle event/trophic requests on the lifecycle core and
 * active-mask/lineage sync packets on the learning/consumer core.
 */

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "config.h"
#include "spin1_api.h"
#include "state_manager.h"

uint32_t g_timestep = 0;
int32_t g_dopamine_level = 0;

static void _clear_mc_packets(void) {
    g_test_last_mc_key = 0;
    g_test_last_mc_payload = 0;
    g_test_last_mc_with_payload = 0;
    g_test_mc_packet_count = 0;
    memset(g_test_mc_keys, 0, sizeof(g_test_mc_keys));
    memset(g_test_mc_payloads, 0, sizeof(g_test_mc_payloads));
    memset(g_test_mc_with_payloads, 0, sizeof(g_test_mc_with_payloads));
}

#ifdef CRA_RUNTIME_PROFILE_LIFECYCLE_CORE
static void test_lifecycle_core_receives_request_packets(void) {
    cra_state_init();
    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);
    _clear_mc_packets();

    uint32_t trophic_key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE,
        0,
        0);
    cra_state_mcpl_lookup_receive(trophic_key, (uint32_t)(FP_ONE / 8));

    cra_state_summary_t runtime_summary;
    cra_lifecycle_summary_t lifecycle_summary;
    cra_state_get_summary(&runtime_summary);
    cra_lifecycle_get_summary(&lifecycle_summary);
    assert(runtime_summary.lifecycle_event_acks_received == 1);
    assert(lifecycle_summary.trophic_update_count == 1);

    uint32_t death_key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_EVENT_REQUEST,
        LIFECYCLE_EVENT_DEATH,
        1);
    cra_state_mcpl_lookup_receive(death_key, 1);

    cra_state_get_summary(&runtime_summary);
    cra_lifecycle_get_summary(&lifecycle_summary);
    assert(runtime_summary.lifecycle_event_acks_received == 2);
    assert(runtime_summary.lifecycle_mask_syncs_sent == 1);
    assert(lifecycle_summary.active_mask_bits == 1);
    assert(lifecycle_summary.death_count == 1);
    assert(g_test_mc_packet_count == 2);
    assert(EXTRACT_MCPL_MSG_TYPE(g_test_mc_keys[0]) == MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC);
    assert(EXTRACT_MCPL_LOOKUP_TYPE(g_test_mc_keys[0]) == MCPL_LIFECYCLE_SYNC_MASK);
    assert(EXTRACT_MCPL_MSG_TYPE(g_test_mc_keys[1]) == MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC);
    assert(EXTRACT_MCPL_LOOKUP_TYPE(g_test_mc_keys[1]) == MCPL_LIFECYCLE_SYNC_LINEAGE);
    printf("  PASS: lifecycle_core receives trophic/event MCPL requests\n");
}
#endif

#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
static void test_learning_core_receives_mask_lineage_sync_packets(void) {
    cra_state_init();

    uint32_t lineage_key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC,
        MCPL_LIFECYCLE_SYNC_LINEAGE,
        7);
    uint32_t mask_key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC,
        MCPL_LIFECYCLE_SYNC_MASK,
        7);

    cra_state_mcpl_lookup_receive(lineage_key, 0x00ABCDEF);
    cra_state_summary_t summary;
    cra_state_get_summary(&summary);
    assert(summary.lifecycle_mask_syncs_received == 0);

    cra_state_mcpl_lookup_receive(mask_key, 0x00020005);
    cra_state_get_summary(&summary);
    assert(summary.lifecycle_mask_syncs_received == 1);
    assert(summary.lifecycle_last_seen_event_count == 7);
    assert(summary.lifecycle_last_seen_active_mask_bits == 5);
    assert(summary.lifecycle_last_seen_lineage_checksum == 0x00ABCDEF);

    uint32_t mask_key_8 = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC,
        MCPL_LIFECYCLE_SYNC_MASK,
        8);
    uint32_t lineage_key_8 = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC,
        MCPL_LIFECYCLE_SYNC_LINEAGE,
        8);
    cra_state_mcpl_lookup_receive(mask_key_8, 0x00010001);
    cra_state_get_summary(&summary);
    assert(summary.lifecycle_mask_syncs_received == 1);
    cra_state_mcpl_lookup_receive(lineage_key_8, 0x0000CAFE);
    cra_state_get_summary(&summary);
    assert(summary.lifecycle_mask_syncs_received == 2);
    assert(summary.lifecycle_last_seen_event_count == 8);
    assert(summary.lifecycle_last_seen_active_mask_bits == 1);
    assert(summary.lifecycle_last_seen_lineage_checksum == 0x0000CAFE);
    printf("  PASS: learning_core coalesces mask/lineage sync MCPL packets\n");
}
#endif

int main(void) {
    printf("Running Tier 4.32g lifecycle MCPL receive contract tests...\n");
#ifdef CRA_RUNTIME_PROFILE_LIFECYCLE_CORE
    test_lifecycle_core_receives_request_packets();
#endif
#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
    test_learning_core_receives_mask_lineage_sync_packets();
#endif
#if !defined(CRA_RUNTIME_PROFILE_LIFECYCLE_CORE) && !defined(CRA_RUNTIME_PROFILE_LEARNING_CORE)
    printf("  SKIP: lifecycle receive contract only applies to learning/lifecycle profiles\n");
#endif
    printf("All lifecycle MCPL receive contract tests passed.\n");
    return 0;
}
