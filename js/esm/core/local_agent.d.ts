import { OpenAICompatibleChat } from "./providers/openai_compatible.js";
import { Tool, ToolPolicy, AgentState } from "../graph/agent.js";
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
    model?: {
        id?: string;
        sha256?: string;
    };
    [key: string]: any;
}
export declare function verifyServerIdentity(endpoint: string, options?: VerifyServerIdentityOptions): Promise<ServerIdentityPayload>;
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
export declare class LocalAgent {
    model: OpenAICompatibleChat;
    tools: Tool[];
    systemPrompt?: string;
    graph: CompiledGraph<AgentState>;
    constructor(options?: LocalAgentOptions | string);
    static connect(endpoint?: string, options?: LocalAgentOptions): Promise<LocalAgent>;
    static local(model?: string, options?: LocalAgentOptions): Promise<LocalAgent>;
    invoke(inputData: Partial<AgentState> | Record<string, any>, maxIterations?: number): Promise<AgentState>;
    run(promptOrInput: string | Record<string, any>, maxIterations?: number): Promise<string>;
}
