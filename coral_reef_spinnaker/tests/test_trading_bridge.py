"""Unit tests for TradingBridge and PaperTrader algorithms."""

import math
import unittest
from dataclasses import dataclass

from coral_reef_spinnaker.trading_bridge import (
    TradingConfig,
    TradingBridge,
    TaskOutcomeSurface,
    PaperTrader,
)


@dataclass
class MockPolypState:
    polyp_id: int
    current_prediction: float = 0.0
    last_raw_rpe: float = 0.0
    last_output_signed_contribution: float = 0.0
    output_scale: float = 0.1
    activity_rate: float = 0.5
    is_alive: bool = True


class TestTradingConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = TradingConfig()
        self.assertGreater(cfg.initial_capital, 0)
        self.assertGreater(cfg.evaluation_horizon_bars, 0)


class TestTaskOutcomeSurface(unittest.TestCase):
    def test_held_position(self):
        t = TaskOutcomeSurface(
            colony_prediction=0.5,
            task_signal=0.3,
            actual_return_1m=0.3,
            actual_return_5m=0.3,
            raw_dopamine=0.1,
            capital=1.0,
            position_size=0.1,
            direction_correct=True,
        )
        self.assertEqual(t.held_position, 0.1)


class TestPaperTrader(unittest.TestCase):
    def setUp(self):
        self.pt = PaperTrader(config=TradingConfig(), stream_key="EUR/USD")

    def test_initial_state(self):
        self.assertEqual(self.pt.capital, 1.0)
        self.assertEqual(self.pt.position, 0.0)
        self.assertEqual(self.pt.step_count, 0)

    def test_step_no_trade(self):
        outcome = self.pt.step(colony_prediction=0.0, actual_return_1m=0.01, dt_seconds=60.0)
        self.assertIsInstance(outcome, TaskOutcomeSurface)

    def test_step_long_position(self):
        outcome = self.pt.step(colony_prediction=0.5, actual_return_1m=0.01, dt_seconds=60.0)
        self.assertGreater(self.pt.position, 0.0)

    def test_step_short_position(self):
        outcome = self.pt.step(colony_prediction=-0.5, actual_return_1m=-0.01, dt_seconds=60.0)
        self.assertLess(self.pt.position, 0.0)

    def test_step_produces_direction_correct(self):
        outcome = self.pt.step(colony_prediction=1.0, actual_return_1m=0.01, dt_seconds=60.0)
        self.assertTrue(outcome.direction_correct)

    def test_step_produces_direction_incorrect(self):
        outcome = self.pt.step(colony_prediction=1.0, actual_return_1m=-0.01, dt_seconds=60.0)
        self.assertFalse(outcome.direction_correct)

    def test_sharpe_ratio_no_history(self):
        # No returns yet -> sharpe should be 0 or NaN
        sharpe = self.pt.sharpe_ratio
        self.assertTrue(math.isnan(sharpe) or sharpe == 0.0)

    def test_time_in_market(self):
        self.assertEqual(self.pt.time_in_market_fraction, 0.0)
        self.pt.step(colony_prediction=1.0, actual_return_1m=0.01, dt_seconds=60.0)
        self.assertGreater(self.pt.time_in_market_fraction, 0.0)


class TestTradingBridgePrediction(unittest.TestCase):
    def setUp(self):
        cfg = TradingConfig(evaluation_horizon_bars=5)
        self.tb = TradingBridge(config=cfg, stream_key="EUR/USD")

    def test_empty_colony_prediction(self):
        pred = self.tb.compute_colony_prediction([], {})
        self.assertEqual(pred, 0.0)

    def test_colony_prediction_averaging(self):
        states = [
            MockPolypState(polyp_id=0, last_raw_rpe=0.3, current_prediction=0.3),
            MockPolypState(polyp_id=1, last_raw_rpe=-0.1, current_prediction=-0.1),
            MockPolypState(polyp_id=2, last_raw_rpe=0.2, current_prediction=0.2),
        ]
        pred = self.tb.compute_colony_prediction(states, {0: 5, 1: 3, 2: 4})
        self.assertNotEqual(pred, 0.0)

    def test_evaluate_step_returns_outcome(self):
        states = [
            MockPolypState(polyp_id=0, last_raw_rpe=0.3, current_prediction=0.3),
            MockPolypState(polyp_id=1, last_raw_rpe=-0.1, current_prediction=-0.1),
        ]
        outcome = self.tb.evaluate_step(
            market_return_1m=0.01,
            dt_seconds=60.0,
            polyp_states=states,
            spike_counts={0: 5, 1: 3},
        )
        self.assertIsInstance(outcome, TaskOutcomeSurface)
        self.assertIsNotNone(outcome.colony_prediction)


class TestPerPolypReward(unittest.TestCase):
    def setUp(self):
        cfg = TradingConfig()
        self.tb = TradingBridge(config=cfg, stream_key="EUR/USD")

    def test_reward_same_sign(self):
        # Prediction and return same sign -> positive reward
        task = TaskOutcomeSurface(
            colony_prediction=0.5, task_signal=0.3,
            actual_return_1m=0.01, actual_return_5m=0.05,
            raw_dopamine=0.1, capital=1.0, position_size=0.1,
            direction_correct=True,
        )
        p = MockPolypState(polyp_id=0, current_prediction=0.5, last_raw_rpe=0.1)
        reward = self.tb.compute_per_polyp_reward(p, task, colony_prediction=0.5)
        self.assertGreater(reward, 0.0)

    def test_reward_opposite_sign(self):
        # Prediction and return opposite sign -> negative reward
        task = TaskOutcomeSurface(
            colony_prediction=0.5, task_signal=0.3,
            actual_return_1m=0.01, actual_return_5m=-0.05,
            raw_dopamine=0.1, capital=1.0, position_size=0.1,
            direction_correct=False,
        )
        p = MockPolypState(polyp_id=0, current_prediction=0.5, last_raw_rpe=0.1)
        reward = self.tb.compute_per_polyp_reward(p, task, colony_prediction=0.5)
        self.assertLess(reward, 0.0)

    def test_reward_zero_prediction(self):
        task = TaskOutcomeSurface(
            colony_prediction=0.5, task_signal=0.3,
            actual_return_1m=0.01, actual_return_5m=0.05,
            raw_dopamine=0.1, capital=1.0, position_size=0.1,
            direction_correct=True,
        )
        p = MockPolypState(polyp_id=0, current_prediction=0.0, last_raw_rpe=0.1)
        reward = self.tb.compute_per_polyp_reward(p, task, colony_prediction=0.5)
        self.assertEqual(reward, 0.0)


class TestTradingBridgeSign(unittest.TestCase):
    def test_sign_positive(self):
        self.assertEqual(TradingBridge._sign(5.0), 1)

    def test_sign_negative(self):
        self.assertEqual(TradingBridge._sign(-3.0), -1)

    def test_sign_zero(self):
        self.assertEqual(TradingBridge._sign(0.0), 0)


if __name__ == "__main__":
    unittest.main()
