/*!
 * \file state_manager.c
 * \brief Static persistent state owned by the custom C runtime.
 */
#include "state_manager.h"
#include "router.h"
#include <sark.h>
#include <spin1_api.h>

static context_slot_t g_context_slots[MAX_CONTEXT_SLOTS];
static route_slot_t g_route_slots[MAX_ROUTE_SLOTS];
static memory_slot_t g_memory_slots[MAX_MEMORY_SLOTS];
static pending_horizon_t g_pending_horizons[MAX_PENDING_HORIZONS];
cra_state_summary_t g_summary;

static schedule_entry_t g_schedule[MAX_SCHEDULE_ENTRIES];
static uint32_t g_schedule_count = 0;
static uint32_t g_schedule_index = 0;
static uint32_t g_schedule_base_timestep = 0;
static uint8_t g_continuous_mode = 0;
static int32_t g_learning_rate = 0;
static lifecycle_slot_t g_lifecycle_slots[MAX_LIFECYCLE_SLOTS];
static cra_lifecycle_summary_t g_lifecycle_summary;
static uint32_t g_lifecycle_next_polyp_id = 2000;
static uint32_t g_lifecycle_next_lineage_id = 100;
static uint8_t g_lifecycle_have_last_event_index = 0;
static uint32_t g_lifecycle_last_event_index = 0;
static uint8_t g_lifecycle_sync_have_mask = 0;
static uint8_t g_lifecycle_sync_have_lineage = 0;
static uint32_t g_lifecycle_sync_pending_seq = 0;
static uint32_t g_lifecycle_sync_pending_mask = 0;
static uint32_t g_lifecycle_sync_pending_lineage = 0;
static int32_t g_temporal_traces[TEMPORAL_TRACE_COUNT];
static cra_temporal_summary_t g_temporal_summary;
static const int32_t g_temporal_decay_raw[TEMPORAL_TRACE_COUNT] = {
    TEMPORAL_DECAY_RAW_0,
    TEMPORAL_DECAY_RAW_1,
    TEMPORAL_DECAY_RAW_2,
    TEMPORAL_DECAY_RAW_3,
    TEMPORAL_DECAY_RAW_4,
    TEMPORAL_DECAY_RAW_5,
    TEMPORAL_DECAY_RAW_6
};
static const int32_t g_temporal_alpha_raw[TEMPORAL_TRACE_COUNT] = {
    TEMPORAL_ALPHA_RAW_0,
    TEMPORAL_ALPHA_RAW_1,
    TEMPORAL_ALPHA_RAW_2,
    TEMPORAL_ALPHA_RAW_3,
    TEMPORAL_ALPHA_RAW_4,
    TEMPORAL_ALPHA_RAW_5,
    TEMPORAL_ALPHA_RAW_6
};

extern uint32_t g_timestep;

static int32_t _floor_div_i32(int32_t value, int32_t divisor) {
    if (divisor <= 0) {
        return 0;
    }
    if (value >= 0) {
        return value / divisor;
    }
    return -(((-value) + divisor - 1) / divisor);
}

static int32_t _clamp_i32(int32_t value, int32_t min_value, int32_t max_value) {
    if (value < min_value) {
        return min_value;
    }
    if (value > max_value) {
        return max_value;
    }
    return value;
}

static int32_t _abs_i32(int32_t value) {
    return value < 0 ? -value : value;
}

static int32_t _temporal_clip_trace(int32_t value, uint32_t *clipped_out) {
    if (value > TEMPORAL_TRACE_BOUND) {
        if (clipped_out != 0) {
            *clipped_out = 1;
        }
        return TEMPORAL_TRACE_BOUND;
    }
    if (value < -TEMPORAL_TRACE_BOUND) {
        if (clipped_out != 0) {
            *clipped_out = 1;
        }
        return -TEMPORAL_TRACE_BOUND;
    }
    return value;
}

static void _temporal_recompute_abs_sum(void) {
    uint32_t total = 0;
    for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
        total += (uint32_t)_abs_i32(g_temporal_traces[i]);
    }
    g_temporal_summary.trace_abs_sum_raw = total;
}

static void _temporal_accumulate_checksum(void) {
    int64_t weighted_sum = 0;
    for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
        weighted_sum += (int64_t)(i + 1) * (int64_t)g_temporal_traces[i];
    }
    g_temporal_summary.trace_checksum =
        (uint32_t)(g_temporal_summary.trace_checksum * 2654435761U + (uint32_t)weighted_sum);
}

static void _temporal_clear_traces_only(void) {
    for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
        g_temporal_traces[i] = 0;
    }
    _temporal_recompute_abs_sum();
}

static void _temporal_clear(uint32_t reset_count) {
    _temporal_clear_traces_only();
    g_temporal_summary.schema_version = TEMPORAL_SCHEMA_VERSION;
    g_temporal_summary.trace_count = TEMPORAL_TRACE_COUNT;
    g_temporal_summary.timescale_checksum = TEMPORAL_TIMESCALE_CHECKSUM;
    g_temporal_summary.update_count = 0;
    g_temporal_summary.saturation_count = 0;
    g_temporal_summary.reset_count = reset_count;
    g_temporal_summary.input_clip_count = 0;
    g_temporal_summary.sham_mode = TEMPORAL_SHAM_ENABLED;
    g_temporal_summary.trace_checksum = 0;
    g_temporal_summary.latest_input_raw = 0;
    g_temporal_summary.latest_novelty_raw = 0;
}

void cra_temporal_reset(void) {
    _temporal_clear(g_temporal_summary.reset_count + 1);
}

int cra_temporal_init(void) {
    _temporal_clear(0);
    return 0;
}

int cra_temporal_set_sham_mode(uint32_t mode) {
    if (mode > TEMPORAL_SHAM_RESET_EACH_UPDATE) {
        return -1;
    }
    g_temporal_summary.sham_mode = mode;
    if (mode == TEMPORAL_SHAM_ZERO_STATE || mode == TEMPORAL_SHAM_RESET_EACH_UPDATE) {
        _temporal_clear_traces_only();
        g_temporal_summary.trace_checksum = 0;
        g_temporal_summary.latest_novelty_raw = 0;
        g_temporal_summary.reset_count++;
    }
    return 0;
}

int cra_temporal_update(int32_t input_raw) {
    int32_t x = input_raw;
    int32_t slowest_before = g_temporal_traces[TEMPORAL_TRACE_COUNT - 1];

    if (x > TEMPORAL_INPUT_BOUND) {
        x = TEMPORAL_INPUT_BOUND;
        g_temporal_summary.input_clip_count++;
    } else if (x < -TEMPORAL_INPUT_BOUND) {
        x = -TEMPORAL_INPUT_BOUND;
        g_temporal_summary.input_clip_count++;
    }

    g_temporal_summary.update_count++;
    g_temporal_summary.latest_input_raw = x;
    g_temporal_summary.latest_novelty_raw =
        _clamp_i32(x - slowest_before, -TEMPORAL_NOVELTY_BOUND, TEMPORAL_NOVELTY_BOUND);

    if (g_temporal_summary.sham_mode == TEMPORAL_SHAM_ZERO_STATE) {
        _temporal_clear_traces_only();
        g_temporal_summary.latest_novelty_raw = 0;
        _temporal_accumulate_checksum();
        return 0;
    }

    if (g_temporal_summary.sham_mode == TEMPORAL_SHAM_RESET_EACH_UPDATE) {
        _temporal_clear_traces_only();
        g_temporal_summary.reset_count++;
    }

    if (g_temporal_summary.sham_mode != TEMPORAL_SHAM_FROZEN_STATE) {
        for (uint32_t i = 0; i < TEMPORAL_TRACE_COUNT; i++) {
            uint32_t clipped = 0;
            int32_t candidate = FP_MUL(g_temporal_decay_raw[i], g_temporal_traces[i])
                + FP_MUL(g_temporal_alpha_raw[i], x);
            g_temporal_traces[i] = _temporal_clip_trace(candidate, &clipped);
            g_temporal_summary.saturation_count += clipped;
        }
    }

    _temporal_recompute_abs_sum();
    _temporal_accumulate_checksum();
    return 0;
}

void cra_temporal_get_summary(cra_temporal_summary_t *summary_out) {
    if (summary_out == 0) {
        return;
    }
    *summary_out = g_temporal_summary;
}

int cra_temporal_get_trace(uint32_t index, int32_t *trace_out) {
    if (index >= TEMPORAL_TRACE_COUNT || trace_out == 0) {
        return -1;
    }
    *trace_out = g_temporal_traces[index];
    return 0;
}

// ------------------------------------------------------------------
// 4.33 edge-of-chaos recurrent dynamics
// ------------------------------------------------------------------
#ifdef CRA_RUNTIME_PROFILE_EOC_RECURRENT

static int32_t g_eoc_hidden[EOC_HIDDEN_UNITS];
static int32_t g_eoc_w_rec[EOC_HIDDEN_UNITS][EOC_HIDDEN_UNITS];
static int32_t g_eoc_w_in[EOC_HIDDEN_UNITS][EOC_INPUT_DIM];
static cra_eoc_summary_t g_eoc_summary;

/* Precomputed antisymmetric rec matrix. Must be initialized by host before
   continuous mode. Done once; matrix is static during operation. */

void cra_eoc_init(void) {
    for (uint32_t i = 0; i < EOC_HIDDEN_UNITS; i++) {
        g_eoc_hidden[i] = 0;
        for (uint32_t j = 0; j < EOC_HIDDEN_UNITS; j++) {
            g_eoc_w_rec[i][j] = 0;
        }
        for (uint32_t j = 0; j < EOC_INPUT_DIM; j++) {
            g_eoc_w_in[i][j] = 0;
        }
    }
    g_eoc_summary.hidden_mean = 0;
    g_eoc_summary.hidden_variance = 0;
    g_eoc_summary.hidden_range = 0;
    g_eoc_summary.update_count = 0;
    g_eoc_summary.saturation_count = 0;
    g_eoc_summary.readout_weight = 0;
    g_eoc_summary.readout_bias = 0;
}

