"""Regression tests for CRA stabilization and source-of-truth fixes."""

import math
import unittest

import numpy as np

from coral_reef_spinnaker.config import LearningConfig, ReefConfig
from coral_reef_spinnaker.config_adapters import (
    energy_manager_config,
    learning_manager_config,
)
from coral_reef_spinnaker.learning_manager import LearningManager
from coral_reef_spinnaker.mock_simulator import MockSimulator
from coral_reef_spinnaker.polyp_population import PolypPopulation
from coral_reef_spinnaker.polyp_state import PolypState
from coral_reef_spinnaker.task_adapter import (
    Observation,
    SignedClassificationAdapter,
)
from coral_reef_spinnaker.trading_bridge import TaskOutcomeSurface


class TestConfigSourceOfTruth(unittest.TestCase):
    def test_adapters_return_root_configs(self):
        cfg = ReefConfig.default()
        cfg.energy.bdnf_per_trophic_source = 0.031
        cfg.learning.dopamine_gain = 1234.0

        self.assertIs(energy_manager_config(cfg), cfg.energy)
        self.assertIs(learning_manager_config(cfg), cfg.learning)

    def test_memory_population_cap_respects_hard_cap(self):
        cfg = ReefConfig.default()
        cfg.lifecycle.max_population_hard = 32
        cfg.lifecycle.max_population_from_memory = True

        self.assertLessEqual(cfg.max_population, 32)

    def test_neuron_threshold_is_consistent_with_polyp_default(self):
        cfg = ReefConfig.default()

        self.assertEqual(cfg.network.v_thresh, -55.0)
        self.assertEqual(cfg.neuron_params["v_thresh"], -55.0)

    def test_context_memory_defaults_are_disabled(self):
        cfg = ReefConfig.default()

        self.assertFalse(cfg.learning.context_memory_enabled)
        self.assertEqual(cfg.learning.context_memory_mode, "normal")
        self.assertEqual(cfg.learning.context_memory_slot_count, 1)
        self.assertEqual(cfg.learning.context_memory_key_metadata, "context_memory_key")
        self.assertFalse(cfg.learning.predictive_context_enabled)
        self.assertEqual(cfg.learning.predictive_context_mode, "keyed")
        self.assertEqual(cfg.learning.predictive_context_slot_count, 8)
        self.assertEqual(
            cfg.learning.predictive_context_key_metadata,
            "predictive_context_key",
        )


