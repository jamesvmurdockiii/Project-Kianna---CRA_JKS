/*!
 * \file neuron_manager.c
 * \brief Dynamic LIF neuron pool — linked-list in SDRAM.
 */
#include "neuron_manager.h"
#include "synapse_manager.h"
#include "router.h"
#include <sark.h>
#include <spin1_api.h>

static neuron_t *g_neuron_list = NULL;   // head of linked list
static uint32_t  g_neuron_count = 0;      // live neuron count
static uint32_t  g_app_id = 0;            // set from c_main

// ------------------------------------------------------------------
// Externals from main.c
// ------------------------------------------------------------------
extern uint32_t get_app_id(void);
extern void emit_spike(uint32_t neuron_id);

void neuron_mgr_init(void) {
    g_neuron_list = NULL;
    g_neuron_count = 0;
    g_app_id = get_app_id();
}

neuron_t *neuron_birth(uint32_t id) {
    if (g_neuron_count >= MAX_NEURONS) {
        return NULL;  // safety ceiling
    }
    // Allocate neuron struct from SDRAM heap
    neuron_t *n = (neuron_t *) sark_alloc(1, sizeof(neuron_t));
    if (n == NULL) {
        return NULL;
    }
    n->id               = id;
    n->v_mem            = DEFAULT_V_REST;
    n->v_thresh         = DEFAULT_V_THRESH;
    n->v_reset          = DEFAULT_V_RESET;
    n->v_rest           = DEFAULT_V_REST;
    n->i_offset         = DEFAULT_I_OFFSET;
    n->tau_m            = DEFAULT_TAU_M;
    n->tau_refr         = DEFAULT_TAU_REFR;
    n->refract_counter  = 0;
    n->synaptic_input   = 0;
    n->spike_count      = 0;
    n->last_spike_time  = 0;
    n->next             = g_neuron_list;
    g_neuron_list       = n;
    g_neuron_count++;

    // Allocate a router CAM entry so spikes for this neuron are delivered
    router_add_neuron(id);
    return n;
}

int neuron_death(uint32_t id) {
    neuron_t **pp = &g_neuron_list;
    while (*pp != NULL) {
        neuron_t *n = *pp;
        if (n->id == id) {
            *pp = n->next;       // unlink
            synapse_remove_incident(id);
            router_remove_neuron(id);
            sark_free(n);        // return to SDRAM heap
            g_neuron_count--;
            return 0;
        }
        pp = &n->next;
    }
    return -1;  // not found
}

neuron_t *neuron_find(uint32_t id) {
    neuron_t *n = g_neuron_list;
    while (n != NULL) {
        if (n->id == id) return n;
        n = n->next;
    }
    return NULL;
}

void neuron_add_input(uint32_t id, int32_t weight) {
    neuron_t *n = neuron_find(id);
    if (n != NULL) {
        n->synaptic_input += weight;
    }
}

void neuron_update_all(uint32_t timestep) {
    neuron_t *n = g_neuron_list;
    while (n != NULL) {
        // Refractory check
        if (n->refract_counter > 0) {
            n->refract_counter--;
            n->v_mem = n->v_reset;
        } else {
            // LIF update: v = v + (v_rest - v)/tau_m + i_offset + synaptic_input
            int32_t leak = FP_DIV(n->v_rest - n->v_mem, n->tau_m);
            n->v_mem += leak + n->i_offset + n->synaptic_input;

            // Threshold check
            if (n->v_mem >= n->v_thresh) {
                // FIRE
                n->v_mem = n->v_reset;
                n->refract_counter = n->tau_refr;
                n->spike_count++;
                n->last_spike_time = timestep;
                emit_spike(n->id);
            }
        }
        // Clear synaptic input for next timestep
        n->synaptic_input = 0;
        n = n->next;
    }
}

uint32_t neuron_count(void) {
    return g_neuron_count;
}

neuron_t *neuron_list_head(void) {
    return g_neuron_list;
}

void neuron_reset_all(void) {
    router_reset_all();
    while (g_neuron_list != NULL) {
        neuron_t *n = g_neuron_list;
        g_neuron_list = n->next;
        sark_free(n);
    }
    g_neuron_count = 0;
}
