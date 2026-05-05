/*!
 * \file host_interface.c
 * \brief SDP command dispatcher.
 */
#include "host_interface.h"
#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
#include "neuron_manager.h"
#include "synapse_manager.h"
#include "router.h"
#endif
#include "state_manager.h"
#include <sark.h>
#include <spin1_api.h>

// ------------------------------------------------------------------
// Externs
// ------------------------------------------------------------------
extern uint32_t g_timestep;
extern int32_t g_dopamine_level;

// Direct host lifecycle commands are allowed only for the legacy monolithic /
// single-core lifecycle smoke surface and the dedicated lifecycle_core profile.
// Context, route, memory, learning, and state cores must not mutate lifecycle
// slots directly in the multi-core split.
#if defined(CRA_RUNTIME_PROFILE_LIFECYCLE_CORE) || \
    (!defined(CRA_RUNTIME_PROFILE_STATE_CORE) && \
     !defined(CRA_RUNTIME_PROFILE_LEARNING_CORE) && \
     !defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) && \
     !defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) && \
     !defined(CRA_RUNTIME_PROFILE_MEMORY_CORE))
#define CRA_RUNTIME_PROFILE_LIFECYCLE_HOST_SURFACE 1
#endif

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

static inline void _write_u32(uint8_t *p, uint32_t value) {
    p[0] = (uint8_t)(value & 0xFF);
    p[1] = (uint8_t)((value >> 8) & 0xFF);
    p[2] = (uint8_t)((value >> 16) & 0xFF);
    p[3] = (uint8_t)((value >> 24) & 0xFF);
}

static inline void _write_s32(uint8_t *p, int32_t value) {
    _write_u32(p, (uint32_t)value);
}

static inline uint32_t _read_u32(const uint8_t *p) {
    return ((uint32_t)p[0])
        | ((uint32_t)p[1] << 8)
        | ((uint32_t)p[2] << 16)
        | ((uint32_t)p[3] << 24);
}

static inline int32_t _read_s32(const uint8_t *p) {
    return (int32_t)_read_u32(p);
}

// ------------------------------------------------------------------
// Command handlers
// ------------------------------------------------------------------

#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
static void _handle_birth(sdp_msg_t *msg) {
    uint32_t id = msg->arg1;
    neuron_t *n = neuron_birth(id);
    uint8_t reply[8];
    reply[0] = CMD_BIRTH;
    reply[1] = (n != NULL) ? 0 : 1;  // 0 = success
    reply[2] = (uint8_t)(id & 0xFF);
    reply[3] = (uint8_t)((id >> 8) & 0xFF);
    reply[4] = (uint8_t)((id >> 16) & 0xFF);
    reply[5] = (uint8_t)((id >> 24) & 0xFF);
    reply[6] = (uint8_t)(neuron_count() & 0xFF);
    reply[7] = (uint8_t)((neuron_count() >> 8) & 0xFF);
    sdp_send_reply(msg, reply, 8);
}

static void _handle_death(sdp_msg_t *msg) {
    uint32_t id = msg->arg1;
    int rc = neuron_death(id);
    uint8_t reply[4];
    reply[0] = CMD_DEATH;
    reply[1] = (rc == 0) ? 0 : 1;
    reply[2] = (uint8_t)(neuron_count() & 0xFF);
    reply[3] = (uint8_t)((neuron_count() >> 8) & 0xFF);
    sdp_send_reply(msg, reply, 4);
}

static void _handle_dopamine(sdp_msg_t *msg) {
    // Dopamine level as s16.15 fixed point
    g_dopamine_level = (int32_t) msg->arg1;
    uint8_t reply[6];
    reply[0] = CMD_DOPAMINE;
    reply[1] = 0;  // ack
    reply[2] = (uint8_t)(g_dopamine_level & 0xFF);
    reply[3] = (uint8_t)((g_dopamine_level >> 8) & 0xFF);
    reply[4] = (uint8_t)((g_dopamine_level >> 16) & 0xFF);
    reply[5] = (uint8_t)((g_dopamine_level >> 24) & 0xFF);
    sdp_send_reply(msg, reply, 6);
}

static void _handle_read_spikes(sdp_msg_t *msg) {
    // Minimal reply: global neuron count + current timestep only.
    // A full per-neuron dump would need SDP fragmentation or a
    // larger transfer mechanism (e.g. DMA to host SDRAM).
    uint8_t reply[6];
    reply[0] = CMD_READ_SPIKES;
    reply[1] = 0;
    uint32_t nc = neuron_count();
    reply[2] = (uint8_t)(nc & 0xFF);
    reply[3] = (uint8_t)((nc >> 8) & 0xFF);
    reply[4] = (uint8_t)(g_timestep & 0xFF);
    reply[5] = (uint8_t)((g_timestep >> 8) & 0xFF);
    sdp_send_reply(msg, reply, 6);
}

