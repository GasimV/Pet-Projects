#!/usr/bin/env python3
import argparse, re, random
from pathlib import Path

TAG_RE = re.compile(r"\[[^\[\]\n]+\]")

def is_only_tags_or_empty(text):
    if not text.strip():
        return True
    without_tags = TAG_RE.sub('', text)
    return re.match(r'^[\s.,;:!?\-]*$', without_tags) is not None

def main():
    ap = argparse.ArgumentParser(
        description="Count .txt files with >2 [tags], only-tags/empty ones, and print random examples."
    )
    ap.add_argument("folder", type=Path, help="Folder to scan (recursively)")
    ap.add_argument("--n", type=int, default=10, help="How many files to print")
    ap.add_argument("--which", choices=["union","mt2","only"], default="union",
                    help="Which set to sample from")
    args = ap.parse_args()

    if not args.folder.is_dir():
        raise SystemExit(f"Not a directory: {args.folder}")

    txt_files = list(args.folder.rglob("*.txt"))
    more_than_two_tags = []
    only_tags_or_empty = []

    for i, f in enumerate(txt_files, 1):
        if i % 1000 == 0:
            print(f"Processed {i}/{len(txt_files)} files...", flush=True)
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if len(TAG_RE.findall(text)) > 2:
            more_than_two_tags.append(f)

        if is_only_tags_or_empty(text):
            only_tags_or_empty.append(f)

    print(f"\nTotal .txt files scanned: {len(txt_files)}")
    print(f"Files with >2 [tags]: {len(more_than_two_tags)}")
    print(f"Files that are only tags or empty: {len(only_tags_or_empty)}")

    if args.which == "mt2":
        candidates = list(dict.fromkeys(more_than_two_tags))
        label = ">2 tags"
    elif args.which == "only":
        candidates = list(dict.fromkeys(only_tags_or_empty))
        label = "only tags or empty"
    else:
        # union
        candidates = list({*more_than_two_tags, *only_tags_or_empty})
        label = "union of both"

    if not candidates:
        print("\nNo matching files found to display.")
        return

    k = min(args.n, len(candidates))
    sample = random.sample(candidates, k)

    print(f"\n--- Printing {k} random files from {label} ---\n")
    for idx, p in enumerate(sample, 1):
        print(f"[{idx}/{k}] {p}\n{'-'*80}")
        try:
            print(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception as e:
            print(f"(Could not read file: {e})")
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
