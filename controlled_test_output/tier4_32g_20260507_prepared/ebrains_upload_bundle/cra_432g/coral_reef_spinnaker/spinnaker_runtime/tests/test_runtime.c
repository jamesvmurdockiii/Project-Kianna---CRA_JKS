/*
 * Host-side unit tests for the Coral Reef SpiNNaker runtime.
 *
 * Build with:
 *     gcc -I ../stubs -I ../src -o test_runtime test_runtime.c \
 *         ../src/neuron_manager.c ../src/synapse_manager.c \
 *         ../src/router.c ../src/host_interface.c
 *
 * Run:
 *     ./test_runtime
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <math.h>

#include "config.h"
#include "neuron_manager.h"
#include "synapse_manager.h"
#include "state_manager.h"
#include "router.h"
#include "host_interface.h"

/* Stub symbols normally defined in main.c */
uint32_t g_timestep = 0;
int32_t g_dopamine_level = 0;
uint32_t get_app_id(void) { return APP_ID; }
void emit_spike(uint32_t neuron_id) { (void)neuron_id; }

/* ------------------------------------------------------------------ */
/* config.h tests                                                      */
/* ------------------------------------------------------------------ */

static void test_make_key(void) {
    uint32_t key = MAKE_KEY(0xC0, 42);
    assert(key == ((0xC0U << 24) | 42U));
    printf("  PASS: MAKE_KEY\n");
}

static void test_fp_math(void) {
    /* FP_ONE = 32768, so 1.0 -> 32768 */
    int32_t one = FP_FROM_FLOAT(1.0f);
    assert(one == 32768);

    /* 0.5 -> 16384 */
    int32_t half = FP_FROM_FLOAT(0.5f);
    assert(half == 16384);

    /* Round-trip */
    float f = FP_TO_FLOAT(16384);
    assert(fabsf(f - 0.5f) < 1e-4f);

    /* FP_MUL: 0.5 * 0.5 = 0.25 */
    int32_t quarter = FP_MUL(half, half);
    assert(quarter == FP_FROM_FLOAT(0.25f));

    printf("  PASS: fixed-point math\n");
}

static void test_fp_signed_large_product(void) {
    int32_t error = FP_FROM_FLOAT(-2.5f);
    int32_t feature = FP_FROM_FLOAT(1.0f);
    int32_t learning_rate = FP_FROM_FLOAT(0.375f);
    int32_t error_feature = FP_MUL(error, feature);
    int32_t delta = FP_MUL(learning_rate, error_feature);

    assert(error_feature == FP_FROM_FLOAT(-2.5f));
    assert(delta == FP_FROM_FLOAT(-0.9375f));

    printf("  PASS: signed large fixed-point product\n");
}

static void test_cmd_values(void) {
    assert(CMD_BIRTH == 1);
    assert(CMD_DEATH == 2);
    assert(CMD_DOPAMINE == 3);
    assert(CMD_READ_SPIKES == 4);
    assert(CMD_CREATE_SYN == 5);
    assert(CMD_REMOVE_SYN == 6);
    assert(CMD_RESET == 7);
    assert(CMD_READ_STATE == 8);
    assert(CMD_SCHEDULE_PENDING == 9);
    assert(CMD_MATURE_PENDING == 10);
    assert(CMD_WRITE_CONTEXT == 11);
    assert(CMD_READ_CONTEXT == 12);
    assert(CMD_SCHEDULE_CONTEXT_PENDING == 13);
    assert(CMD_WRITE_ROUTE == 14);
    assert(CMD_READ_ROUTE == 15);
    assert(CMD_SCHEDULE_ROUTED_CONTEXT_PENDING == 16);
    assert(CMD_WRITE_ROUTE_SLOT == 17);
    assert(CMD_READ_ROUTE_SLOT == 18);
    assert(CMD_SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING == 19);
    assert(CMD_WRITE_MEMORY_SLOT == 20);
    assert(CMD_READ_MEMORY_SLOT == 21);
    assert(CMD_SCHEDULE_MEMORY_ROUTE_CONTEXT_PENDING == 22);
    assert(CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING == 23);
    assert(CMD_RUN_CONTINUOUS == 24);
    assert(CMD_PAUSE == 25);
    assert(CMD_WRITE_SCHEDULE_ENTRY == 26);
    assert(CMD_SCHEDULE_PENDING_SPLIT == 30);
    assert(CMD_MATURE_ACK_SPLIT == 31);
    assert(CMD_LOOKUP_REQUEST == 32);
    assert(CMD_LOOKUP_REPLY == 33);
    assert(CMD_LIFECYCLE_INIT == 34);
    assert(CMD_LIFECYCLE_EVENT == 35);
    assert(CMD_LIFECYCLE_TROPHIC_UPDATE == 36);
    assert(CMD_LIFECYCLE_READ_STATE == 37);
    assert(CMD_LIFECYCLE_SHAM_MODE == 38);
    assert(CMD_TEMPORAL_INIT == 39);
    assert(CMD_TEMPORAL_UPDATE == 40);
    assert(CMD_TEMPORAL_READ_STATE == 41);
    assert(CMD_TEMPORAL_SHAM_MODE == 42);
    printf("  PASS: command constants\n");
}

