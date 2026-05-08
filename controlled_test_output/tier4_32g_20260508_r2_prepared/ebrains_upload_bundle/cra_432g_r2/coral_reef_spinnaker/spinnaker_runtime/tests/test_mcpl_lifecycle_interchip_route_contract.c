/*
 * Tier 4.32g-r0 lifecycle MCPL inter-chip route contract tests.
 *
 * This is a local source/route gate only. It proves lifecycle event/trophic
 * request packets and active-mask/lineage sync packets can be assigned explicit
 * chip-link routes before any EBRAINS two-chip lifecycle package is allowed.
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
#if defined(CRA_RUNTIME_PROFILE_LIFECYCLE_CORE)
    cra_state_mcpl_init(4);
#else
    cra_state_mcpl_init(7);
#endif

    uint32_t mask = 0xFFF0F000;  // match app/msg/shard, ignore subtype and seq

#if defined(CRA_RUNTIME_PROFILE_LEARNING_CORE)
    printf("Tier 4.32g-r0 learning-core lifecycle route contract\n");

    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0),
        mask,
        MC_CORE_ROUTE(7)) == 1);

#if CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE
    uint32_t link_route = CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE;
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0),
        mask,
        link_route) == 1);
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0),
        mask,
        link_route) == 1);
    printf("  PASS: learning core installs outbound lifecycle request link routes\n");
#else
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0),
        mask,
        MC_CORE_ROUTE(7)) == 0);
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0),
        mask,
        MC_CORE_ROUTE(7)) == 0);
    printf("  PASS: learning core remains lifecycle-local without link macro\n");
#endif

#elif defined(CRA_RUNTIME_PROFILE_LIFECYCLE_CORE)
    printf("Tier 4.32g-r0 lifecycle-core inter-chip route contract\n");

    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0),
        mask,
        MC_CORE_ROUTE(4)) == 1);
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0),
        mask,
        MC_CORE_ROUTE(4)) == 1);

#if CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE
    uint32_t link_route = CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE;
    assert(count_route(
        MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0),
        mask,
        link_route) == 1);
    printf("  PASS: lifecycle core installs local request routes plus outbound sync link route\n");
#else
    assert(g_test_rtr_mc_set_count == 2);
    printf("  PASS: lifecycle core remains sync-local without link macro\n");
#endif

#else
    printf("Tier 4.32g-r0 lifecycle route contract has no active runtime profile\n");
#endif

    return 0;
}
