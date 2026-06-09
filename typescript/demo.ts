// End-to-end demo (TypeScript): provision an Orgo box, drive it, tear it down.
//   ORGO_API_KEY=sk_live_... npx tsx demo.ts
import { OrgoProvider } from "./src/orgo.js";

async function main() {
  const provider = new OrgoProvider();
  console.log(`→ provider: ${provider.name}`);

  const t0 = Date.now();
  const computer = await provider.create({ name: "miosa-orgo-ts-demo" });
  console.log(
    `→ created ${computer.info.id} in ${Date.now() - t0}ms (status=${computer.info.status})`,
  );

  try {
    for (const cmd of ["whoami", "uname -sm", "nproc"]) {
      const r = await computer.exec(cmd);
      console.log(
        `  $ ${cmd.padEnd(12)} -> ${r.output.trim()} (exit ${r.exitCode})`,
      );
    }
    const ep = computer.shellEndpoint();
    console.log(`  shell: kind=${ep.kind} uri=${ep.uri.slice(0, 60)}...`);
  } finally {
    await computer.destroy();
    console.log(`→ destroyed ${computer.info.id}`);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
