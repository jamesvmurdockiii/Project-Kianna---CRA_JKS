/*!
 * \file host_interface.h
 * \brief SDP packet parsing and host command dispatch.
 *
 * Command opcodes are defined in config.h (single source of truth).
 * This header only declares the C callback API.
 */
#ifndef __HOST_INTERFACE_H__
#define __HOST_INTERFACE_H__

#include <sark.h>
#include "config.h"

// ------------------------------------------------------------------
// SDP callback registration / handler
// ------------------------------------------------------------------

/*! Register the SDP RX callback with spin1_api. */
void host_if_init(void);

/*! Called from spin1_api when an SDP packet arrives for us.
    mailbox is actually the address of an sdp_msg_t in DTCM. */
void sdp_rx_callback(uint mailbox, uint port);

/*! Send a reply SDP packet back to the host.
    payload_len must be ≤ 256 bytes. */
void sdp_send_reply(sdp_msg_t *req, const uint8_t *payload, uint8_t payload_len);

#endif // __HOST_INTERFACE_H__
