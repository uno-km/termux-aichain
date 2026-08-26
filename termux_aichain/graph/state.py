"""
==============================================================================
termux-aichain Graph Engine: StateGraph & Cyclic Orchestration
==============================================================================
Ultra-lightweight state machine and cyclic multi-agent graph engine.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import inspect
import asyncio
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union
from termux_aichain.core.base import Runnable

START = "__start__"
END = "__end__"

class StateGraph:
    """Cyclic state graph orchestrator replacing heavy LangGraph dependencies."""

    def __init__(self, state_schema: Optional[type] = None):
        self.state_schema = state_schema or dict
        self.nodes: Dict[str, Callable[[Dict[str, Any]], Union[Dict[str, Any], Any]]] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, Tuple[Callable[[Dict[str, Any]], str], Optional[Dict[str, str]]]] = {}
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, action: Callable[[Dict[str, Any]], Union[Dict[str, Any], Any]]) -> StateGraph:
        if name in (START, END):
            raise ValueError(f"Cannot name node '{name}': reserved keyword.")
        self.nodes[name] = action
        return self

    def add_edge(self, from_node: str, to_node: str) -> StateGraph:
        if from_node == START:
            self.entry_point = to_node
        else:
            self.edges[from_node] = to_node
        return self

    def add_conditional_edges(
        self,
        source: str,
        router: Callable[[Dict[str, Any]], str],
        path_map: Optional[Dict[str, str]] = None
    ) -> StateGraph:
        self.conditional_edges[source] = (router, path_map)
        return self

    def set_entry_point(self, node_name: str) -> StateGraph:
        self.entry_point = node_name
        return self

    def set_finish_point(self, node_name: str) -> StateGraph:
        self.edges[node_name] = END
        return self

    def compile(self) -> CompiledGraph:
        if not self.entry_point:
            raise ValueError("StateGraph requires an entry point. Call set_entry_point() or add_edge(START, ...).")
        return CompiledGraph(
            nodes=dict(self.nodes),
            edges=dict(self.edges),
            conditional_edges=dict(self.conditional_edges),
            entry_point=self.entry_point,
            state_schema=self.state_schema
        )

class CompiledGraph(Runnable):
    """Executable compiled state graph instance."""

    def __init__(
        self,
        nodes: Dict[str, Callable[[Dict[str, Any]], Any]],
        edges: Dict[str, str],
        conditional_edges: Dict[str, Tuple[Callable[[Dict[str, Any]], str], Optional[Dict[str, str]]]],
        entry_point: str,
        state_schema: type
    ):
        self.nodes = nodes
        self.edges = edges
        self.conditional_edges = conditional_edges
        self.entry_point = entry_point
        self.state_schema = state_schema

    def _get_next_node(self, current_node: str, state: Dict[str, Any]) -> str:
        # Check conditional edge first
        if current_node in self.conditional_edges:
            router, path_map = self.conditional_edges[current_node]
            route_res = router(state)
            if path_map and route_res in path_map:
                return path_map[route_res]
            return route_res
        
        # Check static edge
        return self.edges.get(current_node, END)

    def invoke(self, input_val: Dict[str, Any], max_iterations: int = 50, **kwargs: Any) -> Dict[str, Any]:
        state = dict(input_val) if isinstance(input_val, dict) else {"input": input_val}
        current_node = self.entry_point
        iteration = 0

        while current_node != END and iteration < max_iterations:
            if current_node not in self.nodes:
                raise KeyError(f"Node '{current_node}' not registered in StateGraph.")

            action = self.nodes[current_node]
            update = action(state)
            if isinstance(update, dict):
                state.update(update)

            current_node = self._get_next_node(current_node, state)
            iteration += 1

        if iteration >= max_iterations:
            raise RuntimeError(f"StateGraph exceeded maximum iteration safety limit ({max_iterations}). Possible infinite cycle.")

        return state

    async def ainvoke(self, input_val: Dict[str, Any], max_iterations: int = 50, **kwargs: Any) -> Dict[str, Any]:
        state = dict(input_val) if isinstance(input_val, dict) else {"input": input_val}
        current_node = self.entry_point
        iteration = 0

        while current_node != END and iteration < max_iterations:
            if current_node not in self.nodes:
                raise KeyError(f"Node '{current_node}' not registered in StateGraph.")

            action = self.nodes[current_node]
            if inspect.iscoroutinefunction(action):
                update = await action(state)
            else:
                update = action(state)

            if isinstance(update, dict):
                state.update(update)

            current_node = self._get_next_node(current_node, state)
            iteration += 1

        if iteration >= max_iterations:
            raise RuntimeError(f"StateGraph exceeded maximum iteration safety limit ({max_iterations}).")

        return state

    def stream(self, input_val: Dict[str, Any], max_iterations: int = 50, **kwargs: Any) -> Iterator[Tuple[str, Dict[str, Any]]]:
        state = dict(input_val) if isinstance(input_val, dict) else {"input": input_val}
        current_node = self.entry_point
        iteration = 0

        while current_node != END and iteration < max_iterations:
            if current_node not in self.nodes:
                raise KeyError(f"Node '{current_node}' not registered in StateGraph.")

            action = self.nodes[current_node]
            update = action(state)
            if isinstance(update, dict):
                state.update(update)

            yield (current_node, dict(state))

            current_node = self._get_next_node(current_node, state)
            iteration += 1

    async def astream(self, input_val: Dict[str, Any], max_iterations: int = 50, **kwargs: Any) -> AsyncIterator[Tuple[str, Dict[str, Any]]]:
        state = dict(input_val) if isinstance(input_val, dict) else {"input": input_val}
        current_node = self.entry_point
        iteration = 0

        while current_node != END and iteration < max_iterations:
            if current_node not in self.nodes:
                raise KeyError(f"Node '{current_node}' not registered in StateGraph.")

            action = self.nodes[current_node]
            if inspect.iscoroutinefunction(action):
                update = await action(state)
            else:
                update = action(state)

            if isinstance(update, dict):
                state.update(update)

            yield (current_node, dict(state))

            current_node = self._get_next_node(current_node, state)
            iteration += 1

    def __repr__(self) -> str:
        return f"CompiledGraph(nodes={list(self.nodes.keys())}, entry_point='{self.entry_point}')"