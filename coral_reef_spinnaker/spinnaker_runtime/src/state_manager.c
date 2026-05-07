/*!
 * \file state_manager.c
 * \brief Static persistent state owned by the custom C runtime.
 */
#include "state_manager.h"
#include "router.h"
#include <sark.h>
#include <spin1_api.h>

static context_slot_t g_context_slots[MAX_CONTEXT_SLOTS];
static route_slot_t g_route_slots[MAX_ROUTE_SLOTS];
static memory_slot_t g_memory_slots[MAX_MEMORY_SLOTS];
static pending_horizon_t g_pending_horizons[MAX_PENDING_HORIZONS];
cra_state_summary_t g_summary;

static schedule_entry_t g_schedule[MAX_SCHEDULE_ENTRIES];
static uint32_t g_schedule_count = 0;
static uint32_t g_schedule_index = 0;
static uint32_t g_schedule_base_timestep = 0;
static uint8_t g_continuous_mode = 0;
static int32_t g_learning_rate = 0;
static lifecycle_slot_t g_lifecycle_slots[MAX_LIFECYCLE_SLOTS];
static cra_lifecycle_summary_t g_lifecycle_summary;
static uint32_t g_lifecycle_next_polyp_id = 2000;
static uint32_t g_lifecycle_next_lineage_id = 100;
static uint8_t g_lifecycle_have_last_event_index = 0;
static uint32_t g_lifecycle_last_event_index = 0;
static int32_t g_temporal_traces[TEMPORAL_TRACE_COUNT];
static cra_temporal_summary_t g_temporal_summary;
static const int32_t g_temporal_decay_raw[TEMPORAL_TRACE_COUNT] = {
    TEMPORAL_DECAY_RAW_0,
    TEMPORAL_DECAY_RAW_1,
    TEMPORAL_DECAY_RAW_2,
    TEMPORAL_DECAY_RAW_3,
    TEMPORAL_DECAY_RAW_4,
    TEMPORAL_DECAY_RAW_5,
    TEMPORAL_DECAY_RAW_6
};
static const int32_t g_temporal_alpha_raw[TEMPORAL_TRACE_COUNT] = {
    TEMPORAL_ALPHA_RAW_0,
    TEMPORAL_ALPHA_RAW_1,
    TEMPORAL_ALPHA_RAW_2,
    TEMPORAL_ALPHA_RAW_3,
    TEMPORAL_ALPHA_RAW_4,
    TEMPORAL_ALPHA_RAW_5,
    TEMPORAL_ALPHA_RAW_6
};

extern uint32_t g_timestep;

static int32_t _floor_div_i32(int32_t value, int32_t divisor) {
    if (divisor <= 0) {
        return 0;
    }
    if (value >= 0) {
        return value / divisor;
    }
    return -(((-value) + divisor - 1) / divisor);
}

static int32_t _clamp_i32(int32_t value, int32_t min_value, int32_t max_value) {
    if (value < min_value) {
        return min_value;
    }
    if (value > max_value) {
        return max_value;
    }
    return value;
}

static int32_t _abs_i32(int32_t value) {
    return value < 0 ? -value : value;
}

static int32_t _temporal_clip_trace(int32_t value, uint32_t *clipped_out) {
    if (value > TEMPORAL_TRACE_BOUND) {
        if (clipped_out != 0) {
            *clipped_out = 1;
        }
        return TEMPORAL_TRACE_BOUND;
    }
    if (value < -TEMPORAL_TRACE_BOUND) {
        if (clipped_out != 0) {
            *clipped_out = 1;
        }
        return -TEMPORAL_TRACE_BOUND;
    }
    return value;
}

static void _temporal_recompute_abs_sum(void) {
    uint32_t total = 0;
    for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
        total += (uint32_t)_abs_i32(g_temporal_traces[i]);
    }
    g_temporal_summary.trace_abs_sum_raw = total;
}

static void _temporal_accumulate_checksum(void) {
    int64_t weighted_sum = 0;
    for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
        weighted_sum += (int64_t)(i + 1) * (int64_t)g_temporal_traces[i];
    }
    g_temporal_summary.trace_checksum =
        (uint32_t)(g_temporal_summary.trace_checksum * 2654435761U + (uint32_t)weighted_sum);
}

static void _temporal_clear_traces_only(void) {
    for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
        g_temporal_traces[i] = 0;
    }
    _temporal_recompute_abs_sum();
}

static void _temporal_clear(uint32_t reset_count) {
    _temporal_clear_traces_only();
    g_temporal_summary.schema_version = TEMPORAL_SCHEMA_VERSION;
    g_temporal_summary.trace_count = TEMPORAL_TRACE_COUNT;
    g_temporal_summary.timescale_checksum = TEMPORAL_TIMESCALE_CHECKSUM;
    g_temporal_summary.update_count = 0;
    g_temporal_summary.saturation_count = 0;
    g_temporal_summary.reset_count = reset_count;
    g_temporal_summary.input_clip_count = 0;
    g_temporal_summary.sham_mode = TEMPORAL_SHAM_ENABLED;
    g_temporal_summary.trace_checksum = 0;
    g_temporal_summary.latest_input_raw = 0;
    g_temporal_summary.latest_novelty_raw = 0;
}

void cra_temporal_reset(void) {
    _temporal_clear(g_temporal_summary.reset_count + 1);
}

int cra_temporal_init(void) {
    _temporal_clear(0);
    return 0;
}

int cra_temporal_set_sham_mode(uint32_t mode) {
    if (mode > TEMPORAL_SHAM_RESET_EACH_UPDATE) {
        return -1;
    }
    g_temporal_summary.sham_mode = mode;
    if (mode == TEMPORAL_SHAM_ZERO_STATE || mode == TEMPORAL_SHAM_RESET_EACH_UPDATE) {
        _temporal_clear_traces_only();
        g_temporal_summary.trace_checksum = 0;
        g_temporal_summary.latest_novelty_raw = 0;
        g_temporal_summary.reset_count++;
    }
    return 0;
}

int cra_temporal_update(int32_t input_raw) {
    int32_t x = input_raw;
    int32_t slowest_before = g_temporal_traces[TEMPORAL_TRACE_COUNT - 1];

    if (x > TEMPORAL_INPUT_BOUND) {
        x = TEMPORAL_INPUT_BOUND;
        g_temporal_summary.input_clip_count++;
    } else if (x < -TEMPORAL_INPUT_BOUND) {
        x = -TEMPORAL_INPUT_BOUND;
        g_temporal_summary.input_clip_count++;
    }

    g_temporal_summary.update_count++;
    g_temporal_summary.latest_input_raw = x;
    g_temporal_summary.latest_novelty_raw =
        _clamp_i32(x - slowest_before, -TEMPORAL_NOVELTY_BOUND, TEMPORAL_NOVELTY_BOUND);

    if (g_temporal_summary.sham_mode == TEMPORAL_SHAM_ZERO_STATE) {
        _temporal_clear_traces_only();
        g_temporal_summary.latest_novelty_raw = 0;
        _temporal_accumulate_checksum();
        return 0;
    }

    if (g_temporal_summary.sham_mode == TEMPORAL_SHAM_RESET_EACH_UPDATE) {
        _temporal_clear_traces_only();
        g_temporal_summary.reset_count++;
    }

    if (g_temporal_summary.sham_mode != TEMPORAL_SHAM_FROZEN_STATE) {
        for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
            uint32_t clipped = 0;
            int32_t candidate = FP_MUL(g_temporal_decay_raw[i], g_temporal_traces[i])
                + FP_MUL(g_temporal_alpha_raw[i], x);
            g_temporal_traces[i] = _temporal_clip_trace(candidate, &clipped);
            g_temporal_summary.saturation_count += clipped;
        }
    }

    _temporal_recompute_abs_sum();
    _temporal_accumulate_checksum();
    return 0;
}

void cra_temporal_get_summary(cra_temporal_summary_t *summary_out) {
    if (summary_out == 0) {
        return;
    }
    *summary_out = g_temporal_summary;
}

int cra_temporal_get_trace(uint32_t index, int32_t *trace_out) {
    if (index >= TEMPORAL_TRACE_COUNT || trace_out == 0) {
        return -1;
    }
    *trace_out = g_temporal_traces[index];
    return 0;
}

static void _lifecycle_recompute_summary(void) {
    uint32_t active_count = 0;
    uint32_t active_mask_bits = 0;
    uint32_t lineage_checksum = 0;
    int64_t trophic_checksum = 0;

    for (uint32_t i = 0; i < MAX_LIFECYCLE_SLOTS; i++) {
        lifecycle_slot_t *slot = &g_lifecycle_slots[i];
        if (i < g_lifecycle_summary.pool_size && slot->active) {
            active_count++;
            active_mask_bits |= (1u << i);
        }
        if (i < g_lifecycle_summary.pool_size) {
            int32_t parent_factor = slot->parent_slot + 3;
            uint32_t active_factor = slot->active ? 1u : 5u;
            uint64_t line = (uint64_t)(slot->slot_id + 1)
                * (uint64_t)(slot->lineage_id + 17)
                * (uint64_t)(slot->generation + 1)
                * (uint64_t)parent_factor
                * (uint64_t)active_factor;
            lineage_checksum = (uint32_t)(lineage_checksum + (uint32_t)line);
            trophic_checksum += (int64_t)(slot->slot_id + 1)
                * (int64_t)(slot->trophic + slot->cyclin - slot->bax);
        }
    }

    g_lifecycle_summary.active_count = active_count;
    g_lifecycle_summary.inactive_count = g_lifecycle_summary.pool_size - active_count;
    g_lifecycle_summary.active_mask_bits = active_mask_bits;
    g_lifecycle_summary.lineage_checksum = lineage_checksum;
    g_lifecycle_summary.trophic_checksum = (int32_t)trophic_checksum;
}

