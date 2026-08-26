/**
 * ==============================================================================
 * @termux-ai/chain Graph Engine: ReAct Agent (TypeScript ESM)
 * ==============================================================================
 */
import { SystemMessage } from "../core/schema.js";
import { StateGraph, END } from "./state.js";
export function tool(config, fn) {
    return {
        name: config.name,
        description: config.description,
        func: fn,
        parameters: config.parameters
    };
}
export function createReactAgent(model, tools, systemPrompt) {
    const toolsByName = new Map();
    tools.forEach(t => toolsByName.set(t.name, t));
    const agentNode = async (state) => {
        let msgs = [...state.messages];
        if (systemPrompt && !msgs.some(m => m.role === "system")) {
            msgs = [new SystemMessage(systemPrompt), ...msgs];
        }
        const gen = await model.generate(msgs);
        return {
            messages: [...msgs, gen.message],
            lastAiMessage: gen.message
        };
    };
    const shouldContinue = (state) => {
        if (!state.lastAiMessage || !state.lastAiMessage.tool_calls || state.lastAiMessage.tool_calls.length === 0) {
            return END;
        }
        return "tools_node";
    };
    const toolsNode = async (state) => {
        const msgs = [...state.messages];
        const toolCalls = state.lastAiMessage?.tool_calls ?? [];
        const newMsgs = [];
        for (const call of toolCalls) {
            const callId = call.id ?? "call_id";
            const fnName = call.function?.name;
            let args = call.function?.arguments;
            if (typeof args === "string") {
                try {
                    args = JSON.parse(args);
                }
                catch {
                    args = {};
                }
            }
            let content = "";
            const t = toolsByName.get(fnName);
            if (t) {
                try {
                    const res = await t.func(args);
                    content = String(res);
                }
                catch (e) {
                    content = `Error in tool ${fnName}: ${e.message}`;
                }
            }
            else {
                content = `Tool '${fnName}' not found.`;
            }
            newMsgs.push({
                role: "tool",
                content,
                name: fnName,
                additional_kwargs: { tool_call_id: callId }
            });
        }
        return { messages: [...msgs, ...newMsgs] };
    };
    const workflow = new StateGraph();
    workflow.addNode("agent_node", agentNode);
    workflow.addNode("tools_node", toolsNode);
    workflow.setEntryPoint("agent_node");
    workflow.addConditionalEdges("agent_node", shouldContinue, { tools_node: "tools_node", [END]: END });
    workflow.addEdge("tools_node", "agent_node");
    return workflow.compile();
}
