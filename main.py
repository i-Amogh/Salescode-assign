#!/usr/bin/env python
"""
Minimal entry point for Phase 1 demo / manual test.
Runs the agent and automatically instantiates the interrupt filter.
"""
import asyncio
import logging
import os

from livekit import rtc
from agent.interrupt_filter import InterruptFilter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

HOST = os.getenv("LIVEKIT_HOST", "ws://localhost:7880")
API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret")


async def main() -> None:
    room = rtc.Room()

    # wire the interrupt filter (only addition vs. vanilla agent)
    InterruptFilter(room)

    # ----- standard LiveKit agent bootstrap -----
    await room.connect(HOST, None, rtc.RoomOptions(
        auto_subscribe=True,
        api_key=API_KEY,
        api_secret=API_SECRET,
    ))
    print("connected to room", room.name)

    try:
        await room.run()
    except KeyboardInterrupt:
        print("shutting down…")
    finally:
        await room.disconnect()


if __name__ == "__main__":
    asyncio.run(main())