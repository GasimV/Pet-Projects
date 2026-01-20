import os, shutil
from pathlib import Path

DEST = Path("...")
SOURCES = [
    #Path("..."),
    #Path("..."),
    Path("..."),
]

DEST.mkdir(parents=True, exist_ok=True)

def resolve_collision(dst: Path) -> Path:
    """If dst exists, append __dupN before suffix until free."""
    if not dst.exists():
        return dst
    stem, suf = dst.stem, dst.suffix
    n = 1
    while True:
        cand = dst.with_name(f"{stem}__dup{n}{suf}")
        if not cand.exists():
            return cand
        n += 1

def copy2_safe(src: Path, dst_dir: Path) -> Path:
    """Copy src into dst_dir, handling name collisions. Returns final dst path."""
    dst = dst_dir / src.name
    dst = resolve_collision(dst)
    shutil.copy2(src, dst)
    return dst

def main():
    copied_pairs = 0
    skipped_missing_txt = 0
    skipped_missing_wav = 0
    skipped_already_present = 0

    # Index existing basenames in DEST to avoid re-copying exact names
    existing = {p.name for p in DEST.glob("*")}

    for root in SOURCES:
        for wav in root.rglob("*.wav"):
            txt = wav.with_suffix(".txt")
            if not txt.exists():
                skipped_missing_txt += 1
                continue

            # If both already present (same base names) skip
            if wav.name in existing and txt.name in existing:
                skipped_already_present += 1
                continue

            # Copy (handle collisions with __dupN)
            final_wav = copy2_safe(wav, DEST)
            final_txt = copy2_safe(txt, DEST)
            existing.add(final_wav.name)
            existing.add(final_txt.name)
            copied_pairs += 1

            if copied_pairs % 100 == 0:
                print(f"[progress] copied {copied_pairs} pairs so far...")

    print("\nDone.")
    print(f"Copied pairs:          {copied_pairs}")
    print(f"Skipped (missing .txt): {skipped_missing_txt}")
    print(f"Skipped (missing .wav): {skipped_missing_wav}")
    print(f"Skipped (already there): {skipped_already_present}")

if __name__ == "__main__":
    main()
