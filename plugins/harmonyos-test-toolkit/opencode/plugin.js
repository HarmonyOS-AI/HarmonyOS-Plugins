import { readdir, readFile, realpath, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { tool } from "@opencode-ai/plugin";
import { loadPluginContent } from "../runtime/plugin-content.js";

const pluginRoot = fileURLToPath(new URL("../", import.meta.url));
const { config, skills, mcpServers } = await loadPluginContent(pluginRoot, "v1");

export default async function portableSkillPlugin() {
  return {
    config: async (hostConfig) => {
      if (Object.keys(mcpServers).length === 0) {
        return;
      }
      hostConfig.mcp ??= {};
      for (const [name, server] of Object.entries(mcpServers)) {
        hostConfig.mcp[name] ??= server;
      }
    },
    ...(skills.size > 0 ? { tool: {
      [config.opencode.toolName]: tool({
        description: `Load instructions or a supporting text resource from ${config.displayName}.`,
        args: {
          skill: tool.schema.string().describe("Exact skill ID from the advertised catalog."),
          resource: tool.schema.string().optional().describe("Optional path relative to the skill directory.")
        },
        async execute({ skill, resource }) {
          const selected = skills.get(skill);
          if (!selected) {
            return `Unknown skill '${skill}'. Available skills: ${[...skills.keys()].join(", ")}`;
          }

          const relativeResource = resource ?? "SKILL.md";
          const resourcePath = await resolveContainedPath(selected.directory, relativeResource);
          const resourceStat = await stat(resourcePath);
          if (resourceStat.isDirectory()) {
            const entries = await readdir(resourcePath);
            return JSON.stringify({
              skill,
              baseDirectory: selected.directory,
              resource: relativeResource,
              entries: entries.sort()
            });
          }
          if (resourceStat.size > 2_000_000) {
            return `Resource is ${resourceStat.size} bytes. Search or read it in smaller ranges from ${resourcePath}.`;
          }

          const content = await readFile(resourcePath, "utf8");
          return [
            `Plugin: ${config.name}`,
            `Skill: ${skill}`,
            `Base directory: ${selected.directory}`,
            `Resource: ${relativeResource}`,
            "",
            content
          ].join("\n");
        }
      })
    } } : {}),
    ...(skills.size > 0 ? { "experimental.chat.system.transform": async (_input, output) => {
      const catalog = [...skills.values()]
        .map((skill) => `- ${skill.id}: ${skill.description}`)
        .join("\n");
      output.system.push([
        `${config.displayName} is installed as an OpenCode plugin.`,
        `When a task matches one of the skills below, call the ${config.opencode.toolName} tool before acting.`,
        `Use the same tool's resource argument for supporting files referenced by a loaded skill.`,
        catalog
      ].join("\n"));
    } } : {})
  };
}

async function resolveContainedPath(root, relativePath) {
  if (path.isAbsolute(relativePath)) {
    throw new Error("Resource paths must be relative to the skill directory.");
  }
  const resolvedRoot = await realpath(root);
  const candidate = await realpath(path.resolve(root, relativePath));
  if (candidate !== resolvedRoot && !candidate.startsWith(`${resolvedRoot}${path.sep}`)) {
    throw new Error("Resource path escapes the selected skill directory.");
  }
  return candidate;
}
