/**
 * ==============================================================================
 * @termux-ai/chain OpenAI Compatible Provider (Pure Fetch / SSE)
 * ==============================================================================
 */

import { BaseChatModel } from "../base.js";
import { Message, AIMessage, GenerationResult, StreamChunk, UsageInfo } from "../schema.js";

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

export class OpenAICompatibleChat extends BaseChatModel {
  baseUrl: string;
  apiKey: string;
  model: string;
  temperature: number;
  maxTokens?: number;
  timeout: number;
  customHeaders: Record<string, string>;
  extraParams: Record<string, any>;

  constructor(config: OpenAICompatibleChatConfig = {}) {
    super();
    this.baseUrl = (config.baseUrl ?? "http://127.0.0.1:8080/v1").replace(/\/+$/, "");
    this.apiKey = config.apiKey ?? "no-key";
    this.model = config.model ?? "default";
    this.temperature = config.temperature ?? 0.7;
    this.maxTokens = config.maxTokens;
    this.timeout = config.timeout ?? 60000;
    this.customHeaders = {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "Authorization": `Bearer ${this.apiKey}`,
      ...(config.headers ?? {})
    };
    const { baseUrl, apiKey, model, temperature, maxTokens, timeout, headers, ...rest } = config;
    this.extraParams = rest;
  }

  private formatMessages(messages: Message[] | string): Array<{ role: string; content: string }> {
    if (typeof messages === "string") {
      return [{ role: "user", content: messages }];
    }
    return messages.map(m => ({
      role: m.role,
      content: m.content,
      ...(m.name ? { name: m.name } : {}),
      ...(m.tool_calls ? { tool_calls: m.tool_calls } : {})
    }));
  }

  async generate(messages: Message[] | string, options: Record<string, any> = {}): Promise<GenerationResult> {
    const payload: any = {
      model: options.model ?? this.model,
      messages: this.formatMessages(messages),
      temperature: options.temperature ?? this.temperature,
      stream: false,
      ...this.extraParams,
      ...options
    };
    if (this.maxTokens !== undefined && !payload.max_tokens) {
      payload.max_tokens = this.maxTokens;
    }

    const tStart = performance.now();
    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: "POST",
      headers: this.customHeaders,
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(this.timeout)
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`OpenAICompatibleChat HTTPError ${response.status}: ${errText}`);
    }

    const data = await response.json();
    const elapsedMs = performance.now() - tStart;
    const choice = data.choices?.[0];
    if (!choice) {
      throw new Error(`No choices returned from model endpoint: ${JSON.stringify(data)}`);
    }

    const content = choice.message?.content ?? "";
    const toolCalls = choice.message?.tool_calls;
    const usage: UsageInfo = {
      prompt_tokens: data.usage?.prompt_tokens ?? 0,
      completion_tokens: data.usage?.completion_tokens ?? 0,
      total_tokens: data.usage?.total_tokens ?? 0,
      latency_ms: Math.round(elapsedMs * 100) / 100
    };

    return {
      content,
      message: new AIMessage(content, { tool_calls: toolCalls }),
      usage,
      raw: data
    };
  }

  async *stream(messages: Message[] | string, options: Record<string, any> = {}): AsyncIterable<StreamChunk> {
    const payload: any = {
      model: options.model ?? this.model,
      messages: this.formatMessages(messages),
      temperature: options.temperature ?? this.temperature,
      stream: true,
      ...this.extraParams,
      ...options
    };
    if (this.maxTokens !== undefined && !payload.max_tokens) {
      payload.max_tokens = this.maxTokens;
    }

    const tStart = performance.now();
    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: "POST",
      headers: this.customHeaders,
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(this.timeout)
    });

    if (!response.ok || !response.body) {
      const errText = await response.text();
      throw new Error(`OpenAICompatibleChat Stream HTTPError ${response.status}: ${errText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let accumulatedContent = "";
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;
          const dataStr = trimmed.slice(5).trim();
          if (dataStr === "[DONE]") {
            const elapsedMs = performance.now() - tStart;
            yield {
              content: accumulatedContent,
              delta: "",
              is_last: true,
              usage: {
                prompt_tokens: 0,
                completion_tokens: 0,
                total_tokens: 0,
                latency_ms: Math.round(elapsedMs * 100) / 100
              }
            };
            return;
          }
          try {
            const parsed = JSON.parse(dataStr);
            const delta = parsed.choices?.[0]?.delta?.content ?? "";
            if (delta) {
              accumulatedContent += delta;
              yield {
                content: accumulatedContent,
                delta,
                is_last: false,
                raw: parsed
              };
            }
          } catch {}
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}