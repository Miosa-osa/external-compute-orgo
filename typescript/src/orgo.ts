// Orgo implementation of the normalized interface (TypeScript).
// Verified against the live Orgo API (base https://www.orgo.ai/api, Bearer auth).
// Uses global fetch (Node 18+ / browsers — keep keys server-side).

import type {
  ComputeProvider,
  ComputerInfo,
  ExecResult,
  ExternalComputer,
  ShellEndpoint,
} from "./provider.js";

const BASE = process.env.ORGO_API_BASE ?? "https://www.orgo.ai/api";

export class OrgoComputer implements ExternalComputer {
  constructor(
    private headers: Record<string, string>,
    private base: string,
    private data: Record<string, any>,
  ) {}

  get info(): ComputerInfo {
    return {
      id: this.data.id,
      name: this.data.name ?? "",
      provider: "orgo",
      status: this.data.status ?? "unknown",
      publicUrl: this.data.url ?? this.data.connection_url ?? null,
      raw: this.data,
    };
  }

  private async post(path: string, body: unknown): Promise<any> {
    const r = await fetch(`${this.base}/computers/${this.data.id}${path}`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`Orgo ${path} -> ${r.status}`);
    return r.json();
  }

  async exec(command: string): Promise<ExecResult> {
    const b = await this.post("/bash", { command });
    return {
      output: b.output ?? "",
      exitCode: b.success ? (b.exit_code ?? 0) : (b.exit_code ?? 1),
      error: b.error ?? null,
    };
  }

  shellEndpoint(): ShellEndpoint {
    const instance = this.data.instance_id ?? this.data.fly_instance_id ?? "";
    const token = this.data.vnc_password ?? "";
    return {
      kind: "websocket",
      uri: `wss://www.orgo.ai/desktops/${instance}/ws/terminal?token=${token}&cols=120&rows=32`,
      token,
      meta: { instanceId: instance },
    };
  }

  async screenshot(): Promise<Uint8Array> {
    const r = await fetch(`${this.base}/computers/${this.data.id}/screenshot`, {
      headers: this.headers,
    });
    if (!r.ok) throw new Error(`Orgo screenshot -> ${r.status}`);
    const body = await r.json();
    const imgPath: string = body.image ?? "";
    if (imgPath.startsWith("/")) {
      const img = await fetch(`https://www.orgo.ai${imgPath}`, {
        headers: this.headers,
      });
      return new Uint8Array(await img.arrayBuffer());
    }
    return new TextEncoder().encode(imgPath);
  }

  async leftClick(x: number, y: number): Promise<void> {
    await this.post("/click", { x, y });
  }
  async type(text: string): Promise<void> {
    await this.post("/type", { text });
  }
  async key(key: string): Promise<void> {
    await this.post("/key", { key });
  }

  async writeFile(path: string, content: string): Promise<void> {
    // heredoc keeps it provider-agnostic; quote the path
    const q = `'${path.replace(/'/g, "'\\''")}'`;
    await this.exec(`cat > ${q} <<'__MIOSA_EOF__'\n${content}\n__MIOSA_EOF__`);
  }
  async readFile(path: string): Promise<string> {
    const q = `'${path.replace(/'/g, "'\\''")}'`;
    return (await this.exec(`cat ${q}`)).output;
  }

  // previewUrl intentionally omitted: Orgo has no general port ingress.
  // Route the port through a MIOSA edge tunnel instead.

  /** Orgo's own OpenAI-compatible agent loop (the model drives the box). */
  async prompt(
    instruction: string,
    model = "claude-sonnet-4-6",
  ): Promise<string> {
    const r = await fetch("https://www.orgo.ai/api/v1/chat/completions", {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({
        model,
        computer_id: this.data.id,
        messages: [{ role: "user", content: instruction }],
      }),
    });
    if (!r.ok) throw new Error(`Orgo prompt -> ${r.status}`);
    const data = await r.json();
    return data?.choices?.[0]?.message?.content ?? JSON.stringify(data);
  }

  async stop(): Promise<void> {
    await this.post("/stop", {});
  }
  async destroy(): Promise<void> {
    const r = await fetch(`${this.base}/computers/${this.data.id}`, {
      method: "DELETE",
      headers: this.headers,
    });
    if (!r.ok && r.status !== 404)
      throw new Error(`Orgo destroy -> ${r.status}`);
  }
}

export class OrgoProvider implements ComputeProvider {
  readonly name = "orgo";
  private headers: Record<string, string>;
  private base: string;
  private workspaceId?: string;

  constructor(
    opts: { apiKey?: string; workspaceId?: string; base?: string } = {},
  ) {
    const key = opts.apiKey ?? process.env.ORGO_API_KEY;
    if (!key) throw new Error("Set ORGO_API_KEY or pass apiKey");
    this.base = opts.base ?? BASE;
    this.workspaceId = opts.workspaceId ?? process.env.ORGO_WORKSPACE_ID;
    this.headers = {
      Authorization: `Bearer ${key}`,
      "content-type": "application/json",
    };
  }

  private async resolveWorkspace(): Promise<string> {
    if (this.workspaceId) return this.workspaceId;
    const r = await fetch(`${this.base}/workspaces`, { headers: this.headers });
    if (!r.ok) throw new Error(`Orgo workspaces -> ${r.status}`);
    const projects = (await r.json()).projects ?? [];
    if (!projects.length) throw new Error("No Orgo workspace for this key");
    this.workspaceId = projects[0].id;
    return this.workspaceId!;
  }

  async create(opts: {
    name: string;
    [k: string]: unknown;
  }): Promise<OrgoComputer> {
    const workspace_id = await this.resolveWorkspace();
    const r = await fetch(`${this.base}/computers`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({ workspace_id, ...opts }),
    });
    if (!r.ok) throw new Error(`Orgo create -> ${r.status}`);
    return new OrgoComputer(this.headers, this.base, await r.json());
  }

  async get(id: string): Promise<OrgoComputer> {
    const r = await fetch(`${this.base}/computers/${id}`, {
      headers: this.headers,
    });
    if (!r.ok) throw new Error(`Orgo get -> ${r.status}`);
    return new OrgoComputer(this.headers, this.base, await r.json());
  }

  async list(): Promise<OrgoComputer[]> {
    const r = await fetch(`${this.base}/workspaces`, { headers: this.headers });
    if (!r.ok) throw new Error(`Orgo list -> ${r.status}`);
    const out: OrgoComputer[] = [];
    for (const ws of (await r.json()).projects ?? [])
      for (const d of ws.desktops ?? [])
        out.push(new OrgoComputer(this.headers, this.base, d));
    return out;
  }
}
