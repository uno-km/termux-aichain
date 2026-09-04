"""
termux_aichain.adapter
=======================
AMEVA Component Protocol v1 — Orchestrator Adapter (v0.8.1 호환)

오케스트레이터 v0.8.1이 ameva.components Entry Point로 탐색합니다.

termux-aichain은 ComponentControl 계층을 갖지 않는 경량 AI 체이닝 프레임워크입니다.
본 어댑터는 패키지 메타데이터와 상태를 직접 관리합니다.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from ameva_component.exceptions import OperationNotSupported

class AIChainOrchestratorAdapter:
    """AIChain Orchestrator Adapter.

    termux-aichain은 LangChain 호환 경량 AI 체이닝 프레임워크로,
    ComponentControl 계층이 없습니다.
    본 어댑터는 ComponentAdapter Protocol 전체 표면을 직접 구현합니다.

    패키지 특성:
    - LLM 서버나 모델 파일을 직접 관리하지 않음 (orchestrate only)
    - instance = LocalAgent 인스턴스 (비상태 요청-응답 단위)
    - activate_model / deactivate_model → OPERATION_NOT_SUPPORTED
    - infer() → OPERATION_NOT_SUPPORTED
      (체이닝 실행은 LocalAgent.run()으로 직접 호출)
    """

    COMPONENT_ID = "termux-aichain"

    def info(self) -> dict[str, Any]:
        """Component Identity — 5대 필수 필드."""
        version = self._get_version()
        return {
            "protocol": "ameva-component-status/1",
            "component_id": self.COMPONENT_ID,
            "component_type": "aichain",
            "version": version,
            "capabilities": [
                "chain.run",
                "agent.local",
                "provider.openai_compatible",
                "provider.bitnet",
            ],
        }

    def health(self) -> dict[str, Any]:
        """경량 진단 — 패키지 import 가능 여부 확인."""
        try:
            import termux_aichain  # noqa: F401
            import os
            return {
                "ok": True,
                "ready": True,
                "degraded": False,
                "component_id": self.COMPONENT_ID,
                "process": {"running": True, "pid": os.getpid(), "verified": True},
                "checks": {"import": "ok"},
            }
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception("Failed to import termux_aichain: %s", exc)
            return {
                "ok": False,
                "ready": False,
                "degraded": True,
                "component_id": self.COMPONENT_ID,
                "process": {
                    "running": False,
                    "pid": None,
                    "verified": False,
                    "inspection_error": {
                        "code": "IMPORT_FAILED",
                        "message": "Component runtime dependency could not be loaded",
                        "cause_type": type(exc).__name__,
                    },
                },
                "checks": {"import": "failed"},
            }

    def models(self) -> dict[str, Any]:
        """termux-aichain은 모델 파일을 직접 관리하지 않습니다."""
        return self._not_supported("models")

    def instances(self) -> dict[str, Any]:
        """LocalAgent는 상태 비저장(stateless) 단위입니다.
        추적 가능한 장기 실행 인스턴스가 없습니다.
        """
        return {
            "ok": True,
            "component_id": self.COMPONENT_ID,
            "instances": [],
            "count": 0,
        }

    async def activate(self, request: dict[str, Any]) -> dict[str, Any]:
        return self._not_supported("activate")

    async def deactivate(self, request: dict[str, Any]) -> dict[str, Any]:
        return self._not_supported("deactivate")

    async def start_instance(self, request: dict[str, Any]) -> dict[str, Any]:
        """LocalAgent는 상태 비저장 단위이므로 start_instance가 해당 없습니다."""
        return self._not_supported("start_instance")

    async def drain_instance(self, instance_id: str) -> dict[str, Any]:
        return self._not_supported("drain_instance")

    async def resume_instance(self, instance_id: str) -> dict[str, Any]:
        return self._not_supported("resume_instance")

    async def stop_instance(self, instance_id: str) -> dict[str, Any]:
        return self._not_supported("stop_instance")

    async def infer(self, request: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        """termux-aichain은 체이닝 프레임워크입니다.
        직접 streaming inference는 미지원 — OperationNotSupported를 발생시킵니다.
        LocalAgent.run()을 직접 호출하십시오.

        P0-2: yield 방식은 상위 소비자가 Frame을 정상으로 처리할 위험이 있어 raise로 변경.
        """
        raise OperationNotSupported(operation="infer", component_id=self.COMPONENT_ID)
        yield  # type: ignore[misc]

    # ── 내부 유틸리티 ──

    def _not_supported(self, operation: str) -> dict[str, Any]:
        """OPERATION_NOT_SUPPORTED 구조화 오류 딕셔너리 반환."""
        return {
            "ok": False,
            "error": {
                "code": "OPERATION_NOT_SUPPORTED",
                "operation": operation,
                "component_id": self.COMPONENT_ID,
                "message": f"{self.COMPONENT_ID} does not support {operation}",
                "retryable": False,
            },
        }

    @staticmethod
    def _get_version() -> str:
        try:
            from termux_aichain import __version__
            return __version__
        except (ImportError, AttributeError):
            return "1.1.1"


def create_adapter() -> AIChainOrchestratorAdapter:
    """Entry Point Factory. 오케스트레이터가 ameva.components 그룹에서 호출합니다."""
    return AIChainOrchestratorAdapter()
