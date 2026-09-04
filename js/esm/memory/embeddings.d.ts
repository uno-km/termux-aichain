/**
 * ==============================================================================
 * @termux-ai/chain Embeddings Engine: Zero-Dependency Vectorizers (Node.js ESM)
 * ==============================================================================
 * Provides standard BaseEmbeddings, LocalEmbeddings (llama-server /v1/embeddings),
 * and SparseBM25Embeddings (pure math zero-state offline vectorizer).
 * Zero external heavy dependencies - Pure Node.js 18+ standard library.
 */
export interface BaseEmbeddings {
    embedDocuments(texts: string[]): Promise<number[][]>;
    embedQuery(text: string): Promise<number[]>;
}
export declare class LocalEmbeddings implements BaseEmbeddings {
    baseUrl: string;
    endpoint: string;
    model: string;
    timeoutMs: number;
    batchSize: number;
    apiKey?: string;
    constructor(options?: {
        baseUrl?: string;
        model?: string;
        timeoutMs?: number;
        batchSize?: number;
        apiKey?: string;
    });
    static local(options?: {
        endpoint?: string;
        model?: string;
    }): LocalEmbeddings;
    private postBatch;
    embedDocuments(texts: string[]): Promise<number[][]>;
    embedQuery(text: string): Promise<number[]>;
}
export declare class SparseBM25Embeddings implements BaseEmbeddings {
    dimension: number;
    k1: number;
    b: number;
    private docCount;
    private docFreq;
    private avgDl;
    constructor(dimension?: number, k1?: number, b?: number);
    private tokenize;
    private hashToken;
    embedDocuments(texts: string[]): Promise<number[][]>;
    embedQuery(text: string): Promise<number[]>;
}
