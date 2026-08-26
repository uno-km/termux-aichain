/**
 * ==============================================================================
 * @termux-ai/chain: Sovereign LocalAgent Facade for Node.js (TypeScript ESM)
 * ==============================================================================
 */
import { OpenAICompatibleChat } from "./providers/openai_compatible.js";
import { HumanMessage } from "./schema.js";
import { createReactAgent } from "../graph/agent.js";

export class LocalAgent {
    constructor(options = {}) {
        const endpoint = typeof options === "string" ? options : (options.endpoint ?? "http://127.0.0.1:8080");
        const apiKey = typeof options === "object" ? options.apiKey : undefined;
        const modelName = typeof options === "object" ? (options.model ?? "default") : "default";
        const systemPrompt = typeof options === "object" ? options.systemPrompt : undefined;
        const tools = typeof options === "object" ? (options.tools ?? []) : [];

        this.model = new OpenAICompatibleChat({
            baseUrl: `${endpoint.replace(/\/+$/, "")}/v1`,
            model: modelName,
            apiKey
        });
        this.tools = tools;
        this.systemPrompt = systemPrompt;
        this.graph = createReactAgent(this.model, this.tools, {
            systemPrompt: this.systemPrompt,
            toolPolicy: { default: "deny", allowedTools: this.tools.map(t => t.name) }
        });
    }

    static connect(endpoint = "http://127.0.0.1:8080", options = {}) {
        return new LocalAgent({ endpoint, ...options });
    }

    static local(model = "qwen2.5-1.5b", options = {}) {
        return new LocalAgent({ endpoint: "http://127.0.0.1:8080", model, ...options });
    }

    async invoke(inputData, maxIterations = 10) {
        return await this.graph.invoke(inputData, maxIterations);
    }

    async run(promptOrInput, maxIterations = 10) {
        let payload;
        if (typeof promptOrInput === "string") {
            payload = { messages: [new HumanMessage(promptOrInput)] };
        } else {
            payload = promptOrInput;
        }
        const res = await this.invoke(payload, maxIterations);
        const messages = res.messages || [];
        if (messages.length > 0) {
            const lastMsg = messages[messages.length - 1];
            return lastMsg.content ? String(lastMsg.content) : JSON.stringify(lastMsg);
        }
        return JSON.stringify(res);
    }
}