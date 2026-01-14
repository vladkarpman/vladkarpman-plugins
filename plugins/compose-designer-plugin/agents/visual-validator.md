---
description: Validates generated Compose UI against design baseline using LLM Vision as the primary validation mechanism, with SSIM as a secondary logging metric
capabilities:
  - Deploy APK to connected Android device via mobile-mcp
  - Capture device screenshots for comparison
  - Extract component bounds from view hierarchy using testTag
  - Perform LLM Vision-based visual comparison (primary validation)
  - Calculate SSIM similarity score (secondary, logging only)
  - Apply targeted fixes based on LLM feedback
  - Invoke baseline-preprocessor for frame detection and cropping
  - Iterate until LLM approves or max iterations reached
model: opus
color: blue
tools:
  - Read
  - Edit
  - Bash
  - mcp__mobile-mcp__mobile_list_available_devices
  - mcp__mobile-mcp__mobile_install_app
  - mcp__mobile-mcp__mobile_launch_app
  - mcp__mobile-mcp__mobile_terminate_app
  - mcp__mobile-mcp__mobile_take_screenshot
  - mcp__mobile-mcp__mobile_save_screenshot
  - mcp__mobile-mcp__mobile_list_elements_on_screen
---

# Visual Validator Agent

Validates generated Compose code against design baseline through iterative device-based refinement using LLM Vision as the primary validation mechanism.

## Core Principle

**LLM Vision is the primary validation mechanism.** SSIM is calculated for logging and monitoring purposes only - it does NOT drive iteration decisions. The LLM's visual assessment determines whether to PASS, ITERATE, or mark as STUCK.

## Input Contract

**Required inputs from parent command:**

```
- kotlin_file_path: Path to generated .kt file to validate
- baseline_image_path: Path to original design baseline PNG
- preprocessed_baseline_path: (optional) Path to already preprocessed baseline
- component_name: Name of component (used for testTag lookup)
- package_name: Android app package name
- temp_dir: Directory for artifacts (screenshots, diffs, hierarchy)
- config: Configuration object containing:
  - validation.visual_similarity_threshold: Base threshold (default: 0.92)
  - validation.max_ralph_iterations: Loop limit (default: 8)
  - validation.ssim_sanity_threshold: Warning threshold (default: 0.70)
  - validation.primary_method: Should be "llm_vision" (default)
```

## Output Contract

**Return JSON structure:**

```json
{
  "status": "SUCCESS | STUCK | MAX_ITERATIONS",
  "llm_verdict": "PASS | ITERATE | STUCK",
  "llm_confidence": "HIGH | MEDIUM | LOW",
  "iterations": 3,
  "ssim_history": [0.42, 0.67, 0.81],
  "final_ssim": 0.81,
  "summary": "LLM assessment summary of final state",
  "issues_fixed": ["Adjusted button padding from 8dp to 16dp", "Changed text color to match design"],
  "screenshots": ["iteration-1.png", "iteration-2.png", "iteration-3.png"],
  "sanity_warning": false
}
```

## Workflow

### Phase 0: Setup and Preprocessing

**Step 1: Validate inputs**

```bash
# Verify Kotlin file exists
if [ ! -f "{kotlin_file_path}" ]; then
    echo "Error: Kotlin file not found: {kotlin_file_path}" >&2
    exit 1
fi

# Verify baseline exists
if [ ! -f "{baseline_image_path}" ]; then
    echo "Error: Baseline image not found: {baseline_image_path}" >&2
    exit 1
fi

# Create temp directory
mkdir -p "{temp_dir}"
```

**Step 2: Preprocess baseline (if not already done)**

If `preprocessed_baseline_path` is NOT provided, invoke the baseline-preprocessor agent:

```
Task tool invocation:
  - subagent_type: "compose-designer:baseline-preprocessor"
  - description: "Preprocess baseline image to detect device frames and crop to content"
  - prompt: |
      Preprocess the baseline image for visual validation.

      Inputs:
      - baseline_path: {baseline_image_path}
      - temp_dir: {temp_dir}
      - config_threshold: {config.validation.visual_similarity_threshold}

      Analyze the image for device frames, composite layouts, and missing assets.
      Crop to content area and calculate recommended threshold.
      Write results to {temp_dir}/preprocessing-output.json
```

After preprocessing completes, read the output:

```bash
# Read preprocessing results
cat "{temp_dir}/preprocessing-output.json"
```

Extract:
- `cropped_image_path` → Use as preprocessed baseline for comparisons
- `recommended_threshold` → Use for sanity check reference
- `metadata.missing_asset_descriptions` → Log expected gaps

If `preprocessed_baseline_path` IS provided, use it directly:

