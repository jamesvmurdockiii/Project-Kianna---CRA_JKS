"""
Minimal CI smoke tests for the Coral Reef SpiNNaker package.

These tests verify:
1. The package imports without errors.
2. Public exports are resolvable.
3. The mock backend can run a short simulation.
4. The custom C-runtime SDP packet format is internally consistent.
"""
import struct
import sys
import unittest
from pathlib import Path

import numpy as np

# Ensure the package root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestImports(unittest.TestCase):
    """Verify the package namespace is healthy."""

    def test_root_import(self):
        import coral_reef_spinnaker as cra

        self.assertTrue(hasattr(cra, "__version__"))
        self.assertTrue(hasattr(cra, "get_version"))
        self.assertTrue(hasattr(cra, "check_dependencies"))

    def test_lazy_exports(self):
        import coral_reef_spinnaker as cra

        # These should resolve without raising
        self.assertIsNotNone(cra.ReefConfig)
        self.assertIsNotNone(cra.Organism)
        self.assertIsNotNone(cra.MockSimulator)

    def test_config_schema(self):
        from coral_reef_spinnaker import ReefConfig

        cfg = ReefConfig.default()
        self.assertGreater(cfg.spinnaker.timestep_ms, 0)


class TestMockBackend(unittest.TestCase):
    """Run a few simulation steps on the pure-Python mock backend."""

    def test_mock_simulator_lifecycle(self):
        from coral_reef_spinnaker import MockSimulator

        MockSimulator.setup(timestep=1.0)
        self.assertTrue(MockSimulator._is_setup)
        MockSimulator.run(10.0)
        self.assertEqual(MockSimulator.get_current_time(), 10.0)
        MockSimulator.end()
        self.assertFalse(MockSimulator._is_setup)

    def test_mock_population_spikes(self):
        from coral_reef_spinnaker import MockSimulator

        MockSimulator.setup(timestep=1.0)
        pop = MockSimulator.Population(4, MockSimulator.IF_curr_exp)
        pop.record("spikes")
        data = pop.get_data("spikes")
        # Mock returns Neo Block-like object with .segments[0].spiketrains
        self.assertTrue(hasattr(data, "segments"))
        self.assertEqual(len(data.segments[0].spiketrains), 4)
        MockSimulator.end()

    def test_short_organism_run(self):
        from coral_reef_spinnaker import Organism, ReefConfig, MockSimulator

        config = ReefConfig.default()
        organism = Organism(config, MockSimulator)
        organism.initialize(stream_keys=["EUR/USD"])

        # Run a few steps with random-ish returns
        import random

        random.seed(42)
        for step in range(5):
            ret = random.gauss(0.0, 0.001)
            metrics = organism.train_step(ret)
            self.assertIsNotNone(metrics)
            self.assertGreaterEqual(metrics.n_alive, 0)

        organism.shutdown()
        MockSimulator.end()

    def test_initial_population_config_seeds_multiple_polyps(self):
        from coral_reef_spinnaker import Organism, ReefConfig, MockSimulator

        config = ReefConfig.default()
        config.lifecycle.initial_population = 4
        config.lifecycle.max_population_hard = 4
        config.lifecycle.enable_reproduction = False
        config.lifecycle.enable_apoptosis = False

        organism = Organism(config, MockSimulator)
        organism.initialize(stream_keys=["controlled"])

        self.assertEqual(organism.n_alive, 4)
        self.assertEqual(len(set(organism.alive_polyp_ids)), 4)

        organism.shutdown()
        MockSimulator.end()

    def test_domain_neutral_adapter_step_does_not_require_trading_bridge(self):
        import numpy as np
        from coral_reef_spinnaker import (
            MockSimulator,
            Observation,
            Organism,
            ReefConfig,
            SensorControlAdapter,
        )

        config = ReefConfig.default()
        config.lifecycle.initial_population = 2
        config.lifecycle.max_population_hard = 2
        config.lifecycle.enable_reproduction = False
        config.lifecycle.enable_apoptosis = False
        config.spinnaker.sync_interval_steps = 0

        organism = Organism(
            config,
            MockSimulator,
            use_default_trading_bridge=False,
        )
        organism.initialize(stream_keys=["sensor_control"])

        self.assertIsNone(organism.trading_bridge)

        observation = Observation(
            stream_id="sensor_control",
            x=np.asarray([0.01], dtype=float),
            target=0.01,
        )
        metrics = organism.train_adapter_step(
            SensorControlAdapter(),
            observation,
            dt_seconds=0.05,
        )

        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.n_alive, 2)
        self.assertIsNone(organism.trading_bridge)

        organism.shutdown()
        MockSimulator.end()


