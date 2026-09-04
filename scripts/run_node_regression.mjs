import {
  PromptTemplate,
  JsonOutputParser,
  StateGraph,
  START,
  END,
  ConversationBufferMemory,
  MicroVectorStore,
  SparseBM25Embeddings,
  getDefaultDeviceTools,
  getEcosystemTools,
  synthesizeSpeech,
  speakText,
  analyzeImageVlm,
  detectFaces,
  detectEdgesCanny,
  Tracer,
  HumanMessage
} from "../js/esm/index.js";

async function main() {
  console.log("==============================================================================");
  console.log("[AUDIT] @termux-ai/chain Node.js ESM Full Regression Suite");
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
    await tracer.trace("MemoryVector", async () => {
      const embedder = new SparseBM25Embeddings(64);
      const vstore = new MicroVectorStore({ embeddings: embedder });
      await vstore.addTexts(["Mobile Edge AI Termux", "Cloud Large Neural Model"]);
      const matches = await vstore.similaritySearch("Termux AI", 1);
      if (!matches[0].content.includes("Termux")) throw new Error("Vector search error");
      const hybridMatches = await vstore.hybridSearch("Edge Mobile", 1);
      if (!hybridMatches[0].content.includes("Mobile")) throw new Error("Hybrid search error");
    });

    // 5. Device Tools
    tracer.trace("DeviceTools", () => {
      const tools = getDefaultDeviceTools();
      if (!tools || tools.length < 4) throw new Error("Device tools mismatch");
    });

    // 6. Ecosystem Tools (STT, Diffusion, Playwright, TTS, Vision)
    await tracer.trace("EcosystemTools", async () => {
      const ecoTools = getEcosystemTools();
      if (!ecoTools || ecoTools.length !== 9) throw new Error(`Ecosystem tools count mismatch: expected 9, got ${ecoTools?.length}`);
      const ttsRes = await synthesizeSpeech.func({ text: "test" });
      if (!ttsRes) throw new Error("TTS synthesize tool call failed");
      const vlmRes = await analyzeImageVlm.func({ image_path: "test.png" });
      if (!vlmRes) throw new Error("VLM analyze tool call failed");
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