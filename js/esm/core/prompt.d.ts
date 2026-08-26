/**
 * ==============================================================================
 * @termux-ai/chain Core Prompt Templates
 * ==============================================================================
 */
import { Message, RoleType } from "./schema.js";
export declare function extractVariables(templateStr: string): string[];
export declare class PromptTemplate {
    template: string;
    inputVariables: string[];
    partialVariables: Record<string, any>;
    constructor(template: string, inputVariables?: string[], partialVariables?: Record<string, any>);
    static fromTemplate(template: string): PromptTemplate;
    partial(variables: Record<string, any>): PromptTemplate;
    format(variables?: Record<string, any>): string;
    invoke(input: any): Promise<string>;
    pipe(next: any): any;
}
export declare class ChatPromptTemplate {
    messages: Array<{
        role: RoleType;
        template: PromptTemplate;
    }>;
    inputVariables: string[];
    constructor(messages: Array<[RoleType, string] | {
        role: RoleType;
        template: PromptTemplate;
    }>);
    static fromMessages(messages: Array<[RoleType, string]>): ChatPromptTemplate;
    formatMessages(variables?: Record<string, any>): Message[];
    invoke(input: any): Promise<Message[]>;
    pipe(next: any): any;
}
