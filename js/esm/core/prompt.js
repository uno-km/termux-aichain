/**
 * ==============================================================================
 * @termux-ai/chain Core Prompt Templates
 * ==============================================================================
 */
import { SystemMessage, HumanMessage, AIMessage } from "./schema.js";
const VARIABLE_PATTERN = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
export function extractVariables(templateStr) {
    const vars = new Set();
    let match;
    while ((match = VARIABLE_PATTERN.exec(templateStr)) !== null) {
        vars.add(match[1]);
    }
    return Array.from(vars);
}
export class PromptTemplate {
    template;
    inputVariables;
    partialVariables;
    constructor(template, inputVariables, partialVariables) {
        this.template = template;
        this.inputVariables = inputVariables ?? extractVariables(template);
        this.partialVariables = partialVariables ?? {};
    }
    static fromTemplate(template) {
        return new PromptTemplate(template);
    }
    partial(variables) {
        const newPartial = { ...this.partialVariables, ...variables };
        return new PromptTemplate(this.template, this.inputVariables.filter(v => !(v in newPartial)), newPartial);
    }
    format(variables = {}) {
        const merged = { ...this.partialVariables, ...variables };
        for (const v of this.inputVariables) {
            if (!(v in merged)) {
                throw new Error(`Missing required prompt variable: ${v}`);
            }
        }
        return this.template.replace(VARIABLE_PATTERN, (_, key) => String(merged[key] ?? ""));
    }
    async invoke(input) {
        if (typeof input === "object" && input !== null) {
            return this.format(input);
        }
        else if (typeof input === "string" && this.inputVariables.length === 1) {
            return this.format({ [this.inputVariables[0]]: input });
        }
        return this.format();
    }
    pipe(next) {
        return createPipeline([this, next]);
    }
}
export class ChatPromptTemplate {
    messages;
    inputVariables;
    constructor(messages) {
        this.messages = [];
        const allVars = new Set();
        for (const m of messages) {
            if (Array.isArray(m)) {
                const [role, tplStr] = m;
                const tpl = new PromptTemplate(tplStr);
                this.messages.push({ role, template: tpl });
                tpl.inputVariables.forEach(v => allVars.add(v));
            }
            else {
                this.messages.push(m);
                m.template.inputVariables.forEach(v => allVars.add(v));
            }
        }
        this.inputVariables = Array.from(allVars);
    }
    static fromMessages(messages) {
        return new ChatPromptTemplate(messages);
    }
    formatMessages(variables = {}) {
        return this.messages.map(({ role, template }) => {
            const content = template.format(variables);
            if (role === "system")
                return new SystemMessage(content);
            if (role === "user")
                return new HumanMessage(content);
            if (role === "assistant")
                return new AIMessage(content);
            return { role, content };
        });
    }
    async invoke(input) {
        if (typeof input === "object" && input !== null) {
            return this.formatMessages(input);
        }
        else if (typeof input === "string" && this.inputVariables.length === 1) {
            return this.formatMessages({ [this.inputVariables[0]]: input });
        }
        return this.formatMessages();
    }
    pipe(next) {
        return createPipeline([this, next]);
    }
}
import { createPipeline } from "./base.js";
