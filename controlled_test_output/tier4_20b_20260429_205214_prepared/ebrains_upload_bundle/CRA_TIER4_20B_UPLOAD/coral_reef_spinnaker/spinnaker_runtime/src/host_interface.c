/*!
 * \file host_interface.c
 * \brief SDP command dispatcher.
 */
#include "host_interface.h"
#include "neuron_manager.h"
#include "synapse_manager.h"
#include "router.h"
#include <sark.h>
#include <spin1_api.h>

// ------------------------------------------------------------------
// Externs
// ------------------------------------------------------------------
extern uint32_t g_timestep;
extern uint32_t g_dopamine_level;

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

static inline int32_t _read_s32(uint8_t *p) {
    return (int32_t)(p[0] | (p[1] << 8) | (p[2] << 16) | (p[3] << 24));
}

// ------------------------------------------------------------------
// Command handlers
// ------------------------------------------------------------------

static void _handle_birth(sdp_msg_t *msg) {
    if (msg->length < 13) return;  // 8-byte header + cmd + 4-byte id
    uint32_t id = _read_s32(&msg->data[1]);
    neuron_t *n = neuron_birth(id);
    uint8_t reply[8];
    reply[0] = CMD_BIRTH;
    reply[1] = (n != NULL) ? 0 : 1;  // 0 = success
    reply[2] = (uint8_t)(id & 0xFF);
    reply[3] = (uint8_t)((id >> 8) & 0xFF);
    reply[4] = (uint8_t)((id >> 16) & 0xFF);
    reply[5] = (uint8_t)((id >> 24) & 0xFF);
    reply[6] = (uint8_t)(neuron_count() & 0xFF);
    reply[7] = (uint8_t)((neuron_count() >> 8) & 0xFF);
    sdp_send_reply(msg, reply, 8);
}

static void _handle_death(sdp_msg_t *msg) {
    if (msg->length < 13) return;
    uint32_t id = _read_s32(&msg->data[1]);
    int rc = neuron_death(id);
    uint8_t reply[4];
    reply[0] = CMD_DEATH;
    reply[1] = (rc == 0) ? 0 : 1;
    reply[2] = (uint8_t)(neuron_count() & 0xFF);
    reply[3] = (uint8_t)((neuron_count() >> 8) & 0xFF);
    sdp_send_reply(msg, reply, 4);
}

static void _handle_dopamine(sdp_msg_t *msg) {
    if (msg->length < 13) return;
    // Dopamine level as s16.15 fixed point
    g_dopamine_level = _read_s32(&msg->data[1]);
    uint8_t reply[6];
    reply[0] = CMD_DOPAMINE;
    reply[1] = 0;  // ack
    reply[2] = (uint8_t)(g_dopamine_level & 0xFF);
    reply[3] = (uint8_t)((g_dopamine_level >> 8) & 0xFF);
    reply[4] = (uint8_t)((g_dopamine_level >> 16) & 0xFF);
    reply[5] = (uint8_t)((g_dopamine_level >> 24) & 0xFF);
    sdp_send_reply(msg, reply, 6);
}

static void _handle_read_spikes(sdp_msg_t *msg) {
    // Minimal reply: global neuron count + current timestep only.
    // A full per-neuron dump would need SDP fragmentation or a
    // larger transfer mechanism (e.g. DMA to host SDRAM).
    uint8_t reply[5];
    reply[0] = CMD_READ_SPIKES;
    uint32_t nc = neuron_count();
    reply[1] = (uint8_t)(nc & 0xFF);
    reply[2] = (uint8_t)((nc >> 8) & 0xFF);
    reply[3] = (uint8_t)(g_timestep & 0xFF);
    reply[4] = (uint8_t)((g_timestep >> 8) & 0xFF);
    sdp_send_reply(msg, reply, 5);
}

static void _handle_create_syn(sdp_msg_t *msg) {
    if (msg->length < 21) return;  // header + cmd + pre + post + weight
    uint32_t pre  = _read_s32(&msg->data[1]);
    uint32_t post = _read_s32(&msg->data[5]);
    int32_t  w    = _read_s32(&msg->data[9]);
    int rc = synapse_create(pre, post, w, DEFAULT_SYN_DELAY);
    uint8_t reply[2];
    reply[0] = CMD_CREATE_SYN;
    reply[1] = (rc == 0) ? 0 : 1;
    sdp_send_reply(msg, reply, 2);
}

static void _handle_remove_syn(sdp_msg_t *msg) {
    if (msg->length < 17) return;  // header + cmd + pre + post
    uint32_t pre  = _read_s32(&msg->data[1]);
    uint32_t post = _read_s32(&msg->data[5]);
    int rc = synapse_remove(pre, post);
    uint8_t reply[2];
    reply[0] = CMD_REMOVE_SYN;
    reply[1] = (rc == 0) ? 0 : 1;
    sdp_send_reply(msg, reply, 2);
}

static void _handle_reset(sdp_msg_t *msg) {
    router_reset_all();
    neuron_reset_all();
    synapse_reset_all();
    g_dopamine_level = 0;
    g_timestep = 0;
    uint8_t reply[2];
    reply[0] = CMD_RESET;
    reply[1] = 0;
    sdp_send_reply(msg, reply, 2);
}

// ------------------------------------------------------------------
// Public API
// ------------------------------------------------------------------

void host_if_init(void) {
    // SDP callback is registered in main.c via spin1_callback_on
}

void sdp_rx_callback(uint mailbox, uint port) {
    sdp_msg_t *msg = (sdp_msg_t *) mailbox;
    uint8_t cmd = msg->data[0];
    switch (cmd) {
        case CMD_BIRTH:       _handle_birth(msg);       break;
        case CMD_DEATH:       _handle_death(msg);       break;
        case CMD_DOPAMINE:    _handle_dopamine(msg);    break;
        case CMD_READ_SPIKES: _handle_read_spikes(msg); break;
        case CMD_CREATE_SYN:  _handle_create_syn(msg);  break;
        case CMD_REMOVE_SYN:  _handle_remove_syn(msg);  break;
        case CMD_RESET:       _handle_reset(msg);       break;
        default:
            // Unknown command — send NAK
            {
                uint8_t nak[2] = {cmd, 0xFF};
                sdp_send_reply(msg, nak, 2);
            }
            break;
    }
    spin1_msg_free(msg);
}

void sdp_send_reply(sdp_msg_t *req, const uint8_t *payload, uint8_t payload_len) {
    sdp_msg_t *reply = (sdp_msg_t *) spin1_msg_get();
    if (reply == NULL) return;

    // Swap source/dest so the reply goes back to the host
    reply->dest_y    = req->src_y;
    reply->dest_x    = req->src_x;
    reply->dest_port = req->src_port;
    reply->dest_cpu  = req->src_cpu;
    reply->src_y     = req->dest_y;
    reply->src_x     = req->dest_x;
    reply->src_port  = req->dest_port;
    reply->src_cpu   = req->dest_cpu;
    reply->flags     = 0x07;  // reply flag
    reply->tag       = req->tag;

    uint8_t len = payload_len;
    if (len > 255) len = 255;
    reply->length = len + 8;  // SDP header (8 bytes) + payload
    sark_memcpy(reply->data, payload, len);

    spin1_send_sdp_msg(reply, 1);
    spin1_msg_free(reply);
}
