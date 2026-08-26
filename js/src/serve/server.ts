/**
 * ==============================================================================
 * @termux-ai/chain Serve Engine: 1-Line REST & SSE Serving (TypeScript ESM)
 * ==============================================================================
 */
import * as http from "node:http";
import * as crypto from "node:crypto";
import { URL } from "node:url";

export interface ServeOptions {
  host?: string;
  port?: number;
  endpointPrefix?: string;
  apiKey?: string;
  maxBodyBytes?: number;
  corsOrigins?: string[];
}

export async function readJsonBody(req: http.IncomingMessage, maxBodyBytes: number): Promise<Record<string, any>> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let size = 0;
    let rejected = false;

    req.on("data", (chunk: Buffer) => {
      if (rejected) return;
      size += chunk.length;
      if (size > maxBodyBytes) {
        rejected = true;
        const err: any = new Error(`Payload too large (limit ${maxBodyBytes} bytes).`);
        err.statusCode = 413;
        req.pause();
        reject(err);
        return;
      }
      chunks.push(chunk);
    });

    req.on("end", () => {
      if (rejected) return;
      try {
        const raw = Buffer.concat(chunks).toString("utf8");
        resolve(raw ? JSON.parse(raw) : {});
      } catch {
        const err: any = new Error("INVALID_JSON: Body is not valid JSON.");
        err.statusCode = 400;
        reject(err);
      }
    });

    req.on("error", (err: Error) => {
      if (!rejected) reject(err);
    });
  });
}

function safeCompare(a: string, b: string): boolean {
  if (typeof a !== "string" || typeof b !== "string") return false;
  const bufA = Buffer.from(a);
  const bufB = Buffer.from(b);
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

export function serve(runnable: any, options: ServeOptions = {}): http.Server {
  const host = options.host ?? "127.0.0.1";
  const port = options.port ?? 8080;
  const prefix = (options.endpointPrefix ?? "").replace(/\/+$/, "");
  const apiKey = options.apiKey;
  const maxBodyBytes = options.maxBodyBytes ?? 2 * 1024 * 1024;
  const allowedOrigins = options.corsOrigins;

  const server = http.createServer(async (req: http.IncomingMessage, res: http.ServerResponse) => {
    const origin = (req.headers["origin"] as string) || "";

    // Strict structural loopback CORS
    if (allowedOrigins) {
      if (allowedOrigins.includes("*")) {
        res.setHeader("Access-Control-Allow-Origin", "*");
      } else if (origin && allowedOrigins.includes(origin)) {
        res.setHeader("Access-Control-Allow-Origin", origin);
        res.setHeader("Vary", "Origin");
      }
    } else {
      if (origin) {
        try {
          const parsedUrl = new URL(origin);
          if (
            (parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:") &&
            !parsedUrl.username && !parsedUrl.password &&
            (parsedUrl.pathname === "" || parsedUrl.pathname === "/") &&
            !parsedUrl.search && !parsedUrl.hash &&
            ["localhost", "127.0.0.1", "::1"].includes(parsedUrl.hostname)
          ) {
            res.setHeader("Access-Control-Allow-Origin", origin);
            res.setHeader("Vary", "Origin");
          }
        } catch {
          // Invalid URL rejected
        }
      }
    }
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

    if (req.method === "OPTIONS") {
      res.writeHead(200);
      res.end();
      return;
    }

    // Healthcheck endpoint
    const parsedPath = req.url ? new URL(req.url, `http://${req.headers.host || "127.0.0.1"}`).pathname : "/";
    if (parsedPath === `${prefix}/health` && req.method === "GET") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({
        status: "ok",
        service: "termux-aichain",
        protocolVersion: "1.0",
        model: { id: "default" }
      }));
      return;
    }

    // Models endpoint
    if (parsedPath === `${prefix}/v1/models` && req.method === "GET") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({
        object: "list",
        data: [{ id: "default", object: "model", owned_by: "termux-aichain" }]
      }));
      return;
    }

    // Authentication Guard
    if (apiKey) {
      const authHeader = req.headers["authorization"] || "";
      const expectedBearer = `Bearer ${apiKey}`;
      if (!safeCompare(authHeader, expectedBearer)) {
        res.writeHead(401, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "UNAUTHORIZED", message: "Missing or invalid Authorization header." }));
        return;
      }
    }

    // Inference invocation endpoint
    if (parsedPath === `${prefix}/invoke` && req.method === "POST") {
      try {
        const body = await readJsonBody(req, maxBodyBytes);
        const input = body.input !== undefined ? body.input : body;
        const result = typeof runnable.invoke === "function" ? await runnable.invoke(input) : await runnable(input);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ output: result }));
      } catch (err: any) {
        const status = err.statusCode || 500;
        res.writeHead(status, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "INVOCATION_ERROR", message: err.message }));
      }
      return;
    }

    // Streaming SSE endpoint
    if (parsedPath === `${prefix}/stream` && req.method === "POST") {
      try {
        const body = await readJsonBody(req, maxBodyBytes);
        const input = body.input !== undefined ? body.input : body;
        res.writeHead(200, {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          "Connection": "keep-alive"
        });
        if (typeof runnable.stream === "function") {
          for await (const chunk of runnable.stream(input)) {
            res.write(`data: ${JSON.stringify(chunk)}\n\n`);
          }
        } else {
          const result = typeof runnable.invoke === "function" ? await runnable.invoke(input) : await runnable(input);
          res.write(`data: ${JSON.stringify({ content: result })}\n\n`);
        }
        res.write("data: [DONE]\n\n");
        res.end();
      } catch (err: any) {
        const status = err.statusCode || 500;
        res.writeHead(status, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "STREAM_ERROR", message: err.message }));
      }
      return;
    }

    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "NOT_FOUND", message: `Endpoint ${req.url} not found.` }));
  });

  server.listen(port, host, () => {
    console.log(`[*] @termux-ai/chain serving agent on http://${host}:${port}${prefix}`);
  });

  return server;
}