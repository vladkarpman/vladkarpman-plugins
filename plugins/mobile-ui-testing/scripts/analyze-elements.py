#!/usr/bin/env python3
"""
Analyze action frames to identify tapped UI elements.

This script is called by Claude during stop-recording to identify
what element was tapped at each step based on the action frame screenshot.

Usage:
    python3 analyze-elements.py <touch_events.json> <test_folder>

Output:
    Updates touch_events.json with element_text for each step.
    Prints analysis results as JSON for Claude to process.
"""

import json
import sys
from pathlib import Path


def load_events(events_path: Path) -> list:
    """Load touch events from JSON file."""
    with open(events_path) as f:
        content = f.read().strip()
        if content.startswith('['):
            return json.loads(content)
        else:
            # JSON Lines format
            return [json.loads(line) for line in content.split('\n') if line.strip()]


def main():
    if len(sys.argv) < 3:
        print("Usage: analyze-elements.py <touch_events.json> <test_folder>", file=sys.stderr)
        sys.exit(1)

    events_path = Path(sys.argv[1])
    test_folder = Path(sys.argv[2])

    events = load_events(events_path)

    # Build analysis requests for Claude
    analysis_requests = []
    for event in events:
        step_num = event.get("index", 0)
        x = event.get("x", 0)
        y = event.get("y", 0)

        # Get action frame path
        frames = event.get("frames", {})
        action_frame = frames.get("action", "")

        if action_frame:
            frame_path = test_folder / action_frame
            if frame_path.exists():
                analysis_requests.append({
                    "step": step_num,
                    "frame_path": str(frame_path),
                    "tap_x": x,
                    "tap_y": y,
                    "screen_width": event.get("screen_width", 1080),
                    "screen_height": event.get("screen_height", 2340)
                })

    # Output requests for Claude to process
    print(json.dumps({
        "events_path": str(events_path),
        "requests": analysis_requests
    }, indent=2))


if __name__ == "__main__":
    main()
