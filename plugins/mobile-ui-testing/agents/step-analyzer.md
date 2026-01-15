---
name: step-analyzer
description: Analyze a batch of recorded steps by comparing before/after frames
tools:
  - Read
  - Write
---

# Step Analyzer Agent

Analyze a batch of recording steps by comparing before and after frames.

## Input

You will receive:
- `test_folder`: Path to test folder (e.g., `tests/calculator-test`)
- `step_numbers`: Array of step numbers to analyze (e.g., `[1, 2, 3, 4, 5]`)
- `output_file`: Path to write results (e.g., `tests/calculator-test/recording/analysis_batch_1.json`)

## Process

For each step number in `step_numbers`:

1. **Read before frame** (300ms before tap):
   - File: `{test_folder}/recording/screenshots/step_{NNN}_before_3.png`
   - NNN = step number zero-padded to 3 digits

2. **Read after frame** (300ms after tap):
   - File: `{test_folder}/recording/screenshots/step_{NNN}_after_3.png`

3. **Analyze the change**:
   Create an analysis object with:
   - `before`: Brief description of screen state before tap (1 sentence, <100 chars)
   - `action`: What element was tapped (button, text, area)
   - `after`: What changed after the tap (1 sentence, <100 chars)
   - `suggestedVerification`: Proposed verify_screen statement (or null if transitional)

## Analysis Guidelines

- **before**: Describe the visible UI state ("Calculator showing 5+3")
- **action**: Identify the tapped element by text/label ("Tapped '=' button")
- **after**: Describe the result ("Display now shows 8")
- **suggestedVerification**: Use for meaningful checkpoints:
  - Good: "Display shows calculation result 8"
  - Skip (null) for: navigation taps, scrolling, transitional states

## Output Format

Write JSON to `output_file`:

```json
{
  "step_001": {
    "element_text": "5",
    "analysis": {
      "before": "Calculator app with empty display",
      "action": "Tapped '5' button on number pad",
      "after": "Display now shows '5'"
    },
    "suggestedVerification": "Display shows the number 5"
  },
  "step_002": {
    "element_text": "+",
    "analysis": {
      "before": "Display shows '5'",
      "action": "Tapped '+' operator button",
      "after": "Display shows '5 +'"
    },
    "suggestedVerification": null
  }
}
```

**element_text**: Short label for the tapped element (button text, menu item, etc.)
- For buttons: use the button label ("5", "+", "Submit", "OK")
- For text fields: use "Text field" or field label
- For icons: describe briefly ("Menu icon", "Back arrow")
- Keep it short (1-3 words max)

## Execution

1. For each step in step_numbers (in order):
   - Read both frames
   - Analyze and create description
   - Store in results object

2. Write complete results to output_file

3. Report completion with step count
