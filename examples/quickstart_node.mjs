import {
  PromptTemplate,
  ChatPromptTemplate,
  JsonOutputParser,
  RecursiveCharacterTextSplitter
} from "../js/esm/index.js";

console.log("=== 1. Node.js Prompt Template Test ===");
const prompt = PromptTemplate.fromTemplate("Task: {task} on {device}");
const formatted = prompt.format({ task: "Process STT", device: "Termux ARM64" });
console.log("Formatted:", formatted);

console.log("\n=== 2. Node.js JSON Output Parser Test ===");
const parser = new JsonOutputParser();
const raw = '```json\n{"status": "ready", "memory_usage_mb": 4.2}\n```';
const parsed = parser.parse(raw);
console.log("Parsed JSON:", parsed);

console.log("\n=== 3. Node.js Recursive Text Splitter Test ===");
const splitter = new RecursiveCharacterTextSplitter({ chunkSize: 35, chunkOverlap: 5 });
const chunks = splitter.splitText("Zero dependency AI chaining for mobile & Termux.");
chunks.forEach((c, i) => console.log(`Chunk #${i}: ${c}`));