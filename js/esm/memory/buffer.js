/**
 * ==============================================================================
 * @termux-ai/chain Memory Engine: ConversationBufferMemory (TypeScript ESM)
 * ==============================================================================
 */
import { HumanMessage, AIMessage } from "../core/schema.js";
export class ConversationBufferMemory {
    k;
    returnMessages;
    memoryKey;
    chatHistory = [];
    constructor(options = {}) {
        this.k = options.k ?? 10;
        this.returnMessages = options.returnMessages ?? true;
        this.memoryKey = options.memoryKey ?? "history";
    }
    saveContext(inputs, outputs) {
        const userText = typeof inputs === "string" ? inputs : Object.values(inputs)[0] ?? "";
        const aiText = typeof outputs === "string" ? outputs : Object.values(outputs)[0] ?? "";
        this.chatHistory.push(new HumanMessage(String(userText)));
        this.chatHistory.push(new AIMessage(String(aiText)));
        if (this.chatHistory.length > this.k * 2) {
            this.chatHistory = this.chatHistory.slice(-(this.k * 2));
        }
    }
    loadMemoryVariables() {
        if (this.returnMessages) {
            return { [this.memoryKey]: [...this.chatHistory] };
        }
        const lines = this.chatHistory.map(m => {
            const role = m.role === "user" ? "Human" : m.role === "assistant" ? "AI" : m.role;
            return `${role}: ${m.content}`;
        });
        return { [this.memoryKey]: lines.join("\n") };
    }
    clear() {
        this.chatHistory = [];
    }
}
