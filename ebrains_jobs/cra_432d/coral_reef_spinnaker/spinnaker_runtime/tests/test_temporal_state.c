/*
 * Tier 4.31c local C tests for the native temporal-substrate state.
 *
 * This is a source/local-host gate only. It proves that the runtime owns the
 * seven-EMA fixed-point state from Tier 4.31b, exposes compact readback, and
 * implements behavior-backed temporal sham modes before any EBRAINS package.
 */

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "config.h"
#include "host_interface.h"
#include "spin1_api.h"
#include "state_manager.h"

uint32_t g_timestep = 0;
int32_t g_dopamine_level = 0;

static const int32_t DECAY[TEMPORAL_TRACE_COUNT] = {
    TEMPORAL_DECAY_RAW_0,
    TEMPORAL_DECAY_RAW_1,
    TEMPORAL_DECAY_RAW_2,
    TEMPORAL_DECAY_RAW_3,
    TEMPORAL_DECAY_RAW_4,
    TEMPORAL_DECAY_RAW_5,
    TEMPORAL_DECAY_RAW_6
};

static const int32_t ALPHA[TEMPORAL_TRACE_COUNT] = {
    TEMPORAL_ALPHA_RAW_0,
    TEMPORAL_ALPHA_RAW_1,
    TEMPORAL_ALPHA_RAW_2,
    TEMPORAL_ALPHA_RAW_3,
    TEMPORAL_ALPHA_RAW_4,
    TEMPORAL_ALPHA_RAW_5,
    TEMPORAL_ALPHA_RAW_6
};

static sdp_msg_t g_test_msg;

static uint32_t _read_u32(const uint8_t *p) {
    return ((uint32_t)p[0])
        | ((uint32_t)p[1] << 8)
        | ((uint32_t)p[2] << 16)
        | ((uint32_t)p[3] << 24);
}

static int32_t _clip_i32(int32_t value, int32_t lo, int32_t hi) {
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
}

static uint8_t _dispatch(uint8_t cmd, uint32_t arg1, uint32_t arg2, uint32_t arg3) {
    memset(&g_test_msg, 0, sizeof(g_test_msg));
    g_test_msg.cmd_rc = cmd;
    g_test_msg.arg1 = arg1;
    g_test_msg.arg2 = arg2;
    g_test_msg.arg3 = arg3;
    sdp_rx_callback((uint)(uintptr_t)&g_test_msg, 0);
    return (uint8_t)((g_test_last_sdp_msg.cmd_rc >> 8) & 0xFF);
}

static uint32_t _trace_checksum_step(uint32_t checksum, const int32_t traces[TEMPORAL_TRACE_COUNT]) {
    int64_t weighted_sum = 0;
    for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
        weighted_sum += (int64_t)(i + 1) * (int64_t)traces[i];
    }
    return (uint32_t)(checksum * 2654435761U + (uint32_t)weighted_sum);
}

static void test_temporal_constants(void) {
    assert(TEMPORAL_SCHEMA_VERSION == 1);
    assert(TEMPORAL_TRACE_COUNT == 7);
    assert(TEMPORAL_TIMESCALE_CHECKSUM == 1811900589U);
    assert(TEMPORAL_TRACE_BOUND == FP_FROM_FLOAT(2.0f));
    assert(TEMPORAL_INPUT_BOUND == FP_FROM_FLOAT(3.0f));
    assert(DECAY[0] == 19874);
    assert(ALPHA[0] == 12893);
    assert(DECAY[6] == 32512);
    assert(ALPHA[6] == 255);
    printf("  PASS: temporal constants\n");
}

static void test_temporal_fixed_point_updates(void) {
    static const int32_t inputs[] = {
        FP_ONE,
        FP_HALF,
        -FP_HALF,
        FP_ONE / 4,
        -FP_ONE - FP_HALF / 2,
        FP_ONE - FP_ONE / 4
    };
    int32_t expected[TEMPORAL_TRACE_COUNT] = {0};
    uint32_t checksum = 0;
    cra_temporal_summary_t summary;

    assert(cra_temporal_init() == 0);
    for (uint32_t step = 0; step < sizeof(inputs) / sizeof(inputs[0]); step++) {
        int32_t x = _clip_i32(inputs[step], -TEMPORAL_INPUT_BOUND, TEMPORAL_INPUT_BOUND);
        for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
            int32_t candidate = FP_MUL(DECAY[i], expected[i]) + FP_MUL(ALPHA[i], x);
            expected[i] = _clip_i32(candidate, -TEMPORAL_TRACE_BOUND, TEMPORAL_TRACE_BOUND);
        }
        checksum = _trace_checksum_step(checksum, expected);

        assert(cra_temporal_update(inputs[step]) == 0);
        cra_temporal_get_summary(&summary);
        assert(summary.update_count == step + 1);
        assert(summary.saturation_count == 0);
        assert(summary.input_clip_count == 0);
        assert(summary.trace_checksum == checksum);
        assert(summary.latest_input_raw == x);

        for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
            int32_t actual = 0;
            assert(cra_temporal_get_trace(i, &actual) == 0);
            assert(actual == expected[i]);
        }
    }
    printf("  PASS: temporal fixed-point mirror updates\n");
}

