import test from "node:test";
import assert from "node:assert";
import { ConversationBufferMemory } from "../js/esm/memory/buffer.js";
import { MicroVectorStore } from "../js/esm/memory/sqlite.js";

test("Node.js: ConversationBufferMemory window", () => {
  const mem = new ConversationBufferMemory({ k: 1 });
  mem.saveContext("Turn 1 question", "Turn 1 answer");
  mem.saveContext("Turn 2 question", "Turn 2 answer");

  const history = mem.loadMemoryVariables().history;
  assert.strictEqual(history.length, 2);
  assert.strictEqual(history[0].content, "Turn 2 question");
  assert.strictEqual(history[1].content, "Turn 2 answer");
});

test("Node.js: MicroVectorStore cosine search", () => {
  const store = new MicroVectorStore();
  store.addTexts(
    ["Fast Edge AI", "STT Audio", "WebGPU Diffusion"],
    [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
  );

  const results = store.similaritySearchByVector([0.9, 0.1, 0], 1);
  assert.strictEqual(results.length, 1);
  assert.strictEqual(results[0].content, "Fast Edge AI");
  assert.ok(results[0].score > 0.9);
});