```bash
preprocessed_baseline="{preprocessed_baseline_path}"
```

**Step 3: Initialize tracking variables**

```
iteration = 0
max_iterations = {config.validation.max_ralph_iterations or 8}
ssim_history = []
issues_fixed = []
screenshots = []
llm_verdict = "ITERATE"
llm_confidence = "MEDIUM"
sanity_threshold = {config.validation.ssim_sanity_threshold or 0.70}
```

### Phase 1: Validation Loop

**REPEAT** the following steps while `llm_verdict == "ITERATE"` AND `iteration < max_iterations`:

---

#### Step 4: Build APK

```bash
# Build debug APK
./gradlew assembleDebug 2>&1

# Check build result
if [ $? -ne 0 ]; then
    echo "Build failed - check compilation errors"
    exit 1
fi

# Verify APK exists
apk_path="app/build/outputs/apk/debug/app-debug.apk"
if [ ! -f "$apk_path" ]; then
    echo "APK not found at expected path: $apk_path"
    # Try to find APK
    find . -name "*.apk" -path "*/debug/*" 2>/dev/null | head -5
fi
```

If build fails:
1. Read compile errors
2. Attempt to fix obvious issues (missing imports, typos)
3. If unfixable, exit with STUCK status

---

#### Step 5: Deploy to Device

**List available devices:**

```
mcp__mobile-mcp__mobile_list_available_devices()
```

Select the first available device (or use `config.testing.device_id` if specified).

**Install APK:**

```
mcp__mobile-mcp__mobile_install_app(
  device: {selected_device_id},
  path: "app/build/outputs/apk/debug/app-debug.apk"
)
```

**Launch app:**

```
mcp__mobile-mcp__mobile_launch_app(
  device: {selected_device_id},
  packageName: {package_name}
)
```

Wait 3 seconds for app to render fully.

---

#### Step 6: Capture Screenshot

```
mcp__mobile-mcp__mobile_save_screenshot(
  device: {selected_device_id},
  saveTo: "{temp_dir}/iteration-{iteration}.png"
)
```

Add to screenshots list:
```
screenshots.append("iteration-{iteration}.png")
```

---

#### Step 7: Extract Component Bounds

**Get view hierarchy:**

```
hierarchy = mcp__mobile-mcp__mobile_list_elements_on_screen(
  device: {selected_device_id}
)
```

**Save hierarchy to file:**

```bash
echo '{hierarchy_json}' > "{temp_dir}/hierarchy-{iteration}.json"
```

**Extract component bounds using testTag:**

```bash
bounds_json=$(python3 "${CLAUDE_PLUGIN_ROOT}/utils/extract-component-bounds.py" \
  "{temp_dir}/hierarchy-{iteration}.json" \
  "{component_name}")

echo "Bounds extraction result: $bounds_json"
```

**Parse bounds and crop screenshot:**

```bash
found=$(echo "$bounds_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('found', False))")

if [ "$found" = "True" ]; then
    x=$(echo "$bounds_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['x'])")
    y=$(echo "$bounds_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['y'])")
    width=$(echo "$bounds_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['width'])")
    height=$(echo "$bounds_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['height'])")

    python3 "${CLAUDE_PLUGIN_ROOT}/utils/crop-image.py" \
      "{temp_dir}/iteration-{iteration}.png" \
      "{temp_dir}/cropped-{iteration}.png" \
      "$x" "$y" "$width" "$height"

    cropped_screenshot="{temp_dir}/cropped-{iteration}.png"
else
    echo "Warning: Component bounds not found for testTag '{component_name}'"
    echo "Using full screenshot for comparison"
    cropped_screenshot="{temp_dir}/iteration-{iteration}.png"
fi
```

If component not found:
- Log warning about missing testTag
- Use full screenshot as fallback
- Consider this a potential issue to address

---

#### Step 8: LLM Vision Validation (PRIMARY)

This is the **primary validation mechanism**. Load and apply the prompt template from `prompts/llm-vision-validation.md`.

**Read both images visually:**
1. Read `{preprocessed_baseline}` - the design baseline (cropped to content)
2. Read `{cropped_screenshot}` - the device screenshot (cropped to component)

**Apply evaluation criteria from the prompt:**

Evaluate against these criteria (in priority order):

1. **Layout Structure (Critical)**
   - Are elements positioned correctly relative to each other?
   - Is the visual hierarchy preserved?
   - Are nested containers structured properly?

2. **Typography (Important)**
   - Are font sizes approximately correct?
   - Is font weight (bold/regular) correct?
   - Is text alignment correct?

3. **Colors & Theming (Important)**
   - Do colors match or align with Material theme conventions?
   - Are accent colors in the right places?
   - Is contrast appropriate?

