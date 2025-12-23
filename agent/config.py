"""
Centralised, pydantic-based configuration for the interrupt-filter feature.
All variables may be overridden by env-vars with the prefix LIVEKIT_.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

# from pydantic import BaseSettings, Field

from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ------------------------------------------------------------------ #
    # Interrupt-filter tuning
    # ------------------------------------------------------------------ #
    interrupt_ignore_list: List[str] = Field(
        default_factory=lambda: [
            "yeah",
            "ok",
            "hmm",
            "uh-huh",
            "right",
            "yep",
            "sure",
        ],
        description="Back-channel words that are ignored while the agent is speaking.",
    )

    interrupt_force_list: List[str] = Field(
        default_factory=lambda: [
            "stop",
            "wait",
            "no",
            "hang on",
            "pause",
        ],
        description="Always trigger interruption (even while agent is speaking).",
    )

    interrupt_buffer_ms: int = Field(
        default=120,
        ge=40,
        le=500,
        description="How long to buffer user speech before making an ignore/forward decision.",
    )

    # ------------------------------------------------------------------ #
    # Telemetry switches
    # ------------------------------------------------------------------ #
    telemetry_enabled: bool = Field(
        default=True,
        description="Emit OpenTelemetry spans & Prometheus metrics.",
    )

    prometheus_port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Port for the Prometheus metrics endpoint.",
    )

    # ------------------------------------------------------------------ #
    # Hot-reload files (Phase 5)
    # ------------------------------------------------------------------ #
    ignore_list_file: Path = Field(
        default=Path("config/ignore_list.txt"),
        description="Path to optional hot-reloadable ignore list.",
    )

    class Config:
        env_prefix = "LIVEKIT_"  # all vars may be overridden by env
        case_sensitive = False


# singleton instance – imported by other modules
settings = Settings()