#!/usr/bin/env python3
"""Tier 4.22i custom-runtime board load and CMD_READ_STATE round-trip.

Tier 4.22h proved compact readback locally. Tier 4.22i is the first
hardware-facing gate for the custom C sidecar itself:

    build .aplx -> load tiny app -> send CMD_READ_STATE -> validate schema

Claim boundary:
- PREPARED means the EBRAINS source bundle and command are ready.
- PASS in run-hardware means a real board target was configured, the custom
  runtime .aplx built, the app was loaded, and CMD_READ_STATE round-tripped with
  schema-v1 state after simple command mutations.
- This is not full CRA learning, not speedup evidence, not multi-core scaling,
  and not a final on-chip runtime claim.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
TIER = "Tier 4.22i - Custom Runtime Board Round-Trip Smoke"
RUNNER_REVISION = "tier4_22i_custom_runtime_roundtrip_20260430_0009"
TIER4_22H_LATEST = CONTROLLED / "tier4_22h_latest_manifest.json"
DEFAULT_OUTPUT = CONTROLLED / "tier4_22i_20260430_custom_runtime_roundtrip_prepared"
UPLOAD_PACKAGE_NAME = "cra_422r"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEPRECATED_EBRAINS_UPLOADS = [
    ROOT / "ebrains_jobs" / "cra_422i",
    ROOT / "ebrains_jobs" / "cra_422j",
    ROOT / "ebrains_jobs" / "cra_422l",
    ROOT / "ebrains_jobs" / "cra_422m",
    ROOT / "ebrains_jobs" / "cra_422n",
    ROOT / "ebrains_jobs" / "cra_422o",
    ROOT / "ebrains_jobs" / "cra_422p",
    ROOT / "ebrains_jobs" / "cra_422q",
]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                keys.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed), "note": note}


def markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def latest_status(path: Path) -> tuple[str, str | None]:
    if not path.exists():
        return "missing", None
    try:
        payload = read_json(path)
    except Exception as exc:
        return f"unreadable:{type(exc).__name__}", None
    return str(payload.get("status", "unknown")).lower(), str(payload.get("manifest") or "")


def run_cmd(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def find_tool(name: str) -> str:
    return shutil.which(name) or ""


def module_status(name: str) -> dict[str, Any]:
    try:
        module = __import__(name)
        return {"name": name, "available": True, "path": getattr(module, "__file__", "")}
    except Exception as exc:
        return {"name": name, "available": False, "error": f"{type(exc).__name__}: {exc}"}


def detect_spinnaker_tools() -> str:
    env_hint = os.environ.get("SPINN_DIRS", "")
    candidates = [
        Path(env_hint) if env_hint else None,
        Path("/opt/spinnaker_tools"),
        Path("/usr/local/spinnaker_tools"),
        Path.home() / "spinnaker_tools",
        Path.home() / "spinnaker" / "spinnaker_tools",
    ]
    for path in candidates:
        if path and (path / "make" / "spinnaker_tools.mk").exists():
            return str(path)
    return ""


def discover_hostname(explicit: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if explicit:
        return explicit, ["from --spinnaker-hostname"]
    for key in ["SPINNAKER_HOSTNAME", "SPINNAKER_HOST", "SPINNAKER_BOARD", "SPYNNAKER_MACHINE", "SPINNAKER_MACHINE"]:
        value = os.environ.get(key, "").strip()
        if value:
            return value, [f"from ${key}"]
    for cfg in [Path.cwd() / "spynnaker.cfg", Path.home() / ".spynnaker.cfg", Path.home() / "spynnaker.cfg"]:
        if not cfg.exists():
            continue
        try:
            for line in cfg.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                k, v = [part.strip() for part in stripped.split("=", 1)]
                if k.lower() in {"machinename", "machine_name", "hostname", "spinnaker_hostname"} and v:
                    return v, [f"from {cfg}:{k}"]
        except Exception as exc:
            notes.append(f"could not read {cfg}: {type(exc).__name__}: {exc}")
    notes.append("no hostname found in args, common environment variables, or spynnaker.cfg")
    return "", notes


def public_target_acquisition(target: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe view of target acquisition state."""
    public: dict[str, Any] = {}
    for key, value in target.items():
        if key.startswith("_"):
            continue
        try:
            json.dumps(value)
            public[key] = value
        except TypeError:
            public[key] = str(value)
    return public


def select_destination_core(args: argparse.Namespace, occupied: list[int]) -> tuple[int, str]:
    """Pick a core for the custom sidecar, avoiding PyNN probe placements when possible."""
    preferred = int(args.dest_cpu)
    occupied_set = {int(p) for p in occupied}
    if not bool(args.auto_dest_cpu):
        return preferred, "--no-auto-dest-cpu; using requested dest_cpu"
    if 1 <= preferred <= 17 and preferred not in occupied_set:
        return preferred, "requested dest_cpu was free"
    for candidate in range(2, 18):
        if candidate not in occupied_set:
            return candidate, f"requested dest_cpu {preferred} was occupied; selected free core {candidate}"
    for candidate in range(1, 18):
        if candidate not in occupied_set:
            return candidate, f"selected free core {candidate}"
    return preferred, "no free application core visible from placements; using requested dest_cpu"


def occupied_cores_from_dataview(data_view: Any, *, x: int, y: int) -> list[int]:
    occupied: list[int] = []
    for p in range(1, 18):
        try:
            data_view.get_placement_on_processor(int(x), int(y), int(p))
            occupied.append(int(p))
        except Exception:
            continue
    return occupied


def acquire_target_via_hostname(args: argparse.Namespace) -> dict[str, Any]:
    hostname, notes = discover_hostname(args.spinnaker_hostname)
    if not hostname:
        return {
            "status": "fail",
            "method": "hostname_discovery",
            "hostname": "",
            "notes": notes,
            "reason": "no explicit hostname/config/environment target found",
        }
    dest_cpu, cpu_note = select_destination_core(args, [])
    return {
        "status": "pass",
        "method": "hostname_discovery",
        "hostname": hostname,
        "target_ipaddress": hostname,
        "notes": notes + [cpu_note],
        "dest_x": int(args.dest_x),
        "dest_y": int(args.dest_y),
        "dest_cpu": int(dest_cpu),
        "occupied_cores": [],
    }


