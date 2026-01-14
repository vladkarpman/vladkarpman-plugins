# Paparazzi Integration Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate Paparazzi for fast JVM-based screenshot validation, reducing iteration time from ~40-75s to ~5-10s per cycle.

**Architecture:** Two-phase validation - Paparazzi for fast iteration, Device for final verification (both enabled by default).

**Tech Stack:** Paparazzi (Cash App), Gradle, Kotlin, Compose

---

## Problem Statement

Current validation loop is slow:
- APK build: ~30-60s
- Deploy to device: ~5-10s
- Screenshot capture: ~2-3s
- **Total: ~40-75s per iteration**

This slows down the design-to-code feedback loop significantly.

## Solution

Integrate [Paparazzi](https://github.com/cashapp/paparazzi) for JVM-based screenshot rendering:
- No APK build needed (JVM test only)
- No device deployment
- Instant screenshot capture
- **Total: ~5-10s per iteration (7-10x faster)**

Device validation remains as final verification to catch platform-specific rendering differences.

---

## Architecture

### Validation Pipeline v3

```
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION PIPELINE v3                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: Input Processing                                      │
│     (unchanged)                                                 │
│                                                                 │
│  Phase 1.5: Baseline Preprocessing                              │
│     (unchanged)                                                 │
│                                                                 │
│  Phase 2: Code Generation                                       │
│     (unchanged - generates .kt with testTag)                    │
│                                                                 │
│  Phase 3: Paparazzi Validation (NEW - Fast Iteration)           │
│     • Copy component to plugin test harness                     │
│     • Generate Paparazzi test                                   │
│     • Run: ./gradlew verifyPaparazziDebug (~5-10s)              │
│     • Compare screenshot with SSIM (threshold: 0.95)            │
│     • If SSIM fails: LLM Vision analysis + iterate              │
│     • Loop until PASS or max iterations (5)                     │
│                                                                 │
│  Phase 4: Device Validation (Final Verification)                │
│     • Enabled by default                                        │
│     • Runs AFTER Paparazzi passes                               │
│     • Uses existing mobile-mcp flow                             │
│     • LLM Vision primary validation                             │
│     • Catches platform-specific rendering issues                │
│                                                                 │
│  Phase 5: Final Report                                          │
│     (updated to include both phase results)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Expected Flow

```
Paparazzi: Iterate 2-3x (~15-30s total)
    │
    ▼ PASS
Device: Usually passes first try (~45s)
    │
    ▼ PASS
COMPLETE (~60-75s total vs ~3-5min before)
```

---

## Plugin Test Harness

Self-contained Gradle project managed by the plugin.

### Location

```
${CLAUDE_PLUGIN_ROOT}/test-harness/
```

### Structure

```
test-harness/
├── build.gradle.kts          # Paparazzi + Compose dependencies
├── settings.gradle.kts
├── gradle.properties
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.jar
│       └── gradle-wrapper.properties
├── src/
│   ├── main/
│   │   └── kotlin/
│   │       └── generated/    # Generated components copied here
│   └── test/
│       └── kotlin/
│           └── generated/    # Generated Paparazzi tests
└── snapshots/                # Baseline images for comparison
```

### build.gradle.kts

```kotlin
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("app.cash.paparazzi")
}

android {
    namespace = "com.compose.designer.testharness"
    compileSdk = 34

    defaultConfig {
        minSdk = 24
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.8"
    }
}

