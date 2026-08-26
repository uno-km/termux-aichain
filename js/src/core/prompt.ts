/**
 * ==============================================================================
 * @termux-ai/chain Core Prompt Templates
 * ==============================================================================
 */

import { Message, SystemMessage, HumanMessage, AIMessage, RoleType } from "./schema.js";

const VARIABLE_PATTERN = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;

export function extractVariables(templateStr: string): string[] {
  const vars = new Set<string>();
  let match: RegExpExecArray | null;
  while ((match = VARIABLE_PATTERN.exec(templateStr)) !== null) {
    vars.add(match[1]);
  }
  return Array.from(vars);
}

export class PromptTemplate {
  template: string;
  inputVariables: string[];
  partialVariables: Record<string, any>;

  constructor(template: string, inputVariables?: string[], partialVariables?: Record<string, any>) {
    this.template = template;
    this.inputVariables = inputVariables ?? extractVariables(template);
    this.partialVariables = partialVariables ?? {};
  }

  static fromTemplate(template: string): PromptTemplate {
    return new PromptTemplate(template);
  }

  partial(variables: Record<string, any>): PromptTemplate {
    const newPartial = { ...this.partialVariables, ...variables };
    return new PromptTemplate(
      this.template,
      this.inputVariables.filter(v => !(v in newPartial)),
      newPartial
    );
  }

  format(variables: Record<string, any> = {}): string {
    const merged = { ...this.partialVariables, ...variables };
    for (const v of this.inputVariables) {
      if (!(v in merged)) {
        throw new Error(`Missing required prompt variable: ${v}`);
      }
    }
    return this.template.replace(VARIABLE_PATTERN, (_, key) => String(merged[key] ?? ""));
  }

  async invoke(input: any): Promise<string> {
    if (typeof input === "object" && input !== null) {
      return this.format(input);
    } else if (typeof input === "string" && this.inputVariables.length === 1) {
      return this.format({ [this.inputVariables[0]]: input });
    }
    return this.format();
  }

  pipe(next: any): any {
    return createPipeline([this, next]);
  }
}

export class ChatPromptTemplate {
  messages: Array<{ role: RoleType; template: PromptTemplate }>;
  inputVariables: string[];

  constructor(messages: Array<[RoleType, string] | { role: RoleType; template: PromptTemplate }>) {
    this.messages = [];
    const allVars = new Set<string>();

    for (const m of messages) {
      if (Array.isArray(m)) {
        const [role, tplStr] = m;
        const tpl = new PromptTemplate(tplStr);
        this.messages.push({ role, template: tpl });
        tpl.inputVariables.forEach(v => allVars.add(v));
      } else {
        this.messages.push(m);
        m.template.inputVariables.forEach(v => allVars.add(v));
      }
    }
    this.inputVariables = Array.from(allVars);
  }

  static fromMessages(messages: Array<[RoleType, string]>): ChatPromptTemplate {
    return new ChatPromptTemplate(messages);
  }

  formatMessages(variables: Record<string, any> = {}): Message[] {
    return this.messages.map(({ role, template }) => {
      const content = template.format(variables);
      if (role === "system") return new SystemMessage(content);
      if (role === "user") return new HumanMessage(content);
      if (role === "assistant") return new AIMessage(content);
      return { role, content };
    });
  }

  async invoke(input: any): Promise<Message[]> {
    if (typeof input === "object" && input !== null) {
      return this.formatMessages(input);
    } else if (typeof input === "string" && this.inputVariables.length === 1) {
      return this.formatMessages({ [this.inputVariables[0]]: input });
    }
    return this.formatMessages();
  }

  pipe(next: any): any {
    return createPipeline([this, next]);
  }
}

import { createPipeline } from "./base.js";