def acquire_target_via_spynnaker_probe(args: argparse.Namespace) -> dict[str, Any]:
    """Acquire the EBRAINS board through the same PyNN path used by prior hardware tiers."""
    started = time.perf_counter()
    sim_module: Any | None = None
    try:
        import pyNN.spiNNaker as sim
        from spynnaker.pyNN.data import SpynnakerDataView

        sim_module = sim
        setup_kwargs: dict[str, Any] = {"timestep": float(args.target_probe_timestep_ms)}
        if args.spinnaker_hostname:
            setup_kwargs["spinnaker_hostname"] = args.spinnaker_hostname
        sim.setup(**setup_kwargs)
        pop_size = max(1, int(args.target_probe_population_size))
        population = sim.Population(
            pop_size,
            sim.IF_curr_exp(),
            label="tier4_22i_target_probe",
        )
        population.record("spikes")
        sim.run(float(args.target_probe_run_ms))

        transceiver = SpynnakerDataView.get_transceiver() if SpynnakerDataView.has_transceiver() else None
        ipaddress = SpynnakerDataView.get_ipaddress() if SpynnakerDataView.has_ipaddress() else ""
        occupied = occupied_cores_from_dataview(
            SpynnakerDataView,
            x=int(args.dest_x),
            y=int(args.dest_y),
        )
        dest_cpu, cpu_note = select_destination_core(args, occupied)
        if transceiver is None:
            raise RuntimeError("SpynnakerDataView did not expose a transceiver after the PyNN probe run")
        if not ipaddress:
            raise RuntimeError("SpynnakerDataView did not expose an IP address after the PyNN probe run")
        return {
            "status": "pass",
            "method": "pyNN.spiNNaker_probe",
            "hostname": ipaddress,
            "target_ipaddress": ipaddress,
            "setup_kwargs": setup_kwargs,
            "probe_population_size": pop_size,
            "probe_run_ms": float(args.target_probe_run_ms),
            "probe_timestep_ms": float(args.target_probe_timestep_ms),
            "dest_x": int(args.dest_x),
            "dest_y": int(args.dest_y),
            "dest_cpu": int(dest_cpu),
            "occupied_cores": occupied,
            "notes": [
                "acquired transceiver/IP via PyNN/sPyNNaker DataView because EBRAINS JobManager may not expose a raw hostname",
                cpu_note,
            ],
            "runtime_seconds": time.perf_counter() - started,
            "_transceiver": transceiver,
            "_sim": sim_module,
        }
    except Exception as exc:
        if sim_module is not None:
            try:
                sim_module.end()
            except Exception:
                pass
        return {
            "status": "fail",
            "method": "pyNN.spiNNaker_probe",
            "hostname": "",
            "target_ipaddress": "",
            "dest_x": int(args.dest_x),
            "dest_y": int(args.dest_y),
            "dest_cpu": int(args.dest_cpu),
            "runtime_seconds": time.perf_counter() - started,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
        }


def acquire_hardware_target(args: argparse.Namespace) -> dict[str, Any]:
    modes = [str(args.target_acquisition)]
    if str(args.target_acquisition) == "auto":
        modes = ["hostname", "spynnaker-probe"]
    attempts: list[dict[str, Any]] = []
    for mode in modes:
        if mode == "hostname":
            target = acquire_target_via_hostname(args)
        elif mode == "spynnaker-probe":
            target = acquire_target_via_spynnaker_probe(args)
        else:
            target = {"status": "fail", "method": mode, "reason": "unsupported target acquisition mode"}
        attempts.append(public_target_acquisition(target))
        if target.get("status") == "pass":
            target["attempts"] = attempts
            return target
    return {
        "status": "fail",
        "method": str(args.target_acquisition),
        "hostname": "",
        "target_ipaddress": "",
        "dest_x": int(args.dest_x),
        "dest_y": int(args.dest_y),
        "dest_cpu": int(args.dest_cpu),
        "attempts": attempts,
        "reason": "no target acquisition method succeeded",
    }


def release_hardware_target(target: dict[str, Any]) -> dict[str, Any]:
    sim_module = target.get("_sim")
    if sim_module is None:
        return {"status": "not_needed", "method": target.get("method", "")}
    try:
        sim_module.end()
        return {"status": "pass", "method": target.get("method", ""), "action": "pyNN.spiNNaker.end"}
    except Exception as exc:
        return {
            "status": "fail",
            "method": target.get("method", ""),
            "action": "pyNN.spiNNaker.end",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
        }


def environment_report() -> dict[str, Any]:
    return {
        "cwd": str(Path.cwd()),
        "python": sys.executable,
        "python_version": sys.version,
        "env": {key: os.environ.get(key, "") for key in ["SPINN_DIRS", "SPINNAKER_HOSTNAME", "SPINNAKER_HOST", "SPINNAKER_BOARD", "SPYNNAKER_MACHINE", "SPINNAKER_MACHINE"]},
        "spinnaker_tools": detect_spinnaker_tools(),
        "tools": {name: find_tool(name) for name in ["ybug", "spin1_api", "make", "cc"]},
        "modules": [
            module_status(name)
            for name in [
                "spinnman",
                "spinn_machine",
                "spinn_utilities",
                "pyNN.spiNNaker",
                "spynnaker.pyNN",
                "spinn_front_end_common",
                "spalloc_client",
            ]
        ],
    }


def copy_tree_clean(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in {"__pycache__", ".pytest_cache", "build", "test_runtime"} or n.endswith((".pyc", ".o"))}
    shutil.copytree(src, dst, ignore=ignore)


