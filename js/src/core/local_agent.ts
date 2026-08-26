/**
 * ==============================================================================
 * @termux-ai/chain LocalAgent Runtime (TypeScript ESM)
 * ==============================================================================
 * Sovereign enterprise agent runtime with fail-closed identity verification,
 * /v1/models capability enumeration fallback, and verifier dependency injection.
 */
import * as http from "node:http";
import * as https from "node:https";
import { URL } from "node:url";
import { OpenAICompatibleChat } from "./providers/openai_compatible.js";
import { HumanMessage } from "./schema.js";
import { createReactAgent, Tool, ToolPolicy, AgentState } from "../graph/agent.js";
import { CompiledGraph } from "../graph/state.js";

export interface VerifyServerIdentityOptions {
    timeoutMs?: number;
    expectedService?: string;
    expectedProtocolVersion?: string;
    expectedModelId?: string;
}

export interface ServerIdentityPayload {
    status?: string;
    service?: string;
    engine?: string;
    protocolVersion?: string;
    version?: string;
    model?: { id?: string; sha256?: string };
    [key: string]: any;
}

export async function verifyServerIdentity(
    endpoint: string,
    options: VerifyServerIdentityOptions = {}
): Promise<ServerIdentityPayload> {
    const {
        timeoutMs = 2000,
        expectedService,
        expectedProtocolVersion,
        expectedModelId
    } = options;

    const baseUrl = endpoint.replace(/\/+$/, "");
    const healthUrl = new URL(`${baseUrl}/health`);
    const transport = healthUrl.protocol === "https:" ? https : http;

    const queryEndpoint = (targetUrl: URL): Promise<ServerIdentityPayload> => {
        return new Promise((resolve, reject) => {
            const req = transport.get(targetUrl, {
                headers: { Accept: "application/json" },
                timeout: timeoutMs
            }, (res) => {
                if (res.statusCode !== 200) {
                    reject(new Error(`Server health check returned HTTP status ${res.statusCode}`));
                    return;
                }
                let data = "";
                res.on("data", (chunk: Buffer | string) => {
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
                        resolve(payload);
                    } catch (err: any) {
                        reject(new Error(`Failed to parse health JSON response: ${err.message}`));
                    }
                });
            });
            req.on("error", (err: Error) => reject(new Error(`Connection refused to ${endpoint}: ${err.message}`)));
            req.on("timeout", () => {
                req.destroy();
                reject(new Error(`Connection timed out after ${timeoutMs}ms`));
            });
        });
    };

    const payload = await queryEndpoint(healthUrl);

    let service = payload.service || payload.engine || (["ok", "loading model", "success"].includes(payload.status || "") ? "openai-compatible" : undefined);
    if (!service) {
        throw new Error(`Incompatible or missing service status (status='${payload.status}').`);
    }

    const protocol = payload.protocolVersion || payload.version;
    if (expectedProtocolVersion && !protocol) {
        throw new Error("Server did not report a protocol version (Fail-Closed).");
    }
    if (expectedProtocolVersion && String(protocol) !== expectedProtocolVersion) {
        throw new Error(`Protocol version mismatch: expected '${expectedProtocolVersion}', got '${protocol}'`);
    }

    const modelObj = payload.model;
    let modelId = typeof modelObj === "object" ? modelObj?.id : (typeof modelObj === "string" ? modelObj : undefined);
    let discoveredModelIds: string[] = [];

    // Fallback to /v1/models query if modelId is absent or if expectedService requires model enumeration
    if (!modelId && (expectedModelId || expectedService === "llama-server" || expectedService === "bitnet-server")) {
        try {
            const modelsUrl = new URL(`${baseUrl}/v1/models`);
            const modelsPayload = await queryEndpoint(modelsUrl);
            const dataList = Array.isArray(modelsPayload?.data) ? modelsPayload.data : [];
            discoveredModelIds = dataList.map((item: any) => item?.id).filter((id: any) => typeof id === "string");
            if (discoveredModelIds.length > 0 && !modelId) {
                if (expectedModelId && discoveredModelIds.includes(expectedModelId)) {
                    modelId = expectedModelId;
                } else if (!expectedModelId) {
                    modelId = discoveredModelIds[0];
                }
            }
        } catch {
            // models query error preserved for fail-closed handling
        }
    }

    // Service matching with upstream capability fallback
    if (expectedService) {
        if (service === expectedService) {
            // direct match
        } else if (service === "openai-compatible" && ["llama-server", "bitnet-server"].includes(expectedService)) {
            if (!modelId && discoveredModelIds.length === 0) {
                throw new Error(`Server does not exhibit required '${expectedService}' capability (missing /v1/models enumeration).`);
            }
            service = expectedService;
        } else {
            throw new Error(`Service mismatch: expected '${expectedService}', got '${service}'`);
        }
    }

    // Strict Fail-Closed Model ID Verification
    if (expectedModelId) {
        if (modelId) {
            if (modelId !== expectedModelId && !discoveredModelIds.includes(expectedModelId)) {
                throw new Error(`Model ID mismatch: expected '${expectedModelId}', got '${modelId}'`);
            }
            if (modelId !== expectedModelId && discoveredModelIds.includes(expectedModelId)) {
                modelId = expectedModelId;
            }
        } else {
            if (discoveredModelIds.includes(expectedModelId)) {
                modelId = expectedModelId;
            } else if (discoveredModelIds.length > 0) {
                throw new Error(`Model ID mismatch: expected '${expectedModelId}', available: ${discoveredModelIds.join(", ")}`);
            } else {
                throw new Error("Expected model ID was configured, but the server did not provide model identity.");
            }
        }
    }

    payload.service = service;
    payload.model = { id: modelId };
    return payload;
}

