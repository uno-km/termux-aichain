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
export declare class CharacterTextSplitter {
    separator: string;
    chunkSize: number;
    chunkOverlap: number;
    lengthFunction: (text: string) => number;
    constructor(separator?: string, options?: SplitterOptions);
    splitText(text: string): string[];
    private mergeSplits;
}
export declare class RecursiveCharacterTextSplitter {
    separators: string[];
    chunkSize: number;
    chunkOverlap: number;
    lengthFunction: (text: string) => number;
    constructor(options?: SplitterOptions & {
        separators?: string[];
    });
    splitText(text: string): string[];
    private splitRecursive;
    private mergeSplits;
}
