import { cp, mkdir, mkdtemp, readdir, rename, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import { renderOpenCodeV2Package } from "./manifests.mjs";
import { json } from "./artifacts.mjs";
import { loadPluginContent } from "../templates/runtime/plugin-content.js";

const run = promisify(execFile);
const zipScript = fileURLToPath(new URL("../zip-directory.py", import.meta.url));
const excluded = new Set(["node_modules", ".git", ".DS_Store", "__pycache__", ".skill-workspaces", ".eval-runs", ".eval-cache"]);

export async function buildDistribution({ config, pluginRoot }, outputRoot) {
  await loadPluginContent(pluginRoot, "v1");
  await loadPluginContent(pluginRoot, "v2");
  await mkdir(outputRoot, { recursive: true });
  const staging = await mkdtemp(path.join(outputRoot, ".build-"));
  const destination = path.join(outputRoot, `${config.name}-${config.version}`);
  try {
    const bundle = path.join(staging, "plugin");
    await cp(pluginRoot, bundle, {
      recursive: true,
      filter: (source) => !excluded.has(path.basename(source)) && !source.endsWith(".pyc")
    });
    const archives = {};
    const pluginZip = `${config.name}-${config.version}.zip`;
    await zipDirectory(bundle, path.join(staging, pluginZip));
    for (const host of ["claude", "codex", "cursor"]) archives[host] = "plugin/";
    archives["qoder-cn"] = pluginZip;
    archives["trae-cn"] = "plugin/trae/install.mjs";
    archives["opencode-v1"] = await npmPack(bundle, staging);

    const v2 = path.join(staging, "opencode-v2");
    await cp(bundle, v2, { recursive: true });
    await writeFile(path.join(v2, "package.json"), json(renderOpenCodeV2Package(config)));
    archives["opencode-v2"] = await npmPack(v2, staging);

    archives["trae-work"] = [];
    if (config.components.skills) {
      const skills = path.resolve(bundle, config.components.skills);
      await mkdir(path.join(staging, "trae-work"));
      for (const entry of await readdir(skills, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        const relative = `trae-work/${entry.name}-${config.version}.zip`;
        await zipDirectory(path.join(skills, entry.name), path.join(staging, relative));
        archives["trae-work"].push(relative);
      }
    }
    await writeFile(path.join(staging, "artifacts.json"), json({ plugin: config.name, version: config.version, archives }));
    await rm(destination, { recursive: true, force: true });
    await rename(staging, destination);
    return destination;
  } catch (error) {
    await rm(staging, { recursive: true, force: true });
    throw error;
  }
}

async function npmPack(root, destination) {
  const { stdout } = await run(process.platform === "win32" ? "npm.cmd" : "npm", [
    "pack", "--json", "--ignore-scripts", "--pack-destination", destination
  ], { cwd: root, maxBuffer: 32 * 1024 * 1024 });
  return JSON.parse(stdout)[0].filename;
}

async function zipDirectory(root, output) {
  await run(process.env.PYTHON ?? "python3", [zipScript, root, output]);
}
