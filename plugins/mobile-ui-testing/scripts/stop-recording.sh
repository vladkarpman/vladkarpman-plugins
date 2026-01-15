#!/bin/bash
# Stop screen recording and pull file from device
# Usage: stop-recording.sh <device_id> <local_path>

DEVICE_ID="$1"
LOCAL_PATH="$2"
REMOTE_PATH="/sdcard/recording.mp4"

if [ -z "$DEVICE_ID" ] || [ -z "$LOCAL_PATH" ]; then
    echo '{"success": false, "error": "Usage: stop-recording.sh <device_id> <local_path>"}'
    exit 1
fi

# Stop screenrecord gracefully with SIGINT (allows moov atom to be written)
# SIGINT (2) = Ctrl+C equivalent, lets screenrecord finalize properly
# SIGTERM (15) = default kill, causes "moov atom not found" corruption
adb -s "$DEVICE_ID" shell "kill -2 \$(pgrep screenrecord)" 2>/dev/null

# Wait for screenrecord to finalize and write moov atom
sleep 2

# Check if file exists on device
if ! adb -s "$DEVICE_ID" shell "[ -f $REMOTE_PATH ]"; then
    echo '{"success": false, "error": "Recording file not found on device"}'
    exit 1
fi

# Pull file from device
if adb -s "$DEVICE_ID" pull "$REMOTE_PATH" "$LOCAL_PATH" > /dev/null 2>&1; then
    # Get file size
    SIZE=$(stat -f%z "$LOCAL_PATH" 2>/dev/null || stat -c%s "$LOCAL_PATH" 2>/dev/null || echo 0)

    # Clean up device
    adb -s "$DEVICE_ID" shell rm -f "$REMOTE_PATH" 2>/dev/null

    echo "{\"success\": true, \"output_path\": \"$LOCAL_PATH\", \"file_size_bytes\": $SIZE}"
    exit 0
else
    echo '{"success": false, "error": "Failed to pull recording from device"}'
    exit 1
fi
