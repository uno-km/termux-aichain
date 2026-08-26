import test from "node:test";
import assert from "node:assert";
import { LocalAgent } from "../js/esm/core/local_agent.js";
import { AIMessage } from "../js/esm/core/schema.js";

test("Node.js: LocalAgent default constructor & run facade", async () => {
  const agent = new LocalAgent();
  assert(agent.model);
  assert(agent.graph);

  // Mock model generate
  agent.model.generate = async () => ({
    message: new AIMessage("Node Sovereign Edge operational.")
  });

  const reply = await agent.run("Status query");
  assert.strictEqual(reply, "Node Sovereign Edge operational.");
});

test("Node.js: LocalAgent.connect and LocalAgent.local factories", async () => {
  const agent1 = LocalAgent.connect("http://127.0.0.1:8080");
  assert(agent1);

  const agent2 = LocalAgent.local("qwen2.5-1.5b");
  assert(agent2);
});