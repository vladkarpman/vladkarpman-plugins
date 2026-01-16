# Step Model Redesign

**Date:** 2026-01-16
**Status:** Approved

## Overview

Redesign the step model and approval UI to support a cleaner mental model where:
- Steps have Before/Action/After frames with descriptions
- Verification is optional and embedded in any step (not a separate step type)
- Conditions check the Before frame state before executing
- Inline editing for all step properties
- Video picker modal for frame selection

## Step Types

| Step Type | Frames | Action Params |
|-----------|--------|---------------|
| **tap** | Before, Action, After | x, y coordinates |
| **swipe** | Before, Action, After | direction, x, y, distance |
| **wait_for** | Before, After | element text |
| **wait** | None | duration |

All step types can have:
- **Verification** (optional) - assertion on After frame
- **Condition** (optional) - checks Before frame state

## Data Model

```javascript
step = {
  id: "step_001",

  // Frames - each has image path and description
  frames: {
    before: { image: "path.png", description: "Login screen" },
    action: { image: "path.png" },  // Only for tap/swipe
    after: { image: "path.png", description: "Dashboard loaded" }
  },

  // Action type and parameters
  action: "tap",  // tap, swipe, wait, wait_for
  params: {
    // For tap: { x, y }
    // For swipe: { direction, x, y, distance }
    // For wait: { duration }
    // For wait_for: { element }
  },

  // Optional verification (assertion on After frame)
  verification: {
    enabled: false,
    description: "Dashboard shows user name"
  },

  // Optional condition (checks Before frame)
  condition: {
    enabled: false,
    type: "if_present",  // if_present, if_absent, if_screen, if_all_present, if_any_present
    value: "Popup"       // string or array for if_all_present/if_any_present
  }
}
```

## UI Components

### Step Card (List View)

Step cards are inline editable. No separate Edit button needed.

**For tap/swipe (3 frames):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ① 🔵 TAP    Tapped Submit button                    [↑] [↓] [✕] │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                      │
│  │ BEFORE  │    │ ACTION  │    │  AFTER  │                      │
│  │  [img]  │    │  [img]  │    │  [img]  │                      │
│  │         │    │    ◉    │    │         │                      │
│  └─────────┘    └─────────┘    └─────────┘                      │
│  Login screen   Tap at (540,   Dashboard                        │
│  showing        800)           loaded                           │
├─────────────────────────────────────────────────────────────────┤
│  ⚡ CONDITION: if_present "Popup"                               │
│  ✓ VERIFICATION: Dashboard shows user name                      │
├─────────────────────────────────────────────────────────────────┤
│                              [+ Condition] [+ Verification]     │
└─────────────────────────────────────────────────────────────────┘
```

**For wait_for (2 frames):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ② ⏳ WAIT_FOR   Waiting for "Loading" to disappear  [↑] [↓] [✕] │
├─────────────────────────────────────────────────────────────────┤
│       ┌─────────┐              ┌─────────┐                      │
│       │ BEFORE  │      →       │  AFTER  │                      │
│       │  [img]  │              │  [img]  │                      │
│       └─────────┘              └─────────┘                      │
│       Loading visible          Loading gone                     │
├─────────────────────────────────────────────────────────────────┤
│                              [+ Condition] [+ Verification]     │
└─────────────────────────────────────────────────────────────────┘
```

