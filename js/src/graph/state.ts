/**
 * ==============================================================================
 * @termux-ai/chain Graph Engine: StateGraph (TypeScript ESM)
 * ==============================================================================
 */

import { Runnable, createPipeline } from "../core/base.js";

export const START = "__start__";
export const END = "__end__";

export type NodeAction<T = Record<string, any>> = (state: T) => Promise<Partial<T> | void> | Partial<T> | void;
export type RouterFn<T = Record<string, any>> = (state: T) => string;

export class StateGraph<T extends Record<string, any> = Record<string, any>> {
  private nodes: Map<string, NodeAction<T>> = new Map();
  private edges: Map<string, string> = new Map();
  private conditionalEdges: Map<string, { router: RouterFn<T>; pathMap?: Record<string, string> }> = new Map();
  private entryPoint?: string;

  addNode(name: string, action: NodeAction<T>): this {
    if (name === START || name === END) {
      throw new Error(`Cannot use reserved name '${name}' as node.`);
    }
    this.nodes.set(name, action);
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

  addConditionalEdges(source: string, router: RouterFn<T>, pathMap?: Record<string, string>): this {
    this.conditionalEdges.set(source, { router, pathMap });
    return this;
  }

  setEntryPoint(nodeName: string): this {
    this.entryPoint = nodeName;
    return this;
  }

  setFinishPoint(nodeName: string): this {
    this.edges.set(nodeName, END);
    return this;
  }

  compile(): CompiledGraph<T> {
    if (!this.entryPoint) {
      throw new Error("StateGraph requires an entry point. Use setEntryPoint() or addEdge(START, ...).");
    }
    return new CompiledGraph<T>(
      new Map(this.nodes),
      new Map(this.edges),
      new Map(this.conditionalEdges),
      this.entryPoint
    );
  }
}

export class CompiledGraph<T extends Record<string, any> = Record<string, any>> implements Runnable<T, T> {
  private nodes: Map<string, NodeAction<T>>;
  private edges: Map<string, string>;
  private conditionalEdges: Map<string, { router: RouterFn<T>; pathMap?: Record<string, string> }>;
  private entryPoint: string;

  constructor(
    nodes: Map<string, NodeAction<T>>,
    edges: Map<string, string>,
    conditionalEdges: Map<string, { router: RouterFn<T>; pathMap?: Record<string, string> }>,
    entryPoint: string
  ) {
    this.nodes = nodes;
    this.edges = edges;
    this.conditionalEdges = conditionalEdges;
    this.entryPoint = entryPoint;
  }

  private getNextNode(currentNode: string, state: T): string {
    const cond = this.conditionalEdges.get(currentNode);
    if (cond) {
      const res = cond.router(state);
      if (cond.pathMap && res in cond.pathMap) {
        return cond.pathMap[res];
      }
      return res;
    }
    return this.edges.get(currentNode) ?? END;
  }

  async invoke(input: T, options?: { maxIterations?: number }): Promise<T> {
    const state: T = { ...input };
    let currentNode: string = this.entryPoint;
    const maxIterations = options?.maxIterations ?? 50;
    let iter = 0;

    while (currentNode !== END && iter < maxIterations) {
      const action = this.nodes.get(currentNode);
      if (!action) {
        throw new Error(`Node '${currentNode}' is not defined in graph.`);
      }

      const update = await action(state);
      if (update && typeof update === "object") {
        Object.assign(state, update);
      }

      currentNode = this.getNextNode(currentNode, state);
      iter++;
    }

    if (iter >= maxIterations) {
      throw new Error(`StateGraph exceeded maxIterations limit (${maxIterations}).`);
    }

    return state;
  }

  async *stream(input: T, options?: { maxIterations?: number }): AsyncIterable<[string, T]> {
    const state: T = { ...input };
    let currentNode: string = this.entryPoint;
    const maxIterations = options?.maxIterations ?? 50;
    let iter = 0;

    while (currentNode !== END && iter < maxIterations) {
      const action = this.nodes.get(currentNode);
      if (!action) {
        throw new Error(`Node '${currentNode}' is not defined in graph.`);
      }

      const update = await action(state);
      if (update && typeof update === "object") {
        Object.assign(state, update);
      }

      yield [currentNode, { ...state }];

      currentNode = this.getNextNode(currentNode, state);
      iter++;
    }
  }

  pipe<NextOutput>(next: any): any {
    return createPipeline([this, next]);
  }
}