# Screen Buffer Recording Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace adb screenrecord with screen-buffer-mcp for video recording and screenshots.

**Architecture:** Use screen-buffer-mcp's `device_start_recording`/`device_stop_recording` for video, `device_screenshot` for screenshots. Remove bash wrapper and adb file pulling.

**Tech Stack:** screen-buffer-mcp (scrcpy-based), mobile-mcp (device interactions), ffmpeg (frame extraction)

---

## Task 1: Update record-test.md

**Files:**
- Modify: `commands/record-test.md`

**Step 1: Add screen-buffer tool to allowed-tools**

In the YAML frontmatter (lines 1-12), add after line 11:

```yaml
  - mcp__screen-buffer__device_start_recording
```

**Step 2: Verify change**

Run: `head -15 commands/record-test.md`
Expected: `mcp__screen-buffer__device_start_recording` in allowed-tools list

**Step 3: Replace Step 8 (video recording)**

Replace lines 123-133 (Step 8: Start Video Recording) with:

```markdown
### Step 8: Start Video Recording

**Tool:** `mcp__screen-buffer__device_start_recording`
```json
{
  "output_path": "tests/{TEST_NAME}/recording/recording.mp4"
}
```

Store the response confirmation. Recording is now active.
```

**Step 4: Update Step 7 (recording state) - remove videoPid**

Replace lines 106-119 (Step 7: Create Initial Recording State) with:

