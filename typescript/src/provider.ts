// Normalized external-compute interface (TypeScript).
// Mirrors the Python `external_compute` package: any provider implementing
// ComputeProvider + ExternalComputer becomes a drop-in compute source that a
// MIOSA agent — or your own harness — can drive without knowing the vendor.

export interface ExecResult {
  output: string;
  exitCode: number;
  error?: string | null;
}

export interface ShellEndpoint {
  kind: "ssh" | "websocket" | "exec-only";
  uri: string;
  token?: string;
  meta?: Record<string, unknown>;
}

export interface ComputerInfo {
  id: string;
  name: string;
  provider: string;
  status: string;
  publicUrl?: string | null;
  raw?: Record<string, unknown>;
}

export interface ExternalComputer {
  readonly info: ComputerInfo;

  // orchestration core (the "SSH path")
  exec(command: string, opts?: { timeout?: number }): Promise<ExecResult>;
  shellEndpoint(): ShellEndpoint;

  // computer-use (optional — may throw if unsupported)
  screenshot(): Promise<Uint8Array>;
  leftClick(x: number, y: number): Promise<void>;
  type(text: string): Promise<void>;
  key(key: string): Promise<void>;

  // files (optional)
  writeFile(path: string, content: string): Promise<void>;
  readFile(path: string): Promise<string>;

  // port ingress (optional — many providers can't; use a MIOSA tunnel)
  previewUrl?(port: number, path?: string): string;

  // lifecycle
  stop(): Promise<void>;
  destroy(): Promise<void>;
}

export interface ComputeProvider {
  readonly name: string;
  create(opts: {
    name: string;
    [k: string]: unknown;
  }): Promise<ExternalComputer>;
  get(id: string): Promise<ExternalComputer>;
  list(): Promise<ExternalComputer[]>;
}
