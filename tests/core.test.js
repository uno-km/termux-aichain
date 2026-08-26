import test from "node:test";
import assert from "node:assert";
import { PromptTemplate, ChatPromptTemplate } from "../dist/core/prompt.js";
import { StringOutputParser, JsonOutputParser } from "../dist/core/parsers.js";
import { CharacterTextSplitter, RecursiveCharacterTextSplitter } from "../dist/core/splitters.js";

test("Node.js: PromptTemplate basic substitution", () => {
  const prompt = PromptTemplate.fromTemplate("Hello {name}, target is {target}.");
  assert.deepStrictEqual(prompt.inputVariables, ["name", "target"]);
  const formatted = prompt.format({ name: "Termux", target: "Edge" });
  assert.strictEqual(formatted, "Hello Termux, target is Edge.");
});

test("Node.js: ChatPromptTemplate formatting", () => {
  const chatPrompt = ChatPromptTemplate.fromMessages([
    ["system", "You are an assistant on {device}"],
    ["user", "Query: {query}"]
  ]);
  assert.deepStrictEqual(chatPrompt.inputVariables, ["device", "query"]);
  const msgs = chatPrompt.formatMessages({ device: "Galaxy S20", query: "Status" });
  assert.strictEqual(msgs.length, 2);
  assert.strictEqual(msgs[0].role, "system");
  assert.strictEqual(msgs[0].content, "You are an assistant on Galaxy S20");
});

test("Node.js: JsonOutputParser markdown extraction", () => {
  const parser = new JsonOutputParser();
  const text = '```json\n{"status": "ok", "code": 200}\n```';
  const data = parser.parse(text);
  assert.strictEqual(data.status, "ok");
  assert.strictEqual(data.code, 200);
});

test("Node.js: RecursiveCharacterTextSplitter", () => {
  const splitter = new RecursiveCharacterTextSplitter({ chunkSize: 50, chunkOverlap: 10 });
  const text = "Termux AI Chain Node version.\n\nUltra lightweight.\n\nPure ESM zero dependencies.";
  const chunks = splitter.splitText(text);
  assert.ok(chunks.length >= 2);
});