```markdown
### Step 7: Create Initial Recording State

**Tool:** `Bash` (use Bash because file doesn't exist yet)
```bash
cat > .claude/recording-state.json << 'EOF'
{
  "testName": "{TEST_NAME}",
  "testFolder": "tests/{TEST_NAME}",
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
```

**Step 5: Update Step 9 - renumber and simplify**

The old Step 9 (Start Touch Monitor) becomes the new Step 9, but we no longer read VIDEO_PID.

Replace lines 134-144 with:

```markdown
### Step 9: Start Touch Monitor

**Tool:** `Bash` with `run_in_background: true`
```bash
python3 ./scripts/monitor-touches.py {DEVICE_ID} tests/{TEST_NAME}/recording &
echo "TOUCH_PID=$!"
```

**Read the background task output file** to get `TOUCH_PID=XXXXX`.
Store the number as `{TOUCH_PID}`.
```

**Step 6: Update Step 10 - remove videoPid update**

Replace lines 145-152 (Step 10: Update Recording State with PIDs) with:

```markdown
### Step 10: Update Recording State with PID

**Tool:** `Read` then `Write` on `.claude/recording-state.json`

Update the file to set:
- `"touchPid": {TOUCH_PID}`
```

**Step 7: Remove 3-minute limit note from success message**

In Step 11 output (around line 174), delete the line:
```
Note: Video recording has a 3-minute limit.
```

**Step 8: Remove Notes section about 3-minute limit**

Delete lines 195-197 (Notes section at end of file):
```markdown
## Notes

- Video recording has a 3-minute limit (Android screenrecord limitation)
```

Keep the other notes about touch events and stopping.

**Step 9: Commit**

```bash
git add commands/record-test.md
git commit -m "feat(mobile-ui-testing): use screen-buffer-mcp for recording

Replace adb screenrecord with device_start_recording from screen-buffer-mcp.
Removes 3-minute recording limit."
```

---

## Task 2: Update stop-recording.md

**Files:**
- Modify: `commands/stop-recording.md`

**Step 1: Add screen-buffer tool to allowed-tools**

In the YAML frontmatter (lines 1-11), add after line 9:

```yaml
  - mcp__screen-buffer__device_stop_recording
```

**Step 2: Verify change**

Run: `head -15 commands/stop-recording.md`
Expected: `mcp__screen-buffer__device_stop_recording` in allowed-tools list

**Step 3: Update Step 1 - remove videoPid extraction**

In Step 1 (lines 21-50), remove line 39:
```markdown
- `{VIDEO_PID}` = videoPid
```

**Step 4: Replace Step 2 (stop screenrecord)**

Replace lines 52-60 (Step 2: Stop Screenrecord on Device) with:

```markdown
### Step 2: Stop Video Recording

**Tool:** `mcp__screen-buffer__device_stop_recording`
```json
{}
```

This stops the recording and finalizes the video file.
The response includes duration and file size.
Video is saved directly to: `{TEST_FOLDER}/recording/recording.mp4`
```

**Step 5: Delete Step 3 (wait for video script)**

Delete lines 62-74 (Step 3: Wait for Video Script to Complete) entirely.

This step is no longer needed - screen-buffer-mcp handles everything synchronously.

**Step 6: Renumber remaining steps**

After deleting Step 3:
- Old Step 4 (Stop Touch Monitor) → New Step 3
- Old Step 5 (Verify Video File) → New Step 4
- Old Step 6 → New Step 5
- etc.

**Step 7: Update verification step**

In the new Step 4 (previously Step 5: Verify Video File), the bash command stays the same but update the context:

```markdown
### Step 4: Verify Video File

**Tool:** `Bash`
```bash
# Check video exists and is valid
ls -la {TEST_FOLDER}/recording/recording.mp4
ffprobe -v error -show_entries format=format_name -of default=noprint_wrappers=1:nokey=1 {TEST_FOLDER}/recording/recording.mp4
```

**If ffprobe fails:** Video may be corrupted. Show warning but continue with touch_events.json.

**If ffprobe succeeds:** Video is valid, continue.
```

**Step 8: Commit**

```bash
git add commands/stop-recording.md
git commit -m "feat(mobile-ui-testing): use screen-buffer-mcp to stop recording

Replace adb pkill screenrecord with device_stop_recording.
Remove wait for background process (no longer needed)."
```

---

## Task 3: Update run-test.md

**Files:**
- Modify: `commands/run-test.md`

**Step 1: Add screen-buffer recording tools to allowed-tools**

In the YAML frontmatter, add after line 11:

```yaml
  - mcp__screen-buffer__device_start_recording
  - mcp__screen-buffer__device_stop_recording
```

**Step 2: Remove mobile-mcp screenshot from allowed-tools**

Delete line 28:
```yaml
  - mcp__mobile-mcp__mobile_take_screenshot
```

**Step 3: Verify allowed-tools changes**

Run: `head -35 commands/run-test.md`
Expected:
- `mcp__screen-buffer__device_start_recording` present
- `mcp__screen-buffer__device_stop_recording` present
- `mcp__mobile-mcp__mobile_take_screenshot` removed

**Step 4: Update Step 5.5 - replace video recording start**

Replace lines 127-134 (the video recording bash command) with:

```markdown
**Start video recording:**

**Tool:** `mcp__screen-buffer__device_start_recording`
```json
{
  "output_path": "{REPORT_DIR}/recording/recording.mp4"
}
```

Store confirmation that recording started.
```

Remove the lines about VIDEO_PID (lines 131-134):
```markdown
Read the background task output file to get `VIDEO_PID=XXXXX`.
Store the number as `{VIDEO_PID}`.
```

**Step 5: Update Step 10 - replace video recording stop**

Replace lines 340-354 (Step 10, item 1: Stop video recording) with:

```markdown
1. **Stop video recording:**

   **Tool:** `mcp__screen-buffer__device_stop_recording`
   ```json
   {}
   ```

   This stops the recording and finalizes the video file.
   Video is saved at: `{REPORT_DIR}/recording/recording.mp4`
```

Remove the bash commands for pkill and waiting for VIDEO_PID.

**Step 6: Commit**

```bash
git add commands/run-test.md
git commit -m "feat(mobile-ui-testing): use screen-buffer-mcp for report recording

Replace adb screenrecord with device_start/stop_recording for test reports.
Remove mobile-mcp screenshot tool (using screen-buffer for all screenshots)."
```

---

## Task 4: Delete record-video.sh

**Files:**
- Delete: `scripts/record-video.sh`

**Step 1: Delete the file**

```bash
rm scripts/record-video.sh
```

**Step 2: Verify deletion**

```bash
ls scripts/record-video.sh
```
Expected: "No such file or directory"

**Step 3: Commit**

```bash
git add -A scripts/record-video.sh
git commit -m "chore(mobile-ui-testing): remove record-video.sh

No longer needed - using screen-buffer-mcp device_start_recording instead of adb screenrecord."
```

---

## Task 5: Update CLAUDE.md documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update Dependencies section**

Find the "ffmpeg (Required for Frame Extraction)" section. Keep it as-is (ffmpeg still needed).

Find "screen-buffer-mcp" section and update to:

```markdown
### screen-buffer-mcp (Video Recording and Screenshots)

Used for video recording and real-time screenshots:

```bash
# Install uv (Python package runner, like npx for Python)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart Claude Code after installation
```

**Note:** screen-buffer-mcp provides video recording without time limits (replaces adb screenrecord) and fast screenshots for verification actions.
```

**Step 2: Update Architecture section - scripts list**

Remove `record-video.sh` from the scripts list:

```markdown
scripts/
├── analyze-checkpoints.py   # Detect verification checkpoints
├── analyze-typing.py        # Detect keyboard typing sequences
├── generate-test.py         # YAML generation with verifications and typing
├── generate-report.py       # JSON→HTML report generator
├── load-config.py           # Load merged configuration
├── check-ffmpeg.sh          # Verifies ffmpeg is installed
├── monitor-touches.py       # Captures touch events via adb getevent
├── extract-frames.py        # Extracts frames from video at touch timestamps
├── parse-touches.py         # Parses raw touch events into gestures (legacy)
└── record-touches.sh        # Touch capture script (legacy)
```

**Step 3: Update Script Architecture Details**

Remove the line:
```markdown
- `record-video.sh` requires: adb accessible in PATH
```

**Step 4: Update Key processing flow**

Replace:
```markdown
Recording:
  Start video + touch monitor → User interacts → Stop → Extract frames → Generate approval UI
```

With:
```markdown
Recording:
  screen-buffer-mcp start recording → Start touch monitor → User interacts → Stop recording → Extract frames → Generate approval UI
```

**Step 5: Update MCP Server Architecture section**

Replace the "Video Recording + Frame Extraction" subsection:

```markdown
### Video Recording (screen-buffer-mcp)

The plugin uses screen-buffer-mcp for video recording during test execution and recording sessions.

**Flow:**
1. Video recording starts via `device_start_recording`
2. Test steps execute (no screenshot overhead)
3. Video stops via `device_stop_recording`
4. `extract-frames.py` extracts 7 frames per step in parallel:
   - 3 before frames (300ms, 200ms, 100ms before action)
   - 1 exact frame (at action moment)
   - 3 after frames (100ms, 200ms, 300ms after action)

**Benefits:**
- No recording time limit (unlike adb screenrecord's 3-minute limit)
- No runtime overhead during test execution
- Parallel frame extraction (10+ frames/sec with 32 workers)
- Video saved directly to host (no adb pull needed)
```

**Step 6: Update screen-buffer-mcp tools table**

Replace the existing tools table with:

```markdown
**Tools used:**
| Tool | Description |
|------|-------------|
| `device_start_recording` | Start video recording to file |
| `device_stop_recording` | Stop recording and finalize video |
| `device_screenshot` | Take screenshot for verification (~50ms) |
```

**Step 7: Update Recording Pipeline section**

Replace:
```markdown
**Requires:** ffmpeg installed (`brew install ffmpeg`)
```

With:
```markdown
**Requires:**
- ffmpeg installed (`brew install ffmpeg`) for frame extraction
- screen-buffer-mcp for video recording
```

Replace:
```markdown
/record-test {name}
    → Check ffmpeg availability
    → Create tests/{name}/ folder structure
    → Start video recording (adb screenrecord) in background
    → Start touch monitor (adb getevent) in background
```

With:
```markdown
/record-test {name}
    → Check ffmpeg availability
    → Create tests/{name}/ folder structure
    → Start video recording via screen-buffer-mcp (device_start_recording)
    → Start touch monitor (adb getevent) in background
```

Replace:
```markdown
/stop-recording
    → Stop video and touch capture processes
    → Pull video from device (recording.mp4)
```

With:
```markdown
/stop-recording
    → Stop video recording via screen-buffer-mcp (device_stop_recording)
    → Stop touch capture process
    → Video already saved to tests/{name}/recording/recording.mp4
```

**Step 8: Remove 3-minute limit mentions**

Search for and remove all mentions of "3-minute" or "3 minute" limit.

**Step 9: Update Debugging Commands section**

Remove the line:
```bash
# Start video recording manually
./scripts/record-video.sh /sdcard/test.mp4
```

**Step 10: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(mobile-ui-testing): update docs for screen-buffer-mcp recording

- Update architecture diagrams
- Remove 3-minute limit references
- Update MCP server documentation
- Remove record-video.sh references"
```

---

## Task 6: Verify Implementation

**Step 1: Check for remaining record-video.sh references**

```bash
grep -r "record-video.sh" . --include="*.md" --include="*.py" --include="*.sh"
```

Expected: No matches

**Step 2: Check for remaining 3-minute references**

```bash
grep -ri "3.minute\|3-minute\|three minute" . --include="*.md"
```

Expected: No matches

**Step 3: Check for remaining adb screenrecord references**

```bash
grep -ri "screenrecord\|pkill -2" . --include="*.md"
```

Expected: No matches (or only in docs/plans/ historical documents)

**Step 4: Final commit if any fixes needed**

If any references found, fix them and commit:

```bash
git add -A
git commit -m "fix(mobile-ui-testing): remove remaining old recording references"
```

---

## Summary

| Task | Files | Key Changes |
|------|-------|-------------|
| 1 | record-test.md | Use device_start_recording, remove videoPid |
| 2 | stop-recording.md | Use device_stop_recording, remove wait for PID |
| 3 | run-test.md | Use screen-buffer for report recording |
| 4 | record-video.sh | Delete file |
| 5 | CLAUDE.md | Update all documentation |
| 6 | - | Verify no old references remain |
