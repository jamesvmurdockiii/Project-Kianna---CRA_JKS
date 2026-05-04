"""Unit tests for LearningManager algorithms.

These tests exercise the pure computational methods of LearningManager
without needing a full organism, simulator, or PyNN backend.
"""

import math
import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import numpy as np

from coral_reef_spinnaker.learning_manager import (
    LearningConfig,
    LearningManager,
    LearningResult,
    CalcificationState,
    PendingHorizon,
)
from coral_reef_spinnaker.trading_bridge import TaskOutcomeSurface


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------

@dataclass
class MockPolypState:
    """Minimal polyp state for LearningManager tests."""

    polyp_id: int
    dopamine_ema: float = 0.0
    last_mi: float = 0.5
    uptake_rate: float = 0.1
    da_gain: float = 0.5
    activity_rate: float = 0.5
    directional_accuracy_ema: float = 0.5
    output_scale: float = 0.1
    last_raw_rpe: float = 0.0
    last_output_signed_contribution: float = 0.0
    last_net_matured_consequence_credit: float = 0.0
    bax_activation: float = 0.0
    calcification: float = 0.0
    is_alive: bool = True

    def step_dopamine(self, raw_dopamine: float, dt_ms: float) -> None:
        # Simple EMA update
        alpha = dt_ms / (100.0 + dt_ms)
        self.dopamine_ema = alpha * raw_dopamine + (1 - alpha) * self.dopamine_ema

    def compute_drive(self) -> float:
        return self.last_mi * self.uptake_rate + self.da_gain * self.dopamine_ema


@dataclass
class MockEdge:
    """Minimal edge for LearningManager tests."""

    source_id: int
    target_id: int
    weight: float = 0.5
    calcification: float = 0.0
    is_pruned: bool = False
    edge_type: str = "ff"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLearningManagerBasics(unittest.TestCase):
    def test_default_config(self):
        cfg = LearningConfig()
        self.assertGreater(cfg.stdp_weight_max, cfg.stdp_weight_min)
        self.assertEqual(cfg.stdp_weight_max, 1.0)

    def test_init_with_none_config(self):
        lm = LearningManager(config=None)
        self.assertIsNotNone(lm.config)
        self.assertIsInstance(lm.config, LearningConfig)


class TestSTDPAlgorithms(unittest.TestCase):
    def setUp(self):
        self.cfg = LearningConfig(
            stdp_a_plus=0.01,
            stdp_a_minus=0.01,
            stdp_tau_plus=20.0,
            stdp_tau_minus=20.0,
        )
        self.lm = LearningManager(config=self.cfg)

    def test_stdp_pair_rule_ltp(self):
        # Pre before post by 10 ms -> LTP (positive dw)
        dw = self.lm.stdp_pair_rule(pre_time=0.0, post_time=10.0)
        self.assertGreater(dw, 0.0)
        # Should be A_plus * exp(-10/20) = 0.01 * exp(-0.5)
        expected = 0.01 * math.exp(-0.5)
        self.assertAlmostEqual(dw, expected, places=6)

    def test_stdp_pair_rule_ltd(self):
        # Post before pre by 10 ms -> LTD (negative dw)
        dw = self.lm.stdp_pair_rule(pre_time=10.0, post_time=0.0)
        self.assertLess(dw, 0.0)
        expected = -0.01 * math.exp(-0.5)
        self.assertAlmostEqual(dw, expected, places=6)

    def test_stdp_pair_rule_simultaneous(self):
        dw = self.lm.stdp_pair_rule(pre_time=5.0, post_time=5.0)
        self.assertEqual(dw, 0.0)

    def test_apply_weight_bounds(self):
        self.assertEqual(self.lm.apply_weight_bounds(0.5), 0.5)
        self.assertEqual(self.lm.apply_weight_bounds(-0.1), 0.0)  # clipped to min
        self.assertEqual(self.lm.apply_weight_bounds(1.5), 1.0)  # clipped to max

    def test_apply_dopamine_modulation_positive(self):
        dw = self.lm.apply_dopamine_modulation(dw_base=0.1, dopamine_ema=0.5)
        # modulation = max(0.2, 1.0 + 1.0 * 0.5) = 1.5
        self.assertAlmostEqual(dw, 0.15, places=6)

    def test_apply_dopamine_modulation_negative(self):
        dw = self.lm.apply_dopamine_modulation(dw_base=0.1, dopamine_ema=-2.0)
        # modulation = max(0.2, 1.0 - 2.0) = 0.2 (floored)
        self.assertAlmostEqual(dw, 0.02, places=6)


