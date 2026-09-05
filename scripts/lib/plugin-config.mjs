import { access, readdir, readFile } from "node:fs/promises";
import path from "node:path";

const PLUGIN_NAME_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const TOOL_NAME_PATTERN = /^[a-z][a-z0-9_]*$/;
const SEMVER_PATTERN = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;

export async function loadMarketplaceConfig(repositoryRoot) {
  return readJson(path.join(repositoryRoot, "marketplace.config.json"));
}

export async function loadPluginConfigs(repositoryRoot) {
  const pluginsRoot = path.join(repositoryRoot, "plugins");
  const entries = await readdir(pluginsRoot, { withFileTypes: true });
  const configs = [];

  for (const entry of entries.filter((item) => item.isDirectory()).sort(byName)) {
    const pluginRoot = path.join(pluginsRoot, entry.name);
    const configPath = path.join(pluginRoot, "plugin.config.json");

    try {
      await access(configPath);
    } catch {
      continue;
    }

    const config = await readJson(configPath);
    validatePluginConfig(config, entry.name);
    configs.push({ config, pluginRoot });
  }

  if (configs.length === 0) {
    throw new Error("No plugin.config.json files were found under plugins/.");
  }

  assertUnique(configs, ({ config }) => config.name, "plugin name");
  assertUnique(configs, ({ config }) => config.opencode.toolName, "OpenCode tool name");
  const packages = configs.flatMap(({ config }) => [config.opencode.packageName, `${config.opencode.packageName}-v2`]);
  assertUnique(packages, (name) => name, "OpenCode package name");
  return configs;
}

export function validatePluginConfig(config, directoryName) {
  requireString(config.name, "name");
  requireString(config.version, "version");
  requireString(config.displayName, "displayName");
  requireString(config.description, "description");
  requireString(config.shortDescription, "shortDescription");
  requireString(config.longDescription, "longDescription");
  requireString(config.author?.name, "author.name");
  requireString(config.author?.url, "author.url");
  requireString(config.homepage, "homepage");
  requireString(config.repository, "repository");
  requireString(config.category, "category");
  requireString(config.brandColor, "brandColor");
  requireString(config.opencode?.packageName, "opencode.packageName");
  requireString(config.opencode?.toolName, "opencode.toolName");

  if (!config.components?.skills && !config.components?.mcpServers) {
    throw new Error(`Plugin ${config.name} must define skills, MCP servers, or both.`);
  }
  if (config.components.skills) {
    requireString(config.components.skills, "components.skills");
  }
  if (config.components.mcpServers) {
    requireString(config.components.mcpServers, "components.mcpServers");
  }
  for (const [component, relative] of Object.entries(config.components)) {
    if (!["skills", "mcpServers"].includes(component)) {
      throw new Error(`Unsupported portable component: ${component}`);
    }
    if (!relative.startsWith("./") || relative.includes("\\") || relative.split("/").includes("..") || relative === "./") {
      throw new Error(`components.${component} must be a ./ path inside the plugin.`);
    }
  }

  if (!PLUGIN_NAME_PATTERN.test(config.name)) {
    throw new Error(`Invalid plugin name: ${config.name}`);
  }
  if (config.name !== directoryName) {
    throw new Error(`Plugin ${config.name} must live in plugins/${config.name}.`);
  }
  if (!SEMVER_PATTERN.test(config.version)) {
    throw new Error(`Plugin ${config.name} has an invalid semantic version: ${config.version}`);
  }
  if (!TOOL_NAME_PATTERN.test(config.opencode.toolName)) {
    throw new Error(`Plugin ${config.name} has an invalid OpenCode tool name.`);
  }

  requireStringArray(config.keywords, "keywords");
  requireStringArray(config.capabilities, "capabilities");
  requireStringArray(config.defaultPrompt, "defaultPrompt");
  if (config.defaultPrompt.length > 3) {
    throw new Error(`Plugin ${config.name} can define at most three default prompts.`);
  }
}

export async function readJson(filePath) {
  const source = await readFile(filePath, "utf8");
  return JSON.parse(source);
}

function requireString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Expected ${field} to be a non-empty string.`);
  }
}

function requireStringArray(value, field) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || item.trim() === "")) {
    throw new Error(`Expected ${field} to be an array of non-empty strings.`);
  }
}

function assertUnique(items, selector, label) {
  const values = new Set();
  for (const item of items) {
    const value = selector(item);
    if (values.has(value)) {
      throw new Error(`Duplicate ${label}: ${value}`);
    }
    values.add(value);
  }
}

function byName(left, right) {
  return left.name.localeCompare(right.name);
}
