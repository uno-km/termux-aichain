/**
 * ==============================================================================
 * @termux-ai/chain Core Schema (TypeScript ESM)
 * ==============================================================================
 * Zero external heavy dependencies - Pure Web & Node.js Standards.
 */
export class SystemMessage {
    role = "system";
    content;
    name;
    additional_kwargs;
    constructor(content, options) {
        this.content = content;
        this.name = options?.name;
        this.additional_kwargs = options?.additional_kwargs;
    }
}
export class HumanMessage {
    role = "user";
    content;
    name;
    additional_kwargs;
    constructor(content, options) {
        this.content = content;
        this.name = options?.name;
        this.additional_kwargs = options?.additional_kwargs;
    }
}
export class AIMessage {
    role = "assistant";
    content;
    name;
    tool_calls;
    additional_kwargs;
    constructor(content, options) {
        this.content = content;
        this.name = options?.name;
        this.tool_calls = options?.tool_calls;
        this.additional_kwargs = options?.additional_kwargs;
    }
}
