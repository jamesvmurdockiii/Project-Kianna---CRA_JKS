/*!
 * \file synapse_manager.c
 * \brief Dynamic synapse pool with pre/post indexes and active trace list.
 */
#include "synapse_manager.h"
#include "neuron_manager.h"
#include <sark.h>

// ------------------------------------------------------------------
// Internal state
// ------------------------------------------------------------------
static uint32_t g_synapse_count = 0;
static uint32_t g_active_trace_count = 0;
static uint32_t g_last_delivery_visits = 0;
static uint32_t g_last_decay_visits = 0;
static uint32_t g_last_modulation_visits = 0;

// ------------------------------------------------------------------
// Synapse indexes
// ------------------------------------------------------------------

typedef struct post_entry {
    uint32_t post_id;
    synapse_t *head;
    struct post_entry *next;
} post_entry_t;

typedef struct pre_entry {
    uint32_t pre_id;
    synapse_t *head;
    struct pre_entry *next;
} pre_entry_t;

static post_entry_t *g_post_index = NULL;
static pre_entry_t *g_pre_index = NULL;
static synapse_t *g_active_trace_head = NULL;

static post_entry_t *_find_post(uint32_t post_id) {
    post_entry_t *e = g_post_index;
    while (e != NULL) {
        if (e->post_id == post_id) return e;
        e = e->next;
    }
    return NULL;
}

static pre_entry_t *_find_pre(uint32_t pre_id) {
    pre_entry_t *e = g_pre_index;
    while (e != NULL) {
        if (e->pre_id == pre_id) return e;
        e = e->next;
    }
    return NULL;
}

static post_entry_t *_find_or_create_post(uint32_t post_id) {
    post_entry_t *e = _find_post(post_id);
    if (e != NULL) return e;
    e = (post_entry_t *) sark_alloc(1, sizeof(post_entry_t));
    if (e == NULL) return NULL;
    e->post_id = post_id;
    e->head = NULL;
    e->next = g_post_index;
    g_post_index = e;
    return e;
}

static pre_entry_t *_find_or_create_pre(uint32_t pre_id) {
    pre_entry_t *e = _find_pre(pre_id);
    if (e != NULL) return e;
    e = (pre_entry_t *) sark_alloc(1, sizeof(pre_entry_t));
    if (e == NULL) return NULL;
    e->pre_id = pre_id;
    e->head = NULL;
    e->next = g_pre_index;
    g_pre_index = e;
    return e;
}

static int32_t _clip_weight(int32_t weight) {
    if (weight > MAX_WEIGHT) return MAX_WEIGHT;
    if (weight < MIN_WEIGHT) return MIN_WEIGHT;
    return weight;
}

static void _drop_empty_post_entry(uint32_t post_id) {
    post_entry_t **pp = &g_post_index;
    while (*pp != NULL) {
        post_entry_t *e = *pp;
        if (e->post_id == post_id) {
            if (e->head == NULL) {
                *pp = e->next;
                sark_free(e);
            }
            return;
        }
        pp = &e->next;
    }
}

static void _drop_empty_pre_entry(uint32_t pre_id) {
    pre_entry_t **pp = &g_pre_index;
    while (*pp != NULL) {
        pre_entry_t *e = *pp;
        if (e->pre_id == pre_id) {
            if (e->head == NULL) {
                *pp = e->next;
                sark_free(e);
            }
            return;
        }
        pp = &e->next;
    }
}

static void _unlink_from_post(synapse_t *target) {
    post_entry_t *pe = _find_post(target->post_id);
    if (pe == NULL) return;
    synapse_t **pp = &pe->head;
    while (*pp != NULL) {
        if (*pp == target) {
            *pp = target->next_post;
            target->next_post = NULL;
            _drop_empty_post_entry(target->post_id);
            return;
        }
        pp = &((*pp)->next_post);
    }
}

static void _unlink_from_pre(synapse_t *target) {
    pre_entry_t *pe = _find_pre(target->pre_id);
    if (pe == NULL) return;
    synapse_t **pp = &pe->head;
    while (*pp != NULL) {
        if (*pp == target) {
            *pp = target->next_pre;
            target->next_pre = NULL;
            _drop_empty_pre_entry(target->pre_id);
            return;
        }
        pp = &((*pp)->next_pre);
    }
}

static void _unlink_from_active(synapse_t *target) {
    if (!target->active_trace) return;
    synapse_t **pp = &g_active_trace_head;
    while (*pp != NULL) {
        if (*pp == target) {
            *pp = target->next_active;
            target->next_active = NULL;
            target->active_trace = 0;
            if (g_active_trace_count > 0) g_active_trace_count--;
            return;
        }
        pp = &((*pp)->next_active);
    }
    target->active_trace = 0;
}

static void _activate_trace(synapse_t *s) {
    if (s->active_trace) return;
    s->next_active = g_active_trace_head;
    g_active_trace_head = s;
    s->active_trace = 1;
    g_active_trace_count++;
}

static void _free_synapse(synapse_t *s) {
    uint32_t pre_id = s->pre_id;
    uint32_t post_id = s->post_id;
    _unlink_from_active(s);
    _unlink_from_post(s);
    _unlink_from_pre(s);
    sark_free(s);
    if (g_synapse_count > 0) g_synapse_count--;
    _drop_empty_post_entry(post_id);
    _drop_empty_pre_entry(pre_id);
}

