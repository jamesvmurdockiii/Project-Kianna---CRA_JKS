/*!
 * \file synapse_manager.h
 * \brief Dynamic synapse allocation.
 *
 * Synapses are stored as a singly-linked list per *target* neuron.
 * Each synapse carries a plastic weight and a pre-synaptic source id.
 * When a spike arrives (multicast packet), the packet callback walks
 * the target neuron's synapse list and adds each weight to the
 * neuron's input buffer.
 *
 * For the PoC we keep synapses in SDRAM and do not implement
 * full STDP (that can be added later in synapse_update_all).
 */
#ifndef __SYNAPSE_MANAGER_H__
#define __SYNAPSE_MANAGER_H__

#include "config.h"

// ------------------------------------------------------------------
// Synapse state
// ------------------------------------------------------------------
typedef struct synapse {
    uint32_t  pre_id;       // source neuron global id
    int32_t   weight;       // s16.15
    uint32_t  delay;        // delay in timesteps
    struct synapse *next;   // linked list (per post neuron)
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

/*! Apply a global dopamine modulation to all synaptic weights.
    This is a simplified neuromodulation step; real STDP+DA would
    use eligibility traces. */
void synapse_modulate_all(int32_t dopamine_level);

/*! Remove all synapses incident to a given neuron (both pre and post).
    Called from neuron_death to prevent dangling synapses. */
void synapse_remove_incident(uint32_t neuron_id);

/*! Free every synapse in the system. */
void synapse_reset_all(void);

/*! Return total synapse count. */
uint32_t synapse_count(void);

#endif // __SYNAPSE_MANAGER_H__
