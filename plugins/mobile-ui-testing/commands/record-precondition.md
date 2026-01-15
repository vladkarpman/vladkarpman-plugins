---
name: record-precondition
description: Start recording a reusable precondition flow
argument-hint: <precondition-name>
allowed-tools:
  - Read
  - Write
  - Glob
  - Bash
  - AskUserQuestion
  - mcp__mobile-mcp__mobile_list_available_devices
  - mcp__screen-buffer__device_start_recording
---

# Record Precondition - Start Recording State Setup Flow

Start recording mode to capture a reusable precondition flow that establishes a specific app state.

## Execution Steps

Execute each step in order. Do not skip steps. Use the exact tools specified.

### Step 1: Get Precondition Name

**If argument provided:** Use it as `{PRECONDITION_NAME}`.

**If no argument:** Use `AskUserQuestion` tool:
```
Question: "What would you like to name this precondition? (e.g., logged_in, premium_user)"
```

Store the result as `{PRECONDITION_NAME}`.

**Validate name:** Must be lowercase with underscores only (a-z, 0-9, _).

### Step 2: Get Precondition Description

Use `AskUserQuestion`:
```
Question: "Brief description of this precondition (e.g., 'User logged in with test account')"
```

Store as `{PRECONDITION_DESCRIPTION}`.

### Step 3: Check ffmpeg

**Tool:** `Bash`
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/check-ffmpeg.sh"
```

**If output contains "OK":** Continue.

**If output contains "not found":** Stop and show:
```
ffmpeg is required for recording.

Install with:
  macOS:   brew install ffmpeg
  Ubuntu:  sudo apt install ffmpeg
  Windows: choco install ffmpeg
```

### Step 4: Detect App Package

**Tool:** `Glob` with pattern `tests/*/test.yaml`

**If files found:** Use `Bash` to extract package:
```bash
grep -h "app:" tests/*/test.yaml | head -1 | sed 's/.*app: *//'
```
Store result as `{APP_PACKAGE}`.

**If no files or grep fails:** Use `AskUserQuestion`:
```
Question: "What is your app package name? (e.g., com.example.app)"
```
Store result as `{APP_PACKAGE}`.

### Step 5: Get Device

**Tool:** `mcp__mobile-mcp__mobile_list_available_devices`

**If 0 devices:** Stop and show:
```
No device found.

Ensure your device is connected:
  Android: adb devices
  iOS: xcrun simctl list devices | grep Booted
```

**If 1 device:** Use it. Store `id` as `{DEVICE_ID}`, `name` as `{DEVICE_NAME}`.

**If multiple devices:** Use `AskUserQuestion` to let user select.

### Step 6: Create Folders

**Tool:** `Bash`
```bash
mkdir -p tests/preconditions/{PRECONDITION_NAME}/recording/screenshots
mkdir -p .claude
```

### Step 7: Get Video Start Timestamp

**Tool:** `Bash`
```bash
python3 -c "import time; print(time.time())"
```

Store the output number as `{VIDEO_START_TIME}` (e.g., `1768233811.7967029`).

### Step 8: Create Initial Recording State

**Tool:** `Bash` (use Bash because file doesn't exist yet)
```bash
cat > .claude/recording-state.json << 'EOF'
{
  "type": "precondition",
  "preconditionName": "{PRECONDITION_NAME}",
  "preconditionDescription": "{PRECONDITION_DESCRIPTION}",
  "preconditionFolder": "tests/preconditions/{PRECONDITION_NAME}",
  "appPackage": "{APP_PACKAGE}",
  "device": "{DEVICE_ID}",
  "startTime": "{CURRENT_ISO_TIMESTAMP}",
  "videoStartTime": {VIDEO_START_TIME},
  "status": "recording",
  "touchPid": null
}
EOF
```

Replace placeholders with actual values.

### Step 9: Start Video Recording

**Tool:** `mcp__screen-buffer__device_start_recording`
```json
{
  "output_path": "tests/preconditions/{PRECONDITION_NAME}/recording/recording.mp4"
}
```

Store the response confirmation. Recording is now active.

### Step 10: Start Touch Monitor

**Tool:** `Bash` with `run_in_background: true`
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/monitor-touches.py" {DEVICE_ID} tests/preconditions/{PRECONDITION_NAME}/recording &
echo "TOUCH_PID=$!"
```

**Read the background task output file** to get `TOUCH_PID=XXXXX`.
Store the number as `{TOUCH_PID}`.

### Step 11: Update Recording State with PID

**Tool:** `Read` then `Write` on `.claude/recording-state.json`

Update the file to set:
- `"touchPid": {TOUCH_PID}`

### Step 12: Output Success Message

Output this message to the user (replace placeholders):

```
Recording Precondition: {PRECONDITION_NAME}
══════════════════════════════════════════════════════════

Description: {PRECONDITION_DESCRIPTION}
Device: {DEVICE_NAME} ({DEVICE_ID})
App: {APP_PACKAGE}
Saving to: tests/preconditions/{PRECONDITION_NAME}/

RECORDING ACTIVE
────────────────
Every tap, swipe, and long-press is being captured.
Perform the steps to reach your desired app state.

When done, say "stop" or use /stop-recording

══════════════════════════════════════════════════════════
```

### Step 13: Wait for Stop Command

When user says "stop", "done", or uses `/stop-recording`:
- Invoke the `stop-recording` command

## Error Handling

| Error | Action |
|-------|--------|
| ffmpeg not found | Show install instructions, stop |
| No device found | Show connection instructions, stop |
| Script file missing | Show: "Plugin not installed correctly. Re-install with: claude plugin install mobile-ui-testing" |
| Device disconnects | Stop recording, notify user |
| Invalid name format | Ask user to provide valid name (lowercase, underscores only) |

## Notes

- Touch events are captured in real-time to `touch_events.json`
- Stopping the recording properly is critical - see `/stop-recording`
- Preconditions are saved to `tests/preconditions/` to separate them from regular tests
- The `type: "precondition"` field in recording state tells `/stop-recording` to generate a precondition file
