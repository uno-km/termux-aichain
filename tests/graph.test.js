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

test("Node.js: createReactAgent tool schema validation & default deny", async () => {
  const { createReactAgent, tool } = await import("../js/esm/graph/agent.js");
  const { AIMessage } = await import("../js/esm/core/schema.js");

  const mockTool = tool(
    {
      name: "secure_action",
      description: "Secure action with integer bounds",
      parameters: {
        type: "object",
        properties: { count: { type: "integer", minimum: 1, maximum: 10 } },
        required: ["count"]
      }
    },
    async (args) => `Executed ${args.count}`
  );

  let step = 0;
  const mockModel = {
    async generate() {
      step++;
      if (step === 1) {
        return {
          message: new AIMessage("Calling tool", {
            tool_calls: [{
              id: "call_1",
              function: { name: "secure_action", arguments: JSON.stringify({ count: 50 }) } // Violates max 10
            }]
          })
        };
      }
      return {
        message: new AIMessage("Final answer after tool error", {
          tool_calls: []
        })
      };
    }
  };

  const agent = createReactAgent(mockModel, [mockTool], {
    toolPolicy: { default: "deny", allowedTools: ["secure_action"] }
  });

  const res = await agent.invoke({ messages: [] });
  const toolMsg = res.messages.find((m) => m.role === "tool");
  assert(toolMsg && (toolMsg.content.includes("ToolArgumentValidationError") || toolMsg.content.includes("must be <= 10")));
});

test("Node.js: createReactAgent unconfigured policy strictly denies all tools (Default Deny)", async () => {
  const { createReactAgent, tool } = await import("../js/esm/graph/agent.js");
  const { AIMessage } = await import("../js/esm/core/schema.js");

  const mockTool = tool({ name: "device_vibrate", description: "Vibrate" }, async () => "vibrated");
  let step = 0;
  const mockModel = {
    async generate() {
      step++;
      if (step === 1) {
        return {
          message: new AIMessage("Calling tool", {
            tool_calls: [{ id: "call_1", function: { name: "device_vibrate", arguments: "{}" } }]
          })
        };
      }
      return { message: new AIMessage("Done", { tool_calls: [] }) };
    }
  };

  // No toolPolicy passed -> Must default to deny with empty allowedTools
  const agent = createReactAgent(mockModel, [mockTool]);
  const res = await agent.invoke({ messages: [] });
  const toolMsg = res.messages.find((m) => m.role === "tool");
  assert(toolMsg && toolMsg.content.includes("ToolPolicyDeniedError"));
});