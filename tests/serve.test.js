import test from "node:test";
import assert from "node:assert";
import { serve } from "../js/esm/serve/server.js";
import { PromptTemplate } from "../js/esm/core/prompt.js";

test("Node.js: 1-Line serve HTTP invoke & security", async () => {
  const prompt = PromptTemplate.fromTemplate("Echo: {msg}");
  const server = serve(prompt, { host: "127.0.0.1", port: 0, apiKey: "secret_node_key", maxBodyBytes: 100 });

  await new Promise((resolve) => {
    if (server.listening) resolve(true);
    else server.once("listening", () => resolve(true));
  });

  const port = server.address().port;

  try {
    // 1. Health check
    const resHealth = await fetch(`http://127.0.0.1:${port}/health`);
    assert.strictEqual(resHealth.status, 200);
    const healthData = await resHealth.json();
    assert.strictEqual(healthData.service, "termux-aichain");

    // 2. Unauthorized request
    const resUnauth = await fetch(`http://127.0.0.1:${port}/invoke`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: { msg: "Node" } })
    });
    assert.strictEqual(resUnauth.status, 401);

    // 3. Authorized request
    const resAuth = await fetch(`http://127.0.0.1:${port}/invoke`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer secret_node_key"
      },
      body: JSON.stringify({ input: { msg: "Node Serve" } })
    });
    // 4. Stream payload limit rejection (413)
    const largePayload = JSON.stringify({ input: { msg: "A".repeat(500) } });
    const resStream413 = await fetch(`http://127.0.0.1:${port}/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer secret_node_key"
      },
      body: largePayload
    });
    assert.strictEqual(resStream413.status, 413);
  } finally {
    server.close();
  }
});