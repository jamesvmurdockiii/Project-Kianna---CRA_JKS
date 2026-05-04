/* Stub spin1_api.h for host-side syntax checking */
#ifndef __SPIN1_API_H__
#define __SPIN1_API_H__

#include <stdint.h>

#define TIMER_TICK_PERIOD  1000
#define TIMER_TICK         0
#define MC_PACKET_RX       1
#define SDP_PACKET_RX      2
#define MCPL_PACKET_RECEIVED 3
#define WITH_PAYLOAD       1
#define SYNC_NOWAIT        0

typedef void (*callback_t)(uint32_t, uint32_t);

static inline void spin1_set_timer_tick(uint32_t period) { (void)period; }
static inline void spin1_callback_on(uint32_t event, callback_t callback, int priority) { (void)event; (void)callback; (void)priority; }
static inline void spin1_start(uint32_t sync_mode) { (void)sync_mode; }
static inline void spin1_send_mc_packet(uint32_t key, uint32_t data, uint32_t with_payload) {
    (void)key; (void)data; (void)with_payload;
}
static inline void spin1_send_sdp_msg(sdp_msg_t *msg, uint32_t timeout) { (void)msg; (void)timeout; }
static inline sdp_msg_t *spin1_msg_get(void) { return NULL; }
static inline void spin1_msg_free(sdp_msg_t *msg) { (void)msg; }

#endif
