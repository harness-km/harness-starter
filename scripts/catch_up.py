"""Bring your repository to a published weekly checkpoint without losing your work.

    make catch-up WEEK=07

1. Commits everything you have (even unfinished work) and saves it on a backup branch
   named my-work-<date>-<time>. Nothing you wrote is lost: `git checkout <that branch>` gets it back.
2. Downloads the checkpoint for that week from the course's starter repository.
3. Copies in ONLY the folders that week's checkpoint lists (see checkpoints.json in the checkpoint).
4. Runs `make test`.

WEEK=00 is a rehearsal: it creates the backup branch and changes nothing else.
Options: --source DIR uses a local copy of the checkpoint instead of downloading (for testing).
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

OWNER = "YOUR-GITHUB-ORG"
REPO = "harness-starter"
ROOT = Path(__file__).resolve().parent.parent


def git(*args: str, check: bool = True) -> str:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and out.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{out.stderr}")
    return out.stdout.strip()


def backup() -> str:
    name = datetime.now().strftime("my-work-%Y%m%d-%H%M%S")
    git("add", "-A")
    if git("status", "--porcelain"):
        git("-c", "user.name=catch-up", "-c", "user.email=catch-up@localhost",
            "commit", "-q", "-m", "catch-up: save my work before copying the checkpoint")
    git("branch", name)
    return name


def fetch_checkpoint(week: str, dest: Path) -> Path:
    url = f"https://codeload.github.com/{OWNER}/{REPO}/tar.gz/refs/tags/checkpoint-{week}"
    print(f"Downloading {url}")
    try:
        data = urllib.request.urlopen(url, timeout=60).read()
    except Exception as e:  # noqa: BLE001
        sys.exit(f"Could not download the week {week} checkpoint ({e}). Is it published yet? Check the course site.")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tar.extractall(dest, filter="data")
    return next(dest.iterdir())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("week", help="two digits, e.g. 07")
    ap.add_argument("--source", help="local checkpoint directory (skips the download)")
    ap.add_argument("--no-test", action="store_true")
    args = ap.parse_args()
    week = f"{int(args.week):02d}"

    branch = backup()
    print(f"Your work is saved on branch '{branch}'.")
    if week == "00":
        print("Rehearsal complete: nothing else was changed. See your branches with: git branch")
        return

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(args.source) if args.source else fetch_checkpoint(week, Path(tmp))
        manifest = json.loads((src / "checkpoints.json").read_text())
        paths = manifest.get(week)
        if not paths:
            sys.exit(f"The checkpoint does not list any folders for week {week}.")
        for rel in paths:
            s, d = src / rel, ROOT / rel
            if not s.exists():
                sys.exit(f"Checkpoint is missing {rel}.")
            if d.exists():
                shutil.rmtree(d) if d.is_dir() else d.unlink()
            d.parent.mkdir(parents=True, exist_ok=True)
            (shutil.copytree if s.is_dir() else shutil.copy2)(s, d)
            print(f"  copied {rel}")

    print(f"Checkpoint {week} copied. Review the changes with `git status`, then commit them.")
    print(f"To compare with your own version: git diff {branch} -- <file>")
    if not args.no_test:
        sys.exit(subprocess.run(["make", "test"], cwd=ROOT).returncode)


if __name__ == "__main__":
    main()
