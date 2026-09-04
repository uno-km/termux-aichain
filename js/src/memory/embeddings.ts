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

export class LocalEmbeddings implements BaseEmbeddings {
  public baseUrl: string;
  public endpoint: string;
  public model: string;
  public timeoutMs: number;
  public batchSize: number;
  public apiKey?: string;

  constructor(options?: {
    baseUrl?: string;
    model?: string;
    timeoutMs?: number;
    batchSize?: number;
    apiKey?: string;
  }) {
    this.baseUrl = (options?.baseUrl ?? "http://127.0.0.1:8080/v1").replace(/\/+$/, "");
    this.endpoint = `${this.baseUrl}/embeddings`;
    this.model = options?.model ?? "default";
    this.timeoutMs = options?.timeoutMs ?? 30000;
    this.batchSize = Math.max(1, options?.batchSize ?? 16);
    this.apiKey = options?.apiKey;
  }

  static local(options?: { endpoint?: string; model?: string }): LocalEmbeddings {
    const ep = options?.endpoint ?? "http://127.0.0.1:8080";
    return new LocalEmbeddings({
      baseUrl: `${ep.replace(/\/+$/, "")}/v1`,
      model: options?.model ?? "bge-micro"
    });
  }

  private async postBatch(texts: string[]): Promise<number[][]> {
    const payload = JSON.stringify({
      model: this.model,
      input: texts
    });

    const headers: Record<string, string> = {
      "Content-Type": "application/json"
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const resp = await fetch(this.endpoint, {
        method: "POST",
        headers,
        body: payload,
        signal: controller.signal
      });

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(`Embedding request failed (HTTP ${resp.status}): ${errText}`);
      }

      const body: any = await resp.json();
      if (!body.data || !Array.isArray(body.data)) {
        throw new Error("Invalid response schema from embeddings endpoint.");
      }

      const sorted = [...body.data].sort((a, b) => (a.index ?? 0) - (b.index ?? 0));
      return sorted.map((item: any) => {
        const emb = item.embedding;
        if (!Array.isArray(emb) || emb.length === 0) {
          throw new Error("Invalid embedding vector returned by server.");
        }
        return emb;
      });
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async embedDocuments(texts: string[]): Promise<number[][]> {
    if (!texts || texts.length === 0) return [];
    const results: number[][] = [];
    for (let i = 0; i < texts.length; i += this.batchSize) {
      const chunk = texts.slice(i, i + this.batchSize);
      const batchEmbs = await this.postBatch(chunk);
      results.push(...batchEmbs);
    }
    return results;
  }

  async embedQuery(text: string): Promise<number[]> {
    const res = await this.embedDocuments([text]);
    if (!res || res.length === 0) {
      throw new Error("Empty embedding returned for query.");
    }
    return res[0];
  }
}

export class SparseBM25Embeddings implements BaseEmbeddings {
  public dimension: number;
  public k1: number;
  public b: number;
  private docCount: number = 0;
  private docFreq: Map<string, number> = new Map();
  private avgDl: number = 1.0;

  constructor(dimension: number = 256, k1: number = 1.5, b: number = 0.75) {
    this.dimension = dimension;
    this.k1 = k1;
    this.b = b;
  }

  private tokenize(text: string): string[] {
    const tokens = text.toLowerCase().match(/\w+/g) || [];
    return tokens.filter(t => t.length > 1);
  }

  private hashToken(token: string): number {
    let h = 0;
    for (let i = 0; i < token.length; i++) {
      h = (h * 31 + token.charCodeAt(i)) >>> 0;
    }
    return h % this.dimension;
  }

  async embedDocuments(texts: string[]): Promise<number[][]> {
    if (!texts || texts.length === 0) return [];

    const docTokensList = texts.map(t => this.tokenize(t));
    this.docCount += texts.length;
    const totalLen = docTokensList.reduce((acc, toks) => acc + toks.length, 0);
    this.avgDl = Math.max(1.0, totalLen / Math.max(1, docTokensList.length));

    for (const toks of docTokensList) {
      const uniqueTerms = new Set(toks);
      for (const term of uniqueTerms) {
        this.docFreq.set(term, (this.docFreq.get(term) ?? 0) + 1);
      }
    }

    const results: number[][] = [];
    for (const toks of docTokensList) {
      const vec = new Array(this.dimension).fill(0.0);
      if (toks.length === 0) {
        results.push(vec);
        continue;
      }

      const tf = new Map<string, number>();
      for (const t of toks) {
        tf.set(t, (tf.get(t) ?? 0) + 1);
      }

      const dl = toks.length;
      for (const [term, count] of tf.entries()) {
        const slot = this.hashToken(term);
        const df = this.docFreq.get(term) ?? 1;
        const idf = Math.log(1.0 + (this.docCount - df + 0.5) / (df + 0.5));
        const bm25Tf = (count * (this.k1 + 1.0)) / (count + this.k1 * (1.0 - this.b + this.b * (dl / this.avgDl)));
        vec[slot] += Math.max(0.0, idf * bm25Tf);
      }

      const norm = Math.sqrt(vec.reduce((sum, v) => sum + v * v, 0));
      results.push(norm > 0 ? vec.map(v => v / norm) : vec);
    }
    return results;
  }

  async embedQuery(text: string): Promise<number[]> {
    const toks = this.tokenize(text);
    const vec = new Array(this.dimension).fill(0.0);
    if (toks.length === 0) return vec;

    const tf = new Map<string, number>();
    for (const t of toks) {
      tf.set(t, (tf.get(t) ?? 0) + 1);
    }

    const dl = toks.length;
    for (const [term, count] of tf.entries()) {
      const slot = this.hashToken(term);
      const df = this.docFreq.get(term) ?? 1;
      const idf = Math.log(1.0 + (this.docCount - df + 0.5) / (df + 0.5));
      const bm25Tf = (count * (this.k1 + 1.0)) / (count + this.k1 * (1.0 - this.b + this.b * (dl / this.avgDl)));
      vec[slot] += Math.max(0.0, idf * bm25Tf);
    }

    const norm = Math.sqrt(vec.reduce((sum, v) => sum + v * v, 0));
    return norm > 0 ? vec.map(v => v / norm) : vec;
  }
}
