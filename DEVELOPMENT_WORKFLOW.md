# Development Workflow Guide

This document outlines the development workflow for the Smart Envi integration.

## Branch Strategy

### Main Branches

- **`main`**: Stable, production-ready code. Only contains released versions.
- **`develop`**: Main development branch. Ongoing work and experiments happen here.

### Feature/Fix Branches

Create branches from `develop` for specific work:

- **`feature/description`**: New features (e.g., `feature/schedule-improvements`)
- **`fix/description`**: Bug fixes (e.g., `fix/temperature-validation`)
- **`experiment/description`**: Experimental changes (e.g., `experiment/new-api-endpoint`)

## Daily Workflow

### Starting New Work

```bash
# 1. Switch to develop and get latest changes
git checkout develop
git pull origin develop

# 2. Create a new branch for your work
git checkout -b feature/my-new-feature
# or
git checkout -b fix/bug-description
# or
git checkout -b experiment/testing-something
```

### Making Changes

```bash
# Make your changes, then commit
git add .
git commit -m "Description of changes"

# Push your branch
git push -u origin feature/my-new-feature
```

### Merging Back to Develop

```bash
# Switch back to develop
git checkout develop
git pull origin develop

# Merge your feature branch
git merge feature/my-new-feature

# Push develop
git push origin develop

# Optionally delete the feature branch locally
git branch -d feature/my-new-feature
```

## Release Workflow

When ready to create a new release:

### 1. Prepare Release

```bash
# Make sure develop is up to date
git checkout develop
git pull origin develop

# Merge develop into main
git checkout main
git pull origin main
git merge develop
```

### 2. Update Version

- Update `custom_components/smart_envi/manifest.json` version number
- Create `RELEASE_NOTES_vX.X.X.md` with changelog

### 3. Create Release

```bash
# Commit version changes
git add .
git commit -m "Bump version to vX.X.X"

# Create tag and push
git tag vX.X.X
git push origin main --tags

# Create GitHub release
gh release create vX.X.X --title "vX.X.X - Release Title" --notes-file RELEASE_NOTES_vX.X.X.md
```

### 4. Continue Development

```bash
# Switch back to develop to continue work
git checkout develop
```

## Version Numbering

- **Major (X.0.0)**: Breaking changes, major rewrites
- **Minor (0.X.0)**: New features, backward compatible
- **Patch (0.0.X)**: Bug fixes, small improvements

Examples:
- `2.0.0` → `2.1.0` (new feature)
- `2.1.0` → `2.1.1` (bug fix)
- `2.1.0` → `3.0.0` (breaking change)

## Best Practices

1. **Keep main stable**: Never commit directly to `main` except during releases
2. **Regular commits**: Commit often with clear messages
3. **Test before merging**: Test your changes before merging to `develop`
4. **Clean up branches**: Delete feature branches after merging
5. **Update documentation**: Keep README and docs updated with changes

## Current Status

- **Stable Release**: v2.0.0 (on `main`)
- **Development Branch**: `develop` (ongoing work)

## Quick Reference

```bash
# Create feature branch
git checkout develop && git pull && git checkout -b feature/name

# Commit and push
git add . && git commit -m "Message" && git push -u origin feature/name

# Merge to develop
git checkout develop && git pull && git merge feature/name && git push

# Create release
git checkout main && git merge develop && git tag vX.X.X && git push --tags
```

