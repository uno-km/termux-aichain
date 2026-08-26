/**
 * ==============================================================================
 * @termux-ai/chain Graph Engine: ReAct Agent (TypeScript ESM)
 * ==============================================================================
 */
import { BaseChatModel } from "../core/base.js";
import { Message, AIMessage } from "../core/schema.js";
import { CompiledGraph } from "./state.js";
export interface Tool {
    name: string;
    description: string;
    func: (...args: any[]) => any;
    parameters?: Record<string, any>;
}
export declare function tool(config: {
    name: string;
    description: string;
    parameters?: Record<string, any>;
}, fn: (...args: any[]) => any): Tool;
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
export declare function validateToolArguments(schema: Record<string, any>, args: Record<string, any>): void;
export declare function createReactAgent(model: BaseChatModel, tools: Tool[], options?: CreateReactAgentOptions | string): CompiledGraph<AgentState>;
