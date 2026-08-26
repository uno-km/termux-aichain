import test from "node:test";
import assert from "node:assert";
import { Tracer } from "../js/esm/trace/tracer.js";

test("Node.js: Tracer hierarchical tree and metrics", async () => {
  const tracer = new Tracer("NodePipeline");

  await tracer.trace("ParseStep", async (span) => {
    span.finish({ ok: true }, 20);
  });

  tracer.finish();

  assert.strictEqual(tracer.rootSpan.children.length, 1);
  assert.strictEqual(tracer.rootSpan.children[0].name, "ParseStep");
  assert.strictEqual(tracer.rootSpan.children[0].tokens, 20);
  assert.ok(tracer.rootSpan.children[0].tps > 0);

  const tree = tracer.renderTree(false);
  assert.ok(tree.includes("NodePipeline"));
  assert.ok(tree.includes("ParseStep"));
});