/*
 * Tier 4.30 lifecycle/static-pool host tests.
 *
 * These tests intentionally exercise the new lifecycle metadata surface only:
 * fixed slot pool, active mask, lineage counters, trophic bookkeeping, and the
 * compact SDP readback. They do not call legacy neuron_birth/neuron_death.
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

#define FP_020 6554
#define FP_010 3277
#define FP_005 1638
#define FP_008 2621
#define FP_002 655
#define FP_004 1311

typedef struct lifecycle_test_event {
    uint32_t event_index;
    uint8_t event_type;
    uint32_t target_slot;
    int32_t parent_slot;
    int32_t child_slot;
    int32_t trophic_delta_raw;
    int32_t reward_raw;
} lifecycle_test_event_t;

static uint32_t _read_u32(const uint8_t *p) {
    return ((uint32_t)p[0])
        | ((uint32_t)p[1] << 8)
        | ((uint32_t)p[2] << 16)
        | ((uint32_t)p[3] << 24);
}

static int32_t _read_s32(const uint8_t *p) {
    return (int32_t)_read_u32(p);
}

static void _write_u32(uint8_t *p, uint32_t value) {
    p[0] = (uint8_t)(value & 0xFF);
    p[1] = (uint8_t)((value >> 8) & 0xFF);
    p[2] = (uint8_t)((value >> 16) & 0xFF);
    p[3] = (uint8_t)((value >> 24) & 0xFF);
}

static void _write_s32(uint8_t *p, int32_t value) {
    _write_u32(p, (uint32_t)value);
}

static void _collect_slots(uint32_t *active, uint32_t *active_n, uint32_t *inactive, uint32_t *inactive_n) {
    *active_n = 0;
    *inactive_n = 0;
    for (uint32_t i = 0; i < MAX_LIFECYCLE_SLOTS; i++) {
        lifecycle_slot_t slot;
        assert(cra_lifecycle_get_slot(i, &slot) == 0);
        if (slot.active) {
            active[(*active_n)++] = i;
        } else {
            inactive[(*inactive_n)++] = i;
        }
    }
}

static lifecycle_test_event_t _choose_event(uint32_t event_index) {
    uint32_t active[MAX_LIFECYCLE_SLOTS];
    uint32_t inactive[MAX_LIFECYCLE_SLOTS];
    uint32_t active_n = 0;
    uint32_t inactive_n = 0;
    uint32_t kind = event_index % 8;
    _collect_slots(active, &active_n, inactive, &inactive_n);
    assert(active_n > 0);

    lifecycle_test_event_t event;
    memset(&event, 0, sizeof(event));
    event.event_index = event_index;
    event.target_slot = 0;
    event.parent_slot = -1;
    event.child_slot = -1;

    if (kind == 0) {
        event.event_type = LIFECYCLE_EVENT_TROPHIC;
        event.target_slot = active[(event_index / 8) % active_n];
        event.trophic_delta_raw = FP_020;
        event.reward_raw = FP_010;
        return event;
    }
    if (kind == 1 && inactive_n > 0) {
        event.event_type = LIFECYCLE_EVENT_CLEAVAGE;
        event.parent_slot = (int32_t)active[(event_index * 3) % active_n];
        event.child_slot = (int32_t)inactive[0];
        return event;
    }
    if (kind == 2) {
        event.event_type = LIFECYCLE_EVENT_TROPHIC;
        event.target_slot = active[active_n - 1];
        event.trophic_delta_raw = -FP_010;
        event.reward_raw = -FP_005;
        return event;
    }
    if (kind == 3) {
        event.event_type = LIFECYCLE_EVENT_MATURITY;
        event.target_slot = active[0];
        return event;
    }
    if (kind == 4 && inactive_n > 0 && active_n > 1) {
        event.event_type = LIFECYCLE_EVENT_ADULT_BIRTH;
        event.parent_slot = (int32_t)active[active_n - 1];
        event.child_slot = (int32_t)inactive[0];
        return event;
    }
    if (kind == 5) {
        event.event_type = LIFECYCLE_EVENT_TROPHIC;
        event.target_slot = active[(event_index + 1) % active_n];
        event.trophic_delta_raw = FP_008;
        event.reward_raw = FP_002;
        return event;
    }
    if (kind == 6 && active_n > 2) {
        event.event_type = LIFECYCLE_EVENT_DEATH;
        event.target_slot = active[active_n - 1];
        return event;
    }

    event.event_type = LIFECYCLE_EVENT_TROPHIC;
    event.target_slot = active[(event_index * 2) % active_n];
    event.trophic_delta_raw = -FP_004;
    event.reward_raw = 0;
    return event;
}

static void _run_events(uint32_t event_count) {
    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);
    for (uint32_t i = 0; i < event_count; i++) {
        lifecycle_test_event_t event = _choose_event(i);
        assert(cra_lifecycle_apply_event(
            event.event_index,
            event.event_type,
            event.target_slot,
            event.parent_slot,
            event.child_slot,
            event.trophic_delta_raw,
            event.reward_raw
        ) == 0);
    }
}

static void _generate_enabled_schedule(lifecycle_test_event_t *schedule, uint32_t event_count) {
    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);
    for (uint32_t i = 0; i < event_count; i++) {
        lifecycle_test_event_t event = _choose_event(i);
        schedule[i] = event;
        assert(cra_lifecycle_apply_event(
            event.event_index,
            event.event_type,
            event.target_slot,
            event.parent_slot,
            event.child_slot,
            event.trophic_delta_raw,
            event.reward_raw
        ) == 0);
    }
}

static void _run_precomputed_schedule(
    const lifecycle_test_event_t *schedule,
    uint32_t event_count,
    uint32_t sham_mode
) {
    static const uint32_t replay_order_32[32] = {
        7, 14, 22, 6, 17, 31, 9, 25,
        1, 18, 11, 13, 24, 2, 20, 3,
        28, 30, 23, 21, 29, 15, 16, 5,
        8, 10, 27, 12, 19, 0, 4, 26
    };
    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);
    assert(cra_lifecycle_set_sham_mode(sham_mode) == 0);
    for (uint32_t i = 0; i < event_count; i++) {
        lifecycle_test_event_t event = schedule[i];
        if (sham_mode == LIFECYCLE_SHAM_RANDOM_REPLAY && event_count == 32) {
            event = schedule[replay_order_32[i]];
            event.event_index = i;
        }
        (void)cra_lifecycle_apply_event(
            event.event_index,
            event.event_type,
            event.target_slot,
            event.parent_slot,
            event.child_slot,
            event.trophic_delta_raw,
            event.reward_raw
        );
    }
}

static void test_reference_parity_32(void) {
    cra_lifecycle_summary_t summary;
    _run_events(32);
    cra_lifecycle_get_summary(&summary);

    assert(summary.schema_version == LIFECYCLE_SCHEMA_VERSION);
    assert(summary.pool_size == 8);
    assert(summary.founder_count == 2);
    assert(summary.active_count == 6);
    assert(summary.inactive_count == 2);
    assert(summary.active_mask_bits == 63);
    assert(summary.attempted_event_count == 32);
    assert(summary.lifecycle_event_count == 32);
    assert(summary.cleavage_count == 4);
    assert(summary.adult_birth_count == 4);
    assert(summary.death_count == 4);
    assert(summary.invalid_event_count == 0);
    assert(summary.lineage_checksum == 105428);
    assert(summary.trophic_checksum == 466851);
    printf("  PASS: 4.30a canonical_32 lifecycle parity\n");
}

static void test_reference_parity_64(void) {
    cra_lifecycle_summary_t summary;
    _run_events(64);
    cra_lifecycle_get_summary(&summary);

    assert(summary.active_count == 7);
    assert(summary.inactive_count == 1);
    assert(summary.active_mask_bits == 127);
    assert(summary.attempted_event_count == 64);
    assert(summary.lifecycle_event_count == 64);
    assert(summary.cleavage_count == 8);
    assert(summary.adult_birth_count == 5);
    assert(summary.death_count == 8);
    assert(summary.invalid_event_count == 0);
    assert(summary.lineage_checksum == 18496);
    assert(summary.trophic_checksum == 761336);
    printf("  PASS: 4.30a boundary_64 lifecycle parity\n");
}

static void _dispatch_init(uint32_t pool_size, uint32_t founder_count) {
    sdp_msg_t msg;
    memset(&msg, 0, sizeof(msg));
    msg.cmd_rc = CMD_LIFECYCLE_INIT;
    msg.arg1 = pool_size;
    msg.arg2 = founder_count;
    msg.arg3 = 42;
    _write_s32(&msg.data[0], FP_ONE);
    _write_u32(&msg.data[4], 0);
    sdp_rx_callback((uint)(uintptr_t)&msg, 0);
    assert(((g_test_last_sdp_msg.cmd_rc >> 8) & 0xFF) == 0);
    assert((g_test_last_sdp_msg.cmd_rc & 0xFF) == CMD_LIFECYCLE_INIT);
}

static void _dispatch_event(const lifecycle_test_event_t *event) {
    sdp_msg_t msg;
    memset(&msg, 0, sizeof(msg));
    msg.cmd_rc = CMD_LIFECYCLE_EVENT;
    msg.arg1 = event->event_index;
    msg.arg2 = event->event_type;
    msg.arg3 = event->target_slot;
    _write_s32(&msg.data[0], event->parent_slot);
    _write_s32(&msg.data[4], event->child_slot);
    _write_s32(&msg.data[8], event->trophic_delta_raw);
    _write_s32(&msg.data[12], event->reward_raw);
    sdp_rx_callback((uint)(uintptr_t)&msg, 0);
    assert(((g_test_last_sdp_msg.cmd_rc >> 8) & 0xFF) == 0);
    assert((g_test_last_sdp_msg.cmd_rc & 0xFF) == CMD_LIFECYCLE_EVENT);
}

static void test_host_lifecycle_readback(void) {
    sdp_msg_t msg;
    _dispatch_init(MAX_LIFECYCLE_SLOTS, 2);
    for (uint32_t i = 0; i < 32; i++) {
        lifecycle_test_event_t event = _choose_event(i);
        _dispatch_event(&event);
    }

    memset(&msg, 0, sizeof(msg));
    msg.cmd_rc = CMD_LIFECYCLE_READ_STATE;
    sdp_rx_callback((uint)(uintptr_t)&msg, 0);
    assert(((g_test_last_sdp_msg.cmd_rc >> 8) & 0xFF) == 0);
    assert((g_test_last_sdp_msg.cmd_rc & 0xFF) == CMD_LIFECYCLE_READ_STATE);

    /* reply->data maps to payload[2..] because sdp_send_reply stores command/status in cmd_rc. */
    assert(g_test_last_sdp_msg.data[0] == LIFECYCLE_SCHEMA_VERSION);
    assert(g_test_last_sdp_msg.data[1] == LIFECYCLE_SHAM_ENABLED);
    assert(_read_u32(&g_test_last_sdp_msg.data[2]) == 8);
    assert(_read_u32(&g_test_last_sdp_msg.data[10]) == 6);
    assert(_read_u32(&g_test_last_sdp_msg.data[18]) == 63);
    assert(_read_u32(&g_test_last_sdp_msg.data[22]) == 32);
    assert(_read_u32(&g_test_last_sdp_msg.data[54]) == 105428);
    assert(_read_s32(&g_test_last_sdp_msg.data[58]) == 466851);
    printf("  PASS: lifecycle SDP readback schema\n");
}

