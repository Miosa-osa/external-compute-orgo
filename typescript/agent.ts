// Model-agnostic agent loop over an Orgo computer (TypeScript).
// Mirrors agent_loop.py: plug in any OpenAI-style chat model; the loop runs the
// tools it calls on the box until it stops.
//
//   ORGO_API_KEY=sk_live_... OPENAI_API_KEY=sk-... npx tsx agent.ts "print the kernel version"
import OpenAI from "openai";
import { OrgoProvider } from "./src/orgo.js";
import type { ExternalComputer } from "./src/provider.js";
import { TOOL_SCHEMAS, dispatch } from "./src/tools.js";

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}
interface ChatModel {
  chat(
    messages: any[],
    tools: any,
  ): Promise<{ text: string; calls: ToolCall[] }>;
}

class OpenAIModel implements ChatModel {
  private c = new OpenAI();
  constructor(private model = "gpt-4.1-mini") {}
  async chat(messages: any[], tools: any) {
    const r = await this.c.chat.completions.create({
      model: this.model,
      messages,
      tools,
    });
    const m = r.choices[0].message;
    const calls = (m.tool_calls ?? []).map((tc: any) => ({
      id: tc.id,
      name: tc.function.name,
      arguments: JSON.parse(tc.function.arguments || "{}"),
    }));
    return { text: m.content ?? "", calls };
  }
}

export async function runAgent(
  computer: ExternalComputer,
  goal: string,
  model: ChatModel,
  maxSteps = 12,
): Promise<string> {
  const messages: any[] = [
    {
      role: "system",
      content:
        "You control a Linux computer via tools. Work step by step; stop when the goal is met.",
    },
    { role: "user", content: goal },
  ];
  let final = "";
  for (let i = 0; i < maxSteps; i++) {
    const { text, calls } = await model.chat(messages, TOOL_SCHEMAS);
    if (text) final = text;
    if (!calls.length) break;
    messages.push({
      role: "assistant",
      content: text || null,
      tool_calls: calls.map((c) => ({
        id: c.id,
        type: "function",
        function: { name: c.name, arguments: JSON.stringify(c.arguments) },
      })),
    });
    for (const call of calls) {
      const result = await dispatch(computer, call.name, call.arguments);
      messages.push({
        role: "tool",
        tool_call_id: call.id,
        content: JSON.stringify(result).slice(0, 4000),
      });
    }
  }
  return final;
}

async function main() {
  const goal = process.argv[2];
  if (!goal) {
    console.log('usage: npx tsx agent.ts "<goal>"');
    process.exit(2);
  }
  const computer = await new OrgoProvider().create({ name: "agent-loop-ts" });
  try {
    console.log(await runAgent(computer, goal, new OpenAIModel()));
  } finally {
    await computer.destroy();
  }
}

if (import.meta.url === `file://${process.argv[1]}`) main();
