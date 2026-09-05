import path from "node:path";
import { syncAll, repositoryRoot } from "./sync-manifests.mjs";
import { loadPluginConfigs } from "./lib/plugin-config.mjs";
import { buildDistribution } from "./lib/distributions.mjs";

const names = process.argv.slice(2);
await syncAll();
const plugins = await loadPluginConfigs(repositoryRoot);
for (const name of names) {
  if (!plugins.some(({ config }) => config.name === name)) throw new Error(`Unknown plugin: ${name}`);
}
for (const plugin of plugins.filter(({ config }) => !names.length || names.includes(config.name))) {
  console.log(await buildDistribution(plugin, path.join(repositoryRoot, "dist")));
}
