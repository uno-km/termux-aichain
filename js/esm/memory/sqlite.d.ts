/**
 * ==============================================================================
 * @termux-ai/chain Memory Engine: In-Memory & Cosine Vector Store (TypeScript ESM)
 * ==============================================================================
 */
import { BaseEmbeddings } from "./embeddings.js";
export declare function cosineSimilarity(v1: number[], v2: number[]): number;
export interface VectorItem {
    id: string;
    content: string;
    metadata: Record<string, any>;
    embedding: number[];
}
export declare class MicroVectorStore {
    private items;
    embeddings?: BaseEmbeddings;
    constructor(options?: {
        embeddings?: BaseEmbeddings;
    });
    addTexts(texts: string[], embeddings?: number[][], metadatas?: Record<string, any>[]): Promise<string[]>;
    similaritySearchByVector(queryEmbedding: number[], k?: number): Array<{
        content: string;
        metadata: Record<string, any>;
        score: number;
    }>;
    similaritySearch(query: string, k?: number): Promise<Array<{
        content: string;
        metadata: Record<string, any>;
        score: number;
    }>>;
    hybridSearch(query: string, k?: number, alpha?: number): Promise<Array<{
        content: string;
        metadata: Record<string, any>;
        score: number;
    }>>;
    clear(): void;
}
