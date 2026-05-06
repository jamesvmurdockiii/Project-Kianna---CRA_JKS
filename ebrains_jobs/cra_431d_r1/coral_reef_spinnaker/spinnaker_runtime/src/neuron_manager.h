/*!
 * \file neuron_manager.h
 * \brief Dynamic neuron allocation and LIF state update.
 *
 * Neurons are stored as a singly-linked list in SDRAM.  Each neuron
 * carries its own parameter set and input spike buffer.  Birth and
 * death operations are O(n) in the list length; for the PoC this is
 * acceptable (target < 1k neurons per core).
 */
#ifndef __NEURON_MANAGER_H__
#define __NEURON_MANAGER_H__

#include "config.h"

// ------------------------------------------------------------------
// Neuron state
// ------------------------------------------------------------------
typedef struct neuron {
    uint32_t  id;              // global neuron identifier
    int32_t   v_mem;           // membrane potential (s16.15)
    int32_t   v_thresh;        // firing threshold (s16.15)
    int32_t   v_reset;         // reset voltage (s16.15)
    int32_t   v_rest;          // resting voltage (s16.15)
    int32_t   i_offset;        // external current (s16.15)
    int32_t   tau_m;           // membrane time constant (s16.15 ms)
    uint32_t  tau_refr;        // refractory period (ms)
    uint32_t  refract_counter; // remaining refractory steps
    int32_t   synaptic_input;  // accumulated input this timestep (s16.15)
    uint32_t  spike_count;     // total spikes emitted
    uint32_t  last_spike_time; // timestep of last spike
    struct neuron *next;       // linked list
} neuron_t;

// ------------------------------------------------------------------
// API
// ------------------------------------------------------------------

/*! Initialise the neuron manager (call once from c_main). */
void neuron_mgr_init(void);

/*! Create a new neuron with default parameters.  Returns pointer
    to the new neuron, or NULL if allocation fails. */
neuron_t *neuron_birth(uint32_t id);

/*! Destroy a neuron and free its SDRAM.  Returns 0 on success. */
int neuron_death(uint32_t id);

/*! Find a neuron by global id.  Returns NULL if not found. */
neuron_t *neuron_find(uint32_t id);

/*! Accumulate a synaptic weight into a neuron's input buffer.
    Called from the packet callback when a spike arrives. */
void neuron_add_input(uint32_t id, int32_t weight);

/*! Advance all neurons by one timestep (LIF update + refractory).
    Called from the timer callback.  Emits multicast spikes. */
void neuron_update_all(uint32_t timestep);

/*! Return the current number of live neurons. */
uint32_t neuron_count(void);

/*! Reset the entire population (free all neurons). */
void neuron_reset_all(void);

/*! Access the global list head (for iteration / diagnostics). */
neuron_t *neuron_list_head(void);

#endif // __NEURON_MANAGER_H__