int cra_eoc_update(int32_t *driver, uint32_t driver_len) {
    if (driver == 0 || driver_len > EOC_INPUT_DIM) return -1;

    /* Tanh lookup table: precomputed s16.15 values for x in [0, 4*FP_ONE] */
    static const int32_t tanh_lut[] = {
        0, 20, 39, 59, 78, 98, 117, 137, 156, 176, 195, 215, 234, 254,
        273, 293, 312, 332, 351, 371, 390, 410, 429, 449, 468, 488, 507,
        527, 546, 566, 585, 604, 624, 643, 663, 682, 701, 721, 740, 759,
        779, 798, 817, 837, 856, 875, 894, 914, 933, 952, 971, 991, 1010,
        1029, 1048, 1067, 1087, 1106, 1125, 1144, 1163, 1182, 1201, 1220,
        1239, 1258, 1277, 1296, 1315, 1334, 1353, 1372, 1391, 1410, 1429,
        1448, 1466, 1485, 1504, 1523, 1542, 1560, 1579, 1598, 1617, 1635,
        1654, 1673, 1691, 1710, 1729, 1747, 1766, 1784, 1803, 1821, 1840,
        1858, 1877, 1895, 1914, 1932, 1951, 1969, 1987, 2006, 2024, 2042,
        2061, 2079, 2097, 2115, 2134, 2152, 2170, 2188, 2206, 2224, 2242,
        2261, 2279, 2297, 2315, 2333, 2351, 2369, 2387, 2404, 2422, 2440,
        2458, 2476, 2494, 2512, 2529, 2547, 2565, 2583, 2600, 2618, 2636,
        2653, 2671, 2689, 2706, 2724, 2742, 2759, 2777, 2794, 2812, 2829,
        2847, 2864, 2881, 2899, 2916, 2934, 2951, 2968, 2986, 3003, 3020,
        3038, 3055, 3072, 3089, 3106, 3124, 3141, 3158, 3175, 3192, 3209,
        3226, 3243, 3260, 3277, 3294, 3311, 3328, 3345, 3362, 3379, 3395,
        3412, 3429, 3446, 3463, 3479, 3496, 3513, 3530, 3546, 3563, 3580,
        3596, 3613, 3629, 3646, 3663, 3679, 3696, 3712, 3729, 3745, 3762,
        3778, 3794, 3811, 3827, 3844, 3860, 3876, 3893, 3909, 3925, 3941,
        3958, 3974, 3990, 4006, 4022, 4039, 4055, 4071, 4087, 4103, 4119,
        4135, 4151, 4167, 4183, 4199, 4215, 4231, 4247, 4263, 4279, 4295,
        4310, 4326, 4342, 4358, 4374, 4389, 4405, 4421, 4437, 4452, 4468,
        4484, 4499, 4515, 4531, 4546, 4562, 4577, 4593, 4609, 4624, 4640,
        4655, 4671, 4686, 4702, 4717, 4732, 4748, 4763, 4779, 4794, 4809,
        4825, 4840, 4855, 4871, 4886, 4901, 4916, 4932, 4947, 4962, 4977,
        4992, 5007, 5023, 5038, 5053, 5068, 5083, 5098, 5113, 5128, 5143,
        5158, 5173, 5188, 5203, 5218, 5233, 5248, 5263, 5278, 5293, 5308,
        5323, 5337, 5352, 5367, 5382, 5397, 5412, 5426, 5441, 5456, 5471,
        5485, 5500, 5515, 5530, 5544, 5559, 5574, 5588, 5603, 5618, 5632,
        5647, 5661, 5676, 5691, 5705, 5720, 5734, 5749, 5763, 5778, 5792,
        5807, 5821, 5836, 5850, 5865, 5879, 5893, 5908, 5922, 5936, 5951,
        5965, 5979, 5994, 6008, 6022, 6037, 6051, 6065, 6079, 6093, 6108,
        6122, 6136, 6150, 6164, 6178, 6193, 6207, 6221, 6235, 6249, 6263,
        6277, 6291, 6305, 6319, 6333, 6347, 6361, 6375, 6389, 6403, 6417,
        6431, 6445, 6459, 6473, 6487, 6500, 6514, 6528, 6542, 6556, 6570,
        6583, 6597, 6611, 6625, 6639, 6652, 6666, 6680, 6693, 6707, 6721,
        6735, 6748, 6762, 6776, 6789, 6803, 6816, 6830, 6844, 6857, 6871,
        6884, 6898, 6911, 6925, 6939, 6952, 6966, 6979, 6993, 7006, 7020,
        7033, 7046, 7060, 7073, 7087, 7100, 7114, 7127, 7140, 7154, 7167,
        7181, 7194, 7207, 7221, 7234, 7247, 7261, 7274, 7287, 7301, 7314,
        7327, 7341, 7354, 7367, 7380, 7394, 7407, 7420, 7433, 7446, 7460,
        7473, 7486, 7499, 7512, 7525, 7539, 7552, 7565, 7578, 7591, 7604,
        7617, 7630, 7644, 7657, 7670, 7683, 7696, 7709, 7722, 7735, 7748,
        7761, 7774, 7787, 7800, 7813, 7826, 7839, 7852, 7865, 7878, 7891,
        7904, 7917, 7930, 7943, 7956, 7969, 7982, 7995, 8008, 8021, 8034,
        8047, 8060, 8073, 8085, 8098, 8111, 8124, 8137, 8150, 8163, 8176,
        8188, 8201, 8214, 8227, 8240, 8253, 8265, 8278, 8291, 8304, 8317,
        8329, 8342, 8355, 8368, 8381, 8393, 8406, 8419, 8432, 8444, 8457,
        8470, 8483, 8495, 8508, 8521, 8533, 8546, 8559, 8572, 8584, 8597,
        8610, 8622, 8635, 8648, 8660, 8673, 8686, 8698, 8711, 8724, 8736,
        8749, 8762, 8774, 8787, 8799, 8812, 8825, 8837, 8850, 8862, 8875,
        8888, 8900, 8913, 8925, 8938, 8951, 8963, 8976, 8988, 9001, 9013,
        9026, 9039, 9051, 9064, 9076, 9089, 9101, 9114, 9126, 9139, 9152,
        9164, 9177, 9189, 9202, 9214, 9227, 9239, 9252, 9264, 9277, 9289,
        9302, 9314, 9327, 9339, 9352, 9364, 9377, 9389, 9402, 9414, 9427,
        9439, 9452, 9464, 9477, 9489, 9502, 9514, 9527, 9539, 9552, 9564,
        9577, 9589, 9602, 9614, 9627, 9639, 9651, 9664, 9676, 9689, 9701,
        9714, 9726, 9739, 9751, 9764, 9776, 9788, 9801, 9813, 9826, 9838,
        9851, 9863, 9876, 9888, 9900, 9913, 9925, 9938, 9950, 9963, 9975,
        9987, 10000, 10012, 10025, 10037, 10050, 10062, 10074, 10087, 10099,
        10112, 10124, 10136, 10149, 10161, 10174, 10186, 10198, 10211, 10223,
        10236, 10248, 10260, 10273, 10285, 10298, 10310, 10322, 10335, 10347,
        10360, 10372, 10384, 10397, 10409, 10422, 10434, 10446, 10459, 10471,
        10484, 10496, 10508, 10521, 10533, 10546, 10558, 10570, 10583, 10595,
        10608, 10620, 10632, 10645, 10657, 10670, 10682, 10694, 10707, 10719
    };

    int32_t new_hidden[EOC_HIDDEN_UNITS];
    int32_t sum = 0;
    int32_t min_val = FP_ONE * 4;
    int32_t max_val = -FP_ONE * 4;

    for (uint32_t i = 0; i < EOC_HIDDEN_UNITS; i++) {
        int32_t preact = 0;
        for (uint32_t j = 0; j < driver_len && j < EOC_INPUT_DIM; j++) {
            preact += FP_MUL(g_eoc_w_in[i][j], driver[j]);
        }
        for (uint32_t j = 0; j < EOC_HIDDEN_UNITS; j++) {
            preact += FP_MUL(g_eoc_w_rec[i][j], g_eoc_hidden[j]);
        }
        preact += g_eoc_hidden[i];  /* self-connection, sr=1.0, decay=0 */

        /* Tanh via lookup: clamp to [-4, +4] range, use LUT */
        int32_t abs_p = preact < 0 ? -preact : preact;
        if (abs_p >= 4 * FP_ONE) {
            new_hidden[i] = preact > 0 ? (FP_ONE - 1) : (-FP_ONE + 1);
            g_eoc_summary.saturation_count++;
        } else {
            uint32_t idx = (uint32_t)(abs_p) / (4 * FP_ONE / EOC_HIDDEN_UNITS);
            if (idx >= EOC_HIDDEN_UNITS) idx = EOC_HIDDEN_UNITS - 1;
            /* Simple approximation: tanh(|x|) ~ x for small x */
            if (abs_p <= FP_ONE / 2) {
                new_hidden[i] = preact;
            } else {
                int32_t sign = preact > 0 ? 1 : -1;
                int32_t frac = preact < 0 ? -preact : preact;
                new_hidden[i] = sign * (FP_ONE - FP_ONE / (1 + frac / FP_ONE));
            }
        }
        sum += new_hidden[i];
        if (new_hidden[i] < min_val) min_val = new_hidden[i];
        if (new_hidden[i] > max_val) max_val = new_hidden[i];
    }

    for (uint32_t i = 0; i < EOC_HIDDEN_UNITS; i++) {
        g_eoc_hidden[i] = new_hidden[i];
    }

    g_eoc_summary.update_count++;
    if (EOC_HIDDEN_UNITS > 0) {
        g_eoc_summary.hidden_mean = sum / (int32_t)EOC_HIDDEN_UNITS;
        int32_t var_sum = 0;
        for (uint32_t i = 0; i < EOC_HIDDEN_UNITS; i++) {
            int32_t diff = g_eoc_hidden[i] - g_eoc_summary.hidden_mean;
            var_sum += FP_MUL(diff, diff);
        }
        g_eoc_summary.hidden_variance = var_sum / (int32_t)EOC_HIDDEN_UNITS;
    }
    g_eoc_summary.hidden_range = max_val - min_val;
    return 0;
}

void cra_eoc_get_summary(cra_eoc_summary_t *summary_out) {
    if (summary_out == 0) return;
    *summary_out = g_eoc_summary;
    for (uint32_t i = 0; i < EOC_HIDDEN_UNITS; i++) {
        summary_out->hidden_sample[i] = g_eoc_hidden[i];
    }
}

#endif /* CRA_RUNTIME_PROFILE_EOC_RECURRENT */

static void _lifecycle_recompute_summary(void) {
    uint32_t active_count = 0;
    uint32_t active_mask_bits = 0;
    uint32_t lineage_checksum = 0;
    int64_t trophic_checksum = 0;

    for (uint32_t i = 0; i < MAX_LIFECYCLE_SLOTS; i++) {
        lifecycle_slot_t *slot = &g_lifecycle_slots[i];
        if (i < g_lifecycle_summary.pool_size && slot->active) {
            active_count++;
            active_mask_bits |= (1u << i);
        }
        if (i < g_lifecycle_summary.pool_size) {
            int32_t parent_factor = slot->parent_slot + 3;
            uint32_t active_factor = slot->active ? 1u : 5u;
            uint64_t line = (uint64_t)(slot->slot_id + 1)
                * (uint64_t)(slot->lineage_id + 17)
                * (uint64_t)(slot->generation + 1)
                * (uint64_t)parent_factor
                * (uint64_t)active_factor;
            lineage_checksum = (uint32_t)(lineage_checksum + (uint32_t)line);
            trophic_checksum += (int64_t)(slot->slot_id + 1)
                * (int64_t)(slot->trophic + slot->cyclin - slot->bax);
        }
    }

    g_lifecycle_summary.active_count = active_count;
    g_lifecycle_summary.inactive_count = g_lifecycle_summary.pool_size - active_count;
    g_lifecycle_summary.active_mask_bits = active_mask_bits;
    g_lifecycle_summary.lineage_checksum = lineage_checksum;
    g_lifecycle_summary.trophic_checksum = (int32_t)trophic_checksum;
}

static void _lifecycle_touch_active_ages(void) {
    for (uint32_t i = 0; i < g_lifecycle_summary.pool_size; i++) {
        if (g_lifecycle_slots[i].active) {
            g_lifecycle_slots[i].age++;
        }
    }
}

static int _lifecycle_slot_is_valid(uint32_t slot_id) {
    return slot_id < g_lifecycle_summary.pool_size && slot_id < MAX_LIFECYCLE_SLOTS;
}