class TestInternalContextMemory(unittest.TestCase):
    def test_context_memory_binds_visible_context_to_later_cue(self):
        cfg = ReefConfig.default()
        cfg.learning.context_memory_enabled = True
        cfg.learning.context_memory_mode = "normal"
        organism = __import__("coral_reef_spinnaker").Organism(
            cfg,
            None,
            use_default_trading_bridge=False,
        )

        context_obs, context_activity = organism._prepare_context_memory_observation(
            observation_value=-0.55,
            metadata={"event_type": "context"},
        )
        decision_obs, decision_activity = organism._prepare_context_memory_observation(
            observation_value=1.0,
            metadata={"event_type": "decision"},
        )

        self.assertEqual(context_obs, -0.55)
        self.assertEqual(context_activity["context_memory_updates"], 1)
        self.assertEqual(context_activity["context_memory_value"], -1)
        self.assertEqual(decision_obs, -1.0)
        self.assertTrue(decision_activity["feature_active"])
        self.assertEqual(decision_activity["feature_source"], "internal_context_bound")
        self.assertEqual(decision_activity["visible_cue_sign"], 1)

    def test_context_memory_wrong_ablation_inverts_bound_cue(self):
        cfg = ReefConfig.default()
        cfg.learning.context_memory_enabled = True
        cfg.learning.context_memory_mode = "wrong"
        organism = __import__("coral_reef_spinnaker").Organism(
            cfg,
            None,
            use_default_trading_bridge=False,
        )

        organism._prepare_context_memory_observation(
            observation_value=-0.55,
            metadata={"event_type": "context"},
        )
        decision_obs, decision_activity = organism._prepare_context_memory_observation(
            observation_value=1.0,
            metadata={"event_type": "decision"},
        )

        self.assertEqual(decision_obs, 1.0)
        self.assertEqual(decision_activity["feature_source"], "internal_wrong_context")

    def test_keyed_context_memory_keeps_overlapping_slots_separate(self):
        cfg = ReefConfig.default()
        cfg.learning.context_memory_enabled = True
        cfg.learning.context_memory_mode = "keyed"
        cfg.learning.context_memory_slot_count = 2
        organism = __import__("coral_reef_spinnaker").Organism(
            cfg,
            None,
            use_default_trading_bridge=False,
        )

        organism._prepare_context_memory_observation(
            observation_value=1.0,
            metadata={"event_type": "context", "context_memory_key": "A"},
        )
        organism._prepare_context_memory_observation(
            observation_value=-1.0,
            metadata={"event_type": "context", "context_memory_key": "B"},
        )
        decision_obs, decision_activity = organism._prepare_context_memory_observation(
            observation_value=1.0,
            metadata={"event_type": "decision", "context_memory_key": "A"},
        )

        self.assertEqual(decision_obs, 1.0)
        self.assertTrue(decision_activity["feature_active"])
        self.assertEqual(decision_activity["feature_source"], "internal_keyed_context")
        self.assertEqual(decision_activity["context_memory_key"], "A")
        self.assertEqual(decision_activity["context_memory_slot_count"], 2)

    def test_keyed_context_memory_lru_eviction_is_bounded(self):
        cfg = ReefConfig.default()
        cfg.learning.context_memory_enabled = True
        cfg.learning.context_memory_mode = "keyed"
        cfg.learning.context_memory_slot_count = 1
        organism = __import__("coral_reef_spinnaker").Organism(
            cfg,
            None,
            use_default_trading_bridge=False,
        )

        organism._prepare_context_memory_observation(
            observation_value=1.0,
            metadata={"event_type": "context", "context_memory_key": "A"},
        )
        organism._prepare_context_memory_observation(
            observation_value=-1.0,
            metadata={"event_type": "context", "context_memory_key": "B"},
        )

        self.assertNotIn("A", organism._context_memory_slots)
        self.assertEqual(organism._context_memory_slots["B"], -1)

    def test_context_replay_restores_evicted_keyed_slot(self):
        cfg = ReefConfig.default()
        cfg.learning.context_memory_enabled = True
        cfg.learning.context_memory_mode = "keyed"
        cfg.learning.context_memory_slot_count = 2
        organism = __import__("coral_reef_spinnaker").Organism(
            cfg,
            None,
            use_default_trading_bridge=False,
        )

        organism._prepare_context_memory_observation(
            observation_value=1.0,
            metadata={"event_type": "context", "context_memory_key": "A"},
        )
        organism._prepare_context_memory_observation(
            observation_value=-1.0,
            metadata={"event_type": "context", "context_memory_key": "B"},
        )
        organism._prepare_context_memory_observation(
            observation_value=-1.0,
            metadata={"event_type": "context", "context_memory_key": "C"},
        )
        self.assertNotIn("A", organism._context_memory_slots)

        replay = organism.replay_context_memory_episode(
            context_memory_key="A",
            context_sign=1,
            consolidate=True,
        )
        decision_obs, decision_activity = organism._prepare_context_memory_observation(
            observation_value=1.0,
            metadata={"event_type": "decision", "context_memory_key": "A"},
        )

        self.assertTrue(replay["wrote"])
        self.assertEqual(decision_obs, 1.0)
        self.assertEqual(decision_activity["feature_source"], "internal_keyed_context")

    def test_context_replay_no_consolidation_does_not_write_slot(self):
        cfg = ReefConfig.default()
        cfg.learning.context_memory_enabled = True
        cfg.learning.context_memory_mode = "keyed"
        organism = __import__("coral_reef_spinnaker").Organism(
            cfg,
            None,
            use_default_trading_bridge=False,
        )

        replay = organism.replay_context_memory_episode(
            context_memory_key="A",
            context_sign=1,
            consolidate=False,
        )

        self.assertFalse(replay["wrote"])
        self.assertNotIn("A", organism._context_memory_slots)


