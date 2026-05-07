/*
 * Tier 4.32a-r1 MCPL lookup contract tests.
 *
 * Validates the repaired MCPL lookup path that must replace transitional SDP
 * before any MCPL-first hardware scale evidence is allowed:
 *   - replies carry value plus confidence/hit/status metadata
 *   - learning core waits for both value and meta packets
 *   - meta-before-value ordering is accepted
 *   - shard_id disambiguates identical seq/type lookups
 *   - wrong shard packets do not complete pending lookups
 */

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "config.h"
#include "state_manager.h"
#include "spin1_api.h"

uint32_t g_timestep = 0;

extern uint32_t g_test_last_mc_key;
extern uint32_t g_test_last_mc_payload;
extern uint32_t g_test_last_mc_with_payload;
extern uint32_t g_test_mc_packet_count;
extern uint32_t g_test_mc_keys[8];
extern uint32_t g_test_mc_payloads[8];
extern uint32_t g_test_mc_with_payloads[8];

static void reset_packets(void) {
    g_test_last_mc_key = 0;
    g_test_last_mc_payload = 0;
    g_test_last_mc_with_payload = 0;
    g_test_mc_packet_count = 0;
    for (uint32_t i = 0; i < 8; i++) {
        g_test_mc_keys[i] = 0;
        g_test_mc_payloads[i] = 0;
        g_test_mc_with_payloads[i] = 0;
    }
}

static void test_value_and_meta_send(void) {
    reset_packets();
    cra_state_mcpl_lookup_send_reply_shard(
        77, FP_FROM_FLOAT(-0.25f), FP_HALF, 1, 0,
        LOOKUP_TYPE_CONTEXT, 3, 7);

    assert(g_test_mc_packet_count == 2);
    assert(EXTRACT_MCPL_MSG_TYPE(g_test_mc_keys[0]) == MCPL_MSG_LOOKUP_REPLY_VALUE);
    assert(EXTRACT_MCPL_MSG_TYPE(g_test_mc_keys[1]) == MCPL_MSG_LOOKUP_REPLY_META);
    assert(EXTRACT_MCPL_LOOKUP_TYPE(g_test_mc_keys[0]) == LOOKUP_TYPE_CONTEXT);
    assert(EXTRACT_MCPL_LOOKUP_TYPE(g_test_mc_keys[1]) == LOOKUP_TYPE_CONTEXT);
    assert(EXTRACT_MCPL_SHARD_ID(g_test_mc_keys[0]) == 3);
    assert(EXTRACT_MCPL_SHARD_ID(g_test_mc_keys[1]) == 3);
    assert(EXTRACT_MCPL_SEQ_ID(g_test_mc_keys[0]) == 77);
    assert(EXTRACT_MCPL_SEQ_ID(g_test_mc_keys[1]) == 77);
    assert((int32_t)g_test_mc_payloads[0] == FP_FROM_FLOAT(-0.25f));
    assert(EXTRACT_MCPL_LOOKUP_META_CONF(g_test_mc_payloads[1]) == FP_HALF);
    assert(EXTRACT_MCPL_LOOKUP_META_HIT(g_test_mc_payloads[1]) == 1);
    assert(EXTRACT_MCPL_LOOKUP_META_STATUS(g_test_mc_payloads[1]) == 0);
    assert(g_test_mc_with_payloads[0] == WITH_PAYLOAD);
    assert(g_test_mc_with_payloads[1] == WITH_PAYLOAD);
    printf("  PASS: reply sends value plus confidence/meta packets\n");
}

static void test_receive_waits_for_both_packets(void) {
    cra_state_lookup_init();
    assert(cra_state_lookup_send_shard(10, 101, LOOKUP_TYPE_ROUTE, 2, 0) == 0);

    uint32_t value_key = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, LOOKUP_TYPE_ROUTE, 2, 10);
    uint32_t meta_key = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, LOOKUP_TYPE_ROUTE, 2, 10);

    cra_state_mcpl_lookup_receive(value_key, (uint32_t)FP_FROM_FLOAT(0.75f));
    assert(cra_state_lookup_is_received_shard(10, LOOKUP_TYPE_ROUTE, 2) == 0);

    cra_state_mcpl_lookup_receive(meta_key, PACK_MCPL_LOOKUP_META(FP_HALF, 1, 0));
    assert(cra_state_lookup_is_received_shard(10, LOOKUP_TYPE_ROUTE, 2) == 1);

    int32_t value = 0;
    int32_t confidence = 0;
    uint8_t hit = 0;
    assert(cra_state_lookup_get_result_shard(10, LOOKUP_TYPE_ROUTE, 2, &value, &confidence, &hit) == 0);
    assert(value == FP_FROM_FLOAT(0.75f));
    assert(confidence == FP_HALF);
    assert(hit == 1);
    printf("  PASS: receive waits for value and meta before completing lookup\n");
}

