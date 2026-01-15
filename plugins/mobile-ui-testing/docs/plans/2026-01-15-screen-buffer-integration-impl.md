# Screen-Buffer MCP Integration - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace deprecated device-manager-mcp with screen-buffer-mcp for screenshots, using mobile-mcp for all other device operations.

**Architecture:** screen-buffer handles only screenshots (its unique fast capability). mobile-mcp handles everything else (device list, screen size, tap, swipe, type, press, app lifecycle).

**Tech Stack:** Claude Code plugin (markdown commands), MCP servers (screen-buffer-mcp, mobile-mcp)

---

## Task 1: Update hooks/hooks.json

**Files:**
- Modify: `hooks/hooks.json`

**Step 1: Add screen-buffer auto-approval**

Add a PreToolUse hook for screen-buffer tools alongside the existing mobile-mcp hook:

```json
{
  "description": "Auto-approve mobile-mcp and screen-buffer tools",
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-end.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "mcp__mobile-mcp__*",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"decision\": \"approve\"}'"
          }
        ]
      },
      {
        "matcher": "mcp__screen-buffer__*",
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"decision\": \"approve\"}'"
          }
        ]
      }
    ]
  }
}
```

**Step 2: Commit**

```bash
git add hooks/hooks.json
git commit -m "feat(mobile-ui-testing): add screen-buffer auto-approval hook"
```

---

## Task 2: Update session-start.sh

**Files:**
- Modify: `hooks/session-start.sh`

**Step 1: Replace device-manager references with screen-buffer**

```bash
#!/usr/bin/env bash

# Mobile UI Testing Plugin - Session Start Hook
# - Auto-approves mobile-mcp and screen-buffer tools for seamless test execution
# - Checks for uv/uvx availability for screen-buffer-mcp

# Check if uvx is available
uv_status="not available"
if command -v uvx &> /dev/null; then
    uv_status="available (fast screenshots enabled)"
else
    echo "⚠️  screen-buffer-mcp requires 'uv' for fast screenshots." >&2
    echo "   Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    echo "   Then restart Claude Code." >&2
fi

cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Mobile UI Testing plugin is active.\n\n**Auto-approved tools:** All mobile-mcp and screen-buffer tools are pre-approved for this session. Tests will run without requiring manual approval for each action.\n\n**screen-buffer-mcp:** ${uv_status}\n\nAvailable commands:\n- \`/run-test <file>\` - Execute a YAML test file\n- \`/create-test <name>\` - Create a new test from template\n- \`/generate-test <description>\` - Generate test from natural language\n- \`/record-test <name>\` - Start recording user actions\n- \`/stop-recording\` - Stop recording and generate YAML\n\nFor help writing tests, just ask about YAML test syntax."
  }
}
EOF

exit 0
```

**Step 2: Commit**

```bash
git add hooks/session-start.sh
git commit -m "refactor(mobile-ui-testing): update session-start for screen-buffer"
```

---

## Task 3: Update record-test.md

**Files:**
- Modify: `commands/record-test.md`

**Step 1: Replace allowed-tools section**

Remove device-manager tools, keep only mobile-mcp:

```yaml
---
name: record-test
description: Start recording user actions to generate a YAML test
argument-hint: <test-name>
allowed-tools:
  - Read
  - Write
  - Glob
  - Bash
  - AskUserQuestion
  - mcp__mobile-mcp__mobile_list_available_devices
---
```

**Step 2: Update Step 4 tool reference**

Change from:
```markdown
**Tool:** `mcp__device-manager__device_list` (preferred) or `mcp__mobile-mcp__mobile_list_available_devices` (fallback)
```

To:
```markdown
**Tool:** `mcp__mobile-mcp__mobile_list_available_devices`
```

**Step 3: Commit**

```bash
git add commands/record-test.md
git commit -m "refactor(mobile-ui-testing): use mobile-mcp for device list in record-test"
```

---

## Task 4: Update run-test.md (allowed-tools)

**Files:**
- Modify: `commands/run-test.md` (lines 1-37)

**Step 1: Replace allowed-tools section**

Remove device-manager tools, add screen-buffer for screenshots:

```yaml
---
name: run-test
description: Execute a YAML mobile UI test file on a connected device
argument-hint: <test-path> [--no-report]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  # screen-buffer-mcp (fast screenshots only)
  - mcp__screen-buffer__device_screenshot
  # mobile-mcp (all device operations)
  - mcp__mobile-mcp__mobile_list_available_devices
  - mcp__mobile-mcp__mobile_get_screen_size
  - mcp__mobile-mcp__mobile_click_on_screen_at_coordinates
  - mcp__mobile-mcp__mobile_swipe_on_screen
  - mcp__mobile-mcp__mobile_type_keys
  - mcp__mobile-mcp__mobile_press_button
  - mcp__mobile-mcp__mobile_list_apps
  - mcp__mobile-mcp__mobile_launch_app
  - mcp__mobile-mcp__mobile_terminate_app
  - mcp__mobile-mcp__mobile_list_elements_on_screen
  - mcp__mobile-mcp__mobile_double_tap_on_screen
  - mcp__mobile-mcp__mobile_long_press_on_screen_at_coordinates
  - mcp__mobile-mcp__mobile_open_url
  - mcp__mobile-mcp__mobile_set_orientation
  - mcp__mobile-mcp__mobile_get_orientation
  - mcp__mobile-mcp__mobile_take_screenshot
  - mcp__mobile-mcp__mobile_save_screenshot
---
```

