# Tier 4.25C — Two-Core State/Learning Split Repeatability — Ingest Report

- Status: **PASS**
- Passed: 23/23
- Hardware output: `controlled_test_output/tier4_25c_seed44_hardware`

## Criteria

- ✓ runner revision current: `tier4_25c_two_core_split_smoke_20260502_0001` (expected current source)
- ✓ custom C host tests pass: `pass` (== pass)
- ✓ main.c syntax check pass: `pass` (== pass)
- ✓ hardware target acquired: `{'status': 'pass', 'method': 'pyNN.spiNNaker_probe', 'hostname': '10.11.193.65', 'target_ipaddress': '10.11.193.65', 'setup_kwargs': {'timestep': 1.0}, 'probe_population_size': 1, 'probe_run_ms': 1.0, 'probe_timestep_ms': 1.0, 'dest_x': 0, 'dest_y': 0, 'dest_cpu': 4, 'occupied_cores': [1, 2, 3], 'notes': ['acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname', 'requested dest_cpu was free'], 'runtime_seconds': 57.15609959885478, 'attempts': [{'status': 'fail', 'method': 'hostname_discovery', 'hostname': '', 'notes': ['no hostname found in args, common environment variables, or spynnaker.cfg'], 'reason': 'no explicit hostname/config/environment target found'}, {'status': 'pass', 'method': 'pyNN.spiNNaker_probe', 'hostname': '10.11.193.65', 'target_ipaddress': '10.11.193.65', 'setup_kwargs': {'timestep': 1.0}, 'probe_population_size': 1, 'probe_run_ms': 1.0, 'probe_timestep_ms': 1.0, 'dest_x': 0, 'dest_y': 0, 'dest_cpu': 4, 'occupied_cores': [1, 2, 3], 'notes': ['acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname', 'requested dest_cpu was free'], 'runtime_seconds': 57.15609959885478}]}` (status == pass)
- ✓ state_core .aplx built: `True` (== True)
- ✓ learning_core .aplx built: `True` (== True)
- ✓ state_core load pass: `pass` (== pass)
- ✓ learning_core load pass: `pass` (== pass)
- ✓ state_core reset succeeded: `True` (== True)
- ✓ learning_core reset succeeded: `True` (== True)
- ✓ all context writes succeeded: `[{'key': 'ctx_A', 'success': True}, {'key': 'ctx_B', 'success': True}, {'key': 'ctx_C', 'success': True}, {'key': 'ctx_D', 'success': True}]` (all success)
- ✓ all route writes succeeded: `[{'key': 'route_A', 'success': True}, {'key': 'route_B', 'success': True}, {'key': 'route_C', 'success': True}, {'key': 'route_D', 'success': True}]` (all success)
- ✓ all memory writes succeeded: `[{'key': 'mem_A', 'success': True}, {'key': 'mem_B', 'success': True}, {'key': 'mem_C', 'success': True}, {'key': 'mem_D', 'success': True}]` (all success)
- ✓ all schedule uploads succeeded: `[{'index': 0, 'success': True}, {'index': 1, 'success': True}, {'index': 2, 'success': True}, {'index': 3, 'success': True}, {'index': 4, 'success': True}, {'index': 5, 'success': True}, {'index': 6, 'success': True}, {'index': 7, 'success': True}, {'index': 8, 'success': True}, {'index': 9, 'success': True}, {'index': 10, 'success': True}, {'index': 11, 'success': True}, {'index': 12, 'success': True}, {'index': 13, 'success': True}, {'index': 14, 'success': True}, {'index': 15, 'success': True}, {'index': 16, 'success': True}, {'index': 17, 'success': True}, {'index': 18, 'success': True}, {'index': 19, 'success': True}, {'index': 20, 'success': True}, {'index': 21, 'success': True}, {'index': 22, 'success': True}, {'index': 23, 'success': True}, {'index': 24, 'success': True}, {'index': 25, 'success': True}, {'index': 26, 'success': True}, {'index': 27, 'success': True}, {'index': 28, 'success': True}, {'index': 29, 'success': True}, {'index': 30, 'success': True}, {'index': 31, 'success': True}, {'index': 32, 'success': True}, {'index': 33, 'success': True}, {'index': 34, 'success': True}, {'index': 35, 'success': True}, {'index': 36, 'success': True}, {'index': 37, 'success': True}, {'index': 38, 'success': True}, {'index': 39, 'success': True}, {'index': 40, 'success': True}, {'index': 41, 'success': True}, {'index': 42, 'success': True}, {'index': 43, 'success': True}, {'index': 44, 'success': True}, {'index': 45, 'success': True}, {'index': 46, 'success': True}, {'index': 47, 'success': True}]` (all success)
- ✓ state_core run_continuous succeeded: `True` (== True)
- ✓ learning_core run_continuous succeeded: `True` (== True)
- ✓ state_core final read succeeded: `True` (== True)
- ✓ learning_core final read succeeded: `True` (== True)
- ✓ learning_core weight near reference: `32767` (within +/- 8192 of 32768)
- ✓ learning_core bias near reference: `-1` (within +/- 8192 of 0)
- ✓ learning_core pending_created matches reference: `48` (== 48)
- ✓ learning_core pending_matured matches reference: `48` (== 48)
- ✓ learning_core active_pending cleared: `0` (== 0)
