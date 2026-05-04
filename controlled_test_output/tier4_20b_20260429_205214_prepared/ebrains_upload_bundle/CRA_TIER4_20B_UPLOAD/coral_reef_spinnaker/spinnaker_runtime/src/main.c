/*!
 * \file main.c
 * \brief Coral Reef SpiNNaker runtime — entry point.
 *
 * This is a stand-alone SpiNNaker application that runs on a single
 * ARM968 core.  It uses spin1_api for event scheduling and sark.h
 * for SDRAM heap management.
 *
 * Build with:
 *     make
 * which produces build/coral_reef.aplx (and .elf) ready for ybug
 * or SpiNNMan loading.
 */
#include <sark.h>
#include <spin1_api.h>
#include "config.h"
#include "neuron_manager.h"
#include "synapse_manager.h"
#include "host_interface.h"
#include "router.h"

// ------------------------------------------------------------------
// Global state
// ------------------------------------------------------------------
uint32_t g_app_id      = APP_ID;
uint32_t g_timestep    = 0;
uint32_t g_dopamine_level = 0;  // s16.15 fixed point

// ------------------------------------------------------------------
// Forward declarations
// ------------------------------------------------------------------
static void timer_callback(uint ticks, uint unused);
static void mc_packet_callback(uint key, uint payload);
static void sdp_callback(uint mailbox, uint port);

// ------------------------------------------------------------------
// Callbacks
// ------------------------------------------------------------------

/*! Timer tick — advances simulation by one timestep. */
static void timer_callback(uint ticks, uint unused) {
    (void)unused;
    g_timestep = ticks;

    // Update all neurons (LIF integration, spike emission)
    neuron_update_all(g_timestep);

    // Optional: apply global dopamine modulation to synapses
    // In a full STDP+DA model this would update eligibility traces.
    if (g_dopamine_level != 0) {
        synapse_modulate_all(g_dopamine_level);
    }
}

/*! Multicast packet RX — spike from another neuron or external source. */
static void mc_packet_callback(uint key, uint payload) {
    (void)payload;  // payload can carry weight or timestamp; ignored for PoC

    // key format expected:  (app_id << 24) | neuron_id
    uint32_t app_id = (key >> 24) & 0xFF;
    if (app_id != g_app_id) {
        return;  // not our application
    }
    uint32_t neuron_id = key & 0x00FFFFFF;

    // Deliver spike to all post-synaptic targets of this neuron
    synapse_deliver_spike(neuron_id);
}

/*! SDP packet RX — host commands (birth, death, dopamine, etc). */
static void sdp_callback(uint mailbox, uint port) {
    sdp_rx_callback(mailbox, port);
}

// ------------------------------------------------------------------
// Public helpers used by other modules
// ------------------------------------------------------------------

uint32_t get_app_id(void) {
    return g_app_id;
}

/*! Emit a multicast spike packet for the given neuron id.
    Called from neuron_update_all() when a neuron fires. */
void emit_spike(uint32_t neuron_id) {
    uint32_t key = (g_app_id << 24) | (neuron_id & 0x00FFFFFF);
    // payload = current timestep (can be used for STDP delay calc)
    spin1_send_mc_packet(key, g_timestep, WITH_PAYLOAD);
}

// ------------------------------------------------------------------
// Entry point
// ------------------------------------------------------------------

void c_main(void) {
    // Inform the monitor we are running
    sark_cpu_state(CPU_STATE_RUN);

    // Initialise subsystems
    neuron_mgr_init();
    router_init();
    host_if_init();

    // Set timer tick period (in microseconds)
    spin1_set_timer_tick(TIMER_PERIOD_US);

    // Register callbacks
    spin1_callback_on(TIMER_TICK,   timer_callback,     1);
    spin1_callback_on(MC_PACKET_RX, mc_packet_callback, 0);
    spin1_callback_on(SDP_PACKET_RX, sdp_callback,      0);

    // Enter the event loop — never returns
    spin1_start(SYNC_NOWAIT);
}