static void _handle_create_syn(sdp_msg_t *msg) {
    uint32_t pre  = msg->arg1;
    uint32_t post = msg->arg2;
    int32_t  w    = (int32_t) msg->arg3;
    int rc = synapse_create(pre, post, w, DEFAULT_SYN_DELAY);
    uint8_t reply[2];
    reply[0] = CMD_CREATE_SYN;
    reply[1] = (rc == 0) ? 0 : 1;
    sdp_send_reply(msg, reply, 2);
}

static void _handle_remove_syn(sdp_msg_t *msg) {
    uint32_t pre  = msg->arg1;
    uint32_t post = msg->arg2;
    int rc = synapse_remove(pre, post);
    uint8_t reply[2];
    reply[0] = CMD_REMOVE_SYN;
    reply[1] = (rc == 0) ? 0 : 1;
    sdp_send_reply(msg, reply, 2);
}
#endif

static void _handle_reset(sdp_msg_t *msg) {
#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
    router_reset_all();
    neuron_reset_all();
    synapse_reset_all();
#endif
    cra_state_reset();
    cra_state_schedule_init();
    g_dopamine_level = 0;
    g_timestep = 0;
    uint8_t reply[2];
    reply[0] = CMD_RESET;
    reply[1] = 0;
    sdp_send_reply(msg, reply, 2);
}

// ------------------------------------------------------------------
// 4.25B inter-core split handlers
// ------------------------------------------------------------------

#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
static void _handle_schedule_pending_split(sdp_msg_t *msg) {
    int32_t feature = (int32_t) msg->arg1;
    int32_t prediction = (int32_t) msg->arg2;
    uint32_t due_timestep = msg->arg3;
    int32_t target = _read_s32(&msg->data[0]);
    int rc = cra_state_schedule_pending_horizon_with_target(
        feature, prediction, target, due_timestep);
    // No reply — fire and forget
    (void)rc;
}
#endif

#ifdef CRA_RUNTIME_PROFILE_STATE_CORE
static void _handle_mature_ack_split(sdp_msg_t *msg) {
    // Advisory only — state core records learning core summary
    (void)msg;
}
#endif

static void _handle_read_state(sdp_msg_t *msg) {
    uint8_t reply[128];
    uint8_t len = host_if_pack_state_summary(reply, sizeof(reply));
    if (len == 0) return;
    sdp_send_reply(msg, reply, len);
}

static void _handle_lifecycle_init(sdp_msg_t *msg) {
    uint32_t pool_size = msg->arg1;
    uint32_t founder_count = msg->arg2;
    uint32_t seed = msg->arg3;
    int32_t trophic_seed_raw = _read_s32(&msg->data[0]);
    uint32_t generation_seed = _read_u32(&msg->data[4]);
    int rc = cra_lifecycle_init(pool_size, founder_count, seed, trophic_seed_raw, generation_seed);
    uint8_t reply[80];
    uint8_t len = host_if_pack_lifecycle_summary(reply, sizeof(reply));
    if (len == 0) {
        reply[0] = CMD_LIFECYCLE_INIT;
        reply[1] = 1;
        sdp_send_reply(msg, reply, 2);
        return;
    }
    reply[0] = CMD_LIFECYCLE_INIT;
    reply[1] = (rc == 0) ? 0 : 1;
    sdp_send_reply(msg, reply, len);
}

static void _handle_lifecycle_event(sdp_msg_t *msg) {
    uint32_t event_index = msg->arg1;
    uint8_t event_type = (uint8_t)(msg->arg2 & 0xFF);
    uint32_t target_slot = msg->arg3;
    int32_t parent_slot = _read_s32(&msg->data[0]);
    int32_t child_slot = _read_s32(&msg->data[4]);
    int32_t trophic_delta_raw = _read_s32(&msg->data[8]);
    int32_t reward_raw = _read_s32(&msg->data[12]);
    int rc = cra_lifecycle_apply_event(
        event_index,
        event_type,
        target_slot,
        parent_slot,
        child_slot,
        trophic_delta_raw,
        reward_raw
    );
    uint8_t reply[80];
    uint8_t len = host_if_pack_lifecycle_summary(reply, sizeof(reply));
    if (len == 0) {
        reply[0] = CMD_LIFECYCLE_EVENT;
        reply[1] = 1;
        sdp_send_reply(msg, reply, 2);
        return;
    }
    reply[0] = CMD_LIFECYCLE_EVENT;
    reply[1] = (rc == 0) ? 0 : 1;
    sdp_send_reply(msg, reply, len);
}

static void _handle_lifecycle_trophic_update(sdp_msg_t *msg) {
    uint32_t target_slot = msg->arg1;
    int32_t trophic_delta_raw = (int32_t)msg->arg2;
    int32_t reward_raw = (int32_t)msg->arg3;
    int rc = cra_lifecycle_apply_trophic_update(target_slot, trophic_delta_raw, reward_raw);
    uint8_t reply[80];
    uint8_t len = host_if_pack_lifecycle_summary(reply, sizeof(reply));
    if (len == 0) {
        reply[0] = CMD_LIFECYCLE_TROPHIC_UPDATE;
        reply[1] = 1;
        sdp_send_reply(msg, reply, 2);
        return;
    }
    reply[0] = CMD_LIFECYCLE_TROPHIC_UPDATE;
    reply[1] = (rc == 0) ? 0 : 1;
    sdp_send_reply(msg, reply, len);
}

