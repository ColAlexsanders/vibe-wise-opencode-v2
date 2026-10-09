// Functional test for the VibeWise OpenCode plugin restore logic.
// Run: node tests/plugin.test.mjs   (Node 22.6+ with type stripping)
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import plugin, { stateDirectory } from "../plugins/vibe-wise/index.ts";

const mk = () => fs.mkdtempSync(path.join(os.tmpdir(), "vw-"));

// state lookup reads the project directory directly; it does not walk up
const root = mk();
fs.mkdirSync(path.join(root, ".vibe-wise"));
const profile = path.join(root, ".vibe-wise", "profile.md");
fs.writeFileSync(profile, "# Learner Profile\n\nLearning mode: active\nOnboarding: complete\n");
assert.equal(stateDirectory(root), path.join(root, ".vibe-wise"), "reads state in the project dir");

const nested = path.join(root, "src", "deep");
fs.mkdirSync(nested, { recursive: true });
assert.equal(stateDirectory(nested), null, "does not borrow a parent directory's state");

const empty = mk();
assert.equal(stateDirectory(empty), null, "missing state returns null");

// Drive the registered context hook with a fake plugin context.
const capture = async (dir, { parentID, sessionDirectory } = {}) => {
	let cb;
	await plugin.setup({
		location: { directory: dir },
		session: {
			hook: async (_name, fn) => {
				cb = fn;
				return {};
			},
			get: async ({ sessionID }) => {
				const info = { id: sessionID };
				if (parentID) info.parentID = parentID;
				if (sessionDirectory) info.location = { directory: sessionDirectory };
				return info;
			},
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

// No AGENTS.md in the project dir: the project-instructions block is absent.
assert.ok(!out[0].text.includes("<vibe-wise-project-agents"), "omits AGENTS.md when absent");

// With AGENTS.md present, its text is included.
fs.writeFileSync(path.join(root, "AGENTS.md"), "# Project rules\n\nUse tabs, never spaces.\n");
out = await capture(root);
assert.match(out[0].text, /<vibe-wise-project-agents file="AGENTS\.md">/, "includes AGENTS.md when present");
assert.match(out[0].text, /Use tabs, never spaces\./, "includes AGENTS.md contents");

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

// A moved session uses its own directory even when the plugin location differs.
const other = mk();
fs.mkdirSync(path.join(other, ".vibe-wise"));
fs.writeFileSync(path.join(other, ".vibe-wise", "profile.md"), "# P\n\nLearning mode: active\nOnboarding: complete\n");
const elsewhere = mk();
out = await capture(elsewhere, { sessionDirectory: other });
assert.equal(out.length, 1, "uses the session directory when it differs from the plugin location");
assert.ok(out[0].text.includes(path.join(other, ".vibe-wise")), "names the session state directory");

// No state directory injects nothing.
out = await capture(empty);
assert.equal(out.length, 0, "missing state injects nothing");

console.log("plugin tests OK");
