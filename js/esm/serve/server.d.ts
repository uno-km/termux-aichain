/**
 * ==============================================================================
 * @termux-ai/chain Serve Engine: 1-Line REST & SSE Serving (TypeScript ESM)
 * ==============================================================================
 */
import { Runnable } from "../core/base.js";
export declare function serve(runnable: Runnable, options?: {
    host?: string;
    port?: number;
    endpointPrefix?: string;
}): any;
