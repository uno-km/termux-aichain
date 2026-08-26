"""
Unit tests for termux_aichain.graph.state (StateGraph, Cycles, Conditional Edges)
"""
import pytest
from termux_aichain.graph.state import StateGraph, START, END

def test_linear_state_graph():
    workflow = StateGraph()
    
    def step1(state):
        return {"val": state.get("val", 0) + 10}
        
    def step2(state):
        return {"val": state["val"] * 2}
        
    workflow.add_node("step1", step1)
    workflow.add_node("step2", step2)
    
    workflow.set_entry_point("step1")
    workflow.add_edge("step1", "step2")
    workflow.set_finish_point("step2")
    
    app = workflow.compile()
    res = app.invoke({"val": 5})
    # (5 + 10) * 2 = 30
    assert res["val"] == 30

def test_conditional_state_graph():
    workflow = StateGraph()
    
    def decider(state):
        return {"checked": True}
        
    def path_a(state):
        return {"choice": "PATH_A"}
        
    def path_b(state):
        return {"choice": "PATH_B"}
        
    def router(state):
        return "node_a" if state.get("score", 0) > 80 else "node_b"
        
    workflow.add_node("decider", decider)
    workflow.add_node("node_a", path_a)
    workflow.add_node("node_b", path_b)
    
    workflow.set_entry_point("decider")
    workflow.add_conditional_edges("decider", router, {"node_a": "node_a", "node_b": "node_b"})
    workflow.set_finish_point("node_a")
    workflow.set_finish_point("node_b")
    
    app = workflow.compile()
    
    res_high = app.invoke({"score": 95})
    assert res_high["choice"] == "PATH_A"
    
    res_low = app.invoke({"score": 40})
    assert res_low["choice"] == "PATH_B"

def test_cyclic_loop_graph():
    workflow = StateGraph()
    
    def increment(state):
        return {"counter": state.get("counter", 0) + 1}
        
    def check_counter(state):
        if state["counter"] >= 5:
            return END
        return "increment"
        
    workflow.add_node("increment", increment)
    workflow.set_entry_point("increment")
    workflow.add_conditional_edges("increment", check_counter)
    
    app = workflow.compile()
    res = app.invoke({"counter": 0})
    assert res["counter"] == 5

def test_max_iterations_safety():
    workflow = StateGraph()
    
    def infinite_loop(state):
        return {"count": state.get("count", 0) + 1}
        
    workflow.add_node("infinite", infinite_loop)
    workflow.set_entry_point("infinite")
    workflow.add_edge("infinite", "infinite") # Infinite cycle
    
    app = workflow.compile()
    with pytest.raises(RuntimeError) as excinfo:
        app.invoke({"count": 0}, max_iterations=10)
    assert "exceeded maximum iteration" in str(excinfo.value)

def test_state_graph_streaming():
    workflow = StateGraph()
    
    workflow.add_node("step_a", lambda s: {"step": "A"})
    workflow.add_node("step_b", lambda s: {"step": "B"})
    workflow.set_entry_point("step_a")
    workflow.add_edge("step_a", "step_b")
    workflow.set_finish_point("step_b")
    
    app = workflow.compile()
    events = list(app.stream({}))
    assert len(events) == 2
    assert events[0][0] == "step_a"
    assert events[0][1]["step"] == "A"
    assert events[1][0] == "step_b"
    assert events[1][1]["step"] == "B"