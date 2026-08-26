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

test("Node.js: LocalAgent.connect and LocalAgent.local factories with identityVerifier DI", async () => {
  const mockVerifier = async (endpoint, opts) => ({ status: "ok", service: "llama-server", model: { id: opts.expectedModelId || "default" } });
  const agent1 = await LocalAgent.connect("http://127.0.0.1:8080", { identityVerifier: mockVerifier });
  assert(agent1);

  const agent2 = await LocalAgent.local("qwen2.5-1.5b", { identityVerifier: mockVerifier });
  assert(agent2);
});

test("Node.js: verifyServerIdentity contract validation & fail-closed fallback", async () => {
  const http = await import("node:http");
  const { verifyServerIdentity } = await import("../js/esm/core/local_agent.js");

  // Create temporary mock server
  const server = http.createServer((req, res) => {
    if (req.url === "/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({
        status: "ok",
        service: "termux-aichain",
        protocolVersion: "1.0",
        model: { id: "qwen2.5-1.5b" }
      }));
    } else if (req.url === "/v1/models") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({
        data: [{ id: "qwen2.5-1.5b" }, { id: "llama-3.2-3b" }]
      }));
    } else {
      res.writeHead(404);
      res.end();
    }
  });

  await new Promise(r => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;
  const endpoint = `http://127.0.0.1:${port}`;

  try {
    // 1. Valid handshake
    const res = await verifyServerIdentity(endpoint, {
      expectedService: "termux-aichain",
      expectedProtocolVersion: "1.0",
      expectedModelId: "qwen2.5-1.5b"
    });
    assert.strictEqual(res.status, "ok");

    // 2. Model ID mismatch rejected
    await assert.rejects(
      verifyServerIdentity(endpoint, { expectedModelId: "different-model" }),
      /Model ID mismatch/
    );

    // 3. Protocol mismatch rejected
    await assert.rejects(
      verifyServerIdentity(endpoint, { expectedProtocolVersion: "99.0" }),
      /Protocol version mismatch/
    );
  } finally {
    server.close();
  }
});

test("Node.js: verifyServerIdentity fail-closed on missing model ID without fallback", async () => {
  const http = await import("node:http");
  const { verifyServerIdentity } = await import("../js/esm/core/local_agent.js");

  const server = http.createServer((req, res) => {
    if (req.url === "/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", service: "termux-aichain", protocolVersion: "1.0" }));
    } else {
      res.writeHead(404);
      res.end();
    }
  });

  await new Promise(r => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;
  const endpoint = `http://127.0.0.1:${port}`;

  try {
    await assert.rejects(
      verifyServerIdentity(endpoint, { expectedModelId: "qwen2.5-1.5b" }),
      /Expected model ID was configured, but the server did not provide model identity/
    );
  } finally {
    server.close();
  }
});