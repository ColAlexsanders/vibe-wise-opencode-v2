#!/usr/bin/env python3
"""Write or remove an OpenCode config that enables VibeWise for a directory.

Run `python3 init.py --help` for the full option list. In short:

    python3 init.py [directory]                # enable for that project (default: cwd)
    python3 init.py --global                   # enable for every project
    python3 init.py . --remove                 # remove the VibeWise entries again
    python3 init.py . --remove --delete-notes  # ...and delete .vibe-wise/ notes

Removal touches only the entries this helper adds -- the skills/plugins paths and
the two commands -- and leaves every other setting in the file alone. Paths are
derived from this file's location, so the same clone works anywhere.
"""

import json
import os
import shutil
import sys
import types
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

# Only these flags are accepted; anything else (including an abbreviation such as
# --rem) is an error, so a typo can never select --remove by accident.
FLAGS = {
    "--global": "global_config",
    "--remove": "remove",
    "--delete-notes": "delete_notes",
    "--force": "force",
    "--dry-run": "dry_run",
}
HELP_FLAGS = ("-h", "--help")

HELP = """\
Write or remove an OpenCode config that enables VibeWise for a directory.

Usage:
  init.py [directory]                      enable for that project (default: cwd)
  init.py --global                         enable for every project
  init.py [directory] --remove             remove the VibeWise entries again
  init.py [directory] --remove --delete-notes
                                           also delete the project's .vibe-wise/ notes
  init.py [directory] --dry-run            print what would happen without writing
  init.py --help                           show this help

Options:
  --global          use the OpenCode config directory instead of a project
  --remove          remove the VibeWise entries instead of adding them
  --delete-notes    with --remove, also delete the project's .vibe-wise/ notes
  --force           overwrite an existing config file (enable only)
  --dry-run         print what would happen without writing
  -h, --help        show this help
"""


class UsageError(Exception):
    pass


def parse_args(argv):
    """Validate every argument against the known flags and options."""
    options = {"global_config": False, "remove": False, "delete_notes": False, "force": False, "dry_run": False}
    directory = None
    for arg in argv:
        if arg in HELP_FLAGS:
            return None  # caller prints help and exits
        if arg in FLAGS:
            options[FLAGS[arg]] = True
        elif arg.startswith("-"):
            raise UsageError("unrecognized argument: %s" % arg)
        elif directory is None:
            directory = arg
        else:
            raise UsageError("unexpected extra argument: %s" % arg)
    return types.SimpleNamespace(directory=directory, **options)


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


def disable(config):
    """Remove the VibeWise entries this helper adds, keeping everything else."""
    removed = False
    for key, value in (("skills", SKILLS), ("plugins", PLUGIN)):
        entries = config.get(key)
        if isinstance(entries, list) and value in entries:
            entries.remove(value)
            removed = True
            if not entries:
                del config[key]
    commands = config.get("commands")
    if isinstance(commands, dict):
        for name in COMMANDS:
            if name in commands:
                del commands[name]
                removed = True
        if not commands:
            del config["commands"]
    # If only our own schema line remains, the helper created the whole file.
    if removed and set(config) <= {"$schema"}:
        config.clear()
    return config, removed


def load(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(directory):
    return directory / ".opencode" / "opencode.json"


def run_remove(args, target, notes, existing):
    result, removed = disable(existing)
    notes_exist = notes is not None and notes.exists()

    if args.dry_run:
        if not removed:
            print("no VibeWise entries in %s" % target)
        elif result:
            print("would update %s:" % target)
            print(json.dumps(result, indent=2))
        else:
            print("would delete %s" % target)
        if args.delete_notes:
            print("would delete %s" % notes if notes_exist else "no notes at %s" % notes)
        return 0

    if not removed:
        print("no VibeWise entries in %s" % target)
    elif result:
        target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("updated %s" % target)
    else:
        target.unlink()
        print("deleted %s" % target)
        # Drop the .opencode directory too when nothing else lives there.
        if target.parent.exists() and not any(target.parent.iterdir()):
            target.parent.rmdir()
            print("deleted %s" % target.parent)

    if args.delete_notes:
        if notes_exist:
            shutil.rmtree(notes)
            print("deleted %s" % notes)
        else:
            print("no notes at %s" % notes)
    elif notes_exist:
        print("left notes in place at %s; pass --delete-notes to remove them" % notes)
    print("Reload OpenCode (or restart the service) to drop the plugin.")
    return 0


def usage_error(message):
    print("error: %s" % message, file=sys.stderr)
    print(HELP, end="", file=sys.stderr)
    return 2


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parse_args(argv)
    except UsageError as error:
        return usage_error(str(error))

    if args is None:  # --help
        print(HELP, end="")
        return 0

    if args.global_config and args.directory:
        return usage_error("pass either a directory or --global, not both")
    if args.delete_notes and not args.remove:
        return usage_error("--delete-notes requires --remove")
    if args.delete_notes and args.global_config:
        return usage_error("--delete-notes applies to a project directory, not --global")
    if args.force and args.remove:
        return usage_error("--force only applies when writing; omit it with --remove")

    project = None
    notes = None
    if args.global_config:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "opencode"
        target = base / "opencode.json"
    else:
        project = Path(args.directory or Path.cwd()).resolve()
        if not project.is_dir():
            print("error: %s is not a directory" % project, file=sys.stderr)
            return 2
        target = config_path(project)
        notes = project / ".vibe-wise"

    try:
        existing = {} if (args.force and not args.remove) else load(target)
    except json.JSONDecodeError as error:
        print(
            "error: %s is not valid JSON (%s). Merge the entries by hand, or pass "
            "--force to overwrite it." % (target, error),
            file=sys.stderr,
        )
        return 1

    if args.remove:
        try:
            return run_remove(args, target, notes, existing)
        except ValueError as error:
            print("error: %s" % error, file=sys.stderr)
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

    print("Run OpenCode in that project directory, then use @vibe-wise-learn (or /vibe-wise-learn).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