static void test_weight_limits(void) {
    assert(MIN_WEIGHT == -32768);
    assert(MAX_WEIGHT == 32768);  /* FP_FROM_FLOAT(1.0f) = 32768 */
    printf("  PASS: weight limits\n");
}

/* ------------------------------------------------------------------ */
/* Neuron manager tests                                                */
/* ------------------------------------------------------------------ */

static void test_neuron_lifecycle(void) {
    neuron_mgr_init();
    assert(neuron_count() == 0);

    neuron_birth(0);
    assert(neuron_count() == 1);

    neuron_birth(1);
    assert(neuron_count() == 2);

    neuron_death(0);
    assert(neuron_count() == 1);

    neuron_death(1);
    assert(neuron_count() == 0);

    printf("  PASS: neuron birth/death\n");
}

static void test_neuron_find(void) {
    neuron_mgr_init();
    neuron_birth(5);
    neuron_t *n = neuron_find(5);
    assert(n != NULL);
    assert(n->id == 5);

    neuron_t *missing = neuron_find(99);
    assert(missing == NULL);

    neuron_death(5);
    printf("  PASS: neuron find\n");
}

static void test_neuron_reset_all(void) {
    neuron_mgr_init();
    neuron_birth(0);
    neuron_birth(1);
    assert(neuron_count() == 2);

    neuron_reset_all();
    assert(neuron_count() == 0);

    printf("  PASS: neuron reset all\n");
}

/* ------------------------------------------------------------------ */
/* Synapse manager tests                                               */
/* ------------------------------------------------------------------ */

static void test_synapse_lifecycle(void) {
    /* Need neurons for synapses to attach to */
    neuron_mgr_init();
    neuron_birth(0);
    neuron_birth(1);
    neuron_birth(2);

    synapse_reset_all();
    assert(synapse_count() == 0);

    synapse_create(0, 1, FP_FROM_FLOAT(0.5f), DEFAULT_SYN_DELAY);
    assert(synapse_count() == 1);

    synapse_create(0, 2, FP_FROM_FLOAT(0.3f), DEFAULT_SYN_DELAY);
    assert(synapse_count() == 2);

    synapse_remove(0, 1);
    assert(synapse_count() == 1);

    synapse_remove_incident(0);
    assert(synapse_count() == 0);

    printf("  PASS: synapse create/remove\n");
}

static void test_synapse_weight_limits(void) {
    neuron_mgr_init();
    neuron_birth(0);
    neuron_birth(1);

    synapse_reset_all();

    /* Weight above MAX_WEIGHT should be clipped by synapse_create */
    synapse_create(0, 1, 40000, DEFAULT_SYN_DELAY);
    /* synapse_count should be 1 even with out-of-range weight */
    assert(synapse_count() == 1);

    synapse_remove_incident(0);
    printf("  PASS: synapse weight limits\n");
}

static void test_synapse_eligibility_modulation(void) {
    int32_t weight = 0;
    int32_t trace = 0;

    neuron_mgr_init();
    neuron_birth(0);
    neuron_birth(1);
    synapse_reset_all();

    synapse_create(0, 1, FP_FROM_FLOAT(0.0f), DEFAULT_SYN_DELAY);
    assert(synapse_get_weight(0, 1, &weight) == 0);
    assert(weight == 0);

    /* Dopamine without a causal spike trace must not move the weight. */
    synapse_modulate_all(FP_FROM_FLOAT(0.5f));
    assert(synapse_get_weight(0, 1, &weight) == 0);
    assert(weight == 0);

    synapse_deliver_spike(0);
    assert(synapse_get_eligibility_trace(0, 1, &trace) == 0);
    assert(trace == MAX_ELIGIBILITY_TRACE);

    synapse_modulate_all(FP_FROM_FLOAT(0.5f));
    assert(synapse_get_weight(0, 1, &weight) == 0);
    assert(weight == FP_FROM_FLOAT(0.5f));

    synapse_decay_traces_all(FP_FROM_FLOAT(0.5f));
    assert(synapse_get_eligibility_trace(0, 1, &trace) == 0);
    assert(trace == FP_FROM_FLOAT(0.5f));

    synapse_reset_all();
    printf("  PASS: eligibility trace modulation\n");
}

