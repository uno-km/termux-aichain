/**
 * ==============================================================================
 * @termux-ai/chain Graph Engine: ReAct Agent (TypeScript ESM)
 * ==============================================================================
 */

import { BaseChatModel } from "../core/base.js";
import { Message, AIMessage, SystemMessage, ToolMessage } from "../core/schema.js";
import { StateGraph, CompiledGraph, END } from "./state.js";

export interface Tool {
  name: string;
  description: string;
  func: (...args: any[]) => any;
  parameters?: Record<string, any>;
}

export function tool(config: { name: string; description: string; parameters?: Record<string, any> }, fn: (...args: any[]) => any): Tool {
  return {
    name: config.name,
    description: config.description,
    func: fn,
    parameters: config.parameters
  };
}

export interface AgentState {
  messages: Message[];
  lastAiMessage?: AIMessage;
  [key: string]: any;
}

export interface ToolRule {
  approval?: "none" | "explicit_prompt" | "token_verified";
  maxCallsPerMinute?: number;
  allowedRanges?: Record<string, [number, number]>;
}

export interface ToolPolicy {
  default: "allow" | "deny";
  allowedTools?: string[];
  rules?: Record<string, ToolRule>;
}

export interface CreateReactAgentOptions {
  systemPrompt?: string;
  toolPolicy?: ToolPolicy;
  approvalCallback?: (toolName: string, args: Record<string, any>) => boolean | Promise<boolean>;
}

export function validateToolArguments(schema: Record<string, any>, args: Record<string, any>): void {
  if (!schema || !args || typeof args !== "object") return;
  const properties = schema.properties || {};
  const required = schema.required || [];

  // 1. Required fields check
  for (const reqField of required) {
    if (!(reqField in args)) {
      throw new Error(`ToolArgumentValidationError: Missing required argument '${reqField}'.`);
    }
  }

  // 2. Additional properties check
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

export function createReactAgent(
  model: BaseChatModel,
  tools: Tool[],
  options: CreateReactAgentOptions | string = {}
): CompiledGraph<AgentState> {
  const resolvedOptions: CreateReactAgentOptions = typeof options === "string" ? { systemPrompt: options } : options;
  const systemPrompt = resolvedOptions.systemPrompt;
  const toolPolicy: ToolPolicy = resolvedOptions.toolPolicy ?? {
    default: "deny",
    allowedTools: []
  };
  const approvalCallback = resolvedOptions.approvalCallback;

  const toolsByName = new Map<string, Tool>();
  tools.forEach(t => toolsByName.set(t.name, t));

  const agentNode = async (state: AgentState): Promise<Partial<AgentState>> => {
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

  const shouldContinue = (state: AgentState): string => {
    if (!state.lastAiMessage || !state.lastAiMessage.tool_calls || state.lastAiMessage.tool_calls.length === 0) {
      return END;
    }
    return "tools_node";
  };

  const toolsNode = async (state: AgentState): Promise<Partial<AgentState>> => {
    const msgs = [...state.messages];
    const toolCalls = state.lastAiMessage?.tool_calls ?? [];
    const newMsgs: Message[] = [];

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
      const t = fnName ? toolsByName.get(fnName) : undefined;

      if (t && fnName) {
        try {
          // 1. Tool Policy Check (Default Deny)
          if (toolPolicy.default === "deny" && !toolPolicy.allowedTools?.includes(fnName)) {
            throw new Error(`ToolPolicyDeniedError: Tool '${fnName}' is denied by security policy (default=deny).`);
          }

          // 2. Strict JSON Schema Validation
          if (t.parameters && args && typeof args === "object") {
            validateToolArguments(t.parameters, args);
          }

          // 3. User Approval Callback
          if (approvalCallback) {
            const approved = await approvalCallback(fnName, args && typeof args === "object" ? args : {});
            if (!approved) {
              throw new Error(`ToolApprovalRequiredError: Invocation of '${fnName}' rejected by user approval.`);
            }
          }

          const res = await t.func(args);
          content = String(res);
        } catch (e: any) {
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

  const workflow = new StateGraph<AgentState>();
  workflow.addNode("agent_node", agentNode);
  workflow.addNode("tools_node", toolsNode);
  workflow.setEntryPoint("agent_node");
  workflow.addConditionalEdges("agent_node", shouldContinue, { tools_node: "tools_node", [END]: END });
  workflow.addEdge("tools_node", "agent_node");
  return workflow.compile();
}