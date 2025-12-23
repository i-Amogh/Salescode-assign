"""
Interrupt-filter middleware for LiveKit agents.
Buffers the first <buffer_ms> of user speech and decides:
  - IGNORE → swallow the VAD event (agent keeps talking)
  - FORWARD → let the normal interruption flow proceed
"""

from __future__ import annotations

import asyncio
# import logging
import time
from collections import deque
from typing import TYPE_CHECKING, Deque, List

from livekit import rtc
from prometheus_client import Counter   # type: ignore
from agent.config import settings
from agent.telemetry import start_telemetry_span

if TYPE_CHECKING:
    from prometheus_client import Counter

# logger = logging.getLogger("interrupt_filter")

import logging
log = logging.getLogger("interrupt_filter")

# Prometheus metrics ------------------------------------------------------------
DECISION_COUNTER: Counter = Counter(
    "livekit_interrupt_filter_decision_total",
    "Final decision taken by the interrupt filter",
    ["decision"],
)


class InterruptFilter:
    """
    Listens to VAD start-of-speech while agent is speaking,
    buffers STT partials, and decides whether to ignore or forward
    the interruption.
    """

    def __init__(self, room: rtc.Room) -> None:
        self.room = room
        self.agent_is_speaking = False
        self._buffer: Deque[str] = deque(maxlen=int(settings.interrupt_buffer_ms / 40))  # ~40 ms per partial
        self._partial_event = asyncio.Event()

        # hook LiveKit events
        room.on("track_published", self._on_track_published)
        room.on("track_unpublished", self._on_track_unpublished)
        room.on("vad_start", self._on_vad_start)

    # --------------------------------------------------------------------- #
    # LiveKit event handlers
    # --------------------------------------------------------------------- #
    def _on_track_published(self, track: rtc.Track, *_args: object) -> None:
        """Agent started publishing audio -> we are speaking."""
        if track.kind == rtc.TrackKind.KIND_AUDIO and track.source == rtc.TrackSource.SOURCE_MICROPHONE:
            self.agent_is_speaking = True
            log.debug("Agent started speaking")

    def _on_track_unpublished(self, track: rtc.Track, *_args: object) -> None:
        """Agent stopped publishing audio."""
        if track.kind == rtc.TrackKind.KIND_AUDIO and track.source == rtc.TrackSource.SOURCE_MICROPHONE:
            self.agent_is_speaking = False
            log.debug("Agent stopped speaking")

    async def _on_vad_start(self, event: object) -> None:
        """VAD detected user speech."""
        if not self.agent_is_speaking:
            # agent silent → always forward
            event.forward_interruption()
            DECISION_COUNTER.labels(decision="forward").inc()
            return

        # ---- buffer & classify ----
        with start_telemetry_span("interrupt_decision") as span:
            tokens = await self._buffer_partials()
            decision = self._classify(tokens)
            span.set_attribute("decision", decision)
            span.set_attribute("buffered_tokens", ",".join(tokens))

        log.info("decision=%s tokens=%s", decision, tokens)
        DECISION_COUNTER.labels(decision=decision).inc()

        if decision == "forward":
            event.forward_interruption()

    # --------------------------------------------------------------------- #
    # internal helpers
    # --------------------------------------------------------------------- #
    async def _buffer_partials(self) -> List[str]:
        """Collect STT partials for <buffer_ms>."""
        deadline = asyncio.get_event_loop().time() + (settings.interrupt_buffer_ms / 1000.0)
        tokens: List[str] = []
        while asyncio.get_event_loop().time() < deadline:
            try:
                partial = await self._wait_partial()
                tokens.append(partial.strip().lower())
            except asyncio.TimeoutError:
                break
        return tokens

    async def _wait_partial(self) -> str:
        """Wait for next STT partial (mocked in tests)."""
        # ---- plug-in point for real STT stream ----
        # here we wait on an async queue fed by the transcription service.
        # For Phase-1 unit tests we patch this method.
        timeout = settings.interrupt_buffer_ms / 1000.0
        await asyncio.wait_for(self._partial_event.wait(), timeout=timeout)
        self._partial_event.clear()
        # pop left (oldest) – in real code this comes from the STT queue
        return self._buffer.popleft() if self._buffer else ""

    def _classify(self, tokens: List[str]) -> str:
        """Return 'ignore' or 'forward'."""
        if not tokens:
            return "forward"

        # 1. force words override everything
        if any(t in settings.interrupt_force_list for t in tokens):
            return "forward"

        # 2. all tokens must be ignore-words
        if all(t in settings.interrupt_ignore_list for t in tokens if t):
            return "ignore"

        # 3. default
        return "forward"