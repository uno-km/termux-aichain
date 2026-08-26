# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-08-27

### Added
- **Fail-Closed Identity Verification (`ServerIdentityVerifier` / `verifyServerIdentity`)**:
  - Implemented multi-backend verification supporting `termux-aichain`, `llama-server`, `bitnet-server`, and `openai-compatible`.
  - Added capability profiling fallback to query `/v1/models` when upstream endpoints return generic `status: ok`.
  - Added strict fail-closed rejection for unverified model identities.
  - Added verifier dependency injection (`options.identityVerifier`) for automated testing and isolated runtime environments.
- **Direct Tool Authorization Parity**:
  - Direct `create_react_agent` and `createReactAgent` graph factories now enforce `ToolPolicy(default="deny")` by default across both Python and Node.js.
  - Added user approval callback (`approval_callback` / `approvalCallback`) and JSON Schema bounds validation for all tool invocations.
- **Audit Verification Tooling**:
  - Permanently tracked `scripts/generate_master_audit.py` and `scripts/verify_master_audit.py` for deterministic SHA-256 byte-level source code validation.
- **Android Native Diagnostics**:
  - Added kernel sysfs fallback (`/sys/class/power_supply/battery`) for battery monitoring when `termux-api` is not present.

### Changed
- **TypeScript Source of Truth (SSOT)**:
  - Standardized all ESM modules under `js/src/**/*.ts` with automated compilation to `js/esm` and zero-drift verification gates.
- **Unified Package Versioning**:
  - Aligned package version across PyPI (`1.1.0`), npm (`1.1.0`), `pyproject.toml`, and `setup.py`.

### Fixed
- **Upstream Server Capability Matching**:
  - Resolved `expected_service` and `expected_protocol_version` resolution conflicts when connecting to external `llama-server` and `BitNet.cpp` instances.
- **Multi-Model Matching**:
  - Fixed `/v1/models` parsing to inspect all items in the `data` array rather than only the first index.
- **README Encoding & Mojibake**:
  - Restored clean UTF-8 ASCII art banner and standard emojis across documentation files.

### Security
- **Loopback CORS & Payload Bounds**:
  - Enforced loopback-only CORS origin validation and strict `max_body_bytes` limit checking in the 1-line `serve` engine.
  - Replaced string comparisons with `timingSafeEqual` in HTTP Authorization headers.

### Verification
- **Automated Test Coverage**:
  - 153/153 automated tests passed with zero observed failures or errors in the verified test scope (Python: 136 passed, Node.js: 17 passed).
- **Zero-Drift Build Gate**:
  - Validated by `git diff --exit-code -- js/esm` following clean `npm run build`.

---

## [1.0.0] - 2026-08-01

### Added
- Initial sovereign zero-dependency release for Android Termux and edge computing.
- Dual-engine architecture: Pure Python 3.10+ stdlib & Pure Node.js 18+ ESM.
- StateGraph cyclic engine, OpenAI-compatible chat client, SQLite long-term memory, and cosine vector RAG.
