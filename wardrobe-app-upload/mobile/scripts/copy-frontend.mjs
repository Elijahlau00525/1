import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(process.cwd(), "..");
const src = resolve(root, "frontend");
const dest = resolve(process.cwd(), "www");

if (!existsSync(src)) {
  throw new Error(`Frontend directory not found: ${src}`);
}

if (existsSync(dest)) {
  rmSync(dest, { recursive: true, force: true });
}

mkdirSync(dest, { recursive: true });
cpSync(src, dest, { recursive: true });

console.log(`Copied frontend -> ${dest}`);