static void test_synapse_indexed_delivery_and_active_traces(void) {
    int32_t weight = 0;
    int32_t trace = 0;

    neuron_mgr_init();
    neuron_birth(0);
    neuron_birth(1);
    neuron_birth(2);
    synapse_reset_all();

    synapse_create(0, 1, FP_FROM_FLOAT(0.0f), DEFAULT_SYN_DELAY);
    synapse_create(0, 2, FP_FROM_FLOAT(0.0f), DEFAULT_SYN_DELAY);
    synapse_create(1, 2, FP_FROM_FLOAT(0.0f), DEFAULT_SYN_DELAY);
    assert(synapse_count() == 3);

    synapse_deliver_spike(0);
    assert(synapse_last_delivery_visit_count() == 2);
    assert(synapse_active_trace_count() == 2);
    assert(synapse_get_eligibility_trace(0, 1, &trace) == 0);
    assert(trace == MAX_ELIGIBILITY_TRACE);
    assert(synapse_get_eligibility_trace(0, 2, &trace) == 0);
    assert(trace == MAX_ELIGIBILITY_TRACE);
    assert(synapse_get_eligibility_trace(1, 2, &trace) == 0);
    assert(trace == 0);

    synapse_modulate_all(FP_FROM_FLOAT(0.5f));
    assert(synapse_last_modulation_visit_count() == 2);
    assert(synapse_get_weight(0, 1, &weight) == 0);
    assert(weight == FP_FROM_FLOAT(0.5f));
    assert(synapse_get_weight(0, 2, &weight) == 0);
    assert(weight == FP_FROM_FLOAT(0.5f));
    assert(synapse_get_weight(1, 2, &weight) == 0);
    assert(weight == 0);

    synapse_decay_traces_all(FP_FROM_FLOAT(0.0f));
    assert(synapse_last_decay_visit_count() == 2);
    assert(synapse_active_trace_count() == 0);

    synapse_deliver_spike(99);
    assert(synapse_last_delivery_visit_count() == 0);

    synapse_reset_all();
    printf("  PASS: indexed delivery and active trace list\n");
}

/* ------------------------------------------------------------------ */
/* Persistent CRA state tests                                          */
/* ------------------------------------------------------------------ */

static void test_state_context_slots(void) {
    cra_state_summary_t summary;
    int32_t value = 0;
    int32_t confidence = 0;

    cra_state_init();
    assert(cra_state_active_slot_count() == 0);

    assert(cra_state_write_context(10, FP_FROM_FLOAT(0.25f), FP_FROM_FLOAT(0.75f), 1) == 0);
    assert(cra_state_write_context(20, FP_FROM_FLOAT(-0.50f), FP_FROM_FLOAT(0.50f), 2) == 0);
    assert(cra_state_active_slot_count() == 2);

    assert(cra_state_read_context(10, &value, &confidence) == 0);
    assert(value == FP_FROM_FLOAT(0.25f));
    assert(confidence == FP_FROM_FLOAT(0.75f));

    assert(cra_state_read_context(999, &value, &confidence) == -1);
    cra_state_get_summary(&summary);
    assert(summary.slot_writes == 2);
    assert(summary.slot_hits == 1);
    assert(summary.slot_misses == 1);
    assert(summary.slot_evictions == 0);

    printf("  PASS: persistent context slots\n");
}

static void test_state_slot_eviction(void) {
    cra_state_summary_t summary;
    int32_t value = 0;
    int32_t confidence = 0;

    cra_state_init();
    for (uint32_t i = 0; i < MAX_CONTEXT_SLOTS; i++) {
        assert(cra_state_write_context(100 + i, (int32_t)i, FP_FROM_FLOAT(0.1f), i) == 0);
    }
    assert(cra_state_active_slot_count() == MAX_CONTEXT_SLOTS);
    assert(cra_state_write_context(999, FP_FROM_FLOAT(0.9f), FP_FROM_FLOAT(1.0f), 100) == 0);
    assert(cra_state_active_slot_count() == MAX_CONTEXT_SLOTS);
    assert(cra_state_read_context(999, &value, &confidence) == 0);
    assert(value == FP_FROM_FLOAT(0.9f));
    assert(confidence == FP_FROM_FLOAT(1.0f));

    cra_state_get_summary(&summary);
    assert(summary.slot_evictions == 1);

    printf("  PASS: bounded slot eviction\n");
}

static void test_state_readout_and_reset(void) {
    cra_state_summary_t summary;
    int32_t prediction;

    cra_state_init();
    cra_state_set_readout(FP_FROM_FLOAT(0.5f), FP_FROM_FLOAT(0.25f));
    prediction = cra_state_predict_readout(FP_FROM_FLOAT(0.5f));
    assert(prediction == FP_FROM_FLOAT(0.5f));
    cra_state_record_decision(FP_FROM_FLOAT(0.5f), prediction);
    cra_state_record_reward(FP_FROM_FLOAT(1.0f));

    cra_state_get_summary(&summary);
    assert(summary.decisions == 1);
    assert(summary.reward_events == 1);
    assert(summary.last_prediction == FP_FROM_FLOAT(0.5f));
    assert(summary.last_reward == FP_FROM_FLOAT(1.0f));

    cra_state_reset();
    cra_state_get_summary(&summary);
    assert(summary.active_slots == 0);
    assert(summary.decisions == 0);
    assert(summary.reward_events == 0);
    assert(summary.state_resets == 1);
    assert(summary.readout_weight == 0);
    assert(summary.readout_bias == 0);

    printf("  PASS: readout state and reset\n");
}

