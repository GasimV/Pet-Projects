#!/usr/bin/env python3
import argparse
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(
        description="Find and remove .wav files that do not have a corresponding .txt file."
    )
    ap.add_argument("folder", type=Path, help="Folder to scan (recursively)")
    ap.add_argument("--execute", action="store_true",
                    help="Actually delete the files. (Default is a dry run)")
    args = ap.parse_args()

    if not args.folder.is_dir():
        raise SystemExit(f"Error: Not a directory: {args.folder}")

    print(f"Scanning {args.folder.resolve()} recursively for orphaned .wav files...")
    wav_files = list(args.folder.rglob("*.wav"))

    if not wav_files:
        print("No .wav files found in the directory.")
        return

    orphaned_wavs = []
    for wav_file in wav_files:
        # Create the expected path for the corresponding .txt file
        corresponding_txt = wav_file.with_suffix(".txt")

        # Check if the .txt file does NOT exist
        if not corresponding_txt.exists():
            orphaned_wavs.append(wav_file)

    if not orphaned_wavs:
        print("\nNo orphaned .wav files found. All .wav files have a corresponding .txt file.")
        return

    print(f"\nFound {len(orphaned_wavs)} orphaned .wav files.")

    if not args.execute:
        print("\n--- DRY RUN MODE ---")
        print("The following files would be deleted. To delete them, run the script again with the --execute flag.")
        # Print the first 10 files as a preview
        for f in orphaned_wavs[:10]:
            print(f"  {f}")
        if len(orphaned_wavs) > 10:
            print(f"  ... and {len(orphaned_wavs) - 10} more.")
    else:
        print(f"\n--- EXECUTE MODE --- Deleting {len(orphaned_wavs)} files...")
        removed_count = 0
        failed_count = 0

        for i, f in enumerate(orphaned_wavs, 1):
            try:
                f.unlink()
                removed_count += 1
                if i % 100 == 0:
                    print(f"  Deleted {i}/{len(orphaned_wavs)} files...", flush=True)
            except Exception as e:
                print(f"  Failed to remove {f}: {e}")
                failed_count += 1

        print(f"\n? Successfully removed: {removed_count} files")
        if failed_count > 0:
            print(f"? Failed to remove: {failed_count} files")

    print("\nDone!")

if __name__ == "__main__":
    main()