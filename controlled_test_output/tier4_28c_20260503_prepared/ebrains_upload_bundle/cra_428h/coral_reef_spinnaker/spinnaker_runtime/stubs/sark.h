/* Stub sark.h for host-side syntax checking */
#ifndef __SARK_H__
#define __SARK_H__

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

typedef uintptr_t uint;

typedef struct sdp_msg {
    struct sdp_msg *next;
    uint16_t length;
    uint16_t checksum;
    uint8_t  flags;
    uint8_t  tag;
    uint8_t  dest_port;
    uint8_t  srce_port;
    uint16_t dest_addr;
    uint16_t srce_addr;
    uint16_t cmd_rc;
    uint16_t seq;
    uint32_t arg1;
    uint32_t arg2;
    uint32_t arg3;
    uint8_t  data[256];
    uint32_t __PAD1;
} sdp_msg_t;

typedef struct vcpu {
    uint32_t *svc_addr;
} vcpu_t;

typedef struct sv {
    vcpu_t *vcpu;
} sv_t;

extern sv_t *sv;

static inline uint32_t sark_core_id(void) { return 1; }
static inline uint32_t sark_chip_id(void) { return 0; }
static inline void *sark_alloc(uint32_t n_blocks, uint32_t block_size) { return malloc(n_blocks * block_size); }
static inline void sark_free(void *ptr) { free(ptr); }
#define MC_CORE_ROUTE(x) (1U << ((x) + 6U))
static inline uint rtr_alloc(uint size) { (void)size; return 1; }
static inline uint rtr_mc_set(uint entry, uint key, uint mask, uint route) {
    (void)entry;
    (void)key;
    (void)mask;
    (void)route;
    return 1;
}
static inline void rtr_free(uint entry, uint clear) { (void)entry; (void)clear; }
static inline void sark_mem_cpy(void *dst, const void *src, uint32_t n) { memcpy(dst, src, n); }
#define CPU_STATE_RUN 0

static inline uint32_t sark_cpu_state(uint32_t core) { (void)core; return 0; }

#endif
