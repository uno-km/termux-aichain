from termux_aichain.graph.agent import create_react_agent, Tool, tool
from termux_aichain.core.base import BaseChatModel
from termux_aichain.core.schema import Message, HumanMessage, AIMessage, ToolMessage, GenerationResult
from typing import List

class RuleBasedAgentModel(BaseChatModel):
    def __init__(self):
        self.call_count = 0

    def generate(self, messages: List[Message], **kwargs) -> GenerationResult:
        self.call_count += 1
        if self.call_count == 1:
            ai_msg = AIMessage(
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
            return GenerationResult(content="", message=ai_msg)
        else:
            final_ai = AIMessage(content="The battery level on galaxy-s20 is 88%.")
            return GenerationResult(content=final_ai.content, message=final_ai)

    async def agenerate(self, messages: List[Message], **kwargs) -> GenerationResult:
        return self.generate(messages, **kwargs)

    def stream(self, messages, **kwargs):
        raise NotImplementedError

    async def astream(self, messages, **kwargs):
        raise NotImplementedError

def test_react_agent_loop():
    @tool(name="get_battery_status", description="Get current battery info")
    def get_battery_status(device_id: str) -> str:
        return f"{device_id}: 88% (discharging)"

    llm = RuleBasedAgentModel()
    agent = create_react_agent(model=llm, tools=[get_battery_status])

    initial_messages = [HumanMessage(content="What is my battery level?")]
    final_state = agent.invoke({"messages": initial_messages})

    tool_msgs = [m for m in final_state["messages"] if m.role == "tool"]
    ai_msgs = [m for m in final_state["messages"] if m.role == "assistant"]

    assert len(tool_msgs) >= 1
    assert "88%" in tool_msgs[0].content
    assert "88%" in ai_msgs[-1].content