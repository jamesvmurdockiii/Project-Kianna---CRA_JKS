/*!
 * \file config.h
 * \brief Coral Reef Architecture — SpiNNaker Runtime Configuration
 *
 * SINGLE SOURCE OF TRUTH for the custom C runtime protocol.
 * Any C file that needs constants, command codes, key layout, or
 * fixed-point helpers includes this header and ONLY this header.
 */
#ifndef __CONFIG_H__
#define __CONFIG_H__

#include <stdint.h>

// ------------------------------------------------------------------
// Application identity
// ------------------------------------------------------------------
#define APP_ID          0x01   // Top 8 bits of every multicast key

// ------------------------------------------------------------------
// Fixed-point arithmetic (s16.15)
// ------------------------------------------------------------------
#define FP_SHIFT      15
#define FP_ONE        (1 << FP_SHIFT)          // 1.0  = 32768
#define FP_HALF       (1 << (FP_SHIFT - 1))    // 0.5  = 16384
#define FP_FROM_FLOAT(f)  ((int32_t)((f) * (float)FP_ONE))
#define FP_TO_FLOAT(v)    ((float)(v) / (float)FP_ONE)
#define FP_MUL(a, b)    ((int32_t)(((int64_t)(a) * (int64_t)(b)) >> FP_SHIFT))
#define FP_DIV(a, b)    (((int32_t)(a) << FP_SHIFT) / (int32_t)(b))

// ------------------------------------------------------------------
// Simulation parameters
// ------------------------------------------------------------------
#define TIMESTEP_MS       1          // 1 ms biological timestep
#define TIMER_PERIOD_US   1000       // 1000 us = 1 ms wall-clock
#define MAX_NEURONS       1024       // Hard ceiling per core (safety)
#define MAX_SYNAPSES      8192       // Hard ceiling per core (safety)
#define MAX_CONTEXT_SLOTS 8          // Bounded keyed-state slots per core
#define MAX_ROUTE_SLOTS 8            // Bounded keyed route-state slots per core
#define MAX_MEMORY_SLOTS 8           // Bounded keyed memory/working-state slots per core
#define MAX_PENDING_HORIZONS 128     // Bounded delayed-credit queue per core
#define DEFAULT_TAU_M     FP_FROM_FLOAT(20.0f)
#define DEFAULT_V_THRESH  FP_FROM_FLOAT(-55.0f)
#define DEFAULT_V_RESET   FP_FROM_FLOAT(-70.0f)
#define DEFAULT_V_REST    FP_FROM_FLOAT(-65.0f)
#define DEFAULT_I_OFFSET  0
#define DEFAULT_TAU_REFR  2          // 2 ms refractory period

// ------------------------------------------------------------------
// Synapse defaults
// ------------------------------------------------------------------
#define DEFAULT_SYN_DELAY 1          // 1 timestep delay
#define MIN_WEIGHT        FP_FROM_FLOAT(-1.0f)
#define MAX_WEIGHT        FP_FROM_FLOAT( 1.0f)
#define DEFAULT_ELIGIBILITY_DECAY FP_FROM_FLOAT(0.995f)
#define DEFAULT_TRACE_INCREMENT   FP_FROM_FLOAT(1.0f)
#define MAX_ELIGIBILITY_TRACE     FP_FROM_FLOAT(1.0f)

// ------------------------------------------------------------------
// SDP host command codes
//
// These MUST match python_host/colony_controller.py exactly.
// ------------------------------------------------------------------
#define CMD_BIRTH        1
#define CMD_DEATH        2
#define CMD_DOPAMINE     3
#define CMD_READ_SPIKES  4
#define CMD_CREATE_SYN   5
#define CMD_REMOVE_SYN   6
#define CMD_RESET        7
#define CMD_READ_STATE   8
#define CMD_SCHEDULE_PENDING 9
#define CMD_MATURE_PENDING   10
#define CMD_WRITE_CONTEXT    11
#define CMD_READ_CONTEXT     12
#define CMD_SCHEDULE_CONTEXT_PENDING 13
#define CMD_WRITE_ROUTE      14
#define CMD_READ_ROUTE       15
#define CMD_SCHEDULE_ROUTED_CONTEXT_PENDING 16
#define CMD_WRITE_ROUTE_SLOT 17
#define CMD_READ_ROUTE_SLOT  18
#define CMD_SCHEDULE_KEYED_ROUTE_CONTEXT_PENDING 19
#define CMD_WRITE_MEMORY_SLOT 20
#define CMD_READ_MEMORY_SLOT  21
#define CMD_SCHEDULE_MEMORY_ROUTE_CONTEXT_PENDING 22
#define CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING 23

// ------------------------------------------------------------------
// SpiNNaker multicast key layout
//
// Single-core PoC:  app_id (8) | neuron_id (24)
// Multi-core future: app_id (8) | core_id (8) | neuron_id (16)
// ------------------------------------------------------------------
#define KEY_APP_SHIFT     24
#define KEY_NEURON_MASK   0x00FFFFFF

#define MAKE_KEY(app, nid) \
    (((app) << KEY_APP_SHIFT) | ((nid) & KEY_NEURON_MASK))

#define EXTRACT_NEURON_ID(key)  ((key) & KEY_NEURON_MASK)

#define MAX_SCHEDULE_ENTRIES 64

#define CMD_RUN_CONTINUOUS       24
#define CMD_PAUSE                25
#define CMD_WRITE_SCHEDULE_ENTRY 26

// ------------------------------------------------------------------
// 4.25B inter-core split opcodes
// ------------------------------------------------------------------
#define CMD_SCHEDULE_PENDING_SPLIT 30
#define CMD_MATURE_ACK_SPLIT       31

#endif // __CONFIG_H__