static void _lifecycle_touch_active_ages(void) {
    for (uint32_t i = 0; i < g_lifecycle_summary.pool_size; i++) {
        if (g_lifecycle_slots[i].active) {
            g_lifecycle_slots[i].age++;
        }
    }
}

static int _lifecycle_slot_is_valid(uint32_t slot_id) {
    return slot_id < g_lifecycle_summary.pool_size && slot_id < MAX_LIFECYCLE_SLOTS;
}

static int32_t _lifecycle_sham_map_slot(int32_t slot_id) {
    static const int32_t permutation[MAX_LIFECYCLE_SLOTS] = {4, 7, 6, 5, 0, 2, 1, 3};
    if (slot_id < 0 || slot_id >= (int32_t)MAX_LIFECYCLE_SLOTS) {
        return slot_id;
    }
    if (slot_id >= (int32_t)g_lifecycle_summary.pool_size) {
        return slot_id;
    }
    return permutation[slot_id];
}

static int _lifecycle_sham_maps_event_slots(void) {
    return g_lifecycle_summary.sham_mode == LIFECYCLE_SHAM_RANDOM_REPLAY
        || g_lifecycle_summary.sham_mode == LIFECYCLE_SHAM_MASK_SHUFFLE;
}

static int _lifecycle_apply_trophic_to_slot(
    lifecycle_slot_t *slot,
    int32_t trophic_delta_raw,
    int32_t reward_raw
) {
    if (slot == 0 || !slot->active) {
        return -1;
    }

    int32_t reward_component = g_lifecycle_summary.sham_mode == LIFECYCLE_SHAM_NO_DOPAMINE
        ? 0
        : _floor_div_i32(reward_raw, 4);
    int32_t net = trophic_delta_raw + reward_component;
    slot->trophic = _clamp_i32(slot->trophic + net, -4 * FP_ONE, 4 * FP_ONE);

    if (net >= 0) {
        slot->cyclin = _clamp_i32(slot->cyclin + _floor_div_i32(net, 2), 0, 4 * FP_ONE);
        slot->bax = _clamp_i32(slot->bax - _floor_div_i32(net, 4), 0, 4 * FP_ONE);
    } else {
        int32_t loss = -net;
        slot->bax = _clamp_i32(slot->bax + _floor_div_i32(loss, 2), 0, 4 * FP_ONE);
        slot->cyclin = _clamp_i32(slot->cyclin + _floor_div_i32(net, 4), 0, 4 * FP_ONE);
    }
    return 0;
}

void cra_lifecycle_reset(void) {
    for (uint32_t i = 0; i < MAX_LIFECYCLE_SLOTS; i++) {
        g_lifecycle_slots[i].slot_id = i;
        g_lifecycle_slots[i].polyp_id = 0;
        g_lifecycle_slots[i].lineage_id = 0;
        g_lifecycle_slots[i].parent_slot = -1;
        g_lifecycle_slots[i].generation = 0;
        g_lifecycle_slots[i].age = 0;
        g_lifecycle_slots[i].trophic = 0;
        g_lifecycle_slots[i].cyclin = 0;
        g_lifecycle_slots[i].bax = 0;
        g_lifecycle_slots[i].event_count = 0;
        g_lifecycle_slots[i].active = 0;
        g_lifecycle_slots[i].last_event_type = LIFECYCLE_EVENT_NONE;
    }

    g_lifecycle_summary.schema_version = LIFECYCLE_SCHEMA_VERSION;
    g_lifecycle_summary.pool_size = 0;
    g_lifecycle_summary.founder_count = 0;
    g_lifecycle_summary.active_count = 0;
    g_lifecycle_summary.inactive_count = 0;
    g_lifecycle_summary.active_mask_bits = 0;
    g_lifecycle_summary.attempted_event_count = 0;
    g_lifecycle_summary.lifecycle_event_count = 0;
    g_lifecycle_summary.cleavage_count = 0;
    g_lifecycle_summary.adult_birth_count = 0;
    g_lifecycle_summary.death_count = 0;
    g_lifecycle_summary.maturity_count = 0;
    g_lifecycle_summary.trophic_update_count = 0;
    g_lifecycle_summary.invalid_event_count = 0;
    g_lifecycle_summary.lineage_checksum = 0;
    g_lifecycle_summary.trophic_checksum = 0;
    g_lifecycle_summary.sham_mode = LIFECYCLE_SHAM_ENABLED;
    g_lifecycle_next_polyp_id = 2000;
    g_lifecycle_next_lineage_id = 100;
    g_lifecycle_have_last_event_index = 0;
    g_lifecycle_last_event_index = 0;
}

int cra_lifecycle_init(
    uint32_t pool_size,
    uint32_t founder_count,
    uint32_t seed,
    int32_t trophic_seed_raw,
    uint32_t generation_seed
) {
    (void)seed;
    if (pool_size == 0 || pool_size > MAX_LIFECYCLE_SLOTS || founder_count > pool_size) {
        cra_lifecycle_reset();
        g_lifecycle_summary.invalid_event_count++;
        return -1;
    }

    cra_lifecycle_reset();
    g_lifecycle_summary.pool_size = pool_size;
    g_lifecycle_summary.founder_count = founder_count;
    g_lifecycle_next_polyp_id = 2000 + generation_seed;
    g_lifecycle_next_lineage_id = 100 + generation_seed;

    for (uint32_t i = 0; i < pool_size; i++) {
        lifecycle_slot_t *slot = &g_lifecycle_slots[i];
        slot->slot_id = i;
        slot->parent_slot = -1;
        if (i < founder_count) {
            slot->active = 1;
            slot->polyp_id = 1000 + i;
            slot->lineage_id = i + 1;
            slot->trophic = trophic_seed_raw;
            slot->cyclin = 0;
            slot->bax = 0;
        }
    }

    _lifecycle_recompute_summary();
    return 0;
}

int cra_lifecycle_apply_trophic_update(
    uint32_t target_slot,
    int32_t trophic_delta_raw,
    int32_t reward_raw
) {
    return cra_lifecycle_apply_event(
        g_lifecycle_summary.attempted_event_count,
        LIFECYCLE_EVENT_TROPHIC,
        target_slot,
        -1,
        -1,
        trophic_delta_raw,
        reward_raw
    );
}

int cra_lifecycle_apply_event(
    uint32_t event_index,
    uint8_t event_type,
    uint32_t target_slot,
    int32_t parent_slot,
    int32_t child_slot,
    int32_t trophic_delta_raw,
    int32_t reward_raw
) {
    (void)event_index;
    int rc = 0;

    g_lifecycle_summary.attempted_event_count++;
    _lifecycle_touch_active_ages();

    if (g_lifecycle_summary.pool_size == 0) {
        g_lifecycle_summary.invalid_event_count++;
        _lifecycle_recompute_summary();
        return -1;
    }

    lifecycle_slot_t *target = _lifecycle_slot_is_valid(target_slot)
        ? &g_lifecycle_slots[target_slot]
        : 0;

    if (_lifecycle_sham_maps_event_slots()) {
        int32_t mapped_target = _lifecycle_sham_map_slot((int32_t)target_slot);
        int32_t mapped_parent = _lifecycle_sham_map_slot(parent_slot);
        int32_t mapped_child = _lifecycle_sham_map_slot(child_slot);
        target_slot = mapped_target < 0 ? target_slot : (uint32_t)mapped_target;
        parent_slot = mapped_parent;
        child_slot = mapped_child;
        target = _lifecycle_slot_is_valid(target_slot)
            ? &g_lifecycle_slots[target_slot]
            : 0;
    }

    if (event_type == LIFECYCLE_EVENT_TROPHIC) {
        if (target == 0 || !target->active) {
            rc = -1;
        } else {
            if (g_lifecycle_summary.sham_mode != LIFECYCLE_SHAM_NO_TROPHIC) {
                (void)_lifecycle_apply_trophic_to_slot(target, trophic_delta_raw, reward_raw);
            }
            target->event_count++;
            target->last_event_type = event_type;
            g_lifecycle_summary.trophic_update_count++;
            g_lifecycle_summary.lifecycle_event_count++;
        }
    } else if (event_type == LIFECYCLE_EVENT_CLEAVAGE || event_type == LIFECYCLE_EVENT_ADULT_BIRTH) {
        if (g_lifecycle_summary.sham_mode == LIFECYCLE_SHAM_FIXED_POOL) {
            g_lifecycle_summary.lifecycle_event_count++;
        } else if (parent_slot < 0 || child_slot < 0 ||
            !_lifecycle_slot_is_valid((uint32_t)parent_slot) ||
            !_lifecycle_slot_is_valid((uint32_t)child_slot) ||
            !g_lifecycle_slots[(uint32_t)parent_slot].active ||
            g_lifecycle_slots[(uint32_t)child_slot].active) {
            rc = -1;
        } else {
            lifecycle_slot_t *parent = &g_lifecycle_slots[(uint32_t)parent_slot];
            lifecycle_slot_t *child = &g_lifecycle_slots[(uint32_t)child_slot];
            child->active = 1;
            child->polyp_id = g_lifecycle_next_polyp_id++;
            child->lineage_id = (event_type == LIFECYCLE_EVENT_CLEAVAGE)
                ? parent->lineage_id
                : g_lifecycle_next_lineage_id++;
            child->parent_slot = parent_slot;
            child->generation = parent->generation + 1;
            child->age = 0;
            child->trophic = parent->trophic / 2;
            if (child->trophic < FP_FROM_FLOAT(0.25f)) {
                child->trophic = FP_FROM_FLOAT(0.25f);
            }
            child->cyclin = 0;
            child->bax = 0;
            child->event_count = 1;
            child->last_event_type = event_type;
            parent->trophic = _clamp_i32(parent->trophic - (child->trophic / 4), -4 * FP_ONE, 4 * FP_ONE);
            parent->event_count++;
            parent->last_event_type = event_type;
            if (event_type == LIFECYCLE_EVENT_CLEAVAGE) {
                g_lifecycle_summary.cleavage_count++;
            } else {
                g_lifecycle_summary.adult_birth_count++;
            }
            g_lifecycle_summary.lifecycle_event_count++;
        }
    } else if (event_type == LIFECYCLE_EVENT_DEATH) {
        if (g_lifecycle_summary.sham_mode == LIFECYCLE_SHAM_FIXED_POOL) {
            g_lifecycle_summary.lifecycle_event_count++;
        } else if (target == 0 || !target->active) {
            rc = -1;
        } else {
            target->active = 0;
            target->event_count++;
            target->last_event_type = event_type;
            g_lifecycle_summary.death_count++;
            g_lifecycle_summary.lifecycle_event_count++;
        }
    } else if (event_type == LIFECYCLE_EVENT_MATURITY) {
        if (target == 0 || !target->active) {
            rc = -1;
        } else {
            if (g_lifecycle_summary.sham_mode != LIFECYCLE_SHAM_NO_TROPHIC) {
                target->trophic = _clamp_i32(target->trophic + FP_FROM_FLOAT(0.0625f), -4 * FP_ONE, 4 * FP_ONE);
                target->cyclin = _clamp_i32(target->cyclin + FP_FROM_FLOAT(0.125f), 0, 4 * FP_ONE);
                target->bax = _clamp_i32(target->bax - FP_FROM_FLOAT(0.03125f), 0, 4 * FP_ONE);
            }
            target->event_count++;
            target->last_event_type = event_type;
            g_lifecycle_summary.maturity_count++;
            g_lifecycle_summary.lifecycle_event_count++;
        }
    } else {
        rc = -1;
    }

    if (rc != 0) {
        g_lifecycle_summary.invalid_event_count++;
    }
    _lifecycle_recompute_summary();
    return rc;
}