static void test_temporal_bounds_and_shams(void) {
    cra_temporal_summary_t summary;
    int32_t before[TEMPORAL_TRACE_COUNT];

    assert(cra_temporal_init() == 0);
    assert(cra_temporal_update(FP_FROM_FLOAT(4.0f)) == 0);
    cra_temporal_get_summary(&summary);
    assert(summary.latest_input_raw == TEMPORAL_INPUT_BOUND);
    assert(summary.input_clip_count == 1);

    assert(cra_temporal_init() == 0);
    assert(cra_temporal_update(FP_ONE) == 0);
    for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
        assert(cra_temporal_get_trace(i, &before[i]) == 0);
        assert(before[i] != 0);
    }
    assert(cra_temporal_set_sham_mode(TEMPORAL_SHAM_FROZEN_STATE) == 0);
    assert(cra_temporal_update(-FP_ONE) == 0);
    for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
        int32_t actual = 0;
        assert(cra_temporal_get_trace(i, &actual) == 0);
        assert(actual == before[i]);
    }

    assert(cra_temporal_init() == 0);
    assert(cra_temporal_set_sham_mode(TEMPORAL_SHAM_ZERO_STATE) == 0);
    assert(cra_temporal_update(FP_ONE) == 0);
    cra_temporal_get_summary(&summary);
    assert(summary.sham_mode == TEMPORAL_SHAM_ZERO_STATE);
    assert(summary.trace_abs_sum_raw == 0);
    assert(summary.latest_novelty_raw == 0);
    printf("  PASS: temporal bounds and sham behavior\n");
}

static void test_temporal_host_readback(void) {
    uint8_t payload[64];
    uint8_t len = 0;

    assert(cra_temporal_init() == 0);
    len = host_if_pack_temporal_summary(payload, sizeof(payload));
    assert(len == 48);
    assert(payload[0] == CMD_TEMPORAL_READ_STATE);
    assert(payload[1] == 0);
    assert(_read_u32(&payload[2]) == TEMPORAL_SCHEMA_VERSION);
    assert(payload[6] == TEMPORAL_TRACE_COUNT);
    assert(_read_u32(&payload[8]) == TEMPORAL_TIMESCALE_CHECKSUM);

    assert(_dispatch(CMD_TEMPORAL_INIT, 0, 0, 0) == 0);
    assert((g_test_last_sdp_msg.cmd_rc & 0xFF) == CMD_TEMPORAL_INIT);
    assert(_read_u32(&g_test_last_sdp_msg.data[0]) == TEMPORAL_SCHEMA_VERSION);
    assert(g_test_last_sdp_msg.data[4] == TEMPORAL_TRACE_COUNT);

    assert(_dispatch(CMD_TEMPORAL_UPDATE, (uint32_t)FP_ONE, 0, 0) == 0);
    assert((g_test_last_sdp_msg.cmd_rc & 0xFF) == CMD_TEMPORAL_UPDATE);
    assert(_read_u32(&g_test_last_sdp_msg.data[10]) == 1);

    assert(_dispatch(CMD_TEMPORAL_SHAM_MODE, TEMPORAL_SHAM_ZERO_STATE, 0, 0) == 0);
    assert((g_test_last_sdp_msg.cmd_rc & 0xFF) == CMD_TEMPORAL_SHAM_MODE);
    assert(g_test_last_sdp_msg.data[5] == TEMPORAL_SHAM_ZERO_STATE);

    assert(_dispatch(CMD_TEMPORAL_READ_STATE, 0, 0, 0) == 0);
    assert((g_test_last_sdp_msg.cmd_rc & 0xFF) == CMD_TEMPORAL_READ_STATE);
    assert(_read_u32(&g_test_last_sdp_msg.data[0]) == TEMPORAL_SCHEMA_VERSION);
    printf("  PASS: temporal compact host readback\n");
}

int main(void) {
    printf("Running Tier 4.31c temporal-state tests...\n");
    test_temporal_constants();
    test_temporal_fixed_point_updates();
    test_temporal_bounds_and_shams();
    test_temporal_host_readback();
    printf("All temporal-state tests passed.\n");
    return 0;
}