static void _handle_lifecycle_read_state(sdp_msg_t *msg) {
    uint8_t reply[80];
    uint8_t len = host_if_pack_lifecycle_summary(reply, sizeof(reply));
    if (len == 0) return;
    sdp_send_reply(msg, reply, len);
}

static void _handle_lifecycle_sham_mode(sdp_msg_t *msg) {
    uint32_t mode = msg->arg1;
    int rc = cra_lifecycle_set_sham_mode(mode);
    uint8_t reply[80];
    uint8_t len = host_if_pack_lifecycle_summary(reply, sizeof(reply));
    if (len == 0) {
        reply[0] = CMD_LIFECYCLE_SHAM_MODE;
        reply[1] = 1;
        sdp_send_reply(msg, reply, 2);
        return;
    }
    reply[0] = CMD_LIFECYCLE_SHAM_MODE;
    reply[1] = (rc == 0) ? 0 : 1;
    sdp_send_reply(msg, reply, len);
}

#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
static void _handle_schedule_pending(sdp_msg_t *msg) {
    int32_t feature = (int32_t) msg->arg1;
    uint32_t delay_steps = msg->arg2;
    uint32_t due_timestep = g_timestep + delay_steps;
    int32_t prediction = cra_state_predict_readout(feature);
    int rc;
    uint8_t reply[10];

    cra_state_record_decision(feature, prediction);
    rc = cra_state_schedule_pending_horizon(feature, prediction, due_timestep);

    reply[0] = CMD_SCHEDULE_PENDING;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_s32(&reply[2], prediction);
    _write_u32(&reply[6], due_timestep);
    sdp_send_reply(msg, reply, 10);
}
#endif

static void _handle_mature_pending(sdp_msg_t *msg) {
    int32_t target = (int32_t) msg->arg1;
    int32_t learning_rate = (int32_t) msg->arg2;
    uint32_t mature_timestep = msg->arg3 != 0 ? msg->arg3 : g_timestep;
    uint32_t matured = cra_state_mature_pending_horizons(
        mature_timestep,
        target,
        learning_rate
    );
    cra_state_summary_t summary;
    uint8_t reply[14];

    cra_state_get_summary(&summary);
    reply[0] = CMD_MATURE_PENDING;
    reply[1] = (matured > 0) ? 0 : 1;
    _write_u32(&reply[2], matured);
    _write_s32(&reply[6], summary.readout_weight);
    _write_s32(&reply[10], summary.readout_bias);
    sdp_send_reply(msg, reply, 14);
}

static void _handle_write_context(sdp_msg_t *msg) {
    uint32_t key = msg->arg1;
    int32_t value = (int32_t) msg->arg2;
    int32_t confidence = (int32_t) msg->arg3;
    int rc = cra_state_write_context(key, value, confidence, g_timestep);
    cra_state_summary_t summary;
    uint8_t reply[10];

    cra_state_get_summary(&summary);
    reply[0] = CMD_WRITE_CONTEXT;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_u32(&reply[2], summary.active_slots);
    _write_u32(&reply[6], summary.slot_writes);
    sdp_send_reply(msg, reply, 10);
}

static void _handle_read_context(sdp_msg_t *msg) {
    uint32_t key = msg->arg1;
    int32_t value = 0;
    int32_t confidence = 0;
    int rc = cra_state_read_context(key, &value, &confidence);
    cra_state_summary_t summary;
    uint8_t reply[18];

    cra_state_get_summary(&summary);
    reply[0] = CMD_READ_CONTEXT;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_s32(&reply[2], value);
    _write_s32(&reply[6], confidence);
    _write_u32(&reply[10], summary.slot_hits);
    _write_u32(&reply[14], summary.slot_misses);
    sdp_send_reply(msg, reply, 18);
}

#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
static void _handle_schedule_context_pending(sdp_msg_t *msg) {
    uint32_t key = msg->arg1;
    int32_t cue = (int32_t) msg->arg2;
    uint32_t delay_steps = msg->arg3;
    int32_t context_value = 0;
    int32_t context_confidence = 0;
    int rc = cra_state_read_context(key, &context_value, &context_confidence);
    int32_t feature = FP_MUL(context_value, cue);
    uint32_t due_timestep = g_timestep + delay_steps;
    int32_t prediction = cra_state_predict_readout(feature);
    uint8_t reply[22];

    if (rc == 0) {
        cra_state_record_decision(feature, prediction);
        rc = cra_state_schedule_pending_horizon(feature, prediction, due_timestep);
    }

    reply[0] = CMD_SCHEDULE_CONTEXT_PENDING;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_s32(&reply[2], prediction);
    _write_u32(&reply[6], due_timestep);
    _write_s32(&reply[10], feature);
    _write_s32(&reply[14], context_value);
    _write_s32(&reply[18], context_confidence);
    sdp_send_reply(msg, reply, 22);
}
#endif

