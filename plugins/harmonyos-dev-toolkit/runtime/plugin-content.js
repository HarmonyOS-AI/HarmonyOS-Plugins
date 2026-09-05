import { readFile, readdir, realpath } from "node:fs/promises";
import path from "node:path";
import { parse } from "yaml";
import { expandPluginRoot, toOpenCodeMcp } from "./mcp.js";

export async function loadPluginContent(pluginRoot, version) {
  pluginRoot = await realpath(pluginRoot);
  const config = JSON.parse(await readFile(path.join(pluginRoot, "plugin.config.json"), "utf8"));
  const skills = new Map();
  if (config.components.skills) {
    const root = await containedPath(pluginRoot, config.components.skills);
    for (const entry of (await readdir(root, { withFileTypes: true })).sort((a, b) => a.name.localeCompare(b.name))) {
      if (!entry.isDirectory()) continue;
      const location = await containedPath(root, `${entry.name}/SKILL.md`);
      const source = await readFile(location, "utf8");
      const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
      const metadata = match ? parse(match[1]) : null;
      if (metadata?.name !== entry.name || typeof metadata?.description !== "string" || !metadata.description.trim()) {
        throw new Error(`Invalid Skill name/description: ${location}`);
      }
      skills.set(entry.name, {
        id: entry.name, name: metadata.name, description: metadata.description.trim(),
        directory: path.dirname(location), location,
        content: source.slice(match[0].length)
      });
    }
  }
  let mcpServers = {};
  if (config.components.mcpServers) {
    const source = JSON.parse(await readFile(await containedPath(pluginRoot, config.components.mcpServers), "utf8"));
    if (!source.mcpServers || typeof source.mcpServers !== "object" || Array.isArray(source.mcpServers)) {
      throw new Error("MCP configuration must contain a mcpServers object.");
    }
    mcpServers = Object.fromEntries(Object.entries(source.mcpServers).map(([name, server]) => [
      name, toOpenCodeMcp(expandPluginRoot(server, pluginRoot), version)
    ]));
  }
  return { config, skills, mcpServers };
}

export async function containedPath(root, relative) {
  if (path.isAbsolute(relative) || relative.split(/[\\/]/).includes("..")) {
    throw new Error(`Component path must stay inside the plugin: ${relative}`);
  }
  const base = await realpath(root);
  const resolved = await realpath(path.resolve(base, relative));
  if (resolved !== base && !resolved.startsWith(`${base}${path.sep}`)) {
    throw new Error(`Component path escapes the plugin: ${relative}`);
  }
  return resolved;
}
