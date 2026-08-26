/**
 * ==============================================================================
 * @termux-ai/chain Trace Engine: Lightweight CLI Observability (TypeScript ESM)
 * ==============================================================================
 */

export interface TraceSpanData {
  name: string;
  durationMs: number;
  tokens: number;
  tps: number;
  error?: string;
  metadata: Record<string, any>;
  children: TraceSpanData[];
}

export class TraceSpan {
  name: string;
  startTime: number;
  endTime?: number;
  inputs?: any;
  outputs?: any;
  tokens: number = 0;
  metadata: Record<string, any>;
  children: TraceSpan[] = [];
  error?: string;

  constructor(name: string, inputs?: any, metadata: Record<string, any> = {}) {
    this.name = name;
    this.startTime = performance.now();
    this.inputs = inputs;
    this.metadata = metadata;
  }

  get durationMs(): number {
    const end = this.endTime ?? performance.now();
    return Math.round((end - this.startTime) * 100) / 100;
  }

  get tps(): number {
    const durSec = this.durationMs / 1000.0;
    if (durSec <= 0 || this.tokens <= 0) return 0;
    return Math.round((this.tokens / durSec) * 100) / 100;
  }

  finish(outputs?: any, tokens: number = 0, error?: Error): void {
    this.endTime = performance.now();
    this.outputs = outputs;
    if (tokens > 0) this.tokens = tokens;
    if (error) this.error = error.message;
  }

  toJSON(): TraceSpanData {
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
  rootSpan: TraceSpan;
  private stack: TraceSpan[];

  constructor(rootName: string = "Execution") {
    this.rootSpan = new TraceSpan(rootName);
    this.stack = [this.rootSpan];
  }

  async trace<T>(name: string, fn: (span: TraceSpan) => Promise<T> | T, metadata: Record<string, any> = {}): Promise<T> {
    const span = new TraceSpan(name, undefined, metadata);
    const parent = this.stack[this.stack.length - 1];
    parent.children.push(span);
    this.stack.push(span);

    try {
      const res = await fn(span);
      span.finish(res);
      return res;
    } catch (err: any) {
      span.finish(undefined, 0, err);
      throw err;
    } finally {
      if (this.stack[this.stack.length - 1] === span) {
        this.stack.pop();
      }
    }
  }

  finish(outputs?: any): void {
    this.rootSpan.finish(outputs);
  }

  renderTree(useColor: boolean = true): string {
    const lines: string[] = [];
    const cCyan = useColor ? "\x1b[36m" : "";
    const cGreen = useColor ? "\x1b[32m" : "";
    const cRed = useColor ? "\x1b[31m" : "";
    const cReset = useColor ? "\x1b[0m" : "";

    const walk = (span: TraceSpan, prefix: string = "", isLast: boolean = true, isRoot: boolean = false) => {
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

  printTree(): void {
    console.log(this.renderTree());
  }
}