#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
static void _handle_write_route(sdp_msg_t *msg) {
    int32_t value = (int32_t) msg->arg1;
    int32_t confidence = (int32_t) msg->arg2;
    int rc = cra_state_write_route(value, confidence, g_timestep);
    cra_state_summary_t summary;
    uint8_t reply[10];

    cra_state_get_summary(&summary);
    reply[0] = CMD_WRITE_ROUTE;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_s32(&reply[2], summary.route_value);
    _write_u32(&reply[6], summary.route_writes);
    sdp_send_reply(msg, reply, 10);
}

static void _handle_read_route(sdp_msg_t *msg) {
    int32_t value = 0;
    int32_t confidence = 0;
    int rc = cra_state_read_route(&value, &confidence);
    cra_state_summary_t summary;
    uint8_t reply[14];

    cra_state_get_summary(&summary);
    reply[0] = CMD_READ_ROUTE;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_s32(&reply[2], value);
    _write_s32(&reply[6], confidence);
    _write_u32(&reply[10], summary.route_reads);
    sdp_send_reply(msg, reply, 14);
}

static void _handle_schedule_routed_context_pending(sdp_msg_t *msg) {
    uint32_t key = msg->arg1;
    int32_t cue = (int32_t) msg->arg2;
    uint32_t delay_steps = msg->arg3;
    int32_t context_value = 0;
    int32_t context_confidence = 0;
    int32_t route_value = 0;
    int32_t route_confidence = 0;
    int rc = cra_state_read_context(key, &context_value, &context_confidence);
    int rc_route = cra_state_read_route(&route_value, &route_confidence);
    int32_t feature = FP_MUL(FP_MUL(context_value, route_value), cue);
    uint32_t due_timestep = g_timestep + delay_steps;
    int32_t prediction = cra_state_predict_readout(feature);
    uint8_t reply[30];

    if (rc == 0 && rc_route == 0) {
        cra_state_record_decision(feature, prediction);
        rc = cra_state_schedule_pending_horizon(feature, prediction, due_timestep);
    } else {
        rc = -1;
    }

    reply[0] = CMD_SCHEDULE_ROUTED_CONTEXT_PENDING;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_s32(&reply[2], prediction);
    _write_u32(&reply[6], due_timestep);
    _write_s32(&reply[10], feature);
    _write_s32(&reply[14], context_value);
    _write_s32(&reply[18], context_confidence);
    _write_s32(&reply[22], route_value);
    _write_s32(&reply[26], route_confidence);
    sdp_send_reply(msg, reply, 30);
}
#endif

static void _handle_write_route_slot(sdp_msg_t *msg) {
    uint32_t key = msg->arg1;
    int32_t value = (int32_t) msg->arg2;
    int32_t confidence = (int32_t) msg->arg3;
    int rc = cra_state_write_route_slot(key, value, confidence, g_timestep);
    cra_state_summary_t summary;
    uint8_t reply[10];

    cra_state_get_summary(&summary);
    reply[0] = CMD_WRITE_ROUTE_SLOT;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_u32(&reply[2], summary.active_route_slots);
    _write_u32(&reply[6], summary.route_slot_writes);
    sdp_send_reply(msg, reply, 10);
}

static void _handle_read_route_slot(sdp_msg_t *msg) {
    uint32_t key = msg->arg1;
    int32_t value = 0;
    int32_t confidence = 0;
    int rc = cra_state_read_route_slot(key, &value, &confidence);
    cra_state_summary_t summary;
    uint8_t reply[18];

    cra_state_get_summary(&summary);
    reply[0] = CMD_READ_ROUTE_SLOT;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_s32(&reply[2], value);
    _write_s32(&reply[6], confidence);
    _write_u32(&reply[10], summary.route_slot_hits);
    _write_u32(&reply[14], summary.route_slot_misses);
    sdp_send_reply(msg, reply, 18);
}

#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
static void _handle_schedule_keyed_route_context_pending(sdp_msg_t *msg) {
    uint32_t key = msg->arg1;
    int32_t cue = (int32_t) msg->arg2;
    uint32_t delay_steps = msg->arg3;
    int32_t context_value = 0;
    int32_t context_confidence = 0;
    int32_t route_value = 0;
    int32_t route_confidence = 0;
    int rc_context = cra_state_read_context(key, &context_value, &context_confidence);
    int rc_route = cra_state_read_route_slot(key, &route_value, &route_confidence);
    int32_t feature = FP_MUL(FP_MUL(context_value, route_value), cue);
    uint32_t due_timestep = g_timestep + delay_steps;
    int32_t prediction = cra_state_predict_readout(feature);
    uint8_t reply[34];
    int rc = -1;

    if (rc_context == 0 && rc_route == 0) {
        cra_state_record_decision(feature, prediction);
        rc = cra_state_schedule_pending_horizon(feature, prediction, due_timestep);
    }

    reply[0] = CMD_SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_s32(&reply[2], prediction);
    _write_u32(&reply[6], due_timestep);
    _write_s32(&reply[10], feature);
    _write_s32(&reply[14], context_value);
    _write_s32(&reply[18], context_confidence);
    _write_s32(&reply[22], route_value);
    _write_s32(&reply[26], route_confidence);
    _write_u32(&reply[30], key);
    sdp_send_reply(msg, reply, 34);
}
#endif

