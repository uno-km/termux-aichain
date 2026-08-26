/**
 * ==============================================================================
 * @termux-ai/chain Graph Engine: StateGraph & Cyclic State Machine (TypeScript ESM)
 * ==============================================================================
 */

export const START = "__start__";
export const END = "__end__";

export type StateNodeFn<T = any> = (state: T) => Promise<Partial<T> | void> | Partial<T> | void;
export type ConditionFn<T = any> = (state: T) => Promise<string> | string;

export interface ConditionalEdge<T = any> {
  condition: ConditionFn<T>;
  pathMap: Record<string, string>;
}

export class StateGraph<T = Record<string, any>> {
  nodes: Map<string, StateNodeFn<T>> = new Map();
  edges: Map<string, string> = new Map();
  conditionalEdges: Map<string, ConditionalEdge<T>> = new Map();
  entryPoint?: string;

  constructor(stateSchema?: any) {}

  addNode(name: string, fn: StateNodeFn<T>): this {
    this.nodes.set(name, fn);
    return this;
  }

  addEdge(fromNode: string, toNode: string): this {
    if (fromNode === START) {
      this.entryPoint = toNode;
    } else {
      this.edges.set(fromNode, toNode);
    }
    return this;
  }

  setEntryPoint(nodeName: string): this {
    this.entryPoint = nodeName;
    return this;
  }

  addConditionalEdges(fromNode: string, condition: ConditionFn<T>, pathMap: Record<string, string>): this {
    this.conditionalEdges.set(fromNode, { condition, pathMap });
    return this;
  }

  compile(): CompiledGraph<T> {
    if (!this.entryPoint) {
      throw new Error("No entry point defined. Call setEntryPoint or addEdge(START, ...).");
    }
    return new CompiledGraph<T>(
      new Map(this.nodes),
      new Map(this.edges),
      new Map(this.conditionalEdges),
      this.entryPoint
    );
  }
}

export class CompiledGraph<T = Record<string, any>> {
  nodes: Map<string, StateNodeFn<T>>;
  edges: Map<string, string>;
  conditionalEdges: Map<string, ConditionalEdge<T>>;
  entryPoint: string;

  constructor(
    nodes: Map<string, StateNodeFn<T>>,
    edges: Map<string, string>,
    conditionalEdges: Map<string, ConditionalEdge<T>>,
    entryPoint: string
  ) {
    this.nodes = nodes;
    this.edges = edges;
    this.conditionalEdges = conditionalEdges;
    this.entryPoint = entryPoint;
  }

  async invoke(initialState: T, maxIterations: number = 25): Promise<T> {
    let currentState: T = { ...initialState };
    let currentNode: string | undefined = this.entryPoint;
    let iterations = 0;

    while (currentNode && currentNode !== END) {
      iterations++;
      if (iterations > maxIterations) {
        throw new Error(`Graph execution exceeded max iterations limit (${maxIterations}).`);
      }

      const nodeFn = this.nodes.get(currentNode);
      if (!nodeFn) {
        throw new Error(`Node '${currentNode}' is not defined in graph.`);
      }

      const result = await nodeFn(currentState);
      if (result && typeof result === "object") {
        currentState = { ...currentState, ...result };
      }

      const condEdge: ConditionalEdge<T> | undefined = this.conditionalEdges.get(currentNode);
      if (condEdge) {
        const targetKey: string = await Promise.resolve(condEdge.condition(currentState));
        currentNode = condEdge.pathMap[targetKey];
      } else if (this.edges.has(currentNode)) {
        currentNode = this.edges.get(currentNode);
      } else {
        currentNode = END;
      }
    }

    return currentState;
  }

  async *stream(initialState: T, maxIterations: number = 25): AsyncGenerator<[string, T]> {
    let currentState: T = { ...initialState };
    let currentNode: string | undefined = this.entryPoint;
    let iterations = 0;

    while (currentNode && currentNode !== END) {
      iterations++;
      if (iterations > maxIterations) {
        throw new Error(`Graph execution exceeded max iterations limit (${maxIterations}).`);
      }

      const nodeFn = this.nodes.get(currentNode);
      if (!nodeFn) {
        throw new Error(`Node '${currentNode}' is not defined in graph.`);
      }

      const result = await nodeFn(currentState);
      if (result && typeof result === "object") {
        currentState = { ...currentState, ...result };
      }
      yield [currentNode, currentState];

      const condEdge: ConditionalEdge<T> | undefined = this.conditionalEdges.get(currentNode);
      if (condEdge) {
        const targetKey: string = await Promise.resolve(condEdge.condition(currentState));
        currentNode = condEdge.pathMap[targetKey];
      } else if (this.edges.has(currentNode)) {
        currentNode = this.edges.get(currentNode);
      } else {
        currentNode = END;
      }
    }
  }
}