# App State Management Actions Design

## Overview

Add two new YAML actions for managing app state during tests:
- `clear_app_data` - Clears all app data (cache, preferences, databases, files)
- `revoke_permissions` - Revokes all runtime permissions

These actions enable testing first-run experiences, permission flows, and fresh app states without manual intervention.

## YAML Syntax

### clear_app_data

```yaml
# Clear configured app's data (uses config.app)
- clear_app_data

# Clear specific app's data
- clear_app_data: "com.other.app"
```

**ADB command:** `adb shell pm clear <package>`

### revoke_permissions

```yaml
# Revoke configured app's permissions (uses config.app)
- revoke_permissions

# Revoke specific app's permissions
- revoke_permissions: "com.other.app"
```

**ADB command:** `adb shell pm reset-permissions -p <package>`

## Usage Examples

### Fresh State Testing

```yaml
config:
  app: com.example.app

setup:
  - clear_app_data
  - launch_app

tests:
  - name: Onboarding flow
    steps:
      - verify_screen: "Welcome screen"
      - tap: "Get Started"
```

### Permission Flow Testing

```yaml
config:
  app: com.example.camera

setup:
  - clear_app_data
  - revoke_permissions
  - launch_app

tests:
  - name: First-run camera permission
    steps:
      - tap: "Take Photo"
      - verify_screen: "Camera permission dialog"
      - tap: "Allow"
      - verify_screen: "Camera viewfinder"
```

### Combined Reset

```yaml
setup:
  - terminate_app
  - clear_app_data
  - revoke_permissions
  - launch_app
```

## Implementation

### Files to Modify

1. **`skills/yaml-test-schema/references/actions.md`**
   - Add "App State Management" section
   - Document both actions with examples
   - Note: Uses Bash/adb directly (not mobile-mcp tools)

2. **`commands/run-test.md`**
   - Ensure `Bash` is in allowed-tools (already present)
   - Add action handling logic

### Execution Logic

#### clear_app_data

```
1. Extract package:
   - If action has value → use that package
   - Else → use config.app
   - If neither → fail "No package specified"

2. Execute:
   adb -s {DEVICE_ID} shell pm clear {package}

3. Check result:
   - Exit code 0 + "Success" → pass
   - Otherwise → fail with adb output

4. Report:
   "[step] clear_app_data ✓" or error details
```

#### revoke_permissions

```
1. Extract package:
   - If action has value → use that package
   - Else → use config.app
   - If neither → fail "No package specified"

2. Execute:
   adb -s {DEVICE_ID} shell pm reset-permissions -p {package}

3. Check result:
   - Exit code 0 → pass
   - Otherwise → fail with adb output

4. Report:
   "[step] revoke_permissions ✓" or error details
```

### Error Handling

| Scenario | Behavior |
|----------|----------|
| App not installed | Fail: "Package not found: {package}" |
| No config.app and no explicit package | Fail: "No package specified for clear_app_data" |
| App running during clear_app_data | ADB force-stops then clears (handled automatically) |
| No permissions granted | revoke_permissions succeeds silently (no-op) |
| Device not connected | Fail: adb error message |

## Testing

### Integration Test

Add `tests/integration/examples/app-state-management.test.yaml`:

```yaml
config:
  app: com.google.android.calculator

tests:
  - name: Clear app data resets calculator
    steps:
      - launch_app
      - tap: "5"
      - tap: "+"
      - tap: "3"
      - tap: "="
      - verify_screen: "Result shows 8"
      - clear_app_data
      - launch_app
      - verify_screen: "Calculator in fresh state, no previous calculation"

  - name: Revoke permissions succeeds
    steps:
      - revoke_permissions
      - launch_app
      - verify_screen: "Calculator app launched"
```

### Manual Verification

```bash
# Test clear_app_data
adb shell pm clear com.google.android.calculator
# Expected: "Success"

# Test revoke_permissions
adb shell pm reset-permissions -p com.google.android.calculator
# Expected: silent success (exit code 0)
```

## Documentation Updates

### actions.md Addition

Add new section after "App Control":

```markdown
## App State Management

### Clear App Data
\`\`\`yaml
# Clear configured app's data
- clear_app_data

# Clear specific app's data
- clear_app_data: "com.example.app"
\`\`\`
Clears all app data: cache, preferences, databases, and files. App is force-stopped if running. Equivalent to "Clear Data" in Android Settings.

### Revoke Permissions
\`\`\`yaml
# Revoke configured app's permissions
- revoke_permissions

# Revoke specific app's permissions
- revoke_permissions: "com.example.app"
\`\`\`
Revokes all runtime permissions (camera, location, storage, etc.). App will prompt for permissions again on next use.
```

### Tool Mapping Table Addition

```markdown
| `clear_app_data` | Bash: `adb shell pm clear` |
| `revoke_permissions` | Bash: `adb shell pm reset-permissions` |
```

## Implementation Checklist

- [ ] Update `skills/yaml-test-schema/references/actions.md` with new section
- [ ] Update `commands/run-test.md` action handling
- [ ] Add integration test file
- [ ] Update CHANGELOG.md
- [ ] Test on real device
