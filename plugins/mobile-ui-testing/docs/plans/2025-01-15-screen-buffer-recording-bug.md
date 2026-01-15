# screen-buffer-mcp Recording Bug: moov atom not written

**Date:** 2025-01-15
**Status:** Blocking
**Affects:** All video recording functionality in mobile-ui-testing plugin

## Problem

The `device_start_recording` and `device_stop_recording` tools from screen-buffer-mcp produce corrupted video files. The "moov atom" (video index/metadata) is not written when recording stops, making the files unplayable and unusable by ffmpeg for frame extraction.

## Error

```
[mov,mp4,m4a,3gp,3g2,mj2 @ 0x936c28000] moov atom not found
tests/migration-test/recording/recording.mp4: Invalid data found when processing input
```

## Reproduction Steps

```bash
# 1. Start recording
mcp__screen-buffer__device_start_recording with output_path="/path/to/recording.mp4"
# Returns: success: true

# 2. Wait or interact with device
# ...

# 3. Stop recording
mcp__screen-buffer__device_stop_recording
# Returns: success: true, duration_seconds: 16.74, file_size_bytes: 1048624

# 4. Verify file
ffprobe -v error -show_entries format=duration tests/migration-test/recording/recording.mp4
# ERROR: moov atom not found
```

## Technical Background

MP4 files require a "moov atom" (movie metadata box) to be playable. This contains:
- Video duration
- Frame index
- Codec parameters

The moov atom is typically written at the end of recording. If recording is interrupted or not properly finalized, the moov atom is missing and the file is corrupt.

With `adb screenrecord`, we solved this by sending SIGINT (`pkill -2 screenrecord`) which triggers proper finalization. screen-buffer-mcp uses scrcpy for recording, which may have a similar requirement that isn't being handled.

## Current State

The migration from adb screenrecord to screen-buffer-mcp is **code complete** but **not functional** due to this bug:

**Commits made (on main branch):**
```
3f6d2e3 docs(mobile-ui-testing): clean up Recording Pipeline section title
a5a1a0c docs(mobile-ui-testing): update README for screen-buffer-mcp
5b84698 docs(mobile-ui-testing): update docs for screen-buffer-mcp recording
ba0cba7 chore(mobile-ui-testing): remove record-video.sh
869b057 feat(mobile-ui-testing): use screen-buffer-mcp for report recording
f1d4429 feat(mobile-ui-testing): use screen-buffer-mcp for precondition recording
b7a8556 feat(mobile-ui-testing): use screen-buffer-mcp to stop recording
1a41e7c feat(mobile-ui-testing): use screen-buffer-mcp for recording
```

## Options to Investigate

### Option A: Fix screen-buffer-mcp

Check the screen-buffer-mcp source code to see how it handles recording finalization. scrcpy has a `--record` flag that should handle this properly. The MCP server may not be passing the right signals.

**Repository:** Check where screen-buffer-mcp is hosted (likely needs `uvx` source inspection)

### Option B: Revert migration

Revert commits and go back to adb screenrecord with 3-minute limit:

```bash
git revert 3f6d2e3 a5a1a0c 5b84698 ba0cba7 869b057 f1d4429 b7a8556 1a41e7c
```

Or restore `record-video.sh` from git history and update commands to use it again.

### Option C: Hybrid approach

Keep screen-buffer-mcp for screenshots (works fine) but use adb screenrecord for video recording:
- `device_screenshot` for verify_screen, if_screen
- `adb screenrecord` for recording sessions (via bash script)

This maintains the 3-minute limit but keeps fast screenshots.

## Files Changed in Migration

| File | Current State | Revert Target |
|------|--------------|---------------|
| `commands/record-test.md` | Uses `device_start_recording` | Restore bash script |
| `commands/stop-recording.md` | Uses `device_stop_recording` | Restore pkill + wait |
| `commands/record-precondition.md` | Uses `device_start_recording` | Restore bash script |
| `commands/run-test.md` | Uses screen-buffer recording | Restore bash script |
| `scripts/record-video.sh` | Deleted | Restore from git |
| `CLAUDE.md` | Updated docs | Restore old docs |
| `README.md` | Updated docs | Restore old docs |

## Test Files (can be deleted)

```
tests/migration-test/recording/recording.mp4
tests/migration-test/recording/recording2.mp4
```

## Next Steps

1. Investigate screen-buffer-mcp source to understand recording mechanism
2. Check if scrcpy `--record` works correctly when invoked directly
3. Decide on option (A, B, or C) based on findings
4. Either fix screen-buffer-mcp or revert migration
