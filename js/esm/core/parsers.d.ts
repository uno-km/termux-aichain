/**
 * ==============================================================================
 * @termux-ai/chain Core Structured Output Parsers
 * ==============================================================================
 */
import { Runnable } from "./base.js";
export declare abstract class BaseOutputParser<T = any> implements Runnable<any, T> {
    invoke(input: any): Promise<T>;
    pipe<NextOutput>(next: any): any;
    protected extractText(input: any): string;
    abstract parse(text: string): T;
}
export declare class StringOutputParser extends BaseOutputParser<string> {
    private strip;
    constructor(strip?: boolean);
    parse(text: string): string;
}
export declare class JsonOutputParser<T = any> extends BaseOutputParser<T> {
    private defaultFactory?;
    constructor(defaultFactory?: () => T);
    parse(text: string): T;
}
