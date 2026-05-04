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

typedef struct route_slot {
    uint32_t key;
    int32_t value;
    int32_t confidence;
    uint32_t last_update;
    uint8_t active;
} route_slot_t;

typedef struct memory_slot {
    uint32_t key;
    int32_t value;
    int32_t confidence;
    uint32_t last_update;
    uint8_t active;
} memory_slot_t;

typedef struct pending_horizon {
    uint32_t due_timestep;
    int32_t feature;
    int32_t prediction;
    int32_t target;
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
    uint32_t active_route_slots;
    uint32_t route_slot_writes;
    uint32_t route_slot_hits;
    uint32_t route_slot_misses;
    uint32_t route_slot_evictions;
    uint32_t active_memory_slots;
    uint32_t memory_slot_writes;
    uint32_t memory_slot_hits;
    uint32_t memory_slot_misses;
    uint32_t memory_slot_evictions;
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
int cra_state_write_route_slot(uint32_t key, int32_t value, int32_t confidence, uint32_t timestep);
int cra_state_read_route_slot(uint32_t key, int32_t *value_out, int32_t *confidence_out);
uint32_t cra_state_active_route_slot_count(void);
int cra_state_write_memory_slot(uint32_t key, int32_t value, int32_t confidence, uint32_t timestep);
int cra_state_read_memory_slot(uint32_t key, int32_t *value_out, int32_t *confidence_out);
uint32_t cra_state_active_memory_slot_count(void);

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

typedef struct schedule_entry {
    uint32_t timestep;
    uint32_t context_key;
    uint32_t route_key;
    uint32_t memory_key;
    int32_t cue;
    int32_t target;
    uint32_t delay;
} schedule_entry_t;

void cra_state_schedule_init(void);
int cra_state_write_schedule_entry(uint32_t index, const schedule_entry_t *entry);
uint32_t cra_state_schedule_entry_count(void);
void cra_state_set_schedule_count(uint32_t count);
uint8_t cra_state_continuous_mode(void);
void cra_state_set_continuous_mode(uint8_t mode);
void cra_state_set_learning_rate(int32_t lr_raw);
uint32_t cra_state_process_continuous_tick(uint32_t timestep);

#ifdef CRA_RUNTIME_PROFILE_STATE_CORE
void cra_state_capture_chip_addr(uint16_t chip_addr);
#endif

int cra_state_schedule_pending_horizon_with_target(
    int32_t feature,
    int32_t prediction,
    int32_t target,
    uint32_t due_timestep
);
uint32_t cra_state_mature_oldest_pending(uint32_t timestep, int32_t learning_rate);

void cra_state_get_summary(cra_state_summary_t *summary_out);

#endif // __STATE_MANAGER_H__
