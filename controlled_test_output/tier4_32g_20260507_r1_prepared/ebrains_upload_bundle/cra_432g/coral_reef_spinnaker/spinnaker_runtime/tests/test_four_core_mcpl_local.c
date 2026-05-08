/*
 * Tier 4.32a-r1 four-core MCPL local integration test.
 *
 * This mirrors the confidence controls in test_four_core_local.c, but replies
 * are delivered through the repaired MCPL value/meta packet path instead of
 * directly calling cra_state_lookup_receive().
 */

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "config.h"
#include "state_manager.h"
#include "host_interface.h"
#include "spin1_api.h"

uint32_t g_timestep = 0;
int32_t  g_dopamine_level = 0;

extern uint32_t g_test_mc_packet_count;
extern uint32_t g_test_last_mc_key;
extern uint32_t g_test_last_mc_payload;
extern uint32_t g_test_last_mc_with_payload;
extern uint32_t g_test_mc_keys[8];
extern uint32_t g_test_mc_payloads[8];
extern uint32_t g_test_mc_with_payloads[8];

static const int32_t s_ctx_val = FP_ONE;
static const int32_t s_route_val = FP_ONE;
static const int32_t s_mem_val = FP_ONE;

static void reset_mc_packets(void) {
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

static void inject_mcpl_replies_conf(int32_t ctx_conf, int32_t route_conf, int32_t mem_conf) {
    uint32_t pending[3];
    uint32_t n = cra_state_lookup_list_pending(pending, 3);
    for (uint32_t i = 0; i < n; i++) {
        uint32_t key_id = 0;
        uint8_t type = 0xFF;
        assert(cra_state_lookup_get_pending_info(pending[i], &key_id, &type) == 0);

        int32_t value = 0;
        int32_t confidence = 0;
        switch (type) {
            case LOOKUP_TYPE_CONTEXT:
                value = s_ctx_val;
                confidence = ctx_conf;
                break;
            case LOOKUP_TYPE_ROUTE:
                value = s_route_val;
                confidence = route_conf;
                break;
            case LOOKUP_TYPE_MEMORY:
                value = s_mem_val;
                confidence = mem_conf;
                break;
            default:
                assert(0 && "unknown lookup type");
        }

        uint32_t value_key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, type, pending[i]);
        uint32_t meta_key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, type, pending[i]);
        cra_state_mcpl_lookup_receive(value_key, (uint32_t)value);
        cra_state_mcpl_lookup_receive(meta_key, PACK_MCPL_LOOKUP_META(confidence, 1, 0));
    }
}

static void setup_single_event(void) {
    reset_mc_packets();
    cra_state_init();
    cra_state_set_readout(0, 0);
    cra_state_set_learning_rate(FP_FROM_FLOAT(0.25f));

    schedule_entry_t entry;
    entry.timestep = 1;
    entry.context_key = 1;
    entry.route_key = 2;
    entry.memory_key = 3;
    entry.cue = FP_ONE;
    entry.target = FP_ONE;
    entry.delay = 1;
    assert(cra_state_write_schedule_entry(0, &entry) == 0);
    cra_state_set_schedule_count(1);
    cra_state_set_continuous_mode(1);
}

static void run_single_event_with_conf(int32_t ctx_conf, int32_t route_conf, int32_t mem_conf) {
    uint32_t timestep = 1;
    while (cra_state_continuous_mode() && timestep < 20) {
        cra_state_process_continuous_tick(timestep);
        if (timestep == 1) {
            assert(g_test_mc_packet_count >= 3);
            assert(EXTRACT_MCPL_MSG_TYPE(g_test_mc_keys[0]) == MCPL_MSG_LOOKUP_REQUEST);
        }
        inject_mcpl_replies_conf(ctx_conf, route_conf, mem_conf);
        timestep++;
    }
}

static void test_mcpl_full_confidence_learning(void) {
    setup_single_event();
    run_single_event_with_conf(FP_ONE, FP_ONE, FP_ONE);

    cra_state_summary_t summary;
    cra_state_get_summary(&summary);
    assert(summary.decisions == 1);
    assert(summary.pending_created == 1);
    assert(summary.pending_matured == 1);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.25f));
    assert(summary.readout_bias == FP_FROM_FLOAT(0.25f));
    printf("  PASS: MCPL full-confidence path learns like SDP reference\n");
}

static void test_mcpl_zero_confidence_blocks_learning(void) {
    setup_single_event();
    run_single_event_with_conf(0, 0, 0);

    cra_state_summary_t summary;
    cra_state_get_summary(&summary);
    assert(summary.decisions == 1);
    assert(summary.pending_created == 1);
    assert(summary.pending_matured == 1);
    assert(summary.readout_weight == 0);
    assert(summary.readout_bias == 0);
    printf("  PASS: MCPL zero-confidence path blocks learning\n");
}

static void test_mcpl_half_confidence_scales_learning(void) {
    setup_single_event();
    run_single_event_with_conf(FP_HALF, FP_ONE, FP_ONE);

    cra_state_summary_t summary;
    cra_state_get_summary(&summary);
    assert(summary.decisions == 1);
    assert(summary.pending_created == 1);
    assert(summary.pending_matured == 1);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.125f));
    assert(summary.readout_bias == FP_FROM_FLOAT(0.125f));
    printf("  PASS: MCPL half-confidence path scales learning\n");
}

int main(void) {
    printf("Tier 4.32a-r1 four-core MCPL local integration test\n");
    test_mcpl_full_confidence_learning();
    test_mcpl_zero_confidence_blocks_learning();
    test_mcpl_half_confidence_scales_learning();
    printf("All Tier 4.32a-r1 four-core MCPL local tests passed.\n");
    return 0;
}
