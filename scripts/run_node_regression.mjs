import {
  PromptTemplate,
  JsonOutputParser,
  StateGraph,
  START,
  END,
  ConversationBufferMemory,
  MicroVectorStore,
  getDefaultDeviceTools,
  Tracer,
  HumanMessage
} from "../js/esm/index.js";

async function main() {
  console.log("==============================================================================");
  console.log("??@termux-ai/chain Node.js ESM Full Regression Suite");
  console.log("==============================================================================");
  
  const tracer = new Tracer("NodeRegressionAudit");

  try {
    // 1. Core Chaining
    tracer.trace("CoreChaining", () => {
      const prompt = PromptTemplate.fromTemplate("Hello {name} from {device}");
      const res = prompt.format({ name: "EdgeUser", device: "NodeESM" });
      if (!res.includes("EdgeUser")) throw new Error("Prompt format error");
    });

    // 2. JSON Parser
    tracer.trace("JsonParser", () => {
      const parser = new JsonOutputParser();
      const obj = parser.parse("```json\n{\"ok\": true, \"tps\": 50}\n```");
      if (obj.ok !== true) throw new Error("JSON parser error");
    });

    // 3. StateGraph
    await tracer.trace("StateGraphCycle", async () => {
      const workflow = new StateGraph();
      workflow.addNode("step", (s) => ({ count: (s.count || 0) + 1 }));
      workflow.setEntryPoint("step");
      workflow.addConditionalEdges("step", (s) => (s.count >= 3 ? END : "step"));
      const app = workflow.compile();
      const res = await app.invoke({ count: 0 });
      if (res.count !== 3) throw new Error("Graph cycle error");
    });

    // 4. Memory & Vector Store
    tracer.trace("MemoryVector", () => {
      const vstore = new MicroVectorStore();
      vstore.addTexts(["Mobile AI", "Cloud AI"], [[1.0, 0.0], [0.0, 1.0]]);
      const matches = vstore.similaritySearchByVector([0.9, 0.1], 1);
      if (matches[0].content !== "Mobile AI") throw new Error("Vector search error");
    });

    // 5. Device Tools
    tracer.trace("DeviceTools", () => {
      const tools = getDefaultDeviceTools();
      if (!tools || tools.length < 4) throw new Error("Device tools mismatch");
    });

    tracer.finish();
    console.log("\n?뱤 Node.js Execution Profiler Tree:");
    console.log(tracer.renderTree());
    console.log("==============================================================================");
    console.log("??Node.js ESM Regression Suite 100% PASS!\n");
  } catch (err) {
    console.error("??Node.js Regression Failed:", err);
    process.exit(1);
  }
}

main();