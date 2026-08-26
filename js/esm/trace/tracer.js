/**
 * ==============================================================================
 * @termux-ai/chain Trace Engine: Lightweight CLI Observability (TypeScript ESM)
 * ==============================================================================
 */
export class TraceSpan {
    name;
    startTime;
    endTime;
    inputs;
    outputs;
    tokens = 0;
    metadata;
    children = [];
    error;
    constructor(name, inputs, metadata = {}) {
        this.name = name;
        this.startTime = performance.now();
        this.inputs = inputs;
        this.metadata = metadata;
    }
    get durationMs() {
        const end = this.endTime ?? performance.now();
        return Math.round((end - this.startTime) * 100) / 100;
    }
    get tps() {
        const durSec = this.durationMs / 1000.0;
        if (durSec <= 0 || this.tokens <= 0)
            return 0;
        return Math.round((this.tokens / durSec) * 100) / 100;
    }
    finish(outputs, tokens = 0, error) {
        this.endTime = performance.now();
        this.outputs = outputs;
        if (tokens > 0)
            this.tokens = tokens;
        if (error)
            this.error = error.message;
    }
    toJSON() {
        return {
            name: this.name,
            durationMs: this.durationMs,
            tokens: this.tokens,
            tps: this.tps,
            error: this.error,
            metadata: this.metadata,
            children: this.children.map(c => c.toJSON())
        };
    }
}
export class Tracer {
    rootSpan;
    stack;
    constructor(rootName = "Execution") {
        this.rootSpan = new TraceSpan(rootName);
        this.stack = [this.rootSpan];
    }
    async trace(name, fn, metadata = {}) {
        const span = new TraceSpan(name, undefined, metadata);
        const parent = this.stack[this.stack.length - 1];
        parent.children.push(span);
        this.stack.push(span);
        try {
            const res = await fn(span);
            span.finish(res);
            return res;
        }
        catch (err) {
            span.finish(undefined, 0, err);
            throw err;
        }
        finally {
            if (this.stack[this.stack.length - 1] === span) {
                this.stack.pop();
            }
        }
    }
    finish(outputs) {
        this.rootSpan.finish(outputs);
    }
    renderTree(useColor = true) {
        const lines = [];
        const cCyan = useColor ? "\x1b[36m" : "";
        const cGreen = useColor ? "\x1b[32m" : "";
        const cRed = useColor ? "\x1b[31m" : "";
        const cReset = useColor ? "\x1b[0m" : "";
        const walk = (span, prefix = "", isLast = true, isRoot = false) => {
            const marker = isRoot ? "" : isLast ? "└── " : "├── ";
            const tokInfo = span.tokens > 0 ? `, ${span.tokens} tok (${span.tps} TPS)` : "";
            const errInfo = span.error ? ` ${cRed}[ERROR: ${span.error}]${cReset}` : "";
            lines.push(`${prefix}${marker}${cCyan}${span.name}${cReset} ${cGreen}[${span.durationMs} ms${tokInfo}]${cReset}${errInfo}`);
            const childPrefix = prefix + (!isRoot ? (isLast ? "    " : "│   ") : "");
            span.children.forEach((c, idx) => {
                walk(c, childPrefix, idx === span.children.length - 1, false);
            });
        };
        walk(this.rootSpan, "", true, true);
        return lines.join("\n");
    }
    printTree() {
        console.log(this.renderTree());
    }
}
