/**
 * ==============================================================================
 * @termux-ai/chain Serve Engine: 1-Line REST & SSE Serving (TypeScript ESM)
 * ==============================================================================
 */
import * as http from "node:http";
export function serve(runnable, options = {}) {
    const host = options.host ?? "0.0.0.0";
    const port = options.port ?? 8080;
    const prefix = (options.endpointPrefix ?? "").replace(/\/+$/, "");
    const server = http.createServer(async (req, res) => {
        // CORS headers
        res.setHeader("Access-Control-Allow-Origin", "*");
        res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
        if (req.method === "OPTIONS") {
            res.writeHead(200);
            res.end();
            return;
        }
        const urlPath = (req.url ?? "/").split("?")[0].replace(/\/+$/, "");
        if (req.method === "GET" && (urlPath === "" || urlPath === "/health")) {
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ status: "ok", engine: "@termux-ai/chain" }));
            return;
        }
        if (req.method === "POST" && (urlPath === `${prefix}/invoke` || urlPath === "/invoke")) {
            let body = "";
            req.on("data", (chunk) => (body += chunk));
            req.on("end", async () => {
                try {
                    const payload = body ? JSON.parse(body) : {};
                    const inputData = payload.input !== undefined ? payload.input : payload;
                    const result = await runnable.invoke(inputData);
                    res.writeHead(200, { "Content-Type": "application/json" });
                    res.end(JSON.stringify({ output: result }));
                }
                catch (err) {
                    res.writeHead(500, { "Content-Type": "application/json" });
                    res.end(JSON.stringify({ error: err.message }));
                }
            });
            return;
        }
        if (req.method === "POST" && (urlPath === `${prefix}/stream` || urlPath === "/stream")) {
            let body = "";
            req.on("data", (chunk) => (body += chunk));
            req.on("end", async () => {
                try {
                    const payload = body ? JSON.parse(body) : {};
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
                    }
                    else {
                        const out = await runnable.invoke(inputData);
                        res.write(`data: ${JSON.stringify(out)}\n\n`);
                    }
                    res.write("data: [DONE]\n\n");
                    res.end();
                }
                catch (err) {
                    res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
                    res.end();
                }
            });
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