**For wait (no frames):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ③ ⏱️ WAIT      Wait 2 seconds                       [↑] [↓] [✕] │
├─────────────────────────────────────────────────────────────────┤
│       Duration: [2    ] seconds                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [+ Condition] [+ Verification]     │
└─────────────────────────────────────────────────────────────────┘
```

**Inline editing:**
- Click description → edit text inline
- Click frame image → open video picker modal
- Click condition/verification → expand for editing

### Add Step Flow

**Step 1: Choose Action Type**
```
┌──────────────────────────────────────┐
│         What type of step?           │
│                                      │
│   ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐ │
│   │ 👆  │  │ ↕️  │  │ ⏳  │  │ ⏱️  │ │
│   │ Tap │  │Swipe│  │Wait │  │Wait │ │
│   │     │  │     │  │ For │  │     │ │
│   └─────┘  └─────┘  └─────┘  └─────┘ │
└──────────────────────────────────────┘
```

**Step 2: Configure (adapts based on type)**

For tap/swipe (3 frames):
```
┌────────────┬────────────┬────────────┐
│   BEFORE   │   ACTION   │   AFTER    │
│  [video]   │  [video]   │  [video]   │
│  Click to  │  Click to  │  Click to  │
│  capture   │  place tap │  capture   │
├────────────┴────────────┴────────────┤
│ Description: ________________________ │
│ [+ Condition]  [+ Verification]       │
│                        [Cancel] [Add] │
└──────────────────────────────────────┘
```

For wait_for (2 frames):
```
┌─────────────────┬─────────────────┐
│     BEFORE      │      AFTER      │
│    [video]      │     [video]     │
├─────────────────┴─────────────────┤
│ Wait for element: _______________ │
│ [+ Condition]  [+ Verification]   │
│                      [Cancel][Add]│
└───────────────────────────────────┘
```

For wait (no frames):
```
┌───────────────────────────────────┐
│ Duration: [____] seconds          │
│ [+ Condition]  [+ Verification]   │
│                      [Cancel][Add]│
└───────────────────────────────────┘
```

### Video Picker Modal

Opens when clicking a frame to select/change it:

```
┌─────────────────────────────────────────────────────────────┐
│  Select BEFORE Frame                                    [✕] │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                     │    │
│  │                    [VIDEO]                          │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│  [▶]  ════════════●══════════════════  0:12 / 0:45          │
├─────────────────────────────────────────────────────────────┤
│  For ACTION frame: click on video to place tap/swipe        │
│                                                             │
│  Description: ________________________________________      │
│                                                             │
│                                    [Cancel]  [Capture]      │
└─────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Scrub video to desired moment
- For Before/After: scrub and capture
- For Action: scrub + click on video to place tap position (shows indicator)
- Description field for this frame
- "Capture" saves frame and closes modal

### Condition Editing (Inline)

**Collapsed:**
```
⚡ CONDITION (click to expand)
```

**Expanded:**
```
┌─────────────────────────────────────────────────────────────┐
│ ⚡ CONDITION                                           [✕]  │
├─────────────────────────────────────────────────────────────┤
│  Type: [if_present     ▼]                                   │
│                                                             │
│  Value: [________________]                                  │
│                                                             │
│  For if_all_present / if_any_present:                       │
│  Elements: [element 1    ] [+ Add]                          │
│            [element 2    ] [✕]                              │
└─────────────────────────────────────────────────────────────┘
```

**Condition types:**
- `if_present` - element exists
- `if_absent` - element doesn't exist
- `if_screen` - AI vision check
- `if_all_present` - multiple elements (AND)
- `if_any_present` - multiple elements (OR)

### Verification Editing (Inline)

**Collapsed:**
```
✓ VERIFICATION (click to expand)
```

**Expanded:**
```
┌─────────────────────────────────────────────────────────────┐
│ ✓ VERIFICATION                                         [✕]  │
├─────────────────────────────────────────────────────────────┤
│  Assert on AFTER frame:                                     │
│  [Dashboard displays welcome message with user name    ]    │
└─────────────────────────────────────────────────────────────┘
```

## Out of Scope (TODO)

- **Preconditions** - global app state setup (separate from per-step conditions)
- **Separate verify_screen step type** - now embedded as verification in any step

## YAML Export Format

The YAML export will generate:

```yaml
config:
  app: com.example.app

tests:
  - name: Test Name
    steps:
      # Tap with condition and verification
      - if_present: "Popup"
        tap: [540, 800]
        verify_screen: "Dashboard shows user name"

      # Simple swipe
      - swipe:
          direction: up
          x: 540
          y: 1200
          distance: 400

      # Wait for element
      - wait_for: "Loading"
        verify_screen: "Content loaded"

      # Simple wait
      - wait: 2s
```

## Implementation Plan

1. Update step data model in JavaScript
2. Refactor step card HTML/CSS for new layout
3. Implement inline editing for descriptions
4. Build video picker modal
5. Implement condition editing UI
6. Implement verification editing UI
7. Update Add Step flow with hybrid approach
8. Update YAML export to match new model
9. Migrate existing steps to new format