static void _handle_write_memory_slot(sdp_msg_t *msg) {
    uint32_t key = msg->arg1;
    int32_t value = (int32_t) msg->arg2;
    int32_t confidence = (int32_t) msg->arg3;
    int rc = cra_state_write_memory_slot(key, value, confidence, g_timestep);
    cra_state_summary_t summary;
    uint8_t reply[10];

    cra_state_get_summary(&summary);
    reply[0] = CMD_WRITE_MEMORY_SLOT;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_u32(&reply[2], summary.active_memory_slots);
    _write_u32(&reply[6], summary.memory_slot_writes);
    sdp_send_reply(msg, reply, 10);
}

static void _handle_read_memory_slot(sdp_msg_t *msg) {
    uint32_t key = msg->arg1;
    int32_t value = 0;
    int32_t confidence = 0;
    int rc = cra_state_read_memory_slot(key, &value, &confidence);
    cra_state_summary_t summary;
    uint8_t reply[18];

    cra_state_get_summary(&summary);
    reply[0] = CMD_READ_MEMORY_SLOT;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_s32(&reply[2], value);
    _write_s32(&reply[6], confidence);
    _write_u32(&reply[10], summary.memory_slot_hits);
    _write_u32(&reply[14], summary.memory_slot_misses);
    sdp_send_reply(msg, reply, 18);
}

static void _schedule_memory_route_context_common(
    sdp_msg_t *msg,
    uint8_t command,
    uint32_t context_key,
    uint32_t route_key,
    uint32_t memory_key,
    int32_t cue,
    uint32_t delay_steps,
    uint8_t include_decoupled_keys
) {
    int32_t context_value = 0;
    int32_t context_confidence = 0;
    int32_t route_value = 0;
    int32_t route_confidence = 0;
    int32_t memory_value = 0;
    int32_t memory_confidence = 0;
    int rc_context = cra_state_read_context(context_key, &context_value, &context_confidence);
    int rc_route = cra_state_read_route_slot(route_key, &route_value, &route_confidence);
    int rc_memory = cra_state_read_memory_slot(memory_key, &memory_value, &memory_confidence);
    int32_t feature = FP_MUL(FP_MUL(FP_MUL(context_value, route_value), memory_value), cue);
    uint32_t due_timestep = g_timestep + delay_steps;
    int32_t prediction = cra_state_predict_readout(feature);
    uint8_t reply[50];
    int rc = -1;

    if (rc_context == 0 && rc_route == 0 && rc_memory == 0) {
        cra_state_record_decision(feature, prediction);
        rc = cra_state_schedule_pending_horizon(feature, prediction, due_timestep);
    }

    reply[0] = command;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_s32(&reply[2], prediction);
    _write_u32(&reply[6], due_timestep);
    _write_s32(&reply[10], feature);
    _write_s32(&reply[14], context_value);
    _write_s32(&reply[18], context_confidence);
    _write_s32(&reply[22], route_value);
    _write_s32(&reply[26], route_confidence);
    _write_s32(&reply[30], memory_value);
    _write_s32(&reply[34], memory_confidence);
    _write_u32(&reply[38], context_key);
    if (include_decoupled_keys) {
        _write_u32(&reply[42], route_key);
        _write_u32(&reply[46], memory_key);
        sdp_send_reply(msg, reply, 50);
    } else {
        sdp_send_reply(msg, reply, 42);
    }
}

#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
static void _handle_schedule_memory_route_context_pending(sdp_msg_t *msg) {
    uint32_t key = msg->arg1;
    _schedule_memory_route_context_common(
        msg,
        CMD_SCHEDULE_MEMORY_ROUTE_CONTEXT_PENDING,
        key,
        key,
        key,
        (int32_t) msg->arg2,
        msg->arg3,
        0
    );
}
#endif

static void _handle_schedule_decoupled_memory_route_context_pending(sdp_msg_t *msg) {
    uint32_t context_key = msg->arg1;
    uint32_t route_key = _read_u32(&msg->data[0]);
    uint32_t memory_key = _read_u32(&msg->data[4]);
    _schedule_memory_route_context_common(
        msg,
        CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING,
        context_key,
        route_key,
        memory_key,
        _read_s32(&msg->data[8]),
        _read_u32(&msg->data[12]),
        1
    );
}

static void _handle_write_schedule_entry(sdp_msg_t *msg) {
    uint32_t index = msg->arg1;
    schedule_entry_t entry;
    entry.timestep = _read_u32(&msg->data[0]);
    entry.context_key = _read_u32(&msg->data[4]);
    entry.route_key = _read_u32(&msg->data[8]);
    entry.memory_key = _read_u32(&msg->data[12]);
    entry.cue = _read_s32(&msg->data[16]);
    entry.target = _read_s32(&msg->data[20]);
    entry.delay = _read_u32(&msg->data[24]);
    int rc = cra_state_write_schedule_entry(index, &entry);
    uint8_t reply[6];
    reply[0] = CMD_WRITE_SCHEDULE_ENTRY;
    reply[1] = (rc == 0) ? 0 : 1;
    _write_u32(&reply[2], index);
    sdp_send_reply(msg, reply, 6);
}

