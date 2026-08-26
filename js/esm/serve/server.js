/**
 * ==============================================================================
 * @termux-ai/chain Serve Engine: 1-Line REST & SSE Serving (TypeScript ESM)
 * ==============================================================================
 */
import * as http from "node:http";
import * as crypto from "node:crypto";

export async function readJsonBody(req, maxBodyBytes) {
    return new Promise((resolve, reject) => {
        const chunks = [];
        let size = 0;
        let rejected = false;

        req.on("data", (chunk) => {
            if (rejected) return;
            size += chunk.length;
            if (size > maxBodyBytes) {
                rejected = true;
                const err = new Error(`Payload too large (limit ${maxBodyBytes} bytes).`);
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
                const err = new Error("INVALID_JSON: Body is not valid JSON.");
                err.statusCode = 400;
                reject(err);
            }
        });

        req.on("error", (err) => {
            if (!rejected) reject(err);
        });
    });
}

function safeCompare(a, b) {
    if (typeof a !== "string" || typeof b !== "string") return false;
    const bufA = Buffer.from(a);
    const bufB = Buffer.from(b);
    if (bufA.length !== bufB.length) return false;
    return crypto.timingSafeEqual(bufA, bufB);
}

export function serve(runnable, options = {}) {
    const host = options.host ?? "127.0.0.1";
    const port = options.port ?? 8080;
    const prefix = (options.endpointPrefix ?? "").replace(/\/+$/, "");
    const apiKey = options.apiKey;
    const maxBodyBytes = options.maxBodyBytes ?? 2 * 1024 * 1024;
    const allowedOrigins = options.corsOrigins;

    const server = http.createServer(async (req, res) => {
        const origin = req.headers["origin"] || "";

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

        const urlPath = (req.url ?? "/").split("?")[0].replace(/\/+$/, "");

        // P0-1 Standardized Health Handshake Contract
        if (req.method === "GET" && (urlPath === "" || urlPath === "/health" || urlPath === "/api/health")) {
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify({
                status: "ok",
                service: "termux-aichain",
                version: "1.0.12-rc.1",
                protocolVersion: "1.0",
                model: {
                    id: "termux-aichain-agent",
                    provider: "termux-aichain"
                }
            }));
            return;
        }

        // Bearer Token Auth Check (Constant-time comparison)
        if (apiKey) {
            const authHeader = req.headers["authorization"] || "";
            const expected = `Bearer ${apiKey}`;
            if (!safeCompare(authHeader, expected)) {
                res.writeHead(401, { "Content-Type": "application/json" });
                res.end(JSON.stringify({ error: "Unauthorized: Invalid or missing Bearer token." }));
                return;
            }
        }

        if (req.method === "POST" && (urlPath === `${prefix}/invoke` || urlPath === "/invoke" || urlPath === "/api/invoke")) {
            try {
                const payload = await readJsonBody(req, maxBodyBytes);
                const inputData = payload.input !== undefined ? payload.input : payload;
                const result = await runnable.invoke(inputData);
                res.writeHead(200, { "Content-Type": "application/json" });
                res.end(JSON.stringify({ output: result }));
            } catch (err) {
                const status = err.statusCode || 500;
                res.writeHead(status, { "Content-Type": "application/json" });
                res.end(JSON.stringify({ error: err.message }));
            }
            return;
        }

        if (req.method === "POST" && (urlPath === `${prefix}/stream` || urlPath === "/stream" || urlPath === "/api/stream")) {
            try {
                const payload = await readJsonBody(req, maxBodyBytes);
                const inputData = payload.input !== undefined ? payload.input : payload;
                res.writeHead(200, {
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                });
                if (runnable.stream) {
                    for await (const chunk of runnable.stream(inputData)) {
                        res.write(`data: ${JSON.stringify(chunk)}\n\n`);
                    }
                } else {
                    const out = await runnable.invoke(inputData);
                    res.write(`data: ${JSON.stringify(out)}\n\n`);
                }
                res.write("data: [DONE]\n\n");
                res.end();
            } catch (err) {
                const status = err.statusCode || 500;
                if (!res.headersSent) {
                    res.writeHead(status, { "Content-Type": "application/json" });
                    res.end(JSON.stringify({ error: err.message }));
                } else {
                    res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
                    res.end();
                }
            }
            return;
        }

        res.writeHead(404, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: `Route ${urlPath} not found.` }));
    });

    server.listen(port, host, () => {
        console.log(`[*] @termux-ai/chain serving agent on http://${host}:${port}${prefix}`);
    });
    return server;
}