int cra_lifecycle_set_sham_mode(uint32_t mode) {
    if (mode > LIFECYCLE_SHAM_NO_DOPAMINE) {
        g_lifecycle_summary.invalid_event_count++;
        return -1;
    }
    g_lifecycle_summary.sham_mode = mode;
    return 0;
}

void cra_lifecycle_get_summary(cra_lifecycle_summary_t *summary_out) {
    if (summary_out == 0) {
        return;
    }
    _lifecycle_recompute_summary();
    *summary_out = g_lifecycle_summary;
}

int cra_lifecycle_get_slot(uint32_t slot_id, lifecycle_slot_t *slot_out) {
    if (!_lifecycle_slot_is_valid(slot_id) || slot_out == 0) {
        return -1;
    }
    *slot_out = g_lifecycle_slots[slot_id];
    return 0;
}

static uint8_t _lifecycle_event_mutates_active_mask(uint8_t event_type) {
    return event_type == LIFECYCLE_EVENT_CLEAVAGE
        || event_type == LIFECYCLE_EVENT_ADULT_BIRTH
        || event_type == LIFECYCLE_EVENT_DEATH;
}

static void _lifecycle_broadcast_active_mask_sync(void) {
    cra_lifecycle_summary_t summary;
    cra_lifecycle_get_summary(&summary);
    uint32_t seq = summary.lifecycle_event_count & MCPL_KEY_SEQ_MASK;
    uint32_t mask_key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC,
        MCPL_LIFECYCLE_SYNC_MASK,
        seq);
    uint32_t mask_payload = (summary.active_mask_bits & 0xFFFF)
        | ((summary.active_count & 0xFF) << 16);
    spin1_send_mc_packet(mask_key, mask_payload, WITH_PAYLOAD);

    uint32_t lineage_key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC,
        MCPL_LIFECYCLE_SYNC_LINEAGE,
        seq);
    spin1_send_mc_packet(lineage_key, summary.lineage_checksum, WITH_PAYLOAD);
    g_summary.lifecycle_mask_syncs_sent++;
}

void cra_lifecycle_send_event_request_stub(uint32_t event_index, uint8_t event_type, uint32_t target_slot) {
    uint32_t key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_EVENT_REQUEST,
        event_type & 0x0F,
        event_index & MCPL_KEY_SEQ_MASK);
    spin1_send_mc_packet(key, target_slot, WITH_PAYLOAD);
    g_summary.lifecycle_event_requests_sent++;
}

void cra_lifecycle_send_trophic_update_stub(uint32_t target_slot, int32_t trophic_delta_raw) {
    uint32_t key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE,
        0,
        target_slot & MCPL_KEY_SEQ_MASK);
    spin1_send_mc_packet(key, (uint32_t)trophic_delta_raw, WITH_PAYLOAD);
    g_summary.lifecycle_trophic_requests_sent++;
}

static int _lifecycle_reject_duplicate_or_stale(uint32_t event_index) {
    if (!g_lifecycle_have_last_event_index) {
        return 0;
    }
    if (event_index == g_lifecycle_last_event_index) {
        g_summary.lifecycle_duplicate_events++;
        g_lifecycle_summary.invalid_event_count++;
        return -1;
    }
    if (event_index < g_lifecycle_last_event_index) {
        g_summary.lifecycle_stale_events++;
        g_lifecycle_summary.invalid_event_count++;
        return -1;
    }
    return 0;
}

int cra_lifecycle_handle_event_request(
    uint32_t event_index,
    uint8_t event_type,
    uint32_t target_slot,
    int32_t parent_slot,
    int32_t child_slot,
    int32_t trophic_delta_raw,
    int32_t reward_raw
) {
    if (_lifecycle_reject_duplicate_or_stale(event_index) != 0) {
        _lifecycle_recompute_summary();
        return -1;
    }

    uint32_t before_mask = g_lifecycle_summary.active_mask_bits;
    int rc = cra_lifecycle_apply_event(
        event_index,
        event_type,
        target_slot,
        parent_slot,
        child_slot,
        trophic_delta_raw,
        reward_raw);

    if (rc == 0) {
        g_lifecycle_have_last_event_index = 1;
        g_lifecycle_last_event_index = event_index;
        g_summary.lifecycle_event_acks_received++;
        if (_lifecycle_event_mutates_active_mask(event_type)
            && g_lifecycle_summary.active_mask_bits != before_mask) {
            _lifecycle_broadcast_active_mask_sync();
        }
    }
    return rc;
}

int cra_lifecycle_handle_trophic_request(
    uint32_t event_index,
    uint32_t target_slot,
    int32_t trophic_delta_raw,
    int32_t reward_raw
) {
    return cra_lifecycle_handle_event_request(
        event_index,
        LIFECYCLE_EVENT_TROPHIC,
        target_slot,
        -1,
        -1,
        trophic_delta_raw,
        reward_raw);
}

void cra_lifecycle_receive_active_mask_sync(
    uint32_t event_count,
    uint32_t active_mask_bits,
    uint32_t lineage_checksum
) {
    g_summary.lifecycle_mask_syncs_received++;
    g_summary.lifecycle_last_seen_event_count = event_count;
    g_summary.lifecycle_last_seen_active_mask_bits = active_mask_bits;
    g_summary.lifecycle_last_seen_lineage_checksum = lineage_checksum;
}

void cra_lifecycle_record_missing_ack(void) {
    g_summary.lifecycle_missing_acks++;
}

static void _clear_slots(void) {
    for (uint32_t i = 0; i < MAX_CONTEXT_SLOTS; i++) {
        g_context_slots[i].key = 0;
        g_context_slots[i].value = 0;
        g_context_slots[i].confidence = 0;
        g_context_slots[i].last_update = 0;
        g_context_slots[i].active = 0;
    }
}

static void _clear_route_slots(void) {
    for (uint32_t i = 0; i < MAX_ROUTE_SLOTS; i++) {
        g_route_slots[i].key = 0;
        g_route_slots[i].value = 0;
        g_route_slots[i].confidence = 0;
        g_route_slots[i].last_update = 0;
        g_route_slots[i].active = 0;
    }
}

static void _clear_memory_slots(void) {
    for (uint32_t i = 0; i < MAX_MEMORY_SLOTS; i++) {
        g_memory_slots[i].key = 0;
        g_memory_slots[i].value = 0;
        g_memory_slots[i].confidence = 0;
        g_memory_slots[i].last_update = 0;
        g_memory_slots[i].active = 0;
    }
}

