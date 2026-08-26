/**
 * ==============================================================================
 * @termux-ai/chain Graph Engine: ReAct Agent (TypeScript ESM)
 * ==============================================================================
 */
import { SystemMessage, ToolMessage } from "../core/schema.js";
import { StateGraph, END } from "./state.js";

export function tool(config, fn) {
    return {
        name: config.name,
        description: config.description,
        func: fn,
        parameters: config.parameters
    };
}

export function validateToolArguments(schema, args) {
    if (!schema || !args || typeof args !== "object") return;
    const properties = schema.properties || {};
    const required = schema.required || [];

    // 1. Required fields check
    for (const reqField of required) {
        if (!(reqField in args)) {
            throw new Error(`ToolArgumentValidationError: Missing required argument '${reqField}'.`);
        }
    }

    // 2. Additional properties check (Reject unknown arguments unless explicitly allowed)
    if (schema.additionalProperties !== true) {
        const unknown = Object.keys(args).filter(k => !(k in properties));
        if (unknown.length > 0) {
            throw new Error(`ToolArgumentValidationError: Unknown argument(s): ${unknown.join(", ")}.`);
        }
    }

    // 3. Property types, bounds, and enum checks
    for (const [key, val] of Object.entries(args)) {
        if (!(key in properties)) continue;
        const fieldSchema = properties[key];
        const type = fieldSchema.type;

        if (type === "integer") {
            if (typeof val !== "number" || !Number.isInteger(val)) {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' must be an integer.`);
            }
            if (fieldSchema.minimum !== undefined && val < fieldSchema.minimum) {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' must be >= ${fieldSchema.minimum}.`);
            }
            if (fieldSchema.maximum !== undefined && val > fieldSchema.maximum) {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' must be <= ${fieldSchema.maximum}.`);
            }
        } else if (type === "number") {
            if (typeof val !== "number") {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' must be a number.`);
            }
            if (fieldSchema.minimum !== undefined && val < fieldSchema.minimum) {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' must be >= ${fieldSchema.minimum}.`);
            }
            if (fieldSchema.maximum !== undefined && val > fieldSchema.maximum) {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' must be <= ${fieldSchema.maximum}.`);
            }
        } else if (type === "boolean") {
            if (typeof val !== "boolean") {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' must be a boolean.`);
            }
        } else if (type === "string") {
            if (typeof val !== "string") {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' must be a string.`);
            }
            if (fieldSchema.minLength !== undefined && val.length < fieldSchema.minLength) {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' length must be >= ${fieldSchema.minLength}.`);
            }
            if (fieldSchema.maxLength !== undefined && val.length > fieldSchema.maxLength) {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' length must be <= ${fieldSchema.maxLength}.`);
            }
        } else if (type === "array") {
            if (!Array.isArray(val)) {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' must be an array.`);
            }
        } else if (type === "object") {
            if (typeof val !== "object" || val === null || Array.isArray(val)) {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' must be an object.`);
            }
        }

        // Global Enum Check
        if (fieldSchema.enum && Array.isArray(fieldSchema.enum)) {
            if (!fieldSchema.enum.includes(val)) {
                throw new Error(`ToolArgumentValidationError: Argument '${key}' value '${val}' is not in allowed enum.`);
            }
        }
    }
}

export function createReactAgent(model, tools, options = {}) {
    const systemPrompt = typeof options === "string" ? options : options.systemPrompt;
    // Strict Fail-Closed Default Deny Tool Policy (allowedTools: [])
    const toolPolicy = (typeof options === "object" && options.toolPolicy) ? options.toolPolicy : {
        default: "deny",
        allowedTools: []
    };
    const approvalCallback = typeof options === "object" ? options.approvalCallback : undefined;

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
                } catch {
                    args = {};
                }
            }

            let content = "";
            const t = toolsByName.get(fnName);

            if (t) {
                try {
                    // 1. Tool Policy Check (Default Deny)
                    if (toolPolicy.default === "deny" && !toolPolicy.allowedTools?.includes(fnName)) {
                        throw new Error(`ToolPolicyDeniedError: Tool '${fnName}' is denied by security policy (default=deny).`);
                    }

                    // 2. Strict JSON Schema Validation
                    if (t.parameters) {
                        validateToolArguments(t.parameters, args);
                    }

                    // 3. User Approval Callback
                    if (approvalCallback) {
                        const approved = await approvalCallback(fnName, args);
                        if (!approved) {
                            throw new Error(`ToolApprovalRequiredError: Invocation of '${fnName}' rejected by user approval.`);
                        }
                    }

                    const res = await t.func(args);
                    content = String(res);
                } catch (e) {
                    content = `Error in tool ${fnName}: ${e.message}`;
                }
            } else {
                content = `Tool '${fnName}' not found.`;
            }

            newMsgs.push(new ToolMessage(content, {
                name: fnName,
                tool_call_id: callId,
                additional_kwargs: { tool_call_id: callId }
            }));
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
