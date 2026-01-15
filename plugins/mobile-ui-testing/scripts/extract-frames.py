#!/usr/bin/env python3
"""
Extract frames from video at specific timestamps using ffmpeg.

Smart extraction: calculates safe boundaries between steps to prevent overlap.
Extracts 3 frames per step: before, action, after.
Uses parallel processing for speed.
"""

import subprocess
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Number of parallel ffmpeg processes
MAX_WORKERS = min(24, (os.cpu_count() or 4) * 4)

# Default timing preferences (in seconds)
# UI responds instantly to touch, so we capture BEFORE touch occurs:
# Before: Stable state well before tap decision
# Action: Moment just before finger contact (shows target button)
# After: Result after UI has settled
BEFORE_OFFSET = 0.5   # 500ms before touch - stable pre-tap state
ACTION_OFFSET = 0.3   # 300ms before touch - target visible, about to tap
AFTER_OFFSET = 0.5    # 500ms after touch end - settled result
SAFE_MARGIN = 0.05    # 50ms margin from adjacent steps


def extract_frame(video_path: str, timestamp_sec: float, output_path: str) -> Tuple[str, bool]:
    """
    Extract a single frame from video at given timestamp.

    Returns tuple of (output_path, success).
    """
    # Ensure timestamp is not negative
    timestamp_sec = max(0, timestamp_sec)

    cmd = [
        "ffmpeg",
        "-ss", f"{timestamp_sec:.3f}",  # Seek to timestamp
        "-i", video_path,
        "-frames:v", "1",  # Extract 1 frame
        "-q:v", "2",  # High quality
        "-y",  # Overwrite
        "-loglevel", "error",  # Suppress verbose output
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return output_path, result.returncode == 0


def calculate_smart_frame_times(
    touch_events: List[Dict[str, Any]],
    video_start_time: float,
    video_duration: float
) -> List[Dict[str, Any]]:
    """
    Calculate frame extraction times with smart boundaries.

    Key insight: touch timestamp is when finger LIFTS (touch end).
    The actual tap started duration_ms earlier.

    Frame timing:
    - before: stable state before finger contact (BEFORE_OFFSET before touch start)
    - action: moment of finger contact (touch start = timestamp - duration_ms)
    - after: result after UI settles (AFTER_OFFSET after touch end)

    Safe boundaries prevent overlap with adjacent steps.
    """
    frame_times = []
    video_end_time = video_start_time + video_duration

    for i, event in enumerate(touch_events):
        if "index" not in event or "timestamp" not in event:
            continue

        touch_end_time = event["timestamp"]
        duration_ms = event.get("duration_ms", 50)  # Default 50ms if not present
        touch_start_time = touch_end_time - (duration_ms / 1000.0)
        step_num = event["index"]

        # Calculate safe boundaries
        if i > 0:
            prev_time = touch_events[i - 1]["timestamp"]
            before_safe = prev_time + SAFE_MARGIN
        else:
            before_safe = video_start_time

        if i < len(touch_events) - 1:
            next_time = touch_events[i + 1]["timestamp"]
            after_safe = next_time - SAFE_MARGIN
        else:
            after_safe = video_end_time

        # Calculate frame times based on touch start/end
        # Before: stable state well before tap
        before_time = max(touch_start_time - BEFORE_OFFSET, before_safe)
        # Action: moment just BEFORE finger contact - shows target button
        action_time = max(touch_start_time - ACTION_OFFSET, before_safe)
        # After: result after UI has responded and settled
        after_time = min(touch_end_time + AFTER_OFFSET, after_safe)

        # Convert to video-relative times
        frame_times.append({
            "step_num": step_num,
            "before": before_time - video_start_time,
            "action": action_time - video_start_time,
            "after": after_time - video_start_time,
        })

    return frame_times


def build_extraction_tasks(
    video_path: str,
    frame_times: List[Dict[str, Any]],
    output_dir: Path
) -> List[Tuple[str, float, str, int, str]]:
    """
    Build list of extraction tasks from calculated frame times.

    Returns list of (video_path, timestamp, output_path, step_num, frame_type).
    """
    tasks = []

    for ft in frame_times:
        step_num = ft["step_num"]
        step_str = f"{step_num:03d}"

        for frame_type in ["before", "action", "after"]:
            frame_position = ft[frame_type]
            frame_filename = f"step_{step_str}_{frame_type}.png"
            frame_path = str(output_dir / frame_filename)

            tasks.append((video_path, frame_position, frame_path, step_num, frame_type))

    return tasks


def extract_frames_parallel(
    video_path: str,
    touch_events: List[Dict[str, Any]],
    video_start_time: float,
    video_duration: float,
    output_dir: str
) -> List[Dict[str, Any]]:
    """
    Extract frames for all touch events in parallel.

    Returns list of touch events with frame paths added.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Calculate smart frame times
    frame_times = calculate_smart_frame_times(touch_events, video_start_time, video_duration)

    # Build all extraction tasks
    tasks = build_extraction_tasks(video_path, frame_times, output_path)

    print(f"Extracting {len(tasks)} frames using {MAX_WORKERS} parallel workers...", file=sys.stderr)

    # Track results by step
    results: Dict[int, Dict[str, str]] = {}
    completed = 0

    # Run extractions in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(extract_frame, video, ts, out): (step_num, frame_type)
            for video, ts, out, step_num, frame_type in tasks
        }

        # Collect results as they complete
        for future in as_completed(future_to_task):
            step_num, frame_type = future_to_task[future]
            output_path_str, success = future.result()

            if step_num not in results:
                results[step_num] = {}

            if success:
                # Store relative path
                filename = Path(output_path_str).name
                results[step_num][frame_type] = f"recording/screenshots/{filename}"
            else:
                results[step_num][frame_type] = None

            completed += 1
            if completed % 50 == 0 or completed == len(tasks):
                print(f"  Progress: {completed}/{len(tasks)} frames", file=sys.stderr)

    # Update events with frame paths
    updated_events = []
    for event in touch_events:
        if "index" not in event:
            continue

        step_num = event["index"]
        frames = results.get(step_num, {})

        event["frames"] = frames
        # Backward compatibility - set screenshot to before
        event["screenshot"] = frames.get("before")

        updated_events.append(event)

    return updated_events


def get_video_duration(video_path: str) -> Optional[float]:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass
    return None


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: extract-frames.py <video> <touch_events.json> <video_start_time> <output_dir>", file=sys.stderr)
        sys.exit(1)

    # Check ffmpeg is installed
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
        print("Error: ffmpeg not found. Install with: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    video_path = sys.argv[1]
    events_path = sys.argv[2]
    output_dir = sys.argv[4]

    # Validate video file exists
    video_file = Path(video_path)
    if not video_file.exists():
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    # Validate video_start_time is a number
    try:
        video_start = float(sys.argv[3])
    except ValueError:
        print(f"Error: video_start_time must be a number, got: {sys.argv[3]}", file=sys.stderr)
        sys.exit(1)

    # Load and validate events file (supports JSON array or JSON Lines format)
    try:
        with open(events_path) as f:
            content = f.read().strip()
            if content.startswith('['):
                # JSON array format
                events = json.loads(content)
            else:
                # JSON Lines format (one object per line)
                events = [json.loads(line) for line in content.split('\n') if line.strip()]
    except FileNotFoundError:
        print(f"Error reading events file: File not found: {events_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error reading events file: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Get video duration (required for smart boundaries)
    duration = get_video_duration(video_path)
    if not duration:
        print("Error: Could not determine video duration", file=sys.stderr)
        sys.exit(1)

    print(f"Video duration: {duration:.1f}s", file=sys.stderr)

    frame_count = len(events) * 3  # 3 frames per step
    print(f"Processing {len(events)} touches × 3 frames = {frame_count} frames", file=sys.stderr)

    import time
    start_time = time.time()

    updated = extract_frames_parallel(video_path, events, video_start, duration, output_dir)

    elapsed = time.time() - start_time
    print(f"Extraction complete in {elapsed:.1f}s ({frame_count/elapsed:.1f} frames/sec)", file=sys.stderr)

    # Output updated events
    print(json.dumps(updated, indent=2))
