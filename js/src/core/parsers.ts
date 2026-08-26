/**
 * ==============================================================================
 * @termux-ai/chain Core Structured Output Parsers
 * ==============================================================================
 */

import { Runnable, createPipeline } from "./base.js";
import { Message, GenerationResult, StreamChunk } from "./schema.js";

export abstract class BaseOutputParser<T = any> implements Runnable<any, T> {
  async invoke(input: any): Promise<T> {
    const text = this.extractText(input);
    return this.parse(text);
  }

  pipe<NextOutput>(next: any): any {
    return createPipeline([this, next]);
  }

  protected extractText(input: any): string {
    if (typeof input === "string") return input;
    if (input && typeof input === "object") {
      if ("content" in input && typeof input.content === "string") return input.content;
      if ("delta" in input && typeof input.delta === "string") return input.delta;
    }
    return String(input);
  }

  abstract parse(text: string): T;
}

export class StringOutputParser extends BaseOutputParser<string> {
  private strip: boolean;

  constructor(strip: boolean = true) {
    super();
    this.strip = strip;
  }

  parse(text: string): string {
    return this.strip ? text.trim() : text;
  }
}

const JSON_BLOCK_REGEX = /```(?:json)?\s*([\s\S]*?)\s*```/i;

export class JsonOutputParser<T = any> extends BaseOutputParser<T> {
  private defaultFactory?: () => T;

  constructor(defaultFactory?: () => T) {
    super();
    this.defaultFactory = defaultFactory;
  }

  parse(text: string): T {
    const cleaned = text.trim();

    // 1. Markdown match
    const match = JSON_BLOCK_REGEX.exec(cleaned);
    if (match) {
      try {
        return JSON.parse(match[1].trim());
      } catch {}
    }

    // 2. Direct JSON load
    try {
      return JSON.parse(cleaned);
    } catch {}

    // 3. Substring match
    const startObj = cleaned.indexOf("{");
    const endObj = cleaned.lastIndexOf("}");
    if (startObj !== -1 && endObj !== -1 && endObj > startObj) {
      try {
        return JSON.parse(cleaned.slice(startObj, endObj + 1));
      } catch {}
    }

    const startArr = cleaned.indexOf("[");
    const endArr = cleaned.lastIndexOf("]");
    if (startArr !== -1 && endArr !== -1 && endArr > startArr) {
      try {
        return JSON.parse(cleaned.slice(startArr, endArr + 1));
      } catch {}
    }

    if (this.defaultFactory) {
      return this.defaultFactory();
    }

    throw new Error(`Failed to parse JSON from generation output:\n${text}`);
  }
}