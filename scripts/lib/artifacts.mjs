import { readFile } from "node:fs/promises";
import path from "node:path";
import {
  renderClaudeManifest, renderClaudeMarketplace, renderCodexManifest,
  renderCodexMarketplace, renderQoderManifest, renderCursorManifest,
  renderCursorMarketplace, renderOpenCodePackage, renderOpenCodeV2Package
} from "./manifests.mjs";

const templates = {
  "opencode/plugin.js": "opencode-plugin.js",
  "opencode-v2/plugin.js": "opencode-v2-plugin.js",
  "runtime/plugin-content.js": "runtime/plugin-content.js",
  "runtime/mcp.js": "runtime/mcp.js",
  "trae/install.mjs": "trae/install.mjs"
};

export async function pluginArtifacts(root, config) {
  const files = {
    ".codex-plugin/plugin.json": json(renderCodexManifest(config)),
    ".claude-plugin/plugin.json": json(renderClaudeManifest(config)),
    ".qoder-plugin/plugin.json": json(renderQoderManifest(config)),
    ".cursor-plugin/plugin.json": json(renderCursorManifest(config)),
    "package.json": json(renderOpenCodePackage(config)),
    "distribution/opencode-v2.package.json": json(renderOpenCodeV2Package(config))
  };
  for (const [destination, source] of Object.entries(templates)) {
    files[destination] = await readFile(path.join(root, "scripts/templates", source), "utf8");
  }
  return files;
}

export function marketplaceArtifacts(marketplace, configs) {
  return {
    ".agents/plugins/marketplace.json": json(renderCodexMarketplace(marketplace, configs)),
    ".claude-plugin/marketplace.json": json(renderClaudeMarketplace(marketplace, configs)),
    ".qoder-plugin/marketplace.json": json(renderClaudeMarketplace(marketplace, configs)),
    ".cursor-plugin/marketplace.json": json(renderCursorMarketplace(marketplace, configs))
  };
}

export function json(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}
