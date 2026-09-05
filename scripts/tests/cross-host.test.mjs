import test from "node:test";
import assert from "node:assert/strict";
import { cp, mkdir, mkdtemp, readFile, realpath, rm, symlink, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import os from "node:os";
import { pathToFileURL } from "node:url";
import { buildDistribution } from "../lib/distributions.mjs";
import { loadPluginContent } from "../templates/runtime/plugin-content.js";
import { installTrae } from "../templates/trae/install.mjs";

const repo = path.resolve(import.meta.dirname, "../..");
const readJson = async (file) => JSON.parse(await readFile(file, "utf8"));

async function fixture(t, components = "both") {
  const root = await realpath(await mkdtemp(path.join(os.tmpdir(), "cross-host-")));
  t.after(() => rm(root, { recursive: true, force: true }));
  await cp(path.join(repo, "scripts/templates"), path.join(root, "scripts/templates"), { recursive: true });
  await cp(path.join(repo, "marketplace.config.json"), path.join(root, "marketplace.config.json"));
  await symlink(path.join(repo, "node_modules"), path.join(root, "node_modules"), "dir");
  const skill = path.join(root, "sample-skill");
  await mkdir(path.join(skill, "references"), { recursive: true });
  await mkdir(path.join(skill, "scripts"));
  await writeFile(path.join(skill, "SKILL.md"), '---\nname: sample-skill\ndescription: >-\n  Review code: run a script\n  and read the reference.\n---\nRead `references/guide.md` and run `scripts/check.js`.\n');
  await writeFile(path.join(skill, "references/guide.md"), "Bundled reference\n");
  await writeFile(path.join(skill, "scripts/check.js"), 'console.log("check passed");\n');
  const mcpFile = path.join(root, "mcp.json");
  await writeFile(mcpFile, JSON.stringify({ mcpServers: {
    docs: { url: "https://example.com/mcp", headers: { "X-Source": "plugin" } },
    local: { command: "node", args: ["${CLAUDE_PLUGIN_ROOT}/server.js"], env: { MODE: "test" } }
  } }));
  const args = [path.join(repo, "scripts/create-plugin-group.mjs"), "sample", "--display-name", "Sample", "--description", "Portable plugin"];
  if (components !== "mcp") args.push("--skill", skill);
  if (components !== "skills") args.push("--mcp", mcpFile);
  const result = spawnSync(process.execPath, args, { encoding: "utf8", env: { ...process.env, PLUGIN_MARKETPLACE_ROOT: root } });
  assert.equal(result.status, 0, result.stderr);
  const pluginRoot = path.join(root, "plugins/sample");
  await writeFile(path.join(pluginRoot, "server.js"), "// Test fixture server entrypoint.\n");
  return { root, pluginRoot, config: await readJson(path.join(pluginRoot, "plugin.config.json")) };
}

for (const components of ["skills", "mcp", "both"]) {
  test(`new ${components} plugin defaults to every host`, async (t) => {
    const { root, pluginRoot, config } = await fixture(t, components);
    for (const host of ["codex", "claude", "qoder", "cursor"]) {
      const manifest = await readJson(path.join(pluginRoot, `.${host}-plugin/plugin.json`));
      assert.equal(manifest.name, "sample");
      if (["qoder", "cursor"].includes(host)) {
        assert.equal(manifest.skills, config.components.skills);
        assert.equal(manifest.mcpServers, config.components.mcpServers);
      }
    }
    for (const host of [".agents/plugins", ".claude-plugin", ".qoder-plugin", ".cursor-plugin"]) {
      const market = await readJson(path.join(root, host, "marketplace.json"));
      assert.equal(market.plugins[0].name, "sample");
    }
    assert.match(await readFile(path.join(pluginRoot, "trae/install.mjs"), "utf8"), /installTrae/);
    assert.equal((await readJson(path.join(pluginRoot, "distribution/opencode-v2.package.json"))).exports, "./opencode-v2/plugin.js");
    const validate = spawnSync(process.execPath, [path.join(repo, "scripts/validate-plugins.mjs")], {
      encoding: "utf8", env: { ...process.env, PLUGIN_MARKETPLACE_ROOT: root }
    });
    assert.equal(validate.status, 0, validate.stderr);
  });
}

test("OpenCode V1 loads bundled references and preserves host MCP overrides", async (t) => {
  const { pluginRoot } = await fixture(t);
  const { default: plugin } = await import(pathToFileURL(path.join(pluginRoot, "opencode/plugin.js")));
  const hooks = await plugin();
  const host = { mcp: { docs: { type: "remote", url: "https://override.example/mcp" } } };
  await hooks.config(host);
  assert.equal(host.mcp.docs.url, "https://override.example/mcp");
  assert.equal(host.mcp.local.command[1], path.join(pluginRoot, "server.js"));
  const loaded = await hooks.tool.sample_skill.execute({ skill: "sample-skill", resource: "references/guide.md" });
  assert.match(loaded, /Bundled reference/);
  await assert.rejects(hooks.tool.sample_skill.execute({ skill: "sample-skill", resource: "../../plugin.config.json" }), /escapes/);
});

test("OpenCode V2 registers native Skills and MCP with cleanup", async (t) => {
  const { pluginRoot } = await fixture(t);
  const { default: plugin } = await import(pathToFileURL(path.join(pluginRoot, "opencode-v2/plugin.js")));
  const skills = new Map();
  const mcp = new Map([["docs", { url: "https://override.example/mcp" }]]);
  const disposed = [];
  const ctx = {
    skill: { transform: async (fn) => {
      fn({ get: (id) => skills.get(id), add: (skill) => skills.set(skill.id, skill) });
      return { dispose: async () => disposed.push("skill") };
    } },
    mcp: { transform: async (fn) => {
      fn({ get: (id) => mcp.get(id), set: (id, value) => mcp.set(id, value) });
      return { dispose: async () => disposed.push("mcp") };
    } }
  };
  const cleanup = await plugin.setup(ctx);
  const skill = skills.get("sample-skill");
  assert.equal(skill.location, path.join(pluginRoot, "skills/sample-skill/SKILL.md"));
  assert.match(skill.description, /Review code: run a script and read the reference/);
  assert.ok(!skill.content.startsWith("---"));
  assert.equal(mcp.get("docs").url, "https://override.example/mcp");
  await cleanup();
  await cleanup();
  assert.deepEqual(disposed, ["mcp", "skill"]);
  disposed.length = 0;
  ctx.mcp.transform = async () => { throw new Error("MCP registration failed"); };
  await assert.rejects(plugin.setup(ctx), /MCP registration failed/);
  assert.deepEqual(disposed, ["skill"]);
});

test("TRAE installer retains complete resources, is repeatable, and fails before conflicting writes", async (t) => {
  const { root, pluginRoot } = await fixture(t);
  const project = path.join(root, "project with spaces");
  await mkdir(path.join(project, ".trae"), { recursive: true });
  const mcp = path.join(project, ".trae/mcp.json");
  await writeFile(mcp, JSON.stringify({ mcpServers: { existing: { url: "https://existing.example/mcp" } }, extra: true }));
  assert.equal((await installTrae(pluginRoot, project)).linkedSkills, 1);
  assert.equal((await installTrae(pluginRoot, project)).linkedSkills, 0);
  assert.equal(await realpath(path.join(project, ".trae/skills/sample-skill")), path.join(pluginRoot, "skills/sample-skill"));
  assert.match(await readFile(path.join(project, ".trae/skills/sample-skill/references/guide.md"), "utf8"), /Bundled reference/);
  const merged = await readJson(mcp);
  assert.equal(merged.extra, true);
  assert.equal(merged.mcpServers.existing.url, "https://existing.example/mcp");
  const conflicting = path.join(root, "conflict");
  await mkdir(path.join(conflicting, ".trae"), { recursive: true });
  await writeFile(path.join(conflicting, ".trae/mcp.json"), JSON.stringify({ mcpServers: { docs: { url: "https://other.example/mcp" } } }));
  await assert.rejects(installTrae(pluginRoot, conflicting), /already exists/);
  await assert.rejects(realpath(path.join(conflicting, ".trae/skills/sample-skill")), { code: "ENOENT" });
});

test("distribution archives retain manifests, Skill assets and isolated V2 entrypoint", async (t) => {
  const data = await fixture(t);
  const output = await buildDistribution(data, path.join(data.root, "dist"));
  const { archives } = await readJson(path.join(output, "artifacts.json"));
  assert.equal(archives["qoder-cn"], "sample-0.1.0.zip");
  const inspect = spawnSync("python3", ["-c", `
import json, sys, zipfile, tarfile, pathlib
root = pathlib.Path(sys.argv[1])
artifacts = json.loads((root / 'artifacts.json').read_text())['archives']
with zipfile.ZipFile(root / artifacts['qoder-cn']) as z:
    assert '.qoder-plugin/plugin.json' in z.namelist()
    assert '.cursor-plugin/plugin.json' in z.namelist()
    assert 'skills/sample-skill/scripts/check.js' in z.namelist()
    assert not any('node_modules/' in name for name in z.namelist())
with zipfile.ZipFile(root / artifacts['trae-work'][0]) as z:
    assert 'SKILL.md' in z.namelist()
    assert 'references/guide.md' in z.namelist()
with tarfile.open(root / artifacts['opencode-v2']) as t:
    package = json.load(t.extractfile('package/package.json'))
    assert package['name'] == '@harmonyos-ai/sample-v2'
    assert package['exports'] == './opencode-v2/plugin.js'
    assert '@opencode-ai/plugin' not in package['dependencies']
    assert 'package/runtime/plugin-content.js' in t.getnames()
    assert 'package/server.js' in t.getnames()
    t.extractall(root / 'unpacked', filter='data')
`, output], { encoding: "utf8" });
  assert.equal(inspect.status, 0, inspect.stderr);
  const { default: plugin } = await import(pathToFileURL(path.join(output, "unpacked/package/opencode-v2/plugin.js")));
  assert.equal(typeof plugin.setup, "function");
});

test("custom component paths work and missing declared resources fail loudly", async (t) => {
  const { pluginRoot, config } = await fixture(t);
  await cp(path.join(pluginRoot, "skills"), path.join(pluginRoot, "knowledge"), { recursive: true });
  await cp(path.join(pluginRoot, ".mcp.json"), path.join(pluginRoot, "servers.json"));
  config.components = { skills: "./knowledge", mcpServers: "./servers.json" };
  await writeFile(path.join(pluginRoot, "plugin.config.json"), JSON.stringify(config));
  assert.equal((await loadPluginContent(pluginRoot, "v2")).skills.size, 1);
  await rm(path.join(pluginRoot, "servers.json"));
  await assert.rejects(loadPluginContent(pluginRoot, "v2"), { code: "ENOENT" });
});
