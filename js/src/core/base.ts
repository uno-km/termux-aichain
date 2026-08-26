/**
 * ==============================================================================
 * @termux-ai/chain Core Runnable & Pipeline Abstractions
 * ==============================================================================
 */

import { Message, AIMessage, GenerationResult, StreamChunk } from "./schema.js";

export interface Runnable<Input = any, Output = any> {
  invoke(input: Input, options?: any): Promise<Output>;
  stream?(input: Input, options?: any): AsyncIterable<any>;
  pipe<NextOutput>(next: Runnable<Output, NextOutput> | ((input: Output) => Promise<NextOutput> | NextOutput)): Runnable<Input, NextOutput>;
}

export class RunnableLambda<Input = any, Output = any> implements Runnable<Input, Output> {
  private fn: (input: Input, options?: any) => Promise<Output> | Output;

  constructor(fn: (input: Input, options?: any) => Promise<Output> | Output) {
    this.fn = fn;
  }

  async invoke(input: Input, options?: any): Promise<Output> {
    return await this.fn(input, options);
  }

  pipe<NextOutput>(next: Runnable<Output, NextOutput> | ((input: Output) => Promise<NextOutput> | NextOutput)): Runnable<Input, NextOutput> {
    return createPipeline([this, next]);
  }
}

export class RunnableSequence<Input = any, Output = any> implements Runnable<Input, Output> {
  steps: Runnable[];

  constructor(steps: Runnable[]) {
    this.steps = steps;
  }

  async invoke(input: Input, options?: any): Promise<Output> {
    let current: any = input;
    for (let i = 0; i < this.steps.length; i++) {
      if (i === 0 && options) {
        current = await this.steps[i].invoke(current, options);
      } else {
        current = await this.steps[i].invoke(current);
      }
    }
    return current;
  }

  async *stream(input: Input, options?: any): AsyncIterable<any> {
    if (this.steps.length === 0) return;
    let current: any = input;
    for (let i = 0; i < this.steps.length - 1; i++) {
      if (i === 0 && options) {
        current = await this.steps[i].invoke(current, options);
      } else {
        current = await this.steps[i].invoke(current);
      }
    }
    const last = this.steps[this.steps.length - 1];
    if (last.stream) {
      for await (const chunk of last.stream(current)) {
        yield chunk;
      }
    } else {
      yield await last.invoke(current);
    }
  }

  pipe<NextOutput>(next: Runnable<Output, NextOutput> | ((input: Output) => Promise<NextOutput> | NextOutput)): Runnable<Input, NextOutput> {
    const nextRunnable = typeof next === "function" ? new RunnableLambda(next) : next;
    if (nextRunnable instanceof RunnableSequence) {
      return new RunnableSequence([...this.steps, ...nextRunnable.steps]);
    }
    return new RunnableSequence([...this.steps, nextRunnable]);
  }
}

export function createPipeline(steps: any[]): RunnableSequence {
  const normalized: Runnable[] = [];
  for (const s of steps) {
    if (typeof s === "function") {
      normalized.push(new RunnableLambda(s));
    } else if (s instanceof RunnableSequence) {
      normalized.push(...s.steps);
    } else if (typeof s === "object" && s !== null && "invoke" in s) {
      normalized.push(s);
    } else {
      throw new TypeError(`Cannot compose non-runnable element: ${typeof s}`);
    }
  }
  return new RunnableSequence(normalized);
}

export abstract class BaseChatModel implements Runnable<Message[] | string, AIMessage> {
  abstract generate(messages: Message[] | string, options?: any): Promise<GenerationResult>;
  abstract stream(messages: Message[] | string, options?: any): AsyncIterable<StreamChunk>;

  async invoke(input: Message[] | string, options?: any): Promise<AIMessage> {
    const res = await this.generate(input, options);
    return res.message;
  }

  pipe<NextOutput>(next: Runnable<AIMessage, NextOutput> | ((input: AIMessage) => Promise<NextOutput> | NextOutput)): Runnable<Message[] | string, NextOutput> {
    return createPipeline([this, next]);
  }
}