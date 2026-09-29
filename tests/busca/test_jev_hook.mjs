import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHook } from "../../plugins/jev-shadow/hook-core.mjs";

function fixture(enabled = true) {
  const mesa = mkdtempSync(join(tmpdir(), "jev-hook-"));
  mkdirSync(join(mesa, "contas"));
  const calls = [];
  const hook = createHook({ mesa, runner: "/poststep.py", enabled: () => enabled,
    spawnProcess: (command, args, options) => {
      calls.push({ command, args, options });
      return { on() {}, unref() {} };
    } });
  return { mesa, hook, calls, done: () => rmSync(mesa, { recursive: true, force: true }) };
}

test("disabled produces no post-step", () => {
  const x = fixture(false);
  try {
    x.hook.beforeAgentRun({}, { runId: "one" });
    writeFileSync(join(x.mesa, "contas/empresa.md"), "saved");
    x.hook.agentEnd({ success: true }, { runId: "one" });
    assert.equal(x.calls.length, 0);
  } finally { x.done(); }
});

test("persisted account spawns one detached post-step; unchanged turn spawns none", () => {
  const x = fixture();
  try {
    x.hook.beforeAgentRun({}, { runId: "one" });
    const path = join(x.mesa, "contas/empresa.md");
    writeFileSync(path, "saved");
    x.hook.agentEnd({ success: true }, { runId: "one" });
    assert.equal(x.calls.length, 1);
    assert.deepEqual(x.calls[0].args, ["/poststep.py", "--mesa", x.mesa, "--account", path]);
    assert.equal(x.calls[0].options.stdio, "ignore");
    x.hook.beforeAgentRun({}, { runId: "two" });
    x.hook.agentEnd({ success: true }, { runId: "two" });
    assert.equal(x.calls.length, 1);
  } finally { x.done(); }
});

test("failed run and non-account writes do not spawn", () => {
  const x = fixture();
  try {
    x.hook.beforeAgentRun({}, { runId: "one" });
    writeFileSync(join(x.mesa, "contas/empresa.md"), "saved");
    x.hook.agentEnd({ success: false }, { runId: "one" });
    assert.equal(x.calls.length, 0);
  } finally { x.done(); }
});
