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

uint32_t g_test_last_mc_key = 0;
uint32_t g_test_last_mc_payload = 0;
uint32_t g_test_last_mc_with_payload = 0;
uint32_t g_test_mc_packet_count = 0;
uint32_t g_test_mc_keys[8];
uint32_t g_test_mc_payloads[8];
uint32_t g_test_mc_with_payloads[8];

void spin1_send_mc_packet(uint32_t key, uint32_t data, uint32_t with_payload) {
    g_test_last_mc_key = key;
    g_test_last_mc_payload = data;
    g_test_last_mc_with_payload = with_payload;
    if (g_test_mc_packet_count < 8) {
        g_test_mc_keys[g_test_mc_packet_count] = key;
        g_test_mc_payloads[g_test_mc_packet_count] = data;
        g_test_mc_with_payloads[g_test_mc_packet_count] = with_payload;
    }
    g_test_mc_packet_count++;
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
