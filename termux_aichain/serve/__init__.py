"""
==============================================================================
termux-aichain Serve Module Exports (LangServe Alternative)
==============================================================================
"""

from termux_aichain.serve.server import AgentServer, serve
from termux_aichain.serve.dashboard import DASHBOARD_HTML

__all__ = [
    "AgentServer",
    "serve",
    "DASHBOARD_HTML",
]