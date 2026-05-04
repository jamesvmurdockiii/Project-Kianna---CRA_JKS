"""
colony_controller.py
====================
Host-side Python controller for the Coral Reef custom SpiNNaker runtime.

Sends SDP packets over UDP to command neuron birth, death, synapse
creation, global dopamine delivery, and compact state readback.

Protocol MUST stay in sync with spinnaker_runtime/src/config.h.

SDP-over-UDP wire format (AppNote 4 + Spin1API sdp_msg_t):
    bytes 0-1 : 2-byte padding (byte 0 = timeout/0, byte 1 = 0)
    bytes 2-9 : 8-byte SDP header
        byte 2 : flags  (0x07 = reply-not-expected, 0x87 = reply-expected)
        byte 3 : tag    (IPTag, 0xFF for default)
        byte 4 : dest_port_cpu = (dest_port << 5) | dest_cpu
        byte 5 : src_port_cpu  = (src_port  << 5) | src_cpu
        byte 6 : dest_y
        byte 7 : dest_x
        byte 8 : src_y
        byte 9 : src_x
    bytes 10-25: Spin1API/SARK command header
        cmd_rc u16, seq u16, arg1 u32, arg2 u32, arg3 u32
    bytes 26+: optional user data (sdp_msg_t.data)
"""
import socket
import struct
from typing import Optional

# ------------------------------------------------------------------------------
# SDP command opcodes (must match config.h)
# ------------------------------------------------------------------------------
CMD_BIRTH        = 1
CMD_DEATH        = 2
CMD_DOPAMINE     = 3
CMD_READ_SPIKES  = 4
CMD_CREATE_SYN   = 5
CMD_REMOVE_SYN   = 6
CMD_RESET        = 7
CMD_READ_STATE   = 8
CMD_SCHEDULE_PENDING = 9
CMD_MATURE_PENDING   = 10

# ------------------------------------------------------------------------------
# Fixed-point helpers (s16.15)
# ------------------------------------------------------------------------------
FP_SHIFT = 15


def float_to_fp(v: float) -> int:
    return int(v * (1 << FP_SHIFT))


def fp_to_float(v: int) -> float:
    return v / (1 << FP_SHIFT)


# ------------------------------------------------------------------------------
# ColonyController
# ------------------------------------------------------------------------------