static void test_state_reward_readout_update(void) {
    cra_state_summary_t summary;
    int32_t prediction;
    int32_t delta_w;

    cra_state_init();
    cra_state_set_readout(FP_FROM_FLOAT(0.0f), FP_FROM_FLOAT(0.0f));
    prediction = cra_state_predict_readout(FP_FROM_FLOAT(1.0f));
    cra_state_record_decision(FP_FROM_FLOAT(1.0f), prediction);
    delta_w = cra_state_apply_reward_to_readout(FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(0.25f));
    assert(delta_w == FP_FROM_FLOAT(0.25f));

    cra_state_get_summary(&summary);
    assert(summary.reward_events == 1);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.25f));
    assert(summary.readout_bias == FP_FROM_FLOAT(0.25f));

    printf("  PASS: reward readout update\n");
}

static void test_state_pending_horizon_maturation(void) {
    cra_state_summary_t summary;

    cra_state_init();
    cra_state_set_readout(0, 0);
    assert(cra_state_schedule_pending_horizon(FP_FROM_FLOAT(1.0f), 0, 5) == 0);
    assert(cra_state_schedule_pending_horizon(FP_FROM_FLOAT(-1.0f), 0, 8) == 0);
    assert(cra_state_active_pending_count() == 2);

    assert(cra_state_mature_pending_horizons(4, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(0.25f)) == 0);
    assert(cra_state_active_pending_count() == 2);

    assert(cra_state_mature_pending_horizons(5, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(0.25f)) == 1);
    cra_state_get_summary(&summary);
    assert(summary.pending_created == 2);
    assert(summary.pending_matured == 1);
    assert(summary.active_pending == 1);
    assert(summary.reward_events == 1);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.25f));
    assert(summary.readout_bias == FP_FROM_FLOAT(0.25f));

    assert(cra_state_mature_pending_horizons(8, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(0.25f)) == 1);
    cra_state_get_summary(&summary);
    assert(summary.pending_matured == 2);
    assert(summary.active_pending == 0);
    assert(summary.reward_events == 2);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.50f));
    assert(summary.readout_bias == 0);

    printf("  PASS: pending horizon maturation\n");
}

static void test_state_pending_horizon_signed_switch_update(void) {
    cra_state_summary_t summary;
    int32_t feature = FP_FROM_FLOAT(1.0f);

    cra_state_init();
    cra_state_set_readout(FP_FROM_FLOAT(0.9375f), FP_FROM_FLOAT(0.75f));

    /* Use prediction=0.5 so |error|=1.5 < SURPRISE_THRESHOLD (2.0).
       The original test used prediction=1.5 (|error|=2.5) which is now
       gated by surprise threshold. Signed switch still holds: pred>0, target<0. */
    assert(cra_state_schedule_pending_horizon(feature, FP_FROM_FLOAT(0.5f), 7) == 0);
    assert(cra_state_mature_pending_horizons(7, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(0.375f)) == 1);

    cra_state_get_summary(&summary);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.375f));
    assert(summary.readout_bias == FP_FROM_FLOAT(0.1875f));

    printf("  PASS: pending signed switch update\n");
}

static void test_state_context_feature_schedule_reference(void) {
    cra_state_summary_t summary;
    int32_t context_value = 0;
    int32_t confidence = 0;
    int32_t cue = FP_FROM_FLOAT(-1.0f);
    int32_t feature;
    int32_t prediction;

    cra_state_init();
    cra_state_set_readout(0, 0);
    assert(cra_state_write_context(42, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(1.0f), 9) == 0);
    assert(cra_state_read_context(42, &context_value, &confidence) == 0);
    assert(context_value == FP_FROM_FLOAT(-1.0f));
    assert(confidence == FP_FROM_FLOAT(1.0f));

    feature = FP_MUL(context_value, cue);
    assert(feature == FP_FROM_FLOAT(1.0f));
    prediction = cra_state_predict_readout(feature);
    cra_state_record_decision(feature, prediction);
    assert(cra_state_schedule_pending_horizon(feature, prediction, 12) == 0);
    assert(cra_state_mature_pending_horizons(12, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(0.25f)) == 1);

    cra_state_get_summary(&summary);
    assert(summary.slot_writes == 1);
    assert(summary.slot_hits == 1);
    assert(summary.pending_created == 1);
    assert(summary.pending_matured == 1);
    assert(summary.decisions == 1);
    assert(summary.reward_events == 1);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.25f));
    assert(summary.readout_bias == FP_FROM_FLOAT(0.25f));

    printf("  PASS: context-derived feature scheduling reference\n");
}