static void _clear_summary(uint32_t reset_count) {
    g_summary.active_slots = 0;
    g_summary.slot_writes = 0;
    g_summary.slot_hits = 0;
    g_summary.slot_misses = 0;
    g_summary.slot_evictions = 0;
    g_summary.decisions = 0;
    g_summary.reward_events = 0;
    g_summary.pending_created = 0;
    g_summary.pending_matured = 0;
    g_summary.pending_dropped = 0;
    g_summary.active_pending = 0;
    g_summary.state_resets = reset_count;
    g_summary.route_writes = 0;
    g_summary.route_reads = 0;
    g_summary.active_route_slots = 0;
    g_summary.route_slot_writes = 0;
    g_summary.route_slot_hits = 0;
    g_summary.route_slot_misses = 0;
    g_summary.route_slot_evictions = 0;
    g_summary.active_memory_slots = 0;
    g_summary.memory_slot_writes = 0;
    g_summary.memory_slot_hits = 0;
    g_summary.memory_slot_misses = 0;
    g_summary.memory_slot_evictions = 0;
    g_summary.readout_weight = 0;
    g_summary.readout_bias = 0;
    g_summary.route_value = FP_ONE;
    g_summary.route_confidence = FP_ONE;
    g_summary.last_feature = 0;
    g_summary.last_prediction = 0;
    g_summary.last_reward = 0;
    g_summary.lookup_requests_sent = 0;
    g_summary.lookup_replies_received = 0;
    g_summary.lookup_stale_replies = 0;
    g_summary.lookup_duplicate_replies = 0;
    g_summary.lookup_timeouts = 0;
    g_summary.commands_received = 0;
    g_summary.schedule_length = 0;
    g_summary.readback_bytes_sent = 0;
    g_summary.lifecycle_event_requests_sent = 0;
    g_summary.lifecycle_trophic_requests_sent = 0;
    g_summary.lifecycle_event_acks_received = 0;
    g_summary.lifecycle_mask_syncs_sent = 0;
    g_summary.lifecycle_mask_syncs_received = 0;
    g_summary.lifecycle_last_seen_event_count = 0;
    g_summary.lifecycle_last_seen_active_mask_bits = 0;
    g_summary.lifecycle_last_seen_lineage_checksum = 0;
    g_summary.lifecycle_duplicate_events = 0;
    g_summary.lifecycle_stale_events = 0;
    g_summary.lifecycle_missing_acks = 0;
}

static void _clear_pending(void) {
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        g_pending_horizons[i].due_timestep = 0;
        g_pending_horizons[i].feature = 0;
        g_pending_horizons[i].prediction = 0;
        g_pending_horizons[i].target = 0;
        g_pending_horizons[i].composite_confidence = 0;
        g_pending_horizons[i].active = 0;
        g_pending_horizons[i].has_confidence = 0;
    }
}

static int _find_slot(uint32_t key) {
    for (uint32_t i = 0; i < MAX_CONTEXT_SLOTS; i++) {
        if (g_context_slots[i].active && g_context_slots[i].key == key) {
            return (int)i;
        }
    }
    return -1;
}

static int _select_slot_for_write(uint32_t *evicted) {
    *evicted = 0;
    for (uint32_t i = 0; i < MAX_CONTEXT_SLOTS; i++) {
        if (!g_context_slots[i].active) {
            return (int)i;
        }
    }

    uint32_t victim = 0;
    for (uint32_t i = 1; i < MAX_CONTEXT_SLOTS; i++) {
        context_slot_t *candidate = &g_context_slots[i];
        context_slot_t *current = &g_context_slots[victim];
        if (candidate->confidence < current->confidence ||
            (candidate->confidence == current->confidence && candidate->last_update < current->last_update)) {
            victim = i;
        }
    }
    *evicted = 1;
    return (int)victim;
}

static int _find_route_slot(uint32_t key) {
    for (uint32_t i = 0; i < MAX_ROUTE_SLOTS; i++) {
        if (g_route_slots[i].active && g_route_slots[i].key == key) {
            return (int)i;
        }
    }
    return -1;
}

static int _select_route_slot_for_write(uint32_t *evicted) {
    *evicted = 0;
    for (uint32_t i = 0; i < MAX_ROUTE_SLOTS; i++) {
        if (!g_route_slots[i].active) {
            return (int)i;
        }
    }

    uint32_t victim = 0;
    for (uint32_t i = 1; i < MAX_ROUTE_SLOTS; i++) {
        route_slot_t *candidate = &g_route_slots[i];
        route_slot_t *current = &g_route_slots[victim];
        if (candidate->confidence < current->confidence ||
            (candidate->confidence == current->confidence && candidate->last_update < current->last_update)) {
            victim = i;
        }
    }
    *evicted = 1;
    return (int)victim;
}

static int _find_memory_slot(uint32_t key) {
    for (uint32_t i = 0; i < MAX_MEMORY_SLOTS; i++) {
        if (g_memory_slots[i].active && g_memory_slots[i].key == key) {
            return (int)i;
        }
    }
    return -1;
}

static int _select_memory_slot_for_write(uint32_t *evicted) {
    *evicted = 0;
    for (uint32_t i = 0; i < MAX_MEMORY_SLOTS; i++) {
        if (!g_memory_slots[i].active) {
            return (int)i;
        }
    }

    uint32_t victim = 0;
    for (uint32_t i = 1; i < MAX_MEMORY_SLOTS; i++) {
        memory_slot_t *candidate = &g_memory_slots[i];
        memory_slot_t *current = &g_memory_slots[victim];
        if (candidate->confidence < current->confidence ||
            (candidate->confidence == current->confidence && candidate->last_update < current->last_update)) {
            victim = i;
        }
    }
    *evicted = 1;
    return (int)victim;
}

void cra_state_init(void) {
    _clear_slots();
    _clear_route_slots();
    _clear_memory_slots();
    _clear_pending();
    cra_state_schedule_init();
    cra_lifecycle_reset();
    (void)cra_temporal_init();
    _clear_summary(0);
}

void cra_state_reset(void) {
    uint32_t reset_count = g_summary.state_resets + 1;
    _clear_slots();
    _clear_route_slots();
    _clear_memory_slots();
    _clear_pending();
    cra_state_schedule_init();
    cra_lifecycle_reset();
    cra_temporal_reset();
    g_learning_rate = 0;
    _clear_summary(reset_count);
}

int cra_state_write_context(uint32_t key, int32_t value, int32_t confidence, uint32_t timestep) {
    int idx = _find_slot(key);
    uint32_t evicted = 0;
    if (idx < 0) {
        idx = _select_slot_for_write(&evicted);
    }
    if (idx < 0) {
        return -1;
    }

    if (!g_context_slots[idx].active) {
        g_summary.active_slots++;
    } else if (evicted) {
        g_summary.slot_evictions++;
    }

    g_context_slots[idx].key = key;
    g_context_slots[idx].value = value;
    g_context_slots[idx].confidence = confidence;
    g_context_slots[idx].last_update = timestep;
    g_context_slots[idx].active = 1;
    g_summary.slot_writes++;
    return 0;
}

int cra_state_read_context(uint32_t key, int32_t *value_out, int32_t *confidence_out) {
    int idx = _find_slot(key);
    if (idx < 0) {
        g_summary.slot_misses++;
        return -1;
    }
    if (value_out != 0) {
        *value_out = g_context_slots[idx].value;
    }
    if (confidence_out != 0) {
        *confidence_out = g_context_slots[idx].confidence;
    }
    g_summary.slot_hits++;
    return 0;
}

uint32_t cra_state_active_slot_count(void) {
    return g_summary.active_slots;
}

int cra_state_write_route(int32_t value, int32_t confidence, uint32_t timestep) {
    (void)timestep;
    g_summary.route_value = value;
    g_summary.route_confidence = confidence;
    g_summary.route_writes++;
    return 0;
}

int cra_state_read_route(int32_t *value_out, int32_t *confidence_out) {
    if (value_out != 0) {
        *value_out = g_summary.route_value;
    }
    if (confidence_out != 0) {
        *confidence_out = g_summary.route_confidence;
    }
    g_summary.route_reads++;
    return 0;
}

int cra_state_write_route_slot(uint32_t key, int32_t value, int32_t confidence, uint32_t timestep) {
    int idx = _find_route_slot(key);
    uint32_t evicted = 0;
    if (idx < 0) {
        idx = _select_route_slot_for_write(&evicted);
    }
    if (idx < 0) {
        return -1;
    }

    if (!g_route_slots[idx].active) {
        g_summary.active_route_slots++;
    } else if (evicted) {
        g_summary.route_slot_evictions++;
    }

    g_route_slots[idx].key = key;
    g_route_slots[idx].value = value;
    g_route_slots[idx].confidence = confidence;
    g_route_slots[idx].last_update = timestep;
    g_route_slots[idx].active = 1;
    g_summary.route_slot_writes++;
    return 0;
}

int cra_state_read_route_slot(uint32_t key, int32_t *value_out, int32_t *confidence_out) {
    int idx = _find_route_slot(key);
    if (idx < 0) {
        g_summary.route_slot_misses++;
        return -1;
    }
    if (value_out != 0) {
        *value_out = g_route_slots[idx].value;
    }
    if (confidence_out != 0) {
        *confidence_out = g_route_slots[idx].confidence;
    }
    g_summary.route_slot_hits++;
    return 0;
}

uint32_t cra_state_active_route_slot_count(void) {
    return g_summary.active_route_slots;
}

