# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [0.1.0] - 2026-08-25

### Added

- Config-driven `pyrightconfig.json` generator with one `executionEnvironment` per package.
- Three discovery providers: `layout` (convention/glob scanning), `manifest` (explicit
  per-package declaration), and `xml` (generic, selector-driven launcher-file discovery).
- Deterministic, timestamp-free output with a `--check` mode for CI drift detection.
- Sample monorepo fixture with vendored duplicate modules, a shared root, an XML-only
  package, and a JS-only package that must be skipped, plus golden expected output for
  all three providers.