**Step 2: Commit (partial)**

```bash
git add commands/run-test.md
git commit -m "refactor(mobile-ui-testing): update run-test allowed-tools for screen-buffer"
```

---

## Task 5: Update run-test.md (Step 4 & 5)

**Files:**
- Modify: `commands/run-test.md` (lines 72-89)

**Step 1: Update Step 4 (Get Device)**

Change from:
```markdown
**Tool:** `mcp__device-manager__device_list` (preferred) or `mcp__mobile-mcp__mobile_list_available_devices` (fallback)
```

To:
```markdown
**Tool:** `mcp__mobile-mcp__mobile_list_available_devices`
```

**Step 2: Update Step 5 (Get Screen Size)**

Change from:
```markdown
**Tool:** `mcp__device-manager__device_screen_size` (preferred) or `mcp__mobile-mcp__mobile_get_screen_size` (fallback)
```

To:
```markdown
**Tool:** `mcp__mobile-mcp__mobile_get_screen_size`
```

**Step 3: Commit**

```bash
git add commands/run-test.md
git commit -m "refactor(mobile-ui-testing): use mobile-mcp for device list and screen size"
```

---

## Task 6: Update run-test.md (Screenshot capture)

**Files:**
- Modify: `commands/run-test.md` (line 179)

**Step 1: Update screenshot tool reference**

Change from:
```markdown
**Tool:** `mcp__device-manager__device_screenshot` (fast, preferred) or `mcp__mobile-mcp__mobile_save_screenshot` (fallback) with path={SCREENSHOT_PATH}
```

To:
```markdown
**Tool:** `mcp__screen-buffer__device_screenshot` with device={DEVICE_ID}

Save result to {SCREENSHOT_PATH} using `Write` tool (screen-buffer returns base64 PNG).
```

**Step 2: Commit**

```bash
git add commands/run-test.md
git commit -m "refactor(mobile-ui-testing): use screen-buffer for screenshot capture"
```

---

## Task 7: Update run-test.md (Action Mapping section)

**Files:**
- Modify: `commands/run-test.md` (lines 279-335)

**Step 1: Rewrite Tool Priority section**

Replace:
```markdown
**Tool Priority:** ALWAYS try device-manager tools first (fast, ~50ms). Only fall back to mobile-mcp if device-manager fails or is unavailable.

**Device-Manager Tools (preferred):**
- `mcp__device-manager__device_tap` - Fast tap (~50ms)
- `mcp__device-manager__device_swipe` - Fast swipe
- `mcp__device-manager__device_type` - Fast text input
- `mcp__device-manager__device_screenshot` - Fast screenshot (~50ms)
- `mcp__device-manager__device_press_key` - Key events (BACK, HOME, ENTER)
- `mcp__device-manager__device_screen_size` - Get screen dimensions

**Mobile-MCP Tools (for features device-manager doesn't have):**
```

With:
```markdown
**Tool Architecture:**

- **screen-buffer-mcp:** Screenshots only (fast ~50ms via scrcpy buffer)
- **mobile-mcp:** All other device operations

**Screen-Buffer Tools:**
- `mcp__screen-buffer__device_screenshot` - Fast screenshot (~50ms)

**Mobile-MCP Tools:**
```

**Step 2: Update Tap Actions table**

Replace all `mcp__device-manager__device_tap` with `mcp__mobile-mcp__mobile_click_on_screen_at_coordinates`.

**Step 3: Update Other Actions table**

| Old Tool | New Tool |
|----------|----------|
| `mcp__device-manager__device_tap` | `mcp__mobile-mcp__mobile_click_on_screen_at_coordinates` |
| `mcp__device-manager__device_type` | `mcp__mobile-mcp__mobile_type_keys` |
| `mcp__device-manager__device_press_key` | `mcp__mobile-mcp__mobile_press_button` |
| `mcp__device-manager__device_swipe` | `mcp__mobile-mcp__mobile_swipe_on_screen` |
| `mcp__device-manager__device_screenshot` | `mcp__screen-buffer__device_screenshot` |

**Step 4: Commit**

```bash
git add commands/run-test.md
git commit -m "refactor(mobile-ui-testing): rewrite action mapping for screen-buffer architecture"
```

---

## Task 8: Update run-test.md (verify_screen and conditionals)

**Files:**
- Modify: `commands/run-test.md` (lines 346, 378)

**Step 1: Update verify_screen Implementation**

Change from:
```markdown
1. **Tool:** `mcp__device-manager__device_screenshot` (fast, ~50ms) or `mcp__mobile-mcp__mobile_take_screenshot` (fallback)
```