static void test_meta_before_value(void) {
    cra_state_lookup_init();
    assert(cra_state_lookup_send_shard(11, 202, LOOKUP_TYPE_MEMORY, 1, 0) == 0);

    uint32_t value_key = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, LOOKUP_TYPE_MEMORY, 1, 11);
    uint32_t meta_key = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, LOOKUP_TYPE_MEMORY, 1, 11);

    cra_state_mcpl_lookup_receive(meta_key, PACK_MCPL_LOOKUP_META(FP_FROM_FLOAT(0.25f), 1, 0));
    assert(cra_state_lookup_is_received_shard(11, LOOKUP_TYPE_MEMORY, 1) == 0);

    cra_state_mcpl_lookup_receive(value_key, (uint32_t)FP_FROM_FLOAT(-0.5f));
    assert(cra_state_lookup_is_received_shard(11, LOOKUP_TYPE_MEMORY, 1) == 1);

    int32_t value = 0;
    int32_t confidence = 0;
    uint8_t hit = 0;
    assert(cra_state_lookup_get_result_shard(11, LOOKUP_TYPE_MEMORY, 1, &value, &confidence, &hit) == 0);
    assert(value == FP_FROM_FLOAT(-0.5f));
    assert(confidence == FP_FROM_FLOAT(0.25f));
    assert(hit == 1);
    printf("  PASS: meta-before-value ordering is accepted\n");
}

static void test_shard_disambiguates_identical_seq_and_type(void) {
    cra_state_lookup_init();
    assert(cra_state_lookup_send_shard(42, 111, LOOKUP_TYPE_CONTEXT, 1, 0) == 0);
    assert(cra_state_lookup_send_shard(42, 222, LOOKUP_TYPE_CONTEXT, 2, 0) == 0);

    uint32_t s1_value = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, LOOKUP_TYPE_CONTEXT, 1, 42);
    uint32_t s1_meta = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, LOOKUP_TYPE_CONTEXT, 1, 42);
    uint32_t s2_value = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, LOOKUP_TYPE_CONTEXT, 2, 42);
    uint32_t s2_meta = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, LOOKUP_TYPE_CONTEXT, 2, 42);

    cra_state_mcpl_lookup_receive(s1_value, (uint32_t)FP_FROM_FLOAT(0.125f));
    cra_state_mcpl_lookup_receive(s1_meta, PACK_MCPL_LOOKUP_META(FP_HALF, 1, 0));

    assert(cra_state_lookup_is_received_shard(42, LOOKUP_TYPE_CONTEXT, 1) == 1);
    assert(cra_state_lookup_is_received_shard(42, LOOKUP_TYPE_CONTEXT, 2) == 0);

    cra_state_mcpl_lookup_receive(s2_value, (uint32_t)FP_FROM_FLOAT(0.875f));
    cra_state_mcpl_lookup_receive(s2_meta, PACK_MCPL_LOOKUP_META(FP_ONE, 1, 0));

    int32_t value = 0;
    int32_t confidence = 0;
    uint8_t hit = 0;
    assert(cra_state_lookup_get_result_shard(42, LOOKUP_TYPE_CONTEXT, 1, &value, &confidence, &hit) == 0);
    assert(value == FP_FROM_FLOAT(0.125f));
    assert(confidence == FP_HALF);
    assert(hit == 1);

    assert(cra_state_lookup_get_result_shard(42, LOOKUP_TYPE_CONTEXT, 2, &value, &confidence, &hit) == 0);
    assert(value == FP_FROM_FLOAT(0.875f));
    assert(confidence == FP_ONE);
    assert(hit == 1);
    printf("  PASS: shard_id prevents identical seq/type cross-talk\n");
}

static void test_wrong_shard_does_not_complete_lookup(void) {
    cra_state_lookup_init();
    assert(cra_state_lookup_send_shard(12, 333, LOOKUP_TYPE_ROUTE, 1, 0) == 0);

    uint32_t wrong_value = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, LOOKUP_TYPE_ROUTE, 2, 12);
    uint32_t wrong_meta = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, LOOKUP_TYPE_ROUTE, 2, 12);

    cra_state_mcpl_lookup_receive(wrong_value, (uint32_t)FP_ONE);
    cra_state_mcpl_lookup_receive(wrong_meta, PACK_MCPL_LOOKUP_META(FP_ONE, 1, 0));

    assert(cra_state_lookup_is_received_shard(12, LOOKUP_TYPE_ROUTE, 1) == 0);
    assert(cra_state_lookup_get_result_shard(12, LOOKUP_TYPE_ROUTE, 1, 0, 0, 0) == -1);
    printf("  PASS: wrong-shard packets cannot complete pending lookup\n");
}

int main(void) {
    printf("Tier 4.32a-r1 MCPL lookup contract tests\n");
    test_value_and_meta_send();
    test_receive_waits_for_both_packets();
    test_meta_before_value();
    test_shard_disambiguates_identical_seq_and_type();
    test_wrong_shard_does_not_complete_lookup();
    printf("All Tier 4.32a-r1 MCPL lookup contract tests passed.\n");
    return 0;
}