static int32_t _lifecycle_sham_map_slot(int32_t slot_id) {
    static const int32_t permutation[MAX_LIFECYCLE_SLOTS] = {4, 7, 6, 5, 0, 2, 1, 3};
    if (slot_id < 0 || slot_id >= (int32_t)MAX_LIFECYCLE_SLOTS) {
        return slot_id;
    }
    if (slot_id >= (int32_t)g_lifecycle_summary.pool_size) {
        return slot_id;
    }
    return permutation[slot_id];
}

static int _lifecycle_sham_maps_event_slots(void) {
    return g_lifecycle_summary.sham_mode == LIFECYCLE_SHAM_RANDOM_REPLAY
        || g_lifecycle_summary.sham_mode == LIFECYCLE_SHAM_MASK_SHUFFLE;
}

static int _lifecycle_apply_trophic_to_slot(
    lifecycle_slot_t *slot,
    int32_t trophic_delta_raw,
    int32_t reward_raw
) {
    if (slot == 0 || !slot->active) {
        return -1;
    }

    int32_t reward_component = g_lifecycle_summary.sham_mode == LIFECYCLE_SHAM_NO_DOPAMINE
        ? 0
        : _floor_div_i32(reward_raw, 4);
    int32_t net = trophic_delta_raw + reward_component;
    slot->trophic = _clamp_i32(slot->trophic + net, -4 * FP_ONE, 4 * FP_ONE);

    if (net >= 0) {
        slot->cyclin = _clamp_i32(slot->cyclin + _floor_div_i32(net, 2), 0, 4 * FP_ONE);
        slot->bax = _clamp_i32(slot->bax - _floor_div_i32(net, 4), 0, 4 * FP_ONE);
    } else {
        int32_t loss = -net;
        slot->bax = _clamp_i32(slot->bax + _floor_div_i32(loss, 2), 0, 4 * FP_ONE);
        slot->cyclin = _clamp_i32(slot->cyclin + _floor_div_i32(net, 4), 0, 4 * FP_ONE);
    }
    return 0;
}

void cra_lifecycle_reset(void) {
    for (uint32_t i = 0; i < MAX_LIFECYCLE_SLOTS; i++) {
        g_lifecycle_slots[i].slot_id = i;
        g_lifecycle_slots[i].polyp_id = 0;
        g_lifecycle_slots[i].lineage_id = 0;
        g_lifecycle_slots[i].parent_slot = -1;
        g_lifecycle_slots[i].generation = 0;
        g_lifecycle_slots[i].age = 0;
        g_lifecycle_slots[i].trophic = 0;
        g_lifecycle_slots[i].cyclin = 0;
        g_lifecycle_slots[i].bax = 0;
        g_lifecycle_slots[i].event_count = 0;
        g_lifecycle_slots[i].active = 0;
        g_lifecycle_slots[i].last_event_type = LIFECYCLE_EVENT_NONE;
    }

    g_lifecycle_summary.schema_version = LIFECYCLE_SCHEMA_VERSION;
    g_lifecycle_summary.pool_size = 0;
    g_lifecycle_summary.founder_count = 0;
    g_lifecycle_summary.active_count = 0;
    g_lifecycle_summary.inactive_count = 0;
    g_lifecycle_summary.active_mask_bits = 0;
    g_lifecycle_summary.attempted_event_count = 0;
    g_lifecycle_summary.lifecycle_event_count = 0;
    g_lifecycle_summary.cleavage_count = 0;
    g_lifecycle_summary.adult_birth_count = 0;
    g_lifecycle_summary.death_count = 0;
    g_lifecycle_summary.maturity_count = 0;
    g_lifecycle_summary.trophic_update_count = 0;
    g_lifecycle_summary.invalid_event_count = 0;
    g_lifecycle_summary.lineage_checksum = 0;
    g_lifecycle_summary.trophic_checksum = 0;
    g_lifecycle_summary.sham_mode = LIFECYCLE_SHAM_ENABLED;
    g_lifecycle_next_polyp_id = 2000;
    g_lifecycle_next_lineage_id = 100;
    g_lifecycle_have_last_event_index = 0;
    g_lifecycle_last_event_index = 0;
}

int cra_lifecycle_init(
    uint32_t pool_size,
    uint32_t founder_count,
    uint32_t seed,
    int32_t trophic_seed_raw,
    uint32_t generation_seed
) {
    (void)seed;
    if (pool_size == 0 || pool_size > MAX_LIFECYCLE_SLOTS || founder_count > pool_size) {
        cra_lifecycle_reset();
        g_lifecycle_summary.invalid_event_count++;
        return -1;
    }

    cra_lifecycle_reset();
    g_lifecycle_summary.pool_size = pool_size;
    g_lifecycle_summary.founder_count = founder_count;
    g_lifecycle_next_polyp_id = 2000 + generation_seed;
    g_lifecycle_next_lineage_id = 100 + generation_seed;

    for (uint32_t i = 0; i < pool_size; i++) {
        lifecycle_slot_t *slot = &g_lifecycle_slots[i];
        slot->slot_id = i;
        slot->parent_slot = -1;
        if (i < founder_count) {
            slot->active = 1;
            slot->polyp_id = 1000 + i;
            slot->lineage_id = i + 1;
            slot->trophic = trophic_seed_raw;
            slot->cyclin = 0;
            slot->bax = 0;
        }
    }

    _lifecycle_recompute_summary();
    return 0;
}

int cra_lifecycle_apply_trophic_update(
    uint32_t target_slot,
    int32_t trophic_delta_raw,
    int32_t reward_raw
) {
    return cra_lifecycle_apply_event(
        g_lifecycle_summary.attempted_event_count,
        LIFECYCLE_EVENT_TROPHIC,
        target_slot,
        -1,
        -1,
        trophic_delta_raw,
        reward_raw
    );
}

int cra_lifecycle_apply_event(
    uint32_t event_index,
    uint8_t event_type,
    uint32_t target_slot,
    int32_t parent_slot,
    int32_t child_slot,
    int32_t trophic_delta_raw,
    int32_t reward_raw
) {
    (void)event_index;
    int rc = 0;

    g_lifecycle_summary.attempted_event_count++;
    _lifecycle_touch_active_ages();

    if (g_lifecycle_summary.pool_size == 0) {
        g_lifecycle_summary.invalid_event_count++;
        _lifecycle_recompute_summary();
        return -1;
    }

    lifecycle_slot_t *target = _lifecycle_slot_is_valid(target_slot)
        ? &g_lifecycle_slots[target_slot]
        : 0;

    if (_lifecycle_sham_maps_event_slots()) {
        int32_t mapped_target = _lifecycle_sham_map_slot((int32_t)target_slot);
        int32_t mapped_parent = _lifecycle_sham_map_slot(parent_slot);
        int32_t mapped_child = _lifecycle_sham_map_slot(child_slot);
        target_slot = mapped_target < 0 ? target_slot : (uint32_t)mapped_target;
        parent_slot = mapped_parent;
        child_slot = mapped_child;
        target = _lifecycle_slot_is_valid(target_slot)
            ? &g_lifecycle_slots[target_slot]
            : 0;
    }

    if (event_type == LIFECYCLE_EVENT_TROPHIC) {
        if (target == 0 || !target->active) {
            rc = -1;
        } else {
            if (g_lifecycle_summary.sham_mode != LIFECYCLE_SHAM_NO_TROPHIC) {
                (void)_lifecycle_apply_trophic_to_slot(target, trophic_delta_raw, reward_raw);
            }
            target->event_count++;
            target->last_event_type = event_type;
            g_lifecycle_summary.trophic_update_count++;
            g_lifecycle_summary.lifecycle_event_count++;
        }
    } else if (event_type == LIFECYCLE_EVENT_CLEAVAGE || event_type == LIFECYCLE_EVENT_ADULT_BIRTH) {
        if (g_lifecycle_summary.sham_mode == LIFECYCLE_SHAM_FIXED_POOL) {
            g_lifecycle_summary.lifecycle_event_count++;
        } else if (parent_slot < 0 || child_slot < 0 ||
            !_lifecycle_slot_is_valid((uint32_t)parent_slot) ||
            !_lifecycle_slot_is_valid((uint32_t)child_slot) ||
            !g_lifecycle_slots[(uint32_t)parent_slot].active ||
            g_lifecycle_slots[(uint32_t)child_slot].active) {
            rc = -1;
        } else {
            lifecycle_slot_t *parent = &g_lifecycle_slots[(uint32_t)parent_slot];
            lifecycle_slot_t *child = &g_lifecycle_slots[(uint32_t)child_slot];
            child->active = 1;
            child->polyp_id = g_lifecycle_next_polyp_id++;
            child->lineage_id = (event_type == LIFECYCLE_EVENT_CLEAVAGE)
                ? parent->lineage_id
                : g_lifecycle_next_lineage_id++;
            child->parent_slot = parent_slot;
            child->generation = parent->generation + 1;
            child->age = 0;
            child->trophic = parent->trophic / 2;
            if (child->trophic < FP_FROM_FLOAT(0.25f)) {
                child->trophic = FP_FROM_FLOAT(0.25f);
            }
            child->cyclin = 0;
            child->bax = 0;
            child->event_count = 1;
            child->last_event_type = event_type;
            parent->trophic = _clamp_i32(parent->trophic - (child->trophic / 4), -4 * FP_ONE, 4 * FP_ONE);
            parent->event_count++;
            parent->last_event_type = event_type;
            if (event_type == LIFECYCLE_EVENT_CLEAVAGE) {
                g_lifecycle_summary.cleavage_count++;
            } else {
                g_lifecycle_summary.adult_birth_count++;
            }
            g_lifecycle_summary.lifecycle_event_count++;
        }
    } else if (event_type == LIFECYCLE_EVENT_DEATH) {
        if (g_lifecycle_summary.sham_mode == LIFECYCLE_SHAM_FIXED_POOL) {
            g_lifecycle_summary.lifecycle_event_count++;
        } else if (target == 0 || !target->active) {
            rc = -1;
        } else {
            target->active = 0;
            target->event_count++;
            target->last_event_type = event_type;
            g_lifecycle_summary.death_count++;
            g_lifecycle_summary.lifecycle_event_count++;
        }
    } else if (event_type == LIFECYCLE_EVENT_MATURITY) {
        if (target == 0 || !target->active) {
            rc = -1;
        } else {
            if (g_lifecycle_summary.sham_mode != LIFECYCLE_SHAM_NO_TROPHIC) {
                target->trophic = _clamp_i32(target->trophic + FP_FROM_FLOAT(0.0625f), -4 * FP_ONE, 4 * FP_ONE);
                target->cyclin = _clamp_i32(target->cyclin + FP_FROM_FLOAT(0.125f), 0, 4 * FP_ONE);
                target->bax = _clamp_i32(target->bax - FP_FROM_FLOAT(0.03125f), 0, 4 * FP_ONE);
            }
            target->event_count++;
            target->last_event_type = event_type;
            g_lifecycle_summary.maturity_count++;
            g_lifecycle_summary.lifecycle_event_count++;
        }
    } else {
        rc = -1;
    }

    if (rc != 0) {
        g_lifecycle_summary.invalid_event_count++;
    }
    _lifecycle_recompute_summary();
    return rc;
}

