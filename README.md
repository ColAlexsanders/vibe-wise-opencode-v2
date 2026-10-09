# VibeWise for OpenCode
An [OpenCode](https://opencode.ai) port of [nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise), a Claude Code plugin by Noah Kim (https://www.youtube.com/watch?v=GckkaKEQ3vo)

All credit for the VibeWise learning method and content goes to the original author. This repository only adapts the packaging and integration layer for OpenCode, specifically adding support for version 2's API

## What is here
| Original (Claude Code) | This port (OpenCode) |
| --- | --- |
| `skills/learn/*` | `skills/vibe-wise-learn/` (same idea; OpenCode tool names) |
| `skills/reset/*` + Python helper | `skills/vibe-wise-reset/` (self-contained `reset.py`) |
| `hooks/session_start.py` + `hooks/hooks.json` (SessionStart, compact) | `plugins/vibe-wise/index.ts` — a session `context` hook that restores learning context |
| `.claude-plugin/marketplace.json` (OG repo) | paths wired through `opencode.json` |
| `/vibe-wise:learn`, `/vibe-wise:reset` | `@vibe-wise-learn` / `@vibe-wise-reset`, or `/vibe-wise-learn` commands |

Notes live in `.vibe-wise/` (legacy `.sensible-vibes/` is read in place), so you can move between the Claude Code plugin and this port without losing learning history.

## Other OpenCode ports

Two other VibeWise ports for OpenCode already exist: [simonaden/vibe-wise-opencode](https://github.com/simonaden/vibe-wise-opencode) and[flynt-3650/opencode-vibe-wise](https://github.com/flynt-3650/opencode-vibe-wise). Both were built for the OpenCode V1 plugin API (`@opencode-ai/plugin`, a `server()` export, and `experimental.*` hooks), but none of those V1 hook names or the V1 package appear in the V2 runtime.


## File-by-file changes

Every change this port makes against upstream [nykooi1/vibe-wise](https://github.com/nykooi1/vibe-wise) and the v1 opencode plugins:

| File | What changed | Why |
| --- | --- | --- |
| `plugins/vibe-wise/index.ts` | Full rewrite: `async (ctx)=>({hooks})` → `{id,setup}`; `experimental.chat.system.transform`/`.messages.transform` → `session.hook("context")`; `experimental.session.compacting` → `session.hook("compaction")`; `(input,output)` → `(event)`; string system parts → `{type,text}`; `directory` → `ctx.location.directory`; `client.session.get({path:{id}})` → `ctx.session.get({sessionID})` | The whole V1→V2 plugin API |
| `skills/vibe-wise-learn/SKILL.md` | Added `metadata: opencode/autoinvoke: false`; `Read`/`Glob`/`Bash` → `read`/`glob`/`shell`; replaced the `find` shell check with the glob tool | OpenCode reads its own `autoinvoke` field (it ignores `disable-model-invocation`), and its built-in tools are lowercase |
| `skills/vibe-wise-learn/behavior.md` | Rewrote the line that named Claude Code's `AskUserQuestion` picker so it points at OpenCode's `question` tool instead, and restated the plain-text fallback that applies when no picker is available. | OpenCode has no `AskUserQuestion`, so the original wording instructed the agent to call a tool that doesn't exist; the fallback keeps the flow working when a picker can't be shown. |
| `skills/vibe-wise-learn/onboarding.md` | Swapped the same picker for OpenCode's `question` tool and corrected its option details: `multiSelect: false` → `multiple: false`, and the header limit widened from 12 to 30 characters. | OpenCode's `question` tool uses different field names and permits longer headers than Claude Code's, so the old parameter values were both invalid and unnecessarily restrictive. |
| `skills/vibe-wise-learn/state-templates.md` | Changed the note about the two profile status lines to attribute them to "the VibeWise restore plugin" rather than "the restoration hook". | This port has no separate hook process — the plugin reads `Learning mode:`/`Onboarding:` directly — so the old wording pointed at infrastructure that doesn't exist here. |
| `skills/vibe-wise-reset/SKILL.md` | Added the `opencode/autoinvoke` field; `learn` → `vibe-wise-learn`; interactive picker → `question` tool; renamed the sibling path; dropped `${CLAUDE_PLUGIN_ROOT}` (via the pi base) | OpenCode field + rename/naming |
| `skills/vibe-wise-reset/reset.py` | Inlined `state_directory` (dropped the `from session_start import state_directory`) and updated the docstring to reference `plugins/vibe-wise.ts` | Port structure — not a V1→V2 change |
| `init.py` | New helper that writes the project-local (or `--global`) config, merging rather than overwriting; `--remove` strips only the entries it added and `--delete-notes` also removes `.vibe-wise/` | Avoids pasting the `opencode.json` block by hand, and lets cleanup leave other project settings untouched |
| `tests/` | New: `plugin.test.mjs`, `reset.test.py`, `init.test.py` | Cover restore gating, the reset flow, and the init helper |

## Requirements
- OpenCode V2
- Python 3 (used only by the `reset` skill; no extra packages)

## Install
The skills and plugin live outside OpenCode's config directory, so point `opencode.json` at them. Replace `<repo>` with the **absolute** path to your clone.

Easiest is the bundled helper, which writes the config for you (paths come from the helper's own location, and it merges rather than overwrites):

```sh
python3 <repo>/init.py /path/to/project   # one project only
python3 <repo>/init.py --global           # every project
python3 <repo>/init.py . --dry-run        # preview

python3 <repo>/init.py /path/to/project --remove                  # remove the entries again
python3 <repo>/init.py /path/to/project --remove --delete-notes   # also delete .vibe-wise/

python3 <repo>/init.py --help             # show all options
```

Or add the entries by hand:

- **Everywhere:** add these entries to `~/.config/opencode/opencode.json`.
- **One project only:** add the same entries to that project's
  `.opencode/opencode.json` instead. Other projects and windows are then
  unaffected.

I recommend making the init.py call an alias

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "skills": ["<repo>/skills"],
  "plugins": ["<repo>/plugins/vibe-wise"],
  "commands": {
    "vibe-wise-learn": {
      "description": "Activate or resume VibeWise learning mode",
      "template": "Load the `vibe-wise-learn` skill (skill id `vibe-wise-learn`) with the skill tool and follow it as the active protocol for this project. Then continue with my request.\n\n$ARGUMENTS"
    },
    "vibe-wise-reset": {
      "description": "Back up VibeWise learning notes and restart onboarding",
      "template": "Load the `vibe-wise-reset` skill (skill id `vibe-wise-reset`) with the skill tool and follow it exactly to reset this project's learning notes.\n\n$ARGUMENTS"
    }
  }
}
```

Restart OpenCode (or let it reload config) after editing.

## Usage

Start in your project with `@vibe-wise-learn` (or `/vibe-wise-learn`). Setup asks one question at a time; pick **Use defaults** to skip preference setup. Then ask the agent to build something. Starting fresh or joining an unfamiliar repository both work — for an existing repository, the agent first inspects the code and sketches a small system map.

Once learning is active (a non-empty `.vibe-wise/profile.md` without `Learning mode: paused`), the plugin silently re-injects the restoration instructions on every request. You can confirm it is active by asking the agent what stage your learning is at.

Reset learning with `@vibe-wise-reset` (or `/vibe-wise-reset`). It previews what will change, asks for explicit confirmation, backs up your notes under `.vibe-wise/backups/`, and restarts onboarding. Source code is never touched.

Pause anytime by typing "Pause learning" into the chat; resume with `@vibe-wise-learn`.

## How the restore works

OpenCode's session `context` hook runs for every agent-loop request, and edits to its `system` field apply to that outgoing request only. Whenever the project has an active profile, the plugin injects the Learn guides plus a short instruction to restore the learner's profile, map, and pending decisions. If the project directory has an `AGENTS.md`, its contents are included too, so project rules travel with the learning guide.

The guides are inlined rather than read from disk, so the injected instructions always match the installed plugin and cannot be shadowed by another copy (for example the repo plus a copy under `.opencode/`). Inlining also saves the agent from re-reading guide files, and avoids external-directory approval for those reads when the plugin is configured as a global install. A short "OpenCode notes"  block translates the Claude Code tool and ommand names the guides use. Child  and subagent sessions are skipped, since learning checkpoints belong to the main session.

This differs from the Claude Code hook, which injected `additionalContext` once at session start and again after compaction. The practical effect is the same or stronger: the guardrails are present at session start, on resume, and after compaction, because the hook rebuilds each request and compaction cannot drop the instruction. The cost is the guides in system context on every request while learning is active.

The activation check and state-directory lookup are scoped to the project directory OpenCode reports: `.vibe-wise/` (or legacy `.sensible-vibes/`) directly under it, never following symlinks, and treating `Learning mode: paused` as inactive. No `.git` boundary is required. If a session was moved to a different directory, the session's own location is used instead, and the mismatch is written to the log.

## Auto-invocation

Both skills set `disable-model-invocation: true` (for Claude Code) and `metadata.opencode/autoinvoke: false` (for OpenCode). OpenCode 2 ignores the Claude-style field, so without the `metadata` key the skills stay advertised and the agent can start learning mode on its own. The `metadata` key keeps them hidden until you invoke `@vibe-wise-learn` or `/vibe-wise-learn` explicitly.

## Development

```sh
node tests/plugin.test.mjs      # plugin state lookup + restore gating (Node 22.6+)
python3 tests/reset.test.py     # reset helper preview / confirm / backup flow
python3 tests/init.test.py      # init helper merge / idempotency / dry-run
```

The plugin is a plain V2 default export (`id` + `setup`) and deliberately does not import `@opencode/plugin`, so it needs no `node_modules` of its own. OpenCode loads `plugins/vibe-wise/index.ts` from the directory named in the `plugins` config entry.

## License

[MIT](LICENSE). Original work Copyright (c) 2026 Noah Kim. Port adaptations
Copyright (c) 2026, under the same license.
