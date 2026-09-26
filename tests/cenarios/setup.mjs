// Monta uma instalação de teste do Milo sem o canal da Plow: mesmo prompt,
// mesmas skills e mesmo provedor de modelo, mas nada conecta à linha.
import { mkdir, readFile, writeFile, rm } from "node:fs/promises";
import { renderConfig } from "/opt/plow/boot/config.js";

const base = process.env.PLOW_API_BASE.replace(/\/$/, "");
const config = renderConfig({ agent: { name: "Milo" }, line: { uid: "ln_teste" }, chats: [] }, base);
delete config.plugins; delete config.channels; delete config.bindings; delete config.mcp;
config.tools.alsoAllow = config.tools.alsoAllow.filter(t => t !== "plow_start_thread");
await mkdir("/var/lib/plow/workspace", { recursive: true });
for (const n of ["BOOTSTRAP.md", "SOUL.md", "IDENTITY.md", "USER.md"]) await rm(`/var/lib/plow/workspace/${n}`, { force: true });
await writeFile("/var/lib/plow/workspace/AGENTS.md", await readFile("/opt/plow/prompt/AGENTS.md", "utf8"));
await writeFile("/var/lib/plow/openclaw.json", JSON.stringify(config, null, 2) + "\n", { mode: 0o600 });
console.log("setup ok");