class TestDopamineComputation(unittest.TestCase):
    def setUp(self):
        self.lm = LearningManager(config=LearningConfig())

    def test_compute_raw_dopamine_same_sign(self):
        # pred and signal same sign -> positive dopamine
        da = self.lm.compute_raw_dopamine(colony_pred=0.5, task_signal=0.3)
        self.assertGreater(da, 0.0)

    def test_compute_raw_dopamine_opposite_sign(self):
        # pred and signal opposite sign -> negative dopamine
        da = self.lm.compute_raw_dopamine(colony_pred=0.5, task_signal=-0.3)
        self.assertLess(da, 0.0)

    def test_compute_raw_dopamine_zero(self):
        da = self.lm.compute_raw_dopamine(colony_pred=0.0, task_signal=0.3)
        self.assertEqual(da, 0.0)

    def test_compute_raw_dopamine_saturates(self):
        # Very large RPE should saturate via tanh to ~1.0
        da = self.lm.compute_raw_dopamine(colony_pred=10.0, task_signal=10.0)
        # dopamine_gain=10000 with seed output scale still saturates.
        self.assertAlmostEqual(da, 1.0, places=5)


class TestWinnerTakeAll(unittest.TestCase):
    def setUp(self):
        self.lm = LearningManager(config=LearningConfig(winner_take_all_base=3))

    def test_empty_population(self):
        winners = self.lm.winner_take_all_selection([], {"rates": {}})
        self.assertEqual(winners, [])

    def test_selects_top_k(self):
        states = [
            MockPolypState(polyp_id=0, last_raw_rpe=0.1),
            MockPolypState(polyp_id=1, last_raw_rpe=0.5),
            MockPolypState(polyp_id=2, last_raw_rpe=0.3),
            MockPolypState(polyp_id=3, last_raw_rpe=0.9),
            MockPolypState(polyp_id=4, last_raw_rpe=0.0),
        ]
        winners = self.lm.winner_take_all_selection(states, {"rates": {}})
        # k = max(3, int(sqrt(5))) = 3
        self.assertEqual(len(winners), 3)
        ids = [w[0] for w in winners]
        self.assertEqual(ids, [3, 1, 2])

    def test_tiebreak_by_activity(self):
        states = [
            MockPolypState(polyp_id=0, last_raw_rpe=0.5, activity_rate=0.1),
            MockPolypState(polyp_id=1, last_raw_rpe=0.5, activity_rate=0.9),
        ]
        winners = self.lm.winner_take_all_selection(
            states, {"rates": {}}
        )
        # Same RPE, higher activity wins tiebreak
        self.assertEqual(winners[0][0], 1)


class TestHomeostasis(unittest.TestCase):
    def setUp(self):
        self.cfg = LearningConfig(
            homeostasis_target_rate_hz=50.0,
            homeostasis_strength=0.1,
        )
        self.lm = LearningManager(config=self.cfg)

    def test_compute_homeostatic_scale_no_change(self):
        scale = self.lm.compute_homeostatic_scale(activity_rate=50.0)
        self.assertEqual(scale, 1.0)

    def test_compute_homeostatic_scale_high_activity(self):
        # Activity above target -> scale < 1 (weaken)
        scale = self.lm.compute_homeostatic_scale(activity_rate=100.0)
        self.assertLess(scale, 1.0)
        self.assertGreaterEqual(scale, 0.9)

    def test_compute_homeostatic_scale_low_activity(self):
        # Activity below target -> scale > 1 (strengthen)
        scale = self.lm.compute_homeostatic_scale(activity_rate=10.0)
        self.assertGreater(scale, 1.0)
        self.assertLessEqual(scale, 1.1)

    def test_apply_homeostasis(self):
        edges = {
            (0, 1): MockEdge(source_id=0, target_id=1, weight=0.5),
            (1, 1): MockEdge(source_id=1, target_id=1, weight=0.6),
            (0, 2): MockEdge(source_id=0, target_id=2, weight=0.4),
        }
        states = [
            MockPolypState(polyp_id=1, activity_rate=100.0),
            MockPolypState(polyp_id=2, activity_rate=10.0),
        ]
        self.lm.apply_homeostasis(states, edges, dt_ms=1.0)
        # Polyp 1 is too active -> incoming weights should decrease
        self.assertLess(edges[(0, 1)].weight, 0.5)
        self.assertLess(edges[(1, 1)].weight, 0.6)
        # Polyp 2 is too quiet -> incoming weights should increase
        self.assertGreater(edges[(0, 2)].weight, 0.4)


