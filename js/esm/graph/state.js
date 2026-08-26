/**
 * ==============================================================================
 * @termux-ai/chain Graph Engine: StateGraph & Cyclic State Machine (TypeScript ESM)
 * ==============================================================================
 */
export const START = "__start__";
export const END = "__end__";
export class StateGraph {
    nodes = new Map();
    edges = new Map();
    conditionalEdges = new Map();
    entryPoint;
    constructor(stateSchema) { }
    addNode(name, fn) {
        this.nodes.set(name, fn);
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
    setEntryPoint(nodeName) {
        this.entryPoint = nodeName;
        return this;
    }
    addConditionalEdges(fromNode, condition, pathMap) {
        this.conditionalEdges.set(fromNode, { condition, pathMap });
        return this;
    }
    compile() {
        if (!this.entryPoint) {
            throw new Error("No entry point defined. Call setEntryPoint or addEdge(START, ...).");
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
    async invoke(initialState, maxIterations = 25) {
        let currentState = { ...initialState };
        let currentNode = this.entryPoint;
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
            const condEdge = this.conditionalEdges.get(currentNode);
            if (condEdge) {
                const targetKey = await Promise.resolve(condEdge.condition(currentState));
                currentNode = condEdge.pathMap[targetKey];
            }
            else if (this.edges.has(currentNode)) {
                currentNode = this.edges.get(currentNode);
            }
            else {
                currentNode = END;
            }
        }
        return currentState;
    }
    async *stream(initialState, maxIterations = 25) {
        let currentState = { ...initialState };
        let currentNode = this.entryPoint;
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
            const condEdge = this.conditionalEdges.get(currentNode);
            if (condEdge) {
                const targetKey = await Promise.resolve(condEdge.condition(currentState));
                currentNode = condEdge.pathMap[targetKey];
            }
            else if (this.edges.has(currentNode)) {
                currentNode = this.edges.get(currentNode);
            }
            else {
                currentNode = END;
            }
        }
    }
}
