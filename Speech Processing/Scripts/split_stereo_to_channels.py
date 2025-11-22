# 1. Basic usage (process ALL .wav files in INPUT_DIR):
#       python split_stereo_to_channels.py
#
#    This will:
#      - Read stereo WAVs from:
#          C:\Proxima Tech Solutions\Bakcell
#      - Split each into two mono channel files:
#          <name>_ch1.wav and <name>_ch2.wav
#      - Convert each channel file to mono 16 kHz
#      - Save outputs into:
#          C:\Proxima Tech Solutions\Proxima AI Voice Call Center\Bakcell-Data-Prep\Bakcell-Channels\original-channels
#
# 2. Process only the first N stereo files in the input directory:
#       python split_stereo_to_channels.py --max-files 100
#
# 3. Process a single specific file by name:
#       python split_stereo_to_channels.py --file-name 728002097383668
#    or:
#       python split_stereo_to_channels.py --file-name 728002097383668.wav
#
# 4. Use a custom input / output directory:
#       python split_stereo_to_channels.py ^
#           --input-dir "C:\path\to\my\input_wavs" ^
#           --output-dir "C:\path\to\my\output_channels"
#
# 5. Use a specific ffmpeg executable (if not in PATH):
#       python split_stereo_to_channels.py ^
#           --ffmpeg-path "C:\ffmpeg\bin\ffmpeg.exe"
#
# 6. Resume behavior:
#      - If both <name>_ch1.wav and <name>_ch2.wav already exist in OUTPUT_DIR,
#        that source file is skipped (useful for resuming after an interrupted run).

import os
import argparse
import subprocess

INPUT_DIR = r"C:\Proxima Tech Solutions\Bakcell"
OUTPUT_DIR = r"C:\Proxima Tech Solutions\Proxima AI Voice Call Center\Bakcell-Data-Prep\Bakcell-Channels\original-channels"


def split_and_convert_with_ffmpeg(input_path, output_dir, ffmpeg_path="ffmpeg"):
    """
    Use ffmpeg to split a stereo WAV file into two mono WAVs,
    and then convert each to mono 16 kHz.
    """
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    out_ch1 = os.path.join(output_dir, f"{base_name}_ch1.wav")
    out_ch2 = os.path.join(output_dir, f"{base_name}_ch2.wav")

    # channelsplit for stereo:
    # channelsplit=channel_layout=stereo[FL][FR]
    # Then map FL and FR to two outputs.
    split_cmd = [
        ffmpeg_path,
        "-y",  # overwrite
        "-i", input_path,
        "-filter_complex", "channelsplit=channel_layout=stereo[FL][FR]",
        "-map", "[FL]", out_ch1,
        "-map", "[FR]", out_ch2,
    ]

    print(f"  Running split: {' '.join(split_cmd)}")
    result = subprocess.run(split_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print(f"  [ERROR] ffmpeg split failed for {os.path.basename(input_path)}")
        print("  ffmpeg stderr:")
        print("  " + result.stderr.replace("\n", "\n  "))
        return

    print(f"  [OK] {os.path.basename(input_path)} ->")
    print(f"       {os.path.basename(out_ch1)}, {os.path.basename(out_ch2)}")

    # Convert each channel to mono 16 kHz
    for out_channel_path in [out_ch1, out_ch2]:
        temp_output_path = os.path.join(output_dir, f"temp_{os.path.basename(out_channel_path)}")

        convert_cmd = [
            ffmpeg_path,
            "-y",  # overwrite
            "-i", out_channel_path,
            "-ac", "1",  # set to mono. [1, 5, 8]
            "-ar", "16000",  # set sample rate to 16 kHz. [1, 2]
            temp_output_path,
        ]

        print(f"  Running convert: {' '.join(convert_cmd)}")
        result = subprocess.run(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            print(f"  [ERROR] ffmpeg convert failed for {os.path.basename(out_channel_path)}")
            print("  ffmpeg stderr:")
            print("  " + result.stderr.replace("\n", "\n  "))
            continue

        # Replace the original split file with the converted one
        os.replace(temp_output_path, out_channel_path)
        print(f"  [OK] Converted {os.path.basename(out_channel_path)} to mono 16 kHz.")


def main():
    parser = argparse.ArgumentParser(
        description="Split stereo WAV call center audios into two mono channel WAVs using ffmpeg and convert to 16 kHz."
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default=INPUT_DIR,
        help=f"Input directory with stereo WAV files (default: {INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=OUTPUT_DIR,
        help=f"Output directory for channel WAV files (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="If set, process only the first N WAV files. Ignored if --file-name is set.",
    )
    parser.add_argument(
        "--file-name",
        type=str,
        default=None,
        help="Name of a single WAV file to process (with or without .wav).",
    )
    parser.add_argument(
        "--ffmpeg-path",
        type=str,
        default="ffmpeg",
        help="Path to ffmpeg executable (default assumes it's in PATH).",
    )

    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir
    max_files = args.max_files
    file_name = args.file_name
    ffmpeg_path = args.ffmpeg_path

    os.makedirs(output_dir, exist_ok=True)

    # Decide which files to process
    if file_name is not None:
        # Normalize extension
        fname = file_name
        if not fname.lower().endswith(".wav"):
            fname += ".wav"

        in_path = os.path.join(input_dir, fname)
        if not os.path.isfile(in_path):
            print(f"[ERROR] File not found: {in_path}")
            return

        all_files = [fname]
        print(f"[INFO] --file-name specified, ignoring --max-files. Processing only: {fname}")
    else:
        # Collect .wav files in sorted order for reproducibility
        all_files = sorted(
            f for f in os.listdir(input_dir)
            if f.lower().endswith(".wav")
        )

        if max_files is not None:
            all_files = all_files[:max_files]

    print(f"Input directory : {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Number of files to process: {len(all_files)}")

    for fname in all_files:
        in_path = os.path.join(input_dir, fname)

        base_name = os.path.splitext(fname)[0]
        out_ch1 = os.path.join(output_dir, f"{base_name}_ch1.wav")
        out_ch2 = os.path.join(output_dir, f"{base_name}_ch2.wav")

        # Skip if both channel files already exist
        if os.path.exists(out_ch1) and os.path.exists(out_ch2):
            print(f"[SKIP] {fname} already processed (both channels exist).")
            continue

        print(f"Processing: {fname}")
        try:
            split_and_convert_with_ffmpeg(in_path, output_dir, ffmpeg_path=ffmpeg_path)
        except Exception as e:
            print(f"  [ERROR] {fname}: {e}")


if __name__ == "__main__":
    main()