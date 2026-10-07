// Functional test for the VibeWise OpenCode plugin restore logic.
// Run: node tests/plugin.test.mjs   (Node 22.6+ with type stripping)
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import plugin, { stateDirectory } from "../plugins/vibe-wise/index.ts";

const mk = () => fs.mkdtempSync(path.join(os.tmpdir(), "vw-"));

// state lookup finds the nearest .vibe-wise and does not cross a .git boundary
const root = mk();
fs.mkdirSync(path.join(root, ".vibe-wise"));
fs.writeFileSync(path.join(root, ".git"), "");
const profile = path.join(root, ".vibe-wise", "profile.md");
fs.writeFileSync(profile, "# Learner Profile\n\nLearning mode: active\nOnboarding: complete\n");
const nested = path.join(root, "src", "deep");
fs.mkdirSync(nested, { recursive: true });
assert.equal(stateDirectory(nested), path.join(root, ".vibe-wise"), "finds state from a subdir");

const bounded = mk();
fs.mkdirSync(path.join(bounded, ".git"), { recursive: true });
fs.mkdirSync(path.join(bounded, "sub"), { recursive: true });
assert.equal(stateDirectory(path.join(bounded, "sub")), null, "stops at a .git boundary");

// Drive the registered context hook with a fake plugin context.
const capture = async (dir, { parentID } = {}) => {
	let cb;
	await plugin.setup({
		location: { directory: dir },
		session: {
			hook: async (_name, fn) => {
				cb = fn;
				return {};
			},
			get: async ({ sessionID }) => (parentID ? { id: sessionID, parentID } : { id: sessionID }),
		},
	});
	const event = { sessionID: "ses_main", system: [] };
	await cb(event);
	return event.system;
};

// Active profile injects the guides inline, not as paths to read from disk.
let out = await capture(root);
assert.equal(out.length, 1, "active profile injects once per call");
assert.match(out[0].text, /included in this message inside <vibe-wise-guide>/, "states guides are inlined");
assert.match(out[0].text, /<vibe-wise-guide file="SKILL.md">/, "inlines SKILL.md");
assert.match(out[0].text, /<vibe-wise-guide file="behavior.md">/, "inlines behavior.md");
assert.match(out[0].text, /<vibe-wise-guide file="state-templates.md">/, "inlines state-templates.md");
assert.ok(!out[0].text.includes('<vibe-wise-guide file="onboarding.md">'), "omits onboarding when complete");
assert.match(out[0].text, /AskUserQuestion is the `question` tool/, "translates Claude tool names");
assert.ok(out[0].text.includes(path.join(root, ".vibe-wise")), "names the resolved state directory");

// Incomplete onboarding adds the onboarding guide.
fs.writeFileSync(profile, "# Learner Profile\n\nLearning mode: active\nOnboarding: incomplete\n");
out = await capture(root);
assert.match(out[0].text, /<vibe-wise-guide file="onboarding.md">/, "includes onboarding when incomplete");

// Paused profile injects nothing.
fs.writeFileSync(profile, "# Learner Profile\n\nLearning mode: paused\n");
out = await capture(root);
assert.equal(out.length, 0, "paused profile injects nothing");

// Child/subagent sessions inject nothing.
fs.writeFileSync(profile, "# Learner Profile\n\nLearning mode: active\nOnboarding: complete\n");
out = await capture(root, { parentID: "ses_parent" });
assert.equal(out.length, 0, "child session injects nothing");

// No state directory injects nothing.
out = await capture(bounded);
assert.equal(out.length, 0, "missing state injects nothing");

console.log("plugin tests OK");
