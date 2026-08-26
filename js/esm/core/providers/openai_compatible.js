/**
 * ==============================================================================
 * @termux-ai/chain Core Engine: OpenAI-Compatible & Local LLM Provider (TypeScript ESM)
 * ==============================================================================
 */
import { BaseChatModel } from "../base.js";
import { HumanMessage, AIMessage } from "../schema.js";
export class OpenAICompatibleChat extends BaseChatModel {
    baseUrl;
    apiKey;
    model;
    temperature;
    topP;
    topK;
    minP;
    repeatPenalty;
    presencePenalty;
    frequencyPenalty;
    maxTokens;
    stop;
    seed;
    responseFormat;
    grammar;
    extraBody;
    timeout;
    constructor(options = {}) {
        super();
        this.baseUrl = (options.baseUrl || "http://127.0.0.1:8080/v1").replace(/\/$/, "");
        this.apiKey = options.apiKey || "sk-termux-sovereign";
        this.model = options.model || "local-model";
        this.temperature = options.temperature ?? 0.7;
        this.topP = options.topP ?? 0.95;
        this.topK = options.topK ?? 40;
        this.minP = options.minP ?? 0.05;
        this.repeatPenalty = options.repeatPenalty ?? 1.1;
        this.presencePenalty = options.presencePenalty ?? 0.0;
        this.frequencyPenalty = options.frequencyPenalty ?? 0.0;
        this.maxTokens = options.maxTokens ?? 512;
        this.stop = options.stop || [];
        this.seed = options.seed;
        this.responseFormat = options.responseFormat;
        this.grammar = options.grammar;
        this.extraBody = options.extraBody || {};
        this.timeout = options.timeout ?? 60000;
    }
    buildPayload(messages, stream = false) {
        const payload = {
            model: this.model,
            messages: messages.map((m) => ({ role: m.role, content: m.content })),
            stream,
            temperature: this.temperature,
            top_p: this.topP,
            max_tokens: this.maxTokens,
        };
        if (this.topK > 0)
            payload.top_k = this.topK;
        if (this.minP > 0)
            payload.min_p = this.minP;
        if (this.repeatPenalty !== 1.0)
            payload.repeat_penalty = this.repeatPenalty;
        if (this.presencePenalty !== 0.0)
            payload.presence_penalty = this.presencePenalty;
        if (this.frequencyPenalty !== 0.0)
            payload.frequency_penalty = this.frequencyPenalty;
        if (this.stop.length > 0)
            payload.stop = this.stop;
        if (this.seed !== undefined)
            payload.seed = this.seed;
        if (this.responseFormat)
            payload.response_format = this.responseFormat;
        if (this.grammar)
            payload.grammar = this.grammar;
        for (const [k, v] of Object.entries(this.extraBody)) {
            payload[k] = v;
        }
        return payload;
    }
    coerceMsgs(input) {
        if (typeof input === "string")
            return [new HumanMessage(input)];
        if (Array.isArray(input))
            return input;
        if (input && typeof input === "object" && "messages" in input)
            return input.messages;
        return [new HumanMessage(JSON.stringify(input))];
    }
    async generate(messages) {
        const url = `${this.baseUrl}/chat/completions`;
        const payload = this.buildPayload(messages, false);
        const t0 = performance.now();
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), this.timeout);
        try {
            const resp = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${this.apiKey}`,
                },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });
            if (!resp.ok) {
                const errText = await resp.text();
                throw new Error(`HTTP ${resp.status} from local LLM: ${errText}`);
            }
            const data = (await resp.json());
            const content = data?.choices?.[0]?.message?.content || "";
            const rawUsage = data?.usage || {};
            const usage = {
                prompt_tokens: rawUsage.prompt_tokens || 0,
                completion_tokens: rawUsage.completion_tokens || 0,
                total_tokens: rawUsage.total_tokens || 0,
                latency_ms: performance.now() - t0,
            };
            return {
                message: new AIMessage(content),
                content,
                usage,
                raw: data
            };
        }
        finally {
            clearTimeout(timer);
        }
    }
    async *stream(input) {
        const messages = this.coerceMsgs(input);
        const url = `${this.baseUrl}/chat/completions`;
        const payload = this.buildPayload(messages, true);
        const resp = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${this.apiKey}`,
            },
            body: JSON.stringify(payload),
        });
        if (!resp.ok || !resp.body) {
            throw new Error(`Streaming failed: HTTP ${resp.status}`);
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let accumulated = "";
        while (true) {
            const { value, done } = await reader.read();
            if (done)
                break;
            const chunk = decoder.decode(value);
            const lines = chunk.split("\n");
            for (const line of lines) {
                if (!line.startsWith("data: "))
                    continue;
                const dataStr = line.slice(6).trim();
                if (dataStr === "[DONE]") {
                    yield { delta: "", content: accumulated, is_last: true };
                    return;
                }
                try {
                    const parsed = JSON.parse(dataStr);
                    const delta = parsed?.choices?.[0]?.delta?.content || "";
                    if (delta) {
                        accumulated += delta;
                        yield { delta, content: accumulated, is_last: false };
                    }
                }
                catch (e) { }
            }
        }
    }
}
