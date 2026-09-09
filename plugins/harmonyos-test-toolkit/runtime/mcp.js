export function expandPluginRoot(value, pluginRoot) {
  if (typeof value === "string") return value.replace(/\$\{(?:CLAUDE|QODER|CURSOR)_PLUGIN_ROOT\}/g, () => pluginRoot);
  if (Array.isArray(value)) return value.map((item) => expandPluginRoot(item, pluginRoot));
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, expandPluginRoot(item, pluginRoot)]));
  return value;
}

export function toOpenCodeMcp(server, version) {
  if (!server || typeof server !== "object" || Array.isArray(server)) throw new Error("Invalid MCP server.");
  const allowed = new Set(["type", "command", "args", "env", "cwd", "url", "headers", "disabled"]);
  for (const field of Object.keys(server)) {
    if (!allowed.has(field)) throw new Error(`MCP field '${field}' has no portable mapping for OpenCode ${version}.`);
  }
  const state = server.disabled === undefined ? {} : version === "v2"
    ? { disabled: server.disabled } : { enabled: !server.disabled };
  if (typeof server.command === "string" && server.command) {
    if (server.args && (!Array.isArray(server.args) || server.args.some((arg) => typeof arg !== "string"))) {
      throw new Error("MCP args must be an array of strings.");
    }
    if (server.cwd && version === "v1") throw new Error("OpenCode V1 does not support MCP cwd; use absolute script paths.");
    return {
      type: "local", command: [server.command, ...(server.args ?? [])],
      ...(server.env ? { environment: server.env } : {}),
      ...(server.cwd ? { cwd: server.cwd } : {}), ...state
    };
  }
  if (typeof server.url === "string" && /^https?:\/\//.test(server.url)) {
    return { type: "remote", url: server.url, ...(server.headers ? { headers: server.headers } : {}), ...state };
  }
  throw new Error("MCP server must define command or an HTTP(S) url.");
}
