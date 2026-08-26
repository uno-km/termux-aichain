/**
 * ==============================================================================
 * @termux-ai/chain OpenAI Compatible Provider (Pure Fetch / SSE)
 * ==============================================================================
 */
import { BaseChatModel } from "../base.js";
import { Message, GenerationResult, StreamChunk } from "../schema.js";
export interface OpenAICompatibleChatConfig {
    baseUrl?: string;
    apiKey?: string;
    model?: string;
    temperature?: number;
    maxTokens?: number;
    timeout?: number;
    headers?: Record<string, string>;
    [key: string]: any;
}
export declare class OpenAICompatibleChat extends BaseChatModel {
    baseUrl: string;
    apiKey: string;
    model: string;
    temperature: number;
    maxTokens?: number;
    timeout: number;
    customHeaders: Record<string, string>;
    extraParams: Record<string, any>;
    constructor(config?: OpenAICompatibleChatConfig);
    private formatMessages;
    generate(messages: Message[] | string, options?: Record<string, any>): Promise<GenerationResult>;
    stream(messages: Message[] | string, options?: Record<string, any>): AsyncIterable<StreamChunk>;
}
