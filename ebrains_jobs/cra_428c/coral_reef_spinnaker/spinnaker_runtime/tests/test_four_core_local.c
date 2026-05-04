/*
 * Local four-core behavioral integration test for Tier 4.26 Step 4.
 *
 * Verifies that the learning_core profile, when driven by simulated
 * lookup replies, produces the same numeric results as the monolithic
 * reference path.
 *
 * Build:
 *   cc -I stubs -I src -DCRA_RUNTIME_PROFILE_LEARNING_CORE=1 \
 *      -DCRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE=1 -DRUNTIME_PROFILE_ID=3 \
 *      tests/test_four_core_local.c stubs/spin1_api.c src/state_manager.c \
 *      src/host_interface.c -lm -o test_four_core_local
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

/* Simulated slot values (same as monolithic reference test) */
static const int32_t s_ctx_val  = FP_FROM_FLOAT(1.0f);
static const int32_t s_route_val = FP_FROM_FLOAT(1.0f);
static const int32_t s_mem_val  = FP_FROM_FLOAT(1.0f);

/* Inject replies for all pending lookups using the simulated slot values */
static void inject_replies(void) {
    uint32_t pending[3];
    uint32_t n = cra_state_lookup_list_pending(pending, 3);
    for (uint32_t i = 0; i < n; i++) {
        uint32_t key = 0;
        uint8_t type = 0xFF;
        int rc = cra_state_lookup_get_pending_info(pending[i], &key, &type);
        assert(rc == 0);
        int32_t value = 0;
        switch (type) {
            case LOOKUP_TYPE_CONTEXT: value = s_ctx_val;  break;
            case LOOKUP_TYPE_ROUTE:   value = s_route_val; break;
            case LOOKUP_TYPE_MEMORY:  value = s_mem_val;  break;
            default: assert(0 && "unknown lookup type");
        }
        rc = cra_state_lookup_receive(pending[i], value, FP_ONE, 1);
        assert(rc == 0);
    }
}

/* ------------------------------------------------------------------ */
/* Test 1: single event                                                 */
/* ------------------------------------------------------------------ */
static void test_single_event(void) {
    cra_state_init();
    cra_state_set_readout(0, 0);
    cra_state_set_learning_rate(FP_FROM_FLOAT(0.25f));

    schedule_entry_t entry;
    entry.timestep = 1;
    entry.context_key = 1;
    entry.route_key = 2;
    entry.memory_key = 3;
    entry.cue = FP_FROM_FLOAT(1.0f);
    entry.target = FP_FROM_FLOAT(1.0f);
    entry.delay = 1;
    assert(cra_state_write_schedule_entry(0, &entry) == 0);
    cra_state_set_schedule_count(1);
    cra_state_set_continuous_mode(1);

    uint32_t timestep = 1;
    while (cra_state_continuous_mode() && timestep < 20) {
        cra_state_process_continuous_tick(timestep);
        inject_replies();
        timestep++;
    }

    cra_state_summary_t summary;
    cra_state_get_summary(&summary);
    assert(summary.decisions == 1);
    assert(summary.pending_created == 1);
    assert(summary.pending_matured == 1);
    assert(summary.active_pending == 0);
    assert(summary.reward_events == 1);
    /* After one event: weight = 0.25, bias = 0.25 */
    assert(summary.readout_weight == FP_FROM_FLOAT(0.25f));
    assert(summary.readout_bias   == FP_FROM_FLOAT(0.25f));
    printf("  PASS: single event weight/bias match monolithic reference\n");
}