static void test_state_routed_context_feature_schedule_reference(void) {
    cra_state_summary_t summary;
    int32_t context_value = 0;
    int32_t context_confidence = 0;
    int32_t route_value = 0;
    int32_t route_confidence = 0;
    int32_t cue = FP_FROM_FLOAT(-1.0f);
    int32_t feature;
    int32_t prediction;

    cra_state_init();
    cra_state_set_readout(0, 0);
    assert(cra_state_write_context(42, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(1.0f), 9) == 0);
    assert(cra_state_write_route(FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(1.0f), 10) == 0);
    assert(cra_state_read_context(42, &context_value, &context_confidence) == 0);
    assert(cra_state_read_route(&route_value, &route_confidence) == 0);
    assert(context_value == FP_FROM_FLOAT(-1.0f));
    assert(context_confidence == FP_FROM_FLOAT(1.0f));
    assert(route_value == FP_FROM_FLOAT(-1.0f));
    assert(route_confidence == FP_FROM_FLOAT(1.0f));

    feature = FP_MUL(FP_MUL(context_value, route_value), cue);
    assert(feature == FP_FROM_FLOAT(-1.0f));
    prediction = cra_state_predict_readout(feature);
    cra_state_record_decision(feature, prediction);
    assert(cra_state_schedule_pending_horizon(feature, prediction, 12) == 0);
    assert(cra_state_mature_pending_horizons(12, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(0.25f)) == 1);

    cra_state_get_summary(&summary);
    assert(summary.slot_writes == 1);
    assert(summary.slot_hits == 1);
    assert(summary.route_writes == 1);
    assert(summary.route_reads == 1);
    assert(summary.pending_created == 1);
    assert(summary.pending_matured == 1);
    assert(summary.decisions == 1);
    assert(summary.reward_events == 1);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.25f));
    assert(summary.readout_bias == FP_FROM_FLOAT(-0.25f));

    printf("  PASS: routed context-derived feature scheduling reference\n");
}

static void test_state_keyed_route_context_feature_schedule_reference(void) {
    cra_state_summary_t summary;
    int32_t context_value = 0;
    int32_t context_confidence = 0;
    int32_t route_value = 0;
    int32_t route_confidence = 0;
    int32_t cue = FP_FROM_FLOAT(-1.0f);
    int32_t feature;
    int32_t prediction;

    cra_state_init();
    cra_state_set_readout(0, 0);
    assert(cra_state_write_context(42, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(1.0f), 9) == 0);
    assert(cra_state_write_route_slot(42, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(1.0f), 10) == 0);
    assert(cra_state_read_context(42, &context_value, &context_confidence) == 0);
    assert(cra_state_read_route_slot(42, &route_value, &route_confidence) == 0);
    assert(context_value == FP_FROM_FLOAT(-1.0f));
    assert(context_confidence == FP_FROM_FLOAT(1.0f));
    assert(route_value == FP_FROM_FLOAT(-1.0f));
    assert(route_confidence == FP_FROM_FLOAT(1.0f));

    feature = FP_MUL(FP_MUL(context_value, route_value), cue);
    assert(feature == FP_FROM_FLOAT(-1.0f));
    prediction = cra_state_predict_readout(feature);
    cra_state_record_decision(feature, prediction);
    assert(cra_state_schedule_pending_horizon(feature, prediction, 12) == 0);
    assert(cra_state_mature_pending_horizons(12, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(0.25f)) == 1);

    cra_state_get_summary(&summary);
    assert(summary.slot_writes == 1);
    assert(summary.slot_hits == 1);
    assert(summary.route_slot_writes == 1);
    assert(summary.route_slot_hits == 1);
    assert(summary.active_route_slots == 1);
    assert(summary.pending_created == 1);
    assert(summary.pending_matured == 1);
    assert(summary.decisions == 1);
    assert(summary.reward_events == 1);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.25f));
    assert(summary.readout_bias == FP_FROM_FLOAT(-0.25f));

    printf("  PASS: keyed route/context-derived feature scheduling reference\n");
}

