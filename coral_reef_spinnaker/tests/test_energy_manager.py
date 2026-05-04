"""Unit tests for EnergyManager algorithms.

Tests the trophic ecology, apoptosis, reproduction, and maternal-reserve
logic without requiring a full organism or simulator.
"""

import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from coral_reef_spinnaker.energy_manager import (
    EnergyConfig,
    EnergyManager,
    EnergyResult,
    MaternalReserve,
)
from coral_reef_spinnaker.polyp_state import PolypState
from coral_reef_spinnaker.signals import ConsequenceSignal


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------

@dataclass
class MockEdge:
    source_id: int
    target_id: int
    weight: float = 0.5
    is_pruned: bool = False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEnergyConfigDefaults(unittest.TestCase):
    def test_defaults_positive(self):
        cfg = EnergyConfig()
        self.assertGreater(cfg.metabolic_decay_default, 0)
        self.assertGreater(cfg.trophic_synapse_cost_default, 0)
        self.assertGreater(cfg.bax_accumulation_rate, 0)


class TestMaternalReserve(unittest.TestCase):
    def test_initial_state(self):
        r = MaternalReserve(trophic_reserve=20.0, atp_reserve=10.0, initial_trophic=20.0, initial_atp=10.0)
        self.assertEqual(r.trophic_reserve, 20.0)
        self.assertEqual(r.atp_reserve, 10.0)
        self.assertFalse(r.is_exhausted)

    def test_deplete_trophic(self):
        r = MaternalReserve(trophic_reserve=20.0, atp_reserve=10.0, initial_trophic=20.0, initial_atp=10.0)
        taken = r.deplete_trophic(5.0)
        self.assertEqual(taken, 5.0)
        self.assertEqual(r.trophic_reserve, 15.0)

    def test_deplete_trophic_partial(self):
        r = MaternalReserve(trophic_reserve=20.0, atp_reserve=10.0, initial_trophic=20.0, initial_atp=10.0)
        taken = r.deplete_trophic(25.0)
        self.assertEqual(taken, 20.0)
        self.assertEqual(r.trophic_reserve, 0.0)
        # Not fully exhausted because ATP reserve still remains
        self.assertFalse(r.is_exhausted)
        # Depleting ATP too should exhaust
        r.deplete_atp(15.0)
        self.assertTrue(r.is_exhausted)

    def test_deplete_atp(self):
        r = MaternalReserve(trophic_reserve=20.0, atp_reserve=10.0, initial_trophic=20.0, initial_atp=10.0)
        taken = r.deplete_atp(3.0)
        self.assertEqual(taken, 3.0)
        self.assertEqual(r.atp_reserve, 7.0)

    def test_can_fund(self):
        r = MaternalReserve(trophic_reserve=20.0, atp_reserve=10.0, initial_trophic=20.0, initial_atp=10.0)
        self.assertTrue(r.can_fund(10.0))
        self.assertFalse(r.can_fund(100.0))


class TestLocalCapacity(unittest.TestCase):
    def setUp(self):
        self.em = EnergyManager(config=EnergyConfig(), n_streams=1)

    def test_capacity_base(self):
        p = PolypState(polyp_id=0, lineage_id=0, trophic_health=1.0, metabolic_decay=0.005)
        cap = self.em._compute_local_capacity(p, degree=0)
        self.assertGreater(cap, 0)

    def test_capacity_increases_with_degree(self):
        # Capacity scales with effective_decay (metabolic need).
        # More synapses = higher metabolic cost = higher capacity ceiling.
        p = PolypState(polyp_id=0, lineage_id=0, trophic_health=1.0, metabolic_decay=0.005, trophic_synapse_cost=0.001)
        cap0 = self.em._compute_local_capacity(p, degree=0)
        cap10 = self.em._compute_local_capacity(p, degree=10)
        self.assertLess(cap0, cap10)

    def test_capacity_positive_even_when_dead(self):
        # _compute_local_capacity does not check is_alive; it computes
        # based on metabolic parameters regardless
        p = PolypState(polyp_id=0, lineage_id=0, is_alive=False, metabolic_decay=0.005)
        cap = self.em._compute_local_capacity(p, degree=0)
        self.assertGreater(cap, 0.0)


class TestDeathCheck(unittest.TestCase):
    def setUp(self):
        self.em = EnergyManager(config=EnergyConfig(), n_streams=1)

    def test_alive_when_healthy(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=1.0,
            apoptosis_threshold=0.1, bax_activation=0.0, is_alive=True,
        )
        self.assertFalse(self.em.check_death(p, degree=0))

    def test_death_when_starved(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=0.05,
            apoptosis_threshold=0.1, bax_activation=0.0, is_alive=True,
        )
        self.assertTrue(self.em.check_death(p, degree=0))

    def test_death_from_bax(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=0.15,
            apoptosis_threshold=0.1, bax_activation=0.1, is_alive=True,
        )
        # threshold + bax = 0.2, health = 0.15 -> dead
        self.assertTrue(self.em.check_death(p, degree=0))

    def test_already_dead_returns_false(self):
        # check_death returns False for already-dead polyps
        p = PolypState(polyp_id=0, lineage_id=0, is_alive=False)
        self.assertFalse(self.em.check_death(p, degree=0))


