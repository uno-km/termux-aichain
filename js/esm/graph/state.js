/**
 * ==============================================================================
 * @termux-ai/chain Graph Engine: StateGraph (TypeScript ESM)
 * ==============================================================================
 */
import { createPipeline } from "../core/base.js";
export const START = "__start__";
export const END = "__end__";
export class StateGraph {
    nodes = new Map();
    edges = new Map();
    conditionalEdges = new Map();
    entryPoint;
    addNode(name, action) {
        if (name === START || name === END) {
            throw new Error(`Cannot use reserved name '${name}' as node.`);
        }
        this.nodes.set(name, action);
        return this;
    }
    addEdge(fromNode, toNode) {
        if (fromNode === START) {
            this.entryPoint = toNode;
        }
        else {
            this.edges.set(fromNode, toNode);
        }
        return this;
    }
    addConditionalEdges(source, router, pathMap) {
        this.conditionalEdges.set(source, { router, pathMap });
        return this;
    }
    setEntryPoint(nodeName) {
        this.entryPoint = nodeName;
        return this;
    }
    setFinishPoint(nodeName) {
        this.edges.set(nodeName, END);
        return this;
    }
    compile() {
        if (!this.entryPoint) {
            throw new Error("StateGraph requires an entry point. Use setEntryPoint() or addEdge(START, ...).");
        }
        return new CompiledGraph(new Map(this.nodes), new Map(this.edges), new Map(this.conditionalEdges), this.entryPoint);
    }
}
export class CompiledGraph {
    nodes;
    edges;
    conditionalEdges;
    entryPoint;
    constructor(nodes, edges, conditionalEdges, entryPoint) {
        this.nodes = nodes;
        this.edges = edges;
        this.conditionalEdges = conditionalEdges;
        this.entryPoint = entryPoint;
    }
    getNextNode(currentNode, state) {
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
    async invoke(input, options) {
        const state = { ...input };
        let currentNode = this.entryPoint;
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
    async *stream(input, options) {
        const state = { ...input };
        let currentNode = this.entryPoint;
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
    pipe(next) {
        return createPipeline([this, next]);
    }
}
