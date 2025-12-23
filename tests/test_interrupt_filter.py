"""
Unit tests for agent/interrupt_filter.py
Uses mocked Room + STT stream so no real LiveKit server required.
"""

from __future__ import annotations

import asyncio
from typing import List

import pytest
from livekit import rtc

from agent.config import settings
from agent.interrupt_filter import InterruptFilter

# import logging
# log = logging.getLogger("interrupt_filter")


class VadStartEvent:
    """Fake VAD event we can spy on."""
    def __init__(self) -> None:
        self.forwarded = False

    def forward_interruption(self) -> None:
        self.forwarded = True


# ------------------------------------------------------------------ #
# Test cases
# ------------------------------------------------------------------ #
@pytest.mark.asyncio
async def test_ignore_when_speaking(mock_room, mock_stt_stream) -> None:
    """Agent is speaking + user says only back-channel words → IGNORE."""
    room = mock_room
    filt = InterruptFilter(room)

    # agent starts speaking
    # track = rtc.Track(
    #     kind=rtc.TrackKind.KIND_AUDIO,
    #     source=rtc.TrackSource.SOURCE_MICROPHONE,
    # )
    # track = rtc.Track.create_audio_track("agent-mic")
    # NEW (minimal mock)
    track = type("MockTrack", (), {
        "kind": rtc.TrackKind.KIND_AUDIO,
        "source": rtc.TrackSource.SOURCE_MICROPHONE,
    })()
    await room.emit("track_published", track)

    # user says “yeah ok”
    canned = ["yeah", "ok"]
    stream = mock_stt_stream(canned, delay_ms=40)

    # patch the internal helper so it feeds from our stream
    async def _mock_wait():
        async for partial in stream.stream():
            filt._buffer.append(partial.lower())
            filt._partial_event.set()

    asyncio.create_task(_mock_wait())

    event = VadStartEvent()
    await filt._on_vad_start(event)

    assert event.forwarded is False, "should have ignored the interruption"


@pytest.mark.asyncio
async def test_forward_when_silent(mock_room, mock_stt_stream) -> None:
    """Agent is silent → any user input is forwarded."""
    room = mock_room
    filt = InterruptFilter(room)

    # agent NOT speaking (default)
    stream = mock_stt_stream(["yeah"], delay_ms=40)
    # asyncio.create_task(_feed_stream(filt, stream))
    await _feed_stream(filt, stream)

    event = VadStartEvent()
    await filt._on_vad_start(event)

    assert event.forwarded is True, "should forward when agent silent"


@pytest.mark.asyncio
async def test_mixed_input_interrupt(mock_room, mock_stt_stream) -> None:
    """Agent speaking + user says “yeah but wait” → FORWARD (because “wait”)."""
    room = mock_room
    filt = InterruptFilter(room)

    # track = rtc.Track(
    #     kind=rtc.TrackKind.KIND_AUDIO,
    #     source=rtc.TrackSource.SOURCE_MICROPHONE,
    # )
    # track = rtc.Track.create_audio_track("agent-mic")
    # NEW (minimal mock)
    track = type("MockTrack", (), {
        "kind": rtc.TrackKind.KIND_AUDIO,
        "source": rtc.TrackSource.SOURCE_MICROPHONE,
    })()
    await room.emit("track_published", track)

    stream = mock_stt_stream(["yeah but wait"], delay_ms=40)
    # asyncio.create_task(_feed_stream(filt, stream))
    await _feed_stream(filt, stream)

    event = VadStartEvent()
    await filt._on_vad_start(event)

    print("BUFFER:", list(filt._buffer))
    
    assert event.forwarded is True, "mixed input with force word must forward"


@pytest.mark.asyncio
async def test_latency_under_160ms(mock_room, mock_stt_stream) -> None:
    """Decision must be taken within 160 ms (hard requirement)."""
    room = mock_room
    filt = InterruptFilter(room)

    # track = rtc.Track(
    #     kind=rtc.TrackKind.KIND_AUDIO,
    #     source=rtc.TrackSource.SOURCE_MICROPHONE,
    # )
    # track = rtc.Track.create_audio_track("agent-mic")
    # NEW (minimal mock)
    track = type("MockTrack", (), {
        "kind": rtc.TrackKind.KIND_AUDIO,
        "source": rtc.TrackSource.SOURCE_MICROPHONE,
    })()
    await room.emit("track_published", track)

    stream = mock_stt_stream(["yeah"], delay_ms=40)
    # asyncio.create_task(_feed_stream(filt, stream))
    await _feed_stream(filt, stream)

    t0 = asyncio.get_event_loop().time()
    event = VadStartEvent()
    await filt._on_vad_start(event)
    latency_ms = (asyncio.get_event_loop().time() - t0) * 1000

    assert latency_ms <= 160, f"latency {latency_ms:.1f} ms > 160 ms"


# ------------------------------------------------------------------ #
# helper
# ------------------------------------------------------------------ #
# async def _feed_stream(filt: InterruptFilter, stream: mock_stt_stream) -> None:
#     """Push canned partials into the filter’s buffer."""
#     async for partial in stream.stream():
#         filt._buffer.append(partial.lower())
#         filt._partial_event.set()

# ------------------------------------------------------------------ #
# helper
# ------------------------------------------------------------------ #
async def _feed_stream(filt: InterruptFilter, stream) -> None:
    """Push canned partials into the filter’s buffer."""
    async for partial in stream.stream():
        filt._buffer.append(partial.lower())
        filt._partial_event.set()