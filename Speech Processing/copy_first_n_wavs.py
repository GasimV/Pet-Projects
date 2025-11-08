#!/usr/bin/env python3
"""
Copy the first N .wav files from SOURCE to DEST as quickly as possible,
without sorting or enumerating the entire directory. Skips files that
already exist in DEST (by name). Non-recursive by default.

Usage:
  python copy_first_n_wavs.py "\\172.21.15.50\tb-data\TB\Bakcell" "C:\Proxima Tech Solutions\Bakcell" --n 5000
"""

import argparse
import os
import shutil
import sys
import time

def copy_file(src_path, dst_path, retries=3, backoff=0.5):
    """Copy a single file with basic retry on transient errors."""
    for attempt in range(1, retries + 1):
        try:
            # copy2 preserves timestamps; switch to copyfile for a tiny speed bump if you don’t care.
            shutil.copy2(src_path, dst_path)
            return True
        except Exception as e:
            if attempt == retries:
                print(f"[ERROR] Failed to copy '{src_path}' -> '{dst_path}': {e}", file=sys.stderr)
                return False
            time.sleep(backoff * attempt)

def iterate_wavs(source, recursive=False):
    """Yield DirEntry objects for .wav files (case-insensitive)."""
    if not recursive:
        with os.scandir(source) as it:
            for entry in it:
                try:
                    if entry.is_file() and entry.name.lower().endswith(".wav"):
                        yield entry
                except FileNotFoundError:
                    # Entry disappeared between listing and stat; skip.
                    continue
    else:
        # Walk only if requested; walking the tree is slower.
        for root, dirs, files in os.walk(source):
            for name in files:
                if name.lower().endswith(".wav"):
                    yield SimpleEntry(os.path.join(root, name), name)

class SimpleEntry:
    """Small helper to mimic DirEntry for os.walk branch."""
    __slots__ = ("path", "name")
    def __init__(self, path, name):
        self.path = path
        self.name = name
    @property
    def is_file(self):
        return True

def main():
    parser = argparse.ArgumentParser(description="Copy first N .wav files fast, skipping existing.")
    parser.add_argument("source", help="Source folder (can be a UNC path).")
    parser.add_argument("dest", help="Destination folder.")
    parser.add_argument("--n", type=int, default=5000, help="Number of files to copy (default: 5000).")
    parser.add_argument("--recursive", action="store_true", help="Include subfolders (slower).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite if file already exists in destination.")
    parser.add_argument("--progress_every", type=int, default=100, help="Print progress every K copied files.")
    args = parser.parse_args()

    source = args.source
    dest = args.dest
    target = max(0, args.n)

    if not os.path.isdir(source):
        print(f"[FATAL] Source folder not found: {source}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(dest, exist_ok=True)

    copied = 0
    seen = 0
    start = time.time()

    print(f"Starting: copying up to {target} .wav files from\n  {source}\n→ {dest}\n"
          f"(no sorting, early stop, skipping existing{' unless --overwrite' if not args.overwrite else ''})")

    for entry in iterate_wavs(source, recursive=args.recursive):
        # Stop as soon as we’ve *copied* N files
        if copied >= target:
            break

        # Resolve full paths
        src_path = getattr(entry, "path", None) or os.path.join(source, entry.name)
        dst_path = os.path.join(dest, entry.name)

        # Skip / overwrite logic
        if os.path.exists(dst_path) and not args.overwrite:
            seen += 1
            continue

        if copy_file(src_path, dst_path):
            copied += 1
            if args.progress_every and (copied % args.progress_every == 0):
                elapsed = time.time() - start
                rate = copied / elapsed if elapsed > 0 else 0
                print(f"  Copied {copied}/{target} files … ({rate:.1f} files/s)")
        else:
            # Failed copy is counted as “seen” but not “copied”
            seen += 1

    elapsed = time.time() - start
    print(f"Done. Copied {copied} file(s) in {elapsed:.1f}s "
          f"({(copied/elapsed if elapsed>0 else 0):.1f} files/s).")

    if copied < target:
        print(f"Note: fewer than requested were copied. "
              f"Possible reasons: not enough new .wav files, permission issues, or early termination.", file=sys.stderr)

if __name__ == "__main__":
    main()
