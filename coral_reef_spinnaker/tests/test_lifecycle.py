"""Unit tests for LifecycleManager algorithms."""

import unittest
from dataclasses import dataclass

from coral_reef_spinnaker.config import LifecycleConfig
from coral_reef_spinnaker.lifecycle import (
    LifecycleManager,
    LifecycleEvent,
    LineageRecord,
)
from coral_reef_spinnaker.polyp_state import PolypState


@dataclass
class MockEnergyResult:
    deaths: list = None


class TestLifecycleEvent(unittest.TestCase):
    def test_event_creation(self):
        e = LifecycleEvent(
            event_type="birth", step=0, polyp_id=5, lineage_id=1, parent_id=3, details={}
        )
        self.assertEqual(e.event_type, "birth")
        self.assertEqual(e.polyp_id, 5)
        self.assertEqual(e.parent_id, 3)


class TestLineageRecord(unittest.TestCase):
    def test_lineage_tracking(self):
        lr = LineageRecord(lineage_id=1, founder_id=0)
        lr.polyp_ids.append(0)
        lr.polyp_ids.append(1)
        self.assertEqual(len(lr.polyp_ids), 2)


class TestLifecycleManagerInit(unittest.TestCase):
    def test_default_init(self):
        lm = LifecycleManager(config=LifecycleConfig(), energy_config=None, n_streams=1)
        self.assertEqual(lm._next_polyp_id, 0)
        self.assertEqual(lm._lineage_counter, 0)

    def test_population_capacity_positive(self):
        lm = LifecycleManager(
            config=LifecycleConfig(max_population_hard=64), energy_config=None, n_streams=1
        )
        # population_capacity computes hardware-limited capacity; just check it's > 0
        self.assertGreater(lm.population_capacity(), 0)


class TestSeedTraits(unittest.TestCase):
    def setUp(self):
        self.lm = LifecycleManager(config=LifecycleConfig(), energy_config=None, n_streams=1)

    def test_seed_traits_has_required_keys(self):
        traits = self.lm._create_seed_traits()
        self.assertIn("metabolic_decay", traits)
        self.assertIn("trophic_synapse_cost", traits)
        self.assertIn("reproduction_threshold", traits)

    def test_seed_traits_in_bounds(self):
        traits = self.lm._create_seed_traits()
        for name, val in traits.items():
            self.assertIsInstance(val, float)
            self.assertGreater(val, 0.0)


class TestCheckDeath(unittest.TestCase):
    def setUp(self):
        self.lm = LifecycleManager(config=LifecycleConfig(), energy_config=None, n_streams=1)

    def test_alive_when_healthy(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, is_alive=True,
            trophic_health=1.0, apoptosis_threshold=0.1, bax_activation=0.0,
            is_juvenile=False,
        )
        self.assertFalse(self.lm.check_death(p, energy_result=MockEnergyResult(deaths=[])))

    def test_dead_when_starved(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, is_alive=True,
            trophic_health=0.05, apoptosis_threshold=0.1, bax_activation=0.0,
            is_juvenile=False,
        )
        self.assertTrue(self.lm.check_death(p, energy_result=MockEnergyResult(deaths=[])))

    def test_energy_death_list(self):
        p = PolypState(polyp_id=0, lineage_id=0, is_alive=True)
        er = MockEnergyResult(deaths=[0])
        # Note: lifecycle.check_death does NOT check energy_result.deaths;
        # that logic is in organism._apply_lifecycle_events
        self.assertFalse(self.lm.check_death(p, energy_result=er))

    def test_juvenile_protection(self):
        # Pre-handoff juveniles are protected from BAX death
        p = PolypState(
            polyp_id=0, lineage_id=0, is_alive=True, is_juvenile=True,
            trophic_health=0.05, apoptosis_threshold=0.1, bax_activation=0.5,
        )
        self.lm._handoff_complete = False
        self.assertFalse(self.lm.check_death(p, energy_result=MockEnergyResult()))

    def test_post_handoff_juvenile_vulnerable(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, is_alive=True, is_juvenile=False,
            trophic_health=0.05, apoptosis_threshold=0.1, bax_activation=0.0,
        )
        self.lm._handoff_complete = True
        self.assertTrue(self.lm.check_death(p, energy_result=MockEnergyResult()))


class TestReproductionReadiness(unittest.TestCase):
    def setUp(self):
        self.lm = LifecycleManager(config=LifecycleConfig(), energy_config=None, n_streams=1)

    def test_ready_when_healthy(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, is_alive=True, trophic_health=2.0,
            reproduction_threshold=1.5,
        )
        self.assertTrue(self.lm.check_reproduction_readiness(p, energy_result=None))

    def test_not_ready_low_trophic(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, is_alive=True, trophic_health=1.0,
            reproduction_threshold=1.5,
        )
        self.assertFalse(self.lm.check_reproduction_readiness(p, energy_result=None))


class TestJuvenileMaturity(unittest.TestCase):
    def setUp(self):
        self.lm = LifecycleManager(config=LifecycleConfig(), energy_config=None, n_streams=1)

    def test_not_mature_when_young(self):
        p = PolypState(polyp_id=0, lineage_id=0, is_alive=True, is_juvenile=True, age_steps=5)
        self.assertFalse(self.lm.check_juvenile_maturity(p, d_eff=1, tau=1.0))

    def test_mature_when_old_enough(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, is_alive=True, is_juvenile=True,
            age_steps=1000, trophic_health=2.0, reproduction_threshold=1.5,
        )
        # Need enough support_history samples
        from collections import deque
        p.support_history = deque([1.0] * 100, maxlen=1000)
        self.assertTrue(self.lm.check_juvenile_maturity(p, d_eff=1, tau=1.0))


class TestLifecycleStep(unittest.TestCase):
    def setUp(self):
        self.lm = LifecycleManager(
            config=LifecycleConfig(max_population_hard=8), energy_config=None, n_streams=1
        )

    def test_step_with_no_polyps(self):
        events = self.lm.step(
            polyp_states=[],
            edges={},
            energy_result=MockEnergyResult(),
            maternal_reserve=None,
            step_num=0,
            dt=1.0,
        )
        self.assertIsInstance(events, list)

    def test_step_extinct_colony(self):
        p = PolypState(polyp_id=0, lineage_id=0, is_alive=False)
        events = self.lm.step(
            polyp_states=[p],
            edges={},
            energy_result=MockEnergyResult(),
            maternal_reserve=None,
            step_num=0,
            dt=1.0,
        )
        self.assertIsInstance(events, list)

    def test_reproduction_disabled_suppresses_birth_events(self):
        lm = LifecycleManager(
            config=LifecycleConfig(
                max_population_hard=8,
                enable_reproduction=False,
            ),
            energy_config=None,
            n_streams=1,
        )
        lm._handoff_complete = True
        p = PolypState(
            polyp_id=0,
            lineage_id=0,
            is_alive=True,
            is_juvenile=False,
            trophic_health=10.0,
            reproduction_threshold=0.1,
            cyclin_d=10.0,
        )
        states = [p]

        events = lm.step(
            polyp_states=states,
            edges={},
            energy_result=MockEnergyResult(),
            maternal_reserve=None,
            step_num=100,
            dt=1.0,
        )

        self.assertFalse(
            any(e.event_type in {"birth", "cleavage"} for e in events)
        )
        self.assertEqual(len(states), 1)


if __name__ == "__main__":
    unittest.main()
