# Changelog

All notable changes to 	ermux-aichain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.4] - 2026-09-05

### Changed
- Synchronized unified orchestration dependencies and ecosystem service telemetry.
- Validated full-stack zero-regression test suite compatibility.

---

## [1.1.3] - 2026-09-05

### Changed
- Migrated hardware acceleration dependency to unified `ameva-runtime>=2.0.0` and `@ameva/runtime>=2.0.0`.
- Enhanced chain execution error reporting with fail-fast validation.

---

## [1.1.1] - 2026-09-02

### Added
- **Graph Agent Workflow**: State-graph based local autonomous agent orchestration.
- **Hardware Diagnostics Tools**: Native sensor, battery, and network telemetry bindings for Termux:API.

### Fixed
- **Subprocess Error Logging**: Eliminated exception black hole in _run_cmd with explicit TimeoutExpired, FileNotFoundError, and PermissionError logging.
- **Termux API Service Monitor**: Added returncode inspection and warning logs in _ensure_termux_api_service_alive.

### Verification
- **Unit Tests**: 136 / 136 passed with 100% assertion coverage.