class TestInternalPredictiveContext(unittest.TestCase):
    def test_predictive_context_binds_visible_precursor_to_decision(self):
        cfg = ReefConfig.default()
        cfg.learning.predictive_context_enabled = True
        cfg.learning.predictive_context_mode = "keyed"
        cfg.learning.predictive_context_slot_count = 2
        organism = __import__("coral_reef_spinnaker").Organism(
            cfg,
            None,
            use_default_trading_bridge=False,
        )

        cue_obs, cue_activity = organism._prepare_predictive_context_observation(
            observation_value=0.25,
            metadata={
                "predictive_context_update": True,
                "predictive_context_sign": -1,
                "predictive_context_key": "trial:A",
            },
        )
        decision_obs, decision_activity = organism._prepare_predictive_context_observation(
            observation_value=0.0,
            metadata={
                "predictive_context_decision": True,
                "predictive_context_key": "trial:A",
            },
        )

        self.assertEqual(cue_obs, 0.25)
        self.assertEqual(cue_activity["predictive_context_updates"], 1)
        self.assertEqual(cue_activity["predictive_context_value"], -1)
        self.assertEqual(decision_obs, -1.0)
        self.assertTrue(decision_activity["feature_active"])
        self.assertEqual(
            decision_activity["feature_source"],
            "internal_predictive_context",
        )
        self.assertEqual(decision_activity["predictive_context_key"], "trial:A")

    def test_predictive_context_ablation_modes_are_causal_controls(self):
        cfg = ReefConfig.default()
        cfg.learning.predictive_context_enabled = True
        cfg.learning.predictive_context_mode = "wrong"
        organism = __import__("coral_reef_spinnaker").Organism(
            cfg,
            None,
            use_default_trading_bridge=False,
        )

        organism._prepare_predictive_context_observation(
            observation_value=0.25,
            metadata={
                "predictive_context_update": True,
                "predictive_context_sign": -1,
                "predictive_context_key": "trial:A",
            },
        )
        decision_obs, decision_activity = organism._prepare_predictive_context_observation(
            observation_value=0.0,
            metadata={
                "predictive_context_decision": True,
                "predictive_context_key": "trial:A",
            },
        )

        self.assertEqual(decision_obs, 1.0)
        self.assertTrue(decision_activity["feature_active"])
        self.assertEqual(
            decision_activity["feature_source"],
            "internal_wrong_predictive_context",
        )

    def test_predictive_context_lru_eviction_is_bounded(self):
        cfg = ReefConfig.default()
        cfg.learning.predictive_context_enabled = True
        cfg.learning.predictive_context_mode = "keyed"
        cfg.learning.predictive_context_slot_count = 1
        organism = __import__("coral_reef_spinnaker").Organism(
            cfg,
            None,
            use_default_trading_bridge=False,
        )

        organism._prepare_predictive_context_observation(
            observation_value=0.25,
            metadata={
                "predictive_context_update": True,
                "predictive_context_sign": 1,
                "predictive_context_key": "A",
            },
        )
        organism._prepare_predictive_context_observation(
            observation_value=-0.25,
            metadata={
                "predictive_context_update": True,
                "predictive_context_sign": -1,
                "predictive_context_key": "B",
            },
        )

        self.assertNotIn("A", organism._predictive_context_slots)
        self.assertEqual(organism._predictive_context_slots["B"], -1)


