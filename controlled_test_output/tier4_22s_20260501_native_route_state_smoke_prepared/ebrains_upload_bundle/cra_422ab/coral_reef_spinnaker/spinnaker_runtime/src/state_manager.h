/*!
 * \file state_manager.h
 * \brief Bounded persistent CRA state for the custom SpiNNaker runtime.
 *
 * Tier 4.22c deliberately keeps this state static and fixed-size. The goal is
 * to move CRA toward chip-owned state without introducing dynamic Python
 * dictionaries, unbounded memory, or hidden host-side bookkeeping.
 */
#ifndef __STATE_MANAGER_H__
#define __STATE_MANAGER_H__

#include "config.h"

typedef struct context_slot {
    uint32_t key;
    int32_t value;
    int32_t confidence;
    uint32_t last_update;
    uint8_t active;
} context_slot_t;

typedef struct pending_horizon {
    uint32_t due_timestep;
    int32_t feature;
    int32_t prediction;
    uint8_t active;
} pending_horizon_t;

typedef struct cra_state_summary {
    uint32_t active_slots;
    uint32_t slot_writes;
    uint32_t slot_hits;
    uint32_t slot_misses;
    uint32_t slot_evictions;
    uint32_t decisions;
    uint32_t reward_events;
    uint32_t pending_created;
    uint32_t pending_matured;
    uint32_t pending_dropped;
    uint32_t active_pending;
    uint32_t state_resets;
    uint32_t route_writes;
    uint32_t route_reads;
    int32_t readout_weight;
    int32_t readout_bias;
    int32_t route_value;
    int32_t route_confidence;
    int32_t last_feature;
    int32_t last_prediction;
    int32_t last_reward;
} cra_state_summary_t;

void cra_state_init(void);
void cra_state_reset(void);

int cra_state_write_context(uint32_t key, int32_t value, int32_t confidence, uint32_t timestep);
int cra_state_read_context(uint32_t key, int32_t *value_out, int32_t *confidence_out);
uint32_t cra_state_active_slot_count(void);

int cra_state_write_route(int32_t value, int32_t confidence, uint32_t timestep);
int cra_state_read_route(int32_t *value_out, int32_t *confidence_out);

void cra_state_set_readout(int32_t weight, int32_t bias);
int32_t cra_state_predict_readout(int32_t feature);
void cra_state_record_decision(int32_t feature, int32_t prediction);
void cra_state_record_reward(int32_t reward);
int32_t cra_state_apply_reward_to_readout(int32_t reward, int32_t learning_rate);

int cra_state_schedule_pending_horizon(
    int32_t feature,
    int32_t prediction,
    uint32_t due_timestep
);
uint32_t cra_state_mature_pending_horizons(uint32_t timestep, int32_t target, int32_t learning_rate);
uint32_t cra_state_active_pending_count(void);

void cra_state_get_summary(cra_state_summary_t *summary_out);

#endif // __STATE_MANAGER_H__
