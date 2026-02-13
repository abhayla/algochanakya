#!/usr/bin/env python3
"""
PostToolUse hook: Auto-resize screenshots > 1800px using PIL/Pillow.

Triggers on:
- mcp__playwright__browser_take_screenshot
- Bash commands that create screenshots

Exit codes:
    0 = success (non-blocking)
    1 = warning (resize failed, non-blocking)
"""

import sys
import re
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import (
    parse_hook_input,
    exit_with_code
)


def resize_screenshot(file_path: str, max_width: int = 1800) -> bool:
    """
    Resize screenshot if width > max_width.

    Args:
        file_path: Path to screenshot file
        max_width: Maximum width in pixels

    Returns:
        True if resized, False if no resize needed or error
    """
    try:
        from PIL import Image

        img_path = Path(file_path)

        if not img_path.exists():
            return False

        # Open image
        img = Image.open(img_path)
        width, height = img.size

        if width <= max_width:
            # No resize needed
            return False

        # Calculate new dimensions (preserve aspect ratio)
        new_width = max_width
        new_height = int(height * (max_width / width))

        # Resize
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Save (overwrite original)
        resized.save(img_path, optimize=True, quality=85)

        print(f"🖼️  Resized {img_path.name}: {width}x{height} → {new_width}x{new_height}", file=sys.stderr)

        return True

    except ImportError:
        print("⚠️  Warning: PIL/Pillow not installed, cannot resize screenshots", file=sys.stderr)
        return False

    except Exception as e:
        print(f"⚠️  Warning: Failed to resize {file_path}: {str(e)}", file=sys.stderr)
        return False


def extract_screenshot_path(tool_input: dict, tool_output: str, tool_name: str) -> str:
    """
    Extract screenshot file path from tool input/output.

    Args:
        tool_input: Tool input dict
        tool_output: Tool output string
        tool_name: Tool name

    Returns:
        Screenshot file path or empty string
    """
    if tool_name == 'mcp__playwright__browser_take_screenshot':
        # Path in filename parameter
        return tool_input.get('filename', '')

    elif tool_name == 'Bash':
        # Try to extract from command
        command = tool_input.get('command', '')

        # Pattern 1: playwright command with --screenshot flag
        match = re.search(r'--screenshot[=\s]+([^\s]+\.(?:png|jpg|jpeg))', command)
        if match:
            return match.group(1)

        # Pattern 2: Saving to file via output redirection
        # e.g., playwright codegen --screenshot > screenshot.png
        match = re.search(r'>\s*([^\s]+\.(?:png|jpg|jpeg))', command)
        if match:
            return match.group(1)

        # Pattern 3: Check output for "Screenshot saved to: {path}"
        match = re.search(r'Screenshot saved to:\s*([^\s]+\.(?:png|jpg|jpeg))', tool_output)
        if match:
            return match.group(1)

    return ''


def main():
    """Main hook entry point."""
    hook_data = parse_hook_input()
    if not hook_data:
        exit_with_code(0)

    tool_name = hook_data.get('tool_name', '')
    tool_input = hook_data.get('tool_input', {})
    tool_output = hook_data.get('tool_output', '')

    # Only process screenshot tools
    if tool_name not in ['mcp__playwright__browser_take_screenshot', 'Bash']:
        exit_with_code(0)

    # Extract screenshot path
    screenshot_path = extract_screenshot_path(tool_input, tool_output, tool_name)

    if not screenshot_path:
        # No screenshot detected
        exit_with_code(0)

    # Resolve to absolute path if relative
    path = Path(screenshot_path)
    if not path.is_absolute():
        # Try project root
        from hook_utils import PROJECT_ROOT
        path = PROJECT_ROOT / screenshot_path

    # Resize if needed
    resized = resize_screenshot(str(path))

    if not resized:
        # No resize needed or failed (non-blocking)
        exit_with_code(0)

    # Success
    exit_with_code(0)


if __name__ == '__main__':
    main()
