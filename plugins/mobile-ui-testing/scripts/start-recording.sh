#!/bin/bash
# Start screen recording using adb screenrecord
# Usage: start-recording.sh <device_id> <output_path>

DEVICE_ID="$1"
OUTPUT_PATH="$2"

if [ -z "$DEVICE_ID" ] || [ -z "$OUTPUT_PATH" ]; then
    echo '{"success": false, "error": "Usage: start-recording.sh <device_id> <output_path>"}'
    exit 1
fi

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_PATH")"

# Remote path on device
REMOTE_PATH="/sdcard/recording.mp4"

# Remove any old recording
adb -s "$DEVICE_ID" shell rm -f "$REMOTE_PATH" 2>/dev/null

# Start recording in background (10 min max - we'll stop it manually)
# Note: Default limit is 180s, --time-limit 600 extends to 10 minutes
adb -s "$DEVICE_ID" shell screenrecord --time-limit 600 --bit-rate 8000000 "$REMOTE_PATH" &
ADB_PID=$!

# Capture timestamp immediately after starting
TIMESTAMP=$(python3 -c "import time; print(time.time())")

# Wait briefly for recording to initialize
sleep 1

# Verify it's running
if kill -0 "$ADB_PID" 2>/dev/null; then
    echo "{\"success\": true, \"recording_start_time\": $TIMESTAMP, \"pid\": $ADB_PID, \"remote_path\": \"$REMOTE_PATH\", \"local_path\": \"$OUTPUT_PATH\"}"
    exit 0
else
    echo '{"success": false, "error": "screenrecord failed to start"}'
    exit 1
fi
