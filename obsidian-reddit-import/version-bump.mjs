import { readFileSync, writeFileSync } from "fs";

const targetVersion = process.env.npm_new_version || process.argv[2];

if (!targetVersion) {
	console.error("❌ Version not specified");
	process.exit(1);
}

// Read current manifest
let manifest = JSON.parse(readFileSync("manifest.json", "utf8"));
const { minAppVersion } = manifest;
manifest.version = targetVersion;

// Write updated manifest
writeFileSync("manifest.json", JSON.stringify(manifest, null, "\t"));

// Update versions.json
let versions = JSON.parse(readFileSync("versions.json", "utf8"));
versions[targetVersion] = minAppVersion;
writeFileSync("versions.json", JSON.stringify(versions, null, "\t"));

console.log(`✅ Updated version to ${targetVersion}`);