/*!
 * \file synapse_manager.h
 * \brief Dynamic synapse allocation.
 *
 * Synapses are indexed by both pre-neuron and post-neuron. The post index is
 * retained for lookup/removal, while the pre index lets multicast spike
 * delivery touch only outgoing synapses for the firing neuron.
 *
 * Eligibility traces are also linked into an active-trace list. Trace decay
 * and dopamine modulation therefore touch only synapses that have causal
 * activity instead of sweeping all synapses every millisecond.
 */
#ifndef __SYNAPSE_MANAGER_H__
#define __SYNAPSE_MANAGER_H__

#include "config.h"

// ------------------------------------------------------------------
// Synapse state
// ------------------------------------------------------------------
typedef struct synapse {
    uint32_t  pre_id;       // source neuron global id
    uint32_t  post_id;      // target neuron global id
    int32_t   weight;       // s16.15
    int32_t   eligibility_trace; // s16.15 causal spike trace
    uint32_t  delay;        // delay in timesteps
    uint8_t   active_trace; // true when linked into active trace list
    struct synapse *next_post;   // linked list (per post neuron)
    struct synapse *next_pre;    // linked list (per pre neuron)
    struct synapse *next_active; // linked list (active eligibility traces)
} synapse_t;

// ------------------------------------------------------------------
// API
// ------------------------------------------------------------------

/*! Create a synapse from pre_id -> post_id with given weight & delay.
    Returns 0 on success, -1 on failure. */
int synapse_create(uint32_t pre_id, uint32_t post_id, int32_t weight, uint32_t delay);

/*! Remove a synapse from pre_id -> post_id.  Returns 0 on success. */
int synapse_remove(uint32_t pre_id, uint32_t post_id);

/*! Deliver a spike from pre_id to all of its post-synaptic targets.
    Called from the packet callback. */
void synapse_deliver_spike(uint32_t pre_id);

/*! Decay all eligibility traces by decay_factor (s16.15). */
void synapse_decay_traces_all(int32_t decay_factor);

/*! Apply a global dopamine modulation to all synaptic weights.
    Weight updates are trace-gated: delta_w = dopamine * eligibility_trace. */
void synapse_modulate_all(int32_t dopamine_level);

/*! Remove all synapses incident to a given neuron (both pre and post).
    Called from neuron_death to prevent dangling synapses. */
void synapse_remove_incident(uint32_t neuron_id);

/*! Free every synapse in the system. */
void synapse_reset_all(void);

/*! Return total synapse count. */
uint32_t synapse_count(void);

/*! Return active eligibility trace count. */
uint32_t synapse_active_trace_count(void);

/*! Diagnostics for scale audits and host tests. */
uint32_t synapse_last_delivery_visit_count(void);
uint32_t synapse_last_decay_visit_count(void);
uint32_t synapse_last_modulation_visit_count(void);

/*! Host-test helpers for audited fixed-point state. */
int synapse_get_weight(uint32_t pre_id, uint32_t post_id, int32_t *weight_out);
int synapse_get_eligibility_trace(uint32_t pre_id, uint32_t post_id, int32_t *trace_out);

#endif // __SYNAPSE_MANAGER_H__
