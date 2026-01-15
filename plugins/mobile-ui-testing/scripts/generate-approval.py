#!/usr/bin/env python3
"""
Generate approval HTML from recording data.

Usage:
    python3 generate-approval.py <recording_folder> [--output <html_path>]

Examples:
    python3 generate-approval.py tests/mytest/recording
    python3 generate-approval.py tests/mytest/recording --output tests/mytest/approval.html
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def find_available_preconditions(base_path: Path) -> List[str]:
    """Find all available precondition names.

    Preconditions are stored in tests/preconditions/{name}.yaml.
    The base_path is the recording folder (tests/{test-name}/recording/),
    so we navigate up to tests/ and into preconditions/.
    """
    preconditions_dir = base_path.parent.parent / "preconditions"
    if not preconditions_dir.exists():
        return []

    preconditions = []
    for f in preconditions_dir.glob("*.yaml"):
        preconditions.append(f.stem)
    return sorted(preconditions)


def get_template_path() -> Path:
    """Get path to HTML template."""
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if plugin_root:
        return Path(plugin_root) / "templates" / "approval.html"
    return Path(__file__).parent.parent / "templates" / "approval.html"


def load_template() -> str:
    """Load HTML template file."""
    template_path = get_template_path()
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text()


def load_touch_events(recording_folder: Path) -> List[Dict[str, Any]]:
    """Load touch events from recording."""
    touch_file = recording_folder / "touch_events.json"
    if not touch_file.exists():
        return []
    with open(touch_file) as f:
        data = json.load(f)
    return data.get("events", data) if isinstance(data, dict) else data


def load_analysis(recording_folder: Path) -> Dict[str, Any]:
    """Load Claude's analysis if it exists."""
    analysis_file = recording_folder / "analysis.json"
    if not analysis_file.exists():
        return {}
    with open(analysis_file) as f:
        return json.load(f)


def find_screenshots(recording_folder: Path) -> Dict[str, Dict[str, List[str]]]:
    """Find screenshot files organized by step."""
    screenshots_dir = recording_folder / "screenshots"
    if not screenshots_dir.exists():
        return {}

    screenshots: Dict[str, Dict[str, Any]] = {}
    for f in sorted(screenshots_dir.iterdir()):
        if f.suffix.lower() not in ['.png', '.jpg', '.jpeg']:
            continue

        rel_path = f"recording/screenshots/{f.name}"

        # Parse filename patterns:
        # - step_001_before_1.png, step_001_exact.png, step_001_after_1.png (new multi-frame)
        # - touch_001.png (legacy single frame)

        # New format: step_NNN_type.png or step_NNN_type_N.png
        match = re.match(r'step_(\d+)_(before|after|exact)(?:_(\d+))?\.png', f.name)
        if match:
            step_num = match.group(1)
            frame_type = match.group(2)

            if step_num not in screenshots:
                screenshots[step_num] = {'before': [], 'after': [], 'exact': None}

            if frame_type == 'exact':
                screenshots[step_num]['exact'] = rel_path
            else:
                screenshots[step_num][frame_type].append(rel_path)
        else:
            # Legacy format: touch_XXX.png
            touch_match = re.match(r'touch_(\d+)\.png', f.name)
            if touch_match:
                step_num = touch_match.group(1)
                if step_num not in screenshots:
                    screenshots[step_num] = {'before': [], 'after': [], 'exact': None}
                screenshots[step_num]['before'].append(rel_path)

    # Sort before/after lists to ensure correct order (before_1, before_2, before_3)
    for step_num in screenshots:
        screenshots[step_num]['before'].sort()
        screenshots[step_num]['after'].sort()

    return screenshots


