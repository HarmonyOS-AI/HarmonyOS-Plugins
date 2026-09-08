import { lstat, mkdir, readFile, readdir, realpath, symlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { expandPluginRoot } from "../runtime/mcp.js";

// Links retain each Skill's scripts and references without duplicating large SDKs.
export async function installTrae(pluginRoot, projectRoot) {
  const project = await realpath(projectRoot);
  const root = await realpath(pluginRoot);
  const config = JSON.parse(await readFile(path.join(root, "plugin.config.json"), "utf8"));
  const target = path.join(project, ".trae");
  const links = [];
  if (config.components.skills) {
    const skillsRoot = await resolveComponent(root, config.components.skills);
    for (const entry of await readdir(skillsRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const source = await resolveComponent(skillsRoot, entry.name);
      await readFile(path.join(source, "SKILL.md"), "utf8");
      const destination = path.join(target, "skills", entry.name);
      let existing;
      try {
        existing = await lstat(destination);
      } catch (error) {
        if (error.code !== "ENOENT") throw error;
      }
      if (existing) {
        if (!existing.isSymbolicLink() || await realpath(destination) !== source) {
          throw new Error(`Skill already exists; refusing to replace: ${destination}`);
        }
      } else {
        links.push({ source, destination });
      }
    }
  }
  const mcpPath = path.join(target, "mcp.json");
  let merged;
  if (config.components.mcpServers) {
    const source = JSON.parse(await readFile(await resolveComponent(root, config.components.mcpServers), "utf8"));
    assertObject(source.mcpServers, "mcpServers");
    merged = await readOptionalJson(mcpPath);
    assertObject(merged, "TRAE MCP configuration");
    merged.mcpServers ??= {};
    assertObject(merged.mcpServers, "Existing mcpServers");
    for (const [name, value] of Object.entries(source.mcpServers)) {
      const server = expandPluginRoot(value, root);
      const existing = Object.hasOwn(merged.mcpServers, name) ? merged.mcpServers[name] : undefined;
      if (existing && JSON.stringify(existing) !== JSON.stringify(server)) {
        throw new Error(`MCP server '${name}' already exists with different settings.`);
      }
      merged.mcpServers = { ...merged.mcpServers, [name]: server };
    }
  }
  // Complete conflict checks for every component before changing the project.
  for (const { source, destination } of links) {
    await mkdir(path.dirname(destination), { recursive: true });
    await symlink(source, destination, process.platform === "win32" ? "junction" : "dir");
  }
  if (merged) {
    await mkdir(target, { recursive: true });
    await writeFile(mcpPath, `${JSON.stringify(merged, null, 2)}\n`);
  }
  return { plugin: config.name, project, linkedSkills: links.length, mcp: Boolean(merged) };
}

async function resolveComponent(root, relative) {
  if (path.isAbsolute(relative) || relative.split(/[\\/]/).includes("..")) throw new Error("Invalid component path.");
  const resolved = await realpath(path.resolve(root, relative));
  if (!resolved.startsWith(`${root}${path.sep}`)) throw new Error("Component escapes plugin root.");
  return resolved;
}

async function readOptionalJson(file) {
  try { return JSON.parse(await readFile(file, "utf8")); }
  catch (error) {
    if (error.code === "ENOENT") return {};
    throw error;
  }
}

function assertObject(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const args = process.argv.slice(2);
  if (args.length !== 2 || args[0] !== "--project") {
    throw new Error("Usage: node trae/install.mjs --project /absolute/path/to/project");
  }
  const result = await installTrae(fileURLToPath(new URL("../", import.meta.url)), path.resolve(args[1]));
  console.log(JSON.stringify(result, null, 2));
  console.log("Reload TRAE CN; enable project MCP in Settings > MCP if this plugin includes MCP servers.");
}