int cra_lifecycle_set_sham_mode(uint32_t mode) {
    if (mode > LIFECYCLE_SHAM_NO_DOPAMINE) {
        g_lifecycle_summary.invalid_event_count++;
        return -1;
    }
    g_lifecycle_summary.sham_mode = mode;
    return 0;
}

void cra_lifecycle_get_summary(cra_lifecycle_summary_t *summary_out) {
    if (summary_out == 0) {
        return;
    }
    _lifecycle_recompute_summary();
    *summary_out = g_lifecycle_summary;
}

int cra_lifecycle_get_slot(uint32_t slot_id, lifecycle_slot_t *slot_out) {
    if (!_lifecycle_slot_is_valid(slot_id) || slot_out == 0) {
        return -1;
    }
    *slot_out = g_lifecycle_slots[slot_id];
    return 0;
}

static uint8_t _lifecycle_event_mutates_active_mask(uint8_t event_type) {
    return event_type == LIFECYCLE_EVENT_CLEAVAGE
        || event_type == LIFECYCLE_EVENT_ADULT_BIRTH
        || event_type == LIFECYCLE_EVENT_DEATH;
}

static void _lifecycle_broadcast_active_mask_sync(void) {
    cra_lifecycle_summary_t summary;
    cra_lifecycle_get_summary(&summary);
    uint32_t seq = summary.lifecycle_event_count & MCPL_KEY_SEQ_MASK;
    uint32_t mask_key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC,
        MCPL_LIFECYCLE_SYNC_MASK,
        seq);
    uint32_t mask_payload = (summary.active_mask_bits & 0xFFFF)
        | ((summary.active_count & 0xFF) << 16);
    spin1_send_mc_packet(mask_key, mask_payload, WITH_PAYLOAD);

    uint32_t lineage_key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC,
        MCPL_LIFECYCLE_SYNC_LINEAGE,
        seq);
    spin1_send_mc_packet(lineage_key, summary.lineage_checksum, WITH_PAYLOAD);
    g_summary.lifecycle_mask_syncs_sent++;
}

void cra_lifecycle_send_event_request_stub(uint32_t event_index, uint8_t event_type, uint32_t target_slot) {
    uint32_t key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_EVENT_REQUEST,
        event_type & 0x0F,
        event_index & MCPL_KEY_SEQ_MASK);
    spin1_send_mc_packet(key, target_slot, WITH_PAYLOAD);
    g_summary.lifecycle_event_requests_sent++;
}

void cra_lifecycle_send_trophic_update_stub(uint32_t target_slot, int32_t trophic_delta_raw) {
    uint32_t key = MAKE_MCPL_KEY(
        APP_ID,
        MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE,
        0,
        target_slot & MCPL_KEY_SEQ_MASK);
    spin1_send_mc_packet(key, (uint32_t)trophic_delta_raw, WITH_PAYLOAD);
    g_summary.lifecycle_trophic_requests_sent++;
}

static int _lifecycle_reject_duplicate_or_stale(uint32_t event_index) {
    if (!g_lifecycle_have_last_event_index) {
        return 0;
    }
    if (event_index == g_lifecycle_last_event_index) {
        g_summary.lifecycle_duplicate_events++;
        g_lifecycle_summary.invalid_event_count++;
        return -1;
    }
    if (event_index < g_lifecycle_last_event_index) {
        g_summary.lifecycle_stale_events++;
        g_lifecycle_summary.invalid_event_count++;
        return -1;
    }
    return 0;
}

int cra_lifecycle_handle_event_request(
    uint32_t event_index,
    uint8_t event_type,
    uint32_t target_slot,
    int32_t parent_slot,
    int32_t child_slot,
    int32_t trophic_delta_raw,
    int32_t reward_raw
) {
    if (_lifecycle_reject_duplicate_or_stale(event_index) != 0) {
        _lifecycle_recompute_summary();
        return -1;
    }

    uint32_t before_mask = g_lifecycle_summary.active_mask_bits;
    int rc = cra_lifecycle_apply_event(
        event_index,
        event_type,
        target_slot,
        parent_slot,
        child_slot,
        trophic_delta_raw,
        reward_raw);

    if (rc == 0) {
        g_lifecycle_have_last_event_index = 1;
        g_lifecycle_last_event_index = event_index;
        g_summary.lifecycle_event_acks_received++;
        if (_lifecycle_event_mutates_active_mask(event_type)
            && g_lifecycle_summary.active_mask_bits != before_mask) {
            _lifecycle_broadcast_active_mask_sync();
        }
    }
    return rc;
}

int cra_lifecycle_handle_trophic_request(
    uint32_t event_index,
    uint32_t target_slot,
    int32_t trophic_delta_raw,
    int32_t reward_raw
) {
    return cra_lifecycle_handle_event_request(
        event_index,
        LIFECYCLE_EVENT_TROPHIC,
        target_slot,
        -1,
        -1,
        trophic_delta_raw,
        reward_raw);
}

void cra_lifecycle_receive_active_mask_sync(
    uint32_t event_count,
    uint32_t active_mask_bits,
    uint32_t lineage_checksum
) {
    g_summary.lifecycle_mask_syncs_received++;
    g_summary.lifecycle_last_seen_event_count = event_count;
    g_summary.lifecycle_last_seen_active_mask_bits = active_mask_bits;
    g_summary.lifecycle_last_seen_lineage_checksum = lineage_checksum;
}

static void _lifecycle_receive_active_mask_sync_packet(
    uint32_t event_count,
    uint8_t sync_type,
    uint32_t payload
) {
    if (event_count != g_lifecycle_sync_pending_seq) {
        g_lifecycle_sync_pending_seq = event_count;
        g_lifecycle_sync_have_mask = 0;
        g_lifecycle_sync_have_lineage = 0;
    }

    if (sync_type == MCPL_LIFECYCLE_SYNC_MASK) {
        g_lifecycle_sync_pending_mask = payload & 0xFFFF;
        g_lifecycle_sync_have_mask = 1;
    } else if (sync_type == MCPL_LIFECYCLE_SYNC_LINEAGE) {
        g_lifecycle_sync_pending_lineage = payload;
        g_lifecycle_sync_have_lineage = 1;
    } else {
        return;
    }

    if (g_lifecycle_sync_have_mask && g_lifecycle_sync_have_lineage) {
        cra_lifecycle_receive_active_mask_sync(
            g_lifecycle_sync_pending_seq,
            g_lifecycle_sync_pending_mask,
            g_lifecycle_sync_pending_lineage);
        g_lifecycle_sync_have_mask = 0;
        g_lifecycle_sync_have_lineage = 0;
    }
}

void cra_lifecycle_record_missing_ack(void) {
    g_summary.lifecycle_missing_acks++;
}

static void _clear_slots(void) {
    for (uint32_t i = 0; i < MAX_CONTEXT_SLOTS; i++) {
        g_context_slots[i].key = 0;
        g_context_slots[i].value = 0;
        g_context_slots[i].confidence = 0;
        g_context_slots[i].last_update = 0;
        g_context_slots[i].active = 0;
    }
}

static void _clear_route_slots(void) {
    for (uint32_t i = 0; i < MAX_ROUTE_SLOTS; i++) {
        g_route_slots[i].key = 0;
        g_route_slots[i].value = 0;
        g_route_slots[i].confidence = 0;
        g_route_slots[i].last_update = 0;
        g_route_slots[i].active = 0;
    }
}

static void _clear_memory_slots(void) {
    for (uint32_t i = 0; i < MAX_MEMORY_SLOTS; i++) {
        g_memory_slots[i].key = 0;
        g_memory_slots[i].value = 0;
        g_memory_slots[i].confidence = 0;
        g_memory_slots[i].last_update = 0;
        g_memory_slots[i].active = 0;
    }
}

static void _clear_summary(uint32_t reset_count) {
    g_summary.active_slots = 0;
    g_summary.slot_writes = 0;
    g_summary.slot_hits = 0;
    g_summary.slot_misses = 0;
    g_summary.slot_evictions = 0;
    g_summary.decisions = 0;
    g_summary.reward_events = 0;
    g_summary.pending_created = 0;
    g_summary.pending_matured = 0;
    g_summary.pending_dropped = 0;
    g_summary.active_pending = 0;
    g_summary.state_resets = reset_count;
    g_summary.route_writes = 0;
    g_summary.route_reads = 0;
    g_summary.active_route_slots = 0;
    g_summary.route_slot_writes = 0;
    g_summary.route_slot_hits = 0;
    g_summary.route_slot_misses = 0;
    g_summary.route_slot_evictions = 0;
    g_summary.active_memory_slots = 0;
    g_summary.memory_slot_writes = 0;
    g_summary.memory_slot_hits = 0;
    g_summary.memory_slot_misses = 0;
    g_summary.memory_slot_evictions = 0;
    g_summary.readout_weight = 0;
    g_summary.readout_bias = 0;
    g_summary.route_value = FP_ONE;
    g_summary.route_confidence = FP_ONE;
    g_summary.last_feature = 0;
    g_summary.last_prediction = 0;
    g_summary.last_reward = 0;
    g_summary.lookup_requests_sent = 0;
    g_summary.lookup_replies_received = 0;
    g_summary.lookup_stale_replies = 0;
    g_summary.lookup_duplicate_replies = 0;
    g_summary.lookup_timeouts = 0;
    g_summary.commands_received = 0;
    g_summary.schedule_length = 0;
    g_summary.readback_bytes_sent = 0;
    g_summary.lifecycle_event_requests_sent = 0;
    g_summary.lifecycle_trophic_requests_sent = 0;
    g_summary.lifecycle_event_acks_received = 0;
    g_summary.lifecycle_mask_syncs_sent = 0;
    g_summary.lifecycle_mask_syncs_received = 0;
    g_summary.lifecycle_last_seen_event_count = 0;
    g_summary.lifecycle_last_seen_active_mask_bits = 0;
    g_summary.lifecycle_last_seen_lineage_checksum = 0;
    g_summary.lifecycle_duplicate_events = 0;
    g_summary.lifecycle_stale_events = 0;
    g_summary.lifecycle_missing_acks = 0;
    g_lifecycle_sync_have_mask = 0;
    g_lifecycle_sync_have_lineage = 0;
    g_lifecycle_sync_pending_seq = 0;
    g_lifecycle_sync_pending_mask = 0;
    g_lifecycle_sync_pending_lineage = 0;
}

static void _clear_pending(void) {
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        g_pending_horizons[i].due_timestep = 0;
        g_pending_horizons[i].feature = 0;
        g_pending_horizons[i].prediction = 0;
        g_pending_horizons[i].target = 0;
        g_pending_horizons[i].composite_confidence = 0;
        g_pending_horizons[i].active = 0;
        g_pending_horizons[i].has_confidence = 0;
    }
}

static int _find_slot(uint32_t key) {
    for (uint32_t i = 0; i < MAX_CONTEXT_SLOTS; i++) {
        if (g_context_slots[i].active && g_context_slots[i].key == key) {
            return (int)i;
        }
    }
    return -1;
}

static int _select_slot_for_write(uint32_t *evicted) {
    *evicted = 0;
    for (uint32_t i = 0; i < MAX_CONTEXT_SLOTS; i++) {
        if (!g_context_slots[i].active) {
            return (int)i;
        }
    }

    uint32_t victim = 0;
    for (uint32_t i = 1; i < MAX_CONTEXT_SLOTS; i++) {
        context_slot_t *candidate = &g_context_slots[i];
        context_slot_t *current = &g_context_slots[victim];
        if (candidate->confidence < current->confidence ||
            (candidate->confidence == current->confidence && candidate->last_update < current->last_update)) {
            victim = i;
        }
    }
    *evicted = 1;
    return (int)victim;
}

