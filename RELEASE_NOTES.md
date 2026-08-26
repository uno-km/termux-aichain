# 📦 Termux-AIChain v1.1.0 릴리즈 노트

> **Release Date**: 2026-08-27  
> **Release Tag**: `aichain-v1.1.0` (Git: `v1.1.0`)  
> **Security Audit & Verification**: 153/153 Automated Tests Passed (Zero Observed Failures or Errors)

---

## 🚀 Key Highlights (주요 핵심 요약)
- **Fail-Closed 신원 검증 & Upstream Capability 매칭**: `llama-server`, `BitNet.cpp` 및 OpenAI 호환 백엔드 연결 시 다중 모델 열거 및 엄격한 모델 식별자 검증 지원
- **도구 권한 정책(ToolPolicy) 동등성**: Python 및 Node.js 전반에서 `ToolPolicy(default="deny")`, JSON Schema 파라미터 유효성 검사, 사용자 승인 콜백 적용
- **TypeScript SSOT & Zero-Drift 빌드 확립**: `js/src/**/*.ts`를 단일 진실 공급원으로 통일하고 ESM 배포 산출물과의 Zero-Drift 검증 완료

---

## 📋 Changelog (상세 변경 내역)

### ✨ Features (신규 기능)
- **Fail-Closed 신원 검증기 (`ServerIdentityVerifier` / `verifyServerIdentity`)**:
  - `termux-aichain`, `llama-server`, `bitnet-server`, `openai-compatible` 다중 백엔드 지원.
  - `/health` 응답이 generic `status: "ok"`인 경우 `/v1/models` 엔드포인트 조회를 통한 capability fallback 판별.
  - 테스트 및 격리 환경을 위한 Verifier Dependency Injection (`options.identityVerifier`) 지원.
- **도구 권한 통제 보안 모델**:
  - `create_react_agent` / `createReactAgent` 호출 시 `ToolPolicy(default="deny")` 기본 적용.
  - 도구 인자 JSON Schema strict 검증 및 사용자 승인 비동기 콜백(`approval_callback` / `approvalCallback`) 내장.
- **Android 네이티브 진단 Fallback**:
  - `termux-api` 부재 시 리눅스 커널 sysfs(`/sys/class/power_supply/battery`) 직접 조회 지원.

### 🐛 Bug Fixes (버그 및 호환성 패치)
- **Upstream 서버 연결 충돌 해결**: `LocalAgent.local()` 및 `cmd_status`의 프로토콜 버전 하드코딩 제거 및 프로파일 기반 capability 매칭 일원화.
- **다중 모델 탐색 개선**: `/v1/models`의 `data` 배열 전체를 검색하여 복수 모델이 로드된 서버에서도 `expected_model_id` 정상 판별.
- **README 인코딩 복구**: 문서 내 ASCII 배너 및 이모지의 UTF-8 인코딩 손상(mojibake) 전면 복구.

### ⚡ Performance & Security (성능 최적화 및 보안)
- **루프백 CORS & 페이로드 제한**: 1-Line `serve` 엔진에 엄격한 루프백 URL 검증, `max_body_bytes` 초과 시 413 반환, constant-time `timingSafeEqual` 토큰 비교 적용.
- **메모리 및 구동 성능**: Cold Start 12.8ms, RSS 14.2MB, 패키지 크기 268KB 유지 (Zero External Dependencies).

---

## 📦 Package Distribution & Verification

| 플랫폼 | 패키지명 | 설치 명령어 | 체크섬 (SHA-256) |
|:---|:---|:---|:---|
| **npm** | `termux-aichain` | `npm install termux-aichain@1.1.0` | `a0f719bf419908ece841c02924561fa008eaca28348c7ee296151550f82298c1` |
| **PyPI (wheel)** | `termux-aichain` | `pip install termux-aichain==1.1.0` | `d53fbab4694ccc43acc1f222f1f02b2236ef8c3a6f6369bcc54d8c68dbada1a1` |
| **PyPI (sdist)** | `termux-aichain` | `pip install termux-aichain==1.1.0` | `f7587ee3a226e3ef7cd00fd0ec2be6ad8e0fd0e8612dd3c2b1e831ff90d2fe07` |

---

## 🔗 Official Documentation
- **Official Docs**: [https://uno-km.vercel.app/lib/aichain/](https://uno-km.vercel.app/lib/aichain/)
- **API Reference**: [https://uno-km.vercel.app/lib/aichain/](https://uno-km.vercel.app/lib/aichain/)
