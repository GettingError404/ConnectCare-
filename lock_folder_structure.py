import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
LOCK_FILE = REPO_ROOT / "FOLDER_STRUCTURE.lock.json"


def fail(msg: str) -> None:
    print(f"[folder-structure-lock] ERROR: {msg}")
    sys.exit(1)


def main() -> None:
    if not LOCK_FILE.exists():
        fail(f"Missing lock file: {LOCK_FILE}")

    lock = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    allowed = set(lock.get("allowedTopLevelFolders", []))
    if not allowed:
        fail("Lock file contains no allowedTopLevelFolders")

    # Consider current top-level directories only.
    present = {
        p.name
        for p in REPO_ROOT.iterdir()
        if p.is_dir() and p.name not in {".git", "__pycache__"}
    }




    missing = sorted(allowed - present)

    extra = sorted(present - allowed)

    if missing or extra:
        if missing:
            print("[folder-structure-lock] Missing top-level folders:")
            for m in missing:
                print(f"  - {m}")
        if extra:
            print("[folder-structure-lock] Unexpected extra top-level folders:")
            for e in extra:
                print(f"  - {e}")
        fail("Folder structure does not match the lock contract")

    print("[folder-structure-lock] OK: Top-level folder structure matches the lock contract")


if __name__ == "__main__":
    main()

