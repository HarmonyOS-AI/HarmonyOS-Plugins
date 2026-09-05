import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { cp, mkdir, mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { validatePluginConfig } from "../lib/plugin-config.mjs";
import { renderCodexMarketplace, renderQoderManifest } from "../lib/manifests.mjs";

const repositoryRoot = path.resolve(import.meta.dirname, "../..");

const config = {
  name: "sample-plugin",
  version: "1.2.3",
  displayName: "Sample Plugin",
  description: "A complete sample plugin.",
  shortDescription: "A sample plugin",
  longDescription: "A complete sample plugin used by tests.",
  author: { name: "Example", url: "https://example.com" },
  homepage: "https://example.com/plugin",
  repository: "https://example.com/repository",
  keywords: ["sample"],
  category: "Developer Tools",
  capabilities: ["Read"],
  defaultPrompt: [],
  brandColor: "#000000",
  components: { skills: "./skills/" },
  opencode: { packageName: "@example/sample-plugin", toolName: "sample_plugin_skill" }
};

test("plugin config accepts aligned portable identifiers", () => {
  assert.doesNotThrow(() => validatePluginConfig(config, "sample-plugin"));
});

test("plugin config rejects a directory/name mismatch", () => {
  assert.throws(() => validatePluginConfig(config, "other-plugin"), /must live/);
});

test("marketplace paths point at isolated plugin roots", () => {
  const marketplace = renderCodexMarketplace(
    { name: "example", displayName: "Example" },
    [config]
  );
  assert.equal(marketplace.plugins[0].source.path, "./plugins/sample-plugin");
});

test("Qoder receives the shared semantic version", () => {
  assert.equal(renderQoderManifest(config).version, "1.2.3");
});

test("plugin scaffolding initializes an empty marketplace root", async () => {
  const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), "plugin-marketplace-test-"));
  try {
    await mkdir(path.join(temporaryRoot, "scripts", "templates"), { recursive: true });
    await cp(
      path.join(repositoryRoot, "marketplace.config.json"),
      path.join(temporaryRoot, "marketplace.config.json")
    );
    await cp(
      path.join(repositoryRoot, "scripts", "templates"),
      path.join(temporaryRoot, "scripts", "templates"),
      { recursive: true }
    );

    const result = spawnSync(
      process.execPath,
      [
        path.join(repositoryRoot, "scripts", "create-plugin-group.mjs"),
        "empty-root-sample",
        "--display-name",
        "Empty Root Sample",
        "--description",
        "Validates creation without a pre-existing plugins directory.",
        "--skill",
        path.join(repositoryRoot, "plugins", "harmonyos-dev-toolkit", "skills", "arkts-rules")
      ],
      {
        cwd: repositoryRoot,
        encoding: "utf8",
        env: { ...process.env, PLUGIN_MARKETPLACE_ROOT: temporaryRoot }
      }
    );

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Created plugins\/empty-root-sample/);
  } finally {
    await rm(temporaryRoot, { recursive: true, force: true });
  }
});
