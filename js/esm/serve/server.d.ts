/**
 * ==============================================================================
 * @termux-ai/chain Serve Engine: 1-Line REST & SSE Serving (TypeScript ESM)
 * ==============================================================================
 */
import * as http from "node:http";
export interface ServeOptions {
    host?: string;
    port?: number;
    endpointPrefix?: string;
    apiKey?: string;
    maxBodyBytes?: number;
    corsOrigins?: string[];
}
export declare function readJsonBody(req: http.IncomingMessage, maxBodyBytes: number): Promise<Record<string, any>>;
export declare function serve(runnable: any, options?: ServeOptions): http.Server;