static synapse_t *_find_synapse(uint32_t pre_id, uint32_t post_id) {
    pre_entry_t *pe = _find_pre(pre_id);
    if (pe == NULL) return NULL;
    synapse_t *s = pe->head;
    while (s != NULL) {
        if (s->post_id == post_id) return s;
        s = s->next_pre;
    }
    return NULL;
}

// ------------------------------------------------------------------
// API
// ------------------------------------------------------------------

int synapse_create(uint32_t pre_id, uint32_t post_id, int32_t weight, uint32_t delay) {
    post_entry_t *post = _find_or_create_post(post_id);
    pre_entry_t *pre = _find_or_create_pre(pre_id);
    if (post == NULL || pre == NULL) return -1;

    synapse_t *s = (synapse_t *) sark_alloc(1, sizeof(synapse_t));
    if (s == NULL) return -1;

    s->pre_id = pre_id;
    s->post_id = post_id;
    s->weight = _clip_weight(weight);
    s->eligibility_trace = 0;
    s->delay = delay;
    s->active_trace = 0;
    s->next_active = NULL;

    s->next_post = post->head;
    post->head = s;
    s->next_pre = pre->head;
    pre->head = s;

    g_synapse_count++;
    return 0;
}

int synapse_remove(uint32_t pre_id, uint32_t post_id) {
    synapse_t *s = _find_synapse(pre_id, post_id);
    if (s == NULL) return -1;
    _free_synapse(s);
    return 0;
}

void synapse_deliver_spike(uint32_t pre_id) {
    g_last_delivery_visits = 0;
    pre_entry_t *pe = _find_pre(pre_id);
    if (pe == NULL) return;

    synapse_t *s = pe->head;
    while (s != NULL) {
        g_last_delivery_visits++;
        int32_t trace = s->eligibility_trace + DEFAULT_TRACE_INCREMENT;
        if (trace > MAX_ELIGIBILITY_TRACE) trace = MAX_ELIGIBILITY_TRACE;
        s->eligibility_trace = trace;
        _activate_trace(s);
        neuron_add_input(s->post_id, s->weight);
        s = s->next_pre;
    }
}

void synapse_decay_traces_all(int32_t decay_factor) {
    g_last_decay_visits = 0;
    synapse_t **pp = &g_active_trace_head;
    while (*pp != NULL) {
        synapse_t *s = *pp;
        g_last_decay_visits++;
        s->eligibility_trace = FP_MUL(s->eligibility_trace, decay_factor);
        if (s->eligibility_trace <= 1) {
            s->eligibility_trace = 0;
            *pp = s->next_active;
            s->next_active = NULL;
            s->active_trace = 0;
            if (g_active_trace_count > 0) g_active_trace_count--;
        } else {
            pp = &s->next_active;
        }
    }
}

void synapse_modulate_all(int32_t dopamine_level) {
    g_last_modulation_visits = 0;
    synapse_t *s = g_active_trace_head;
    while (s != NULL) {
        g_last_modulation_visits++;
        int32_t delta_w = FP_MUL(dopamine_level, s->eligibility_trace);
        s->weight = _clip_weight(s->weight + delta_w);
        s = s->next_active;
    }
}

void synapse_remove_incident(uint32_t neuron_id) {
    uint8_t removed = 0;
    do {
        removed = 0;
        post_entry_t *pe = g_post_index;
        while (pe != NULL && !removed) {
            synapse_t *s = pe->head;
            while (s != NULL) {
                if (s->pre_id == neuron_id || s->post_id == neuron_id) {
                    _free_synapse(s);
                    removed = 1;
                    break;
                }
                s = s->next_post;
            }
            if (!removed) {
                pe = pe->next;
            }
        }
    } while (removed);
}

void synapse_reset_all(void) {
    while (g_post_index != NULL) {
        post_entry_t *pe = g_post_index;
        synapse_t *s = pe->head;
        while (s != NULL) {
            synapse_t *next = s->next_post;
            sark_free(s);
            s = next;
        }
        g_post_index = pe->next;
        sark_free(pe);
    }
    while (g_pre_index != NULL) {
        pre_entry_t *pe = g_pre_index;
        g_pre_index = pe->next;
        sark_free(pe);
    }
    g_active_trace_head = NULL;
    g_synapse_count = 0;
    g_active_trace_count = 0;
    g_last_delivery_visits = 0;
    g_last_decay_visits = 0;
    g_last_modulation_visits = 0;
}

uint32_t synapse_count(void) {
    return g_synapse_count;
}

uint32_t synapse_active_trace_count(void) {
    return g_active_trace_count;
}

uint32_t synapse_last_delivery_visit_count(void) {
    return g_last_delivery_visits;
}

uint32_t synapse_last_decay_visit_count(void) {
    return g_last_decay_visits;
}

uint32_t synapse_last_modulation_visit_count(void) {
    return g_last_modulation_visits;
}

int synapse_get_weight(uint32_t pre_id, uint32_t post_id, int32_t *weight_out) {
    synapse_t *s = _find_synapse(pre_id, post_id);
    if (s == NULL) return -1;
    if (weight_out != 0) *weight_out = s->weight;
    return 0;
}

int synapse_get_eligibility_trace(uint32_t pre_id, uint32_t post_id, int32_t *trace_out) {
    synapse_t *s = _find_synapse(pre_id, post_id);
    if (s == NULL) return -1;
    if (trace_out != 0) *trace_out = s->eligibility_trace;
    return 0;
}
