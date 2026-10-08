#!/usr/bin/env python3
"""Write an OpenCode config that enables VibeWise for a directory.

Usage:
    python3 init.py [directory]        # enable for that project (default: cwd)
    python3 init.py --global           # enable for every project
    python3 init.py . --dry-run        # print the result without writing
    python3 init.py . --force          # overwrite an existing config file

Paths are derived from this file's location, so the same clone works anywhere.
The plugin and skills are referenced by absolute path; the target project keeps
its notes in <directory>/.vibe-wise/. Run @vibe-wise-learn there to onboard.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Resolve the repo from this script, not from the caller's working directory.
REPO = Path(__file__).resolve().parent
SKILLS = (REPO / "skills").as_posix()
PLUGIN = (REPO / "plugins" / "vibe-wise").as_posix()

COMMANDS = {
    "vibe-wise-learn": {
        "description": "Activate or resume VibeWise learning mode",
        "template": (
            "Load the `vibe-wise-learn` skill (skill id `vibe-wise-learn`) with the "
            "skill tool and follow it as the active protocol for this project. Then "
            "continue with my request.\n\n$ARGUMENTS"
        ),
    },
    "vibe-wise-reset": {
        "description": "Back up VibeWise learning notes and restart onboarding",
        "template": (
            "Load the `vibe-wise-reset` skill (skill id `vibe-wise-reset`) with the "
            "skill tool and follow it exactly to reset this project's learning notes."
            "\n\n$ARGUMENTS"
        ),
    },
}


def enable(config):
    """Add the VibeWise entries to a config mapping, keeping existing entries."""
    config.setdefault("$schema", "https://opencode.ai/config.json")
    # Use lists for skills/plugins so an existing entry isn't dropped.
    for key, value in (("skills", SKILLS), ("plugins", PLUGIN)):
        entries = config.setdefault(key, [])
        if not isinstance(entries, list):
            raise ValueError('existing "%s" is not a list; merge by hand' % key)
        if value not in entries:
            entries.append(value)
    commands = config.setdefault("commands", {})
    if not isinstance(commands, dict):
        raise ValueError('existing "commands" is not an object; merge by hand')
    # A command the user already defined with the same name wins.
    for name, spec in COMMANDS.items():
        commands.setdefault(name, spec)
    return config


def load(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(directory):
    return directory / ".opencode" / "opencode.json"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "directory", nargs="?", default=None,
        help="project directory to enable (default: current directory)",
    )
    parser.add_argument(
        "--global", dest="global_config", action="store_true",
        help="write to the OpenCode config directory instead of a project",
    )
    parser.add_argument("--force", action="store_true", help="overwrite an existing config file")
    parser.add_argument("--dry-run", action="store_true", help="print the result without writing")
    args = parser.parse_args(argv)

    if args.global_config and args.directory:
        parser.error("pass either a directory or --global, not both")

    project = None
    if args.global_config:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "opencode"
        target = base / "opencode.json"
    else:
        project = Path(args.directory or Path.cwd()).resolve()
        if not project.is_dir():
            print("error: %s is not a directory" % project, file=sys.stderr)
            return 2
        target = config_path(project)

    try:
        existing = {} if args.force else load(target)
    except json.JSONDecodeError as error:
        print(
            "error: %s is not valid JSON (%s). Merge the entries by hand, or pass "
            "--force to overwrite it." % (target, error),
            file=sys.stderr,
        )
        return 1

    try:
        result = enable(existing)
    except ValueError as error:
        print("error: %s" % error, file=sys.stderr)
        return 1

    text = json.dumps(result, indent=2) + "\n"
    if args.dry_run:
        print(text, end="")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print("wrote %s" % target)

    # Without a .git boundary the plugin's state lookup can walk into a parent.
    if project is not None and not (project / ".git").exists():
        print(
            "warning: %s has no .git; run `git init` there so VibeWise notes stay "
            "scoped to this project." % project
        )
    print("Run OpenCode in that project directory, then use @vibe-wise-learn (or /vibe-wise-learn).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