static void test_state_memory_route_context_feature_schedule_reference(void) {
    cra_state_summary_t summary;
    int32_t context_value = 0;
    int32_t context_confidence = 0;
    int32_t route_value = 0;
    int32_t route_confidence = 0;
    int32_t memory_value = 0;
    int32_t memory_confidence = 0;
    int32_t cue = FP_FROM_FLOAT(-1.0f);
    int32_t feature;
    int32_t prediction;

    cra_state_init();
    cra_state_set_readout(0, 0);
    assert(cra_state_write_context(42, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(1.0f), 9) == 0);
    assert(cra_state_write_route_slot(42, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(1.0f), 10) == 0);
    assert(cra_state_write_memory_slot(42, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(1.0f), 11) == 0);
    assert(cra_state_read_context(42, &context_value, &context_confidence) == 0);
    assert(cra_state_read_route_slot(42, &route_value, &route_confidence) == 0);
    assert(cra_state_read_memory_slot(42, &memory_value, &memory_confidence) == 0);
    assert(context_value == FP_FROM_FLOAT(-1.0f));
    assert(context_confidence == FP_FROM_FLOAT(1.0f));
    assert(route_value == FP_FROM_FLOAT(-1.0f));
    assert(route_confidence == FP_FROM_FLOAT(1.0f));
    assert(memory_value == FP_FROM_FLOAT(1.0f));
    assert(memory_confidence == FP_FROM_FLOAT(1.0f));

    feature = FP_MUL(FP_MUL(FP_MUL(context_value, route_value), memory_value), cue);
    assert(feature == FP_FROM_FLOAT(-1.0f));
    prediction = cra_state_predict_readout(feature);
    cra_state_record_decision(feature, prediction);
    assert(cra_state_schedule_pending_horizon(feature, prediction, 12) == 0);
    assert(cra_state_mature_pending_horizons(12, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(0.25f)) == 1);

    cra_state_get_summary(&summary);
    assert(summary.slot_writes == 1);
    assert(summary.slot_hits == 1);
    assert(summary.route_slot_writes == 1);
    assert(summary.route_slot_hits == 1);
    assert(summary.active_route_slots == 1);
    assert(summary.memory_slot_writes == 1);
    assert(summary.memory_slot_hits == 1);
    assert(summary.active_memory_slots == 1);
    assert(summary.pending_created == 1);
    assert(summary.pending_matured == 1);
    assert(summary.decisions == 1);
    assert(summary.reward_events == 1);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.25f));
    assert(summary.readout_bias == FP_FROM_FLOAT(-0.25f));

    printf("  PASS: memory/route/context-derived feature scheduling reference\n");
}

static void test_state_decoupled_memory_route_context_feature_schedule_reference(void) {
    cra_state_summary_t summary;
    int32_t context_value = 0;
    int32_t context_confidence = 0;
    int32_t route_value = 0;
    int32_t route_confidence = 0;
    int32_t memory_value = 0;
    int32_t memory_confidence = 0;
    int32_t cue = FP_FROM_FLOAT(1.0f);
    int32_t feature;
    int32_t prediction;

    cra_state_init();
    cra_state_set_readout(0, 0);
    assert(cra_state_write_context(101, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(1.0f), 9) == 0);
    assert(cra_state_write_route_slot(202, FP_FROM_FLOAT(-1.0f), FP_FROM_FLOAT(1.0f), 10) == 0);
    assert(cra_state_write_memory_slot(303, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(1.0f), 11) == 0);
    assert(cra_state_read_context(101, &context_value, &context_confidence) == 0);
    assert(cra_state_read_route_slot(202, &route_value, &route_confidence) == 0);
    assert(cra_state_read_memory_slot(303, &memory_value, &memory_confidence) == 0);
    assert(context_value == FP_FROM_FLOAT(-1.0f));
    assert(route_value == FP_FROM_FLOAT(-1.0f));
    assert(memory_value == FP_FROM_FLOAT(1.0f));

    feature = FP_MUL(FP_MUL(FP_MUL(context_value, route_value), memory_value), cue);
    assert(feature == FP_FROM_FLOAT(1.0f));
    prediction = cra_state_predict_readout(feature);
    cra_state_record_decision(feature, prediction);
    assert(cra_state_schedule_pending_horizon(feature, prediction, 12) == 0);
    assert(cra_state_mature_pending_horizons(12, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(0.25f)) == 1);

    cra_state_get_summary(&summary);
    assert(summary.slot_writes == 1);
    assert(summary.slot_hits == 1);
    assert(summary.route_slot_writes == 1);
    assert(summary.route_slot_hits == 1);
    assert(summary.memory_slot_writes == 1);
    assert(summary.memory_slot_hits == 1);
    assert(summary.pending_created == 1);
    assert(summary.pending_matured == 1);
    assert(summary.decisions == 1);
    assert(summary.reward_events == 1);
    assert(summary.readout_weight == FP_FROM_FLOAT(0.25f));
    assert(summary.readout_bias == FP_FROM_FLOAT(0.25f));

    printf("  PASS: decoupled memory/route/context-derived feature scheduling reference\n");
}

