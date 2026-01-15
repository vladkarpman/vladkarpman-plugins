#!/usr/bin/env python3
"""
Extract frames from video at specific timestamps using ffmpeg.
Extracts multiple frames per touch: before, exact, and after.
Uses parallel processing for speed.
"""

import subprocess
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Frame extraction offsets in milliseconds
FRAME_OFFSETS = {
    "before_1": -300,  # 300ms before tap
    "before_2": -200,  # 200ms before tap
    "before_3": -100,  # 100ms before tap
    "exact": 0,        # At tap moment
    "after_1": 100,    # 100ms after tap
    "after_2": 200,    # 200ms after tap
    "after_3": 300,    # 300ms after tap
}

# Number of parallel ffmpeg processes
MAX_WORKERS = min(32, (os.cpu_count() or 4) * 4)


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


def build_extraction_tasks(
    video_path: str,
    touch_events: List[Dict[str, Any]],
    video_start_time: float,
    output_dir: Path
) -> List[Tuple[str, float, str, int, str]]:
    """
    Build list of extraction tasks.

    Returns list of (video_path, timestamp, output_path, step_num, frame_type).
    """
    tasks = []

    for event in touch_events:
        if "index" not in event or "timestamp" not in event:
            continue

        touch_time = event["timestamp"]
        step_num = event["index"]
        step_str = f"{step_num:03d}"

        # Calculate base position in video
        video_position = touch_time - video_start_time

        for frame_type, offset_ms in FRAME_OFFSETS.items():
            frame_position = video_position + (offset_ms / 1000)
            frame_filename = f"step_{step_str}_{frame_type}.png"
            frame_path = str(output_dir / frame_filename)

            tasks.append((video_path, frame_position, frame_path, step_num, frame_type))

    return tasks


def extract_frames_parallel(
    video_path: str,
    touch_events: List[Dict[str, Any]],
    video_start_time: float,
    output_dir: str
) -> List[Dict[str, Any]]:
    """
    Extract frames for all touch events in parallel.

    Returns list of touch events with frame paths added.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build all extraction tasks
    tasks = build_extraction_tasks(video_path, touch_events, video_start_time, output_path)

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
        # Backward compatibility - set screenshot to before_3
        event["screenshot"] = frames.get("before_3")

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

    # Load and validate events file
    try:
        with open(events_path) as f:
            events = json.load(f)
    except FileNotFoundError:
        print(f"Error reading events file: File not found: {events_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error reading events file: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Get video duration for info
    duration = get_video_duration(video_path)
    if duration:
        print(f"Video duration: {duration:.1f}s", file=sys.stderr)

    frame_count = len(events) * len(FRAME_OFFSETS)
    print(f"Processing {len(events)} touches × {len(FRAME_OFFSETS)} frames = {frame_count} frames", file=sys.stderr)

    import time
    start_time = time.time()

    updated = extract_frames_parallel(video_path, events, video_start, output_dir)

    elapsed = time.time() - start_time
    print(f"Extraction complete in {elapsed:.1f}s ({frame_count/elapsed:.1f} frames/sec)", file=sys.stderr)

    # Output updated events
    print(json.dumps(updated, indent=2))
