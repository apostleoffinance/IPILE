#!/usr/bin/env node
const { spawnSync } = require("node:child_process");
const { readdirSync } = require("node:fs");
const { join } = require("node:path");

const root = join(__dirname);
const files = readdirSync(root)
  .filter((name) => name.endsWith(".test.ts"))
  .sort();

if (!files.length) {
  console.error("No *.test.ts files found in lib/");
  process.exit(1);
}

let failed = 0;
for (const file of files) {
  const result = spawnSync(
    process.execPath,
    ["--import", "tsx", join(root, file)],
    { stdio: "inherit", cwd: join(root, "..") },
  );
  if (result.status !== 0) failed += 1;
}

if (failed) {
  console.error(`\n${failed} test file(s) failed`);
  process.exit(1);
}

console.log(`\nAll ${files.length} frontend test files passed`);
