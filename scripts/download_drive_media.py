#!/usr/bin/env python3
"""
Google Drive media downloader — two modes:

1. fast (default): parallel download of MISSING files only (no re-scan)
2. folder:         gdown --folder --continue per subfolder
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path("/workspace/media")
MANIFEST = OUTPUT_DIR / "file_manifest.json"
MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".avi", ".mkv"}

SUBFOLDERS = [
    ("1kIjnptCcfXCPa38WT03Tfzs3ONbBP7yP", "الفديو"),
    ("1eHUjI3DtY8dx9dGTPBhuh4m_Nu0xDPk_", "صور"),
    ("1JtfGvBQcECft-ay5P_ag5k0JCzn4MuHz", "فديو2"),
]


def count_media() -> int:
    return sum(1 for f in OUTPUT_DIR.rglob("*") if f.is_file() and f.suffix.lower() in MEDIA_EXTS)


def missing_entries() -> list[dict]:
    entries = [e for e in json.loads(MANIFEST.read_text()) if Path(e["path"]).suffix.lower() in MEDIA_EXTS]
    return [e for e in entries if not (OUTPUT_DIR / e["path"]).exists()]


def write_jobs(path: Path, entries: list[dict]) -> None:
    lines = [f"{e['url']}\t{OUTPUT_DIR / e['path']}" for e in entries]
    path.write_text("\n".join(lines))


def download_parallel(jobs_file: Path, workers: int = 8) -> int:
    cmd = [
        "parallel",
        "--colsep", r"\t",
        "-j", str(workers),
        "--delay", "0.5",
        "--joblog", str(OUTPUT_DIR / "parallel.log"),
        "--resume-failed",
        "mkdir -p $(dirname {2}) && [ -s {2} ] || gdown {1} -O {2} -q",
        "::::",
        str(jobs_file),
    ]
    print(f"Running: {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd).returncode


def download_folders() -> int:
    code = 0
    for folder_id, name in SUBFOLDERS:
        dest = OUTPUT_DIR / name
        dest.mkdir(parents=True, exist_ok=True)
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        print(f"\n=== {name} ===", flush=True)
        result = subprocess.run(["gdown", "--folder", "--continue", url, "-O", str(dest)])
        if result.returncode != 0:
            code = 1
    return code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["fast", "folder"], default="fast")
    parser.add_argument("--workers", type=int, default=8, help="parallel workers (fast mode)")
    args = parser.parse_args()

    before = count_media()
    print(f"Before: {before}/1520")

    if args.mode == "fast":
        if not MANIFEST.exists():
            print("Run manifest export first:", file=sys.stderr)
            print('  gdown --folder --json "FOLDER_URL" -q > media/file_manifest.json', file=sys.stderr)
            return 1
        missing = missing_entries()
        print(f"Missing: {len(missing)}")
        if not missing:
            print("All done.")
            return 0
        jobs = OUTPUT_DIR / "missing_jobs.tsv"
        write_jobs(jobs, missing)
        code = download_parallel(jobs, args.workers)
    else:
        code = download_folders()

    after = count_media()
    print(f"\nAfter: {after}/1520 (+{after - before})")
    return code


if __name__ == "__main__":
    sys.exit(main())
