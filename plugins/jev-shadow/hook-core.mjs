import { readdirSync, lstatSync } from "node:fs";
import { join } from "node:path";
import { spawn } from "node:child_process";

const ACCOUNT_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*\.md$/;

function snapshot(mesa) {
  const dir = join(mesa, "contas");
  const files = new Map();
  try {
    for (const name of readdirSync(dir)) {
      if (!ACCOUNT_NAME.test(name)) continue;
      const path = join(dir, name);
      const stat = lstatSync(path, { bigint: true });
      if (stat.isFile()) files.set(path, `${stat.mtimeNs}:${stat.size}`);
    }
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
  return files;
}

export function createHook({ mesa, runner, enabled = () => process.env.JEV_ENABLED === "1" &&
  process.env.JEV_MODE === "shadow", spawnProcess = spawn }) {
  const before = new Map();
  const key = (event, ctx) => event?.runId ?? ctx?.runId;
  return {
    beforeAgentRun(event, ctx) {
      if (!enabled()) return;
      const runId = key(event, ctx);
      if (runId) before.set(runId, snapshot(mesa));
    },
    agentEnd(event, ctx) {
      const runId = key(event, ctx);
      const old = runId && before.get(runId);
      if (runId) before.delete(runId);
      if (!enabled() || !old || event?.success === false) return;
      for (const [path, stamp] of snapshot(mesa)) {
        if (old.get(path) === stamp) continue;
        // The child runs after the completed turn. Its answer is never part of Milo's reply.
        const child = spawnProcess("python3", [runner, "--mesa", mesa, "--account", path],
                                   { stdio: "ignore", env: process.env });
        child.on?.("error", () => {});
        child.unref?.();
      }
    },
  };
}
