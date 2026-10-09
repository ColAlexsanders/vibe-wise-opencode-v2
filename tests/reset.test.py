"""Functional test for the reset helper.

Run: python3 tests/reset.test.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
RESET = os.path.join(HERE, "..", "skills", "vibe-wise-reset", "reset.py")

# Import the helper directly to check its return type matches the plugin's.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "skills", "vibe-wise-reset")))
import reset  # noqa: E402  (import after sys.path setup)


def test_state_directory_type():
    project = tempfile.mkdtemp(prefix="vw-type-")
    empty = tempfile.mkdtemp(prefix="vw-type-empty-")
    try:
        assert reset.state_directory(empty) is None, "missing state must be None"
        os.makedirs(os.path.join(project, ".vibe-wise"))
        got = reset.state_directory(project)
        assert isinstance(got, str), "state_directory must return str, not Path"
        assert got == os.path.join(project, ".vibe-wise"), got
    finally:
        shutil.rmtree(project)
        shutil.rmtree(empty)


def run(*args):
    proc = subprocess.run([sys.executable, RESET, *args], capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout)


def main():
    test_state_directory_type()
    root = tempfile.mkdtemp(prefix="vw-reset-")
    try:
        os.makedirs(os.path.join(root, ".vibe-wise"))
        profile = os.path.join(root, ".vibe-wise", "profile.md")
        with open(profile, "w", encoding="utf-8") as fh:
            fh.write("# Learner Profile\n\nLearning mode: active\nOnboarding: complete\n")
        with open(os.path.join(root, ".vibe-wise", "progress.md"), "w", encoding="utf-8") as fh:
            fh.write("# Learning Progress\n\nDid a thing.\n")

        # Scoped to the given directory: notes live directly under it.
        code, preview = run("--cwd", root)
        assert code == 0, preview
        assert preview["status"] == "preview", preview
        assert preview["state"] == os.path.join(root, ".vibe-wise"), preview
        assert "profile.md" in preview["files"], preview
        assert os.path.exists(profile), "preview must not modify notes"

        # A subdirectory is not the project directory, so it has no notes.
        sub = os.path.join(root, "src")
        os.makedirs(sub)
        code, none = run("--cwd", sub)
        assert none["status"] == "no_notes", none

        # Confirming with the snapshot token resets and backs up.
        code, done = run("--cwd", root, "--confirm", preview["confirmation"])
        assert code == 0, done
        assert done["status"] == "reset", done
        assert os.path.isdir(done["backup"]), done
        with open(profile, encoding="utf-8") as fh:
            assert "Onboarding: incomplete" in fh.read(), "profile was not reset"

        # A stale confirmation is rejected.
        code, stale = run("--cwd", root, "--confirm", preview["confirmation"])
        assert code != 0 or stale["status"] == "no_notes", stale

        # A directory with no notes reports nothing to reset.
        empty = tempfile.mkdtemp(prefix="vw-empty-")
        try:
            code, none = run("--cwd", empty)
            assert none["status"] == "no_notes", none
        finally:
            shutil.rmtree(empty)

        print("reset tests OK")
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    main()