class TestSDPPacketFormat(unittest.TestCase):
    """Verify colony_controller.py builds valid SDP-over-UDP packets."""

    def test_packet_length(self):
        from coral_reef_spinnaker.python_host.colony_controller import ColonyController

        ctrl = ColonyController()
        pkt = ctrl._build_sdp(1, args=(42, 0, 0))  # birth neuron 42
        # 2 UDP pad + 8 SDP header + 16 Spin1API command header.
        self.assertEqual(len(pkt), 26)
        cmd_rc, seq, arg1, arg2, arg3 = struct.unpack_from("<HHIII", pkt, 10)
        self.assertEqual(cmd_rc, 1)
        self.assertEqual(seq, 0)
        self.assertEqual((arg1, arg2, arg3), (42, 0, 0))

    def test_header_layout(self):
        from coral_reef_spinnaker.python_host.colony_controller import ColonyController

        ctrl = ColonyController()
        pkt = ctrl._build_sdp(cmd=3, payload=b"", dest_x=1, dest_y=2, dest_cpu=5, dest_port=2)

        # bytes 0-1 : padding
        self.assertEqual(pkt[0:2], b"\x00\x00")
        # byte 2 : flags; host commands expect an SDP reply
        self.assertEqual(pkt[2], 0x87)
        # byte 3 : tag
        self.assertEqual(pkt[3], 0xFF)
        # byte 4 : dest_port_cpu = (port << 5) | cpu
        self.assertEqual(pkt[4], (2 << 5) | 5)
        # byte 6 : dest_y
        self.assertEqual(pkt[6], 2)
        # byte 7 : dest_x
        self.assertEqual(pkt[7], 1)
        # bytes 10-25 : Spin1API command header
        cmd_rc, seq, arg1, arg2, arg3 = struct.unpack_from("<HHIII", pkt, 10)
        self.assertEqual(cmd_rc, 3)
        self.assertEqual(seq, 0)
        self.assertEqual((arg1, arg2, arg3), (0, 0, 0))

    def test_read_state_payload_parser(self):
        from coral_reef_spinnaker.python_host.colony_controller import (
            CMD_READ_STATE,
            ColonyController,
            float_to_fp,
        )

        payload = bytearray(73)
        payload[0] = CMD_READ_STATE
        payload[1] = 0
        payload[2] = 1

        def put_u32(offset, value):
            payload[offset:offset + 4] = int(value).to_bytes(4, "little", signed=False)

        def put_s32(offset, value):
            payload[offset:offset + 4] = int(value).to_bytes(4, "little", signed=True)

        put_u32(4, 123)
        put_u32(8, 2)
        put_u32(12, 1)
        put_u32(16, 1)
        put_u32(20, 1)
        put_u32(24, 3)
        put_u32(28, 2)
        put_u32(32, 1)
        put_u32(36, 0)
        put_u32(40, 5)
        put_u32(44, 4)
        put_u32(48, 7)
        put_u32(52, 6)
        put_u32(56, 1)
        put_u32(60, 2)
        put_s32(64, float_to_fp(0.25))
        put_s32(68, float_to_fp(-0.125))

        state = ColonyController.parse_state_payload(bytes(payload))
        self.assertTrue(state["success"])
        self.assertEqual(state["schema_version"], 1)
        self.assertEqual(state["timestep"], 123)
        self.assertEqual(state["neuron_count"], 2)
        self.assertEqual(state["synapse_count"], 1)
        self.assertEqual(state["pending_created"], 7)
        self.assertAlmostEqual(state["readout_weight"], 0.25)
        self.assertAlmostEqual(state["readout_bias"], -0.125)

    def test_reply_parsing(self):
        from coral_reef_spinnaker.python_host.colony_controller import ColonyController

        # Simulate a reply from the board: padding + header + payload
        raw = b"\x00\x00"  # pad
        raw += struct.pack("<8B", 0x07, 0xFF, 0x21, 0xE7, 0, 0, 0, 0)  # header
        raw += struct.pack("<HHIII", 1, 0, 0, 0, 0)  # cmd_rc: cmd=1, status=0

        cmd, status, payload = ColonyController._parse_reply(raw)
        self.assertEqual(cmd, 1)
        self.assertEqual(status, 0)


