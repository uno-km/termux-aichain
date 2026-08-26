/**
 * ==============================================================================
 * @termux-ai/chain Core Runnable & Pipeline Abstractions
 * ==============================================================================
 */
export class RunnableLambda {
    fn;
    constructor(fn) {
        this.fn = fn;
    }
    async invoke(input, options) {
        return await this.fn(input, options);
    }
    pipe(next) {
        return createPipeline([this, next]);
    }
}
export class RunnableSequence {
    steps;
    constructor(steps) {
        this.steps = steps;
    }
    async invoke(input, options) {
        let current = input;
        for (let i = 0; i < this.steps.length; i++) {
            if (i === 0 && options) {
                current = await this.steps[i].invoke(current, options);
            }
            else {
                current = await this.steps[i].invoke(current);
            }
        }
        return current;
    }
    async *stream(input, options) {
        if (this.steps.length === 0)
            return;
        let current = input;
        for (let i = 0; i < this.steps.length - 1; i++) {
            if (i === 0 && options) {
                current = await this.steps[i].invoke(current, options);
            }
            else {
                current = await this.steps[i].invoke(current);
            }
        }
        const last = this.steps[this.steps.length - 1];
        if (last.stream) {
            for await (const chunk of last.stream(current)) {
                yield chunk;
            }
        }
        else {
            yield await last.invoke(current);
        }
    }
    pipe(next) {
        const nextRunnable = typeof next === "function" ? new RunnableLambda(next) : next;
        if (nextRunnable instanceof RunnableSequence) {
            return new RunnableSequence([...this.steps, ...nextRunnable.steps]);
        }
        return new RunnableSequence([...this.steps, nextRunnable]);
    }
}
export function createPipeline(steps) {
    const normalized = [];
    for (const s of steps) {
        if (typeof s === "function") {
            normalized.push(new RunnableLambda(s));
        }
        else if (s instanceof RunnableSequence) {
            normalized.push(...s.steps);
        }
        else if (typeof s === "object" && s !== null && "invoke" in s) {
            normalized.push(s);
        }
        else {
            throw new TypeError(`Cannot compose non-runnable element: ${typeof s}`);
        }
    }
    return new RunnableSequence(normalized);
}
export class BaseChatModel {
    async invoke(input, options) {
        const res = await this.generate(input, options);
        return res.message;
    }
    pipe(next) {
        return createPipeline([this, next]);
    }
}