int cra_state_write_memory_slot(uint32_t key, int32_t value, int32_t confidence, uint32_t timestep) {
    int idx = _find_memory_slot(key);
    uint32_t evicted = 0;
    if (idx < 0) {
        idx = _select_memory_slot_for_write(&evicted);
    }
    if (idx < 0) {
        return -1;
    }

    if (!g_memory_slots[idx].active) {
        g_summary.active_memory_slots++;
    } else if (evicted) {
        g_summary.memory_slot_evictions++;
    }

    g_memory_slots[idx].key = key;
    g_memory_slots[idx].value = value;
    g_memory_slots[idx].confidence = confidence;
    g_memory_slots[idx].last_update = timestep;
    g_memory_slots[idx].active = 1;
    g_summary.memory_slot_writes++;
    return 0;
}

int cra_state_read_memory_slot(uint32_t key, int32_t *value_out, int32_t *confidence_out) {
    int idx = _find_memory_slot(key);
    if (idx < 0) {
        g_summary.memory_slot_misses++;
        return -1;
    }
    if (value_out != 0) {
        *value_out = g_memory_slots[idx].value;
    }
    if (confidence_out != 0) {
        *confidence_out = g_memory_slots[idx].confidence;
    }
    g_summary.memory_slot_hits++;
    return 0;
}

uint32_t cra_state_active_memory_slot_count(void) {
    return g_summary.active_memory_slots;
}

void cra_state_set_readout(int32_t weight, int32_t bias) {
    g_summary.readout_weight = weight;
    g_summary.readout_bias = bias;
}

int32_t cra_state_predict_readout(int32_t feature) {
    return FP_MUL(g_summary.readout_weight, feature) + g_summary.readout_bias;
}

void cra_state_record_decision(int32_t feature, int32_t prediction) {
    g_summary.decisions++;
    g_summary.last_feature = feature;
    g_summary.last_prediction = prediction;
}

void cra_state_record_reward(int32_t reward) {
    g_summary.reward_events++;
    g_summary.last_reward = reward;
}

int32_t cra_state_apply_reward_to_readout(int32_t reward, int32_t learning_rate) {
    int32_t error = reward - g_summary.last_prediction;
    int32_t delta_w = FP_MUL(learning_rate, FP_MUL(error, g_summary.last_feature));
    int32_t delta_b = FP_MUL(learning_rate, error);
    g_summary.readout_weight += delta_w;
    g_summary.readout_bias += delta_b;
    cra_state_record_reward(reward);
    return delta_w;
}

static int32_t _apply_reward_to_feature_prediction(
    int32_t feature,
    int32_t prediction,
    int32_t target,
    int32_t learning_rate
) {
    int32_t error = target - prediction;
    int32_t surprise = error < 0 ? -error : error;
    if (surprise < SURPRISE_THRESHOLD) {
        int32_t delta_w = FP_MUL(learning_rate, FP_MUL(error, feature));
        int32_t delta_b = FP_MUL(learning_rate, error);
        g_summary.readout_weight += delta_w;
        g_summary.readout_bias += delta_b;
    }
    g_summary.reward_events++;
    g_summary.last_feature = feature;
    g_summary.last_prediction = prediction;
    g_summary.last_reward = target;
    return error;
}

int cra_state_schedule_pending_horizon(
    int32_t feature,
    int32_t prediction,
    uint32_t due_timestep
) {
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        if (!g_pending_horizons[i].active) {
            g_pending_horizons[i].due_timestep = due_timestep;
            g_pending_horizons[i].feature = feature;
            g_pending_horizons[i].prediction = prediction;
            g_pending_horizons[i].active = 1;
            g_summary.pending_created++;
            g_summary.active_pending++;
            return 0;
        }
    }
    g_summary.pending_dropped++;
    return -1;
}

uint32_t cra_state_mature_pending_horizons(uint32_t timestep, int32_t target, int32_t learning_rate) {
    uint32_t matured = 0;
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        if (g_pending_horizons[i].active && g_pending_horizons[i].due_timestep <= timestep) {
            int32_t effective_lr = learning_rate;
            if (g_pending_horizons[i].has_confidence) {
                effective_lr = FP_MUL(learning_rate, g_pending_horizons[i].composite_confidence);
            }
            _apply_reward_to_feature_prediction(
                g_pending_horizons[i].feature,
                g_pending_horizons[i].prediction,
                target,
                effective_lr
            );
            g_pending_horizons[i].active = 0;
            g_pending_horizons[i].has_confidence = 0;
            if (g_summary.active_pending > 0) {
                g_summary.active_pending--;
            }
            g_summary.pending_matured++;
            matured++;
        }
    }
    return matured;
}

uint32_t cra_state_active_pending_count(void) {
    return g_summary.active_pending;
}

void cra_state_schedule_init(void) {
    g_schedule_count = 0;
    g_schedule_index = 0;
    g_schedule_base_timestep = 0;
    g_continuous_mode = 0;
    for (uint32_t i = 0; i < MAX_SCHEDULE_ENTRIES; i++) {
        g_schedule[i].timestep = 0;
        g_schedule[i].context_key = 0;
        g_schedule[i].route_key = 0;
        g_schedule[i].memory_key = 0;
        g_schedule[i].cue = 0;
        g_schedule[i].target = 0;
        g_schedule[i].delay = 0;
    }
}

int cra_state_write_schedule_entry(uint32_t index, const schedule_entry_t *entry) {
    if (index >= MAX_SCHEDULE_ENTRIES || entry == 0) {
        return -1;
    }
    g_schedule[index] = *entry;
    if (index >= g_schedule_count) {
        g_schedule_count = index + 1;
    }
    return 0;
}

uint32_t cra_state_schedule_entry_count(void) { return g_schedule_count; }
void cra_state_set_schedule_count(uint32_t count) { g_schedule_count = count; }
uint8_t cra_state_continuous_mode(void) { return g_continuous_mode; }
void cra_state_set_continuous_mode(uint8_t mode) {
    g_continuous_mode = mode;
    if (mode) {
        g_schedule_base_timestep = g_timestep;
    }
}
void cra_state_set_learning_rate(int32_t lr_raw) { g_learning_rate = lr_raw; }

int cra_state_schedule_pending_horizon_with_target(
    int32_t feature,
    int32_t prediction,
    int32_t target,
    uint32_t due_timestep
) {
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        if (!g_pending_horizons[i].active) {
            g_pending_horizons[i].due_timestep = due_timestep;
            g_pending_horizons[i].feature = feature;
            g_pending_horizons[i].prediction = prediction;
            g_pending_horizons[i].target = target;
            g_pending_horizons[i].composite_confidence = 0;
            g_pending_horizons[i].active = 1;
            g_pending_horizons[i].has_confidence = 0;
            g_summary.pending_created++;
            g_summary.active_pending++;
            return 0;
        }
    }
    g_summary.pending_dropped++;
    return -1;
}

int cra_state_schedule_pending_horizon_with_target_and_confidence(
    int32_t feature,
    int32_t prediction,
    int32_t target,
    uint32_t due_timestep,
    int32_t composite_confidence
) {
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        if (!g_pending_horizons[i].active) {
            g_pending_horizons[i].due_timestep = due_timestep;
            g_pending_horizons[i].feature = feature;
            g_pending_horizons[i].prediction = prediction;
            g_pending_horizons[i].target = target;
            g_pending_horizons[i].composite_confidence = composite_confidence;
            g_pending_horizons[i].active = 1;
            g_pending_horizons[i].has_confidence = 1;
            g_summary.pending_created++;
            g_summary.active_pending++;
            return 0;
        }
    }
    g_summary.pending_dropped++;
    return -1;
}

uint32_t cra_state_mature_oldest_pending(uint32_t timestep, int32_t learning_rate) {
    // Find the active pending with the smallest due_timestep that is <= timestep
    int oldest_idx = -1;
    uint32_t oldest_due = 0xFFFFFFFF;
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        if (g_pending_horizons[i].active && g_pending_horizons[i].due_timestep <= timestep) {
            if (g_pending_horizons[i].due_timestep < oldest_due) {
                oldest_due = g_pending_horizons[i].due_timestep;
                oldest_idx = (int)i;
            }
        }
    }
    if (oldest_idx < 0) {
        return 0;
    }
    pending_horizon_t *ph = &g_pending_horizons[oldest_idx];
    int32_t effective_lr = learning_rate;
    if (ph->has_confidence) {
        effective_lr = FP_MUL(learning_rate, ph->composite_confidence);
    }
    _apply_reward_to_feature_prediction(
        ph->feature,
        ph->prediction,
        ph->target,
        effective_lr
    );
    ph->active = 0;
    ph->has_confidence = 0;
    if (g_summary.active_pending > 0) {
        g_summary.active_pending--;
    }
    g_summary.pending_matured++;
    return 1;
}

// ------------------------------------------------------------------
// 4.25B inter-core SDP send (state core → learning core)
// ------------------------------------------------------------------
#ifdef CRA_RUNTIME_PROFILE_STATE_CORE
static uint16_t g_chip_addr = 0;