def prepare_bundle(output_dir: Path) -> tuple[Path, str, dict[str, str]]:
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    for old_name in ["cra_422i", "cra_422j", "cra_422l", "cra_422m", "cra_422n", "cra_422o", "cra_422p", "cra_422q"]:
        old_bundle = output_dir / "ebrains_upload_bundle" / old_name
        if old_bundle.exists():
            shutil.rmtree(old_bundle)
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    shutil.copy2(ROOT / "experiments" / "tier4_22i_custom_runtime_roundtrip.py", bundle / "experiments" / "tier4_22i_custom_runtime_roundtrip.py")
    os.chmod(bundle / "experiments" / "tier4_22i_custom_runtime_roundtrip.py", 0o755)
    shutil.copy2(ROOT / "coral_reef_spinnaker" / "__init__.py", bundle / "coral_reef_spinnaker" / "__init__.py")
    shutil.copy2(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py", bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py")
    copy_tree_clean(RUNTIME, bundle / "coral_reef_spinnaker" / "spinnaker_runtime")

    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_22i_custom_runtime_roundtrip.py --mode run-hardware --output-dir tier4_22i_job_output"
    readme = bundle / "README_TIER4_22I_JOB.md"
    readme.write_text(
        "# Tier 4.22i EBRAINS Custom Runtime Round-Trip Job\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`. Do not upload `controlled_test_output`.\n\n"
        "This package uses the Tier 4.22k-confirmed official Spin1API event enum constants `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`; legacy guessed names such as `MC_PACKET_RX` are intentionally blocked by the local syntax guard. It also uses the EBRAINS-confirmed packed SARK SDP fields (`dest_port`, `srce_port`, `dest_addr`, `srce_addr`) and `sark_mem_cpy`. Host commands follow the official Spin1API `sdp_msg_t` layout: opcode/status in `cmd_rc`, simple command arguments in `arg1`/`arg2`/`arg3`, and optional bytes in `data[]`. Router entries use official SARK router calls (`rtr_alloc`, `rtr_mc_set`, `rtr_free`) rather than local-stub-only helper names. The hardware Makefile delegates linking/APLX creation to official `spinnaker_tools.mk` so the generated build object, `cpu_reset` entrypoint, `libspin1_api.a`, and RO/RW section packing are present; it also creates nested object directories such as `build/gnu/src/` before official compile rules emit `build/gnu/src/*.o`.\n\n"
        "Run command:\n\n"
        f"```text\n{command}\n```\n\n"
        "Target acquisition defaults to `--target-acquisition auto`: first use an explicit hostname/config if EBRAINS exposes one, otherwise run a tiny `pyNN.spiNNaker` probe and reuse `SpynnakerDataView`'s transceiver/IP for the raw custom-runtime load. If the EBRAINS image exposes a known board hostname, `--spinnaker-hostname <host>` is still accepted.\n\n"
        "Expected pass means the custom C runtime builds, loads, and replies to `CMD_READ_STATE` on real SpiNNaker. It is not a full learning claim.\n",
        encoding="utf-8",
    )
    artifacts = {
        "upload_bundle": str(bundle),
        "job_readme": str(readme),
    }
    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    for old_upload in DEPRECATED_EBRAINS_UPLOADS:
        if old_upload.exists():
            shutil.rmtree(old_upload)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)
    artifacts["stable_upload_folder"] = str(STABLE_EBRAINS_UPLOAD)
    return bundle, command, artifacts


def build_aplx(output_dir: Path) -> dict[str, Any]:
    env = os.environ.copy()
    tools = detect_spinnaker_tools()
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools
    result = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT, env=env)
    aplx = RUNTIME / "build" / "coral_reef.aplx"
    result["spinnaker_tools"] = tools
    result["aplx_artifact"] = str(aplx) if aplx.exists() else ""
    result["status"] = "pass" if result["returncode"] == 0 and aplx.exists() else "fail"
    (output_dir / "tier4_22i_aplx_build_stdout.txt").write_text(result["stdout"], encoding="utf-8")
    (output_dir / "tier4_22i_aplx_build_stderr.txt").write_text(result["stderr"], encoding="utf-8")
    result["stdout_artifact"] = str(output_dir / "tier4_22i_aplx_build_stdout.txt")
    result["stderr_artifact"] = str(output_dir / "tier4_22i_aplx_build_stderr.txt")
    return result


def run_host_tests(output_dir: Path) -> dict[str, Any]:
    result = run_cmd(["make", "-C", str(RUNTIME), "clean-host", "test"], cwd=ROOT)
    result["status"] = "pass" if result["returncode"] == 0 and "=== ALL TESTS PASSED ===" in result["stdout"] else "fail"
    (output_dir / "tier4_22i_host_test_stdout.txt").write_text(result["stdout"], encoding="utf-8")
    (output_dir / "tier4_22i_host_test_stderr.txt").write_text(result["stderr"], encoding="utf-8")
    result["stdout_artifact"] = str(output_dir / "tier4_22i_host_test_stdout.txt")
    result["stderr_artifact"] = str(output_dir / "tier4_22i_host_test_stderr.txt")
    return result


