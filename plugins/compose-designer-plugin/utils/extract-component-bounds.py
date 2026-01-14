#!/usr/bin/env python3
"""
Extract component bounds from mobile-mcp view hierarchy JSON.

Usage:
    python3 extract-component-bounds.py <hierarchy_json> <test_tag>

Output:
    JSON with bounds: {"x": 0, "y": 100, "width": 1080, "height": 500, "found": true}

If not found:
    {"found": false, "error": "Element with tag \"X\" not found"}
    Exit code: 1
"""

import sys
import json
import argparse
from pathlib import Path


def find_element_by_tag(elements, test_tag):
    """
    Recursively search for element matching the test tag.

    Searches by:
    - testTag field (exact match)
    - resource-id ending with the test tag
    - content-desc matching the test tag

    Args:
        elements: List of elements or single element dict
        test_tag: Tag to search for

    Returns:
        Element dict if found, None otherwise
    """
    if elements is None:
        return None

    # Handle single element (dict)
    if isinstance(elements, dict):
        elements = [elements]

    # Handle non-list types
    if not isinstance(elements, list):
        return None

    for element in elements:
        if not isinstance(element, dict):
            continue

        # Check testTag field (exact match)
        if element.get("testTag") == test_tag:
            return element

        # Check resource-id ending with test tag
        resource_id = element.get("resource-id", "")
        if resource_id and resource_id.endswith(test_tag):
            return element

        # Check content-desc matching test tag
        content_desc = element.get("content-desc", "")
        if content_desc == test_tag:
            return element

        # Check accessibilityLabel (iOS equivalent)
        accessibility_label = element.get("accessibilityLabel", "")
        if accessibility_label == test_tag:
            return element

        # Check text field as fallback
        text = element.get("text", "")
        if text == test_tag:
            return element

        # Recurse into children
        children = element.get("children") or element.get("elements")
        if children:
            result = find_element_by_tag(children, test_tag)
            if result:
                return result

    return None


def extract_bounds(element):
    """
    Extract bounds from element.

    Handles different formats:
    - {"bounds": {"x": 0, "y": 100, "width": 1080, "height": 500}}
    - {"x": 0, "y": 100, "width": 1080, "height": 500}
    - {"bounds": "[0,100][1080,600]"} (Android format)
    - {"frame": {"x": 0, "y": 100, "width": 1080, "height": 500}} (iOS format)

    Args:
        element: Element dict

    Returns:
        Dict with x, y, width, height or None if not found
    """
    # Check for bounds object
    bounds = element.get("bounds")
    if isinstance(bounds, dict):
        if all(k in bounds for k in ["x", "y", "width", "height"]):
            return {
                "x": int(bounds["x"]),
                "y": int(bounds["y"]),
                "width": int(bounds["width"]),
                "height": int(bounds["height"])
            }

    # Check for direct x, y, width, height fields
    if all(k in element for k in ["x", "y", "width", "height"]):
        return {
            "x": int(element["x"]),
            "y": int(element["y"]),
            "width": int(element["width"]),
            "height": int(element["height"])
        }

    # Check for frame object (iOS format)
    frame = element.get("frame")
    if isinstance(frame, dict):
        if all(k in frame for k in ["x", "y", "width", "height"]):
            return {
                "x": int(frame["x"]),
                "y": int(frame["y"]),
                "width": int(frame["width"]),
                "height": int(frame["height"])
            }

    # Check for Android bounds string format: "[left,top][right,bottom]"
    if isinstance(bounds, str):
        try:
            # Parse format like "[0,100][1080,600]"
            parts = bounds.replace("][", ",").strip("[]").split(",")
            if len(parts) == 4:
                left, top, right, bottom = map(int, parts)
                return {
                    "x": left,
                    "y": top,
                    "width": right - left,
                    "height": bottom - top
                }
        except (ValueError, AttributeError):
            pass

    # Check for rect field (alternative naming)
    rect = element.get("rect")
    if isinstance(rect, dict):
        if all(k in rect for k in ["x", "y", "width", "height"]):
            return {
                "x": int(rect["x"]),
                "y": int(rect["y"]),
                "width": int(rect["width"]),
                "height": int(rect["height"])
            }

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract component bounds from mobile-mcp view hierarchy JSON",
        epilog="Example: python3 extract-component-bounds.py hierarchy.json TestCard"
    )
    parser.add_argument("hierarchy_json", help="Path to view hierarchy JSON file")
    parser.add_argument("test_tag", help="Test tag to search for")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Always output as JSON (default behavior)"
    )

    args = parser.parse_args()

    # Validate file exists
    hierarchy_path = Path(args.hierarchy_json)
    if not hierarchy_path.exists():
        result = {
            "found": False,
            "error": f"File not found: {args.hierarchy_json}"
        }
        print(json.dumps(result))
        sys.exit(1)

    # Load JSON
    try:
        with open(hierarchy_path, "r", encoding="utf-8") as f:
            hierarchy = json.load(f)
    except json.JSONDecodeError as e:
        result = {
            "found": False,
            "error": f"Invalid JSON: {e}"
        }
        print(json.dumps(result))
        sys.exit(1)
    except IOError as e:
        result = {
            "found": False,
            "error": f"Could not read file: {e}"
        }
        print(json.dumps(result))
        sys.exit(1)

    # Search for element
    element = find_element_by_tag(hierarchy, args.test_tag)

    if element is None:
        result = {
            "found": False,
            "error": f'Element with tag "{args.test_tag}" not found'
        }
        print(json.dumps(result))
        sys.exit(1)

    # Extract bounds
    bounds = extract_bounds(element)

    if bounds is None:
        result = {
            "found": False,
            "error": f'Element found but bounds not extractable for tag "{args.test_tag}"'
        }
        print(json.dumps(result))
        sys.exit(1)

    # Success
    result = {
        "x": bounds["x"],
        "y": bounds["y"],
        "width": bounds["width"],
        "height": bounds["height"],
        "found": True
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