class TestPlasticityTemperature(unittest.TestCase):
    def setUp(self):
        self.lm = LearningManager(config=LearningConfig(plasticity_bocpd_weight=2.0))

    def test_no_changepoint(self):
        t = self.lm.compute_plasticity_temperature(0.0)
        self.assertEqual(t, 1.0)

    def test_full_changepoint(self):
        t = self.lm.compute_plasticity_temperature(1.0)
        self.assertEqual(t, 3.0)

    def test_clamps_input(self):
        t = self.lm.compute_plasticity_temperature(5.0)
        self.assertEqual(t, 3.0)


class TestCalcification(unittest.TestCase):
    def setUp(self):
        self.lm = LearningManager(config=LearningConfig())

    def test_calcification_state_update(self):
        cs = CalcificationState(edge_key=(0, 1), calcification=0.0)
        matured = cs.update(weight_change=0.1, step=1, temperature=1.0)
        self.assertGreater(cs.synaptic_tag, 0.0)

    def test_calcification_frozen(self):
        cs = CalcificationState(edge_key=(0, 1), calcification=1.0)
        self.assertEqual(cs.calcification, 1.0)

    def test_check_unlock_temperature_high(self):
        cs = CalcificationState(edge_key=(0, 1), calcification=0.5)
        # High temperature (>2.0) should unlock moderately calcified synapses
        self.assertTrue(self.lm.check_calcification_unlock(cs, temperature=3.0))

    def test_check_unlock_temperature_low(self):
        cs = CalcificationState(edge_key=(0, 1), calcification=1.0)
        # Low temperature should not unlock heavily calcified synapses
        self.assertFalse(self.lm.check_calcification_unlock(cs, temperature=1.0))

    def test_check_unlock_heavily_calcified(self):
        cs = CalcificationState(edge_key=(0, 1), calcification=0.99)
        # Even high temp won't unlock if calcification >= 0.95
        self.assertFalse(self.lm.check_calcification_unlock(cs, temperature=3.0))


