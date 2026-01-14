#!/usr/bin/env python3
"""Scrcpy backend - fast device interaction via scrcpy protocol."""

import asyncio
import io
import logging
import sys
from pathlib import Path
from typing import Any

from PIL import Image
import numpy as np

logger = logging.getLogger("device-manager.scrcpy")

# Add scrcpy_helper to path
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
SCRCPY_HELPER_DIR = SCRIPTS_DIR / "scrcpy_helper"


class ScrcpyBackend:
    """Fast device interaction using scrcpy_helper."""

    def __init__(self):
        self._client = None
        self._connected = False
        self._screen_size: tuple[int, int] | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Try to connect to device via scrcpy. Returns True if successful."""
        if self._connected and self._client:
            return True

        try:
            # Import scrcpy_helper
            if str(SCRIPTS_DIR) not in sys.path:
                sys.path.insert(0, str(SCRIPTS_DIR))

            from scrcpy_helper.client import ScrcpyClient

            # Create client and connect
            self._client = ScrcpyClient()

            # Try to connect (this starts scrcpy if needed)
            loop = asyncio.get_event_loop()
            connected = await loop.run_in_executor(None, self._client.connect)

            if connected:
                self._connected = True
                # Get screen size
                resolution = await loop.run_in_executor(None, self._client.get_resolution)
                if resolution:
                    self._screen_size = resolution
                logger.info(f"scrcpy connected, screen: {self._screen_size}")
                return True
            else:
                logger.warning("scrcpy connection failed")
                return False

        except ImportError as e:
            logger.warning(f"scrcpy_helper not available: {e}")
            return False
        except Exception as e:
            logger.warning(f"scrcpy connection error: {e}")
            return False

    async def screenshot(self) -> bytes:
        """Take a screenshot. Returns PNG bytes."""
        if not self._connected or not self._client:
            raise RuntimeError("scrcpy not connected")

        loop = asyncio.get_event_loop()
        frame_data = await loop.run_in_executor(None, self._client.get_frame)

        # get_frame returns (frame, timestamp) tuple
        frame = frame_data[0] if isinstance(frame_data, tuple) else frame_data

        if frame is None:
            raise RuntimeError("Failed to get frame from scrcpy")

        # Convert numpy array to PNG bytes
        if isinstance(frame, np.ndarray):
            img = Image.fromarray(frame)
        else:
            img = frame

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    async def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        if not self._connected or not self._client:
            raise RuntimeError("scrcpy not connected")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.tap, x, y)

    async def swipe(
        self,
        start_x: int, start_y: int,
        end_x: int, end_y: int,
        duration_ms: int = 300
    ) -> None:
        """Swipe from start to end coordinates."""
        if not self._connected or not self._client:
            raise RuntimeError("scrcpy not connected")

        loop = asyncio.get_event_loop()
        # client.swipe(x1, y1, x2, y2, steps, duration_ms)
        steps = max(10, duration_ms // 30)  # ~30ms per step
        await loop.run_in_executor(
            None,
            self._client.swipe,
            start_x, start_y, end_x, end_y, steps, duration_ms
        )

    async def type_text(self, text: str) -> None:
        """Type text."""
        if not self._connected or not self._client:
            raise RuntimeError("scrcpy not connected")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.type_text, text)

    async def press_key(self, key: str) -> None:
        """Press a key (BACK, HOME, ENTER, etc.)."""
        if not self._connected or not self._client:
            raise RuntimeError("scrcpy not connected")

        # Map key names to Android keycodes
        key_map = {
            "BACK": 4,
            "HOME": 3,
            "ENTER": 66,
            "VOLUME_UP": 24,
            "VOLUME_DOWN": 25,
            "POWER": 26,
            "TAB": 61,
            "ESCAPE": 111,
            "DELETE": 67,
        }

        keycode = key_map.get(key.upper())
        if keycode is None:
            raise ValueError(f"Unknown key: {key}")

        loop = asyncio.get_event_loop()
        # client.key(keycode) - uses adb fallback internally
        await loop.run_in_executor(None, self._client.key, keycode)

    async def get_screen_size(self) -> tuple[int, int]:
        """Get screen size."""
        if self._screen_size:
            return self._screen_size

        if not self._connected or not self._client:
            raise RuntimeError("scrcpy not connected")

        loop = asyncio.get_event_loop()
        resolution = await loop.run_in_executor(None, self._client.get_resolution)
        if resolution:
            self._screen_size = resolution
            return self._screen_size

        raise RuntimeError("Failed to get screen size")