static void test_sham_mode_bounds(void) {
    cra_lifecycle_summary_t summary;
    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);
    assert(cra_lifecycle_set_sham_mode(LIFECYCLE_SHAM_LINEAGE_SHUFFLE) == 0);
    cra_lifecycle_get_summary(&summary);
    assert(summary.sham_mode == LIFECYCLE_SHAM_LINEAGE_SHUFFLE);
    assert(cra_lifecycle_set_sham_mode(99) != 0);
    cra_lifecycle_get_summary(&summary);
    assert(summary.invalid_event_count == 1);
    printf("  PASS: lifecycle sham mode bounds\n");
}

static void test_fixed_pool_sham_suppresses_mask_mutation(void) {
    cra_lifecycle_summary_t summary;
    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);
    assert(cra_lifecycle_set_sham_mode(LIFECYCLE_SHAM_FIXED_POOL) == 0);

    assert(cra_lifecycle_apply_event(0, LIFECYCLE_EVENT_CLEAVAGE, 0, 0, 2, 0, 0) == 0);
    assert(cra_lifecycle_apply_event(1, LIFECYCLE_EVENT_DEATH, 0, -1, -1, 0, 0) == 0);
    cra_lifecycle_get_summary(&summary);

    assert(summary.sham_mode == LIFECYCLE_SHAM_FIXED_POOL);
    assert(summary.active_count == 2);
    assert(summary.active_mask_bits == 3);
    assert(summary.lifecycle_event_count == 2);
    assert(summary.cleavage_count == 0);
    assert(summary.death_count == 0);
    assert(summary.invalid_event_count == 0);
    printf("  PASS: fixed-pool sham suppresses lifecycle mask mutation\n");
}

