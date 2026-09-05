import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { loadMarketplaceConfig, loadPluginConfigs } from "./lib/plugin-config.mjs";
import { pluginArtifacts, marketplaceArtifacts } from "./lib/artifacts.mjs";

export const repositoryRoot = process.env.PLUGIN_MARKETPLACE_ROOT
  ? path.resolve(process.env.PLUGIN_MARKETPLACE_ROOT)
  : fileURLToPath(new URL("../", import.meta.url));

export async function syncAll(root = repositoryRoot) {
  const marketplace = await loadMarketplaceConfig(root);
  const plugins = await loadPluginConfigs(root);
  for (const { config, pluginRoot } of plugins) {
    for (const [relative, content] of Object.entries(await pluginArtifacts(root, config))) {
      await writeText(path.join(pluginRoot, relative), content);
    }
  }
  const configs = plugins.map(({ config }) => config);
  for (const [relative, content] of Object.entries(marketplaceArtifacts(marketplace, configs))) {
    await writeText(path.join(root, relative), content);
  }

  return configs;
}

async function writeText(filePath, value) {
  await mkdir(path.dirname(filePath), { recursive: true });
  await writeFile(filePath, value, "utf8");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const configs = await syncAll();
  console.log(`Synchronized ${configs.length} plugin group(s).`);
}
