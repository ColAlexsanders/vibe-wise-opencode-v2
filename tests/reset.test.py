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


def run(*args):
    proc = subprocess.run(
        [sys.executable, RESET, *args], capture_output=True, text=True
    )
    return proc.returncode, json.loads(proc.stdout)


def main():
    root = tempfile.mkdtemp(prefix="vw-reset-")
    try:
        os.makedirs(os.path.join(root, ".vibe-wise"))
        os.makedirs(os.path.join(root, "src"))
        open(os.path.join(root, ".git"), "w").close()
        profile = os.path.join(root, ".vibe-wise", "profile.md")
        with open(profile, "w", encoding="utf-8") as fh:
            fh.write("# Learner Profile\n\nLearning mode: active\nOnboarding: complete\n")
        with open(os.path.join(root, ".vibe-wise", "progress.md"), "w", encoding="utf-8") as fh:
            fh.write("# Learning Progress\n\nDid a thing.\n")

        # Preview from a subdirectory resolves the project state; no writes yet.
        code, preview = run("--cwd", os.path.join(root, "src"))
        assert code == 0, preview
        assert preview["status"] == "preview", preview
        assert preview["state"] == os.path.join(root, ".vibe-wise"), preview
        assert "profile.md" in preview["files"], preview
        assert os.path.exists(profile), "preview must not modify notes"

        # Confirming with the snapshot token resets and backs up.
        code, done = run("--cwd", os.path.join(root, "src"), "--confirm", preview["confirmation"])
        assert code == 0, done
        assert done["status"] == "reset", done
        assert os.path.isdir(done["backup"]), done
        with open(profile, encoding="utf-8") as fh:
            assert "Onboarding: incomplete" in fh.read(), "profile was not reset"

        # A stale confirmation is rejected.
        code, stale = run("--cwd", os.path.join(root, "src"), "--confirm", preview["confirmation"])
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