static void test_trophic_shams_change_trophic_bookkeeping(void) {
    cra_lifecycle_summary_t summary;

    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);
    assert(cra_lifecycle_set_sham_mode(LIFECYCLE_SHAM_NO_TROPHIC) == 0);
    assert(cra_lifecycle_apply_event(0, LIFECYCLE_EVENT_TROPHIC, 0, -1, -1, FP_020, FP_010) == 0);
    assert(cra_lifecycle_apply_event(1, LIFECYCLE_EVENT_MATURITY, 0, -1, -1, 0, 0) == 0);
    cra_lifecycle_get_summary(&summary);
    assert(summary.sham_mode == LIFECYCLE_SHAM_NO_TROPHIC);
    assert(summary.trophic_checksum == 3 * FP_ONE);
    assert(summary.trophic_update_count == 1);
    assert(summary.maturity_count == 1);
    assert(summary.lifecycle_event_count == 2);

    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);
    assert(cra_lifecycle_set_sham_mode(LIFECYCLE_SHAM_NO_DOPAMINE) == 0);
    assert(cra_lifecycle_apply_event(0, LIFECYCLE_EVENT_TROPHIC, 0, -1, -1, 0, FP_ONE) == 0);
    cra_lifecycle_get_summary(&summary);
    assert(summary.sham_mode == LIFECYCLE_SHAM_NO_DOPAMINE);
    assert(summary.trophic_checksum == 3 * FP_ONE);
    assert(summary.trophic_update_count == 1);
    assert(summary.lifecycle_event_count == 1);
    printf("  PASS: no-trophic and no-dopamine shams alter trophic bookkeeping\n");
}

