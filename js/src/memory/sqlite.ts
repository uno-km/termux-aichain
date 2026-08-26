/**
 * ==============================================================================
 * @termux-ai/chain Memory Engine: In-Memory & Cosine Vector Store (TypeScript ESM)
 * ==============================================================================
 */

export function cosineSimilarity(v1: number[], v2: number[]): number {
  if (v1.length !== v2.length || v1.length === 0) return 0;
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < v1.length; i++) {
    dot += v1[i] * v2[i];
    normA += v1[i] * v1[i];
    normB += v2[i] * v2[i];
  }
  normA = Math.sqrt(normA);
  normB = Math.sqrt(normB);
  if (normA === 0 || normB === 0) return 0;
  return dot / (normA * normB);
}

export interface VectorItem {
  id: string;
  content: string;
  metadata: Record<string, any>;
  embedding: number[];
}

export class MicroVectorStore {
  private items: VectorItem[] = [];

  addTexts(texts: string[], embeddings: number[][], metadatas?: Record<string, any>[]): string[] {
    const ids: string[] = [];
    for (let i = 0; i < texts.length; i++) {
      const id = String(this.items.length + 1);
      this.items.push({
        id,
        content: texts[i],
        metadata: metadatas?.[i] ?? {},
        embedding: embeddings[i]
      });
      ids.push(id);
    }
    return ids;
  }

  similaritySearchByVector(queryEmbedding: number[], k: number = 4): Array<{ content: string; metadata: Record<string, any>; score: number }> {
    const scored = this.items.map(item => ({
      content: item.content,
      metadata: item.metadata,
      score: cosineSimilarity(queryEmbedding, item.embedding)
    }));
    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, k);
  }
}