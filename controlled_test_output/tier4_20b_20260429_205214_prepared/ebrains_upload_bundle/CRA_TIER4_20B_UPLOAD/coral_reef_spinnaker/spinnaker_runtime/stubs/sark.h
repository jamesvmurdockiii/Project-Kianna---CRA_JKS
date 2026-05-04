/* Stub sark.h for host-side syntax checking */
#ifndef __SARK_H__
#define __SARK_H__

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>

typedef unsigned int uint;

typedef struct sdp_msg {
    uint16_t length;
    uint16_t checksum;
    uint8_t  flags;
    uint8_t  tag;
    uint8_t  dest_port;
    uint8_t  dest_cpu;
    uint8_t  src_port;
    uint8_t  src_cpu;
    uint8_t  dest_y;
    uint8_t  dest_x;
    uint8_t  src_y;
    uint8_t  src_x;
    uint8_t  data[256];
} sdp_msg_t;

typedef struct vcpu {
    uint32_t *svc_addr;
} vcpu_t;

typedef struct sv {
    vcpu_t *vcpu;
} sv_t;

extern sv_t *sv;

static inline uint32_t sark_core_id(void) { return 1; }
static inline void *sark_alloc(uint32_t n_blocks, uint32_t block_size) { return malloc(n_blocks * block_size); }
static inline void sark_free(void *ptr) { free(ptr); }
static inline int sark_router_alloc(uint32_t key, uint32_t mask, uint32_t route) { return 0; }
static inline void sark_router_free(int entry) { (void)entry; }
static inline void sark_memcpy(void *dst, const void *src, uint32_t n) { (void)dst; (void)src; (void)n; }
#define CPU_STATE_RUN 0

static inline uint32_t sark_cpu_state(uint32_t core) { (void)core; return 0; }

#endif
