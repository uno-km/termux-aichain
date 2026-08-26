declare global {
  interface Buffer {
    length: number;
    toString(encoding?: string): string;
    [key: string]: any;
  }
  var Buffer: {
    from(data: any, encoding?: string): any;
    concat(list: any[], totalLength?: number): any;
  };
}

declare module "node:http" {
  export interface IncomingMessage {
    method?: string;
    url?: string;
    headers: Record<string, string | string[] | undefined>;
    on(event: string, listener: (...args: any[]) => void): this;
    pause(): this;
    destroy(error?: Error): this;
    [key: string]: any;
  }
  export interface ServerResponse {
    statusCode: number;
    writeHead(statusCode: number, headers?: Record<string, any>): this;
    setHeader(name: string, value: any): this;
    end(data?: any): this;
    [key: string]: any;
  }
  export interface Server {
    listen(port: number, host?: string, callback?: () => void): this;
    close(callback?: (err?: Error) => void): this;
    address(): any;
    [key: string]: any;
  }
  export function createServer(requestListener?: (req: any, res: any) => void): Server;
  export function get(url: any, options: any, callback?: (res: any) => void): any;
}

declare module "node:https" {
  export function get(url: any, options: any, callback?: (res: any) => void): any;
}

declare module "node:url" {
  export class URL {
    constructor(url: string, base?: string | URL);
    protocol: string;
    hostname: string;
    pathname: string;
    search: string;
    hash: string;
    username?: string;
    password?: string;
  }
}

declare module "node:crypto" {
  export function timingSafeEqual(a: any, b: any): boolean;
}

declare module "node:child_process" {
  export function execFile(file: string, args: string[], options: any, callback?: (error: any, stdout: string, stderr: string) => void): any;
  export function execFile(file: string, callback?: (error: any, stdout: string, stderr: string) => void): any;
}

declare module "node:util" {
  export function promisify<T = any>(fn: any): (...args: any[]) => Promise<T>;
}

declare module "node:fs" {
  export function existsSync(path: string): boolean;
  export function readFileSync(path: string, encoding: string): string;
}

declare module "node:fs/promises" {
  export function readFile(path: string, encoding: string): Promise<string>;
}

declare module "node:path" {
  export function basename(path: string): string;
}

export {};