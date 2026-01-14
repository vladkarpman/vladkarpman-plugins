#!/usr/bin/env python3
"""
Generate HTML report from JSON test results.

Usage:
    python3 generate-report.py <json_path> [--output <html_path>]

Examples:
    python3 generate-report.py tests/reports/2026-01-14_calc/report.json
    python3 generate-report.py report.json --output /tmp/report.html
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def get_template_path() -> Path:
    """Get path to HTML template."""
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if plugin_root:
        return Path(plugin_root) / "templates" / "report.html"
    # Fallback: relative to script
    return Path(__file__).parent.parent / "templates" / "report.html"


def load_template() -> str:
    """Load HTML template file."""
    template_path = get_template_path()
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text()


def load_json(json_path: Path) -> Dict[str, Any]:
    """Load JSON results file."""
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    with open(json_path) as f:
        return json.load(f)


def get_nested_value(data: Dict[str, Any], key: str) -> Any:
    """Get nested value from dict using dot notation (e.g., 'device.name')."""
    keys = key.split(".")
    value = data
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k, "")
        else:
            return ""
    return value


def format_value(value: Any) -> str:
    """Format value for HTML output."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def process_conditionals(template: str, data: Dict[str, Any]) -> str:
    """Process {{#if condition}}...{{/if}} blocks."""
    pattern = r"\{\{#if\s+(\w+(?:\.\w+)*)\}\}(.*?)\{\{/if\}\}"

    def replace_if(match):
        condition_key = match.group(1)
        content = match.group(2)
        value = get_nested_value(data, condition_key)
        # Truthy check: non-empty, non-zero, non-false
        if value and value != 0 and value != "0":
            return content
        return ""

    # Process nested conditionals from innermost to outermost
    while re.search(pattern, template, re.DOTALL):
        template = re.sub(pattern, replace_if, template, flags=re.DOTALL)

    return template


def process_loops(template: str, data: Dict[str, Any]) -> str:
    """Process {{#each items}}...{{/each}} blocks."""
    pattern = r"\{\{#each\s+(\w+(?:\.\w+)*)\}\}(.*?)\{\{/each\}\}"

    def replace_each(match):
        array_key = match.group(1)
        item_template = match.group(2)
        items = get_nested_value(data, array_key)

        if not isinstance(items, list):
            return ""

        result = []
        for index, item in enumerate(items):
            # Create context with item data and index
            item_context = item if isinstance(item, dict) else {"value": item}
            item_context["@index"] = index
            item_context["@first"] = index == 0
            item_context["@last"] = index == len(items) - 1

            # Process item template
            item_html = item_template

            # Process nested loops first
            item_html = process_loops(item_html, item_context)

            # Process conditionals
            item_html = process_conditionals(item_html, item_context)

            # Replace simple placeholders
            item_html = process_placeholders(item_html, item_context)

            result.append(item_html)

        return "".join(result)

    # Process from innermost to outermost
    while re.search(pattern, template, re.DOTALL):
        template = re.sub(pattern, replace_each, template, flags=re.DOTALL, count=1)

    return template


def process_placeholders(template: str, data: Dict[str, Any]) -> str:
    """Replace {{placeholder}} with values."""
    pattern = r"\{\{(\w+(?:\.\w+)*)\}\}"

    def replace_placeholder(match):
        key = match.group(1)
        value = get_nested_value(data, key)
        return format_value(value)

    return re.sub(pattern, replace_placeholder, template)


def get_status_class(status: str) -> str:
    """Get CSS class for status."""
    status_map = {
        "passed": "passed",
        "failed": "failed",
        "skipped": "skipped",
        "expected_failure": "failed",
    }
    return status_map.get(status, "")


def get_status_icon(status: str) -> str:
    """Get icon for status."""
    icon_map = {
        "passed": "✓",
        "failed": "✗",
        "skipped": "○",
    }
    return icon_map.get(status, "?")


def enrich_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add computed fields to data."""
    # Add formatted timestamp
    if "started_at" in data:
        try:
            dt = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
            data["timestamp"] = dt.strftime("%B %d, %Y at %I:%M %p")
        except (ValueError, AttributeError):
            data["timestamp"] = data.get("started_at", "")

    # Add test file name (without path)
    if "test_file" in data:
        data["testFile"] = Path(data["test_file"]).name
        data["testFilePath"] = data["test_file"]

    # Add duration formatting
    if "summary" in data and "duration_seconds" in data["summary"]:
        data["duration"] = f"{data['summary']['duration_seconds']:.1f}"

    # Enrich each test
    for test in data.get("tests", []):
        test["statusClass"] = get_status_class(test.get("status", ""))
        test["statusIcon"] = get_status_icon(test.get("status", ""))

        # Enrich each step
        for step in test.get("steps", []):
            step["statusClass"] = get_status_class(step.get("status", ""))
            step["statusIcon"] = get_status_icon(step.get("status", ""))
            # Format step number with zero padding
            if "number" in step:
                step["numberPadded"] = f"{step['number']:03d}"

    return data


def generate_html(template: str, data: Dict[str, Any]) -> str:
    """Generate HTML from template and data."""
    # Enrich data with computed fields
    data = enrich_data(data)

    # Process in order: loops, conditionals, placeholders
    html = process_loops(template, data)
    html = process_conditionals(html, data)
    html = process_placeholders(html, data)

    return html


def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from JSON")
    parser.add_argument("json_path", help="Path to JSON results file")
    parser.add_argument("--output", "-o", help="Output HTML path (default: report.html in same dir)")
    args = parser.parse_args()

    json_path = Path(args.json_path)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = json_path.parent / "report.html"

    try:
        # Load inputs
        template = load_template()
        data = load_json(json_path)

        # Generate HTML
        html = generate_html(template, data)

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)

        print(f"Report generated: {output_path}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