class ColonyController:
    """
    UDP/SDP client that talks to a running Coral Reef application on SpiNNaker.

    Parameters
    ----------
    spinnaker_ip : str
        IP address of the SpiNNaker board (default: "192.168.240.253").
    port : int
        UDP port the board listens on for SDP (default: 17893).
    timeout : float
        Seconds to wait for an SDP reply (default: 2.0).
    """

    def __init__(
        self,
        spinnaker_ip: str = "192.168.240.253",
        port: int = 17893,
        timeout: float = 2.0,
    ):
        self.addr = (spinnaker_ip, port)
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)

    # ------------------------------------------------------------------
    # Low-level SDP helpers
    # ------------------------------------------------------------------

    def _build_sdp(
        self,
        cmd: int,
        payload: bytes = b"",
        args: tuple[int, int, int] = (0, 0, 0),
        dest_x: int = 0,
        dest_y: int = 0,
        dest_cpu: int = 1,
        dest_port: int = 1,
        reply_expected: bool = True,
    ) -> bytes:
        """
        Build a raw SDP packet wrapped in the 2-byte UDP padding.

        Header byte order matches AppNote 4 / Rig SDPPacket:
            flags, tag, dest_port_cpu, src_port_cpu, dest_y, dest_x, src_y, src_x
        """
        pad = struct.pack("BB", 0, 0)
        flags = 0x87 if reply_expected else 0x07
        header = struct.pack(
            "<8B",
            flags,
            0xFF,  # tag (default)
            (dest_port & 0x7) << 5 | (dest_cpu & 0x1F),
            (7 << 5) | (31 & 0x1F),  # src_port_cpu (host defaults)
            dest_y,
            dest_x,
            0,     # src_y
            0,     # src_x
        )
        arg1, arg2, arg3 = (int(v) & 0xFFFFFFFF for v in args)
        # Spin1API exposes incoming SDP packets as sdp_msg_t, where cmd_rc,
        # seq, and arg1-3 sit before data[0].
        command_header = struct.pack("<HHIII", cmd & 0xFFFF, 0, arg1, arg2, arg3)
        return pad + header + command_header + payload

    def _send_and_wait(self, packet: bytes) -> Optional[bytes]:
        """Send packet and block for reply. Returns raw UDP data or None on timeout."""
        self.sock.sendto(packet, self.addr)
        try:
            data, _ = self.sock.recvfrom(1024)
            return data
        except socket.timeout:
            return None

    @staticmethod
    def _reply_payload(data: Optional[bytes]) -> bytes:
        """Return the raw SDP payload bytes, or b"" when the packet is invalid."""
        if data is None or len(data) < 11:
            return b""
        if len(data) >= 26:
            cmd_rc, _seq, _arg1, _arg2, _arg3 = struct.unpack_from("<HHIII", data, 10)
            return bytes([cmd_rc & 0xFF, (cmd_rc >> 8) & 0xFF]) + data[26:]
        # Legacy fallback for pre-repair artifacts.
        return data[10:]

    @staticmethod
    def _raw_reply_debug(data: Optional[bytes]) -> dict:
        """Return a compact debug view of received SDP bytes."""
        if data is None:
            return {"received": False, "raw_len": 0, "raw_hex": ""}
        payload = ColonyController._reply_payload(data)
        return {
            "received": True,
            "raw_len": len(data),
            "raw_hex": data.hex(),
            "payload_len": len(payload),
            "payload_hex": payload.hex(),
        }

    @staticmethod
    def _parse_reply(data: Optional[bytes]) -> tuple:
        """
        Parse an SDP reply from raw UDP bytes.

        Returns (cmd: int, status: int, payload: bytes) or (None, None, b"")
        if the packet is too short.
        """
        payload = ColonyController._reply_payload(data)
        if len(payload) < 2:
            return None, None, b""
        return payload[0], payload[1], payload[2:]

    @staticmethod
    def parse_state_payload(payload: bytes) -> dict:
        """Parse the 73-byte CMD_READ_STATE schema-v1 payload."""
        if len(payload) < 73:
            return {"success": False, "reason": "payload_too_short", "payload_len": len(payload)}
        if payload[0] != CMD_READ_STATE:
            return {"success": False, "reason": "wrong_command", "cmd": payload[0]}
        if payload[1] != 0:
            return {"success": False, "reason": "nonzero_status", "status": payload[1]}
        if payload[2] != 1:
            return {"success": False, "reason": "unsupported_schema", "schema_version": payload[2]}

        def u32(offset: int) -> int:
            return struct.unpack_from("<I", payload, offset)[0]

        def s32(offset: int) -> int:
            return struct.unpack_from("<i", payload, offset)[0]

        return {
            "success": True,
            "cmd": payload[0],
            "status": payload[1],
            "schema_version": payload[2],
            "payload_len": len(payload),
            "timestep": u32(4),
            "neuron_count": u32(8),
            "synapse_count": u32(12),
            "active_trace_count": u32(16),
            "active_slots": u32(20),
            "slot_writes": u32(24),
            "slot_hits": u32(28),
            "slot_misses": u32(32),
            "slot_evictions": u32(36),
            "decisions": u32(40),
            "reward_events": u32(44),
            "pending_created": u32(48),
            "pending_matured": u32(52),
            "pending_dropped": u32(56),
            "active_pending": u32(60),
            "readout_weight_raw": s32(64),
            "readout_bias_raw": s32(68),
            "readout_weight": fp_to_float(s32(64)),
            "readout_bias": fp_to_float(s32(68)),
            "flags": payload[72],
        }

    # ------------------------------------------------------------------
    # High-level colony commands
    # ------------------------------------------------------------------

    def birth_neuron(self, neuron_id: int, dest_x=0, dest_y=0, dest_cpu=1) -> bool:
        """Create a new neuron on the target core. Returns True on ack."""
        packet = self._build_sdp(
            CMD_BIRTH,
            args=(neuron_id, 0, 0),
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=dest_cpu,
        )
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return cmd == CMD_BIRTH and status == 0

    def death_neuron(self, neuron_id: int, dest_x=0, dest_y=0, dest_cpu=1) -> bool:
        """Destroy a neuron on the target core. Returns True on ack."""
        packet = self._build_sdp(
            CMD_DEATH,
            args=(neuron_id, 0, 0),
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=dest_cpu,
        )
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return cmd == CMD_DEATH and status == 0

    def create_synapse(
        self,
        pre_id: int,
        post_id: int,
        weight: float,
        dest_x=0,
        dest_y=0,
        dest_cpu=1,
    ) -> bool:
        """Create a synapse pre->post with given weight (float, clamped)."""
        w_fp = float_to_fp(weight)
        packet = self._build_sdp(
            CMD_CREATE_SYN,
            args=(pre_id, post_id, w_fp),
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=dest_cpu,
        )
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return cmd == CMD_CREATE_SYN and status == 0

    def remove_synapse(
        self, pre_id: int, post_id: int, dest_x=0, dest_y=0, dest_cpu=1
    ) -> bool:
        """Remove a synapse pre->post. Returns True on ack."""
        packet = self._build_sdp(
            CMD_REMOVE_SYN,
            args=(pre_id, post_id, 0),
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=dest_cpu,
        )
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return cmd == CMD_REMOVE_SYN and status == 0

    def deliver_dopamine(
        self, level: float, dest_x=0, dest_y=0, dest_cpu=1
    ) -> bool:
        """Broadcast a global dopamine level (float) to the target core."""
        level_fp = float_to_fp(level)
        packet = self._build_sdp(
            CMD_DOPAMINE,
            args=(level_fp, 0, 0),
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=dest_cpu,
        )
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return cmd == CMD_DOPAMINE and status == 0

    def schedule_pending_decision(
        self,
        feature: float,
        delay_steps: int,
        dest_x=0,
        dest_y=0,
        dest_cpu=1,
    ) -> dict:
        """Ask the runtime to predict from feature and schedule delayed credit."""
        packet = self._build_sdp(
            CMD_SCHEDULE_PENDING,
            args=(float_to_fp(feature), int(delay_steps), 0),
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=dest_cpu,
        )
        cmd, status, payload = self._parse_reply(self._send_and_wait(packet))
        if cmd != CMD_SCHEDULE_PENDING or len(payload) < 8:
            return {"success": False, "cmd": cmd, "status": status, "payload_len": len(payload)}
        prediction_raw = struct.unpack_from("<i", payload, 0)[0]
        due_timestep = struct.unpack_from("<I", payload, 4)[0]
        return {
            "success": status == 0,
            "cmd": cmd,
            "status": status,
            "prediction_raw": prediction_raw,
            "prediction": fp_to_float(prediction_raw),
            "due_timestep": due_timestep,
        }

    def mature_pending(
        self,
        target: float,
        learning_rate: float,
        mature_timestep: int = 0,
        dest_x=0,
        dest_y=0,
        dest_cpu=1,
    ) -> dict:
        """Mature due pending horizons with the supplied target and learning rate."""
        packet = self._build_sdp(
            CMD_MATURE_PENDING,
            args=(float_to_fp(target), float_to_fp(learning_rate), int(mature_timestep)),
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=dest_cpu,
        )
        cmd, status, payload = self._parse_reply(self._send_and_wait(packet))
        if cmd != CMD_MATURE_PENDING or len(payload) < 12:
            return {"success": False, "cmd": cmd, "status": status, "payload_len": len(payload)}
        matured_count = struct.unpack_from("<I", payload, 0)[0]
        readout_weight_raw = struct.unpack_from("<i", payload, 4)[0]
        readout_bias_raw = struct.unpack_from("<i", payload, 8)[0]
        return {
            "success": status == 0,
            "cmd": cmd,
            "status": status,
            "matured_count": matured_count,
            "readout_weight_raw": readout_weight_raw,
            "readout_bias_raw": readout_bias_raw,
            "readout_weight": fp_to_float(readout_weight_raw),
            "readout_bias": fp_to_float(readout_bias_raw),
        }

    def read_spikes(self, dest_x=0, dest_y=0, dest_cpu=1) -> dict:
        """
        Query the target core for minimal spike statistics.

        Returns a dict with keys:
            neuron_count, timestep, success
        """
        packet = self._build_sdp(
            CMD_READ_SPIKES,
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=dest_cpu,
        )
        cmd, status, payload = self._parse_reply(self._send_and_wait(packet))
        if cmd != CMD_READ_SPIKES or status != 0 or len(payload) < 4:
            return {"success": False}
        nc = payload[0] | (payload[1] << 8)
        ts = payload[2] | (payload[3] << 8)
        return {
            "success": True,
            "neuron_count": nc,
            "timestep": ts,
        }

    def read_state(self, dest_x=0, dest_y=0, dest_cpu=1) -> dict:
        """Read the compact CMD_READ_STATE schema-v1 state summary."""
        packet = self._build_sdp(
            CMD_READ_STATE,
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=dest_cpu,
        )
        data = self._send_and_wait(packet)
        payload = self._reply_payload(data)
        result = self.parse_state_payload(payload)
        if not result.get("success"):
            result["debug"] = self._raw_reply_debug(data)
        return result

    def reset(self, dest_x=0, dest_y=0, dest_cpu=1) -> bool:
        """Wipe all neurons and synapses on the target core."""
        packet = self._build_sdp(
            CMD_RESET,
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=dest_cpu,
        )
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return cmd == CMD_RESET and status == 0

    def close(self):
        self.sock.close()

    # ------------------------------------------------------------------
    # Convenience batch helpers
    # ------------------------------------------------------------------

    def birth_batch(self, ids: list[int], dest_x=0, dest_y=0, dest_cpu=1) -> list[bool]:
        """Birth multiple neurons; returns list of success flags."""
        return [self.birth_neuron(i, dest_x, dest_y, dest_cpu) for i in ids]

    def wire_random(
        self,
        pre_ids: list[int],
        post_ids: list[int],
        p_connect: float = 0.1,
        weight_mean: float = 0.05,
        weight_std: float = 0.02,
        dest_x=0,
        dest_y=0,
        dest_cpu=1,
    ) -> int:
        """
        Create random synapses between pre and post populations.
        Returns number of synapses successfully created.
        """
        import random

        created = 0
        for pre in pre_ids:
            for post in post_ids:
                if random.random() < p_connect:
                    w = random.gauss(weight_mean, weight_std)
                    if self.create_synapse(pre, post, w, dest_x, dest_y, dest_cpu):
                        created += 1
        return created


