"""
Unit tests for termux_aichain.graph.agent (Tool & create_react_agent)
"""
import pytest
from termux_aichain.core.base import BaseChatModel
from termux_aichain.core.schema import Message, HumanMessage, AIMessage, GenerationResult
from termux_aichain.graph.agent import Tool, tool, create_react_agent

class MockAgentLLM(BaseChatModel):
    def __init__(self):
        self.call_count = 0

    def generate(self, messages, **kwargs):
        self.call_count += 1
        # First turn: call the battery tool
        if self.call_count == 1:
            return GenerationResult(
                content="",
                message=AIMessage(
                    content="",
                    tool_calls=[{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "get_battery_status",
                            "arguments": '{"device_id": "galaxy-s20"}'
                        }
                    }]
                )
            )
        # Second turn: answer with the battery information
        return GenerationResult(
            content="The battery level on galaxy-s20 is 88%.",
            message=AIMessage(content="The battery level on galaxy-s20 is 88%.")
        )

    async def agenerate(self, messages, **kwargs):
        return self.generate(messages, **kwargs)

    def stream(self, messages, **kwargs):
        raise NotImplementedError

    async def astream(self, messages, **kwargs):
        raise NotImplementedError

def test_react_agent_loop():
    @tool(name="get_battery_status", description="Get current battery info")
    def get_battery_status(device_id: str) -> str:
        return f"{device_id}: 88% (discharging)"

    mock_llm = MockAgentLLM()
    agent = create_react_agent(model=mock_llm, tools=[get_battery_status])

    initial_messages = [HumanMessage(content="What is my battery level?")]
    final_state = agent.invoke({"messages": initial_messages})

    assert len(final_state["messages"]) == 4
    # 0: HumanMessage
    # 1: AIMessage with tool_calls
    # 2: ToolMessage with "galaxy-s20: 88% (discharging)"
    # 3: AIMessage with final text
    assert final_state["messages"][2].role == "tool"
    assert "88%" in final_state["messages"][2].content
    assert final_state["messages"][3].content == "The battery level on galaxy-s20 is 88%."