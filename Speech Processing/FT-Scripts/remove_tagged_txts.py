#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

TAG_RE = re.compile(r"\[[^\[\]\n]+\]")

def is_only_tags_or_empty(text):
    """Check if text is empty or contains only tags and whitespace/punctuation."""
    if not text.strip():
        return True
    without_tags = TAG_RE.sub('', text)
    return re.match(r'^[\s.,;:!?\-]*$', without_tags) is not None

def main():
    ap = argparse.ArgumentParser(
        description="Remove .txt files with >2 [tags] and/or only-tags/empty files."
    )
    ap.add_argument("folder", type=Path, help="Folder to scan (recursively)")
    ap.add_argument("--which", choices=["union", "mt2", "only"], default="union",
                    help="Which set to remove: union (both), mt2 (>2 tags), only (empty/tags-only)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be deleted without actually deleting")
    args = ap.parse_args()
    
    if not args.folder.is_dir():
        raise SystemExit(f"Not a directory: {args.folder}")
    
    print(f"Scanning {args.folder} recursively...")
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
    
    # Determine which files to remove
    if args.which == "mt2":
        to_remove = list(dict.fromkeys(more_than_two_tags))
        label = ">2 tags"
    elif args.which == "only":
        to_remove = list(dict.fromkeys(only_tags_or_empty))
        label = "only tags or empty"
    else:  # union
        to_remove = list({*more_than_two_tags, *only_tags_or_empty})
        label = "union of both"
    
    if not to_remove:
        print(f"\nNo files to remove matching criteria: {label}")
        return
    
    print(f"\n{'DRY RUN: Would remove' if args.dry_run else 'Removing'} {len(to_remove)} files ({label})...")
    
    if args.dry_run:
        print("\nFirst 10 files that would be removed:")
        for f in to_remove[:10]:
            print(f"  {f}")
        if len(to_remove) > 10:
            print(f"  ... and {len(to_remove) - 10} more")
    else:
        removed_count = 0
        failed_count = 0
        
        for i, f in enumerate(to_remove, 1):
            if i % 100 == 0:
                print(f"Removed {i}/{len(to_remove)} files...", flush=True)
            
            try:
                f.unlink()
                removed_count += 1
            except Exception as e:
                print(f"Failed to remove {f}: {e}")
                failed_count += 1
        
        print(f"\n? Successfully removed: {removed_count} files")
        if failed_count > 0:
            print(f"? Failed to remove: {failed_count} files")
    
    print("\nDone!")

if __name__ == "__main__":
    main()