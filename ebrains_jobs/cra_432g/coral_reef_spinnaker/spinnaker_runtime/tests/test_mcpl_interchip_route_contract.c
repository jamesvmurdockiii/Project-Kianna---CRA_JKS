/*
 * Tier 4.32d-r1 MCPL inter-chip route contract tests.
 *
 * These tests prove source-level route-table ownership before any EBRAINS
 * two-chip package is allowed. The packet send API still leaves delivery to
 * the router table; this gate verifies the table can be built with explicit
 * chip-link routes for the split-role single-shard smoke.
 */

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "config.h"
#include "router.h"
#include "state_manager.h"
#include "spin1_api.h"

uint32_t g_timestep = 0;

extern uint32_t g_test_rtr_mc_set_count;
extern uint32_t g_test_rtr_keys[32];
extern uint32_t g_test_rtr_masks[32];
extern uint32_t g_test_rtr_routes[32];

static void reset_routes(void) {
    g_test_rtr_mc_set_count = 0;
    for (uint32_t i = 0; i < 32; i++) {
        g_test_rtr_keys[i] = 0;
        g_test_rtr_masks[i] = 0;
        g_test_rtr_routes[i] = 0;
    }
}

static uint32_t count_route(uint32_t key, uint32_t mask, uint32_t route) {
    uint32_t count = 0;
    for (uint32_t i = 0; i < g_test_rtr_mc_set_count && i < 32; i++) {
        if (g_test_rtr_keys[i] == key &&
            g_test_rtr_masks[i] == mask &&
            g_test_rtr_routes[i] == route) {
            count++;
        }
    }
    return count;
}

int main(void) {
    reset_routes();
#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
    cra_state_mcpl_init(4);
#else
    cra_state_mcpl_init(7);
#endif

#if defined(CRA_RUNTIME_PROFILE_LEARNING_CORE)
    printf("Tier 4.32d-r1 learning-core inter-chip route contract\n");
    uint32_t reply_mask = 0xFFF0F000;
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, 0, 0),
        reply_mask,
        MC_CORE_ROUTE(7)) == 1);
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, 0, 0),
        reply_mask,
        MC_CORE_ROUTE(7)) == 1);

#if CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE
    uint32_t request_mask = 0xFFFFF000;
    uint32_t link_route = CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE;
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_CONTEXT, 0),
        request_mask,
        link_route) == 1);
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_ROUTE, 0),
        request_mask,
        link_route) == 1);
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_MEMORY, 0),
        request_mask,
        link_route) == 1);
    printf("  PASS: learning core installs outbound request link routes\n");
#else
    assert(g_test_rtr_mc_set_count == 2);
    printf("  PASS: learning core remains local-only without link macro\n");
#endif

#elif defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
    printf("Tier 4.32d-r1 state-core inter-chip route contract\n");
#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE)
    uint8_t lookup_type = LOOKUP_TYPE_CONTEXT;
#elif defined(CRA_RUNTIME_PROFILE_ROUTE_CORE)
    uint8_t lookup_type = LOOKUP_TYPE_ROUTE;
#else
    uint8_t lookup_type = LOOKUP_TYPE_MEMORY;
#endif

    uint32_t mask = 0xFFFFF000;
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, lookup_type, 0),
        mask,
        MC_CORE_ROUTE(4)) == 1);

#if CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE
    uint32_t link_route = CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE;
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, lookup_type, 0),
        mask,
        link_route) == 1);
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, lookup_type, 0),
        mask,
        link_route) == 1);
    printf("  PASS: state core installs local request route plus outbound reply link routes\n");
#else
    assert(g_test_rtr_mc_set_count == 1);
    printf("  PASS: state core remains request-local without link macro\n");
#endif
#else
    printf("Tier 4.32d-r1 route contract has no active runtime profile\n");
#endif

    return 0;
}
