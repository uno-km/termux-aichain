/**
 * ==============================================================================
 * @termux-ai/chain Memory Engine: In-Memory & Cosine Vector Store (TypeScript ESM)
 * ==============================================================================
 */
export declare function cosineSimilarity(v1: number[], v2: number[]): number;
export interface VectorItem {
    id: string;
    content: string;
    metadata: Record<string, any>;
    embedding: number[];
}
export declare class MicroVectorStore {
    private items;
    addTexts(texts: string[], embeddings: number[][], metadatas?: Record<string, any>[]): string[];
    similaritySearchByVector(queryEmbedding: number[], k?: number): Array<{
        content: string;
        metadata: Record<string, any>;
        score: number;
    }>;
}
