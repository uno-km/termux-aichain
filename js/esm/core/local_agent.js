import http from "node:http";
import https from "node:https";
import { OpenAICompatibleChat } from "./providers/openai_compatible.js";
import { HumanMessage } from "./schema.js";
import { createReactAgent } from "../graph/agent.js";

export async function verifyServerIdentity(endpoint, {
    timeoutMs = 2000,
    expectedService,
    expectedProtocolVersion,
    expectedModelId
} = {}) {
    const url = new URL(`${endpoint.replace(/\/+$/, "")}/health`);
    const transport = url.protocol === "https:" ? https : http;

    return new Promise((resolve, reject) => {
        const req = transport.get(url, {
            headers: { Accept: "application/json" },
            timeout: timeoutMs
        }, (res) => {
            if (res.statusCode !== 200) {
                reject(new Error(`Server health check returned HTTP status ${res.statusCode}`));
                return;
            }
            let data = "";
            res.on("data", chunk => {
                data += chunk;
                if (data.length > 65536) {
                    req.destroy();
                    reject(new Error("Health response exceeds maximum allowed size (64KB)."));
                }
            });
            res.on("end", () => {
                try {
                    const payload = JSON.parse(data);
                    if (!payload || typeof payload !== "object") {
                        reject(new Error("Health response is not a valid JSON object."));
                        return;
                    }
                    const service = payload.service || (payload.status === "ok" ? "openai-compatible" : undefined);
                    if (expectedService && service !== expectedService) {
                        reject(new Error(`Service mismatch: expected '${expectedService}', got '${service}'`));
                        return;
                    }
                    const protocol = payload.protocolVersion || payload.version;
                    if (expectedProtocolVersion && !protocol) {
                        reject(new Error("Server did not report a protocol version (Fail-Closed)."));
                        return;
                    }
                    if (expectedProtocolVersion && String(protocol) !== expectedProtocolVersion) {
                        reject(new Error(`Protocol version mismatch: expected '${expectedProtocolVersion}', got '${protocol}'`));
                        return;
                    }
                    const modelObj = payload.model;
                    const modelId = typeof modelObj === "object" ? modelObj?.id : (typeof modelObj === "string" ? modelObj : undefined);
                    if (expectedModelId && modelId && modelId !== expectedModelId) {
                        reject(new Error(`Model ID mismatch: expected '${expectedModelId}', got '${modelId}'`));
                        return;
                    }
                    resolve(payload);
                } catch (err) {
                    reject(new Error(`Failed to parse health JSON response: ${err.message}`));
                }
            });
        });
        req.on("error", err => reject(new Error(`Connection refused to ${endpoint}: ${err.message}`)));
        req.on("timeout", () => {
            req.destroy();
            reject(new Error(`Connection timed out after ${timeoutMs}ms`));
        });
    });
}

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

    static async connect(endpoint = "http://127.0.0.1:8080", options = {}) {
        if (!options.skipVerification) {
            await verifyServerIdentity(endpoint, {
                timeoutMs: 2000,
                expectedProtocolVersion: options.expectedProtocolVersion,
                expectedModelId: options.model
            });
        }
        return new LocalAgent({ endpoint, ...options });
    }

    static async local(model = "qwen2.5-1.5b", options = {}) {
        const endpoint = options.endpoint || "http://127.0.0.1:8080";
        if (!options.skipVerification) {
            await verifyServerIdentity(endpoint, {
                timeoutMs: 2000,
                expectedModelId: model
            });
        }
        return new LocalAgent({ endpoint, model, ...options });
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