static void test_state_pending_horizon_bound(void) {
    cra_state_summary_t summary;

    cra_state_init();
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        assert(cra_state_schedule_pending_horizon(FP_FROM_FLOAT(1.0f), 0, i + 1) == 0);
    }
    assert(cra_state_active_pending_count() == MAX_PENDING_HORIZONS);
    assert(cra_state_schedule_pending_horizon(FP_FROM_FLOAT(1.0f), 0, 999) == -1);
    cra_state_get_summary(&summary);
    assert(summary.pending_created == MAX_PENDING_HORIZONS);
    assert(summary.pending_dropped == 1);
    assert(summary.active_pending == MAX_PENDING_HORIZONS);

    printf("  PASS: bounded pending horizons\n");
}

/* ------------------------------------------------------------------ */
/* Continuous schedule tests                                           */
/* ------------------------------------------------------------------ */

static void test_state_schedule_entry_write_and_read(void) {
    schedule_entry_t entry;
    cra_state_init();

    entry.timestep = 5;
    entry.context_key = 1;
    entry.route_key = 2;
    entry.memory_key = 3;
    entry.cue = FP_FROM_FLOAT(1.0f);
    entry.target = FP_FROM_FLOAT(1.0f);
    entry.delay = 2;

    assert(cra_state_write_schedule_entry(0, &entry) == 0);
    assert(cra_state_schedule_entry_count() == 1);

    entry.timestep = 10;
    assert(cra_state_write_schedule_entry(1, &entry) == 0);
    assert(cra_state_schedule_entry_count() == 2);

    assert(cra_state_write_schedule_entry(MAX_SCHEDULE_ENTRIES, &entry) == -1);
    assert(cra_state_write_schedule_entry(0, NULL) == -1);

    printf("  PASS: schedule entry write and read\n");
}

static void test_state_continuous_tick(void) {
    cra_state_summary_t summary;
    schedule_entry_t entry;
    cra_state_init();
    cra_state_set_readout(0, 0);
    cra_state_set_learning_rate(FP_FROM_FLOAT(0.25f));

    cra_state_write_context(1, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(1.0f), 0);
    cra_state_write_route_slot(2, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(1.0f), 0);
    cra_state_write_memory_slot(3, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(1.0f), 0);

    entry.timestep = 1;
    entry.context_key = 1;
    entry.route_key = 2;
    entry.memory_key = 3;
    entry.cue = FP_FROM_FLOAT(1.0f);
    entry.target = FP_FROM_FLOAT(1.0f);
    entry.delay = 1;
    assert(cra_state_write_schedule_entry(0, &entry) == 0);

    cra_state_set_continuous_mode(1);

    assert(cra_state_process_continuous_tick(1) == 0);
    cra_state_get_summary(&summary);
    assert(summary.decisions == 1);
    assert(summary.pending_created == 1);
    assert(summary.active_pending == 1);
    assert(summary.pending_matured == 0);

    assert(cra_state_process_continuous_tick(2) == 1);
    cra_state_get_summary(&summary);
    assert(summary.pending_matured == 1);
    assert(summary.active_pending == 0);
    assert(summary.reward_events == 1);

    printf("  PASS: continuous tick processing\n");
}

static void test_state_continuous_auto_pause(void) {
    schedule_entry_t entry;
    cra_state_init();
    cra_state_set_readout(0, 0);
    cra_state_set_learning_rate(FP_FROM_FLOAT(0.25f));

    cra_state_write_context(1, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(1.0f), 0);
    cra_state_write_route_slot(2, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(1.0f), 0);
    cra_state_write_memory_slot(3, FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(1.0f), 0);

    entry.timestep = 1;
    entry.context_key = 1;
    entry.route_key = 2;
    entry.memory_key = 3;
    entry.cue = FP_FROM_FLOAT(1.0f);
    entry.target = FP_FROM_FLOAT(1.0f);
    entry.delay = 0;
    assert(cra_state_write_schedule_entry(0, &entry) == 0);

    cra_state_set_continuous_mode(1);
    assert(cra_state_continuous_mode() == 1);

    assert(cra_state_process_continuous_tick(1) == 1);
    assert(cra_state_continuous_mode() == 0);

    printf("  PASS: continuous auto-pause\n");
}

/* ------------------------------------------------------------------ */
/* Router tests                                                        */
/* ------------------------------------------------------------------ */

static void test_router_lifecycle(void) {
    router_init();
    assert(router_route_count() == 0);

    int rc = router_add_neuron(42);
    assert(rc == 0);
    assert(router_route_count() == 1);

    rc = router_remove_neuron(42);
    assert(rc == 0);
    assert(router_route_count() == 0);

    printf("  PASS: router add/remove\n");
}

static void test_router_reset_all(void) {
    router_init();
    router_add_neuron(1);
    router_add_neuron(2);
    assert(router_route_count() == 2);

    router_reset_all();
    assert(router_route_count() == 0);

    printf("  PASS: router reset all\n");
}

/* ------------------------------------------------------------------ */
/* Host interface tests                                                */
/* ------------------------------------------------------------------ */