static int _find_route_slot(uint32_t key) {
    for (uint32_t i = 0; i < MAX_ROUTE_SLOTS; i++) {
        if (g_route_slots[i].active && g_route_slots[i].key == key) {
            return (int)i;
        }
    }
    return -1;
}

static int _select_route_slot_for_write(uint32_t *evicted) {
    *evicted = 0;
    for (uint32_t i = 0; i < MAX_ROUTE_SLOTS; i++) {
        if (!g_route_slots[i].active) {
            return (int)i;
        }
    }

    uint32_t victim = 0;
    for (uint32_t i = 1; i < MAX_ROUTE_SLOTS; i++) {
        route_slot_t *candidate = &g_route_slots[i];
        route_slot_t *current = &g_route_slots[victim];
        if (candidate->confidence < current->confidence ||
            (candidate->confidence == current->confidence && candidate->last_update < current->last_update)) {
            victim = i;
        }
    }
    *evicted = 1;
    return (int)victim;
}

static int _find_memory_slot(uint32_t key) {
    for (uint32_t i = 0; i < MAX_MEMORY_SLOTS; i++) {
        if (g_memory_slots[i].active && g_memory_slots[i].key == key) {
            return (int)i;
        }
    }
    return -1;
}

static int _select_memory_slot_for_write(uint32_t *evicted) {
    *evicted = 0;
    for (uint32_t i = 0; i < MAX_MEMORY_SLOTS; i++) {
        if (!g_memory_slots[i].active) {
            return (int)i;
        }
    }

    uint32_t victim = 0;
    for (uint32_t i = 1; i < MAX_MEMORY_SLOTS; i++) {
        memory_slot_t *candidate = &g_memory_slots[i];
        memory_slot_t *current = &g_memory_slots[victim];
        if (candidate->confidence < current->confidence ||
            (candidate->confidence == current->confidence && candidate->last_update < current->last_update)) {
            victim = i;
        }
    }
    *evicted = 1;
    return (int)victim;
}

void cra_state_init(void) {
    _clear_slots();
    _clear_route_slots();
    _clear_memory_slots();
    _clear_pending();
    cra_state_schedule_init();
    cra_lifecycle_reset();
    (void)cra_temporal_init();
    _clear_summary(0);
}

void cra_state_reset(void) {
    uint32_t reset_count = g_summary.state_resets + 1;
    _clear_slots();
    _clear_route_slots();
    _clear_memory_slots();
    _clear_pending();
    cra_state_schedule_init();
    cra_lifecycle_reset();
    cra_temporal_reset();
    g_learning_rate = 0;
    _clear_summary(reset_count);
}

int cra_state_write_context(uint32_t key, int32_t value, int32_t confidence, uint32_t timestep) {
    int idx = _find_slot(key);
    uint32_t evicted = 0;
    if (idx < 0) {
        idx = _select_slot_for_write(&evicted);
    }
    if (idx < 0) {
        return -1;
    }

    if (!g_context_slots[idx].active) {
        g_summary.active_slots++;
    } else if (evicted) {
        g_summary.slot_evictions++;
    }

    g_context_slots[idx].key = key;
    g_context_slots[idx].value = value;
    g_context_slots[idx].confidence = confidence;
    g_context_slots[idx].last_update = timestep;
    g_context_slots[idx].active = 1;
    g_summary.slot_writes++;
    return 0;
}

int cra_state_read_context(uint32_t key, int32_t *value_out, int32_t *confidence_out) {
    int idx = _find_slot(key);
    if (idx < 0) {
        g_summary.slot_misses++;
        return -1;
    }
    if (value_out != 0) {
        *value_out = g_context_slots[idx].value;
    }
    if (confidence_out != 0) {
        *confidence_out = g_context_slots[idx].confidence;
    }
    g_summary.slot_hits++;
    return 0;
}

uint32_t cra_state_active_slot_count(void) {
    return g_summary.active_slots;
}

int cra_state_write_route(int32_t value, int32_t confidence, uint32_t timestep) {
    (void)timestep;
    g_summary.route_value = value;
    g_summary.route_confidence = confidence;
    g_summary.route_writes++;
    return 0;
}

int cra_state_read_route(int32_t *value_out, int32_t *confidence_out) {
    if (value_out != 0) {
        *value_out = g_summary.route_value;
    }
    if (confidence_out != 0) {
        *confidence_out = g_summary.route_confidence;
    }
    g_summary.route_reads++;
    return 0;
}

int cra_state_write_route_slot(uint32_t key, int32_t value, int32_t confidence, uint32_t timestep) {
    int idx = _find_route_slot(key);
    uint32_t evicted = 0;
    if (idx < 0) {
        idx = _select_route_slot_for_write(&evicted);
    }
    if (idx < 0) {
        return -1;
    }

    if (!g_route_slots[idx].active) {
        g_summary.active_route_slots++;
    } else if (evicted) {
        g_summary.route_slot_evictions++;
    }

    g_route_slots[idx].key = key;
    g_route_slots[idx].value = value;
    g_route_slots[idx].confidence = confidence;
    g_route_slots[idx].last_update = timestep;
    g_route_slots[idx].active = 1;
    g_summary.route_slot_writes++;
    return 0;
}

int cra_state_read_route_slot(uint32_t key, int32_t *value_out, int32_t *confidence_out) {
    int idx = _find_route_slot(key);
    if (idx < 0) {
        g_summary.route_slot_misses++;
        return -1;
    }
    if (value_out != 0) {
        *value_out = g_route_slots[idx].value;
    }
    if (confidence_out != 0) {
        *confidence_out = g_route_slots[idx].confidence;
    }
    g_summary.route_slot_hits++;
    return 0;
}

uint32_t cra_state_active_route_slot_count(void) {
    return g_summary.active_route_slots;
}

int cra_state_write_memory_slot(uint32_t key, int32_t value, int32_t confidence, uint32_t timestep) {
    int idx = _find_memory_slot(key);
    uint32_t evicted = 0;
    if (idx < 0) {
        idx = _select_memory_slot_for_write(&evicted);
    }
    if (idx < 0) {
        return -1;
    }

    if (!g_memory_slots[idx].active) {
        g_summary.active_memory_slots++;
    } else if (evicted) {
        g_summary.memory_slot_evictions++;
    }

    g_memory_slots[idx].key = key;
    g_memory_slots[idx].value = value;
    g_memory_slots[idx].confidence = confidence;
    g_memory_slots[idx].last_update = timestep;
    g_memory_slots[idx].active = 1;
    g_summary.memory_slot_writes++;
    return 0;
}

int cra_state_read_memory_slot(uint32_t key, int32_t *value_out, int32_t *confidence_out) {
    int idx = _find_memory_slot(key);
    if (idx < 0) {
        g_summary.memory_slot_misses++;
        return -1;
    }
    if (value_out != 0) {
        *value_out = g_memory_slots[idx].value;
    }
    if (confidence_out != 0) {
        *confidence_out = g_memory_slots[idx].confidence;
    }
    g_summary.memory_slot_hits++;
    return 0;
}

uint32_t cra_state_active_memory_slot_count(void) {
    return g_summary.active_memory_slots;
}

void cra_state_set_readout(int32_t weight, int32_t bias) {
    g_summary.readout_weight = weight;
    g_summary.readout_bias = bias;
}

int32_t cra_state_predict_readout(int32_t feature) {
    return FP_MUL(g_summary.readout_weight, feature) + g_summary.readout_bias;
}

void cra_state_record_decision(int32_t feature, int32_t prediction) {
    g_summary.decisions++;
    g_summary.last_feature = feature;
    g_summary.last_prediction = prediction;
}

void cra_state_record_reward(int32_t reward) {
    g_summary.reward_events++;
    g_summary.last_reward = reward;
}

int32_t cra_state_apply_reward_to_readout(int32_t reward, int32_t learning_rate) {
    int32_t error = reward - g_summary.last_prediction;
    int32_t delta_w = FP_MUL(learning_rate, FP_MUL(error, g_summary.last_feature));
    int32_t delta_b = FP_MUL(learning_rate, error);
    g_summary.readout_weight += delta_w;
    g_summary.readout_bias += delta_b;
    cra_state_record_reward(reward);
    return delta_w;
}

static int32_t _apply_reward_to_feature_prediction(
    int32_t feature,
    int32_t prediction,
    int32_t target,
    int32_t learning_rate
) {
    int32_t error = target - prediction;
    int32_t surprise = error < 0 ? -error : error;
    if (surprise < SURPRISE_THRESHOLD) {
        int32_t delta_w = FP_MUL(learning_rate, FP_MUL(error, feature));
        int32_t delta_b = FP_MUL(learning_rate, error);
        g_summary.readout_weight += delta_w;
        g_summary.readout_bias += delta_b;
    }
    g_summary.reward_events++;
    g_summary.last_feature = feature;
    g_summary.last_prediction = prediction;
    g_summary.last_reward = target;
    return error;
}

int cra_state_schedule_pending_horizon(
    int32_t feature,
    int32_t prediction,
    uint32_t due_timestep
) {
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        if (!g_pending_horizons[i].active) {
            g_pending_horizons[i].due_timestep = due_timestep;
            g_pending_horizons[i].feature = feature;
            g_pending_horizons[i].prediction = prediction;
            g_pending_horizons[i].active = 1;
            g_summary.pending_created++;
            g_summary.active_pending++;
            return 0;
        }
    }
    g_summary.pending_dropped++;
    return -1;
}

uint32_t cra_state_mature_pending_horizons(uint32_t timestep, int32_t target, int32_t learning_rate) {
    uint32_t matured = 0;
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        if (g_pending_horizons[i].active && g_pending_horizons[i].due_timestep <= timestep) {
            int32_t effective_lr = learning_rate;
            if (g_pending_horizons[i].has_confidence) {
                effective_lr = FP_MUL(learning_rate, g_pending_horizons[i].composite_confidence);
            }
            _apply_reward_to_feature_prediction(
                g_pending_horizons[i].feature,
                g_pending_horizons[i].prediction,
                target,
                effective_lr
            );
            g_pending_horizons[i].active = 0;
            g_pending_horizons[i].has_confidence = 0;
            if (g_summary.active_pending > 0) {
                g_summary.active_pending--;
            }
            g_summary.pending_matured++;
            matured++;
        }
    }
    return matured;
}

uint32_t cra_state_active_pending_count(void) {
    return g_summary.active_pending;
}

void cra_state_schedule_init(void) {
    g_schedule_count = 0;
    g_schedule_index = 0;
    g_schedule_base_timestep = 0;
    g_continuous_mode = 0;
    for (uint32_t i = 0; i < MAX_SCHEDULE_ENTRIES; i++) {
        g_schedule[i].timestep = 0;
        g_schedule[i].context_key = 0;
        g_schedule[i].route_key = 0;
        g_schedule[i].memory_key = 0;
        g_schedule[i].cue = 0;
        g_schedule[i].target = 0;
        g_schedule[i].delay = 0;
    }
}