/* ------------------------------------------------------------------ */
/* Test 2: two events (verifies sequential lookup + composition)        */
/* ------------------------------------------------------------------ */
static void test_two_events(void) {
    cra_state_init();
    cra_state_set_readout(0, 0);
    cra_state_set_learning_rate(FP_FROM_FLOAT(0.25f));

    schedule_entry_t entry;
    entry.timestep = 1;
    entry.context_key = 1;
    entry.route_key = 2;
    entry.memory_key = 3;
    entry.cue = FP_FROM_FLOAT(1.0f);
    entry.target = FP_FROM_FLOAT(1.0f);
    entry.delay = 1;
    assert(cra_state_write_schedule_entry(0, &entry) == 0);

    entry.timestep = 2;
    assert(cra_state_write_schedule_entry(1, &entry) == 0);

    cra_state_set_schedule_count(2);
    cra_state_set_continuous_mode(1);

    uint32_t timestep = 1;
    while (cra_state_continuous_mode() && timestep < 20) {
        cra_state_process_continuous_tick(timestep);
        inject_replies();
        timestep++;
    }

    cra_state_summary_t summary;
    cra_state_get_summary(&summary);
    assert(summary.decisions == 2);
    assert(summary.pending_created == 2);
    assert(summary.pending_matured == 2);
    assert(summary.active_pending == 0);
    assert(summary.reward_events == 2);
    /* After two events: weight = 0.375, bias = 0.375 */
    assert(summary.readout_weight == FP_FROM_FLOAT(0.375f));
    assert(summary.readout_bias   == FP_FROM_FLOAT(0.375f));
    printf("  PASS: two events weight/bias match monolithic reference\n");
}

/* ------------------------------------------------------------------ */
/* Test 3: signed target (verifies fixed-point sign handling)           */
/* ------------------------------------------------------------------ */
static void test_signed_target(void) {
    cra_state_init();
    cra_state_set_readout(0, 0);
    cra_state_set_learning_rate(FP_FROM_FLOAT(0.25f));

    schedule_entry_t entry;
    entry.timestep = 1;
    entry.context_key = 1;
    entry.route_key = 2;
    entry.memory_key = 3;
    entry.cue = FP_FROM_FLOAT(1.0f);
    entry.target = FP_FROM_FLOAT(-1.0f);
    entry.delay = 1;
    assert(cra_state_write_schedule_entry(0, &entry) == 0);
    cra_state_set_schedule_count(1);
    cra_state_set_continuous_mode(1);

    uint32_t timestep = 1;
    while (cra_state_continuous_mode() && timestep < 20) {
        cra_state_process_continuous_tick(timestep);
        inject_replies();
        timestep++;
    }

    cra_state_summary_t summary;
    cra_state_get_summary(&summary);
    assert(summary.pending_created == 1);
    assert(summary.pending_matured == 1);
    /* After one negative-target event: weight = -0.25, bias = -0.25 */
    assert(summary.readout_weight == -FP_FROM_FLOAT(0.25f));
    assert(summary.readout_bias   == -FP_FROM_FLOAT(0.25f));
    printf("  PASS: signed target weight/bias match monolithic reference\n");
}

/* ------------------------------------------------------------------ */
/* Test 4: all 3 lookups per event, no stale/timeout in normal path     */
/* ------------------------------------------------------------------ */
static void test_lookup_integrity(void) {
    cra_state_init();
    cra_state_set_readout(0, 0);
    cra_state_set_learning_rate(FP_FROM_FLOAT(0.25f));

    schedule_entry_t entry;
    entry.timestep = 1;
    entry.context_key = 1;
    entry.route_key = 2;
    entry.memory_key = 3;
    entry.cue = FP_FROM_FLOAT(1.0f);
    entry.target = FP_FROM_FLOAT(1.0f);
    entry.delay = 1;
    assert(cra_state_write_schedule_entry(0, &entry) == 0);
    cra_state_set_schedule_count(1);
    cra_state_set_continuous_mode(1);

    uint32_t timestep = 1;
    uint32_t total_lookups = 0;
    while (cra_state_continuous_mode() && timestep < 20) {
        cra_state_process_continuous_tick(timestep);
        uint32_t pending[3];
        uint32_t n = cra_state_lookup_list_pending(pending, 3);
        total_lookups += n;
        /* Verify exactly 3 lookups sent on tick 1, 0 thereafter */
        if (timestep == 1) {
            assert(n == 3);
            assert(cra_state_lookup_is_stale(999) == 1); /* unknown seq is stale */
        }
        inject_replies();
        timestep++;
    }

    assert(total_lookups == 3);
    printf("  PASS: exactly 3 lookups sent, no stale/timeout in normal path\n");
}

/* ------------------------------------------------------------------ */
/* Main                                                                 */
/* ------------------------------------------------------------------ */

int main(void) {
    printf("Four-core local integration test (learning_core profile)\n");
    test_single_event();
    test_two_events();
    test_signed_target();
    test_lookup_integrity();
    printf("All integration tests passed.\n");
    return 0;
}
