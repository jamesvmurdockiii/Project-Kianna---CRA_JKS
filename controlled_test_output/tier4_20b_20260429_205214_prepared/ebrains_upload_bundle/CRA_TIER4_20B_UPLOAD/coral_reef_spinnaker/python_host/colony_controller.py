"""
colony_controller.py
====================
Host-side Python controller for the Coral Reef custom SpiNNaker runtime.

Sends SDP packets over UDP to command neuron birth, death, synapse
creation, and global dopamine delivery.

Protocol MUST stay in sync with spinnaker_runtime/src/config.h.

SDP-over-UDP wire format (AppNote 4):
    bytes 0-1 : 2-byte padding (byte 0 = timeout/0, byte 1 = 0)
    bytes 2-9 : 8-byte SDP header
        byte 2 : flags  (0x07 = no-reply, 0x87 = reply-expected)
        byte 3 : tag    (IPTag, 0xFF for default)
        byte 4 : dest_port_cpu = (dest_port << 5) | dest_cpu
        byte 5 : src_port_cpu  = (src_port  << 5) | src_cpu
        byte 6 : dest_y
        byte 7 : dest_x
        byte 8 : src_y
        byte 9 : src_x
    bytes 10+: payload (our custom command bytes)
"""
import struct
import socket
import time
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
        dest_x: int = 0,
        dest_y: int = 0,
        dest_cpu: int = 1,
        dest_port: int = 1,
    ) -> bytes:
        """
        Build a raw SDP packet wrapped in the 2-byte UDP padding.

        Header byte order matches AppNote 4 / Rig SDPPacket:
            flags, tag, dest_port_cpu, src_port_cpu, dest_y, dest_x, src_y, src_x
        """
        pad = struct.pack("BB", 0, 0)
        header = struct.pack(
            "<8B",
            0x07,  # flags (reply expected)
            0xFF,  # tag (default)
            (dest_port & 0x7) << 5 | (dest_cpu & 0x1F),
            (7 << 5) | (31 & 0x1F),  # src_port_cpu (host defaults)
            dest_y,
            dest_x,
            0,     # src_y
            0,     # src_x
        )
        return pad + header + struct.pack("B", cmd) + payload

    def _send_and_wait(self, packet: bytes) -> Optional[bytes]:
        """Send packet and block for reply. Returns raw UDP data or None on timeout."""
        self.sock.sendto(packet, self.addr)
        try:
            data, _ = self.sock.recvfrom(1024)
            return data
        except socket.timeout:
            return None

    @staticmethod
    def _parse_reply(data: bytes) -> tuple:
        """
        Parse an SDP reply from raw UDP bytes.

        Returns (cmd: int, status: int, payload: bytes) or (None, None, b"")
        if the packet is too short.
        """
        if data is None or len(data) < 12:
            return None, None, b""
        # Skip 2-byte padding, 8-byte header -> payload starts at byte 10
        payload = data[10:]
        if len(payload) < 2:
            return None, None, b""
        return payload[0], payload[1], payload[2:]

    # ------------------------------------------------------------------
    # High-level colony commands
    # ------------------------------------------------------------------

    def birth_neuron(self, neuron_id: int, dest_x=0, dest_y=0, dest_cpu=1) -> bool:
        """Create a new neuron on the target core. Returns True on ack."""
        payload = struct.pack("<I", neuron_id)
        packet = self._build_sdp(CMD_BIRTH, payload, dest_x, dest_y, dest_cpu)
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return status == 0

    def death_neuron(self, neuron_id: int, dest_x=0, dest_y=0, dest_cpu=1) -> bool:
        """Destroy a neuron on the target core. Returns True on ack."""
        payload = struct.pack("<I", neuron_id)
        packet = self._build_sdp(CMD_DEATH, payload, dest_x, dest_y, dest_cpu)
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return status == 0

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
        payload = struct.pack("<IIi", pre_id, post_id, w_fp)
        packet = self._build_sdp(CMD_CREATE_SYN, payload, dest_x, dest_y, dest_cpu)
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return status == 0

    def remove_synapse(
        self, pre_id: int, post_id: int, dest_x=0, dest_y=0, dest_cpu=1
    ) -> bool:
        """Remove a synapse pre->post. Returns True on ack."""
        payload = struct.pack("<II", pre_id, post_id)
        packet = self._build_sdp(CMD_REMOVE_SYN, payload, dest_x, dest_y, dest_cpu)
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return status == 0

    def deliver_dopamine(
        self, level: float, dest_x=0, dest_y=0, dest_cpu=1
    ) -> bool:
        """Broadcast a global dopamine level (float) to the target core."""
        level_fp = float_to_fp(level)
        payload = struct.pack("<i", level_fp)
        packet = self._build_sdp(CMD_DOPAMINE, payload, dest_x, dest_y, dest_cpu)
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return status == 0

    def read_spikes(self, dest_x=0, dest_y=0, dest_cpu=1) -> dict:
        """
        Query the target core for spike statistics.

        Returns a dict with keys:
            neuron_count, timestep, success
        """
        packet = self._build_sdp(CMD_READ_SPIKES, b"", dest_x, dest_y, dest_cpu)
        cmd, status, payload = self._parse_reply(self._send_and_wait(packet))
        if status is None or len(payload) < 4:
            return {"success": False}
        nc = payload[0] | (payload[1] << 8)
        ts = payload[2] | (payload[3] << 8)
        return {
            "success": True,
            "neuron_count": nc,
            "timestep": ts,
        }

    def reset(self, dest_x=0, dest_y=0, dest_cpu=1) -> bool:
        """Wipe all neurons and synapses on the target core."""
        packet = self._build_sdp(CMD_RESET, b"", dest_x, dest_y, dest_cpu)
        cmd, status, _ = self._parse_reply(self._send_and_wait(packet))
        return status == 0

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
        "birth", "death", "syn", "dopamine", "read", "reset"
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
    elif args.cmd == "reset":
        ok = ctrl.reset()
        print(f"Reset: {'OK' if ok else 'TIMEOUT/NAK'}")

    ctrl.close()