static void test_mask_shuffle_sham_maps_slots(void) {
    cra_lifecycle_summary_t summary;
    assert(cra_lifecycle_init(MAX_LIFECYCLE_SLOTS, 2, 42, FP_ONE, 0) == 0);
    assert(cra_lifecycle_set_sham_mode(LIFECYCLE_SHAM_MASK_SHUFFLE) == 0);

    /* Slot 4 is inactive in the initialized pool, but sham mapping 4 -> 0
     * makes this a valid death event against founder slot 0. */
    assert(cra_lifecycle_apply_event(0, LIFECYCLE_EVENT_DEATH, 4, -1, -1, 0, 0) == 0);
    cra_lifecycle_get_summary(&summary);
    assert(summary.sham_mode == LIFECYCLE_SHAM_MASK_SHUFFLE);
    assert(summary.active_count == 1);
    assert(summary.active_mask_bits == 2);
    assert(summary.death_count == 1);
    assert(summary.invalid_event_count == 0);
    printf("  PASS: mask-shuffle sham remaps lifecycle event slots\n");
}

static void test_canonical_32_sham_reference_parity(void) {
    lifecycle_test_event_t schedule[32];
    cra_lifecycle_summary_t summary;
    _generate_enabled_schedule(schedule, 32);

    _run_precomputed_schedule(schedule, 32, LIFECYCLE_SHAM_FIXED_POOL);
    cra_lifecycle_get_summary(&summary);
    assert(summary.active_mask_bits == 3);
    assert(summary.active_count == 2);
    assert(summary.lifecycle_event_count == 19);
    assert(summary.invalid_event_count == 13);
    assert(summary.cleavage_count == 0);
    assert(summary.adult_birth_count == 0);
    assert(summary.death_count == 0);
    assert(summary.trophic_checksum == 151469);

    _run_precomputed_schedule(schedule, 32, LIFECYCLE_SHAM_RANDOM_REPLAY);
    cra_lifecycle_get_summary(&summary);
    assert(summary.active_mask_bits == 0);
    assert(summary.lifecycle_event_count == 2);
    assert(summary.invalid_event_count == 30);
    assert(summary.lineage_checksum == 6170);
    assert(summary.trophic_checksum == 98304);

    _run_precomputed_schedule(schedule, 32, LIFECYCLE_SHAM_MASK_SHUFFLE);
    cra_lifecycle_get_summary(&summary);
    assert(summary.active_mask_bits == 0);
    assert(summary.lifecycle_event_count == 3);
    assert(summary.invalid_event_count == 29);
    assert(summary.lineage_checksum == 6170);
    assert(summary.trophic_checksum == 102480);

    _run_precomputed_schedule(schedule, 32, LIFECYCLE_SHAM_NO_TROPHIC);
    cra_lifecycle_get_summary(&summary);
    assert(summary.active_mask_bits == 63);
    assert(summary.lifecycle_event_count == 32);
    assert(summary.invalid_event_count == 0);
    assert(summary.trophic_checksum == 336384);

    _run_precomputed_schedule(schedule, 32, LIFECYCLE_SHAM_NO_DOPAMINE);
    cra_lifecycle_get_summary(&summary);
    assert(summary.active_mask_bits == 63);
    assert(summary.lifecycle_event_count == 32);
    assert(summary.invalid_event_count == 0);
    assert(summary.trophic_checksum == 457850);

    printf("  PASS: canonical_32 sham-control reference parity\n");
}

int main(void) {
    printf("Running Tier 4.30 lifecycle/static-pool tests...\n");
    cra_state_init();
    test_reference_parity_32();
    test_reference_parity_64();
    test_host_lifecycle_readback();
    test_sham_mode_bounds();
    test_fixed_pool_sham_suppresses_mask_mutation();
    test_trophic_shams_change_trophic_bookkeeping();
    test_mask_shuffle_sham_maps_slots();
    test_canonical_32_sham_reference_parity();
    printf("All lifecycle/static-pool tests passed.\n");
    return 0;
}