class TestCanonicalDopaminePath(unittest.TestCase):
    def test_raw_dopamine_uses_configured_gain_and_output_scale(self):
        lm = LearningManager(
            LearningConfig(dopamine_gain=10.0, seed_output_scale=0.5)
        )

        da = lm.compute_raw_dopamine(
            colony_pred=1.0,
            task_signal=2.0,
            output_scale=0.25,
        )

        self.assertAlmostEqual(da, math.tanh(1.0 * 2.0 * 0.25 * 10.0))

    def test_dopamine_ema_is_updated_once(self):
        lm = LearningManager(LearningConfig(dopamine_tau=100.0))
        p = PolypState(polyp_id=0, lineage_id=0, dopamine_tau_ms=100.0)

        lm.update_polyp_dopamine([p], raw_dopamine=1.0, dt_ms=50.0)

        self.assertAlmostEqual(p.dopamine_ema, 0.5)

    def test_step_overwrites_task_dopamine_with_learning_result(self):
        lm = LearningManager(
            LearningConfig(dopamine_gain=10.0, seed_output_scale=0.5)
        )
        p = PolypState(
            polyp_id=0,
            lineage_id=0,
            last_raw_rpe=1.0,
            current_prediction=1.0,
            last_output_signed_contribution=1.0,
        )
        task = TaskOutcomeSurface(
            colony_prediction=1.0,
            actual_return_5m=1.0,
            raw_dopamine=-1.0,
            dopamine_output_scale=0.25,
        )

        result = lm.step(
            polyp_states=[p],
            spike_data={"rates": {0: 1.0}},
            task_outcome=task,
            edges={},
            step_num=0,
            dt_ms=1.0,
        )

        expected = math.tanh(1.0 * 1.0 * 0.25 * 10.0)
        self.assertAlmostEqual(result.raw_dopamine, expected)
        self.assertAlmostEqual(task.raw_dopamine, expected)


class TestRewardMath(unittest.TestCase):
    def test_dissenting_correct_specialist_gets_positive_reward(self):
        lm = LearningManager(LearningConfig())
        polyp = PolypState(
            polyp_id=1,
            lineage_id=0,
            last_output_signed_contribution=-0.7,
        )
        task = TaskOutcomeSurface(actual_return_5m=-0.2)

        reward = lm.compute_single_reward(polyp, task, colony_pred=0.5)

        self.assertGreater(reward, 0.0)

    def test_zero_prediction_gets_zero_reward(self):
        lm = LearningManager(LearningConfig())
        polyp = PolypState(
            polyp_id=1,
            lineage_id=0,
            last_output_signed_contribution=0.0,
        )
        task = TaskOutcomeSurface(actual_return_5m=0.2)

        reward = lm.compute_single_reward(polyp, task, colony_pred=0.5)

        self.assertEqual(reward, 0.0)

    def test_configured_horizon_controls_maturity(self):
        lm = LearningManager(LearningConfig(evaluation_horizon_bars=7))
        horizon = lm.create_horizon_record(
            polyp_id=1,
            prediction=1.0,
            held_position=1.0,
            step=0,
        )
        lm.pending_horizons.append(horizon)

        for step in range(1, 7):
            lm.advance_horizons(actual_return=0.1, step=step)
            self.assertEqual(len(lm.matured_horizons), 0)

        lm.advance_horizons(actual_return=0.1, step=7)
        self.assertEqual(len(lm.matured_horizons), 1)
        self.assertEqual(len(lm.matured_horizons[0].future_returns), 7)


class TestLifecycleIdentity(unittest.TestCase):
    def tearDown(self):
        MockSimulator.end()

    def test_population_preserves_lifecycle_child_identity(self):
        MockSimulator.setup(timestep=1.0)
        population = PolypPopulation(
            simulator=MockSimulator,
            max_polyps=4,
            label="identity_test",
        )

        founder = PolypState(polyp_id=-1, lineage_id=-1)
        population.add_polyp(founder, preserve_identity=False)

        child = PolypState(polyp_id=7, lineage_id=founder.lineage_id)
        population.add_polyp(child, preserve_identity=True)

        self.assertIsNotNone(population.get_state_by_polyp_id(7))
        self.assertEqual(child.lineage_id, founder.lineage_id)
        self.assertGreaterEqual(population.next_polyp_id, 8)


class TestNonFinanceAdapter(unittest.TestCase):
    def test_signed_classification_encode_and_evaluate(self):
        adapter = SignedClassificationAdapter()
        observation = Observation(
            stream_id="vision",
            x=np.array([2.0, -1.0, 0.5]),
            target=-1.0,
        )

        encoded = adapter.encode(observation, n_channels=5)
        result = adapter.evaluate(
            prediction=-0.3,
            observation=observation,
            dt_seconds=1.0,
        )

        self.assertEqual(encoded.shape, (5,))
        self.assertLessEqual(float(np.max(np.abs(encoded))), 1.0)
        self.assertTrue(result.direction_correct)
        self.assertEqual(result.metadata["adapter"], "signed_classification")


if __name__ == "__main__":
    unittest.main()
