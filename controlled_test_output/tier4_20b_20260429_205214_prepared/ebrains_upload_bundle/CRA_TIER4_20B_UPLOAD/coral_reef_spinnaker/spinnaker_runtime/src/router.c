/*!
 * \file router.c
 * \brief Dynamic routing table entry allocation per neuron.
 *
 * Uses sark_router_alloc() / sark_router_free() to manage exact-match
 * entries in the chip-level multicast router.  Each neuron gets one
 * entry that matches its full 32-bit spike key and routes to the local
 * application core (determined at runtime via sark_core_id()).
 *
 * Because sark_router_alloc() returns an index into the 1024-entry CAM,
 * we keep a small software index (also a linked list in SDRAM) to map
 * neuron_id -> CAM index so that death can free the correct entry.
 */
#include "router.h"
#include "config.h"
#include <sark.h>

// ------------------------------------------------------------------
// Internal index: maps neuron_id -> CAM entry index
// ------------------------------------------------------------------
typedef struct route_entry {
    uint32_t neuron_id;
    uint32_t cam_index;
    struct route_entry *next;
} route_entry_t;

static route_entry_t *g_route_list = NULL;
static uint32_t       g_route_count = 0;
static uint32_t       g_app_id = 0;

// ------------------------------------------------------------------
// Extern
// ------------------------------------------------------------------
extern uint32_t get_app_id(void);

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

static route_entry_t *_find_route(uint32_t neuron_id) {
    route_entry_t *e = g_route_list;
    while (e != NULL) {
        if (e->neuron_id == neuron_id) return e;
        e = e->next;
    }
    return NULL;
}

// ------------------------------------------------------------------
// Public API
// ------------------------------------------------------------------

void router_init(void) {
    g_route_list = NULL;
    g_route_count = 0;
    g_app_id = get_app_id();
}

int router_add_neuron(uint32_t neuron_id) {
    if (_find_route(neuron_id) != NULL) {
        return -1;  // already routed
    }

    // Build the exact-match key for this neuron's spikes
    uint32_t key  = MAKE_KEY(g_app_id, neuron_id);
    uint32_t mask = 0xFFFFFFFF;

    // Route to the core we are actually running on.
    // Core 0 is the monitor; application cores are 1–17.
    uint32_t route = ROUTE_CORE(sark_core_id());

    // Allocate a CAM entry via SARK
    uint32_t cam_index = sark_router_alloc(key, mask, route);
    if (cam_index == 0xFFFFFFFF) {
        return -1;  // CAM full
    }

    // Record in our software index
    route_entry_t *e = (route_entry_t *) sark_alloc(1, sizeof(route_entry_t));
    if (e == NULL) {
        // Allocation failed — clean up the CAM entry
        sark_router_free(cam_index);
        return -1;
    }
    e->neuron_id = neuron_id;
    e->cam_index = cam_index;
    e->next      = g_route_list;
    g_route_list = e;
    g_route_count++;
    return 0;
}

int router_remove_neuron(uint32_t neuron_id) {
    route_entry_t **pp = &g_route_list;
    while (*pp != NULL) {
        route_entry_t *e = *pp;
        if (e->neuron_id == neuron_id) {
            *pp = e->next;
            sark_router_free(e->cam_index);
            sark_free(e);
            g_route_count--;
            return 0;
        }
        pp = &e->next;
    }
    return -1;  // not found
}

void router_reset_all(void) {
    while (g_route_list != NULL) {
        route_entry_t *e = g_route_list;
        g_route_list = e->next;
        sark_router_free(e->cam_index);
        sark_free(e);
    }
    g_route_count = 0;
}

uint32_t router_route_count(void) {
    return g_route_count;
}
