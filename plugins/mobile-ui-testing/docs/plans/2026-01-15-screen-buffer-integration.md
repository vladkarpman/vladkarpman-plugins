# Screen-Buffer MCP Integration

## Overview

Replace deprecated device-manager-mcp with screen-buffer-mcp for screenshots, falling back to mobile-mcp for all other device operations.

## Architecture

**Principle:** Use screen-buffer only for what it does uniquely well (fast screenshots + frame buffer). Use mobile-mcp for everything else.

| Operation | MCP | Reasoning |
|-----------|-----|-----------|
| Screenshot | screen-buffer | Fast (~50ms), frame buffer |
| Frame buffer | screen-buffer | Unique capability |
| Device list | mobile-mcp | Single source of truth |
| Screen size | mobile-mcp | Single source of truth |
| Tap/Swipe/Type | mobile-mcp | Only option |
| App lifecycle | mobile-mcp | Only option |
| Element listing | mobile-mcp | Only option |

## Tool Mapping

```
# Screenshots → screen-buffer
mcp__device-manager__device_screenshot  → mcp__screen-buffer__device_screenshot

# Everything else → mobile-mcp
mcp__device-manager__device_list        → mcp__mobile-mcp__mobile_list_available_devices
mcp__device-manager__device_screen_size → mcp__mobile-mcp__mobile_get_screen_size
mcp__device-manager__device_tap         → mcp__mobile-mcp__mobile_click_on_screen_at_coordinates
mcp__device-manager__device_swipe       → mcp__mobile-mcp__mobile_swipe_on_screen
mcp__device-manager__device_type        → mcp__mobile-mcp__mobile_type_keys
mcp__device-manager__device_press_key   → mcp__mobile-mcp__mobile_press_button
```

## Parameter Changes

| device-manager | mobile-mcp | Change |
|----------------|------------|--------|
| `device_tap(x, y)` | `mobile_click_on_screen_at_coordinates(device, x, y)` | Add `device` param |
| `device_type(text)` | `mobile_type_keys(device, text, submit)` | Add `device`, `submit` params |
| `device_press_key(key)` | `mobile_press_button(device, button)` | Rename `key` → `button` |
| `device_swipe(direction, distance)` | `mobile_swipe_on_screen(device, direction, distance)` | Add `device` param |

## Files to Update

| File | Action |
|------|--------|
| `commands/run-test.md` | Replace all device-manager refs |
| `commands/record-test.md` | Replace device list refs |
| `CLAUDE.md` | Rewrite MCP architecture section |
| `hooks/hooks.json` | Add screen-buffer auto-approval |
| `README.md` | Update if device-manager mentioned |

## Files NOT Changed

- `.mcp.json` — Already configured
- `agents/*.md` — Use commands, no direct MCP refs
- `skills/**` — Documentation only

## Verification

Run `/run-test` on existing test after changes to confirm functionality.
