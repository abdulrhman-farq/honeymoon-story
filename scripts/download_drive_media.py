#!/usr/bin/env python3
"""
Fast Google Drive media downloader.

Strategy: download each subfolder in one gdown call (--folder --continue)
instead of file-by-file requests. Much faster and avoids rate limits.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path("/workspace/media")
FOLDER_ID = "1OkFMZtF3dJE8xOehDp4avaHJZpJ-rEnM"
DRIVE_URL = f"https://drive.google.com/drive/folders/{FOLDER_ID}"

# Subfolders inside the main Drive folder
SUBFOLDERS = [
    ("1kIjnptCcfXCPa38WT03Tfzs3ONbBP7yP", "الفديو"),
    ("1eHUjI3DtY8dx9dGTPBhuh4m_Nu0xDPk_", "صور"),
    ("1JtfGvBQcECft-ay5P_ag5k0JCzn4MuHz", "فديو2"),
]


def count_media() -> int:
    exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov"}
    return sum(1 for f in OUTPUT_DIR.rglob("*") if f.is_file() and f.suffix.lower() in exts)


def download_subfolder(folder_id: str, name: str) -> bool:
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    dest = OUTPUT_DIR / name
    dest.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Downloading: {name} ({folder_id}) ===", flush=True)
    result = subprocess.run(
        ["gdown", "--folder", "--continue", url, "-O", str(dest)],
        text=True,
    )
    return result.returncode == 0


def main() -> int:
    before = count_media()
    print(f"Media files before: {before}")

    for folder_id, name in SUBFOLDERS:
        if not download_subfolder(folder_id, name):
            print(f"Warning: {name} had errors (may be partial)", flush=True)

    after = count_media()
    print(f"\nMedia files after: {after} (+{after - before})")
    print(f"Expected total: 1520")
    return 0 if after >= 1520 else 1


if __name__ == "__main__":
    sys.exit(main())
