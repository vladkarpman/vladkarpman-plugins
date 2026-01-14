#!/usr/bin/env python3
"""
Background screenshot capture for test verification.

Usage:
    python3 screenshot-buffer.py --device DEVICE_ID --output /tmp/buffer --interval 150

Captures screenshots every INTERVAL ms, saves to OUTPUT directory with timestamps.
Runs until killed (SIGTERM/SIGINT).
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


class ScreenshotBuffer:
    def __init__(self, device: str, output_dir: Path, interval_ms: int = 150):
        self.device = device
        self.output_dir = output_dir
        self.interval_ms = interval_ms
        self.running = False
        self.manifest = {
            "device": device,
            "started_at": None,
            "capture_interval_ms": interval_ms,
            "screenshots": []
        }
        self.max_screenshots = 200  # Rolling buffer limit

    def setup(self):
        """Create output directory and initialize manifest."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest["started_at"] = time.time()
        self._write_manifest()

    def _write_manifest(self):
        """Write manifest.json to output directory."""
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def capture_screenshot(self) -> Optional[str]:
        """Capture screenshot via ADB, return filename or None on failure."""
        timestamp = time.time()
        filename = f"{timestamp:.3f}.png"
        device_path = "/sdcard/screen_buffer.png"
        local_path = self.output_dir / filename

        try:
            # Capture on device
            subprocess.run(
                ["adb", "-s", self.device, "shell", "screencap", "-p", device_path],
                check=True,
                capture_output=True,
                timeout=5
            )

            # Pull to local
            subprocess.run(
                ["adb", "-s", self.device, "pull", device_path, str(local_path)],
                check=True,
                capture_output=True,
                timeout=5
            )

            # Add to manifest
            self.manifest["screenshots"].append({
                "timestamp": timestamp,
                "file": filename
            })

            # Enforce rolling buffer limit
            self._cleanup_old_screenshots()

            self._write_manifest()
            return filename

        except subprocess.TimeoutExpired:
            print(f"Screenshot timeout at {timestamp}", file=sys.stderr)
            return None
        except subprocess.CalledProcessError as e:
            print(f"Screenshot failed: {e}", file=sys.stderr)
            return None

    def _cleanup_old_screenshots(self):
        """Remove oldest screenshots if over limit."""
        while len(self.manifest["screenshots"]) > self.max_screenshots:
            oldest = self.manifest["screenshots"].pop(0)
            old_path = self.output_dir / oldest["file"]
            if old_path.exists():
                old_path.unlink()

    def run(self):
        """Main capture loop."""
        self.running = True
        self.setup()

        print(f"Buffer started: {self.output_dir}", file=sys.stderr)
        print(f"Capturing every {self.interval_ms}ms", file=sys.stderr)

        while self.running:
            start = time.time()
            self.capture_screenshot()

            # Sleep for remaining interval
            elapsed_ms = (time.time() - start) * 1000
            sleep_ms = max(0, self.interval_ms - elapsed_ms)
            time.sleep(sleep_ms / 1000)

    def stop(self):
        """Stop the capture loop."""
        self.running = False
        print(f"Buffer stopped. {len(self.manifest['screenshots'])} screenshots captured.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Background screenshot capture")
    parser.add_argument("--device", required=True, help="ADB device ID")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--interval", type=int, default=150, help="Capture interval in ms")
    args = parser.parse_args()

    buffer = ScreenshotBuffer(
        device=args.device,
        output_dir=Path(args.output),
        interval_ms=args.interval
    )

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        buffer.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    buffer.run()


if __name__ == "__main__":
    main()
