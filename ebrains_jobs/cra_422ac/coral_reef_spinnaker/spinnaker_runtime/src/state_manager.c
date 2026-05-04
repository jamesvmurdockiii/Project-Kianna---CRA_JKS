/*!
 * \file state_manager.c
 * \brief Static persistent state owned by the custom C runtime.
 */
#include "state_manager.h"

static context_slot_t g_context_slots[MAX_CONTEXT_SLOTS];
static route_slot_t g_route_slots[MAX_ROUTE_SLOTS];
static pending_horizon_t g_pending_horizons[MAX_PENDING_HORIZONS];
static cra_state_summary_t g_summary;

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

void cra_state_init(void) {
    _clear_slots();
    _clear_route_slots();
    _clear_pending();
    _clear_summary(0);
}

void cra_state_reset(void) {
    uint32_t reset_count = g_summary.state_resets + 1;
    _clear_slots();
    _clear_route_slots();
    _clear_pending();
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

void cra_state_get_summary(cra_state_summary_t *summary_out) {
    if (summary_out == 0) {
        return;
    }
    *summary_out = g_summary;
}