static void _handle_run_continuous(sdp_msg_t *msg) {
    cra_state_set_learning_rate((int32_t)msg->arg1);
    cra_state_set_schedule_count(msg->arg2);
    cra_state_set_continuous_mode(1);
    uint8_t reply[2];
    reply[0] = CMD_RUN_CONTINUOUS;
    reply[1] = 0;
    sdp_send_reply(msg, reply, 2);
}

static void _handle_pause(sdp_msg_t *msg) {
    cra_state_set_continuous_mode(0);
    uint8_t reply[6];
    reply[0] = CMD_PAUSE;
    reply[1] = 0;
    _write_u32(&reply[2], g_timestep);
    sdp_send_reply(msg, reply, 6);
}

// ------------------------------------------------------------------
// 4.26 inter-core lookup handlers (transitional SDP; target is multicast/MCPL)
// ------------------------------------------------------------------

#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
static void _handle_lookup_request(sdp_msg_t *msg) {
    uint32_t seq_id = msg->arg1;
    uint32_t key = msg->arg2;
    uint8_t type = (uint8_t)(msg->arg3 & 0xFF);
    cra_state_handle_lookup_request(seq_id, key, type);
}
#endif

#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
static void _handle_lookup_reply(sdp_msg_t *msg) {
    uint32_t seq_id = msg->arg1;
    int32_t value = (int32_t)msg->arg2;
    int32_t confidence = (int32_t)msg->arg3;
    uint8_t hit = msg->data[0];
    int rc = cra_state_lookup_receive(seq_id, value, confidence, hit);
    (void)rc;
    /* No reply sent — fire and forget */
}
#endif

// ------------------------------------------------------------------
// Public API
// ------------------------------------------------------------------

void host_if_init(void) {
    // SDP callback is registered in main.c via spin1_callback_on
}

