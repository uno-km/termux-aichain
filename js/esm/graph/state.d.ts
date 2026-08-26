/**
 * ==============================================================================
 * @termux-ai/chain Graph Engine: StateGraph & Cyclic State Machine (TypeScript ESM)
 * ==============================================================================
 */
export declare const START = "__start__";
export declare const END = "__end__";
export type StateNodeFn<T = any> = (state: T) => Promise<Partial<T> | void> | Partial<T> | void;
export type ConditionFn<T = any> = (state: T) => Promise<string> | string;
export interface ConditionalEdge<T = any> {
    condition: ConditionFn<T>;
    pathMap?: Record<string, string>;
}
export declare class StateGraph<T = Record<string, any>> {
    nodes: Map<string, StateNodeFn<T>>;
    edges: Map<string, string>;
    conditionalEdges: Map<string, ConditionalEdge<T>>;
    entryPoint?: string;
    constructor(stateSchema?: any);
    addNode(name: string, fn: StateNodeFn<T>): this;
    addEdge(fromNode: string, toNode: string): this;
    setEntryPoint(nodeName: string): this;
    setFinishPoint(nodeName: string): this;
    addConditionalEdges(fromNode: string, condition: ConditionFn<T>, pathMap?: Record<string, string>): this;
    compile(): CompiledGraph<T>;
}
export declare class CompiledGraph<T = Record<string, any>> {
    nodes: Map<string, StateNodeFn<T>>;
    edges: Map<string, string>;
    conditionalEdges: Map<string, ConditionalEdge<T>>;
    entryPoint: string;
    constructor(nodes: Map<string, StateNodeFn<T>>, edges: Map<string, string>, conditionalEdges: Map<string, ConditionalEdge<T>>, entryPoint: string);
    invoke(initialState: T, maxIterations?: number): Promise<T>;
    stream(initialState: T, maxIterations?: number): AsyncGenerator<[string, T]>;
}
