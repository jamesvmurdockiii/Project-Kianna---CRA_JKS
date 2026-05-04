/*!
 * \file state_manager.c
 * \brief Static persistent state owned by the custom C runtime.
 */
#include "state_manager.h"
#ifdef CRA_RUNTIME_PROFILE_STATE_CORE
#include <sark.h>
#include <spin1_api.h>
#endif

static context_slot_t g_context_slots[MAX_CONTEXT_SLOTS];
static route_slot_t g_route_slots[MAX_ROUTE_SLOTS];
static memory_slot_t g_memory_slots[MAX_MEMORY_SLOTS];
static pending_horizon_t g_pending_horizons[MAX_PENDING_HORIZONS];
static cra_state_summary_t g_summary;

static schedule_entry_t g_schedule[MAX_SCHEDULE_ENTRIES];
static uint32_t g_schedule_count = 0;
static uint32_t g_schedule_index = 0;
static uint32_t g_schedule_base_timestep = 0;
static uint8_t g_continuous_mode = 0;
static int32_t g_learning_rate = 0;

extern uint32_t g_timestep;

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
}

static void _clear_pending(void) {
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        g_pending_horizons[i].due_timestep = 0;
        g_pending_horizons[i].feature = 0;
        g_pending_horizons[i].prediction = 0;
        g_pending_horizons[i].target = 0;
        g_pending_horizons[i].active = 0;
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
    _clear_summary(0);
}

void cra_state_reset(void) {
    uint32_t reset_count = g_summary.state_resets + 1;
    _clear_slots();
    _clear_route_slots();
    _clear_memory_slots();
    _clear_pending();
    cra_state_schedule_init();
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
    int32_t delta_w = FP_MUL(learning_rate, FP_MUL(error, feature));
    int32_t delta_b = FP_MUL(learning_rate, error);
    g_summary.readout_weight += delta_w;
    g_summary.readout_bias += delta_b;
    g_summary.reward_events++;
    g_summary.last_feature = feature;
    g_summary.last_prediction = prediction;
    g_summary.last_reward = target;
    return delta_w;
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
            _apply_reward_to_feature_prediction(
                g_pending_horizons[i].feature,
                g_pending_horizons[i].prediction,
                target,
                learning_rate
            );
            g_pending_horizons[i].active = 0;
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
            g_pending_horizons[i].active = 1;
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
#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
    int32_t prediction = cra_state_predict_readout(ph->feature);
#else
    int32_t prediction = ph->prediction;
#endif
    _apply_reward_to_feature_prediction(
        ph->feature,
        prediction,
        ph->target,
        learning_rate
    );
    ph->active = 0;
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
    // Learning core: only mature pending (schedule entries arrive via SDP)
    uint32_t matured = cra_state_mature_oldest_pending(timestep, g_learning_rate);
    if (g_summary.active_pending == 0 && g_continuous_mode) {
        // Keep running until host pauses or all pending matured
    }
    return matured;
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

void cra_state_get_summary(cra_state_summary_t *summary_out) {
    if (summary_out == 0) {
        return;
    }
    *summary_out = g_summary;
}
