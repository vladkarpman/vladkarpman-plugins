#!/usr/bin/env python3
"""
Crop image to specified bounds.

Usage:
    python3 crop-image.py <input_image> <output_image> <x> <y> <width> <height>

Example:
    python3 crop-image.py screenshot.png cropped.png 0 100 1080 500

Requirements:
    pip3 install pillow
"""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as e:
    print(f"Error: Required package not installed: {e}", file=sys.stderr)
    print("Install with: pip3 install pillow", file=sys.stderr)
    sys.exit(1)


def crop_image(input_path, output_path, x, y, width, height):
    """
    Crop an image to specified bounds.

    Args:
        input_path: Path to input image
        output_path: Path to save cropped image
        x: Left coordinate of crop area
        y: Top coordinate of crop area
        width: Width of crop area
        height: Height of crop area

    Returns:
        tuple: (cropped_width, cropped_height)
    """
    # Open the image
    img = Image.open(input_path)
    img_width, img_height = img.size

    # Validate bounds are non-negative
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError(f"Invalid bounds: x={x}, y={y}, width={width}, height={height}. "
                         "All values must be non-negative and width/height must be positive.")

    # Validate bounds don't exceed image dimensions
    if x + width > img_width:
        raise ValueError(f"Crop area exceeds image width: x({x}) + width({width}) = {x + width} > {img_width}")

    if y + height > img_height:
        raise ValueError(f"Crop area exceeds image height: y({y}) + height({height}) = {y + height} > {img_height}")

    # Crop the image: PIL uses (left, top, right, bottom)
    crop_box = (x, y, x + width, y + height)
    cropped = img.crop(crop_box)

    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save the cropped image
    cropped.save(output_path)

    return width, height


def main():
    # Check argument count
    if len(sys.argv) != 7:
        print("Usage: crop-image.py <input_image> <output_image> <x> <y> <width> <height>", file=sys.stderr)
        print("Example: crop-image.py screenshot.png cropped.png 0 100 1080 500", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # Parse numeric arguments
    try:
        x = int(sys.argv[3])
        y = int(sys.argv[4])
        width = int(sys.argv[5])
        height = int(sys.argv[6])
    except ValueError as e:
        print(f"Error: Invalid numeric argument: {e}", file=sys.stderr)
        print("x, y, width, and height must be integers", file=sys.stderr)
        sys.exit(1)

    # Validate input file exists
    if not Path(input_path).exists():
        print(f"Error: Input image not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Crop the image
    try:
        crop_image(input_path, output_path, x, y, width, height)
        print(f"Cropped to {width}x{height} at ({x}, {y})")
        sys.exit(0)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: Cannot write output file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to crop image: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
