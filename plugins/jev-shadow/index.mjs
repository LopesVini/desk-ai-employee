import { createHook } from "./hook-core.mjs";

export default {
  id: "milo-jev-shadow",
  name: "Milo Jev shadow post-step",
  description: "Observe completed account-file writes and record Jev separately.",
  register(api) {
    const hook = createHook({
      mesa: process.env.MILO_MESA ?? "/var/lib/plow/workspace/mesa",
      runner: "/opt/plow/skills/qualificar-conta/scripts/jev-poststep.py",
    });
    api.on("before_agent_run", (event, ctx) => {
      try { hook.beforeAgentRun(event, ctx); }
      catch { /* Shadow observation must never gate Milo. */ }
    });
    api.on("agent_end", (event, ctx) => {
      try { hook.agentEnd(event, ctx); }
      catch { /* No shadow failure can change a completed turn. */ }
    });
  },
};
