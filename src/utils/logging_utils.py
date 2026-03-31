"""Shared logging helpers for CLI entrypoints."""

from __future__ import annotations

import logging
import sys
from typing import TextIO


def build_stdout_stream_handler(stream: TextIO | None = None) -> logging.StreamHandler:
    """Return a stream handler that defaults to stdout for CLI-friendly logging."""
    return logging.StreamHandler(stream=stream or sys.stdout)