void sdp_rx_callback(uint mailbox, uint port) {
    sdp_msg_t *msg = (sdp_msg_t *) mailbox;
    uint8_t cmd = (uint8_t)(msg->cmd_rc & 0xFF);
    g_summary.commands_received++;
#if defined(CRA_RUNTIME_PROFILE_STATE_CORE) || defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
    cra_state_capture_chip_addr(msg->dest_addr);
#endif
    switch (cmd) {
// ------------------------------------------------------------------
// Full runtime only: neuron/synapse/router commands
// ------------------------------------------------------------------
#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
        case CMD_BIRTH:       _handle_birth(msg);       break;
        case CMD_DEATH:       _handle_death(msg);       break;
        case CMD_DOPAMINE:    _handle_dopamine(msg);    break;
        case CMD_READ_SPIKES: _handle_read_spikes(msg); break;
        case CMD_CREATE_SYN:  _handle_create_syn(msg);  break;
        case CMD_REMOVE_SYN:  _handle_remove_syn(msg);  break;
#endif

// ------------------------------------------------------------------
// All profiles handle RESET and READ_STATE
// ------------------------------------------------------------------
        case CMD_RESET:       _handle_reset(msg);       break;
        case CMD_READ_STATE:  _handle_read_state(msg);  break;

// ------------------------------------------------------------------
// Tier 4.30 lifecycle/static-pool surface. This is metadata/mask state,
// not legacy dynamic neuron allocation.
// ------------------------------------------------------------------
#ifdef CRA_RUNTIME_PROFILE_LIFECYCLE_HOST_SURFACE
        case CMD_LIFECYCLE_INIT:           _handle_lifecycle_init(msg);           break;
        case CMD_LIFECYCLE_EVENT:          _handle_lifecycle_event(msg);          break;
        case CMD_LIFECYCLE_TROPHIC_UPDATE: _handle_lifecycle_trophic_update(msg); break;
        case CMD_LIFECYCLE_READ_STATE:     _handle_lifecycle_read_state(msg);     break;
        case CMD_LIFECYCLE_SHAM_MODE:      _handle_lifecycle_sham_mode(msg);      break;
#endif

// ------------------------------------------------------------------
// 4.25B two-core split opcodes (state_core only)
// ------------------------------------------------------------------
#ifdef CRA_RUNTIME_PROFILE_STATE_CORE
        case CMD_MATURE_ACK_SPLIT:       _handle_mature_ack_split(msg);       break;
#endif

// ------------------------------------------------------------------
// Full runtime only: monolithic schedule commands
// ------------------------------------------------------------------
#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
        case CMD_SCHEDULE_PENDING: _handle_schedule_pending(msg); break;
        case CMD_SCHEDULE_CONTEXT_PENDING: _handle_schedule_context_pending(msg); break;
        case CMD_WRITE_ROUTE:      _handle_write_route(msg);      break;
        case CMD_READ_ROUTE:       _handle_read_route(msg);       break;
        case CMD_SCHEDULE_ROUTED_CONTEXT_PENDING: _handle_schedule_routed_context_pending(msg); break;
        case CMD_SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING: _handle_schedule_keyed_route_context_pending(msg); break;
        case CMD_SCHEDULE_MEMORY_ROUTE_CONTEXT_PENDING: _handle_schedule_memory_route_context_pending(msg); break;
#endif

// ------------------------------------------------------------------
// context_core: context state only
// ------------------------------------------------------------------
#ifdef CRA_RUNTIME_PROFILE_CONTEXT_CORE
        case CMD_WRITE_CONTEXT:    _handle_write_context(msg);    break;
        case CMD_READ_CONTEXT:     _handle_read_context(msg);     break;
#endif

// ------------------------------------------------------------------
// route_core: route state only
// ------------------------------------------------------------------
#ifdef CRA_RUNTIME_PROFILE_ROUTE_CORE
        case CMD_WRITE_ROUTE_SLOT: _handle_write_route_slot(msg); break;
        case CMD_READ_ROUTE_SLOT:  _handle_read_route_slot(msg);  break;
#endif

// ------------------------------------------------------------------
// memory_core: memory state only
// ------------------------------------------------------------------
#ifdef CRA_RUNTIME_PROFILE_MEMORY_CORE
        case CMD_WRITE_MEMORY_SLOT: _handle_write_memory_slot(msg); break;
        case CMD_READ_MEMORY_SLOT:  _handle_read_memory_slot(msg);  break;
#endif

// ------------------------------------------------------------------
// learning_core: schedule, pending, run control, lookup replies
// ------------------------------------------------------------------
#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
        case CMD_MATURE_PENDING:        _handle_mature_pending(msg);        break;
        case CMD_WRITE_SCHEDULE_ENTRY:  _handle_write_schedule_entry(msg);  break;
        case CMD_RUN_CONTINUOUS:        _handle_run_continuous(msg);        break;
        case CMD_PAUSE:                 _handle_pause(msg);                 break;
        case CMD_LOOKUP_REPLY:          _handle_lookup_reply(msg);          break;
#endif

// ------------------------------------------------------------------
// decoupled_memory_route and state_core: all state commands
// ------------------------------------------------------------------
#if defined(CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE) && !defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) && !defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) && !defined(CRA_RUNTIME_PROFILE_MEMORY_CORE) && !defined(CRA_RUNTIME_PROFILE_LEARNING_CORE) && !defined(CRA_RUNTIME_PROFILE_LIFECYCLE_CORE)
        case CMD_MATURE_PENDING:   _handle_mature_pending(msg);   break;
        case CMD_WRITE_CONTEXT:    _handle_write_context(msg);    break;
        case CMD_READ_CONTEXT:     _handle_read_context(msg);     break;
        case CMD_WRITE_ROUTE_SLOT: _handle_write_route_slot(msg); break;
        case CMD_READ_ROUTE_SLOT:  _handle_read_route_slot(msg);  break;
        case CMD_WRITE_MEMORY_SLOT: _handle_write_memory_slot(msg); break;
        case CMD_READ_MEMORY_SLOT:  _handle_read_memory_slot(msg);  break;
        case CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING: _handle_schedule_decoupled_memory_route_context_pending(msg); break;
        case CMD_WRITE_SCHEDULE_ENTRY: _handle_write_schedule_entry(msg); break;
        case CMD_RUN_CONTINUOUS:       _handle_run_continuous(msg);       break;
        case CMD_PAUSE:                _handle_pause(msg);                break;
#endif

// ------------------------------------------------------------------
// 4.26 state-server cores: handle lookup requests from learning core
// Also acknowledge run/pause so the host control surface is uniform.
// ------------------------------------------------------------------
#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
        case CMD_LOOKUP_REQUEST: _handle_lookup_request(msg); break;
        case CMD_RUN_CONTINUOUS: _handle_run_continuous(msg); break;
        case CMD_PAUSE:          _handle_pause(msg);          break;
#endif

        default:
            // Unknown or unsupported command for this profile — send NAK
            {
                uint8_t nak[2] = {cmd, 0xFF};
                sdp_send_reply(msg, nak, 2);
            }
            break;
    }
    spin1_msg_free(msg);
}

