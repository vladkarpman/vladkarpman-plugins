# Interactive Approval UI Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the terminal-based verification interview with a browser-based visual approval UI where users can review, edit, and approve recorded test flows before generating YAML.

**Architecture:** Standalone HTML file with embedded JSON data, references video file in same folder. Two-panel layout with video scrubber and editable step timeline. Claude analyzes before/after frames during generation to provide smart descriptions and suggested verifications.

**Tech Stack:** HTML5, CSS, vanilla JavaScript, HTML5 Video API

---

## User Flow

```
User runs /stop-recording
    ↓
Stop video & touch capture (same as now)
    ↓
Extract frames at touch timestamps (before/after)
    ↓
Claude analyzes each step: before state, action, after state, suggested verification
    ↓
Generate approval.html + keep recording.mp4 in same folder
    ↓
Open approval.html in browser automatically
    ↓
User reviews, edits, reorders, adds verifications
    ↓
User clicks "Export YAML"
    ↓
Browser downloads test.yaml
    ↓
User places file in tests/{name}/ folder
```

## UI Layout

Two-panel layout with video on left, steps on right:

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER: Test: {name}  |  [Export YAML]  [Discard]              │
├───────────────────────────────────┬─────────────────────────────┤
│  VIDEO PANEL                      │  STEPS PANEL (scrollable)   │
│  ┌─────────────────────────────┐  │                             │
│  │                             │  │  Step 1: tap "5"       [×]  │
│  │    Current video frame      │  │  Before → Action → After    │
│  │                             │  │  💡 Suggested: [+ Add]      │
│  └─────────────────────────────┘  │  ────────────────────────   │
│  ◀────────●────────────────────▶  │  Step 2: tap "+"       [×]  │
│  0:05  [markers]           0:30   │  Before → Action → After    │
│                                   │  💡 Suggested: [+ Add]      │
│  [+ verify_screen] [+ wait_for]   │  ────────────────────────   │
│  [+ wait]                         │  ...                        │
├───────────────────────────────────┴─────────────────────────────┤
│  STEP EDITOR (when step selected or adding new)                 │
│  Action: [tap ▼]  Target: [5]  Wait after: [0]ms  [Save]       │
└─────────────────────────────────────────────────────────────────┘
```

## Step Card Design

Each step shows Before → Action → After pattern (same as report):

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: tap "5"                                       [Delete] │
│                                                                 │
│  ┌─────────┐      ┌─────────┐      ┌─────────┐                 │
│  │ BEFORE  │  →   │ ACTION  │  →   │  AFTER  │                 │
│  │ (frames)│      │   ●     │      │ (frames)│                 │
│  └─────────┘      └─────────┘      └─────────┘                 │
│                                                                 │
│  Before: Empty calculator display                               │
│  Action: Tapped "5" button                                      │
│  After:  Display shows "5"                                      │
│                                                                 │
│  💡 Suggested verification: "Display shows 5"                   │
│     [+ Add]  [Edit]  [Skip]                                     │
│                                                                 │
│  Wait after: [ 0 ] ms    [↑ Move up] [↓ Move down]             │
└─────────────────────────────────────────────────────────────────┘
```

## Editing Capabilities

**Standard editing (v1):**
- Delete steps
- Reorder steps (up/down buttons)
- Edit tap target (element text or coordinates)
- Add wait time after step
- Accept/edit/skip suggested verifications

**Adding new steps via video:**
1. User scrubs video to desired timestamp
2. Clicks "+ verify_screen", "+ wait_for", or "+ wait"
3. Enters description/element/duration
4. Step inserted in correct position based on timestamp

**NOT in v1 (too complex):**
- Adding new tap/swipe/type actions
- Element picker UI
- If needed, user edits downloaded YAML manually

## Data Structures

### Input: Recording artifacts

```
tests/{name}/recording/
├── recording.mp4              # Video file (referenced, not embedded)
├── touch_events.json          # Raw touch events with timestamps
└── screenshots/
    ├── step_001_before_*.png  # Before frames
    └── step_001_after_*.png   # After frames
```

### Embedded in approval.html

```json
{
  "testName": "calculator-test",
  "appPackage": "com.google.android.calculator",
  "device": { "id": "RFCW318P7NV", "name": "SM_S911B" },
  "videoFile": "recording.mp4",
  "videoDuration": 30.5,
  "steps": [
    {
      "id": "step_001",
      "timestamp": 2.34,
      "action": "tap",
      "target": { "text": "5", "x": 406, "y": 1645 },
      "frames": {
        "before": ["screenshots/step_001_before_1.png", "..."],
        "after": ["screenshots/step_001_after_1.png", "..."]
      },
      "analysis": {
        "before": "Calculator app with empty display",
        "action": "Tapped '5' button on number pad",
        "after": "Display now shows '5'",
        "change": "Number 5 appeared in display"
      },
      "suggestedVerification": "Display shows 5",
      "waitAfter": 0
    }
  ]
}
```

### Output: Generated YAML

```yaml
config:
  app: com.google.android.calculator

tests:
  - name: calculator-test
    steps:
      - tap: "5"
      - verify_screen: "Display shows 5"
      - tap: "+"
      - tap: "3"
      - tap: "="
      - verify_screen: "Display shows 8"
```

## Video Integration

**HTML5 Video features used:**
- Native `<video>` element with controls
- `video.currentTime` for scrubbing and position
- Custom markers on timeline showing step positions
- Click step → video seeks to that timestamp
- Pause at position → add step at that timestamp

**File reference (not embedded):**
```html
<video id="recording" src="recording.mp4" controls></video>
```

Approval.html and recording.mp4 must be in same folder.

## Claude Analysis (during /stop-recording)

For each touch event, Claude:

1. **Views before frames** - Describes screen state before tap
2. **Identifies action** - What element was tapped (uses vision + coordinates)
3. **Views after frames** - Describes screen state after tap
4. **Detects change** - What changed between before and after
5. **Suggests verification** - Proposes verify_screen based on change

This happens during `/stop-recording` before generating approval.html.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `templates/approval.html` | Create | New approval UI template |
| `scripts/generate-approval.py` | Create | Generate HTML with embedded data |
| `commands/stop-recording.md` | Modify | Replace interview with approval UI generation |

## Reuse from Report

Components to copy/adapt from `templates/report.html`:
- CSS variables and dark theme
- Frame container with Before → Action → After
- Frame animation CSS
- Thumbnail strip (for frame preview)
- Modal for full-size image view

## Export Logic (JavaScript)

```javascript
function exportYAML() {
    const steps = collectStepsFromUI();
    const yaml = generateYAML(steps);
    downloadFile('test.yaml', yaml);
}

function generateYAML(steps) {
    let yaml = `config:\n  app: ${appPackage}\n\ntests:\n  - name: ${testName}\n    steps:\n`;
    for (const step of steps) {
        yaml += stepToYAML(step);
    }
    return yaml;
}

function downloadFile(filename, content) {
    const blob = new Blob([content], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
}
```

## Success Criteria

1. User can review all recorded steps with Before/Action/After visuals
2. User can delete, reorder steps
3. User can edit tap targets (text or coordinates)
4. User can add wait times between steps
5. User can accept suggested verifications with one click
6. User can add new verify_screen/wait_for/wait via video scrubber
7. Export generates valid YAML that runs successfully
8. UI is consistent with report.html styling
