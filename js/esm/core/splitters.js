/**
 * ==============================================================================
 * @termux-ai/chain Core Text Splitters & Micro Document Loaders
 * ==============================================================================
 */
export class CharacterTextSplitter {
    separator;
    chunkSize;
    chunkOverlap;
    lengthFunction;
    constructor(separator = "\n\n", options = {}) {
        this.separator = separator;
        this.chunkSize = options.chunkSize ?? 1000;
        this.chunkOverlap = options.chunkOverlap ?? 200;
        this.lengthFunction = options.lengthFunction ?? ((t) => t.length);
        if (this.chunkOverlap >= this.chunkSize) {
            throw new Error(`chunkOverlap (${this.chunkOverlap}) must be less than chunkSize (${this.chunkSize})`);
        }
    }
    splitText(text) {
        const splits = this.separator ? text.split(this.separator) : Array.from(text);
        return this.mergeSplits(splits, this.separator);
    }
    mergeSplits(splits, separator) {
        const docs = [];
        const currentDoc = [];
        let totalLen = 0;
        const sepLen = this.lengthFunction(separator);
        for (const s of splits) {
            const sLen = this.lengthFunction(s);
            if (currentDoc.length > 0 && totalLen + sepLen + sLen > this.chunkSize) {
                const merged = currentDoc.join(separator);
                if (merged.trim())
                    docs.push(merged);
                while (currentDoc.length > 0 && totalLen > this.chunkOverlap) {
                    const popped = currentDoc.shift();
                    totalLen -= this.lengthFunction(popped) + sepLen;
                }
            }
            currentDoc.push(s);
            totalLen += sLen + (currentDoc.length > 1 ? sepLen : 0);
        }
        if (currentDoc.length > 0) {
            const merged = currentDoc.join(separator);
            if (merged.trim())
                docs.push(merged);
        }
        return docs;
    }
}
export class RecursiveCharacterTextSplitter {
    separators;
    chunkSize;
    chunkOverlap;
    lengthFunction;
    constructor(options = {}) {
        this.separators = options.separators ?? ["\n\n", "\n", ". ", "? ", "! ", " ", ""];
        this.chunkSize = options.chunkSize ?? 1000;
        this.chunkOverlap = options.chunkOverlap ?? 200;
        this.lengthFunction = options.lengthFunction ?? ((t) => t.length);
    }
    splitText(text) {
        return this.splitRecursive(text, this.separators);
    }
    splitRecursive(text, separators) {
        const finalChunks = [];
        let separator = separators[separators.length - 1];
        let newSeparators = [];
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
        let goodSplits = [];
        for (const s of splits) {
            if (this.lengthFunction(s) < this.chunkSize) {
                goodSplits.push(s);
            }
            else {
                if (goodSplits.length > 0) {
                    finalChunks.push(...this.mergeSplits(goodSplits, separator));
                    goodSplits = [];
                }
                if (newSeparators.length === 0) {
                    finalChunks.push(s);
                }
                else {
                    finalChunks.push(...this.splitRecursive(s, newSeparators));
                }
            }
        }
        if (goodSplits.length > 0) {
            finalChunks.push(...this.mergeSplits(goodSplits, separator));
        }
        return finalChunks;
    }
    mergeSplits(splits, separator) {
        const splitter = new CharacterTextSplitter(separator, {
            chunkSize: this.chunkSize,
            chunkOverlap: this.chunkOverlap,
            lengthFunction: this.lengthFunction
        });
        return splitter.mergeSplits(splits, separator);
    }
}
