# Configuration Documentation Design

**Date:** 2026-01-14
**Status:** Approved
**Goal:** Add comprehensive configuration documentation with examples and option explanations

## Overview

Users need better documentation for configuration options. The current README has a config schema but lacks detailed explanations of valid options for fields like `device_id`, `interaction_depth`, and model settings.

## Deliverables

### 1. Create `docs/CONFIGURATION.md`

Detailed configuration guide with:

1. **Overview** - What the config file does, where it lives
2. **Required Fields** - `output.package_base` and `testing.test_activity_package`
3. **Configuration Sections** - One section per YAML block with tables and detailed explanations
4. **Complete Example** - Fully annotated config file
5. **Common Presets** - Fast iteration, high quality configurations

### 2. Update `README.md`

- Replace verbose config schema with condensed quick-reference table
- Add link to `docs/CONFIGURATION.md` for details
- Keep it scannable

## Field Documentation

### Model Configuration

| Field | Type | Default | Options |
|-------|------|---------|---------|
| `default` | string | `"opus"` | `opus`, `sonnet`, `haiku` |
| `design_generator` | string | inherits default | `opus`, `sonnet`, `haiku` |
| `visual_validator` | string | inherits default | `opus`, `sonnet`, `haiku` |
| `baseline_preprocessor` | string | inherits default | `opus`, `sonnet`, `haiku` |
| `device_tester` | string | inherits default | `opus`, `sonnet`, `haiku` |

**Model Options:**
- **`opus`** - Most capable. Best for complex designs, nuanced visual analysis. Default for highest quality.
- **`sonnet`** - Balanced capability and speed. Good for faster iteration during development.
- **`haiku`** - Fastest and cheapest. Use for simple components or quick prototyping.

### Device Testing

| Field | Type | Default | Options |
|-------|------|---------|---------|
| `test_activity_package` | string | **required** | Any valid package name |
| `test_activity_name` | string | `"ComposeTestActivity"` | Any valid class name |
| `device_id` | string | `"auto"` | `auto`, device ID, name pattern |
| `interaction_depth` | string | `"comprehensive"` | `basic`, `comprehensive` |
| `cleanup_artifacts` | string | `"ask"` | `always`, `never`, `ask` |

**`device_id` Options:**
- **`"auto"`** - Selects first available device from `adb devices`. Best for single-device setups.
- **Specific ID** - Use exact device ID like `"emulator-5554"` or `"RFCN123ABC"`. Find with `adb devices`.
- **Name pattern** - Use wildcards like `"Pixel*"` or `"*Emulator*"` to match device names.

**`interaction_depth` Options:**
- **`"basic"`** - Tests rendering only. Verifies component displays correctly without crashes.
- **`"comprehensive"`** - Tests rendering plus interactions: button clicks, text input, scrolling, state changes.

**`cleanup_artifacts` Options:**
- **`"always"`** - Auto-remove test activity and APK after testing.
- **`"never"`** - Keep all artifacts for debugging.
- **`"ask"`** - Prompt after each test run. Recommended for learning.

### Validation

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `visual_similarity_threshold` | float | `0.92` | Range: 0.0-1.0. Higher = stricter |
| `max_ralph_iterations` | int | `10` | More iterations = better but slower |
| `preview_screenshot_delay` | string/int | `"auto"` | `"auto"` or milliseconds |

**`preview_screenshot_delay`** - Use `"auto"` normally. Set manual value (e.g., `3000`) if previews render incomplete.

### Batch Processing

| Field | Type | Default | Options |
|-------|------|---------|---------|
| `mode` | string | `"sequential"` | `sequential`, `parallel` |

- **`"sequential"`** - Process one design at a time. Safer, easier to debug.
- **`"parallel"`** - Process multiple concurrently. Faster but harder to trace errors.

### Figma Integration

| Field | Type | Default | Options |
|-------|------|---------|---------|
| `api_token_source` | string | `"env"` | `env`, `config` |

- **`"env"`** - Read from `$FIGMA_TOKEN` environment variable. More secure.
- **`"config"`** - Store in config file. Avoid committing to version control.

## Common Presets

### Fast Iteration (Development)

```yaml
model:
  default: "sonnet"
validation:
  visual_similarity_threshold: 0.85
  max_ralph_iterations: 5
testing:
  interaction_depth: "basic"
  cleanup_artifacts: "always"
```

### High Quality (Production)

```yaml
model:
  default: "opus"
validation:
  visual_similarity_threshold: 0.95
  max_ralph_iterations: 12
testing:
  interaction_depth: "comprehensive"
```

## Complete Example Config

```yaml
# .claude/compose-designer.yaml

model:
  default: "opus"

naming:
  component_suffix: "Component"
  screen_suffix: "Screen"
  preview_annotation: "@Preview"

architecture:
  stateless_components: true
  state_hoisting: true
  remember_saveable: false

preview:
  show_background: true
  background_color: "#FFFFFF"
  device_spec: "spec:width=411dp,height=891dp"
  font_scale: 1.0

validation:
  visual_similarity_threshold: 0.92
  max_ralph_iterations: 10
  preview_screenshot_delay: "auto"

batch:
  mode: "sequential"

testing:
  test_activity_package: "com.yourapp.test"  # REQUIRED
  test_activity_name: "ComposeTestActivity"
  device_id: "auto"
  interaction_depth: "comprehensive"
  cleanup_artifacts: "ask"

figma:
  extract_tokens: true
  api_token_source: "env"
  fallback_to_image: true

output:
  package_base: "com.yourapp"  # REQUIRED
  default_output_dir: "app/src/main/java"
  include_comments: false
  extract_theme_from_existing: true
```
