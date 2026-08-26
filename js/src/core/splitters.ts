/**
 * ==============================================================================
 * @termux-ai/chain Core Text Splitters & Micro Document Loaders
 * ==============================================================================
 */

export interface Document {
  pageContent: string;
  metadata: Record<string, any>;
}

export interface SplitterOptions {
  chunkSize?: number;
  chunkOverlap?: number;
  lengthFunction?: (text: string) => number;
}

export class CharacterTextSplitter {
  separator: string;
  chunkSize: number;
  chunkOverlap: number;
  lengthFunction: (text: string) => number;

  constructor(separator: string = "\n\n", options: SplitterOptions = {}) {
    this.separator = separator;
    this.chunkSize = options.chunkSize ?? 1000;
    this.chunkOverlap = options.chunkOverlap ?? 200;
    this.lengthFunction = options.lengthFunction ?? ((t: string) => t.length);

    if (this.chunkOverlap >= this.chunkSize) {
      throw new Error(`chunkOverlap (${this.chunkOverlap}) must be less than chunkSize (${this.chunkSize})`);
    }
  }

  splitText(text: string): string[] {
    const splits = this.separator ? text.split(this.separator) : Array.from(text);
    return this.mergeSplits(splits, this.separator);
  }

  private mergeSplits(splits: string[], separator: string): string[] {
    const docs: string[] = [];
    const currentDoc: string[] = [];
    let totalLen = 0;
    const sepLen = this.lengthFunction(separator);

    for (const s of splits) {
      const sLen = this.lengthFunction(s);
      if (currentDoc.length > 0 && totalLen + sepLen + sLen > this.chunkSize) {
        const merged = currentDoc.join(separator);
        if (merged.trim()) docs.push(merged);

        while (currentDoc.length > 0 && totalLen > this.chunkOverlap) {
          const popped = currentDoc.shift()!;
          totalLen -= this.lengthFunction(popped) + sepLen;
        }
      }
      currentDoc.push(s);
      totalLen += sLen + (currentDoc.length > 1 ? sepLen : 0);
    }

    if (currentDoc.length > 0) {
      const merged = currentDoc.join(separator);
      if (merged.trim()) docs.push(merged);
    }

    return docs;
  }
}

export class RecursiveCharacterTextSplitter {
  separators: string[];
  chunkSize: number;
  chunkOverlap: number;
  lengthFunction: (text: string) => number;

  constructor(options: SplitterOptions & { separators?: string[] } = {}) {
    this.separators = options.separators ?? ["\n\n", "\n", ". ", "? ", "! ", " ", ""];
    this.chunkSize = options.chunkSize ?? 1000;
    this.chunkOverlap = options.chunkOverlap ?? 200;
    this.lengthFunction = options.lengthFunction ?? ((t: string) => t.length);
  }

  splitText(text: string): string[] {
    return this.splitRecursive(text, this.separators);
  }

  private splitRecursive(text: string, separators: string[]): string[] {
    const finalChunks: string[] = [];
    let separator = separators[separators.length - 1];
    let newSeparators: string[] = [];

    for (let i = 0; i < separators.length; i++) {
      const s = separators[i];
      if (s === "") {
        separator = "";
        break;
      }
      if (text.includes(s)) {
        separator = s;
        newSeparators = separators.slice(i + 1);
        break;
      }
    }

    const splits = separator ? text.split(separator) : Array.from(text);
    let goodSplits: string[] = [];

    for (const s of splits) {
      if (this.lengthFunction(s) < this.chunkSize) {
        goodSplits.push(s);
      } else {
        if (goodSplits.length > 0) {
          finalChunks.push(...this.mergeSplits(goodSplits, separator));
          goodSplits = [];
        }
        if (newSeparators.length === 0) {
          finalChunks.push(s);
        } else {
          finalChunks.push(...this.splitRecursive(s, newSeparators));
        }
      }
    }

    if (goodSplits.length > 0) {
      finalChunks.push(...this.mergeSplits(goodSplits, separator));
    }

    return finalChunks;
  }

  private mergeSplits(splits: string[], separator: string): string[] {
    const splitter = new CharacterTextSplitter(separator, {
      chunkSize: this.chunkSize,
      chunkOverlap: this.chunkOverlap,
      lengthFunction: this.lengthFunction
    });
    return (splitter as any).mergeSplits(splits, separator);
  }
}