dependencies {
    // Compose
    implementation(platform("androidx.compose:compose-bom:2024.02.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")

    // Paparazzi
    testImplementation("app.cash.paparazzi:paparazzi:1.3.2")
}
```

### Generated Test Example

```kotlin
// test-harness/src/test/kotlin/generated/JetNewsCardComponentTest.kt
package generated

import app.cash.paparazzi.DeviceConfig
import app.cash.paparazzi.Paparazzi
import org.junit.Rule
import org.junit.Test

class JetNewsCardComponentTest {
    @get:Rule
    val paparazzi = Paparazzi(
        deviceConfig = DeviceConfig.PIXEL_5
    )

    @Test
    fun snapshot() {
        paparazzi.snapshot {
            JetNewsCardComponentPreview()
        }
    }
}
```

---

## Configuration

### Updated compose-designer.yaml

```yaml
# Validation settings
validation:
  ssim_sanity_threshold: 0.4           # Flag for review if LLM passes but SSIM below

  # Paparazzi phase (JVM-based fast iteration)
  paparazzi:
    enabled: true                      # Enable Paparazzi validation
    threshold: 0.95                    # SSIM threshold (stricter - deterministic JVM rendering)
    max_iterations: 5                  # Max iterations in Paparazzi phase
    device_config: "PIXEL_5"           # Paparazzi device configuration

  # Device phase (Android device/emulator verification)
  device:
    enabled: true                      # Enable device validation (default: true)
    threshold: 0.92                    # SSIM threshold (for sanity check)
    max_iterations: 5                  # Max iterations in Device phase
```

### Why Different Thresholds?

| Phase | Threshold | Reason |
|-------|-----------|--------|
| Paparazzi | 0.95 | Deterministic JVM rendering - no device variance |
| Device | 0.92 | Platform differences in fonts, antialiasing, etc. |

---

## Paparazzi Validation Flow

### Phase 3: Paparazzi Validation

```
1. SETUP
   ├── Check test harness exists, initialize if needed
   ├── Copy generated component.kt to test-harness/src/main/kotlin/generated/
   ├── Copy baseline image to test-harness/snapshots/
   └── Generate ComponentTest.kt with Paparazzi snapshot call

2. ITERATION LOOP
   ├── Run: ./gradlew verifyPaparazziDebug
   ├── Paparazzi renders component → captures screenshot
   ├── Compare Paparazzi output with baseline using SSIM
   │
   ├── If SSIM ≥ 0.95 (threshold):
   │   └── PASS → Proceed to Phase 4 (Device Validation)
   │
   └── If SSIM < 0.95:
       ├── LLM Vision analyzes diff (Paparazzi output vs baseline)
       ├── Apply suggested fixes to component.kt
       ├── Copy updated component to test harness
       ├── Increment iteration counter
       └── Repeat (max 5 iterations)

3. EXIT CONDITIONS
   ├── PASS: SSIM threshold reached → Continue to Device phase
   ├── MAX_ITERATIONS: Couldn't converge → Ask user (continue to device or abort)
   └── STUCK: LLM says unfixable → Ask user
```

### Phase 4: Device Validation (unchanged from v2)

```
1. Build APK (only once - component pre-validated by Paparazzi)
2. Deploy to device via mobile-mcp
3. Capture screenshot
4. Extract component bounds, crop
5. LLM Vision validation (primary)
6. SSIM calculation (secondary, logged)
7. Handle verdict (PASS/ITERATE/STUCK)
```

---

## Integration Points

### Device Phase Benefits from Paparazzi

- Component already ~95% correct from Paparazzi phase
- Device phase typically passes first try
- Only catches platform-specific issues:
  - Font rendering differences
  - Hardware-accelerated drawing
  - Material theme variations
  - Android version differences

### When Device Might Still Iterate

- Custom fonts not available in Paparazzi
- Platform-specific Compose behaviors
- Hardware-dependent rendering (shadows, blur)

---

## New Components

### Files to Create

| Component | Description |
|-----------|-------------|
| `test-harness/` | Self-contained Gradle project with Paparazzi |
| `agents/paparazzi-validator.md` | Agent for Paparazzi validation loop |
| `utils/setup-test-harness.sh` | Initialize test harness on first run |
| `utils/generate-paparazzi-test.py` | Generate test file for component |

### Files to Modify

| File | Change |
|------|--------|
| `commands/config.md` | Add `validation.paparazzi.*` and `validation.device.*` |
| `commands/create.md` | Add Phase 3 (Paparazzi), rename Phase 4 (Device) |
| `test-project/.claude/compose-designer.yaml` | Add new config defaults |
| `tests/validate-plugin.sh` | Add validation for test-harness |

---

## Implementation Tasks

### Task 1: Create Test Harness Gradle Project
- Create `test-harness/` directory structure
- Add `build.gradle.kts` with Paparazzi + Compose
- Add Gradle wrapper
- Verify builds: `./gradlew build`

### Task 2: Create Test Harness Setup Utility
- Create `utils/setup-test-harness.sh`
- Initialize test harness if not exists
- Verify Gradle wrapper works
- Handle first-run setup

### Task 3: Create Paparazzi Test Generator
- Create `utils/generate-paparazzi-test.py`
- Input: component name, preview function name
- Output: `ComponentTest.kt` file
- Handle package imports

### Task 4: Create Paparazzi Validator Agent
- Create `agents/paparazzi-validator.md`
- Copy component to test harness
- Generate test file
- Run Paparazzi
- Compare output with SSIM
- LLM Vision analysis on failure
- Iteration loop

### Task 5: Update Configuration Schema
- Add `validation.paparazzi.*` fields to `commands/config.md`
- Add `validation.device.*` fields
- Remove legacy `max_ralph_iterations`
- Update `test-project/.claude/compose-designer.yaml`

### Task 6: Update Create Command Orchestrator
- Add Phase 3: Paparazzi Validation
- Rename existing Phase 3 to Phase 4: Device Validation
- Update phase numbering
- Pass config to both phases

### Task 7: Update Visual Validator Agent
- Rename to clarify it's device validation
- Accept `validation.device.*` config
- Update references

### Task 8: Update Validation Script
- Add checks for test-harness existence
- Add checks for Paparazzi agent
- Add checks for new utilities

### Task 9: Integration Testing
- Test full workflow with Paparazzi + Device
- Verify iteration speedup
- Test config options (disable device, etc.)

---

## Success Criteria

1. **Speed**: Paparazzi iteration < 15s (vs ~60s current)
2. **Accuracy**: Paparazzi catches >90% of issues before device phase
3. **Reliability**: Test harness works without user setup
4. **Backwards compatible**: Existing workflows still work

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Paparazzi rendering differs from device | Device phase as mandatory final verification |
| Test harness Gradle version conflicts | Self-contained wrapper, no dependency on user's Gradle |
| First-run setup slow (Gradle download) | One-time cost, cached afterward |
| Complex Compose features not supported | Fall back to device-only if Paparazzi fails repeatedly |

---

## Future Enhancements

- **Parallel validation**: Run Paparazzi and Device simultaneously
- **Paparazzi-only mode**: For CI/CD without device access
- **Multiple device configs**: Test on different screen sizes via Paparazzi
- **Snapshot management**: Git LFS for golden images
