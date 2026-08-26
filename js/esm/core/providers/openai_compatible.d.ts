/**
 * ==============================================================================
 * @termux-ai/chain Core Engine: OpenAI-Compatible & Local LLM Provider (TypeScript ESM)
 * ==============================================================================
 */
import { BaseChatModel } from "../base.js";
import { Message, GenerationResult, StreamChunk } from "../schema.js";
export interface ChatModelOptions {
    baseUrl?: string;
    apiKey?: string;
    model?: string;
    temperature?: number;
    topP?: number;
    topK?: number;
    minP?: number;
    repeatPenalty?: number;
    presencePenalty?: number;
    frequencyPenalty?: number;
    maxTokens?: number;
    stop?: string[];
    seed?: number;
    responseFormat?: Record<string, any>;
    grammar?: string;
    extraBody?: Record<string, any>;
    timeout?: number;
}
export declare class OpenAICompatibleChat extends BaseChatModel {
    baseUrl: string;
    apiKey: string;
    model: string;
    temperature: number;
    topP: number;
    topK: number;
    minP: number;
    repeatPenalty: number;
    presencePenalty: number;
    frequencyPenalty: number;
    maxTokens: number;
    stop: string[];
    seed?: number;
    responseFormat?: Record<string, any>;
    grammar?: string;
    extraBody: Record<string, any>;
    timeout: number;
    constructor(options?: ChatModelOptions);
    protected buildPayload(messages: Message[], stream?: boolean): Record<string, any>;
    protected coerceMsgs(input: string | Message[] | Record<string, any>): Message[];
    generate(messages: Message[]): Promise<GenerationResult>;
    stream(input: string | Message[] | Record<string, any>): AsyncGenerator<StreamChunk>;
}
