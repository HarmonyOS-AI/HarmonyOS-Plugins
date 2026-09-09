import { fileURLToPath } from "node:url";
import { readFile } from "node:fs/promises";
import { loadPluginContent } from "../runtime/plugin-content.js";

const pluginRoot = fileURLToPath(new URL("../", import.meta.url));
const config = JSON.parse(await readFile(new URL("../plugin.config.json", import.meta.url), "utf8"));

// OpenCode V2 Plugin.define is an identity function. Export the plugin contract
// directly so this entrypoint does not import the incompatible V1 SDK.
export default {
  id: `harmonyos.${config.name}`,
  async setup(ctx) {
    const { skills, mcpServers } = await loadPluginContent(pluginRoot, "v2");
    const registrations = [];
    const dispose = async () => {
      while (registrations.length) await registrations.pop().dispose();
    };
    try {
      if (skills.size) registrations.push(await ctx.skill.transform((editor) => {
        for (const { directory, ...skill } of skills.values()) {
          if (!editor.get(skill.id)) editor.add(skill);
        }
      }));
      if (Object.keys(mcpServers).length) registrations.push(await ctx.mcp.transform((editor) => {
        for (const [name, server] of Object.entries(mcpServers)) {
          if (!editor.get(name)) editor.set(name, server);
        }
      }));
      return dispose;
    } catch (error) {
      await dispose();
      throw error;
    }
  }
};
