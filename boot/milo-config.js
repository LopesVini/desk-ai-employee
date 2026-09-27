
// Milo overrides, appended to the base's /opt/plow/boot/config.js by our
// Dockerfile. The base's function was renamed to renderConfigBase; boot
// imports this renderConfig and gets the base config with Milo's changes.
export function renderConfig(identity, apiBase) {
  const config = renderConfigBase(identity, apiBase);
  const defaults = config.agents.defaults;
  // GLM 5.2 invented facts and misjudged fit in the 26/09 comparison.
  defaults.model = { primary: "plow/anthropic/claude-sonnet-5", fallbacks: ["plow/z-ai/glm-5.2"] };
  // The base declares 1M-token windows, so pruning and compaction only start
  // near 300k tokens. A group reached ~300k and each message cost ~US$ 0.60.
  // A smaller declared window makes them start early.
  for (const model of config.models.providers.plow.models) model.contextWindow = 128000;
  // Trim old tool results (fetched pages) instead of resending them every turn.
  defaults.contextPruning = { mode: "cache-ttl", ttl: "5m" };
  // Milo does nothing proactive and scheduled delivery failed T6-B; each
  // heartbeat re-read the main session (~US$ 0.17 every 30 minutes on Sonnet).
  defaults.heartbeat = { every: "0m" };
  // The base's "messaging" profile leaves out the cron tool, so Milo could not
  // schedule anything (likely why T6-B failed). Proactive work is explicit jobs.
  config.tools.alsoAllow = [...new Set([...(config.tools.alsoAllow ?? []), "cron"])];
  return config;
}