# ------------------------------------------------------------------------------
# Simple CLI smoke-test
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Coral Reef Colony Controller")
    parser.add_argument("--ip", default="192.168.240.253", help="SpiNNaker board IP")
    parser.add_argument("--port", type=int, default=17893, help="UDP port")
    parser.add_argument("--cmd", required=True, choices=[
        "birth", "death", "syn", "dopamine", "read", "read-state", "reset"
    ])
    parser.add_argument("--id", type=int, default=0, help="Neuron ID")
    parser.add_argument("--pre", type=int, default=0, help="Pre-synaptic ID")
    parser.add_argument("--post", type=int, default=0, help="Post-synaptic ID")
    parser.add_argument("--weight", type=float, default=0.05, help="Synaptic weight")
    parser.add_argument("--level", type=float, default=1.0, help="Dopamine level")
    args = parser.parse_args()

    ctrl = ColonyController(args.ip, args.port)
    ok = False

    if args.cmd == "birth":
        ok = ctrl.birth_neuron(args.id)
        print(f"Birth neuron {args.id}: {'OK' if ok else 'TIMEOUT/NAK'}")
    elif args.cmd == "death":
        ok = ctrl.death_neuron(args.id)
        print(f"Death neuron {args.id}: {'OK' if ok else 'TIMEOUT/NAK'}")
    elif args.cmd == "syn":
        ok = ctrl.create_synapse(args.pre, args.post, args.weight)
        print(f"Synapse {args.pre}->{args.post}: {'OK' if ok else 'TIMEOUT/NAK'}")
    elif args.cmd == "dopamine":
        ok = ctrl.deliver_dopamine(args.level)
        print(f"Dopamine {args.level}: {'OK' if ok else 'TIMEOUT/NAK'}")
    elif args.cmd == "read":
        result = ctrl.read_spikes()
        print(f"Read spikes: {result}")
    elif args.cmd == "read-state":
        result = ctrl.read_state()
        print(f"Read state: {result}")
    elif args.cmd == "reset":
        ok = ctrl.reset()
        print(f"Reset: {'OK' if ok else 'TIMEOUT/NAK'}")

    ctrl.close()
