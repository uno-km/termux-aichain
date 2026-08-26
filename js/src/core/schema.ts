/**
 * ==============================================================================
 * @termux-ai/chain Core Schema (TypeScript ESM)
 * ==============================================================================
 * Zero external heavy dependencies - Pure Web & Node.js Standards.
 */

export type RoleType = "system" | "user" | "assistant" | "tool" | "function";

export interface Message {
  role: RoleType;
  content: string;
  name?: string;
  tool_calls?: any[];
  additional_kwargs?: Record<string, any>;
}

export class SystemMessage implements Message {
  role: RoleType = "system";
  content: string;
  name?: string;
  additional_kwargs?: Record<string, any>;

  constructor(content: string, options?: { name?: string; additional_kwargs?: Record<string, any> }) {
    this.content = content;
    this.name = options?.name;
    this.additional_kwargs = options?.additional_kwargs;
  }
}

export class HumanMessage implements Message {
  role: RoleType = "user";
  content: string;
  name?: string;
  additional_kwargs?: Record<string, any>;

  constructor(content: string, options?: { name?: string; additional_kwargs?: Record<string, any> }) {
    this.content = content;
    this.name = options?.name;
    this.additional_kwargs = options?.additional_kwargs;
  }
}

export class AIMessage implements Message {
  role: RoleType = "assistant";
  content: string;
  name?: string;
  tool_calls?: any[];
  additional_kwargs?: Record<string, any>;

  constructor(content: string, options?: { name?: string; tool_calls?: any[]; additional_kwargs?: Record<string, any> }) {
    this.content = content;
    this.name = options?.name;
    this.tool_calls = options?.tool_calls;
    this.additional_kwargs = options?.additional_kwargs;
  }
}

export interface UsageInfo {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
}

export interface GenerationResult {
  content: string;
  message: AIMessage;
  usage: UsageInfo;
  raw: any;
}

export interface StreamChunk {
  content: string;
  delta: string;
  is_last: boolean;
  usage?: UsageInfo;
  raw?: any;
}