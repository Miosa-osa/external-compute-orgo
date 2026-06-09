// Control primitives as tool/function schemas for YOUR OWN agent (TypeScript).
// Drop TOOL_SCHEMAS into an OpenAI-style tools array; run dispatch() on each call.

import type { ExternalComputer } from "./provider.js";

export const TOOL_SCHEMAS = [
  {
    type: "function",
    function: {
      name: "exec",
      description:
        "Run a shell command on the computer; returns stdout/stderr and exit code.",
      parameters: {
        type: "object",
        properties: { command: { type: "string" } },
        required: ["command"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "screenshot",
      description: "Capture the screen as a base64 PNG.",
      parameters: { type: "object", properties: {} },
    },
  },
  {
    type: "function",
    function: {
      name: "left_click",
      description: "Click at pixel coordinates (top-left origin).",
      parameters: {
        type: "object",
        properties: { x: { type: "integer" }, y: { type: "integer" } },
        required: ["x", "y"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "type",
      description: "Type text at the current focus.",
      parameters: {
        type: "object",
        properties: { text: { type: "string" } },
        required: ["text"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "key",
      description: "Press a key or chord, e.g. 'Enter', 'ctrl+c'.",
      parameters: {
        type: "object",
        properties: { key: { type: "string" } },
        required: ["key"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "write_file",
      description: "Write text to a file path.",
      parameters: {
        type: "object",
        properties: { path: { type: "string" }, content: { type: "string" } },
        required: ["path", "content"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "read_file",
      description: "Read a text file.",
      parameters: {
        type: "object",
        properties: { path: { type: "string" } },
        required: ["path"],
      },
    },
  },
] as const;

const b64 = (u: Uint8Array) => Buffer.from(u).toString("base64");

export async function dispatch(
  c: ExternalComputer,
  name: string,
  args: any,
): Promise<unknown> {
  switch (name) {
    case "exec":
      return c.exec(args.command);
    case "screenshot":
      return { image_base64: b64(await c.screenshot()) };
    case "left_click":
      await c.leftClick(Number(args.x), Number(args.y));
      return { ok: true };
    case "type":
      await c.type(args.text);
      return { ok: true };
    case "key":
      await c.key(args.key);
      return { ok: true };
    case "write_file":
      await c.writeFile(args.path, args.content);
      return { ok: true };
    case "read_file":
      return { content: await c.readFile(args.path) };
    default:
      throw new Error(`unknown tool: ${name}`);
  }
}

/** Anthropic-format (input_schema instead of parameters). */
export const anthropicTools = () =>
  TOOL_SCHEMAS.map((t) => ({
    name: t.function.name,
    description: t.function.description,
    input_schema: t.function.parameters,
  }));
