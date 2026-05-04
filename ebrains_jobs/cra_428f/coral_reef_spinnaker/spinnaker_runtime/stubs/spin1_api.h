/* Stub spin1_api.h for host-side syntax checking */
#ifndef __SPIN1_API_H__
#define __SPIN1_API_H__

#include <stdint.h>
#include "sark.h"

#define TIMER_TICK_PERIOD  1000
#define MC_PACKET_RECEIVED   0
#define TIMER_TICK           2
#define SDP_PACKET_RX        3
#define MCPL_PACKET_RECEIVED 5
#define WITH_PAYLOAD       1
#define SYNC_NOWAIT        0

typedef void (*callback_t)(uint32_t, uint32_t);

extern sdp_msg_t g_spin1_msg_stub;
extern sdp_msg_t g_test_last_sdp_msg;
extern uint8_t   g_test_last_sdp_msg_valid;

sdp_msg_t *spin1_msg_get(void);
void spin1_msg_free(sdp_msg_t *msg);
void spin1_send_sdp_msg(sdp_msg_t *msg, uint32_t timeout);
void spin1_send_mc_packet(uint32_t key, uint32_t data, uint32_t with_payload);
void spin1_set_timer_tick(uint32_t period);
void spin1_callback_on(uint32_t event, callback_t callback, int priority);
void spin1_start(uint32_t sync_mode);

#endif