4. **Spacing (Moderate)**
   - Are margins and padding approximately correct?
   - Is element spacing consistent?
   - Minor pixel differences are acceptable.

5. **Content Completeness (Critical)**
   - Is all visible content from the design present?
   - Are icons/images in correct positions?
   - Is text content accurate?

**Acceptable differences (do NOT flag these):**
- Minor pixel variations (up to 5px)
- Platform-specific rendering (antialiasing, shadows)
- Material theme color adaptation
- System font substitution
- Status bar / navigation bar differences

**Generate structured assessment:**

```json
{
  "status": "PASS | ITERATE | STUCK",
  "confidence": "HIGH | MEDIUM | LOW",
  "summary": "One sentence overall assessment",
  "issues": [
    {
      "severity": "critical | important | minor",
      "category": "layout | typography | colors | spacing | content",
      "description": "Specific issue description",
      "fix": "Exact code change to make"
    }
  ],
  "reasoning": "If STUCK, explain why this cannot be fixed with code changes"
}
```

**Status definitions:**
- **PASS**: Implementation matches design intent. Only minor acceptable differences.
- **ITERATE**: Fixable issues found. Apply suggested fixes and re-validate.
- **STUCK**: Fundamental mismatch that cannot be resolved with code changes (e.g., missing assets, wrong design reference, hardware limitations).

Store the verdict:
```
llm_verdict = {status}
llm_confidence = {confidence}
llm_summary = {summary}
llm_issues = {issues}
```

---

#### Step 9: SSIM Calculation (SECONDARY - Logging Only)

Calculate SSIM for monitoring and logging purposes. **This does NOT affect iteration decisions.**

```bash
ssim=$(python3 "${CLAUDE_PLUGIN_ROOT}/utils/image-similarity.py" \
  "{preprocessed_baseline}" \
  "{cropped_screenshot}" \
  --output "{temp_dir}/diff-{iteration}.png")

echo "Iteration {iteration}: SSIM = $ssim, LLM verdict = {llm_verdict}"
```

Append to history:
```
ssim_history.append({ssim})
```

Log the iteration:
```
Iteration {iteration} Summary:
  - LLM Verdict: {llm_verdict} ({llm_confidence} confidence)
  - SSIM Score: {ssim} (for reference only)
  - Summary: {llm_summary}
  - Issues found: {len(llm_issues)}
```

---

#### Step 10: Handle LLM Verdict

**If `llm_verdict == "PASS"`:**

Check SSIM sanity:
```
if ssim < sanity_threshold:
    sanity_warning = true
    log("Warning: LLM approved but SSIM ({ssim}) is below sanity threshold ({sanity_threshold})")
    log("This may indicate a visual mismatch the LLM overlooked")
else:
    sanity_warning = false
```

Exit loop with SUCCESS status.

**If `llm_verdict == "ITERATE"`:**

Apply each fix from the LLM assessment:

```
for issue in llm_issues:
    if issue.fix:
        # Read current Kotlin file
        # Apply the suggested fix using Edit tool
        # Track what was fixed
        issues_fixed.append(issue.description)
```

Example fix application:
```
Edit tool:
  file_path: {kotlin_file_path}
  old_string: "padding = 8.dp"
  new_string: "padding = 16.dp"
```

Increment iteration counter and continue loop.

**If `llm_verdict == "STUCK"`:**

Exit loop with STUCK status:
```
stuck_reason = llm_issues[0].reasoning if llm_issues else "Unknown reason"
log("Validation stuck: {stuck_reason}")
```

---

#### Step 11: Check Iteration Limit

If `iteration >= max_iterations` AND `llm_verdict != "PASS"`:

```
status = "MAX_ITERATIONS"
log("Maximum iterations ({max_iterations}) reached without achieving PASS")
log("Final LLM verdict: {llm_verdict}")
log("Final SSIM: {ssim_history[-1]}")
```

Exit loop.

---

### Phase 2: Cleanup and Report

**Step 12: Terminate app**

```
mcp__mobile-mcp__mobile_terminate_app(
  device: {selected_device_id},
  packageName: {package_name}
)
```

**Step 13: Generate final report**

Determine final status:
```
if llm_verdict == "PASS":
    status = "SUCCESS"
elif llm_verdict == "STUCK":
    status = "STUCK"
else:
    status = "MAX_ITERATIONS"
```

**Output JSON result:**

```json
{
  "status": "{status}",
  "llm_verdict": "{llm_verdict}",
  "llm_confidence": "{llm_confidence}",
  "iterations": {iteration},
  "ssim_history": [{ssim_history}],
  "final_ssim": {ssim_history[-1]},
  "summary": "{llm_summary}",
  "issues_fixed": [{issues_fixed}],
  "screenshots": [{screenshots}],
  "sanity_warning": {sanity_warning}
}
```

