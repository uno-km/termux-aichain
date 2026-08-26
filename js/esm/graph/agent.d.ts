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
export declare function createReactAgent(model: BaseChatModel, tools: Tool[], systemPrompt?: string): CompiledGraph<AgentState>;
