import pytest

from coral_reef_spinnaker.runtime_modes import (
    chunk_ranges,
    estimate_plans,
    make_runtime_plan,
)


def test_step_host_plan_is_current_implementation():
    plan = make_runtime_plan(
        runtime_mode="step",
        learning_location="host",
        chunk_size_steps=1,
        total_steps=120,
        dt_seconds=0.05,
    )

    assert plan.implemented is True
    assert plan.implementation_stage == "current_step_host_loop"
    assert plan.sim_run_calls == 120
    assert plan.call_reduction_factor == 1.0


def test_chunked_host_plan_is_implemented_after_local_parity_gate():
    plan = make_runtime_plan(
        runtime_mode="chunked",
        learning_location="host",
        chunk_size_steps=25,
        total_steps=1200,
        dt_seconds=0.05,
    )

    assert plan.implemented is True
    assert plan.implementation_stage == "chunked_host_stepcurrent_binned_replay"
    assert plan.sim_run_calls == 48
    assert plan.call_reduction_factor == 25.0
    assert plan.blockers == ()


def test_future_learning_locations_are_explicitly_not_implemented():
    plan = make_runtime_plan(
        runtime_mode="continuous",
        learning_location="on_chip",
        chunk_size_steps=1200,
        total_steps=1200,
        dt_seconds=0.05,
    )

    assert plan.implemented is False
    assert plan.implementation_stage == "future_custom_runtime"
    assert "custom_c_or_backend_native_closed_loop" in plan.blockers


def test_step_mode_rejects_chunk_size_greater_than_one():
    with pytest.raises(ValueError, match="step runtime mode requires"):
        make_runtime_plan(
            runtime_mode="step",
            learning_location="host",
            chunk_size_steps=2,
            total_steps=120,
            dt_seconds=0.05,
        )


def test_chunk_ranges_are_half_open_and_cover_total_steps():
    ranges = chunk_ranges(total_steps=10, chunk_size_steps=4)

    assert ranges == [(0, 4), (4, 8), (8, 10)]


def test_estimate_plans_deduplicates_chunk_sizes():
    plans = estimate_plans(total_steps=100, dt_seconds=0.05, chunk_sizes=[1, 5, 5, 20])

    assert [p.chunk_size_steps for p in plans] == [1, 5, 20]
    assert [p.runtime_mode for p in plans] == ["step", "chunked", "chunked"]


def test_tier416b_debug_uses_canonical_hard_switch_defaults():
    from experiments import tier4_16b_hard_switch_debug as debug
    from experiments import tier4_harder_spinnaker_capsule as capsule

    args = debug.build_parser().parse_args(["--backends", "nest", "--seeds", "42"])

    assert args.min_switch_interval == capsule.DEFAULT_HARD_MIN_SWITCH_INTERVAL
    assert args.max_switch_interval == capsule.DEFAULT_HARD_MAX_SWITCH_INTERVAL
    assert args.sensory_noise_fraction == capsule.DEFAULT_HARD_SENSORY_NOISE_FRACTION
    assert args.noise_prob == capsule.DEFAULT_HARD_NOISE_PROB

    task = debug.build_task(42, args)
    assert task.switch_steps[:4] == [0, 44, 81, 122]
