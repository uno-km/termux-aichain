/**
 * ==============================================================================
 * @termux-ai/chain Trace Engine: Lightweight CLI Observability (TypeScript ESM)
 * ==============================================================================
 */
export interface TraceSpanData {
    name: string;
    durationMs: number;
    tokens: number;
    tps: number;
    error?: string;
    metadata: Record<string, any>;
    children: TraceSpanData[];
}
export declare class TraceSpan {
    name: string;
    startTime: number;
    endTime?: number;
    inputs?: any;
    outputs?: any;
    tokens: number;
    metadata: Record<string, any>;
    children: TraceSpan[];
    error?: string;
    constructor(name: string, inputs?: any, metadata?: Record<string, any>);
    get durationMs(): number;
    get tps(): number;
    finish(outputs?: any, tokens?: number, error?: Error): void;
    toJSON(): TraceSpanData;
}
export declare class Tracer {
    rootSpan: TraceSpan;
    private stack;
    constructor(rootName?: string);
    trace<T>(name: string, fn: (span: TraceSpan) => Promise<T> | T, metadata?: Record<string, any>): Promise<T>;
    finish(outputs?: any): void;
    renderTree(useColor?: boolean): string;
    printTree(): void;
}