static void test_host_interface_init(void) {
    host_if_init();
    printf("  PASS: host_interface init\n");
}

static uint32_t read_u32_le(uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int32_t read_s32_le(uint8_t *p) {
    return (int32_t)read_u32_le(p);
}

static void test_host_state_summary_pack(void) {
    uint8_t payload[180];
    uint8_t len;

    neuron_mgr_init();
    synapse_reset_all();
    cra_state_init();
    neuron_birth(10);
    neuron_birth(11);
    synapse_create(10, 11, FP_FROM_FLOAT(0.25f), DEFAULT_SYN_DELAY);
    synapse_deliver_spike(10);

    cra_state_write_context(7, FP_FROM_FLOAT(0.5f), FP_FROM_FLOAT(0.75f), 3);
    cra_state_set_readout(FP_FROM_FLOAT(0.25f), FP_FROM_FLOAT(-0.125f));
    cra_state_record_decision(FP_FROM_FLOAT(1.0f), FP_FROM_FLOAT(0.125f));
    cra_state_record_reward(FP_FROM_FLOAT(1.0f));
    cra_state_schedule_pending_horizon(FP_FROM_FLOAT(1.0f), 0, 20);
    cra_lifecycle_send_event_request_stub(1, LIFECYCLE_EVENT_DEATH, 0);
    cra_lifecycle_send_trophic_update_stub(0, FP_FROM_FLOAT(0.125f));
    cra_lifecycle_receive_active_mask_sync(2, 3, 12345);
    cra_lifecycle_record_missing_ack();
    g_timestep = 1234;

    assert(host_if_pack_state_summary(payload, 8) == 0);
    len = host_if_pack_state_summary(payload, sizeof(payload));
    assert(len == 149);
    assert(payload[0] == CMD_READ_STATE);
    assert(payload[1] == 0);
    assert(payload[2] == 2);
    assert(read_u32_le(&payload[4]) == 1234);
    assert(read_u32_le(&payload[8]) == 2);
    assert(read_u32_le(&payload[12]) == 1);
    assert(read_u32_le(&payload[16]) == 1);
    assert(read_u32_le(&payload[20]) == 1);
    assert(read_u32_le(&payload[24]) == 1);
    assert(read_u32_le(&payload[40]) == 1);
    assert(read_u32_le(&payload[44]) == 1);
    assert(read_u32_le(&payload[48]) == 1);
    assert(read_u32_le(&payload[60]) == 1);
    assert(read_s32_le(&payload[64]) == FP_FROM_FLOAT(0.25f));
    assert(read_s32_le(&payload[68]) == FP_FROM_FLOAT(-0.125f));
    assert(read_u32_le(&payload[105]) == 1);
    assert(read_u32_le(&payload[109]) == 1);
    assert(read_u32_le(&payload[121]) == 1);
    assert(read_u32_le(&payload[125]) == 2);
    assert(read_u32_le(&payload[129]) == 3);
    assert(read_u32_le(&payload[133]) == 12345);
    assert(read_u32_le(&payload[145]) == 1);

    synapse_reset_all();
    neuron_reset_all();
    cra_state_reset();
    printf("  PASS: compact state summary pack\n");
}

/* ------------------------------------------------------------------ */
/* Main                                                                */
/* ------------------------------------------------------------------ */

int main(void) {
    printf("=== Coral Reef Runtime Host Tests ===\n\n");

    printf("config.h:\n");
    test_make_key();
    test_fp_math();
    test_fp_signed_large_product();
    test_cmd_values();
    test_weight_limits();

    printf("\nneuron_manager:\n");
    test_neuron_lifecycle();
    test_neuron_find();
    test_neuron_reset_all();

    printf("\nsynapse_manager:\n");
    test_synapse_lifecycle();
    test_synapse_weight_limits();
    test_synapse_eligibility_modulation();
    test_synapse_indexed_delivery_and_active_traces();

    printf("\nstate_manager:\n");
    test_state_context_slots();
    test_state_slot_eviction();
    test_state_readout_and_reset();
    test_state_reward_readout_update();
    test_state_pending_horizon_maturation();
    test_state_pending_horizon_signed_switch_update();
    test_state_context_feature_schedule_reference();
    test_state_routed_context_feature_schedule_reference();
    test_state_keyed_route_context_feature_schedule_reference();
    test_state_memory_route_context_feature_schedule_reference();
    test_state_decoupled_memory_route_context_feature_schedule_reference();
    test_state_pending_horizon_bound();
    test_state_schedule_entry_write_and_read();
    test_state_continuous_tick();
    test_state_continuous_auto_pause();

    printf("\nrouter:\n");
    test_router_lifecycle();
    test_router_reset_all();

    printf("\nhost_interface:\n");
    test_host_interface_init();
    test_host_state_summary_pack();

    printf("\n=== ALL TESTS PASSED ===\n");
    return 0;
}
