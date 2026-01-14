#!/usr/bin/env python3
"""
Query screenshot buffer for verification candidates.

Usage:
    python3 verify-from-buffer.py --buffer /tmp/buffer --since TIMESTAMP [--recency 500]

Returns JSON with candidate screenshots for AI verification.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any


def load_manifest(buffer_dir: Path) -> Dict[str, Any]:
    """Load manifest.json from buffer directory."""
    manifest_path = buffer_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path) as f:
        return json.load(f)


def get_screenshots_since(manifest: Dict[str, Any], since_timestamp: float) -> List[Dict[str, Any]]:
    """Get all screenshots captured after the given timestamp."""
    return [
        s for s in manifest["screenshots"]
        if s["timestamp"] >= since_timestamp
    ]


def filter_candidates(
    screenshots: List[Dict[str, Any]],
    recency_threshold_ms: float = 500
) -> List[Dict[str, Any]]:
    """
    Filter to verification candidates:
    - Within recency threshold of now, OR
    - Most recent screenshot
    """
    if not screenshots:
        return []

    now = time.time()
    most_recent = screenshots[-1]

    candidates = []
    for s in screenshots:
        age_ms = (now - s["timestamp"]) * 1000
        is_recent = age_ms <= recency_threshold_ms
        is_most_recent = s == most_recent

        if is_recent or is_most_recent:
            candidates.append({
                **s,
                "age_ms": age_ms,
                "is_most_recent": is_most_recent
            })

    return candidates


def main():
    parser = argparse.ArgumentParser(description="Query buffer for verification")
    parser.add_argument("--buffer", required=True, help="Buffer directory")
    parser.add_argument("--since", required=True, type=float, help="Action timestamp")
    parser.add_argument("--recency", type=int, default=500, help="Recency threshold in ms")
    args = parser.parse_args()

    buffer_dir = Path(args.buffer)

    try:
        manifest = load_manifest(buffer_dir)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e), "candidates": []}))
        sys.exit(1)

    # Get screenshots since action
    screenshots = get_screenshots_since(manifest, args.since)

    # Filter to candidates
    candidates = filter_candidates(screenshots, args.recency)

    # Build full paths
    for c in candidates:
        c["path"] = str(buffer_dir / c["file"])

    result = {
        "buffer_dir": str(buffer_dir),
        "since": args.since,
        "total_since_action": len(screenshots),
        "candidates": candidates,
        "recommended": candidates[-1]["path"] if candidates else None
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