def get_video_duration(recording_folder: Path) -> str:
    """Get video duration as formatted string."""
    video_file = recording_folder / "recording.mp4"
    if not video_file.exists():
        return "0:00"

    # Try to get duration from touch events
    touch_file = recording_folder / "touch_events.json"
    if touch_file.exists():
        try:
            with open(touch_file) as f:
                data = json.load(f)
            events = data.get("events", data) if isinstance(data, dict) else data
            if events:
                first_ts = events[0].get("timestamp", 0)
                last_ts = events[-1].get("timestamp", 0)
                duration = last_ts - first_ts
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                return f"{minutes}:{seconds:02d}"
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

    return "0:30"


def build_steps(touch_events: List[Dict[str, Any]], screenshots: Dict[str, Dict[str, List[str]]], analysis: Dict[str, Any], video_start_time: float = 0) -> List[Dict[str, Any]]:
    """Build step objects from touch events.

    Args:
        touch_events: List of touch event dictionaries
        screenshots: Dictionary mapping step numbers to screenshot paths
        analysis: Dictionary mapping step IDs to analysis data
        video_start_time: Unix timestamp when video recording started
                         Used to convert absolute timestamps to video-relative
    """
    steps = []

    # If no video start time provided, use first touch event timestamp
    if video_start_time == 0 and touch_events:
        video_start_time = touch_events[0].get("timestamp", 0)

    for i, event in enumerate(touch_events):
        step_num = f"{i+1:03d}"
        step_id = f"step_{step_num}"

        # Normalize gesture type (handle both "gesture" and "gesture_type" fields)
        gesture = event.get("gesture") or event.get("gesture_type", "tap")

        # Convert absolute timestamp to video-relative time
        abs_timestamp = event.get("timestamp", 0)
        rel_timestamp = abs_timestamp - video_start_time if abs_timestamp > 0 else 0

        step: Dict[str, Any] = {
            "id": step_id,
            "timestamp": rel_timestamp,  # Now relative to video start
            "action": gesture,
            "target": {
                "x": event.get("x"),
                "y": event.get("y"),
                "text": event.get("element_text", "")
            },
            "waitAfter": 0
        }

        # Add screenshots if available
        if step_num in screenshots:
            step["frames"] = screenshots[step_num]

        # Add analysis if available
        step_analysis = analysis.get(step_id, {})
        if step_analysis:
            step["analysis"] = step_analysis.get("analysis", {})
            step["suggestedVerification"] = step_analysis.get("suggestedVerification", "")

        steps.append(step)

    return steps


def generate_html(template: str, data: Dict[str, Any]) -> str:
    """Generate HTML from template and data."""
    # Simple placeholder replacement
    html = template
    html = html.replace("{{testName}}", data.get("testName", "test"))
    html = html.replace("{{stepCount}}", str(len(data.get("steps", []))))
    html = html.replace("{{videoFile}}", data.get("videoFile", "recording.mp4"))
    html = html.replace("{{videoDuration}}", data.get("videoDuration", "0:00"))
    html = html.replace("{{testDataJSON}}", json.dumps(data, indent=2))

    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate approval HTML from recording")
    parser.add_argument("recording_folder", help="Path to recording folder")
    parser.add_argument("--output", "-o", help="Output HTML path")
    parser.add_argument("--test-name", help="Test name (default: folder name)")
    parser.add_argument("--app-package", help="App package name")
    args = parser.parse_args()

    recording_folder = Path(args.recording_folder)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = recording_folder.parent / "approval.html"

    # Determine test name
    test_name = args.test_name or recording_folder.parent.name

    try:
        # Load data
        template = load_template()
        touch_events = load_touch_events(recording_folder)
        screenshots = find_screenshots(recording_folder)
        analysis = load_analysis(recording_folder)

        # Get video duration
        video_duration = get_video_duration(recording_folder)

        # Build test data
        data: Dict[str, Any] = {
            "testName": test_name,
            "appPackage": args.app_package or "com.example.app",
            "videoFile": "recording/recording.mp4",
            "videoDuration": video_duration,
            "steps": build_steps(touch_events, screenshots, analysis),
            "availablePreconditions": find_available_preconditions(recording_folder)
        }

        # Generate HTML
        html = generate_html(template, data)

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)

        print(f"Approval UI generated: {output_path}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