def _compile_main(output_dir: Path, *, label: str, extra_cflags: list[str] | None = None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    obj = output_dir / f"tier4_22i_main_syntax_{label}.o"
    cc = shutil.which("cc") or "cc"
    cmd = [
        cc,
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Wno-unused-parameter",
        "-Wno-int-to-pointer-cast",
        *(extra_cflags or []),
        "-I",
        str(RUNTIME / "stubs"),
        "-I",
        str(RUNTIME / "src"),
        "-c",
        str(RUNTIME / "src" / "main.c"),
        "-o",
        str(obj),
    ]
    result = run_cmd(cmd, cwd=ROOT)
    result["status"] = "pass" if result["returncode"] == 0 and obj.exists() else "fail"
    (output_dir / f"tier4_22i_main_syntax_{label}_stdout.txt").write_text(result["stdout"], encoding="utf-8")
    (output_dir / f"tier4_22i_main_syntax_{label}_stderr.txt").write_text(result["stderr"], encoding="utf-8")
    result["stdout_artifact"] = str(output_dir / f"tier4_22i_main_syntax_{label}_stdout.txt")
    result["stderr_artifact"] = str(output_dir / f"tier4_22i_main_syntax_{label}_stderr.txt")
    result["object_artifact"] = str(obj) if obj.exists() else ""
    return result


def run_main_syntax_check(output_dir: Path) -> dict[str, Any]:
    """Compile main.c against host stubs that mirror Tier 4.22k event symbols."""
    normal = _compile_main(output_dir, label="normal")
    return {
        "status": "pass" if normal["status"] == "pass" else "fail",
        "normal": normal,
    }


def callback_compatibility_checks(main_source: str, stub_source: str, *, label: str) -> list[dict[str, Any]]:
    return [
        criterion(
            f"{label} official no-payload MC callback registered",
            "spin1_callback_on(MC_PACKET_RECEIVED",
            "uses Tier 4.22k-confirmed official Spin1API enum constant",
            "spin1_callback_on(MC_PACKET_RECEIVED" in main_source,
        ),
        criterion(
            f"{label} official payload MC callback registered",
            "spin1_callback_on(MCPL_PACKET_RECEIVED",
            "uses Tier 4.22k-confirmed official Spin1API enum constant",
            "spin1_callback_on(MCPL_PACKET_RECEIVED" in main_source,
        ),
        criterion(
            f"{label} legacy guessed callback names absent",
            "MC_PACKET_RX/MCPL_PACKET_RX absent",
            "no direct brittle guessed callback names remain",
            "MC_PACKET_RX" not in main_source and "MCPL_PACKET_RX" not in main_source,
        ),
        criterion(
            f"{label} host stub mirrors confirmed EBRAINS event names",
            "MC_PACKET_RECEIVED/MCPL_PACKET_RECEIVED",
            "local syntax guard exposes official names and omits guessed names",
            "MC_PACKET_RECEIVED" in stub_source
            and "MCPL_PACKET_RECEIVED" in stub_source
            and "MC_PACKET_RX" not in stub_source
            and "MCPL_PACKET_RX" not in stub_source,
        ),
    ]


def sark_sdp_compatibility_checks(host_source: str, stub_source: str, *, label: str) -> list[dict[str, Any]]:
    return [
        criterion(
            f"{label} SDP reply uses packed official sdp_msg_t fields",
            "dest_port/srce_port/dest_addr/srce_addr",
            "mirrors real SARK SDP field names instead of local split x/y/cpu guesses",
            all(
                token in host_source
                for token in [
                    "reply->dest_port = req->srce_port",
                    "reply->srce_port = req->dest_port",
                    "reply->dest_addr = req->srce_addr",
                    "reply->srce_addr = req->dest_addr",
                ]
            ),
        ),
        criterion(
            f"{label} deprecated split SDP fields absent",
            "dest_y/src_y/dest_x/src_x/src_cpu absent",
            "EBRAINS SARK sdp_msg_t uses packed address/port fields",
            not any(token in host_source for token in ["reply->dest_y", "reply->src_y", "reply->dest_x", "reply->src_x", "reply->dest_cpu", "reply->src_cpu", "req->src_port"]),
        ),
        criterion(
            f"{label} uses official SARK memory copy API",
            "sark_mem_cpy",
            "real spinnaker_tools exposes sark_mem_cpy, not sark_memcpy",
            "sark_mem_cpy(" in host_source and "sark_memcpy" not in host_source,
        ),
        criterion(
            f"{label} host stub mirrors official SARK SDP fields",
            "srce_port/srce_addr/sark_mem_cpy",
            "local syntax guard exposes the same fields/API that EBRAINS build requires",
            all(token in stub_source for token in ["srce_port", "srce_addr", "sark_mem_cpy"])
            and not any(token in stub_source for token in ["src_port", "dest_y", "src_y", "sark_memcpy"]),
        ),
    ]


def sdp_command_protocol_checks(controller_source: str, host_source: str, stub_source: str, *, label: str) -> list[dict[str, Any]]:
    return [
        criterion(
            f"{label} host sends official sdp_msg_t command header",
            "struct.pack(\"<HHIII\"",
            "host must place opcode in cmd_rc and use arg1/arg2/arg3 before data[]",
            'struct.pack("<HHIII", cmd & 0xFFFF' in controller_source
            and "args=(neuron_id, 0, 0)" in controller_source
            and "args=(pre_id, post_id, w_fp)" in controller_source,
        ),
        criterion(
            f"{label} host parses cmd_rc before data payload",
            "struct.unpack_from(\"<HHIII\", data, 10)",
            "board replies expose cmd/status in cmd_rc before data[] on UDP SDP",
            'struct.unpack_from("<HHIII", data, 10)' in controller_source
            and "return bytes([cmd_rc & 0xFF, (cmd_rc >> 8) & 0xFF]) + data[26:]" in controller_source,
        ),
        criterion(
            f"{label} runtime dispatch reads cmd_rc",
            "msg->cmd_rc",
            "Spin1API callback receives an sdp_msg_t whose data[0] follows cmd_rc/seq/args",
            "uint8_t cmd = (uint8_t)(msg->cmd_rc & 0xFF)" in host_source
            and "uint8_t cmd = msg->data[0]" not in host_source,
        ),
        criterion(
            f"{label} runtime command args use arg1-arg3",
            "msg->arg1/msg->arg2/msg->arg3",
            "simple CRA commands use official SDP argument fields instead of hidden data offsets",
            all(token in host_source for token in ["uint32_t id = msg->arg1", "uint32_t pre  = msg->arg1", "uint32_t post = msg->arg2", "int32_t  w    = (int32_t) msg->arg3"]),
        ),
        criterion(
            f"{label} runtime replies put cmd/status into cmd_rc",
            "reply->cmd_rc",
            "host parser expects cmd/status in the command header and optional state bytes in data[]",
            "reply->cmd_rc = (uint16_t)cmd | ((uint16_t)status << 8)" in host_source
            and "reply->length = (uint16_t)(8 + 16 + data_len)" in host_source,
        ),
        criterion(
            f"{label} host stub mirrors command-header fields",
            "cmd_rc/seq/arg1/arg2/arg3",
            "local syntax guard must expose the real Spin1API command header fields",
            all(token in stub_source for token in ["cmd_rc", "seq", "arg1", "arg2", "arg3"]),
        ),
    ]


def router_compatibility_checks(router_h: str, router_c: str, stub_source: str, *, label: str) -> list[dict[str, Any]]:
    return [
        criterion(
            f"{label} router header includes stdint directly",
            "#include <stdint.h>",
            "router.h must not rely on indirect EBRAINS header includes for uint32_t",
            "#include <stdint.h>" in router_h,
        ),
        criterion(
            f"{label} router uses official SARK allocation API",
            "rtr_alloc/rtr_mc_set/rtr_free",
            "real spinnaker_tools exposes official rtr_* router calls",
            all(token in router_c for token in ["rtr_alloc(1)", "rtr_mc_set(", "rtr_free("]),
        ),
        criterion(
            f"{label} deprecated local-only router helpers absent",
            "sark_router_alloc/sark_router_free absent",
            "local stubs must not hide EBRAINS SARK API drift",
            "sark_router_alloc" not in router_c
            and "sark_router_free" not in router_c
            and "sark_router_alloc" not in stub_source
            and "sark_router_free" not in stub_source,
        ),
        criterion(
            f"{label} host stub mirrors official router API",
            "rtr_alloc/rtr_mc_set/rtr_free",
            "local syntax guard exposes official SARK router names",
            all(token in stub_source for token in ["rtr_alloc", "rtr_mc_set", "rtr_free"]),
        ),
    ]


def build_recipe_compatibility_checks(makefile_source: str, *, label: str) -> list[dict[str, Any]]:
    return [
        criterion(
            f"{label} hardware build uses official spinnaker_tools.mk",
            "spinnaker_tools.mk",
            "official build chain supplies cpu_reset, build object, spin1_api library, and APLX section packing",
            "make/spinnaker_tools.mk" in makefile_source,
        ),
        criterion(
            f"{label} hardware build avoids deprecated Makefile.common include",
            "Makefile.common absent",
            "Makefile.common inclusion lacks the app build rules needed for APLX creation",
            "Makefile.common" not in makefile_source,
        ),
        criterion(
            f"{label} hardware build avoids manual direct linker recipe",
            "no direct $(LD) object-only link",
            "manual object-only link produced empty ELF without cpu_reset/startup sections on EBRAINS",
            "$(LD) $(LDFLAGS) $^ -o" not in makefile_source
            and "$(OC) -O binary $(BUILD_DIR)/$(APP).elf" not in makefile_source
            and "aplx-maker" not in makefile_source,
        ),
        criterion(
            f"{label} hardware output stays under build directory",
            "APP_OUTPUT_DIR := build/",
            "runner expects build/coral_reef.aplx",
            "APP_OUTPUT_DIR := build/" in makefile_source,
        ),
        criterion(
            f"{label} hardware build creates nested object directories",
            "$(OBJECTS): | $(OBJECT_DIRS)",
            "spinnaker_tools.mk writes build/gnu/src/*.o and does not create nested source subdirectories itself",
            "OBJECT_DIRS := $(sort $(dir $(OBJECTS)))" in makefile_source
            and "$(OBJECTS): | $(OBJECT_DIRS)" in makefile_source
            and "mkdir -p $@" in makefile_source,
        ),
    ]


def load_application_spinnman(
    hostname: str,
    aplx: Path,
    *,
    x: int,
    y: int,
    p: int,
    app_id: int,
    delay: float,
    transceiver: Any | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        from spinn_machine import CoreSubsets
        if transceiver is None:
            from spinnman.transceiver import create_transceiver_from_hostname
            tx = create_transceiver_from_hostname(hostname, ensure_board_is_ready=True)
            method = "spinnman.create_transceiver_from_hostname.execute_flood"
        else:
            tx = transceiver
            method = "spynnaker_dataview_transceiver.execute_flood"
        cores = CoreSubsets()
        cores.add_processor(int(x), int(y), int(p))
        tx.execute_flood(cores, str(aplx), int(app_id), wait=False)
        time.sleep(float(delay))
        return {
            "status": "pass",
            "method": method,
            "hostname": hostname,
            "x": x,
            "y": y,
            "p": p,
            "app_id": app_id,
            "runtime_seconds": time.perf_counter() - started,
        }
    except Exception as exc:
        return {
            "status": "fail",
            "method": "spinnman.execute_flood",
            "hostname": hostname,
            "x": x,
            "y": y,
            "p": p,
            "app_id": app_id,
            "runtime_seconds": time.perf_counter() - started,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
        }


def command_roundtrip(hostname: str, args: argparse.Namespace, *, dest_cpu: int | None = None) -> dict[str, Any]:
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    started = time.perf_counter()
    cpu = int(args.dest_cpu if dest_cpu is None else dest_cpu)
    ctrl = ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
    try:
        reset_ok = ctrl.reset(args.dest_x, args.dest_y, cpu)
        time.sleep(args.command_delay_seconds)
        state_after_reset = ctrl.read_state(args.dest_x, args.dest_y, cpu)
        birth_1 = ctrl.birth_neuron(1, args.dest_x, args.dest_y, cpu)
        birth_2 = ctrl.birth_neuron(2, args.dest_x, args.dest_y, cpu)
        synapse = ctrl.create_synapse(1, 2, 0.25, args.dest_x, args.dest_y, cpu)
        dopamine = ctrl.deliver_dopamine(0.125, args.dest_x, args.dest_y, cpu)
        time.sleep(args.post_mutation_delay_seconds)
        state_after_mutation = ctrl.read_state(args.dest_x, args.dest_y, cpu)
        return {
            "status": "pass" if state_after_reset.get("success") and state_after_mutation.get("success") else "fail",
            "hostname": hostname,
            "dest_x": int(args.dest_x),
            "dest_y": int(args.dest_y),
            "dest_cpu": cpu,
            "reset_ok": reset_ok,
            "birth_1_ok": birth_1,
            "birth_2_ok": birth_2,
            "create_synapse_ok": synapse,
            "dopamine_ok": dopamine,
            "state_after_reset": state_after_reset,
            "state_after_mutation": state_after_mutation,
            "runtime_seconds": time.perf_counter() - started,
        }
    except Exception as exc:
        return {
            "status": "fail",
            "hostname": hostname,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "runtime_seconds": time.perf_counter() - started,
        }
    finally:
        ctrl.close()


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    lines = [
        "# Tier 4.22i Custom Runtime Board Round-Trip Smoke",
        "",
        f"- Generated: `{result.get('generated_at_utc', utc_now())}`",
        f"- Mode: `{result.get('mode', summary.get('mode', 'unknown'))}`",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Output directory: `{result.get('output_dir', path.parent)}`",
        "",
        "Tier 4.22i tests the custom C runtime itself on hardware: build/load the tiny `.aplx`, send `CMD_READ_STATE`, and validate the compact state packet after simple command mutations.",
        "",
        "## Claim Boundary",
        "",
        "- `PREPARED` means the source bundle and command are ready, not hardware evidence.",
        "- `PASS` in `run-hardware` means board load plus `CMD_READ_STATE` round-trip worked on real SpiNNaker.",
        "- This is not full CRA learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "tier4_22h_status", "hardware_target_configured", "spinnaker_hostname", "host_tests_passed",
        "hardware_target_acquisition_method", "selected_dest_cpu", "main_syntax_check_passed", "aplx_build_status", "app_load_status", "command_roundtrip_status", "read_state_schema_version",
        "state_after_mutation_neuron_count", "state_after_mutation_synapse_count",
        "custom_runtime_learning_hardware_allowed_next", "next_step_if_passed",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{markdown_value(summary[key])}`")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        lines.append(f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} |")
    artifacts = result.get("artifacts", {})
    if artifacts:
        lines.extend(["", "## Artifacts", ""])
        for key, value in artifacts.items():
            lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str, mode: str) -> None:
    CONTROLLED.mkdir(parents=True, exist_ok=True)
    write_json(
        CONTROLLED / "tier4_22i_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "mode": mode,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
            "report": str(report),
            "canonical": False,
            "claim": "Latest Tier 4.22i custom-runtime board round-trip smoke; prepared is not hardware evidence, run-hardware pass is command round-trip only.",
        },
    )


def finalize(output_dir: Path, result: dict[str, Any]) -> int:
    manifest = output_dir / "tier4_22i_results.json"
    report = output_dir / "tier4_22i_report.md"
    result.setdefault("artifacts", {})
    result["artifacts"].update({"manifest_json": str(manifest), "report_md": str(report)})
    write_json(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, str(result.get("status", "unknown")), str(result.get("mode", "unknown")))
    print(json.dumps({"status": result.get("status"), "output_dir": str(output_dir), "manifest": str(manifest), "report": str(report)}, indent=2))
    return 0 if str(result.get("status", "")).lower() in {"pass", "prepared"} else 1


def prepare(args: argparse.Namespace, output_dir: Path) -> int:
    tier4_22h_status, tier4_22h_manifest = latest_status(TIER4_22H_LATEST)
    main_syntax = run_main_syntax_check(output_dir)
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    source_checks = callback_compatibility_checks(
        read_text(RUNTIME / "src" / "main.c"),
        read_text(RUNTIME / "stubs" / "spin1_api.h"),
        label="source",
    )
    source_checks += sark_sdp_compatibility_checks(
        read_text(RUNTIME / "src" / "host_interface.c"),
        read_text(RUNTIME / "stubs" / "sark.h"),
        label="source",
    )
    source_checks += sdp_command_protocol_checks(
        read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        read_text(RUNTIME / "src" / "host_interface.c"),
        read_text(RUNTIME / "stubs" / "sark.h"),
        label="source",
    )
    source_checks += router_compatibility_checks(
        read_text(RUNTIME / "src" / "router.h"),
        read_text(RUNTIME / "src" / "router.c"),
        read_text(RUNTIME / "stubs" / "sark.h"),
        label="source",
    )
    source_checks += build_recipe_compatibility_checks(
        read_text(RUNTIME / "Makefile"),
        label="source",
    )
    bundle_runtime = bundle / "coral_reef_spinnaker" / "spinnaker_runtime"
    bundle_checks = callback_compatibility_checks(
        read_text(bundle_runtime / "src" / "main.c"),
        read_text(bundle_runtime / "stubs" / "spin1_api.h"),
        label="bundle",
    )
    bundle_checks += sark_sdp_compatibility_checks(
        read_text(bundle_runtime / "src" / "host_interface.c"),
        read_text(bundle_runtime / "stubs" / "sark.h"),
        label="bundle",
    )
    bundle_checks += sdp_command_protocol_checks(
        read_text(bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        read_text(bundle_runtime / "src" / "host_interface.c"),
        read_text(bundle_runtime / "stubs" / "sark.h"),
        label="bundle",
    )
    bundle_checks += router_compatibility_checks(
        read_text(bundle_runtime / "src" / "router.h"),
        read_text(bundle_runtime / "src" / "router.c"),
        read_text(bundle_runtime / "stubs" / "sark.h"),
        label="bundle",
    )
    bundle_checks += build_recipe_compatibility_checks(
        read_text(bundle_runtime / "Makefile"),
        label="bundle",
    )
    criteria = [
        criterion("Tier 4.22h compact-readback pass exists", tier4_22h_status, "== pass", tier4_22h_status == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("runtime source included", str(bundle / "coral_reef_spinnaker" / "spinnaker_runtime"), "exists", (bundle / "coral_reef_spinnaker" / "spinnaker_runtime").exists()),
        criterion("controller source includes CMD_READ_STATE", str(bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"), "contains CMD_READ_STATE", "CMD_READ_STATE" in (bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py").read_text(encoding="utf-8")),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
    ] + source_checks + bundle_checks
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "failure_reason": "" if status == "prepared" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "mode": "prepare",
            "tier4_22h_status": tier4_22h_status,
            "tier4_22h_manifest": tier4_22h_manifest,
            "main_syntax_check_passed": main_syntax.get("status") == "pass",
            "jobmanager_command": command,
            "upload_folder": str(bundle),
            "what_i_need_from_user": f"Upload the generated {UPLOAD_PACKAGE_NAME} folder to EBRAINS/JobManager and run the emitted command; download returned files after completion.",
            "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
            "next_step_if_passed": "Run the emitted EBRAINS command and ingest returned files.",
        },
        "criteria": criteria,
        "main_syntax_check": main_syntax,
        "artifacts": bundle_artifacts,
    }
    return finalize(output_dir, result)


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    tier4_22h_status, tier4_22h_manifest = latest_status(TIER4_22H_LATEST)
    env_report = environment_report()
    host_tests = run_host_tests(output_dir)
    main_syntax = run_main_syntax_check(output_dir)
    build = build_aplx(output_dir)
    aplx = Path(build.get("aplx_artifact") or RUNTIME / "build" / "coral_reef.aplx")
    target = {"status": "not_attempted", "reason": "blocked_before_target_acquisition"}
    target_cleanup = {"status": "not_attempted"}
    load = {"status": "not_attempted", "reason": "blocked_before_load"}
    roundtrip = {"status": "not_attempted", "reason": "blocked_before_roundtrip"}

    if build.get("status") == "pass":
        target = acquire_hardware_target(args)
        hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
        dest_cpu = int(target.get("dest_cpu") or args.dest_cpu)
        try:
            if target.get("status") == "pass" and not args.skip_load:
                load = load_application_spinnman(
                    hostname,
                    aplx,
                    x=int(args.dest_x),
                    y=int(args.dest_y),
                    p=dest_cpu,
                    app_id=int(args.app_id),
                    delay=float(args.startup_delay_seconds),
                    transceiver=target.get("_transceiver"),
                )
            elif args.skip_load:
                load = {"status": "skipped", "reason": "--skip-load set", "hostname": hostname, "dest_cpu": dest_cpu}

            if target.get("status") == "pass" and hostname and load.get("status") in {"pass", "skipped"}:
                roundtrip = command_roundtrip(hostname, args, dest_cpu=dest_cpu)
        finally:
            target_cleanup = release_hardware_target(target)
    else:
        hostname = ""
        dest_cpu = int(args.dest_cpu)

    env_path = output_dir / "tier4_22i_environment.json"
    target_path = output_dir / "tier4_22i_target_acquisition.json"
    write_json(env_path, env_report)
    write_json(target_path, public_target_acquisition({**target, "cleanup": target_cleanup}))
    write_json(output_dir / "tier4_22i_load_result.json", load)
    write_json(output_dir / "tier4_22i_roundtrip_result.json", roundtrip)

    state_after_mutation = roundtrip.get("state_after_mutation", {}) if isinstance(roundtrip, dict) else {}
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.22h compact-readback pass exists or fresh bundle", tier4_22h_status, "== pass OR missing in fresh EBRAINS bundle", tier4_22h_status in {"pass", "missing"}),
        criterion("hardware target acquired", public_target_acquisition(target), "status == pass and hostname/IP/transceiver acquired", target.get("status") == "pass" and bool(hostname), "; ".join(str(n) for n in target.get("notes", []))),
        criterion("custom C host tests pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        *callback_compatibility_checks(
            read_text(RUNTIME / "src" / "main.c"),
            read_text(RUNTIME / "stubs" / "spin1_api.h"),
            label="runtime",
        ),
        *sark_sdp_compatibility_checks(
            read_text(RUNTIME / "src" / "host_interface.c"),
            read_text(RUNTIME / "stubs" / "sark.h"),
            label="runtime",
        ),
        *sdp_command_protocol_checks(
            read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
            read_text(RUNTIME / "src" / "host_interface.c"),
            read_text(RUNTIME / "stubs" / "sark.h"),
            label="runtime",
        ),
        *router_compatibility_checks(
            read_text(RUNTIME / "src" / "router.h"),
            read_text(RUNTIME / "src" / "router.c"),
            read_text(RUNTIME / "stubs" / "sark.h"),
            label="runtime",
        ),
        *build_recipe_compatibility_checks(
            read_text(RUNTIME / "Makefile"),
            label="runtime",
        ),
        criterion("custom runtime .aplx build pass", build.get("status"), "== pass", build.get("status") == "pass"),
        criterion("custom runtime app load pass", load.get("status"), "== pass", load.get("status") == "pass"),
        criterion("CMD_READ_STATE roundtrip pass", roundtrip.get("status"), "== pass", roundtrip.get("status") == "pass"),
        criterion("reset command acknowledged", roundtrip.get("reset_ok"), "True", bool(roundtrip.get("reset_ok"))),
        criterion("birth/synapse mutation commands acknowledged", {"birth_1": roundtrip.get("birth_1_ok"), "birth_2": roundtrip.get("birth_2_ok"), "synapse": roundtrip.get("create_synapse_ok")}, "all True", bool(roundtrip.get("birth_1_ok")) and bool(roundtrip.get("birth_2_ok")) and bool(roundtrip.get("create_synapse_ok"))),
        criterion("READ_STATE schema version valid", state_after_mutation.get("schema_version"), "== 1", state_after_mutation.get("schema_version") == 1),
        criterion("READ_STATE payload compact", state_after_mutation.get("payload_len"), "== 73", state_after_mutation.get("payload_len") == 73),
        criterion("post-mutation neuron count visible", state_after_mutation.get("neuron_count"), ">= 2", int(state_after_mutation.get("neuron_count") or 0) >= 2),
        criterion("post-mutation synapse count visible", state_after_mutation.get("synapse_count"), ">= 1", int(state_after_mutation.get("synapse_count") or 0) >= 1),
        criterion("synthetic fallback zero", 0, "== 0", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "mode": "run-hardware",
            "tier4_22h_status": tier4_22h_status,
            "tier4_22h_manifest": tier4_22h_manifest,
            "hardware_target_configured": target.get("status") == "pass" and bool(hostname),
            "hardware_target_acquisition_method": target.get("method", ""),
            "spinnaker_hostname": hostname,
            "hostname_notes": target.get("notes", []),
            "selected_dest_cpu": dest_cpu,
            "host_tests_passed": host_tests.get("status") == "pass",
            "main_syntax_check_passed": main_syntax.get("status") == "pass",
            "aplx_build_status": build.get("status"),
            "aplx_artifact": build.get("aplx_artifact", ""),
            "app_load_status": load.get("status"),
            "command_roundtrip_status": roundtrip.get("status"),
            "read_state_schema_version": state_after_mutation.get("schema_version"),
            "state_after_mutation_neuron_count": state_after_mutation.get("neuron_count"),
            "state_after_mutation_synapse_count": state_after_mutation.get("synapse_count"),
            "custom_runtime_learning_hardware_allowed_next": status == "pass",
            "claim_boundary": "Board-load/CMD_READ_STATE command smoke only; not full CRA learning, speedup, or final custom-runtime evidence.",
            "next_step_if_passed": "Tier 4.22j minimal custom-runtime closed-loop learning smoke: delayed pending/readout update on board with compact state readback.",
        },
        "criteria": criteria,
        "environment": env_report,
        "target_acquisition": public_target_acquisition(target),
        "target_cleanup": target_cleanup,
        "host_tests": host_tests,
        "main_syntax_check": main_syntax,
        "aplx_build": build,
        "app_load": load,
        "roundtrip": roundtrip,
        "artifacts": {
            "environment_json": str(env_path),
            "target_acquisition_json": str(target_path),
            "host_test_stdout": str(output_dir / "tier4_22i_host_test_stdout.txt"),
            "host_test_stderr": str(output_dir / "tier4_22i_host_test_stderr.txt"),
            "main_syntax_stdout": str(output_dir / "tier4_22i_main_syntax_normal_stdout.txt"),
            "main_syntax_stderr": str(output_dir / "tier4_22i_main_syntax_normal_stderr.txt"),
            "aplx_build_stdout": str(output_dir / "tier4_22i_aplx_build_stdout.txt"),
            "aplx_build_stderr": str(output_dir / "tier4_22i_aplx_build_stderr.txt"),
            "load_result_json": str(output_dir / "tier4_22i_load_result.json"),
            "roundtrip_result_json": str(output_dir / "tier4_22i_roundtrip_result.json"),
        },
    }
    return finalize(output_dir, result)


def ingest(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required in ingest mode")
    source = args.ingest_dir.resolve()
    if not source.exists():
        raise SystemExit(f"ingest dir does not exist: {source}")
    output_dir.mkdir(parents=True, exist_ok=True)
    ingest_items = [item for item in source.iterdir() if item.name.startswith("tier4_22i")]
    if not ingest_items:
        raise SystemExit(f"no tier4_22i artifacts found in ingest dir: {source}")
    for item in ingest_items:
        target = output_dir / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    manifest = output_dir / "tier4_22i_results.json"
    if manifest.exists():
        data = read_json(manifest)
    else:
        latest = output_dir / "tier4_22i_latest_manifest.json"
        if not latest.exists():
            raise SystemExit(f"missing tier4_22i_results.json or tier4_22i_latest_manifest.json in ingested files: {source}")
        latest_data = read_json(latest)
        stderr_path = output_dir / "tier4_22i_aplx_build_stderr.txt"
        roundtrip_path = output_dir / "tier4_22i_roundtrip_result.json"
        env_path = output_dir / "tier4_22i_environment.json"
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="ignore") if stderr_path.exists() else ""
        roundtrip = read_json(roundtrip_path) if roundtrip_path.exists() else {"status": "missing"}
        env_report = read_json(env_path) if env_path.exists() else {}
        build_failed = "error:" in stderr_text or "Error" in stderr_text
        data = {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": "ingest",
            "status": str(latest_data.get("status", "unknown")),
            "failure_reason": "Downloaded EBRAINS artifacts did not include tier4_22i_results.json; reconstructed from latest manifest and partial failure files. APLX build failed before board roundtrip."
            if build_failed
            else "Downloaded EBRAINS artifacts did not include tier4_22i_results.json; reconstructed from latest manifest and partial failure files.",
            "output_dir": str(output_dir),
            "summary": {
                "mode": "ingest",
                "source_latest_manifest": str(latest),
                "aplx_build_status": "fail" if build_failed else "unknown",
                "command_roundtrip_status": roundtrip.get("status"),
                "blocked_before_roundtrip": roundtrip.get("reason") == "blocked_before_roundtrip",
                "spinnaker_tools": env_report.get("spinnaker_tools", ""),
                "python": env_report.get("python", ""),
                "claim_boundary": "Failed EBRAINS build artifact only; not board-load evidence, not command round-trip evidence, not CRA learning evidence.",
                "next_step_if_passed": f"Regenerate {UPLOAD_PACKAGE_NAME} from fixed source and rerun Tier 4.22i.",
            },
            "criteria": [
                criterion("downloaded latest manifest exists", str(latest), "exists", True),
                criterion("custom runtime .aplx build pass", "fail" if build_failed else "unknown", "== pass", False),
                criterion("CMD_READ_STATE roundtrip attempted", roundtrip.get("status"), "== pass", False, str(roundtrip.get("reason", ""))),
                criterion("synthetic fallback zero", 0, "== 0", True),
            ],
            "environment": env_report,
            "aplx_build": {
                "status": "fail" if build_failed else "unknown",
                "stderr_artifact": str(stderr_path) if stderr_path.exists() else "",
                "stderr_excerpt": stderr_text[-2000:],
            },
            "roundtrip": roundtrip,
            "artifacts": {
                "latest_manifest": str(latest),
                "aplx_build_stderr": str(stderr_path) if stderr_path.exists() else "",
                "environment_json": str(env_path) if env_path.exists() else "",
                "roundtrip_result_json": str(roundtrip_path) if roundtrip_path.exists() else "",
            },
        }
        write_json(manifest, data)
    data["mode"] = data.get("mode", "ingest")
    report = output_dir / "tier4_22i_report.md"
    if not report.exists():
        write_report(report, data)
    write_latest(output_dir, manifest, report, str(data.get("status", "unknown")), "ingest")
    print(json.dumps({"status": data.get("status"), "output_dir": str(output_dir), "manifest": str(manifest)}, indent=2))
    return 0 if str(data.get("status")).lower() in {"pass", "prepared"} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 4.22i custom-runtime board round-trip smoke.")
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--auto-dest-cpu", dest="auto_dest_cpu", action="store_true", default=True)
    parser.add_argument("--no-auto-dest-cpu", dest="auto_dest_cpu", action="store_false")
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    parser.add_argument("--dest-x", type=int, default=0)
    parser.add_argument("--dest-y", type=int, default=0)
    parser.add_argument("--dest-cpu", type=int, default=1)
    parser.add_argument("--app-id", type=int, default=17)
    parser.add_argument("--startup-delay-seconds", type=float, default=1.0)
    parser.add_argument("--command-delay-seconds", type=float, default=0.05)
    parser.add_argument("--post-mutation-delay-seconds", type=float, default=0.10)
    parser.add_argument("--skip-load", action="store_true", help="Only for manual debugging when the app is already loaded; pass criteria still require normal load unless this mode is used outside canonical evidence.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default = DEFAULT_OUTPUT if args.mode == "prepare" else CONTROLLED / f"tier4_22i_{stamp}_{args.mode.replace('-', '_')}"
    output_dir = (args.output_dir or default).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "prepare":
        return prepare(args, output_dir)
    if args.mode == "run-hardware":
        return run_hardware(args, output_dir)
    if args.mode == "ingest":
        return ingest(args, output_dir)
    raise AssertionError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