**Human-readable summary:**

```
Visual Validation Complete
==========================

Status: {status}
LLM Verdict: {llm_verdict} ({llm_confidence} confidence)
Iterations: {iteration}

SSIM History (for reference):
{for i, ssim in enumerate(ssim_history):}
  Iteration {i+1}: {ssim:.4f}
{end for}

{if status == "SUCCESS":}
Implementation matches design intent.
{if sanity_warning:}
Warning: SSIM ({final_ssim:.4f}) is below sanity threshold ({sanity_threshold}).
         Consider manual review to verify visual accuracy.
{end if}
{end if}

{if status == "STUCK":}
Unable to fix: {stuck_reason}
Recommendation: Review the design baseline and generated code manually.
{end if}

{if status == "MAX_ITERATIONS":}
Could not achieve LLM approval within {max_iterations} iterations.
Final state may be acceptable - manual review recommended.
{end if}

Issues Fixed:
{for issue in issues_fixed:}
  - {issue}
{end for}

Artifacts:
  - Screenshots: {temp_dir}/iteration-*.png
  - Diff images: {temp_dir}/diff-*.png
  - View hierarchies: {temp_dir}/hierarchy-*.json
  - Cropped screenshots: {temp_dir}/cropped-*.png
```

## Error Handling

### Build Failure

```
Build failed during iteration {iteration}

Error output:
{gradle_error}

Attempting automatic fix...
{if fixable:}
  Fixed: {what_was_fixed}
  Retrying build...
{else:}
  Cannot automatically fix build errors.

  Common issues:
  1. Missing imports - add required import statements
  2. Type mismatch - check parameter types
  3. Unresolved reference - verify all referenced symbols exist

  Manual intervention required.

  Exiting with STUCK status.
{end if}
```

### Device Not Available

```
No Android devices found

Requirements:
  - USB debugging enabled on physical device, OR
  - Android emulator running

Check:
  - adb devices (should show device)
  - Emulator: Android Studio -> AVD Manager -> Start

Exiting with STUCK status.
```

### Component Bounds Not Found

```
Warning: Component testTag '{component_name}' not found in view hierarchy

Possible causes:
  1. testTag not applied to root composable
  2. Component name mismatch (expected: {component_name})
  3. App not fully rendered

Actions taken:
  - Using full screenshot for comparison (less accurate)

Recommendation:
  - Verify testTag is applied: .testTag("{component_name}")
  - Ensure testTag matches component name exactly
```

### SSIM Sanity Warning

```
Warning: LLM approved but SSIM is low

LLM verdict: PASS ({llm_confidence} confidence)
SSIM score: {final_ssim:.4f}
Sanity threshold: {sanity_threshold}

This discrepancy may indicate:
  1. LLM overlooked significant differences
  2. Baseline preprocessing artifacts
  3. Device rendering differences

Recommendation:
  - Review screenshots manually: {temp_dir}/
  - Compare diff images for visual differences
  - Consider adjusting sanity_threshold if this is expected
```

## Best Practices

### LLM Vision Assessment

**Be systematic:** Compare images element by element, from top to bottom.

**Be specific:** When identifying issues, provide exact values:
- "Button padding is 8dp, should be 16dp" (good)
- "Padding looks wrong" (too vague)

**Be practical:** Only flag issues that can be fixed with code changes:
- "Text color is wrong" -> Fixable
- "Image asset is different" -> Not fixable (STUCK)

**Be consistent:** Apply the same standards across iterations.

### Fix Application

**One fix at a time:** Apply fixes in priority order (critical first).

**Verify fix applicability:** Before editing, confirm the old_string exists.

**Track all changes:** Log every modification for the issues_fixed list.

### Iteration Efficiency

**Early exit:** If LLM says PASS, exit immediately (don't wait for SSIM).

**Stuck detection:** If the same issues appear 3+ times, consider STUCK.

**Fix quality:** Prefer precise fixes over speculative changes.

## Integration Notes

### Upstream (from design-generator)

Expects:
- Generated .kt file with testTag applied to root composable
- Baseline image (original or preprocessed)
- Component name matching testTag

### Downstream (to device-tester or parent command)

Provides:
- Validated .kt file (with fixes applied)
- Screenshot history for documentation
- SSIM metrics for trend analysis
- Pass/fail status for workflow control

### Baseline Preprocessor Integration

If preprocessing not done upstream:
1. Invoke baseline-preprocessor agent
2. Wait for `preprocessing-output.json`
3. Use `cropped_image_path` for comparisons
4. Apply `recommended_threshold` for sanity checks
