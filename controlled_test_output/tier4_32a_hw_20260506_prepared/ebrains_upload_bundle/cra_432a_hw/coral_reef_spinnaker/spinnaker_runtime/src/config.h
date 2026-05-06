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
#define MAX_CONTEXT_SLOTS 128        // Bounded keyed-state slots per core (expanded for regime-per-event tasks)
#define MAX_ROUTE_SLOTS 8            // Bounded keyed route-state slots per core
#define MAX_MEMORY_SLOTS 8           // Bounded keyed memory/working-state slots per core
#define MAX_PENDING_HORIZONS 128     // Bounded delayed-credit queue per core
#define MAX_LIFECYCLE_SLOTS 8        // Tier 4.30 static lifecycle pool; no dynamic birth/death allocation
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
#define SURPRISE_THRESHOLD        (2 * FP_ONE)  // Skip weight updates when |error| >= 2.0 (noisy trials)

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

#define MAX_SCHEDULE_ENTRIES 512

#define CMD_RUN_CONTINUOUS       24
#define CMD_PAUSE                25
#define CMD_WRITE_SCHEDULE_ENTRY 26

// ------------------------------------------------------------------
// 4.25B inter-core split opcodes
// ------------------------------------------------------------------
#define CMD_SCHEDULE_PENDING_SPLIT 30
#define CMD_MATURE_ACK_SPLIT       31

// ------------------------------------------------------------------
// 4.26 inter-core lookup protocol opcodes
//
// Transitional SDP-based messaging. Architecture target is multicast/MCPL.
// Host SDP remains reserved for control/readback only.
// ------------------------------------------------------------------
#define CMD_LOOKUP_REQUEST 32
#define CMD_LOOKUP_REPLY   33

// ------------------------------------------------------------------
// 4.30 lifecycle/static-pool protocol opcodes
//
// These commands deliberately do NOT call legacy neuron_birth/neuron_death.
// Tier 4.30 models lifecycle as a fixed hardware slot pool with active masks,
// lineage metadata, and compact telemetry before any multi-core migration.
// ------------------------------------------------------------------
#define CMD_LIFECYCLE_INIT           34
#define CMD_LIFECYCLE_EVENT          35
#define CMD_LIFECYCLE_TROPHIC_UPDATE 36
#define CMD_LIFECYCLE_READ_STATE     37
#define CMD_LIFECYCLE_SHAM_MODE      38

// ------------------------------------------------------------------
// 4.31 native temporal-substrate protocol opcodes
//
// Tier 4.31b refined the selected trace range to +/-2.0 in s16.15 after the
// earlier +/-1.0 sketch saturated. Keep that range explicit until a later gate
// proves a different range.
// ------------------------------------------------------------------
#define CMD_TEMPORAL_INIT            39
#define CMD_TEMPORAL_UPDATE          40
#define CMD_TEMPORAL_READ_STATE      41
#define CMD_TEMPORAL_SHAM_MODE       42

#define TEMPORAL_SCHEMA_VERSION      1
#define TEMPORAL_TRACE_COUNT         7
#define TEMPORAL_TIMESCALE_CHECKSUM  1811900589U
#define TEMPORAL_TRACE_BOUND         FP_FROM_FLOAT(2.0f)
#define TEMPORAL_INPUT_BOUND         FP_FROM_FLOAT(3.0f)
#define TEMPORAL_NOVELTY_BOUND       FP_FROM_FLOAT(5.0f)

#define TEMPORAL_DECAY_RAW_0         19874
#define TEMPORAL_DECAY_RAW_1         25519
#define TEMPORAL_DECAY_RAW_2         28917
#define TEMPORAL_DECAY_RAW_3         30782
#define TEMPORAL_DECAY_RAW_4         31759
#define TEMPORAL_DECAY_RAW_5         32259
#define TEMPORAL_DECAY_RAW_6         32512

#define TEMPORAL_ALPHA_RAW_0         12893
#define TEMPORAL_ALPHA_RAW_1         7248
#define TEMPORAL_ALPHA_RAW_2         3850
#define TEMPORAL_ALPHA_RAW_3         1985
#define TEMPORAL_ALPHA_RAW_4         1008
#define TEMPORAL_ALPHA_RAW_5         508
#define TEMPORAL_ALPHA_RAW_6         255

#define TEMPORAL_SHAM_ENABLED        0
#define TEMPORAL_SHAM_ZERO_STATE     1
#define TEMPORAL_SHAM_FROZEN_STATE   2
#define TEMPORAL_SHAM_RESET_EACH_UPDATE 3

#define LIFECYCLE_SCHEMA_VERSION 1

#define LIFECYCLE_EVENT_NONE          0
#define LIFECYCLE_EVENT_TROPHIC       1
#define LIFECYCLE_EVENT_CLEAVAGE      2
#define LIFECYCLE_EVENT_ADULT_BIRTH   3
#define LIFECYCLE_EVENT_DEATH         4
#define LIFECYCLE_EVENT_MATURITY      5

#define LIFECYCLE_SHAM_ENABLED        0
#define LIFECYCLE_SHAM_FIXED_POOL     1
#define LIFECYCLE_SHAM_RANDOM_REPLAY  2
#define LIFECYCLE_SHAM_MASK_SHUFFLE   3
#define LIFECYCLE_SHAM_LINEAGE_SHUFFLE 4
#define LIFECYCLE_SHAM_NO_TROPHIC     5
#define LIFECYCLE_SHAM_NO_DOPAMINE    6

