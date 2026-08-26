/**
 * ==============================================================================
 * @termux-ai/chain Memory Engine: ConversationBufferMemory (TypeScript ESM)
 * ==============================================================================
 */
import { Message } from "../core/schema.js";
export declare class ConversationBufferMemory {
    k: number;
    returnMessages: boolean;
    memoryKey: string;
    chatHistory: Message[];
    constructor(options?: {
        k?: number;
        returnMessages?: boolean;
        memoryKey?: string;
    });
    saveContext(inputs: Record<string, any> | string, outputs: Record<string, any> | string): void;
    loadMemoryVariables(): Record<string, any>;
    clear(): void;
}
