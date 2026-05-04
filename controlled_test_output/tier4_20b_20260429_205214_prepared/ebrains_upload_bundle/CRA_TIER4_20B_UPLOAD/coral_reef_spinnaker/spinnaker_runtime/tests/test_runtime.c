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
#include "router.h"
#include "host_interface.h"

/* Stub symbols normally defined in main.c */
uint32_t g_timestep = 0;
uint32_t g_dopamine_level = 0;
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

static void test_cmd_values(void) {
    assert(CMD_BIRTH == 1);
    assert(CMD_DEATH == 2);
    assert(CMD_DOPAMINE == 3);
    assert(CMD_READ_SPIKES == 4);
    assert(CMD_CREATE_SYN == 5);
    assert(CMD_REMOVE_SYN == 6);
    assert(CMD_RESET == 7);
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

/* ------------------------------------------------------------------ */
/* Main                                                                */
/* ------------------------------------------------------------------ */

int main(void) {
    printf("=== Coral Reef Runtime Host Tests ===\n\n");

    printf("config.h:\n");
    test_make_key();
    test_fp_math();
    test_cmd_values();
    test_weight_limits();

    printf("\nneuron_manager:\n");
    test_neuron_lifecycle();
    test_neuron_find();
    test_neuron_reset_all();

    printf("\nsynapse_manager:\n");
    test_synapse_lifecycle();
    test_synapse_weight_limits();

    printf("\nrouter:\n");
    test_router_lifecycle();
    test_router_reset_all();

    printf("\nhost_interface:\n");
    test_host_interface_init();

    printf("\n=== ALL TESTS PASSED ===\n");
    return 0;
}
