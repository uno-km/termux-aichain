/**
 * ==============================================================================
 * @termux-ai/chain Node.js ESM Regression & Performance Benchmark
 * ==============================================================================
 */

import {
  PromptTemplate,
  ChatPromptTemplate,
  JsonOutputParser,
  RecursiveCharacterTextSplitter,
  StateGraph,
  START,
  END,
  ConversationBufferMemory,
  MicroVectorStore,
  Tracer,
  getDefaultDeviceTools
} from "../js/esm/index.js";

async function main() {
  console.log("==============================================================================");
  console.log("⚡ @termux-ai/chain Node.js ESM Full Regression Suite");
  console.log("==============================================================================");

  const tracer = new Tracer("NodeRegressionAudit");

  // 1. Core Chaining & Prompt
  await tracer.trace("CoreChaining", async () => {
    const prompt = PromptTemplate.fromTemplate("Compute {val}");
    const formatted = prompt.format({ val: "100" });
    if (formatted !== "Compute 100") throw new Error("Prompt formatting mismatch");
  });

  // 2. Parser
  await tracer.trace("JsonParser", async () => {
    const parser = new JsonOutputParser();
    const parsed = parser.parse("Output: ```json\n{\"ok\": true}\n```");
    if (!parsed?.ok) throw new Error("Parser extraction failed");
  });

  // 3. StateGraph Cyclic
  await tracer.trace("StateGraphCycle", async () => {
    const g = new StateGraph();
    g.addNode("step_a", async (s) => ({ count: (s.count || 0) + 1 }));
    g.addEdge(START, "step_a");
    g.addConditionalEdges("step_a", async (s) => (s.count < 3 ? "loop" : "done"), {
      loop: "step_a",
      done: END
    });
    const compiled = g.compile();
    const res = await compiled.invoke({ count: 0 });
    if (res.count !== 3) throw new Error("Graph cycle count incorrect");
  });

  // 4. Memory & Vector Store
  await tracer.trace("MemoryVector", async () => {
    const mem = new ConversationBufferMemory({ k: 1 });
    mem.saveContext("Q1", "A1");
    mem.saveContext("Q2", "A2");
    if (mem.loadMemoryVariables().history.length !== 2) throw new Error("Buffer window error");

    const vstore = new MicroVectorStore();
    vstore.addTexts(["Mobile AI", "Cloud Backend"], [[1, 0], [0, 1]]);
    const res = vstore.similaritySearchByVector([0.9, 0.1], 1);
    if (res[0].content !== "Mobile AI") throw new Error("Cosine search error");
  });

  // 5. Device Tools
  await tracer.trace("DeviceTools", async () => {
    const tools = getDefaultDeviceTools();
    if (tools.length !== 3) throw new Error("Device tools mismatch");
    const bat = await tools[0].func();
    if (!bat.includes("percentage")) throw new Error("Battery tool output invalid");
  });

  tracer.finish();
  console.log("\n📊 Node.js Execution Profiler Tree:");
  tracer.printTree();
  console.log("==============================================================================");
  console.log("✅ Node.js ESM Regression Suite 100% PASS!");
}

main().catch(err => {
  console.error("❌ Node.js Regression Failed:", err);
  process.exit(1);
});