class TestReproductionEligibility(unittest.TestCase):
    def setUp(self):
        self.em = EnergyManager(config=EnergyConfig(), n_streams=1)

    def test_not_eligible_when_juvenile(self):
        # Juvenile + handoff NOT complete -> blocked
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=2.0,
            cyclin_d=0.6, is_juvenile=True, handoff_complete=False,
            metabolic_decay=0.005, trophic_synapse_cost=0.001,
        )
        self.assertFalse(self.em.check_reproduction_eligible(p, degree=0, local_supportable=1.0))

    def test_not_eligible_when_low_cyclin(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=2.0,
            cyclin_d=0.1, is_juvenile=False, handoff_complete=True,
            metabolic_decay=0.005, trophic_synapse_cost=0.001,
        )
        self.assertFalse(self.em.check_reproduction_eligible(p, degree=0, local_supportable=1.0))

    def test_eligible_when_mature_and_healthy(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=2.0,
            cyclin_d=0.6, is_juvenile=False, handoff_complete=True,
            metabolic_decay=0.005, trophic_synapse_cost=0.001,
        )
        self.assertTrue(self.em.check_reproduction_eligible(p, degree=0, local_supportable=1.0))

    def test_not_eligible_when_dead(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=2.0,
            cyclin_d=0.6, is_juvenile=False, handoff_complete=True,
            metabolic_decay=0.005, trophic_synapse_cost=0.001,
            is_alive=False,
        )
        self.assertFalse(self.em.check_reproduction_eligible(p, degree=0, local_supportable=1.0))


class TestTrophicUpdate(unittest.TestCase):
    def setUp(self):
        self.em = EnergyManager(config=EnergyConfig(), n_streams=1)

    def test_earned_support_increases_health(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=1.0,
            metabolic_decay=0.005, trophic_synapse_cost=0.001,
        )
        self.em._apply_trophic_update(
            p, earned=0.5, retro_spent=0.0, degree=0, dt=1.0
        )
        self.assertGreater(p.trophic_health, 1.0)

    def test_metabolic_decay_decreases_health(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=1.0,
            metabolic_decay=0.1, trophic_synapse_cost=0.0,
        )
        self.em._apply_trophic_update(
            p, earned=0.0, retro_spent=0.0, degree=0, dt=1.0
        )
        self.assertLess(p.trophic_health, 1.0)

    def test_synapse_cost_scales_with_degree(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=1.0,
            metabolic_decay=0.0, trophic_synapse_cost=0.01,
        )
        self.em._apply_trophic_update(
            p, earned=0.0, retro_spent=0.0, degree=10, dt=1.0
        )
        # effective_decay = 0.1, decay_factor = exp(-0.1) ≈ 0.9048
        self.assertLess(p.trophic_health, 1.0)


class TestCyclinUpdate(unittest.TestCase):
    def setUp(self):
        self.em = EnergyManager(config=EnergyConfig(), n_streams=1)

    def test_cyclin_accumulates_when_healthy(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=2.0,
            cyclin_d=0.0, cyclin_accumulation_rate=1.0,
            cyclin_degradation_rate=0.1,
        )
        self.em._update_cyclin(p, dt=1.0)
        self.assertGreater(p.cyclin_d, 0.0)

    def test_cyclin_degrades_when_unhealthy(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, trophic_health=0.0,
            cyclin_d=0.5, cyclin_accumulation_rate=1.0,
            cyclin_degradation_rate=0.5,
        )
        self.em._update_cyclin(p, dt=1.0)
        self.assertLess(p.cyclin_d, 0.5)


class TestBaxUpdate(unittest.TestCase):
    def setUp(self):
        self.em = EnergyManager(config=EnergyConfig(), n_streams=1)

    def test_bax_increases_when_accuracy_low(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, bax_activation=0.0,
            directional_accuracy_ema=0.3,
            earned_support=0.5, metabolic_decay=0.005,
        )
        self.em._update_bax(p, dt=1.0, post_handoff=True)
        self.assertGreater(p.bax_activation, 0.0)

    def test_bax_decreases_when_accuracy_high(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, bax_activation=0.5,
            directional_accuracy_ema=0.9,
            earned_support=1.0, metabolic_decay=0.005,
        )
        self.em._update_bax(p, dt=1.0, post_handoff=True)
        self.assertLess(p.bax_activation, 0.5)

    def test_bax_never_negative(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, bax_activation=0.0,
            directional_accuracy_ema=1.0,
            earned_support=1.0, metabolic_decay=0.005,
        )
        self.em._update_bax(p, dt=1.0, post_handoff=True)
        self.assertGreaterEqual(p.bax_activation, 0.0)

    def test_bax_suppressed_pre_handoff(self):
        p = PolypState(
            polyp_id=0, lineage_id=0, bax_activation=0.5,
            directional_accuracy_ema=0.3,
            earned_support=0.0, metabolic_decay=0.005,
        )
        self.em._update_bax(p, dt=1.0, post_handoff=False)
        # Pre-handoff: BAX should decrease (suppressed)
        self.assertLess(p.bax_activation, 0.5)


class TestEnergyManagerStep(unittest.TestCase):
    def setUp(self):
        self.em = EnergyManager(config=EnergyConfig(), n_streams=1)

    def test_step_returns_result(self):
        states = [
            PolypState(polyp_id=0, lineage_id=0, is_alive=True, direct_stream_mask={0}),
            PolypState(polyp_id=1, lineage_id=0, is_alive=True, direct_stream_mask=set()),
        ]
        edges = {}
        task = ConsequenceSignal(
            immediate_signal=0.1,
            horizon_signal=0.2,
            actual_value=0.1,
            prediction=0.5,
            direction_correct=True,
            raw_dopamine=0.1,
            matured_gross_positive=0.0,
            matured_net_positive=0.0,
        )
        result = self.em.step(
            polyp_states=states,
            edges=edges,
            stream_mi={"stream0": 0.5},
            task_outcome=task,
            matured_consequence=(0.0, 0.0),
            dt=1.0,
            step_num=0,
        )
        self.assertIsInstance(result, EnergyResult)


if __name__ == "__main__":
    unittest.main()
