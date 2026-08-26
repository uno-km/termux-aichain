/**
 * ==============================================================================
 * @termux-ai/chain Core Engine: BitNet 1-Bit LLM Provider Adapter (TypeScript ESM)
 * ==============================================================================
 */
import { OpenAICompatibleChat } from "./openai_compatible.js";
export class BitNetChat extends OpenAICompatibleChat {
    constructor(options = {}) {
        super({
            baseUrl: options.baseUrl ?? "http://127.0.0.1:8080/v1",
            model: options.model ?? "bitnet-b1.58-3b",
            temperature: options.temperature ?? 0.1,
            maxTokens: options.maxTokens ?? 256,
            timeout: options.timeout ?? 60000
        });
    }
}