class TestBackendConformance(unittest.TestCase):
    """Verify backend_factory.py detects backends and exposes a uniform API."""

    def _make_mock_sim(self, name: str):
        """Create a minimal object that looks like a PyNN simulator module."""
        import types

        mod = types.ModuleType(name)
        mod.IF_curr_exp = lambda **kw: {"celltype": "IF_curr_exp", "params": kw}
        mod.StaticSynapse = lambda **kw: {"synapse": "static", "params": kw}
        mod.STDPMechanism = lambda **kw: {"stdp": True, "params": kw}
        mod.SpikePairRule = lambda **kw: {"rule": "spikepair", "params": kw}
        mod.AdditiveWeightDependence = lambda **kw: {"wd": "additive", "params": kw}
        mod.Projection = lambda *a, **kw: {"projection": True}
        mod.Population = lambda n, celltype, **kw: {"population": n}
        mod.FromListConnector = lambda conns: {"connector": conns}
        mod.setup = lambda **kw: None
        mod.run = lambda t: None
        mod.end = lambda: None
        return mod

    def test_factory_detection_map(self):
        from coral_reef_spinnaker.backend_factory import (
            get_backend_factory,
            BackendFactory,
            NESTFactory,
            Brian2Factory,
            MockSimulatorFactory,
            SpiNNakerFactory,
        )

        cases = [
            ("pyNN.spiNNaker", SpiNNakerFactory),
            ("pyNN.nest", NESTFactory),
            ("pyNN.brian2", Brian2Factory),
            ("MockSimulator", MockSimulatorFactory),
            ("some_unknown", BackendFactory),
        ]
        for name, expected_cls in cases:
            sim = self._make_mock_sim(name)
            factory = get_backend_factory(sim)
            self.assertIsInstance(
                factory,
                expected_cls,
                f"Expected {expected_cls.__name__} for {name}, got {type(factory).__name__}",
            )

    def test_mock_factory_cell_type(self):
        from coral_reef_spinnaker.backend_factory import get_backend_factory

        sim = self._make_mock_sim("MockSimulator")
        factory = get_backend_factory(sim)
        cell = factory.create_cell_type(tau_m=20.0, v_thresh=-55.0)
        self.assertEqual(cell["celltype"], "IF_curr_exp")
        self.assertEqual(cell["params"]["tau_m"], 20.0)
        self.assertEqual(cell["params"]["v_thresh"], -55.0)

    def test_mock_factory_synapse_creation(self):
        from coral_reef_spinnaker.backend_factory import get_backend_factory

        sim = self._make_mock_sim("MockSimulator")
        factory = get_backend_factory(sim)

        exc = factory.create_excitatory_synapse(weight=0.1)
        self.assertEqual(exc["params"]["weight"], 0.1)

        inh = factory.create_inhibitory_synapse(weight=-0.1)
        self.assertEqual(inh["params"]["weight"], -0.1)

        static = factory.create_static_synapse(weight=0.5, delay=2.0)
        self.assertEqual(static["params"]["weight"], 0.5)
        self.assertEqual(static["params"]["delay"], 2.0)

    def test_capability_flags_consistency(self):
        from coral_reef_spinnaker.backend_factory import (
            get_backend_factory,
            SpiNNakerFactory,
        )

        # sPyNNaker should NOT support dynamic projections (hardware limitation)
        sim = self._make_mock_sim("pyNN.spiNNaker")
        spinn = get_backend_factory(sim)
        self.assertIsInstance(spinn, SpiNNakerFactory)
        self.assertFalse(spinn.supports_dynamic_projections())
        self.assertFalse(spinn.supports_runtime_weight_update())
        self.assertTrue(spinn.uses_fixed_point())

    def test_spinnaker_neuromodulation_connections_are_sharded(self):
        from collections import Counter
        from coral_reef_spinnaker.backend_factory import (
            get_backend_factory,
            SpiNNakerFactory,
        )

        sim = self._make_mock_sim("pyNN.spiNNaker")
        spinn = get_backend_factory(sim)
        self.assertIsInstance(spinn, SpiNNakerFactory)

        connections = spinn._build_neuromodulation_connections(256)
        self.assertEqual(len(connections), 256)
        self.assertEqual({target for _, target in connections}, set(range(256)))
        fanout_by_source = Counter(source for source, _ in connections)
        self.assertGreater(len(fanout_by_source), 1)
        self.assertLessEqual(
            max(fanout_by_source.values()),
            spinn._NM_MAX_TARGETS_PER_SOURCE,
        )
        self.assertLessEqual(max(fanout_by_source.values()), 255)

    def test_default_factory_raises(self):
        from coral_reef_spinnaker.backend_factory import factory, _default_factory
        import coral_reef_spinnaker.backend_factory as _bf

        # Save whatever factory a previous test left behind
        saved = _bf._default_factory
        try:
            # Force the uninitialized default
            _bf._default_factory = _bf._DefaultFactory()
            f = factory()
            self.assertEqual(f.backend_name, "uninitialized")
            with self.assertRaises(RuntimeError):
                f.create_cell_type()
        finally:
            _bf._default_factory = saved