To:
```markdown
1. **Tool:** `mcp__screen-buffer__device_screenshot` (fast, ~50ms)
```

**Step 2: Update if_screen conditional**

Change from:
```markdown
- **Tool:** `mcp__device-manager__device_screenshot` (preferred) or `mcp__mobile-mcp__mobile_take_screenshot` (fallback)
```

To:
```markdown
- **Tool:** `mcp__screen-buffer__device_screenshot`
```

**Step 3: Commit**

```bash
git add commands/run-test.md
git commit -m "refactor(mobile-ui-testing): use screen-buffer for verify_screen and conditionals"
```

---

## Task 9: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Replace device-manager-mcp section with screen-buffer-mcp**

Find and replace the entire "device-manager-mcp (Recommended)" section (around lines 23-40) with:

```markdown
### screen-buffer-mcp (Fast Screenshots)

For high-performance screenshots (~50ms vs ~500ms with mobile-mcp):

```bash
# Install uv (Python package runner, like npx for Python)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart Claude Code after installation
```

The plugin uses screen-buffer-mcp via `uvx` for fast screenshots. Falls back to mobile-mcp if unavailable.

**Benefits of screen-buffer-mcp:**
- **~50ms** screenshot latency (vs 500-2000ms with mobile-mcp)
- **Frame buffer** - access previous frames for analysis
- **No bundled dependencies** - runs via uvx on demand
```

**Step 2: Update MCP Server Architecture section**

Replace the device-manager-mcp subsection with screen-buffer-mcp:

```markdown
### screen-buffer-mcp (Fast Screenshots)

High-performance screenshots via scrcpy buffer. Runs via `uvx` (requires `uv` installed).

**Tools provided:**
| Tool | Description |
|------|-------------|
| `device_screenshot` | Take screenshot (~50ms) |
| `device_get_frame` | Get frame from buffer at offset |
| `device_list` | List connected devices |
| `device_screen_size` | Get screen dimensions |
| `device_backend_status` | Check scrcpy connection status |

**Configuration** (`.mcp.json`):
```json
{
  "screen-buffer": {
    "command": "uvx",
    "args": ["screen-buffer-mcp"]
  }
}
```

### mobile-mcp (Device Operations)

Standard device interaction via adb. Runs via `npx`.

**Used for:**
- `mobile_list_available_devices` - Device discovery
- `mobile_get_screen_size` - Screen dimensions
- `mobile_click_on_screen_at_coordinates` - Tap
- `mobile_swipe_on_screen` - Swipe
- `mobile_type_keys` - Text input
- `mobile_press_button` - Key events (BACK, HOME, ENTER)
- `mobile_list_elements_on_screen` - UI element discovery
- `mobile_launch_app` / `mobile_terminate_app` - App lifecycle
- `mobile_set_orientation` - Screen orientation
```

**Step 3: Update Key processing flow diagram**

Change:
```
User Action → Command (markdown) → device-manager-mcp tool (fast) → Device
                                 → mobile-mcp tool (fallback)      → Device
```

To:
```
User Action → Command (markdown) → screen-buffer tool (screenshots) → Device
                                 → mobile-mcp tool (all other ops)  → Device
```

**Step 4: Update Troubleshooting section**

Replace device-manager references:
- Change "device-manager" to "screen-buffer" in uvx check instructions
- Update error messages

**Step 5: Update design docs reference**

Change:
```markdown
- **remove-scrcpy-helper-design.md** - Migration from scrcpy-helper to device-manager-mcp
```

To:
```markdown
- **screen-buffer-integration.md** - Migration to screen-buffer-mcp for fast screenshots
```

**Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(mobile-ui-testing): update CLAUDE.md for screen-buffer architecture"
```

---

## Task 10: Verification

**Step 1: Check for remaining device-manager references**

```bash
grep -r "device-manager" --include="*.md" --include="*.json" --include="*.sh" .
```

Expected: No results (or only in design docs as historical reference)

**Step 2: Test with /run-test**

Create a minimal test file if needed, or use existing test:

```yaml
# tests/verify-integration/test.yaml
config:
  app: com.google.android.calculator

tests:
  - name: Basic screenshot test
    steps:
      - launch_app
      - wait: 2s
      - verify_screen: "Calculator app is open"
      - tap: "5"
      - verify_screen: "Number 5 is displayed"
```

Run: `/run-test tests/verify-integration/`

**Step 3: Verify screen-buffer is used**

Check that `mcp__screen-buffer__device_screenshot` is called for screenshots.

**Step 4: Final commit**

```bash
git add .
git commit -m "test(mobile-ui-testing): verify screen-buffer integration"
```

---

## Summary

| Task | File | Change |
|------|------|--------|
| 1 | hooks/hooks.json | Add screen-buffer auto-approval |
| 2 | hooks/session-start.sh | Update status message |
| 3 | commands/record-test.md | Use mobile-mcp for device list |
| 4-8 | commands/run-test.md | Full refactor to new architecture |
| 9 | CLAUDE.md | Documentation update |
| 10 | - | Verification |
