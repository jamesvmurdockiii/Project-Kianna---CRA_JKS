/* Stub implementations for spin1_api functions that need shared state across
 * translation units (e.g., spin1_msg_get() must return the same buffer to
 * both the caller in host_interface.c and the test inspector). */
#include "spin1_api.h"

sdp_msg_t g_spin1_msg_stub;
sdp_msg_t g_test_last_sdp_msg;
uint8_t    g_test_last_sdp_msg_valid = 0;

sdp_msg_t *spin1_msg_get(void) {
    return &g_spin1_msg_stub;
}

void spin1_msg_free(sdp_msg_t *msg) {
    (void)msg;
}

void spin1_send_sdp_msg(sdp_msg_t *msg, uint32_t timeout) {
    (void)timeout;
    if (msg != NULL) {
        memcpy(&g_test_last_sdp_msg, msg, sizeof(sdp_msg_t));
        g_test_last_sdp_msg_valid = 1;
    }
}

void spin1_send_mc_packet(uint32_t key, uint32_t data, uint32_t with_payload) {
    (void)key;
    (void)data;
    (void)with_payload;
}

void spin1_set_timer_tick(uint32_t period) {
    (void)period;
}

void spin1_callback_on(uint32_t event, callback_t callback, int priority) {
    (void)event;
    (void)callback;
    (void)priority;
}

void spin1_start(uint32_t sync_mode) {
    (void)sync_mode;
}