class TestHorizonCredit(unittest.TestCase):
    def setUp(self):
        self.lm = LearningManager(config=LearningConfig(evaluation_horizon_bars=3))

    def test_pending_horizon_accumulate(self):
        h = PendingHorizon(polyp_id=1, prediction=0.5, held_position=0.1, creation_step=0)
        h.accumulate_return(0.1)
        h.accumulate_return(-0.05)
        self.assertEqual(len(h.future_returns), 2)

    def test_evaluate_maturity_not_ready(self):
        h = PendingHorizon(polyp_id=1, prediction=0.5, held_position=0.1, creation_step=0)
        h.accumulate_return(0.1)
        # Only 1 bar elapsed, horizon=3 -> returns 0.0 (not enough history)
        matured = h.evaluate_maturity(horizon_bars=3)
        self.assertEqual(matured, 0.0)
        self.assertFalse(h.is_matured)

    def test_evaluate_maturity_ready(self):
        h = PendingHorizon(polyp_id=1, prediction=0.5, held_position=0.1, creation_step=0)
        h.accumulate_return(0.1)
        h.accumulate_return(0.2)
        h.accumulate_return(-0.05)
        matured = h.evaluate_maturity(horizon_bars=3)
        self.assertIsNotNone(matured)
        # Credit = sign(pred) * sign(sum) * tanh(abs(sum))
        # sum = 0.25, tanh(0.25) ≈ 0.2449
        self.assertAlmostEqual(matured, math.tanh(0.25), places=6)

    def test_step_creates_horizon_after_advancing_existing_records(self):
        state = MockPolypState(
            polyp_id=1,
            last_raw_rpe=1.0,
            last_output_signed_contribution=1.0,
        )
        state.last_prediction_feature = 1.0
        edges = {}

        task0 = TaskOutcomeSurface(
            colony_prediction=1.0,
            actual_return_1m=0.0,
            actual_return_5m=0.0,
        )
        self.lm.step(
            polyp_states=[state],
            spike_data={"spike_counts": {1: 1}},
            task_outcome=task0,
            edges=edges,
            step_num=0,
            dt_ms=1.0,
        )

        created = [h for h in self.lm.pending_horizons if h.creation_step == 0]
        self.assertEqual(len(created), 1)
        self.assertEqual(len(created[0].future_returns), 0)

        task1 = TaskOutcomeSurface(
            colony_prediction=1.0,
            actual_return_1m=0.1,
            actual_return_5m=0.1,
        )
        self.lm.step(
            polyp_states=[state],
            spike_data={"spike_counts": {1: 1}},
            task_outcome=task1,
            edges=edges,
            step_num=1,
            dt_ms=1.0,
        )

        created = [h for h in self.lm.pending_horizons if h.creation_step == 0]
        self.assertEqual(len(created), 1)
        self.assertEqual(list(created[0].future_returns), [0.1])

    def test_horizon_one_does_not_update_delayed_readout(self):
        lm = LearningManager(config=LearningConfig(evaluation_horizon_bars=1))
        state = MockPolypState(polyp_id=1)
        state.predictive_readout_weight = 0.25
        horizon = PendingHorizon(
            polyp_id=1,
            prediction=1.0,
            held_position=1.0,
            creation_step=0,
            prediction_feature=1.0,
            is_matured=True,
            gross_matured_credit=1.0,
        )

        lm.update_predictive_readouts_from_matured(
            polyp_states=[state],
            matured_horizons=[horizon],
        )

        self.assertEqual(state.predictive_readout_weight, 0.25)

    def test_true_delayed_horizon_updates_delayed_readout(self):
        lm = LearningManager(config=LearningConfig(evaluation_horizon_bars=3))
        state = MockPolypState(polyp_id=1)
        state.predictive_readout_weight = 0.25
        horizon = PendingHorizon(
            polyp_id=1,
            prediction=1.0,
            held_position=1.0,
            creation_step=0,
            prediction_feature=1.0,
            is_matured=True,
            gross_matured_credit=1.0,
        )

        lm.update_predictive_readouts_from_matured(
            polyp_states=[state],
            matured_horizons=[horizon],
        )

        self.assertGreater(state.predictive_readout_weight, 0.25)

    def test_delayed_readout_respects_per_polyp_lr_scale(self):
        lm = LearningManager(
            config=LearningConfig(
                evaluation_horizon_bars=3,
                delayed_readout_learning_rate=0.05,
                readout_weight_decay=0.0,
            )
        )
        frozen = MockPolypState(polyp_id=1)
        fast = MockPolypState(polyp_id=2)
        frozen.predictive_readout_weight = 0.25
        fast.predictive_readout_weight = 0.25
        frozen.predictive_readout_lr_scale = 0.0
        fast.predictive_readout_lr_scale = 2.0
        horizons = [
            PendingHorizon(
                polyp_id=1,
                prediction=1.0,
                held_position=1.0,
                creation_step=0,
                prediction_feature=1.0,
                is_matured=True,
                gross_matured_credit=1.0,
            ),
            PendingHorizon(
                polyp_id=2,
                prediction=1.0,
                held_position=1.0,
                creation_step=0,
                prediction_feature=1.0,
                is_matured=True,
                gross_matured_credit=1.0,
            ),
        ]

        lm.update_predictive_readouts_from_matured(
            polyp_states=[frozen, fast],
            matured_horizons=horizons,
        )

        self.assertEqual(frozen.predictive_readout_weight, 0.25)
        self.assertAlmostEqual(fast.predictive_readout_weight, 0.35)


class TestLearningManagerStep(unittest.TestCase):
    def setUp(self):
        self.cfg = LearningConfig(
            stdp_weight_max=1.0,
            stdp_weight_min=0.0,
            stdp_a_plus=0.01,
            winner_take_all_base=3,
        )
        self.lm = LearningManager(config=self.cfg)

    def test_step_returns_result(self):
        states = [
            MockPolypState(polyp_id=0, last_raw_rpe=0.1, activity_rate=0.5),
            MockPolypState(polyp_id=1, last_raw_rpe=-0.1, activity_rate=0.5),
        ]
        edges = {
            (0, 1): MockEdge(source_id=0, target_id=1, weight=0.5),
        }
        task = TaskOutcomeSurface(
            colony_prediction=0.5,
            task_signal=0.3,
            actual_return_1m=0.3,
            actual_return_5m=0.3,
            raw_dopamine=0.1,
            capital=1.0,
            position_size=0.1,
            direction_correct=True,
        )
        result = self.lm.step(
            polyp_states=states,
            spike_data={"spike_counts": {0: 5, 1: 3}},
            task_outcome=task,
            edges=edges,
            step_num=0,
            dt_ms=1000.0,
        )
        self.assertIsInstance(result, LearningResult)


if __name__ == "__main__":
    unittest.main()