export interface LocalAgentOptions {
    endpoint?: string;
    apiKey?: string;
    model?: string;
    systemPrompt?: string;
    tools?: Tool[];
    toolPolicy?: ToolPolicy;
    approvalCallback?: (toolName: string, args: Record<string, any>) => boolean | Promise<boolean>;
    identityVerifier?: (endpoint: string, options?: VerifyServerIdentityOptions) => Promise<ServerIdentityPayload>;
    timeoutMs?: number;
    expectedService?: string;
    expectedProtocolVersion?: string;
    expectedModelId?: string;
}

export class LocalAgent {
    public model: OpenAICompatibleChat;
    public tools: Tool[];
    public systemPrompt?: string;
    public graph: CompiledGraph<AgentState>;

    constructor(options: LocalAgentOptions | string = {}) {
        const resolvedOptions: LocalAgentOptions = typeof options === "string" ? { endpoint: options } : options;
        const endpoint = resolvedOptions.endpoint ?? "http://127.0.0.1:8080";
        const apiKey = resolvedOptions.apiKey;
        const modelName = resolvedOptions.model ?? "default";
        const systemPrompt = resolvedOptions.systemPrompt;
        const tools = resolvedOptions.tools ?? [];

        this.model = new OpenAICompatibleChat({
            baseUrl: `${endpoint.replace(/\/+$/, "")}/v1`,
            model: modelName,
            apiKey
        });
        this.tools = tools;
        this.systemPrompt = systemPrompt;
        this.graph = createReactAgent(this.model, this.tools, {
            systemPrompt: this.systemPrompt,
            toolPolicy: resolvedOptions.toolPolicy ?? { default: "deny", allowedTools: this.tools.map(t => t.name) },
            approvalCallback: resolvedOptions.approvalCallback
        });
    }

    static async connect(endpoint: string = "http://127.0.0.1:8080", options: LocalAgentOptions = {}): Promise<LocalAgent> {
        const verifier = options.identityVerifier ?? verifyServerIdentity;
        await verifier(endpoint, {
            timeoutMs: options.timeoutMs ?? 2000,
            expectedService: options.expectedService,
            expectedProtocolVersion: options.expectedProtocolVersion,
            expectedModelId: options.expectedModelId ?? options.model
        });
        return new LocalAgent({ endpoint, ...options });
    }

    static async local(model: string = "qwen2.5-1.5b", options: LocalAgentOptions = {}): Promise<LocalAgent> {
        const endpoint = options.endpoint || "http://127.0.0.1:8080";
        const verifier = options.identityVerifier ?? verifyServerIdentity;
        await verifier(endpoint, {
            timeoutMs: options.timeoutMs ?? 2000,
            expectedService: options.expectedService ?? "llama-server",
            expectedModelId: model
        });
        return new LocalAgent({ endpoint, model, ...options });
    }

    async invoke(inputData: Partial<AgentState> | Record<string, any>, maxIterations: number = 10): Promise<AgentState> {
        return await this.graph.invoke(inputData as any, maxIterations);
    }

    async run(promptOrInput: string | Record<string, any>, maxIterations: number = 10): Promise<string> {
        let payload: Record<string, any>;
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
