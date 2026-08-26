import test from "node:test";
import assert from "node:assert";
import { StateGraph, START, END } from "../js/esm/graph/state.js";

test("Node.js: StateGraph linear execution", async () => {
  const workflow = new StateGraph();
  workflow.addNode("step1", (s) => ({ count: (s.count || 0) + 5 }));
  workflow.addNode("step2", (s) => ({ count: s.count * 2 }));
  
  workflow.setEntryPoint("step1");
  workflow.addEdge("step1", "step2");
  workflow.setFinishPoint("step2");
  
  const app = workflow.compile();
  const res = await app.invoke({ count: 10 });
  assert.strictEqual(res.count, 30);
});

test("Node.js: StateGraph cyclic loop", async () => {
  const workflow = new StateGraph();
  workflow.addNode("inc", (s) => ({ n: (s.n || 0) + 1 }));
  
  workflow.setEntryPoint("inc");
  workflow.addConditionalEdges("inc", (s) => (s.n >= 3 ? END : "inc"));
  
  const app = workflow.compile();
  const res = await app.invoke({ n: 0 });
  assert.strictEqual(res.n, 3);
});