int cra_state_write_schedule_entry(uint32_t index, const schedule_entry_t *entry) {
    if (index >= MAX_SCHEDULE_ENTRIES || entry == 0) {
        return -1;
    }
    g_schedule[index] = *entry;
    if (index >= g_schedule_count) {
        g_schedule_count = index + 1;
    }
    return 0;
}

uint32_t cra_state_schedule_entry_count(void) { return g_schedule_count; }
void cra_state_set_schedule_count(uint32_t count) { g_schedule_count = count; }
uint8_t cra_state_continuous_mode(void) { return g_continuous_mode; }
void cra_state_set_continuous_mode(uint8_t mode) {
    g_continuous_mode = mode;
    if (mode) {
        g_schedule_base_timestep = g_timestep;
    }
}
void cra_state_set_learning_rate(int32_t lr_raw) { g_learning_rate = lr_raw; }

int cra_state_schedule_pending_horizon_with_target(
    int32_t feature,
    int32_t prediction,
    int32_t target,
    uint32_t due_timestep
) {
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        if (!g_pending_horizons[i].active) {
            g_pending_horizons[i].due_timestep = due_timestep;
            g_pending_horizons[i].feature = feature;
            g_pending_horizons[i].prediction = prediction;
            g_pending_horizons[i].target = target;
            g_pending_horizons[i].composite_confidence = 0;
            g_pending_horizons[i].active = 1;
            g_pending_horizons[i].has_confidence = 0;
            g_summary.pending_created++;
            g_summary.active_pending++;
            return 0;
        }
    }
    g_summary.pending_dropped++;
    return -1;
}

int cra_state_schedule_pending_horizon_with_target_and_confidence(
    int32_t feature,
    int32_t prediction,
    int32_t target,
    uint32_t due_timestep,
    int32_t composite_confidence
) {
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        if (!g_pending_horizons[i].active) {
            g_pending_horizons[i].due_timestep = due_timestep;
            g_pending_horizons[i].feature = feature;
            g_pending_horizons[i].prediction = prediction;
            g_pending_horizons[i].target = target;
            g_pending_horizons[i].composite_confidence = composite_confidence;
            g_pending_horizons[i].active = 1;
            g_pending_horizons[i].has_confidence = 1;
            g_summary.pending_created++;
            g_summary.active_pending++;
            return 0;
        }
    }
    g_summary.pending_dropped++;
    return -1;
}

uint32_t cra_state_mature_oldest_pending(uint32_t timestep, int32_t learning_rate) {
    // Find the active pending with the smallest due_timestep that is <= timestep
    int oldest_idx = -1;
    uint32_t oldest_due = 0xFFFFFFFF;
    for (uint32_t i = 0; i < MAX_PENDING_HORIZONS; i++) {
        if (g_pending_horizons[i].active && g_pending_horizons[i].due_timestep <= timestep) {
            if (g_pending_horizons[i].due_timestep < oldest_due) {
                oldest_due = g_pending_horizons[i].due_timestep;
                oldest_idx = (int)i;
            }
        }
    }
    if (oldest_idx < 0) {
        return 0;
    }
    pending_horizon_t *ph = &g_pending_horizons[oldest_idx];
    int32_t effective_lr = learning_rate;
    if (ph->has_confidence) {
        effective_lr = FP_MUL(learning_rate, ph->composite_confidence);
    }
    _apply_reward_to_feature_prediction(
        ph->feature,
        ph->prediction,
        ph->target,
        effective_lr
    );
    ph->active = 0;
    ph->has_confidence = 0;
    if (g_summary.active_pending > 0) {
        g_summary.active_pending--;
    }
    g_summary.pending_matured++;
    return 1;
}

// ------------------------------------------------------------------
// 4.25B inter-core SDP send (state core → learning core)
// ------------------------------------------------------------------
#ifdef CRA_RUNTIME_PROFILE_STATE_CORE
static uint16_t g_chip_addr = 0;

static void _send_schedule_pending_split(int32_t feature, int32_t prediction, int32_t target, uint32_t due_timestep) {
    sdp_msg_t *msg = (sdp_msg_t *) spin1_msg_get();
    if (msg == NULL) return;
    // Same chip, Core 5 (learning core), port 1
    msg->dest_addr = g_chip_addr;
    msg->srce_addr = g_chip_addr;
    msg->dest_port = (1 << 5) | 5;
    msg->srce_port = (uint8_t)((sark_core_id() << 5) | 1);
    msg->flags = 0;
    msg->tag = 0;
    msg->cmd_rc = CMD_SCHEDULE_PENDING_SPLIT;
    msg->arg1 = (uint32_t)feature;
    msg->arg2 = (uint32_t)prediction;
    msg->arg3 = due_timestep;
    msg->data[0] = (uint8_t)(target & 0xFF);
    msg->data[1] = (uint8_t)((target >> 8) & 0xFF);
    msg->data[2] = (uint8_t)((target >> 16) & 0xFF);
    msg->data[3] = (uint8_t)((target >> 24) & 0xFF);
    msg->length = sizeof(sdp_msg_t) - 256 + 4;  // header + 4 bytes data
    spin1_send_sdp_msg(msg, 1);
    spin1_msg_free(msg);
}

void cra_state_capture_chip_addr(uint16_t chip_addr) {
    if (g_chip_addr == 0) {
        g_chip_addr = chip_addr;
    }
}
#endif

#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
static void _send_lookup_request(uint32_t seq_id, uint32_t key, uint8_t type, uint8_t dest_cpu);
#endif

uint32_t cra_state_process_continuous_tick(uint32_t timestep) {
#ifdef CRA_RUNTIME_PROFILE_STATE_CORE
    // State core: check schedule, compute feature, send SDP to learning core
    if (g_schedule_index < g_schedule_count) {
        schedule_entry_t *entry = &g_schedule[g_schedule_index];
        if (entry->timestep + g_schedule_base_timestep == timestep) {
            int32_t ctx_val = 0, ctx_conf = 0;
            int32_t route_val = 0, route_conf = 0;
            int32_t mem_val = 0, mem_conf = 0;

            cra_state_read_context(entry->context_key, &ctx_val, &ctx_conf);
            cra_state_read_route_slot(entry->route_key, &route_val, &route_conf);
            cra_state_read_memory_slot(entry->memory_key, &mem_val, &mem_conf);

            int32_t feature = FP_MUL(FP_MUL(FP_MUL(ctx_val, route_val), mem_val), entry->cue);
            int32_t prediction = cra_state_predict_readout(feature);

            cra_state_record_decision(feature, prediction);
            _send_schedule_pending_split(feature, prediction, entry->target, timestep + entry->delay);
            g_schedule_index++;
        }
    }
    // State core does NOT mature pending locally
    // Auto-pause when schedule exhausted
    if (g_schedule_index >= g_schedule_count) {
        g_continuous_mode = 0;
    }
    return 0;
#elif CRA_RUNTIME_PROFILE_LEARNING_CORE
    // 4.26 learning core: schedule-driven parallel lookups + feature composition.
    // Sends 3 lookups per event; waits for replies; composes feature; schedules pending.
    // Transitional SDP inter-core messaging. Target architecture is multicast/MCPL.
    uint32_t matured = 0;

    static uint32_t s_event_seq[3];
    static int32_t  s_event_cue;
    static int32_t  s_event_target;
    static uint32_t s_event_delay;
    static uint32_t s_event_base_timestep;
    static uint8_t  s_event_active = 0;
    static uint32_t s_lookup_next_seq = 1;

    // Phase B: If current event lookups are complete, compose and schedule.
    if (s_event_active) {
        if (cra_state_lookup_is_received(s_event_seq[0]) &&
            cra_state_lookup_is_received(s_event_seq[1]) &&
            cra_state_lookup_is_received(s_event_seq[2])) {

            int32_t ctx_val = 0, route_val = 0, mem_val = 0;
            int32_t ctx_conf = 0, route_conf = 0, mem_conf = 0;
            uint8_t hit;

            cra_state_lookup_get_result(s_event_seq[0], &ctx_val, &ctx_conf, &hit);
            cra_state_lookup_get_result(s_event_seq[1], &route_val, &route_conf, &hit);
            cra_state_lookup_get_result(s_event_seq[2], &mem_val, &mem_conf, &hit);

            int32_t feature = FP_MUL(FP_MUL(FP_MUL(ctx_val, route_val), mem_val), s_event_cue);
            int32_t prediction = cra_state_predict_readout(feature);
            int32_t composite_confidence = FP_MUL(FP_MUL(ctx_conf, route_conf), mem_conf);

            cra_state_record_decision(feature, prediction);
            cra_state_schedule_pending_horizon_with_target_and_confidence(
                feature, prediction, s_event_target,
                s_event_base_timestep + s_event_delay,
                composite_confidence);

            /* Clear lookup entries to free table slots for next event */
            cra_state_lookup_clear(s_event_seq[0]);
            cra_state_lookup_clear(s_event_seq[1]);
            cra_state_lookup_clear(s_event_seq[2]);

            s_event_active = 0;
        }
    }

    // Phase A: If no active event and schedule entry is due, send lookups.
    if (!s_event_active && g_schedule_index < g_schedule_count) {
        schedule_entry_t *entry = &g_schedule[g_schedule_index];
        if (entry->timestep + g_schedule_base_timestep == timestep) {
            s_event_seq[0] = s_lookup_next_seq++;
            s_event_seq[1] = s_lookup_next_seq++;
            s_event_seq[2] = s_lookup_next_seq++;

            cra_state_lookup_send(s_event_seq[0], entry->context_key, LOOKUP_TYPE_CONTEXT, timestep);
            _send_lookup_request(s_event_seq[0], entry->context_key, LOOKUP_TYPE_CONTEXT, 4);
            cra_state_lookup_send(s_event_seq[1], entry->route_key, LOOKUP_TYPE_ROUTE, timestep);
            _send_lookup_request(s_event_seq[1], entry->route_key, LOOKUP_TYPE_ROUTE, 5);
            cra_state_lookup_send(s_event_seq[2], entry->memory_key, LOOKUP_TYPE_MEMORY, timestep);
            _send_lookup_request(s_event_seq[2], entry->memory_key, LOOKUP_TYPE_MEMORY, 6);

            s_event_cue = entry->cue;
            s_event_target = entry->target;
            s_event_delay = entry->delay;
            s_event_base_timestep = timestep;
            s_event_active = 1;

            g_schedule_index++;
        }
    }

    // Phase C: Mature oldest pending if due.
    matured = cra_state_mature_oldest_pending(timestep, g_learning_rate);

    // Auto-pause when schedule exhausted, event complete, and pending drained.
    if (g_schedule_index >= g_schedule_count && !s_event_active && g_summary.active_pending == 0) {
        g_continuous_mode = 0;
    }

    return matured;
#elif CRA_RUNTIME_PROFILE_CONTEXT_CORE || CRA_RUNTIME_PROFILE_ROUTE_CORE || CRA_RUNTIME_PROFILE_MEMORY_CORE
    // 4.26 state-server cores: no schedule or pending. Host reads state directly.
    (void)timestep;
    return 0;
#else
    // Monolithic decoupled_memory_route: original behavior
    uint32_t matured = 0;

    // 1. Process next schedule entry if due
    if (g_schedule_index < g_schedule_count) {
        schedule_entry_t *entry = &g_schedule[g_schedule_index];
        if (entry->timestep + g_schedule_base_timestep == timestep) {
            int32_t ctx_val = 0, ctx_conf = 0;
            int32_t route_val = 0, route_conf = 0;
            int32_t mem_val = 0, mem_conf = 0;

            cra_state_read_context(entry->context_key, &ctx_val, &ctx_conf);
            cra_state_read_route_slot(entry->route_key, &route_val, &route_conf);
            cra_state_read_memory_slot(entry->memory_key, &mem_val, &mem_conf);

            int32_t feature = FP_MUL(FP_MUL(FP_MUL(ctx_val, route_val), mem_val), entry->cue);
            int32_t prediction = cra_state_predict_readout(feature);

            cra_state_record_decision(feature, prediction);
            cra_state_schedule_pending_horizon_with_target(
                feature, prediction, entry->target, timestep + entry->delay);

            g_schedule_index++;
        }
    }

    // 2. Mature oldest pending if due
    matured = cra_state_mature_oldest_pending(timestep, g_learning_rate);

    // 3. Auto-pause when schedule exhausted and pending drained
    if (g_schedule_index >= g_schedule_count && g_summary.active_pending == 0) {
        g_continuous_mode = 0;
    }

    return matured;
#endif
}

