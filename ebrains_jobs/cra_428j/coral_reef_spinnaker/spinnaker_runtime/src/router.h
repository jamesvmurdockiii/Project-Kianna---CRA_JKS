/*!
 * \file router.h
 * \brief Dynamic multicast routing table management.
 *
 * SpiNNaker's router is a ternary CAM with 1024 entries per chip.
 * Each entry matches on a 32-bit key + 32-bit mask and outputs to
 * a set of links and/or local cores.
 *
 * For the Coral Reef runtime we allocate one route per neuron birth:
 *   key  = (app_id << 24) | neuron_id
 *   mask = 0xFFFFFFFF            (exact match)
 *   route = local core + optional external links
 *
 * On death the route is freed back to the router CAM.
 *
 * NOTE: Virtual core 0 is the monitor processor. Application cores
 * are numbered 1–17.  We route to the current application core via
 * sark_core_id() rather than hard-coding core 1.
 */
#ifndef __ROUTER_H__
#define __ROUTER_H__

#include <stdint.h>
#include <sark.h>

// ------------------------------------------------------------------
// Route direction bitmasks (same as sark.h RK_* constants)
// ------------------------------------------------------------------
#define ROUTE_E   (1 << 0)   // East
#define ROUTE_NE  (1 << 1)   // North-East
#define ROUTE_N   (1 << 2)   // North
#define ROUTE_W   (1 << 3)   // West
#define ROUTE_SW  (1 << 4)   // South-West
#define ROUTE_S   (1 << 5)   // South
#ifndef MC_CORE_ROUTE
#define MC_CORE_ROUTE(n) (1 << (6 + (n)))  // Core n (0-17)
#endif
#define ROUTE_CORE(n) MC_CORE_ROUTE(n)

// ------------------------------------------------------------------
// API
// ------------------------------------------------------------------

/*! Initialise router subsystem (call once from c_main). */
void router_init(void);

/*! Allocate a routing table entry for the given neuron id.
    Returns 0 on success, -1 if the CAM is full. */
int router_add_neuron(uint32_t neuron_id);

/*! Free the routing table entry for the given neuron id.
    Returns 0 on success, -1 if not found. */
int router_remove_neuron(uint32_t neuron_id);

/*! Remove every Coral Reef route from the router CAM. */
void router_reset_all(void);

/*! Return number of active routes. */
uint32_t router_route_count(void);

#endif // __ROUTER_H__