uint8_t host_if_pack_state_summary(uint8_t *payload, uint8_t max_len) {
    cra_state_summary_t summary;
    const uint8_t required_len = 105;
    if (payload == 0 || max_len < required_len) {
        return 0;
    }
    cra_state_get_summary(&summary);

    payload[0] = CMD_READ_STATE;
    payload[1] = 0;  // status
    payload[2] = 2;  // payload schema version
    payload[3] = 0;  // reserved/alignment

    _write_u32(&payload[4], g_timestep);
#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE
    _write_u32(&payload[8], neuron_count());
    _write_u32(&payload[12], synapse_count());
    _write_u32(&payload[16], synapse_active_trace_count());
#else
    _write_u32(&payload[8], 0);
    _write_u32(&payload[12], 0);
    _write_u32(&payload[16], 0);
#endif
#if defined(CRA_RUNTIME_PROFILE_ROUTE_CORE)
    _write_u32(&payload[20], summary.active_route_slots);
    _write_u32(&payload[24], summary.route_slot_writes);
    _write_u32(&payload[28], summary.route_slot_hits);
    _write_u32(&payload[32], summary.route_slot_misses);
    _write_u32(&payload[36], summary.route_slot_evictions);
#elif defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
    _write_u32(&payload[20], summary.active_memory_slots);
    _write_u32(&payload[24], summary.memory_slot_writes);
    _write_u32(&payload[28], summary.memory_slot_hits);
    _write_u32(&payload[32], summary.memory_slot_misses);
    _write_u32(&payload[36], summary.memory_slot_evictions);
#else
    _write_u32(&payload[20], summary.active_slots);
    _write_u32(&payload[24], summary.slot_writes);
    _write_u32(&payload[28], summary.slot_hits);
    _write_u32(&payload[32], summary.slot_misses);
    _write_u32(&payload[36], summary.slot_evictions);
#endif
    _write_u32(&payload[40], summary.decisions);
    _write_u32(&payload[44], summary.reward_events);
    _write_u32(&payload[48], summary.pending_created);
    _write_u32(&payload[52], summary.pending_matured);
    _write_u32(&payload[56], summary.pending_dropped);
    _write_u32(&payload[60], summary.active_pending);
    _write_s32(&payload[64], summary.readout_weight);
    _write_s32(&payload[68], summary.readout_bias);
    payload[72] = MAKE_STATE_FLAGS(RUNTIME_PROFILE_ID, 0);  // low 4 bits = profile_id, high 4 bits = flags
    _write_u32(&payload[73], summary.lookup_requests_sent);
    _write_u32(&payload[77], summary.lookup_replies_received);
    _write_u32(&payload[81], summary.lookup_stale_replies);
    _write_u32(&payload[85], summary.lookup_duplicate_replies);
    _write_u32(&payload[89], summary.lookup_timeouts);
    _write_u32(&payload[93], summary.commands_received);
    _write_u32(&payload[97], cra_state_schedule_entry_count());
    _write_u32(&payload[101], summary.readback_bytes_sent + required_len);
    g_summary.readback_bytes_sent += required_len;
    return required_len;
}

uint8_t host_if_pack_lifecycle_summary(uint8_t *payload, uint8_t max_len) {
    cra_lifecycle_summary_t summary;
    const uint8_t required_len = 68;
    if (payload == 0 || max_len < required_len) {
        return 0;
    }
    cra_lifecycle_get_summary(&summary);

    payload[0] = CMD_LIFECYCLE_READ_STATE;
    payload[1] = 0;
    payload[2] = (uint8_t)summary.schema_version;
    payload[3] = (uint8_t)(summary.sham_mode & 0xFF);
    _write_u32(&payload[4], summary.pool_size);
    _write_u32(&payload[8], summary.founder_count);
    _write_u32(&payload[12], summary.active_count);
    _write_u32(&payload[16], summary.inactive_count);
    _write_u32(&payload[20], summary.active_mask_bits);
    _write_u32(&payload[24], summary.attempted_event_count);
    _write_u32(&payload[28], summary.lifecycle_event_count);
    _write_u32(&payload[32], summary.cleavage_count);
    _write_u32(&payload[36], summary.adult_birth_count);
    _write_u32(&payload[40], summary.death_count);
    _write_u32(&payload[44], summary.maturity_count);
    _write_u32(&payload[48], summary.trophic_update_count);
    _write_u32(&payload[52], summary.invalid_event_count);
    _write_u32(&payload[56], summary.lineage_checksum);
    _write_s32(&payload[60], summary.trophic_checksum);
    _write_u32(&payload[64], g_summary.readback_bytes_sent + required_len);
    g_summary.readback_bytes_sent += required_len;
    return required_len;
}

void sdp_send_reply(sdp_msg_t *req, const uint8_t *payload, uint8_t payload_len) {
    sdp_msg_t *reply = (sdp_msg_t *) spin1_msg_get();
    if (reply == NULL) return;

    // Swap source/dest so the reply goes back to the host.  SpiNNaker's real
    // sdp_msg_t stores port+CPU and x/y coordinates in packed fields:
    // dest_port/srce_port and dest_addr/srce_addr.
    reply->dest_port = req->srce_port;
    reply->srce_port = req->dest_port;
    reply->dest_addr = req->srce_addr;
    reply->srce_addr = req->dest_addr;
    reply->flags     = 0x07;  // reply flag
    reply->tag       = req->tag;
    reply->seq       = req->seq;
    reply->arg1      = 0;
    reply->arg2      = 0;
    reply->arg3      = 0;

    uint8_t cmd = payload_len > 0 ? payload[0] : 0;
    uint8_t status = payload_len > 1 ? payload[1] : 0xFF;
    uint8_t data_len = payload_len > 2 ? (uint8_t)(payload_len - 2) : 0;
    reply->cmd_rc = (uint16_t)cmd | ((uint16_t)status << 8);
    reply->length = (uint16_t)(8 + 16 + data_len);  // SDP header + command header + data
    if (data_len > 0) {
        sark_mem_cpy(reply->data, &payload[2], data_len);
    }

    spin1_send_sdp_msg(reply, 1);
    spin1_msg_free(reply);
}
