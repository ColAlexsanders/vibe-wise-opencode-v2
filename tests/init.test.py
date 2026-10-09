"""Functional test for the init helper.

Run: python3 tests/init.test.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
INIT = os.path.join(REPO, "init.py")
SKILLS = os.path.join(REPO, "skills").replace(os.sep, "/")
PLUGIN = os.path.join(REPO, "plugins", "vibe-wise").replace(os.sep, "/")


def run(*args):
    return subprocess.run([sys.executable, INIT, *args], capture_output=True, text=True)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def main():
    project = tempfile.mkdtemp(prefix="vw-init-")
    try:
        config = os.path.join(project, ".opencode", "opencode.json")

        # Fresh project: writes a config that points at this clone.
        proc = run(project)
        assert proc.returncode == 0, proc.stderr
        data = read(config)
        assert SKILLS in data["skills"], data
        assert PLUGIN in data["plugins"], data
        assert set(data["commands"]) == {"vibe-wise-learn", "vibe-wise-reset"}, data

        # Idempotent: running again does not duplicate entries.
        run(project)
        data = read(config)
        assert data["skills"].count(SKILLS) == 1, data
        assert data["plugins"].count(PLUGIN) == 1, data

        # Merge: keeps unrelated entries and an existing command of the same name.
        write(config, {
            "$schema": "https://opencode.ai/config.json",
            "skills": ["/some/other/skill"],
            "commands": {"vibe-wise-learn": {"template": "mine"}},
        })
        run(project)
        data = read(config)
        assert data["skills"] == ["/some/other/skill", SKILLS], data
        assert data["commands"]["vibe-wise-learn"] == {"template": "mine"}, data
        assert "vibe-wise-reset" in data["commands"], data

        # --dry-run must not write.
        os.remove(config)
        proc = run(project, "--dry-run")
        assert proc.returncode == 0, proc.stderr
        assert SKILLS in proc.stdout, proc.stdout
        assert not os.path.exists(config), "dry-run wrote a file"

        # Invalid JSON: refuse unless --force.
        os.makedirs(os.path.dirname(config), exist_ok=True)
        with open(config, "w", encoding="utf-8") as fh:
            fh.write("{ not json // comment\n")
        proc = run(project)
        assert proc.returncode == 1, proc.stdout
        assert "not valid JSON" in proc.stderr, proc.stderr
        run(project, "--force")
        assert SKILLS in read(config)["skills"]

        # A missing directory is an error, not a crash.
        proc = run(os.path.join(project, "does-not-exist"))
        assert proc.returncode == 2, proc.stdout

        # Abbreviated flags are rejected, so --rem can't select --remove.
        proc = run(project, "--rem")
        assert proc.returncode == 2, proc.stdout

        # A second positional argument is rejected too.
        proc = run(project, project)
        assert proc.returncode == 2, proc.stdout

        # --help / -h print usage and exit 0.
        for flag in ("--help", "-h"):
            proc = run(flag)
            assert proc.returncode == 0, proc.stdout
            assert "Usage:" in proc.stdout, proc.stdout

        # --remove strips the helper's entries and leaves other settings intact.
        keep = {"template": "keep me"}
        write(config, {
            "$schema": "https://opencode.ai/config.json",
            "model": "openai/local-model",
            "skills": ["/other/skills", SKILLS],
            "plugins": [PLUGIN],
            "commands": {"vibe-wise-learn": {"template": "mine"}, "my-command": keep},
        })
        proc = run(project, "--remove")
        assert proc.returncode == 0, proc.stderr
        data = read(config)
        assert data["skills"] == ["/other/skills"], data
        assert "plugins" not in data, data
        assert data["commands"] == {"my-command": keep}, data
        assert data["model"] == "openai/local-model", data

        # --remove on a helper-only config deletes the file and the now-empty dir.
        os.remove(config)
        run(project)
        assert os.path.exists(config)
        proc = run(project, "--remove")
        assert proc.returncode == 0, proc.stderr
        assert not os.path.exists(config), "config not deleted"
        assert not os.path.exists(os.path.join(project, ".opencode")), ".opencode not deleted"

        # --dry-run leaves the config and notes untouched.
        notes = os.path.join(project, ".vibe-wise")
        os.makedirs(notes, exist_ok=True)
        run(project)
        proc = run(project, "--remove", "--dry-run")
        assert proc.returncode == 0, proc.stderr
        assert os.path.exists(config) and os.path.isdir(notes), "dry-run changed something"

        # --delete-notes removes the notes along with the config entries.
        proc = run(project, "--remove", "--delete-notes")
        assert proc.returncode == 0, proc.stderr
        assert not os.path.exists(notes), "notes not deleted"

        # --delete-notes without --remove is rejected.
        proc = run(project, "--delete-notes")
        assert proc.returncode == 2, proc.stdout

        print("init tests OK")
    finally:
        shutil.rmtree(project)


if __name__ == "__main__":
    main()
