#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

TAG_RE = re.compile(r"\[[^\[\]\n]+\]")

def remove_tags(text):
    """Remove all [*] tags from text."""
    return TAG_RE.sub('', text)

def main():
    ap = argparse.ArgumentParser(
        description="Remove all [*] tags from .txt files in a folder."
    )
    ap.add_argument("folder", type=Path, help="Folder to process (recursively)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview changes without modifying files")
    ap.add_argument("--execute", action="store_true",
                    help="Actually modify the files (removes tags)")
    args = ap.parse_args()
    
    if not args.folder.is_dir():
        raise SystemExit(f"Not a directory: {args.folder}")
    
    if not args.dry_run and not args.execute:
        raise SystemExit("ERROR: You must specify either --dry-run or --execute")
    
    if args.dry_run and args.execute:
        raise SystemExit("ERROR: Cannot use both --dry-run and --execute together")
    
    print(f"{'DRY RUN: ' if args.dry_run else ''}Scanning {args.folder} recursively...")
    txt_files = list(args.folder.rglob("*.txt"))
    
    files_with_tags = []
    total_tags_found = 0
    
    for i, f in enumerate(txt_files, 1):
        if i % 1000 == 0:
            print(f"Scanned {i}/{len(txt_files)} files...", flush=True)
        
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        tags = TAG_RE.findall(text)
        if tags:
            files_with_tags.append((f, len(tags)))
            total_tags_found += len(tags)
    
    print(f"\nTotal .txt files scanned: {len(txt_files)}")
    print(f"Files containing [*] tags: {len(files_with_tags)}")
    print(f"Total tags found: {total_tags_found}")
    
    if not files_with_tags:
        print("\nNo files with tags found. Nothing to do.")
        return
    
    if args.dry_run:
        print("\n--- DRY RUN MODE ---")
        print("Showing first 10 files that would be modified:\n")
        
        for idx, (f, tag_count) in enumerate(files_with_tags[:10], 1):
            print(f"[{idx}] {f}")
            print(f"    Tags to remove: {tag_count}")
            
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                cleaned = remove_tags(text)
                
                # Show before/after preview (first 200 chars)
                preview_len = 200
                print(f"    BEFORE: {text[:preview_len]!r}{'...' if len(text) > preview_len else ''}")
                print(f"    AFTER:  {cleaned[:preview_len]!r}{'...' if len(cleaned) > preview_len else ''}")
            except Exception as e:
                print(f"    Error reading file: {e}")
            
            print()
        
        if len(files_with_tags) > 10:
            print(f"... and {len(files_with_tags) - 10} more files")
        
        print(f"\nTo actually remove tags, run with --execute instead of --dry-run")
    
    elif args.execute:
        print("\n--- EXECUTING: Removing tags from files ---\n")
        
        modified_count = 0
        failed_count = 0
        
        for i, (f, tag_count) in enumerate(files_with_tags, 1):
            if i % 100 == 0:
                print(f"Processed {i}/{len(files_with_tags)} files...", flush=True)
            
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                cleaned = remove_tags(text)
                
                # Write back the cleaned text
                f.write_text(cleaned, encoding="utf-8")
                modified_count += 1
            except Exception as e:
                print(f"Failed to process {f}: {e}")
                failed_count += 1
        
        print(f"\n? Successfully modified: {modified_count} files")
        print(f"? Total tags removed: {total_tags_found}")
        if failed_count > 0:
            print(f"? Failed to process: {failed_count} files")
    
    print("\nDone!")

if __name__ == "__main__":
    main()