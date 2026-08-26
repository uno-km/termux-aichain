import test from "node:test";
import assert from "node:assert";
import { serve } from "../js/esm/serve/server.js";
import { PromptTemplate } from "../js/esm/core/prompt.js";

test("Node.js: 1-Line serve HTTP invoke", async () => {
  const prompt = PromptTemplate.fromTemplate("Echo: {msg}");
  const server = serve(prompt, { host: "127.0.0.1", port: 0 });

  await new Promise((resolve) => {
    if (server.listening) resolve(true);
    else server.once("listening", () => resolve(true));
  });

  const port = server.address().port;

  try {
    const res = await fetch(`http://127.0.0.1:${port}/invoke`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: { msg: "Node Serve" } })
    });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.output, "Echo: Node Serve");
  } finally {
    server.close();
  }
});