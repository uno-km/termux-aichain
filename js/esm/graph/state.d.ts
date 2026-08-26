/**
 * ==============================================================================
 * @termux-ai/chain Graph Engine: StateGraph (TypeScript ESM)
 * ==============================================================================
 */
import { Runnable } from "../core/base.js";
export declare const START = "__start__";
export declare const END = "__end__";
export type NodeAction<T = Record<string, any>> = (state: T) => Promise<Partial<T> | void> | Partial<T> | void;
export type RouterFn<T = Record<string, any>> = (state: T) => string;
export declare class StateGraph<T extends Record<string, any> = Record<string, any>> {
    private nodes;
    private edges;
    private conditionalEdges;
    private entryPoint?;
    addNode(name: string, action: NodeAction<T>): this;
    addEdge(fromNode: string, toNode: string): this;
    addConditionalEdges(source: string, router: RouterFn<T>, pathMap?: Record<string, string>): this;
    setEntryPoint(nodeName: string): this;
    setFinishPoint(nodeName: string): this;
    compile(): CompiledGraph<T>;
}
export declare class CompiledGraph<T extends Record<string, any> = Record<string, any>> implements Runnable<T, T> {
    private nodes;
    private edges;
    private conditionalEdges;
    private entryPoint;
    constructor(nodes: Map<string, NodeAction<T>>, edges: Map<string, string>, conditionalEdges: Map<string, {
        router: RouterFn<T>;
        pathMap?: Record<string, string>;
    }>, entryPoint: string);
    private getNextNode;
    invoke(input: T, options?: {
        maxIterations?: number;
    }): Promise<T>;
    stream(input: T, options?: {
        maxIterations?: number;
    }): AsyncIterable<[string, T]>;
    pipe<NextOutput>(next: any): any;
}
