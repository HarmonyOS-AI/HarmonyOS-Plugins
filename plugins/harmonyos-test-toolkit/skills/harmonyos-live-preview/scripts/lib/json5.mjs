// Minimal tolerant reader for HarmonyOS *.json5 config files.
// Strips `//` line comments, `/* */` block comments, quotes bare (unquoted) object keys, and drops
// trailing commas — enough for the generated build-profile.json5 / module.json5 / oh-package.json5 /
// *.json files as well as the hand-edited ones found in real projects. Every pass is string-aware so
// comment/comma markers inside string literals are preserved. Single-quoted strings are handled as a
// last-resort fallback.

function stripComments(text) {
  let out = '';
  let quote = null; // active string delimiter or null
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    const c2 = text[i + 1];
    if (quote) {
      out += c;
      if (c === '\\') { out += c2 ?? ''; i++; continue; }
      if (c === quote) quote = null;
      continue;
    }
    if (c === '"' || c === "'") { quote = c; out += c; continue; }
    if (c === '/' && c2 === '/') { while (i < text.length && text[i] !== '\n') i++; out += '\n'; continue; }
    if (c === '/' && c2 === '*') { i += 2; while (i < text.length && !(text[i] === '*' && text[i + 1] === '/')) i++; i++; continue; }
    out += c;
  }
  return out;
}

// `{ dependencies: { commonlib: "file:../x" } }` → `{ "dependencies": { "commonlib": "file:../x" } }`.
// Only identifiers sitting in key position (preceded by `{` or `,`, followed by `:`) are quoted, so
// bare literals like `true` / `null` in value position are left alone.
function quoteBareKeys(text) {
  const isIdent = (c) => c !== undefined && /[A-Za-z0-9_$]/.test(c);
  let out = '';
  let quote = null;
  let prev = ''; // last non-whitespace character emitted
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quote) {
      out += c;
      if (c === '\\') { out += text[i + 1] ?? ''; i++; continue; }
      if (c === quote) { quote = null; prev = c; }
      continue;
    }
    if (c === '"' || c === "'") { quote = c; out += c; prev = c; continue; }
    if (/[A-Za-z_$]/.test(c) && (prev === '{' || prev === ',')) {
      let end = i;
      while (isIdent(text[end])) end++;
      let after = end;
      while (after < text.length && /\s/.test(text[after])) after++;
      const ident = text.slice(i, end);
      out += text[after] === ':' ? `"${ident}"` : ident;
      i = end - 1;
      prev = ident[ident.length - 1];
      continue;
    }
    out += c;
    if (!/\s/.test(c)) prev = c;
  }
  return out;
}

function stripTrailingCommas(text) {
  let out = '';
  let quote = null;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quote) {
      out += c;
      if (c === '\\') { out += text[i + 1] ?? ''; i++; continue; }
      if (c === quote) quote = null;
      continue;
    }
    if (c === '"' || c === "'") { quote = c; out += c; continue; }
    if (c === ',') {
      let j = i + 1;
      while (j < text.length && /\s/.test(text[j])) j++;
      if (text[j] === '}' || text[j] === ']') continue; // drop trailing comma
    }
    out += c;
  }
  return out;
}

export function parseJson5(text) {
  const cleaned = stripTrailingCommas(quoteBareKeys(stripComments(text)));
  try {
    return JSON.parse(cleaned);
  } catch {
    const doubleQuoted = cleaned.replace(/'((?:[^'\\]|\\.)*)'/g, (_, s) => '"' + s.replace(/"/g, '\\"') + '"');
    return JSON.parse(doubleQuoted);
  }
}
