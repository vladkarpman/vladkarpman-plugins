---
name: scan-components
description: Scan codebase for reusable Compose components and update config
argument-hint: [--path <scan-path>]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# Compose Designer: Scan Components

Scan the codebase for `@Composable` functions and generate the `component_library` section in config.

## Usage

```bash
# Scan default paths from config
/compose-design scan-components

# Scan specific directory
/compose-design scan-components --path app/src/main/java/ui/components
```

## Instructions for Claude

### Step 1: Load Configuration

```bash
if [ ! -f .claude/compose-designer.yaml ]; then
  echo "Configuration not found. Run: /compose-design config"
  exit 1
fi
```

Read config to get `output.default_output_dir` for default scan path.

### Step 2: Determine Scan Path

```bash
# Use --path argument if provided, otherwise use config default
scan_path="${path_arg:-${config.output.default_output_dir}}"

if [ ! -d "$scan_path" ]; then
  echo "Scan path not found: $scan_path"
  exit 1
fi

echo "Scanning: $scan_path"
```

### Step 3: Find Composable Functions

Use Grep to find all `@Composable` function declarations:

```bash
# Find all @Composable fun declarations
grep -r "@Composable" "$scan_path" --include="*.kt" -A 2 | \
  grep -E "^[^:]+:fun [A-Z]" | \
  sed 's/:fun /|/' | \
  sort -u
```

Parse results to extract:
- File path
- Function name
- Parameters (signature)

### Step 4: Categorize Components

Group components by inferred type based on naming:

**Buttons:** Names containing "Button"
**Cards:** Names containing "Card"
**Inputs:** Names containing "Field", "Input", "TextField"
**Lists:** Names containing "List", "Item", "Row"
**Other:** Everything else

### Step 5: Generate use_when Hints

Infer `use_when` from function name:

| Name pattern | use_when hint |
|--------------|---------------|
| `PrimaryButton` | "primary action, main CTA" |
| `SecondaryButton` | "secondary action, alternative" |
| `OutlinedButton` | "outlined style, less emphasis" |
| `IconButton` | "icon-only button, toolbar" |
| `TextButton` | "text-only, minimal emphasis" |
| `Card`, `ContentCard` | "card container, elevated content" |
| `TextField`, `Input` | "text input, form field" |
| `SearchBar` | "search input, query" |
| Names with "Item" | "list item, repeated element" |

For unrecognized patterns, use generic: "reusable component"

### Step 6: Build Component Library YAML

Generate YAML structure:

```yaml
component_library:
  buttons:
    - name: "{FunctionName}"
      import: "{package}.{FunctionName}"
      use_when: "{inferred_hint}"
      signature: "{extracted_signature}"

  cards:
    - name: "..."
      ...

  inputs:
    - name: "..."
      ...

  other:
    - name: "..."
      ...
```

### Step 7: Update Config File

Read existing `.claude/compose-designer.yaml`.

If `component_library:` section exists:
- Ask user: "Component library exists. Overwrite? [Y/n]"
- If no, exit

Append or replace `component_library:` section.

Write updated config using Write tool.

### Step 8: Report Results

```
Scanned: {scan_path}
Found: {total_count} reusable components

Component Library:
  - Buttons: {button_count}
  - Cards: {card_count}
  - Inputs: {input_count}
  - Other: {other_count}

Updated: .claude/compose-designer.yaml

Next steps:
  1. Review component_library section
  2. Adjust use_when hints for accuracy
  3. Remove components you don't want reused
```

## Error Handling

**No composables found:**
```
No @Composable functions found in: {scan_path}

Check:
  - Path contains Kotlin files
  - Files have @Composable annotations
  - You're scanning the right directory

Try: /compose-design scan-components --path <correct-path>
```

**Config write fails:**
```
Cannot write to .claude/compose-designer.yaml

Check permissions and try again.
```