// ------------------------------------------------------------------
// 4.26 inter-core lookup protocol (transitional SDP; target is multicast/MCPL)
// ------------------------------------------------------------------

#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
static lookup_entry_t g_lookup_entries[MAX_LOOKUP_REPLIES];

void cra_state_lookup_init(void) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        g_lookup_entries[i].seq_id = 0;
        g_lookup_entries[i].received = 0;
        g_lookup_entries[i].value_received = 0;
        g_lookup_entries[i].meta_received = 0;
    }
}

#ifndef CRA_USE_MCPL_LOOKUP
static uint16_t g_learning_chip_addr = 0;
#endif

static void _send_lookup_request(uint32_t seq_id, uint32_t key, uint8_t type, uint8_t dest_cpu) {
    // SDP stays available as a transitional fallback. CRA_USE_MCPL_LOOKUP
    // selects the confidence-bearing MCPL path repaired in Tier 4.32a-r1.
#ifdef CRA_USE_MCPL_LOOKUP
    cra_state_mcpl_lookup_send_request(seq_id, key, type, dest_cpu);
    g_summary.lookup_requests_sent++;
#else
    sdp_msg_t *msg = (sdp_msg_t *) spin1_msg_get();
    if (msg == NULL) return;
    if (g_learning_chip_addr == 0) {
        g_learning_chip_addr = (uint16_t) sark_chip_id();
    }
    msg->dest_addr = g_learning_chip_addr;
    msg->srce_addr = g_learning_chip_addr;
    msg->dest_port = (1 << 5) | dest_cpu;
    msg->srce_port = (uint8_t)((sark_core_id() << 5) | 1);
    msg->flags = 0;
    msg->tag = 0;
    msg->cmd_rc = CMD_LOOKUP_REQUEST;
    msg->arg1 = seq_id;
    msg->arg2 = key;
    msg->arg3 = (uint32_t)type;
    msg->length = sizeof(sdp_msg_t) - 256;  /* header only, no data payload */
    g_summary.lookup_requests_sent++;
    spin1_send_sdp_msg(msg, 1);
    spin1_msg_free(msg);
#endif
}

int cra_state_lookup_send_shard(uint32_t seq_id, uint32_t key, uint8_t type, uint8_t shard_id, uint32_t timestamp) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == 0) {
            g_lookup_entries[i].seq_id = seq_id;
            g_lookup_entries[i].key = key;
            g_lookup_entries[i].type = type;
            g_lookup_entries[i].shard_id = shard_id & MCPL_KEY_SHARD_MASK;
            g_lookup_entries[i].received = 0;
            g_lookup_entries[i].value_received = 0;
            g_lookup_entries[i].meta_received = 0;
            g_lookup_entries[i].hit = 0;
            g_lookup_entries[i].status = 0;
            g_lookup_entries[i].value = 0;
            g_lookup_entries[i].confidence = 0;
            g_lookup_entries[i].timestamp = timestamp;
            return 0;
        }
    }
    return -1; /* table full */
}

int cra_state_lookup_send(uint32_t seq_id, uint32_t key, uint8_t type, uint32_t timestamp) {
    return cra_state_lookup_send_shard(seq_id, key, type, CRA_MCPL_SHARD_ID, timestamp);
}

int cra_state_lookup_receive(uint32_t seq_id, int32_t value, int32_t confidence, uint8_t hit) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id && !g_lookup_entries[i].received) {
            g_lookup_entries[i].value = value;
            g_lookup_entries[i].confidence = confidence;
            g_lookup_entries[i].hit = hit;
            g_lookup_entries[i].status = 0;
            g_lookup_entries[i].value_received = 1;
            g_lookup_entries[i].meta_received = 1;
            g_lookup_entries[i].received = 1;
            g_summary.lookup_replies_received++;
            return 0;
        }
    }
    /* Distinguish stale (seq_id never seen) from duplicate (already received) */
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id) {
            g_summary.lookup_duplicate_replies++;
            return -1; /* duplicate reply */
        }
    }
    g_summary.lookup_stale_replies++;
    return -1; /* stale reply: seq_id not in pending list */
}

static lookup_entry_t *_lookup_find_shard(uint32_t seq_id, uint8_t type, uint8_t shard_id) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id &&
            g_lookup_entries[i].type == type &&
            g_lookup_entries[i].shard_id == (shard_id & MCPL_KEY_SHARD_MASK)) {
            return &g_lookup_entries[i];
        }
    }
    return 0;
}

static int _lookup_receive_mcpl_value(uint32_t seq_id, uint8_t type, uint8_t shard_id, int32_t value) {
    lookup_entry_t *entry = _lookup_find_shard(seq_id, type, shard_id);
    if (entry == 0) {
        g_summary.lookup_stale_replies++;
        return -1;
    }
    if (entry->received || entry->value_received) {
        g_summary.lookup_duplicate_replies++;
        return -1;
    }
    entry->value = value;
    entry->value_received = 1;
    if (entry->meta_received) {
        entry->received = 1;
        g_summary.lookup_replies_received++;
    }
    return 0;
}

static int _lookup_receive_mcpl_meta(uint32_t seq_id, uint8_t type, uint8_t shard_id, int32_t confidence, uint8_t hit, uint8_t status) {
    lookup_entry_t *entry = _lookup_find_shard(seq_id, type, shard_id);
    if (entry == 0) {
        g_summary.lookup_stale_replies++;
        return -1;
    }
    if (entry->received || entry->meta_received) {
        g_summary.lookup_duplicate_replies++;
        return -1;
    }
    entry->confidence = confidence;
    entry->hit = hit;
    entry->status = status;
    entry->meta_received = 1;
    if (entry->value_received) {
        entry->received = 1;
        g_summary.lookup_replies_received++;
    }
    return 0;
}

uint8_t cra_state_lookup_is_received_shard(uint32_t seq_id, uint8_t type, uint8_t shard_id) {
    lookup_entry_t *entry = _lookup_find_shard(seq_id, type, shard_id);
    return entry ? entry->received : 0;
}

uint8_t cra_state_lookup_is_received(uint32_t seq_id) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id) {
            return g_lookup_entries[i].received;
        }
    }
    return 0;
}

uint8_t cra_state_lookup_is_stale(uint32_t seq_id) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id) {
            return 0; /* found = not stale */
        }
    }
    return 1; /* not found = stale */
}

uint32_t cra_state_lookup_check_timeout(uint32_t timestamp, uint32_t *seq_ids_out, uint32_t max_out) {
    uint32_t count = 0;
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id != 0 && !g_lookup_entries[i].received) {
            if (timestamp - g_lookup_entries[i].timestamp > 10) {
                if (count < max_out) {
                    seq_ids_out[count++] = g_lookup_entries[i].seq_id;
                }
                g_summary.lookup_timeouts++;
            }
        }
    }
    return count;
}

int cra_state_lookup_get_result_shard(uint32_t seq_id, uint8_t type, uint8_t shard_id, int32_t *value_out, int32_t *confidence_out, uint8_t *hit_out) {
    lookup_entry_t *entry = _lookup_find_shard(seq_id, type, shard_id);
    if (entry != 0 && entry->received) {
        if (value_out) *value_out = entry->value;
        if (confidence_out) *confidence_out = entry->confidence;
        if (hit_out) *hit_out = entry->hit;
        return 0;
    }
    return -1;
}

int cra_state_lookup_get_result(uint32_t seq_id, int32_t *value_out, int32_t *confidence_out, uint8_t *hit_out) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id && g_lookup_entries[i].received) {
            if (value_out) *value_out = g_lookup_entries[i].value;
            if (confidence_out) *confidence_out = g_lookup_entries[i].confidence;
            if (hit_out) *hit_out = g_lookup_entries[i].hit;
            return 0;
        }
    }
    return -1;
}

void cra_state_lookup_clear(uint32_t seq_id) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id) {
            g_lookup_entries[i].seq_id = 0;
            g_lookup_entries[i].received = 0;
            g_lookup_entries[i].value_received = 0;
            g_lookup_entries[i].meta_received = 0;
            return;
        }
    }
}

uint32_t cra_state_lookup_list_pending(uint32_t *seq_ids_out, uint32_t max_out) {
    uint32_t count = 0;
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id != 0 && !g_lookup_entries[i].received) {
            if (seq_ids_out && count < max_out) {
                seq_ids_out[count] = g_lookup_entries[i].seq_id;
            }
            count++;
        }
    }
    return count;
}

int cra_state_lookup_get_pending_info(uint32_t seq_id, uint32_t *key_out, uint8_t *type_out) {
    for (uint32_t i = 0; i < MAX_LOOKUP_REPLIES; i++) {
        if (g_lookup_entries[i].seq_id == seq_id && !g_lookup_entries[i].received) {
            if (key_out) *key_out = g_lookup_entries[i].key;
            if (type_out) *type_out = g_lookup_entries[i].type;
            return 0;
        }
    }
    return -1;
}
#endif

#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
static uint16_t g_chip_addr = 0;

void cra_state_capture_chip_addr(uint16_t chip_addr) {
    if (g_chip_addr == 0) {
        g_chip_addr = chip_addr;
    }
}

static void _send_lookup_reply(uint32_t seq_id, int32_t value, int32_t confidence, uint8_t hit, uint8_t status) {
    // SDP stays available as a transitional fallback. CRA_USE_MCPL_LOOKUP
    // selects the confidence-bearing MCPL path repaired in Tier 4.32a-r1.
#ifdef CRA_USE_MCPL_LOOKUP
    cra_state_mcpl_lookup_send_reply_shard(seq_id, value, confidence, hit, status,
        /* lookup_type inferred from profile at compile time */
#ifdef CRA_RUNTIME_PROFILE_CONTEXT_CORE
        LOOKUP_TYPE_CONTEXT,
#elif defined(CRA_RUNTIME_PROFILE_ROUTE_CORE)
        LOOKUP_TYPE_ROUTE,
#elif defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
        LOOKUP_TYPE_MEMORY,
#else
        0,
#endif
        CRA_MCPL_SHARD_ID,
        7);  // dest_core = learning core
#else
    sdp_msg_t *msg = (sdp_msg_t *) spin1_msg_get();
    if (msg == NULL) return;
    msg->dest_addr = g_chip_addr;
    msg->srce_addr = g_chip_addr;
    msg->dest_port = (1 << 5) | 7; /* port 1, CPU 7 (learning core) */
    msg->srce_port = (uint8_t)((sark_core_id() << 5) | 1);
    msg->flags = 0;
    msg->tag = 0;
    msg->cmd_rc = CMD_LOOKUP_REPLY;
    msg->arg1 = seq_id;
    msg->arg2 = (uint32_t)value;
    msg->arg3 = (uint32_t)confidence;
    msg->data[0] = hit;
    msg->data[1] = status;
    msg->length = sizeof(sdp_msg_t) - 256 + 2;
    spin1_send_sdp_msg(msg, 1);
    spin1_msg_free(msg);
#endif
}

