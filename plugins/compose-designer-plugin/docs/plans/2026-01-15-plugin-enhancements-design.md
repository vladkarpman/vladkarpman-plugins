# Compose Designer Plugin Enhancements

**Date:** 2026-01-15
**Status:** Draft

## Problem

Users expect the plugin to:
1. Accept output directory as a command argument, not just config default
2. Understand existing project theme, colors, and reusable components
3. Run device tests with the project's actual theme, not generic MaterialTheme

## Solution

Three enhancements to configuration and workflow.

### 1. Output Directory Override

**Config (existing + clarified):**

```yaml
output:
  package_base: "com.myapp"
  default_output_dir: "app/src/main/java/ui"  # Default location
```

**Command flag (new):**

```bash
# Uses default
/compose-design create --input design.png --name ProfileScreen --type screen

# Overrides default for this run
/compose-design create --input design.png --name ProfileScreen --type screen --output ./features/profile/ui/
```

The `--output` flag takes precedence over `default_output_dir`.

### 2. Component Library (User-Curated)

Users specify reusable components in config. The generator prefers these over creating fresh code.

**Config section:**

```yaml
component_library:
  buttons:
    - name: "PrimaryButton"
      import: "com.myapp.ui.components.PrimaryButton"
      use_when: "primary action, submit, confirm"
      signature: "(text: String, onClick: () -> Unit, modifier: Modifier)"

    - name: "SecondaryButton"
      import: "com.myapp.ui.components.SecondaryButton"
      use_when: "secondary action, cancel, back"
      signature: "(text: String, onClick: () -> Unit, modifier: Modifier)"

  cards:
    - name: "ContentCard"
      import: "com.myapp.ui.components.ContentCard"
      use_when: "card container, elevated content"
      signature: "(modifier: Modifier, content: @Composable () -> Unit)"
```

**Generator behavior:**

1. Reads `component_library` before generating
2. Matches design elements to `use_when` hints
3. Uses listed components when appropriate
4. Generates fresh code for unlisted elements

**Scan command (new):**

```bash
/compose-design scan-components
```

Scans the codebase for `@Composable` functions and generates the `component_library` section automatically. Users review and edit the output.

Output:
```
✓ Found 12 reusable components
✓ Updated .claude/compose-designer.yaml

Review the component_library section and adjust if needed.
```

### 3. Project Theme for Device Testing

**Config section:**

```yaml
theme:
  composable: "com.myapp.ui.theme.AppTheme"
```

**Test activity generation:**

Current (generic):
```kotlin
setContent {
    MaterialTheme {
        ProfileScreen()
    }
}
```

New (project theme):
```kotlin
import com.myapp.ui.theme.AppTheme

setContent {
    AppTheme {
        ProfileScreen()
    }
}
```

**Fallback:** If `theme.composable` is not set, uses `MaterialTheme`.

## Complete Config Example

```yaml
# .claude/compose-designer.yaml

output:
  package_base: "com.myapp"
  default_output_dir: "app/src/main/java/ui"
  extract_theme_from_existing: true

theme:
  composable: "com.myapp.ui.theme.AppTheme"

component_library:
  buttons:
    - name: "PrimaryButton"
      import: "com.myapp.ui.components.PrimaryButton"
      use_when: "primary action, submit, confirm"
      signature: "(text: String, onClick: () -> Unit, modifier: Modifier)"

    - name: "SecondaryButton"
      import: "com.myapp.ui.components.SecondaryButton"
      use_when: "secondary action, cancel, back"
      signature: "(text: String, onClick: () -> Unit, modifier: Modifier)"

# ... rest of existing config unchanged
```

## Implementation Tasks

### Phase 1: Output Override
1. Add `--output` flag to `commands/create.md`
2. Update command argument parsing
3. Override `default_output_dir` when flag present

### Phase 2: Project Theme
1. Add `theme.composable` to config schema
2. Update `agents/device-tester.md` to read theme config
3. Generate test activity with configured theme
4. Add import statement for theme composable

### Phase 3: Component Library
1. Add `component_library` section to config schema
2. Create `commands/scan-components.md` command
3. Implement codebase scanner for `@Composable` functions
4. Infer `use_when` hints from function names and context
5. Update `agents/design-generator.md` to read component library
6. Match design elements to library components

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Output subdirs by type | No | Over-engineering. Single default + override is simpler. |
| Component detection | User-curated | Automatic matching is complex and error-prone. Users know their codebase. |
| Scan command | Yes | Automates initial setup while keeping user control. |
| Theme config | Explicit | No magic detection. User specifies, plugin uses, fallback to MaterialTheme. |

## Out of Scope

- Automatic component matching based on visual similarity
- Per-type output subdirectories (`components/` vs `screens/`)
- Theme auto-detection from codebase

These can be revisited in future versions if needed.
