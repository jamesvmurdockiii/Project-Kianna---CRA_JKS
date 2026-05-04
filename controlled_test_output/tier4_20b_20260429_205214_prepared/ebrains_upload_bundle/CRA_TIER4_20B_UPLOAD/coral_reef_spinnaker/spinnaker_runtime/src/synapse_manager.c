/*!
 * \file synapse_manager.c
 * \brief Dynamic synapse pool using per-post-neuron linked lists in SDRAM.
 */
#include "synapse_manager.h"
#include "neuron_manager.h"
#include <sark.h>

// ------------------------------------------------------------------
// Internal state
// ------------------------------------------------------------------
static uint32_t g_synapse_count = 0;

// ------------------------------------------------------------------
// Synapse index: one linked list per post-neuron
// ------------------------------------------------------------------

typedef struct post_entry {
    uint32_t post_id;
    synapse_t *head;
    struct post_entry *next;
} post_entry_t;

static post_entry_t *g_post_index = NULL;

static post_entry_t *_find_or_create_post(uint32_t post_id) {
    post_entry_t *e = g_post_index;
    while (e != NULL) {
        if (e->post_id == post_id) return e;
        e = e->next;
    }
    // create new entry
    e = (post_entry_t *) sark_alloc(1, sizeof(post_entry_t));
    if (e == NULL) return NULL;
    e->post_id = post_id;
    e->head    = NULL;
    e->next    = g_post_index;
    g_post_index = e;
    return e;
}

static post_entry_t *_find_post(uint32_t post_id) {
    post_entry_t *e = g_post_index;
    while (e != NULL) {
        if (e->post_id == post_id) return e;
        e = e->next;
    }
    return NULL;
}

// ------------------------------------------------------------------
// API
// ------------------------------------------------------------------

int synapse_create(uint32_t pre_id, uint32_t post_id, int32_t weight, uint32_t delay) {
    post_entry_t *pe = _find_or_create_post(post_id);
    if (pe == NULL) return -1;

    synapse_t *s = (synapse_t *) sark_alloc(1, sizeof(synapse_t));
    if (s == NULL) return -1;

    s->pre_id  = pre_id;
    s->weight  = weight;
    s->delay   = delay;
    s->next    = pe->head;
    pe->head   = s;
    g_synapse_count++;
    return 0;
}

int synapse_remove(uint32_t pre_id, uint32_t post_id) {
    post_entry_t *pe = _find_post(post_id);
    if (pe == NULL) return -1;

    synapse_t **pp = &pe->head;
    while (*pp != NULL) {
        synapse_t *s = *pp;
        if (s->pre_id == pre_id) {
            *pp = s->next;
            sark_free(s);
            g_synapse_count--;
            return 0;
        }
        pp = &s->next;
    }
    return -1;
}

void synapse_deliver_spike(uint32_t pre_id) {
    // O(S) scan — acceptable for PoC (<1k synapses).
    // Production would use a reverse index: pre_id -> list of posts.
    post_entry_t *pe = g_post_index;
    while (pe != NULL) {
        synapse_t *s = pe->head;
        while (s != NULL) {
            if (s->pre_id == pre_id) {
                neuron_add_input(pe->post_id, s->weight);
            }
            s = s->next;
        }
        pe = pe->next;
    }
}

void synapse_modulate_all(int32_t dopamine_level) {
    post_entry_t *pe = g_post_index;
    while (pe != NULL) {
        synapse_t *s = pe->head;
        while (s != NULL) {
            int32_t w = s->weight + dopamine_level;
            if (w > MAX_WEIGHT) w = MAX_WEIGHT;
            if (w < MIN_WEIGHT) w = MIN_WEIGHT;
            s->weight = w;
            s = s->next;
        }
        pe = pe->next;
    }
}

void synapse_remove_incident(uint32_t neuron_id) {
    // Remove all synapses where pre_id == neuron_id OR post_id == neuron_id.
    post_entry_t **pe_pp = &g_post_index;
    while (*pe_pp != NULL) {
        post_entry_t *pe = *pe_pp;

        // Scan synapses in this post-entry and remove any where pre matches
        synapse_t **s_pp = &pe->head;
        while (*s_pp != NULL) {
            synapse_t *s = *s_pp;
            if (s->pre_id == neuron_id || pe->post_id == neuron_id) {
                *s_pp = s->next;
                sark_free(s);
                g_synapse_count--;
            } else {
                s_pp = &s->next;
            }
        }

        // If this post-entry's post_id matches neuron_id, remove the whole entry
        if (pe->post_id == neuron_id) {
            *pe_pp = pe->next;
            sark_free(pe);
        } else {
            pe_pp = &pe->next;
        }
    }
}

void synapse_reset_all(void) {
    while (g_post_index != NULL) {
        post_entry_t *pe = g_post_index;
        synapse_t *s = pe->head;
        while (s != NULL) {
            synapse_t *next = s->next;
            sark_free(s);
            s = next;
        }
        g_post_index = pe->next;
        sark_free(pe);
    }
    g_synapse_count = 0;
}

uint32_t synapse_count(void) {
    return g_synapse_count;
}
