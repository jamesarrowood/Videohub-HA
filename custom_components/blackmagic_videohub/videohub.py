from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class VideohubState:
    """Parsed Videohub state snapshot."""

    model_name: str | None = None
    unique_id: str | None = None
    input_labels: dict[int, str] = field(default_factory=dict)
    output_labels: dict[int, str] = field(default_factory=dict)
    video_output_routing: dict[int, int] = field(default_factory=dict)
    device_fields: dict[str, str] = field(default_factory=dict)

    @property
    def output_indexes(self) -> list[int]:
        keys = set(self.output_labels) | set(self.video_output_routing)
        return sorted(keys)

    @property
    def input_indexes(self) -> list[int]:
        keys = set(self.input_labels) | set(self.video_output_routing.values())
        return sorted(keys)


class BlackmagicVideohubClient:
    """Minimal TCP client for the Blackmagic Videohub text protocol."""

    def __init__(
        self,
        host: str,
        port: int = 9990,
        *,
        connect_timeout: float = 5.0,
        idle_read_timeout: float = 0.4,
        max_reads: int = 32,
        min_command_interval: float = 0.35,
    ) -> None:
        self._host = host
        self._port = port
        self._connect_timeout = connect_timeout
        self._idle_read_timeout = idle_read_timeout
        self._max_reads = max_reads
        self._min_command_interval = min_command_interval
        self._op_lock = asyncio.Lock()
        self._last_command_at = 0.0

    async def async_fetch_state(self) -> VideohubState:
        """Connect and read a snapshot."""
        async with self._op_lock:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._connect_timeout,
            )
            try:
                raw = await self._async_read_snapshot(reader)
            finally:
                writer.close()
                await writer.wait_closed()

        if not raw:
            raise ConnectionError("No data received from Videohub")
        return parse_videohub_snapshot(raw)

    async def async_route_output(self, output_index: int, input_index: int) -> None:
        """Route one output to one input."""
        if output_index < 0 or input_index < 0:
            raise ValueError("Routing indexes must be >= 0")

        async with self._op_lock:
            loop = asyncio.get_running_loop()
            elapsed = loop.time() - self._last_command_at
            if elapsed < self._min_command_interval:
                await asyncio.sleep(self._min_command_interval - elapsed)

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._connect_timeout,
            )
            try:
                # Drain any initial device banner to keep command exchange ordered.
                await self._async_read_snapshot(reader)
                payload = f"VIDEO OUTPUT ROUTING:\r\n{output_index} {input_index}\r\n\r\n"
                writer.write(payload.encode("utf-8"))
                await asyncio.wait_for(writer.drain(), timeout=self._connect_timeout)
                await asyncio.sleep(0.05)
            finally:
                writer.close()
                await writer.wait_closed()
                self._last_command_at = loop.time()

    async def _async_read_snapshot(self, reader: asyncio.StreamReader) -> bytes:
        chunks: list[bytes] = []

        for _ in range(self._max_reads):
            try:
                chunk = await asyncio.wait_for(
                    reader.read(4096),
                    timeout=self._idle_read_timeout,
                )
            except TimeoutError:
                if chunks:
                    break
                continue

            if not chunk:
                break

            chunks.append(chunk)

            if b"VIDEO OUTPUT ROUTING:" in b"".join(chunks):
                # Most devices send a full snapshot quickly; stop after the stream
                # has gone idle in the next iteration.
                continue

        return b"".join(chunks)


def parse_videohub_snapshot(raw: bytes) -> VideohubState:
    """Parse a Videohub text snapshot into structured state."""
    text = raw.decode("utf-8", errors="ignore").replace("\r\n", "\n")
    state = VideohubState()
    section: str | None = None

    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        if not line:
            section = None
            continue

        if line.endswith(":"):
            section = line[:-1].strip().upper()
            continue

        if section == "VIDEOHUB DEVICE":
            key, value = _parse_key_value(line)
            if key is None:
                continue
            state.device_fields[key] = value
            if key.lower() == "model name":
                state.model_name = value
            elif key.lower() == "unique id":
                state.unique_id = value
            continue

        if section == "INPUT LABELS":
            parsed = _parse_index_and_text(line)
            if parsed:
                idx, label = parsed
                state.input_labels[idx] = label
            continue

        if section == "OUTPUT LABELS":
            parsed = _parse_index_and_text(line)
            if parsed:
                idx, label = parsed
                state.output_labels[idx] = label
            continue

        if section == "VIDEO OUTPUT ROUTING":
            parsed = _parse_index_pair(line)
            if parsed:
                output_idx, input_idx = parsed
                state.video_output_routing[output_idx] = input_idx
            continue

    _ensure_fallback_labels(state)
    return state


def _parse_key_value(line: str) -> tuple[str, str] | tuple[None, None]:
    if ":" not in line:
        return None, None
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _parse_index_and_text(line: str) -> tuple[int, str] | None:
    try:
        idx_str, text = line.split(" ", 1)
    except ValueError:
        return None
    try:
        return int(idx_str), text.strip()
    except ValueError:
        return None


def _parse_index_pair(line: str) -> tuple[int, int] | None:
    parts = line.split()
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _ensure_fallback_labels(state: VideohubState) -> None:
    for idx in state.input_indexes:
        state.input_labels.setdefault(idx, f"Input {idx}")
    for idx in state.output_indexes:
        state.output_labels.setdefault(idx, f"Output {idx}")
