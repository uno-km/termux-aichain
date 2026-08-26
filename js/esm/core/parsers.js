/**
 * ==============================================================================
 * @termux-ai/chain Core Structured Output Parsers
 * ==============================================================================
 */
import { createPipeline } from "./base.js";
export class BaseOutputParser {
    async invoke(input) {
        const text = this.extractText(input);
        return this.parse(text);
    }
    pipe(next) {
        return createPipeline([this, next]);
    }
    extractText(input) {
        if (typeof input === "string")
            return input;
        if (input && typeof input === "object") {
            if ("content" in input && typeof input.content === "string")
                return input.content;
            if ("delta" in input && typeof input.delta === "string")
                return input.delta;
        }
        return String(input);
    }
}
export class StringOutputParser extends BaseOutputParser {
    strip;
    constructor(strip = true) {
        super();
        this.strip = strip;
    }
    parse(text) {
        return this.strip ? text.trim() : text;
    }
}
const JSON_BLOCK_REGEX = /```(?:json)?\s*([\s\S]*?)\s*```/i;
export class JsonOutputParser extends BaseOutputParser {
    defaultFactory;
    constructor(defaultFactory) {
        super();
        this.defaultFactory = defaultFactory;
    }
    parse(text) {
        const cleaned = text.trim();
        // 1. Markdown match
        const match = JSON_BLOCK_REGEX.exec(cleaned);
        if (match) {
            try {
                return JSON.parse(match[1].trim());
            }
            catch { }
        }
        // 2. Direct JSON load
        try {
            return JSON.parse(cleaned);
        }
        catch { }
        // 3. Substring match
        const startObj = cleaned.indexOf("{");
        const endObj = cleaned.lastIndexOf("}");
        if (startObj !== -1 && endObj !== -1 && endObj > startObj) {
            try {
                return JSON.parse(cleaned.slice(startObj, endObj + 1));
            }
            catch { }
        }
        const startArr = cleaned.indexOf("[");
        const endArr = cleaned.lastIndexOf("]");
        if (startArr !== -1 && endArr !== -1 && endArr > startArr) {
            try {
                return JSON.parse(cleaned.slice(startArr, endArr + 1));
            }
            catch { }
        }
        if (this.defaultFactory) {
            return this.defaultFactory();
        }
        throw new Error(`Failed to parse JSON from generation output:\n${text}`);
    }
}