#define LOOKUP_TYPE_CONTEXT 0
#define LOOKUP_TYPE_ROUTE   1
#define LOOKUP_TYPE_MEMORY  2

// ------------------------------------------------------------------
// 4.32a-r1 MCPL inter-core lookup key format
//
// Bit layout: app_id (8) | msg_type (4) | lookup_type (4) | shard_id (4) | seq_id (12)
// Uses official spin1_api symbol MCPL_PACKET_RECEIVED.
// ------------------------------------------------------------------
#define MCPL_KEY_APP_SHIFT        24
#define MCPL_KEY_TYPE_SHIFT       20
#define MCPL_KEY_LOOKUP_SHIFT     16
#define MCPL_KEY_SHARD_SHIFT      12
#define MCPL_KEY_SEQ_MASK         0x0FFF
#define MCPL_KEY_SHARD_MASK       0x0F

#define MCPL_MSG_LOOKUP_REQUEST   1
#define MCPL_MSG_LOOKUP_REPLY_VALUE 2
#define MCPL_MSG_LOOKUP_REPLY     MCPL_MSG_LOOKUP_REPLY_VALUE
#define MCPL_MSG_LIFECYCLE_EVENT_REQUEST 3
#define MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE 4
#define MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC 5
#define MCPL_MSG_LOOKUP_REPLY_META 6

#define MCPL_LIFECYCLE_SYNC_MASK    0
#define MCPL_LIFECYCLE_SYNC_LINEAGE 1

#ifndef CRA_MCPL_SHARD_ID
#define CRA_MCPL_SHARD_ID 0
#endif

#define MAKE_MCPL_KEY_SHARD(app, msg_type, lookup_type, shard_id, seq_id) \
    (((app) << MCPL_KEY_APP_SHIFT) | \
     ((msg_type) << MCPL_KEY_TYPE_SHIFT) | \
     ((lookup_type) << MCPL_KEY_LOOKUP_SHIFT) | \
     (((shard_id) & MCPL_KEY_SHARD_MASK) << MCPL_KEY_SHARD_SHIFT) | \
     ((seq_id) & MCPL_KEY_SEQ_MASK))

#define MAKE_MCPL_KEY(app, msg_type, lookup_type, seq_id) \
    MAKE_MCPL_KEY_SHARD((app), (msg_type), (lookup_type), CRA_MCPL_SHARD_ID, (seq_id))

#define EXTRACT_MCPL_MSG_TYPE(key)   (((key) >> MCPL_KEY_TYPE_SHIFT) & 0xF)
#define EXTRACT_MCPL_LOOKUP_TYPE(key) (((key) >> MCPL_KEY_LOOKUP_SHIFT) & 0xF)
#define EXTRACT_MCPL_SHARD_ID(key)   (((key) >> MCPL_KEY_SHARD_SHIFT) & MCPL_KEY_SHARD_MASK)
#define EXTRACT_MCPL_SEQ_ID(key)     ((key) & MCPL_KEY_SEQ_MASK)

#define MCPL_LOOKUP_META_HIT_BIT     0x80000000U
#define MCPL_LOOKUP_META_STATUS_BIT  0x40000000U
#define MCPL_LOOKUP_META_CONF_MASK   0x3FFFFFFFU

#define PACK_MCPL_LOOKUP_META(confidence, hit, status) \
    ((((hit) ? 1U : 0U) << 31) | \
     (((status) ? 1U : 0U) << 30) | \
     ((uint32_t)(confidence) & MCPL_LOOKUP_META_CONF_MASK))

#define EXTRACT_MCPL_LOOKUP_META_CONF(payload) ((int32_t)((payload) & MCPL_LOOKUP_META_CONF_MASK))
#define EXTRACT_MCPL_LOOKUP_META_HIT(payload)  (((payload) & MCPL_LOOKUP_META_HIT_BIT) ? 1U : 0U)
#define EXTRACT_MCPL_LOOKUP_META_STATUS(payload) (((payload) & MCPL_LOOKUP_META_STATUS_BIT) ? 1U : 0U)

// ------------------------------------------------------------------
// 4.26 runtime profile IDs (packed into byte 72 of CMD_READ_STATE payload)
// Low 4 bits = profile_id, high 4 bits = flags
// ------------------------------------------------------------------
#ifndef RUNTIME_PROFILE_ID
#define RUNTIME_PROFILE_ID 0
#endif
#define PROFILE_FULL                   0
#define PROFILE_DECOUPLED_MEMORY_ROUTE 1
#define PROFILE_STATE_CORE             2
#define PROFILE_LEARNING_CORE          3
#define PROFILE_CONTEXT_CORE           4
#define PROFILE_ROUTE_CORE             5
#define PROFILE_MEMORY_CORE            6
#define PROFILE_LIFECYCLE_CORE         7

#define MAKE_STATE_FLAGS(profile_id, flags) (((flags) & 0x0F) << 4 | ((profile_id) & 0x0F))
#define EXTRACT_PROFILE_ID(state_flags) ((state_flags) & 0x0F)

#endif // __CONFIG_H__
