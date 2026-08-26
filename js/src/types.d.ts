declare module "node:http" {
  export function createServer(requestListener?: (req: any, res: any) => void): any;
}
declare module "node:fs/promises" {
  export function readFile(path: string, encoding: string): Promise<string>;
}
declare module "node:path" {
  export function basename(path: string): string;
}