class TestSpiNNakerCompatibility(unittest.TestCase):
    """Verify local hardware shims do not regress under NumPy 2."""

    def test_uint8_memory_view_preserves_high_uint32_words(self):
        from coral_reef_spinnaker.spinnaker_compat import (
            _uint8_memory_view,
            _uint32_checksum,
        )

        word = 0xC0000000
        expected = np.asarray([word], dtype=np.uint32).view(np.uint8)
        observed = _uint8_memory_view([word])

        self.assertEqual(observed.dtype, np.dtype(np.uint8))
        self.assertEqual(observed.tolist(), expected.tolist())
        self.assertEqual(
            _uint32_checksum([word]),
            int(np.sum(expected.view(np.uint32), dtype=np.uint32)) & 0xFFFFFFFF,
        )

    def test_spinnman_numpy2_patch_is_safe_when_available(self):
        from coral_reef_spinnaker.spinnaker_compat import (
            apply_numpy_uint8_overflow_patch,
            apply_spynnaker_neuromodulation_numpy2_patch,
            apply_spinnman_numpy2_write_memory_patch,
            _neuromodulation_flags,
        )

        numpy_status = apply_numpy_uint8_overflow_patch()
        self.assertTrue(numpy_status.get("available"))

        # This is the exact EBRAINS failure value.  Under NumPy 2 without the
        # shim it raises instead of producing a byte buffer.
        recovered = np.asarray([0xC0000000], dtype=np.uint8)
        expected = np.asarray([0xC0000000], dtype=np.uint32).view(np.uint8)
        self.assertEqual(recovered.tolist(), expected.tolist())
        self.assertEqual(
            _neuromodulation_flags(True, np.uint8(0)),
            0xC0000000,
        )

        nm_status = apply_spynnaker_neuromodulation_numpy2_patch()
        if not nm_status.get("available"):
            self.skipTest(nm_status.get("reason", "sPyNNaker is not installed"))
        self.assertTrue(nm_status.get("available"))

        spinnman_status = apply_spinnman_numpy2_write_memory_patch()
        if not spinnman_status.get("available"):
            self.skipTest(spinnman_status.get("reason", "spinnman is not installed"))
        self.assertTrue(spinnman_status.get("available"))
        self.assertIn("numpy_version", spinnman_status)


if __name__ == "__main__":
    unittest.main()