static void _send_schedule_pending_split(int32_t feature, int32_t prediction, int32_t target, uint32_t due_timestep) {
    sdp_msg_t *msg = (sdp_msg_t *) spin1_msg_get();
    if (msg == NULL) return;
    // Same chip, Core 5 (learning core), port 1
    msg->dest_addr = g_chip_addr;
    msg->srce_addr = g_chip_addr;
    msg->dest_port = (1 << 5) | 5;
    msg->srce_port = (uint8_t)((sark_core_id() << 5) | 1);
    msg->flags = 0;
    msg->tag = 0;
    msg->cmd_rc = CMD_SCHEDULE_PENDING_SPLIT;
    msg->arg1 = (uint32_t)feature;
    msg->arg2 = (uint32_t)prediction;
    msg->arg3 = due_timestep;
    msg->data[0] = (uint8_t)(target & 0xFF);
    msg->data[1] = (uint8_t)((target >> 8) & 0xFF);
    msg->data[2] = (uint8_t)((target >> 16) & 0xFF);
    msg->data[3] = (uint8_t)((target >> 24) & 0xFF);
    msg->length = sizeof(sdp_msg_t) - 256 + 4;  // header + 4 bytes data
    spin1_send_sdp_msg(msg, 1);
    spin1_msg_free(msg);
}

void cra_state_capture_chip_addr(uint16_t chip_addr) {
    if (g_chip_addr == 0) {
        g_chip_addr = chip_addr;
    }
}
#endif

#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
static void _send_lookup_request(uint32_t seq_id, uint32_t key, uint8_t type, uint8_t dest_cpu);
#endif

uint32_t cra_state_process_continuous_tick(uint32_t timestep) {
#ifdef CRA_RUNTIME_PROFILE_STATE_CORE
    // State core: check schedule, compute feature, send SDP to learning core
    if (g_schedule_index < g_schedule_count) {
        schedule_entry_t *entry = &g_schedule[g_schedule_index];
        if (entry->timestep + g_schedule_base_timestep == timestep) {
            int32_t ctx_val = 0, ctx_conf = 0;
            int32_t route_val = 0, route_conf = 0;
            int32_t mem_val = 0, mem_conf = 0;

            cra_state_read_context(entry->context_key, &ctx_val, &ctx_conf);
            cra_state_read_route_slot(entry->route_key, &route_val, &route_conf);
            cra_state_read_memory_slot(entry->memory_key, &mem_val, &mem_conf);

            int32_t feature = FP_MUL(FP_MUL(FP_MUL(ctx_val, route_val), mem_val), entry->cue);
            int32_t prediction = cra_state_predict_readout(feature);

            cra_state_record_decision(feature, prediction);
            _send_schedule_pending_split(feature, prediction, entry->target, timestep + entry->delay);
            g_schedule_index++;
        }
    }
    // State core does NOT mature pending locally
    // Auto-pause when schedule exhausted
    if (g_schedule_index >= g_schedule_count) {
        g_continuous_mode = 0;
    }
    return 0;
#elif CRA_RUNTIME_PROFILE_LEARNING_CORE
    // 4.26 learning core: schedule-driven parallel lookups + feature composition.
    // Sends 3 lookups per event; waits for replies; composes feature; schedules pending.
    // Transitional SDP inter-core messaging. Target architecture is multicast/MCPL.
    uint32_t matured = 0;

    static uint32_t s_event_seq[3];
    static int32_t  s_event_cue;
    static int32_t  s_event_target;
    static uint32_t s_event_delay;
    static uint32_t s_event_base_timestep;
    static uint8_t  s_event_active = 0;
    static uint32_t s_lookup_next_seq = 1;

    // Phase B: If current event lookups are complete, compose and schedule.
    if (s_event_active) {
        if (cra_state_lookup_is_received(s_event_seq[0]) &&
            cra_state_lookup_is_received(s_event_seq[1]) &&
            cra_state_lookup_is_received(s_event_seq[2])) {

            int32_t ctx_val = 0, route_val = 0, mem_val = 0;
            int32_t ctx_conf = 0, route_conf = 0, mem_conf = 0;
            uint8_t hit;

            cra_state_lookup_get_result(s_event_seq[0], &ctx_val, &ctx_conf, &hit);
            cra_state_lookup_get_result(s_event_seq[1], &route_val, &route_conf, &hit);
            cra_state_lookup_get_result(s_event_seq[2], &mem_val, &mem_conf, &hit);

            int32_t feature = FP_MUL(FP_MUL(FP_MUL(ctx_val, route_val), mem_val), s_event_cue);
            int32_t prediction = cra_state_predict_readout(feature);
            int32_t composite_confidence = FP_MUL(FP_MUL(ctx_conf, route_conf), mem_conf);

            cra_state_record_decision(feature, prediction);
            cra_state_schedule_pending_horizon_with_target_and_confidence(
                feature, prediction, s_event_target,
                s_event_base_timestep + s_event_delay,
                composite_confidence);

            /* Clear lookup entries to free table slots for next event */
            cra_state_lookup_clear(s_event_seq[0]);
            cra_state_lookup_clear(s_event_seq[1]);
            cra_state_lookup_clear(s_event_seq[2]);

            s_event_active = 0;
        }
    }

    // Phase A: If no active event and schedule entry is due, send lookups.
    if (!s_event_active && g_schedule_index < g_schedule_count) {
        schedule_entry_t *entry = &g_schedule[g_schedule_index];
        if (entry->timestep + g_schedule_base_timestep == timestep) {
            s_event_seq[0] = s_lookup_next_seq++;
            s_event_seq[1] = s_lookup_next_seq++;
            s_event_seq[2] = s_lookup_next_seq++;

            cra_state_lookup_send(s_event_seq[0], entry->context_key, LOOKUP_TYPE_CONTEXT, timestep);
            _send_lookup_request(s_event_seq[0], entry->context_key, LOOKUP_TYPE_CONTEXT, 4);
            cra_state_lookup_send(s_event_seq[1], entry->route_key, LOOKUP_TYPE_ROUTE, timestep);
            _send_lookup_request(s_event_seq[1], entry->route_key, LOOKUP_TYPE_ROUTE, 5);
            cra_state_lookup_send(s_event_seq[2], entry->memory_key, LOOKUP_TYPE_MEMORY, timestep);
            _send_lookup_request(s_event_seq[2], entry->memory_key, LOOKUP_TYPE_MEMORY, 6);

            s_event_cue = entry->cue;
            s_event_target = entry->target;
            s_event_delay = entry->delay;
            s_event_base_timestep = timestep;
            s_event_active = 1;

            g_schedule_index++;
        }
    }

    // Phase C: Mature oldest pending if due.
    matured = cra_state_mature_oldest_pending(timestep, g_learning_rate);

    // Auto-pause when schedule exhausted, event complete, and pending drained.
    if (g_schedule_index >= g_schedule_count && !s_event_active && g_summary.active_pending == 0) {
        g_continuous_mode = 0;
    }

    return matured;
#elif CRA_RUNTIME_PROFILE_CONTEXT_CORE || CRA_RUNTIME_PROFILE_ROUTE_CORE || CRA_RUNTIME_PROFILE_MEMORY_CORE
    // 4.26 state-server cores: no schedule or pending. Host reads state directly.
    (void)timestep;
    return 0;
#else
    // Monolithic decoupled_memory_route: original behavior
    uint32_t matured = 0;

    // 1. Process next schedule entry if due
    if (g_schedule_index < g_schedule_count) {
        schedule_entry_t *entry = &g_schedule[g_schedule_index];
        if (entry->timestep + g_schedule_base_timestep == timestep) {
            int32_t ctx_val = 0, ctx_conf = 0;
            int32_t route_val = 0, route_conf = 0;
            int32_t mem_val = 0, mem_conf = 0;

            cra_state_read_context(entry->context_key, &ctx_val, &ctx_conf);
            cra_state_read_route_slot(entry->route_key, &route_val, &route_conf);
            cra_state_read_memory_slot(entry->memory_key, &mem_val, &mem_conf);

            int32_t feature = FP_MUL(FP_MUL(FP_MUL(ctx_val, route_val), mem_val), entry->cue);
            int32_t prediction = cra_state_predict_readout(feature);

            cra_state_record_decision(feature, prediction);
            cra_state_schedule_pending_horizon_with_target(
                feature, prediction, entry->target, timestep + entry->delay);

            g_schedule_index++;
        }
    }

    // 2. Mature oldest pending if due
    matured = cra_state_mature_oldest_pending(timestep, g_learning_rate);

    // 3. Auto-pause when schedule exhausted and pending drained
    if (g_schedule_index >= g_schedule_count && g_summary.active_pending == 0) {
        g_continuous_mode = 0;
    }

    return matured;
#endif
}

// ------------------------------------------------------------------
// 4.26 inter-core lookup protocol (transitional SDP; target is multicast/MCPL)
// ------------------------------------------------------------------

#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
static lookup_entry_t g_lookup_entries[MAX_LOOKUP_REPLIES];

void cra_state_lookup_init(void) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        g_lookup_entries[i].seq_id = 0;
        g_lookup_entries[i].received = 0;
        g_lookup_entries[i].value_received = 0;
        g_lookup_entries[i].meta_received = 0;
    }
}

#ifndef CRA_USE_MCPL_LOOKUP
static uint16_t g_learning_chip_addr = 0;
#endif

