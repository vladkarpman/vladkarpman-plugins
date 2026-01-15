# Preconditions Reference

**Implementation Status:** 🚧 Implementation in progress

Preconditions are named, reusable flows that establish specific app states before tests run. They enable consistent test setup and conditional branching based on app state.

## What is a Precondition?

A precondition represents a known app state, such as:
- `logged_in` - User is authenticated
- `premium_user` - Premium features enabled
- `fresh_install` - App data cleared
- `onboarding_complete` - Tutorial finished

## File Location

```
tests/
├── preconditions/           # Precondition definitions
│   ├── logged_in.yaml
│   ├── premium_user.yaml
│   └── fresh_install.yaml
└── my-test/
    └── test.yaml            # References preconditions
```

## Precondition File Format

```yaml
name: premium_user
description: "App state with premium features enabled"

# Steps to reach this state
steps:
  - launch_app
  - tap: "Debug Menu"
  - tap: "Enable Premium"
  - verify_screen: "Premium badge visible"

# Runtime verification (for if_precondition checks)
verify:
  element: "Premium Badge"
  # OR for complex states:
  # screen: "Dashboard showing premium badge"
```

**Fields:**
- `name` (required): Identifier used to reference this precondition
- `description` (optional): Human-readable explanation
- `steps` (required): Actions to reach this state
- `verify` (required): How to check if state is active at runtime

## Creating Preconditions

**Command:** `/record-precondition {name}`

```
/record-precondition premium_user
→ Recording starts (video + touch capture)
→ User performs steps to reach premium state
/stop-recording
→ Generates tests/preconditions/premium_user.yaml
```

## Using Preconditions

### Single Precondition

```yaml
config:
  app: com.example.app
  precondition: logged_in
```

### Multiple Preconditions (Sequential)

```yaml
config:
  app: com.example.app
  preconditions:
    - fresh_install
    - logged_in
    - premium_user
```

Preconditions run in order, each building on previous state.

## Execution Order

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ fresh_install│ → │  logged_in   │ → │ TEST STEPS   │
└──────────────┘    └──────────────┘    └──────────────┘
```

1. All preconditions run in specified order
2. No app restart between (unless precondition does it)
3. Precondition failure stops test execution
4. Then test steps execute

## Conditional Checking

Use `if_precondition` to branch based on active precondition:

```yaml
- if_precondition: premium_user
  then:
    - tap: "Premium Features"
    - verify_screen: "Full feature list"
  else:
    - verify_screen: "Upgrade prompt"
```

The check uses the precondition's `verify` section:
- If `verify.element` specified: Check if element is present
- If `verify.screen` specified: AI vision check against description

## Best Practices

**DO:**
- Keep preconditions focused (one state per precondition)
- Use descriptive names (`logged_in_as_admin` vs `admin`)
- Include verification step in precondition to confirm state
- Use `verify.element` for fast checks, `verify.screen` for complex states

**DON'T:**
- Create overly complex preconditions (split into multiple)
- Skip the `verify` section (needed for `if_precondition`)
- Chain too many preconditions (consider separate test files)
