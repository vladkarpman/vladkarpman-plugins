# YouTube Comprehensive Test Design

## Overview

A single comprehensive test covering YouTube's core user journeys: search & playback flow, and content discovery through Home/Shorts tabs.

## Test Details

- **Test Name:** youtube-comprehensive-flow
- **App:** com.google.android.youtube
- **Duration:** ~22 steps, 120s timeout
- **Search Term:** "lofi hip hop" (evergreen, reliable results)

## Verification Strategy

Hybrid approach:
- **Element-based** for navigation (Home, Search, Shorts tabs)
- **Screen-based** for content states (video playing, feed loaded)
- **Conditional handling** for popups, ads, login prompts

## Test Flow

### Part 1: Search & Playback (12 steps)
1. Launch app, wait for Home tab
2. Handle potential popup
3. Open search, enter "lofi hip hop"
4. Verify search results
5. Tap first video result
6. Verify video playback
7. Return to results

### Part 2: Content Discovery (10 steps)
1. Navigate to Home tab
2. Verify home feed loaded
3. Scroll feed, verify more content
4. Navigate to Shorts
5. Verify short-form video playing
6. Exit and verify main UI

## Error Handling

| Issue | Mitigation |
|-------|------------|
| Login prompt | `if_exists: "Sign in"` → dismiss |
| Ad before video | `if_exists: "Skip Ad"` → tap |
| Network slow | 120s timeout, generous waits |
| Shorts auto-advance | Quick verification |

## Files

- `tests/youtube-comprehensive/test.yaml` - Main test file
- `tests/youtube-comprehensive/baselines/` - Screenshot baselines
- `tests/youtube-comprehensive/reports/` - Test reports