static void _send_lookup_request(uint32_t seq_id, uint32_t key, uint8_t type, uint8_t dest_cpu) {
    // SDP stays available as a transitional fallback. CRA_USE_MCPL_LOOKUP
    // selects the confidence-bearing MCPL path repaired in Tier 4.32a-r1.
#ifdef CRA_USE_MCPL_LOOKUP
    cra_state_mcpl_lookup_send_request(seq_id, key, type, dest_cpu);
    g_summary.lookup_requests_sent++;
#else
    sdp_msg_t *msg = (sdp_msg_t *) spin1_msg_get();
    if (msg == NULL) return;
    if (g_learning_chip_addr == 0) {
        g_learning_chip_addr = (uint16_t) sark_chip_id();
    }
    msg->dest_addr = g_learning_chip_addr;
    msg->srce_addr = g_learning_chip_addr;
    msg->dest_port = (1 << 5) | dest_cpu;
    msg->srce_port = (uint8_t)((sark_core_id() << 5) | 1);
    msg->flags = 0;
    msg->tag = 0;
    msg->cmd_rc = CMD_LOOKUP_REQUEST;
    msg->arg1 = seq_id;
    msg->arg2 = key;
    msg->arg3 = (uint32_t)type;
    msg->length = sizeof(sdp_msg_t) - 256;  /* header only, no data payload */
    g_summary.lookup_requests_sent++;
    spin1_send_sdp_msg(msg, 1);
    spin1_msg_free(msg);
#endif
}

int cra_state_lookup_send_shard(uint32_t seq_id, uint32_t key, uint8_t type, uint8_t shard_id, uint32_t timestamp) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == 0) {
            g_lookup_entries[i].seq_id = seq_id;
            g_lookup_entries[i].key = key;
            g_lookup_entries[i].type = type;
            g_lookup_entries[i].shard_id = shard_id & MCPL_KEY_SHARD_MASK;
            g_lookup_entries[i].received = 0;
            g_lookup_entries[i].value_received = 0;
            g_lookup_entries[i].meta_received = 0;
            g_lookup_entries[i].hit = 0;
            g_lookup_entries[i].status = 0;
            g_lookup_entries[i].value = 0;
            g_lookup_entries[i].confidence = 0;
            g_lookup_entries[i].timestamp = timestamp;
            return 0;
        }
    }
    return -1; /* table full */
}

int cra_state_lookup_send(uint32_t seq_id, uint32_t key, uint8_t type, uint32_t timestamp) {
    return cra_state_lookup_send_shard(seq_id, key, type, CRA_MCPL_SHARD_ID, timestamp);
}

int cra_state_lookup_receive(uint32_t seq_id, int32_t value, int32_t confidence, uint8_t hit) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id && !g_lookup_entries[i].received) {
            g_lookup_entries[i].value = value;
            g_lookup_entries[i].confidence = confidence;
            g_lookup_entries[i].hit = hit;
            g_lookup_entries[i].status = 0;
            g_lookup_entries[i].value_received = 1;
            g_lookup_entries[i].meta_received = 1;
            g_lookup_entries[i].received = 1;
            g_summary.lookup_replies_received++;
            return 0;
        }
    }
    /* Distinguish stale (seq_id never seen) from duplicate (already received) */
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id) {
            g_summary.lookup_duplicate_replies++;
            return -1; /* duplicate reply */
        }
    }
    g_summary.lookup_stale_replies++;
    return -1; /* stale reply: seq_id not in pending list */
}

static lookup_entry_t *_lookup_find_shard(uint32_t seq_id, uint8_t type, uint8_t shard_id) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id &&
            g_lookup_entries[i].type == type &&
            g_lookup_entries[i].shard_id == (shard_id & MCPL_KEY_SHARD_MASK)) {
            return &g_lookup_entries[i];
        }
    }
    return 0;
}

static int _lookup_receive_mcpl_value(uint32_t seq_id, uint8_t type, uint8_t shard_id, int32_t value) {
    lookup_entry_t *entry = _lookup_find_shard(seq_id, type, shard_id);
    if (entry == 0) {
        g_summary.lookup_stale_replies++;
        return -1;
    }
    if (entry->received || entry->value_received) {
        g_summary.lookup_duplicate_replies++;
        return -1;
    }
    entry->value = value;
    entry->value_received = 1;
    if (entry->meta_received) {
        entry->received = 1;
        g_summary.lookup_replies_received++;
    }
    return 0;
}

static int _lookup_receive_mcpl_meta(uint32_t seq_id, uint8_t type, uint8_t shard_id, int32_t confidence, uint8_t hit, uint8_t status) {
    lookup_entry_t *entry = _lookup_find_shard(seq_id, type, shard_id);
    if (entry == 0) {
        g_summary.lookup_stale_replies++;
        return -1;
    }
    if (entry->received || entry->meta_received) {
        g_summary.lookup_duplicate_replies++;
        return -1;
    }
    entry->confidence = confidence;
    entry->hit = hit;
    entry->status = status;
    entry->meta_received = 1;
    if (entry->value_received) {
        entry->received = 1;
        g_summary.lookup_replies_received++;
    }
    return 0;
}

uint8_t cra_state_lookup_is_received_shard(uint32_t seq_id, uint8_t type, uint8_t shard_id) {
    lookup_entry_t *entry = _lookup_find_shard(seq_id, type, shard_id);
    return entry ? entry->received : 0;
}

uint8_t cra_state_lookup_is_received(uint32_t seq_id) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id) {
            return g_lookup_entries[i].received;
        }
    }
    return 0;
}

uint8_t cra_state_lookup_is_stale(uint32_t seq_id) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id) {
            return 0; /* found = not stale */
        }
    }
    return 1; /* not found = stale */
}

uint32_t cra_state_lookup_check_timeout(uint32_t timestamp, uint32_t *seq_ids_out, uint32_t max_out) {
    uint32_t count = 0;
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id != 0 && !g_lookup_entries[i].received) {
            if (timestamp - g_lookup_entries[i].timestamp > 10) {
                if (count < max_out) {
                    seq_ids_out[count++] = g_lookup_entries[i].seq_id;
                }
                g_summary.lookup_timeouts++;
            }
        }
    }
    return count;
}

int cra_state_lookup_get_result_shard(uint32_t seq_id, uint8_t type, uint8_t shard_id, int32_t *value_out, int32_t *confidence_out, uint8_t *hit_out) {
    lookup_entry_t *entry = _lookup_find_shard(seq_id, type, shard_id);
    if (entry != 0 && entry->received) {
        if (value_out) *value_out = entry->value;
        if (confidence_out) *confidence_out = entry->confidence;
        if (hit_out) *hit_out = entry->hit;
        return 0;
    }
    return -1;
}

int cra_state_lookup_get_result(uint32_t seq_id, int32_t *value_out, int32_t *confidence_out, uint8_t *hit_out) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id && g_lookup_entries[i].received) {
            if (value_out) *value_out = g_lookup_entries[i].value;
            if (confidence_out) *confidence_out = g_lookup_entries[i].confidence;
            if (hit_out) *hit_out = g_lookup_entries[i].hit;
            return 0;
        }
    }
    return -1;
}

void cra_state_lookup_clear(uint32_t seq_id) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id) {
            g_lookup_entries[i].seq_id = 0;
            g_lookup_entries[i].received = 0;
            g_lookup_entries[i].value_received = 0;
            g_lookup_entries[i].meta_received = 0;
            return;
        }
    }
}

uint32_t cra_state_lookup_list_pending(uint32_t *seq_ids_out, uint32_t max_out) {
    uint32_t count = 0;
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id != 0 && !g_lookup_entries[i].received) {
            if (seq_ids_out && count < max_out) {
                seq_ids_out[count] = g_lookup_entries[i].seq_id;
            }
            count++;
        }
    }
    return count;
}

int cra_state_lookup_get_pending_info(uint32_t seq_id, uint32_t *key_out, uint8_t *type_out) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id && !g_lookup_entries[i].received) {
            if (key_out) *key_out = g_lookup_entries[i].key;
            if (type_out) *type_out = g_lookup_entries[i].type;
            return 0;
        }
    }
    return -1;
}
#endif

#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
static uint16_t g_chip_addr = 0;

void cra_state_capture_chip_addr(uint16_t chip_addr) {
    if (g_chip_addr == 0) {
        g_chip_addr = chip_addr;
    }
}

static void _send_lookup_reply(uint32_t seq_id, int32_t value, int32_t confidence, uint8_t hit, uint8_t status) {
    // SDP stays available as a transitional fallback. CRA_USE_MCPL_LOOKUP
    // selects the confidence-bearing MCPL path repaired in Tier 4.32a-r1.
#ifdef CRA_USE_MCPL_LOOKUP
    cra_state_mcpl_lookup_send_reply_shard(seq_id, value, confidence, hit, status,
        /* lookup_type inferred from profile at compile time */
#ifdef CRA_RUNTIME_PROFILE_CONTEXT_CORE
        LOOKUP_TYPE_CONTEXT,
#elif defined(CRA_RUNTIME_PROFILE_ROUTE_CORE)
        LOOKUP_TYPE_ROUTE,
#elif defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
        LOOKUP_TYPE_MEMORY,
#else
        0,
#endif
        CRA_MCPL_SHARD_ID,
        7);  // dest_core = learning core
#else
    sdp_msg_t *msg = (sdp_msg_t *) spin1_msg_get();
    if (msg == NULL) return;
    msg->dest_addr = g_chip_addr;
    msg->srce_addr = g_chip_addr;
    msg->dest_port = (1 << 5) | 7; /* port 1, CPU 7 (learning core) */
    msg->srce_port = (uint8_t)((sark_core_id() << 5) | 1);
    msg->flags = 0;
    msg->tag = 0;
    msg->cmd_rc = CMD_LOOKUP_REPLY;
    msg->arg1 = seq_id;
    msg->arg2 = (uint32_t)value;
    msg->arg3 = (uint32_t)confidence;
    msg->data[0] = hit;
    msg->data[1] = status;
    msg->length = sizeof(sdp_msg_t) - 256 + 2;
    spin1_send_sdp_msg(msg, 1);
    spin1_msg_free(msg);
#endif
}

