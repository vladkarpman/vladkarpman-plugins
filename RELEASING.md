# Release Workflow

This document describes how to release new versions of plugins in the marketplace.

## Overview

The marketplace uses automated version syncing and release creation through GitHub Actions. The workflow ensures that:

1. Plugin versions in `plugin.json` are the source of truth
2. Marketplace catalog (`marketplace.json`) stays in sync automatically
3. Releases are created with proper changelogs

## Releasing a Plugin Update

### Quick Release (Recommended)

Just update the plugin version and push - everything else is automatic:

```bash
# 1. Update plugin version
vim plugins/mobile-ui-testing/.claude-plugin/plugin.json
# Change: "version": "3.3.2" → "3.3.3"

# 2. Commit and push
git add plugins/mobile-ui-testing/.claude-plugin/plugin.json
git commit -m "feat(mobile-ui-testing): add new feature"
git push origin main

# 3. GitHub Actions automatically:
#    ✅ Syncs marketplace.json
#    ✅ Creates release tag
#    ✅ Generates changelog
#    ✅ Publishes GitHub release
```

That's it! The entire release process is automated.

### Manual Sync (Optional)

If you want to preview changes before pushing:

```bash
# 1. Update plugin version
vim plugins/mobile-ui-testing/.claude-plugin/plugin.json

# 2. Run sync script locally
./scripts/sync-versions.sh

# 3. Review changes
git diff .claude-plugin/marketplace.json

# 4. Commit and push both files
git add plugins/mobile-ui-testing/.claude-plugin/plugin.json
git add .claude-plugin/marketplace.json
git commit -m "feat(mobile-ui-testing): add new feature"
git push origin main
```

### Semantic Versioning

Follow [semantic versioning](https://semver.org/) for plugin updates:
- **Patch** (1.0.0 → 1.0.1): Bug fixes, no breaking changes
- **Minor** (1.0.0 → 1.1.0): New features, backward compatible
- **Major** (1.0.0 → 2.0.0): Breaking changes

The marketplace version is automatically managed and will auto-increment if needed.

## Marketplace Version Updates

The marketplace version in `.claude-plugin/marketplace.json` (`metadata.version`) should be bumped when:
- Adding new plugins
- Removing plugins
- Changing marketplace metadata

Individual plugin version changes don't require marketplace version bumps.

## Manual Release Creation

To force a release manually:

```bash
# Via GitHub UI: Actions → Auto Release → Run workflow → Check "Force release"

# Or via gh CLI:
gh workflow run auto-release.yml -f force=true
```

## Version Sync Automation

The `auto-release.yml` workflow runs when:
- You push changes to `plugins/*/.claude-plugin/plugin.json`
- You manually trigger it (Actions → Auto Release → Run workflow)

### What It Does Automatically

1. **Syncs Versions**: Reads plugin.json files and updates marketplace.json
2. **Handles Conflicts**: If release tag exists, auto-bumps marketplace patch version
3. **Creates Release**: Generates tag, changelog, and GitHub release
4. **Notifies**: Adds summary to Actions tab showing what was released

### The Complete Flow

```
Plugin version change → Push to main
  ↓
Auto-release workflow triggers
  ↓
Sync plugin versions to marketplace.json
  ↓
Check if marketplace version tag exists
  ↓ (if exists)
Auto-bump marketplace patch version
  ↓
Commit marketplace.json
  ↓
Create git tag
  ↓
Generate changelog from commits
  ↓
Create GitHub release
  ↓
Done! Users can update their plugins
```

## Local Development

### Pre-commit Hook (Optional)

To automatically sync versions before each commit:

```bash
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
./scripts/sync-versions.sh
git add .claude-plugin/marketplace.json
EOF

chmod +x .git/hooks/pre-commit
```

### Testing Plugin Changes

```bash
# Load plugin locally for testing
claude --plugin-dir ./plugins/mobile-ui-testing

# Or install from local marketplace
claude plugin marketplace add file://$(pwd)
claude plugin install mobile-ui-testing@vladkarpman-plugins
```

## Users Getting Updates

### Automatic Updates

Users can update all marketplace plugins:

```bash
# Update marketplace catalogs
claude plugin marketplace update

# Update all installed plugins
claude plugin update
```

### Version Pinning

Users can pin specific versions:

```bash
# Install specific version
claude plugin install mobile-ui-testing@3.3.1

# Update to latest
claude plugin install mobile-ui-testing@latest
```

## Troubleshooting

### Version Mismatch Detected

If GitHub Actions reports version mismatch:

```bash
./scripts/sync-versions.sh
git add .claude-plugin/marketplace.json
git commit --amend --no-edit
git push --force-with-lease
```

### Release Tag Already Exists

The workflow automatically handles this by bumping the marketplace patch version. No manual intervention needed.

If you want to force a specific version:

```bash
# Delete local and remote tag
git tag -d v1.2.0
git push origin :refs/tags/v1.2.0

# Update marketplace version manually
vim .claude-plugin/marketplace.json
git commit -am "chore: bump marketplace version"
git push

# Trigger workflow again
gh workflow run auto-release.yml
```

## Best Practices

1. **Always test locally** before pushing version bumps
2. **Write meaningful commit messages** - they appear in changelog
3. **Update plugin README** when releasing major changes
4. **Coordinate breaking changes** - communicate with users first
5. **Use semantic versioning** - helps users understand impact

## Example Release Flow

```bash
# 1. Make changes to plugin
vim plugins/mobile-ui-testing/commands/run-test.md

# 2. Update plugin version
vim plugins/mobile-ui-testing/.claude-plugin/plugin.json
# Change: "version": "3.3.2" → "3.3.3"

# 3. Commit and push ONLY the plugin.json
git add plugins/mobile-ui-testing/.claude-plugin/plugin.json
git commit -m "feat(mobile-ui-testing): add retry logic to run-test"
git push origin main

# 4. Watch the magic happen! 🎉
# GitHub Actions will:
#   - Sync marketplace.json
#   - Create release v1.2.1 (or bump if needed)
#   - Generate changelog
#   - Publish release

# Done! Users can now update with: claude plugin update
```