void cra_state_handle_lookup_request(uint32_t seq_id, uint32_t key, uint8_t type) {
    int32_t value = 0;
    int32_t confidence = 0;
    uint8_t hit = 0;
    uint8_t status = 0;

#ifdef CRA_RUNTIME_PROFILE_CONTEXT_CORE
    if (type == LOOKUP_TYPE_CONTEXT) {
        int rc = cra_state_read_context(key, &value, &confidence);
        hit = (rc == 0) ? 1 : 0;
    } else
#endif
#ifdef CRA_RUNTIME_PROFILE_ROUTE_CORE
    if (type == LOOKUP_TYPE_ROUTE) {
        int rc = cra_state_read_route_slot(key, &value, &confidence);
        hit = (rc == 0) ? 1 : 0;
    } else
#endif
#ifdef CRA_RUNTIME_PROFILE_MEMORY_CORE
    if (type == LOOKUP_TYPE_MEMORY) {
        int rc = cra_state_read_memory_slot(key, &value, &confidence);
        hit = (rc == 0) ? 1 : 0;
    } else
#endif
    {
        status = 1; /* wrong lookup type for this profile */
    }

    _send_lookup_reply(seq_id, value, confidence, hit, status);
}
#endif

// ------------------------------------------------------------------
// 4.32a-r1 MCPL inter-core lookup repair
//
// These functions use the official spin1_api MCPL symbols.
// Tier 4.32a-r1 carries value plus confidence/hit/status over MCPL
// and includes shard_id in the key to avoid replicated-shard cross-talk.
// ------------------------------------------------------------------

#ifndef CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE
#define CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE 0
#endif

#ifndef CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE
#define CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE 0
#endif

#ifndef CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE
#define CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE 0
#endif

#ifndef CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE
#define CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE 0
#endif

static void _mcpl_install_route(uint32_t key, uint32_t mask, uint route) {
    uint entry = rtr_alloc(1);
    if (entry == 0) {
        return;
    }
    (void)rtr_mc_set(entry, key, mask, route);
}

void cra_state_mcpl_lookup_send_request(uint32_t seq_id, uint32_t key_id, uint8_t lookup_type, uint8_t dest_core) {
    cra_state_mcpl_lookup_send_request_shard(seq_id, key_id, lookup_type, CRA_MCPL_SHARD_ID, dest_core);
}

void cra_state_mcpl_lookup_send_request_shard(uint32_t seq_id, uint32_t key_id, uint8_t lookup_type, uint8_t shard_id, uint8_t dest_core) {
    (void)dest_core;  // routing table decides delivery by key/mask
    uint32_t key = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REQUEST, lookup_type, shard_id, seq_id);
    spin1_send_mc_packet(key, key_id, WITH_PAYLOAD);
}

void cra_state_mcpl_lookup_send_reply(uint32_t seq_id, int32_t value, int32_t confidence, uint8_t hit, uint8_t lookup_type, uint8_t dest_core) {
    cra_state_mcpl_lookup_send_reply_shard(seq_id, value, confidence, hit, 0, lookup_type, CRA_MCPL_SHARD_ID, dest_core);
}

void cra_state_mcpl_lookup_send_reply_shard(uint32_t seq_id, int32_t value, int32_t confidence, uint8_t hit, uint8_t status, uint8_t lookup_type, uint8_t shard_id, uint8_t dest_core) {
    (void)dest_core;  // routing table decides delivery by key/mask
    uint32_t value_key = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, lookup_type, shard_id, seq_id);
    uint32_t meta_key = MAKE_MCPL_KEY_SHARD(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, lookup_type, shard_id, seq_id);
    spin1_send_mc_packet(value_key, (uint32_t)value, WITH_PAYLOAD);
    spin1_send_mc_packet(meta_key, PACK_MCPL_LOOKUP_META(confidence, hit, status), WITH_PAYLOAD);
}

void cra_state_mcpl_lookup_receive(uint32_t key, uint32_t payload) {
    uint8_t msg_type = EXTRACT_MCPL_MSG_TYPE(key);
    uint32_t seq_id = EXTRACT_MCPL_SEQ_ID(key);
    uint8_t lookup_type = EXTRACT_MCPL_LOOKUP_TYPE(key);
    uint8_t shard_id = EXTRACT_MCPL_SHARD_ID(key);
    (void)msg_type;
    (void)seq_id;
    (void)lookup_type;
    (void)shard_id;

#ifdef CRA_RUNTIME_PROFILE_LEARNING_CORE
    if (msg_type == MCPL_MSG_LOOKUP_REPLY_VALUE) {
        // Learning core receives reply
        int32_t value = (int32_t)payload;
        (void)_lookup_receive_mcpl_value(seq_id, lookup_type, shard_id, value);
    } else if (msg_type == MCPL_MSG_LOOKUP_REPLY_META) {
        int32_t confidence = EXTRACT_MCPL_LOOKUP_META_CONF(payload);
        uint8_t hit = (uint8_t)EXTRACT_MCPL_LOOKUP_META_HIT(payload);
        uint8_t status = (uint8_t)EXTRACT_MCPL_LOOKUP_META_STATUS(payload);
        (void)_lookup_receive_mcpl_meta(seq_id, lookup_type, shard_id, confidence, hit, status);
    } else if (msg_type == MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC) {
        if (shard_id != (CRA_MCPL_SHARD_ID & MCPL_KEY_SHARD_MASK)) {
            return;
        }
        _lifecycle_receive_active_mask_sync_packet(seq_id, lookup_type, payload);
    }
#endif
#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
    if (msg_type == MCPL_MSG_LOOKUP_REQUEST) {
        if (shard_id != (CRA_MCPL_SHARD_ID & MCPL_KEY_SHARD_MASK)) {
            return;
        }
        // State core receives request
        cra_state_handle_lookup_request(seq_id, payload, lookup_type);
    }
#endif
#ifdef CRA_RUNTIME_PROFILE_LIFECYCLE_CORE
    if (msg_type == MCPL_MSG_LIFECYCLE_EVENT_REQUEST) {
        if (shard_id != (CRA_MCPL_SHARD_ID & MCPL_KEY_SHARD_MASK)) {
            return;
        }
        (void)cra_lifecycle_handle_event_request(
            seq_id,
            lookup_type,
            payload,
            -1,
            -1,
            0,
            0);
    } else if (msg_type == MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE) {
        if (shard_id != (CRA_MCPL_SHARD_ID & MCPL_KEY_SHARD_MASK)) {
            return;
        }
        (void)cra_lifecycle_handle_trophic_request(
            seq_id,
            seq_id,
            (int32_t)payload,
            0);
    }
#endif
}

void cra_state_mcpl_init(uint8_t core_id) {
#ifdef CRA_USE_MCPL_LOOKUP
#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE) || defined(CRA_RUNTIME_PROFILE_ROUTE_CORE) || defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
    // State core: route REQUEST keys to this core
    uint8_t lookup_type =
#if defined(CRA_RUNTIME_PROFILE_CONTEXT_CORE)
        LOOKUP_TYPE_CONTEXT;
#elif defined(CRA_RUNTIME_PROFILE_ROUTE_CORE)
        LOOKUP_TYPE_ROUTE;
#elif defined(CRA_RUNTIME_PROFILE_MEMORY_CORE)
        LOOKUP_TYPE_MEMORY;
#else
        0;
#endif
    uint32_t key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, lookup_type, 0);
    uint32_t mask = 0xFFFFF000;  // match app/msg/lookup/shard, ignore seq_id
    uint route = MC_CORE_ROUTE(core_id);
    _mcpl_install_route(key, mask, route);
#if CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE
    // Remote state-chip path: replies are routed back over an explicit chip
    // link. The route is specific to this state profile's lookup type so
    // context/route/memory cores do not install duplicate broad reply routes.
    uint reply_route = CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE;
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, lookup_type, 0);
    _mcpl_install_route(key, mask, reply_route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, lookup_type, 0);
    _mcpl_install_route(key, mask, reply_route);
#endif
#elif defined(CRA_RUNTIME_PROFILE_LEARNING_CORE)
    // Learning core: route VALUE and META reply keys to this core.
    // Match app/msg/shard, ignore lookup_type and seq_id.
    uint32_t key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_VALUE, 0, 0);
    uint32_t mask = 0xFFF0F000;
    uint route = MC_CORE_ROUTE(core_id);
    _mcpl_install_route(key, mask, route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REPLY_META, 0, 0);
    _mcpl_install_route(key, mask, route);
#if CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE
    // Source-chip path: lookup requests leave the learning chip over an
    // explicit chip link. Destination state chips install matching local-core
    // routes for the same request keys.
    uint request_route = CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE;
    mask = 0xFFFFF000;  // match app/msg/lookup/shard, ignore seq_id
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_CONTEXT, 0);
    _mcpl_install_route(key, mask, request_route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_ROUTE, 0);
    _mcpl_install_route(key, mask, request_route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_MEMORY, 0);
    _mcpl_install_route(key, mask, request_route);
#endif
    // Learning/consumer core: route lifecycle active-mask/lineage sync packets
    // to this core. Inter-chip lifecycle smoke uses this as the consumer-side
    // readback proof that a lifecycle core's mask sync crossed the chip link.
    mask = 0xFFF0F000;  // match app/msg/shard, ignore lifecycle subtype and seq
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0);
    _mcpl_install_route(key, mask, route);
#if CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE
    // Source-chip path for lifecycle traffic: event/trophic requests leave the
    // learning chip over an explicit chip link. Destination lifecycle cores
    // install matching local-core routes for the same message types.
    uint lifecycle_request_route = CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE;
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0);
    _mcpl_install_route(key, mask, lifecycle_request_route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0);
    _mcpl_install_route(key, mask, lifecycle_request_route);
#endif
#elif defined(CRA_RUNTIME_PROFILE_LIFECYCLE_CORE)
    // Lifecycle core: route lifecycle event/trophic requests to this core.
    uint32_t key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0);
    uint32_t mask = 0xFFF0F000;  // match app/msg/shard, ignore subtype and seq
    uint route = MC_CORE_ROUTE(core_id);
    _mcpl_install_route(key, mask, route);
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0);
    _mcpl_install_route(key, mask, route);
#if CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE
    // Lifecycle state-chip path: active-mask/lineage sync packets leave the
    // lifecycle chip over an explicit chip link back to learning/consumer cores.
    uint sync_route = CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE;
    key = MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0);
    _mcpl_install_route(key, mask, sync_route);
#endif
#else
    (void)core_id;
#endif
#else
    (void)core_id;
#endif  // CRA_USE_MCPL_LOOKUP
}

void cra_state_get_summary(cra_state_summary_t *summary_out) {
    if (summary_out == 0) {
        return;
    }
    *summary_out = g_summary;
}