void cra_state_handle_lookup_request(uint32_t seq_id, uint32_t key, uint8_t type) {
    int32_t value = 0;
    int32_t confidence = 0;
    uint8_t hit = 0;
    uint8_t status = 0;

#ifdef CRA_RUNTIME_PROFILE_CONTEXT_CORE
    if (type == LOOKUP_TYPE_CONTEXT) {
        int rc = cra_state_read_context(key, &value, &confidence);
        hit = (rc == 0) ? 1 : 0;
    } else
#endif
#ifdef CRA_RUNTIME_PROFILE_ROUTE_CORE
    if (type == LOOKUP_TYPE_ROUTE) {
        int rc = cra_state_read_route_slot(key, &value, &confidence);
        hit = (rc == 0) ? 1 : 0;
    } else
#endif
#ifdef CRA_RUNTIME_PROFILE_MEMORY_CORE
    if (type == LOOKUP_TYPE_MEMORY) {
        int rc = cra_state_read_memory_slot(key, &value, &confidence);
        hit = (rc == 0) ? 1 : 0;
    } else
#endif
    {
        status = 1; /* wrong lookup type for this profile */
    }

    _send_lookup_reply(seq_id, value, confidence, hit, status);
}
#endif

// ------------------------------------------------------------------
// 4.32a-r1 MCPL inter-core lookup repair
//
// These functions use the official spin1_api MCPL symbols.
// Tier 4.32a-r1 carries value plus confidence/hit/status over MCPL
// and includes shard_id in the key to avoid replicated-shard cross-talk.
// ------------------------------------------------------------------

#ifndef CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE
#define CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE 0
#endif

#ifndef CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE
#define CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE 0
#endif

#ifndef CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE
#define CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE 0
#endif

#ifndef CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE
#define CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE 0
#endif

static void _mcpl_install_route(uint32_t key, uint32_t mask, uint route) {
    uint entry = rtr_alloc(1);
    if (entry == 0) {
        return;
    }
    (void)rtr_mc_set(entry, key, mask, route);
}

void cra_state_mcpl_lookup_send_request(uint32_t seq_id, uint32_t key_id, uint8_t lookup_type, uint8_t dest_core) {
    cra_state_mcpl_lookup_send_request_shard(seq_id, key_id, lookup_type, CRA_MCPL_SHARD_ID, dest_core);
}

void cra_state_mcpl_lookup_send_request_shard(uint32_t seq_id, uint32_t key_id, uint8_t lookup_type, uint8_t shard_id, uint8_t dest_core) {
    (void)dest_core;  // routing table decides delivery by key/mask
    uint32_t key = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REQUEST, lookup_type, shard_id, seq_id);
    spin1_send_mc_packet(key, key_id, WITH_PAYLOAD);
}

void cra_state_mcpl_lookup_send_reply(uint32_t seq_id, int32_t value, int32_t confidence, uint8_t hit, uint8_t lookup_type, uint8_t dest_core) {
    cra_state_mcpl_lookup_send_reply_shard(seq_id, value, confidence, hit, 0, lookup_type, CRA_MCPL_SHARD_ID, dest_core);
}

void cra_state_mcpl_lookup_send_reply_shard(uint32_t seq_id, int32_t value, int32_t confidence, uint8_t hit, uint8_t status, uint8_t lookup_type, uint8_t shard_id, uint8_t dest_core) {
    (void)dest_core;  // routing table decides delivery by key/mask
    uint32_t value_key = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, lookup_type, shard_id, seq_id);
    uint32_t meta_key = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, lookup_type, shard_id, seq_id);
    spin1_send_mc_packet(value_key, (uint32_t)value, WITH_PAYLOAD);
    spin1_send_mc_packet(meta_key, PACK_MCPL_LOOKUP_META(confidence, hit, status), WITH_PAYLOAD);
}

void cra_state_mcpl_lookup_receive(uint32_t key, uint32_t payload) {
    uint8_t msg_type = EXTRACT_MCPL_MSG_TYPE(key);
    uint32_t seq_id = EXTRACT_MCPL_SEQ_ID(key);
    uint8_t lookup_type = EXTRACT_MCPL_LOOKUP_TYPE(key);
    uint8_t shard_id = EXTRACT_MCPL_SHARD_ID(key);
    (void)msg_type;
    (void)seq_id;
    (void)lookup_type;
    (void)shard_id;

#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
    if (msg_type == MCPL_MSG_LOOKUP_REPLY_VALUE) {
        // Learning core receives reply
        int32_t value = (int32_t)payload;
        (void)_lookup_receive_mcpl_value(seq_id, lookup_type, shard_id, value);
    } else if (msg_type == MCPL_MSG_LOOKUP_REPLY_META) {
        int32_t confidence = EXTRACT_MCPL_LOOKUP_META_CONF(payload);
        uint8_t hit = (uint8_t)EXTRACT_MCPL_LOOKUP_META_HIT(payload);
        uint8_t status = (uint8_t)EXTRACT_MCPL_LOOKUP_META_STATUS(payload);
        (void)_lookup_receive_mcpl_meta(seq_id, lookup_type, shard_id, confidence, hit, status);
    }
#endif
#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
    if (msg_type == MCPL_MSG_LOOKUP_REQUEST) {
        if (shard_id != (CRA_MCPL_SHARD_ID & MCPL_KEY_SHARD_MASK)) {
            return;
        }
        // State core receives request
        cra_state_handle_lookup_request(seq_id, payload, lookup_type);
    }
#endif
}

void cra_state_mcpl_init(uint8_t core_id) {
#ifdef CRA_USE_MCPL_LOOKUP
#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
    // State core: route REQUEST keys to this core
    uint8_t lookup_type =
#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE)
        LOOKUP_TYPE_CONTEXT;
#elif defined(CRA_RUNTIME_PROFILE_ROUTE_CORE)
        LOOKUP_TYPE_ROUTE;
#elif defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
        LOOKUP_TYPE_MEMORY;
#else
        0;
#endif
    uint32_t key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, lookup_type, 0);
    uint32_t mask = 0xFFFFF000;  // match app/msg/lookup/shard, ignore seq_id
    uint route = MC_CORE_ROUTE(core_id);
    _mcpl_install_route(key, mask, route);
#if CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE
    // Remote state-chip path: replies are routed back over an explicit chip
    // link. The route is specific to this state profile's lookup type so
    // context/route/memory cores do not install duplicate broad reply routes.
    uint reply_route = CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE;
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, lookup_type, 0);
    _mcpl_install_route(key, mask, reply_route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, lookup_type, 0);
    _mcpl_install_route(key, mask, reply_route);
#endif
#elif defined(CRA_RUNTIME_PROFILE_LEARNING_CORE)
    // Learning core: route VALUE and META reply keys to this core.
    // Match app/msg/shard, ignore lookup_type and seq_id.
    uint32_t key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, 0, 0);
    uint32_t mask = 0xFFF0F000;
    uint route = MC_CORE_ROUTE(core_id);
    _mcpl_install_route(key, mask, route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, 0, 0);
    _mcpl_install_route(key, mask, route);
#if CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE
    // Source-chip path: lookup requests leave the learning chip over an
    // explicit chip link. Destination state chips install matching local-core
    // routes for the same request keys.
    uint request_route = CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE;
    mask = 0xFFFFF000;  // match app/msg/lookup/shard, ignore seq_id
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_CONTEXT, 0);
    _mcpl_install_route(key, mask, request_route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_ROUTE, 0);
    _mcpl_install_route(key, mask, request_route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_MEMORY, 0);
    _mcpl_install_route(key, mask, request_route);
#endif
    // Learning/consumer core: route lifecycle active-mask/lineage sync packets
    // to this core. Inter-chip lifecycle smoke uses this as the consumer-side
    // readback proof that a lifecycle core's mask sync crossed the chip link.
    mask = 0xFFF0F000;  // match app/msg/shard, ignore lifecycle subtype and seq
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0);
    _mcpl_install_route(key, mask, route);
#if CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE
    // Source-chip path for lifecycle traffic: event/trophic requests leave the
    // learning chip over an explicit chip link. Destination lifecycle cores
    // install matching local-core routes for the same message types.
    uint lifecycle_request_route = CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE;
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0);
    _mcpl_install_route(key, mask, lifecycle_request_route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0);
    _mcpl_install_route(key, mask, lifecycle_request_route);
#endif
#elif defined(CRA_RUNTIME_PROFILE_LIFECYCLE_CORE)
    // Lifecycle core: route lifecycle event/trophic requests to this core.
    uint32_t key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0);
    uint32_t mask = 0xFFF0F000;  // match app/msg/shard, ignore subtype and seq
    uint route = MC_CORE_ROUTE(core_id);
    _mcpl_install_route(key, mask, route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0);
    _mcpl_install_route(key, mask, route);
#if CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE
    // Lifecycle state-chip path: active-mask/lineage sync packets leave the
    // lifecycle chip over an explicit chip link back to learning/consumer cores.
    uint sync_route = CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE;
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0);
    _mcpl_install_route(key, mask, sync_route);
#endif
#else
    (void)core_id;
#endif
#else
    (void)core_id;
#endif  // CRA_USE_MCPL_LOOKUP
}

void cra_state_get_summary(cra_state_summary_t *summary_out) {
    if (summary_out == 0) {
        return;
    }
    *summary_out = g_summary;
}
