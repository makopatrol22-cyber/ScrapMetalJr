#!/usr/bin/env python3
"""
Sort JeepContent photos/videos into YYYY-MM_EventName folder structure.

Usage:
    python3 sort_photos.py /Volumes/12TBook/website/Images/JeepContent [--dry-run] [--output /path/to/sorted]

Default output: creates a "Sorted" folder next to JeepContent.
Always does a dry-run first unless --execute is passed.
"""

import os
import sys
import re
import shutil
import struct
import argparse
from datetime import datetime
from pathlib import Path


# ============================================================
# EXIF date reader (no external dependencies)
# ============================================================


def read_exif_date(filepath):
    """Read DateTimeOriginal from JPEG EXIF data."""
    try:
        with open(filepath, "rb") as f:
            data = f.read(65536)  # Read first 64KB

        # Find EXIF marker (0xFFE1)
        idx = 0
        while idx < len(data) - 4:
            if data[idx] == 0xFF and data[idx + 1] == 0xE1:
                # Found APP1 marker
                exif_data = data[idx + 4 :]
                return parse_exif_datetime(exif_data)
            idx += 1
    except Exception:
        pass
    return None


def parse_exif_datetime(exif_data):
    """Parse DateTimeOriginal from EXIF data."""
    try:
        if exif_data[:6] != b"Exif\x00\x00":
            return None

        tiff = exif_data[6:]
        if len(tiff) < 8:
            return None

        # Determine byte order
        byte_order = tiff[:2]
        endian = "<" if byte_order == b"II" else ">"

        # Number of IFD entries
        num_entries = struct.unpack(endian + "H", tiff[8:10])[0]

        offset = 10
        for _ in range(num_entries):
            if offset + 12 > len(tiff):
                break
            tag, typ, count, value_offset = struct.unpack(
                endian + "HHII", tiff[offset : offset + 12]
            )
            # Tag 0x9003 = DateTimeOriginal, 0x0132 = DateTime
            if tag in (0x9003, 0x0132) and typ == 2:  # ASCII string
                if count <= 4:
                    # Value is in the offset field itself
                    raw = tiff[offset + 8 : offset + 8 + count]
                else:
                    # Value is at offset
                    if value_offset + count > len(tiff):
                        break
                    raw = tiff[value_offset : value_offset + count]
                date_str = raw.decode("ascii", errors="ignore").strip("\x00")
                return parse_date_string(date_str)
            offset += 12
    except Exception:
        pass
    return None


def parse_date_string(date_str):
    """Parse EXIF date string like '2022:06:15 14:30:00'."""
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d"):
        try:
            return datetime.strptime(date_str[:19], fmt)
        except ValueError:
            continue
    return None


# ============================================================
# Date extraction from various sources
# ============================================================


def get_file_date(filepath):
    """Get the best available date for a file: EXIF > filename > mtime."""
    ext = os.path.splitext(filepath)[1].lower()

    # 1. Try EXIF for JPEGs
    if ext in (".jpg", ".jpeg", ".JPG", ".JPEG"):
        exif_date = read_exif_date(filepath)
        if exif_date:
            return exif_date

    # 2. Try extracting date from filename
    basename = os.path.basename(filepath)
    filename_date = extract_date_from_name(basename)
    if filename_date:
        return filename_date

    # 3. Fall back to file modification time
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime)
    except Exception:
        return None


def extract_date_from_name(name):
    """Extract date from filenames like DSC_20220615_1430.jpg, IMG_20220615.jpg, etc."""
    # Pattern: YYYYMMDD anywhere in filename
    match = re.search(r"(20[12]\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", name)
    if match:
        try:
            return datetime(
                int(match.group(1)), int(match.group(2)), int(match.group(3))
            )
        except ValueError:
            pass
    return None


# ============================================================
# Folder name parsing
# ============================================================

KNOWN_EVENTS = {
    "Krawlin": "Krawlin",
    "Jeep_Beach": "Jeep Beach",
    "JeepBeach": "Jeep Beach",
    "JWJ": "Jeepin' With Judd",
    "FTTC": "Florida Trail Team Challenge",
    "Jeeptoberfest": "Jeeptoberfest",
    "ONF": "Ocala National Forest",
    "Citrus_Ride": "Citrus Ride",
    "Citrus": "Citrus Ride",
    "Blueberry Jam": "Blueberry Jam",
    "Hard_Rock_Ocala": "Hard Rock Ocala",
    "4x4": "4x4 Adventure",
    "4X4": "4x4 Adventure",
    "dd214": "DD-214 Ride",
    "DD-214": "DD-214 Ride",
    "FTS": "FTS",
    "Gladiator": "Gladiator Build",
    "TJ_Rebuild": "TJ Rebuild",
    "oilpan": "Oil Pan Repair",
}

MONTH_NAMES = {
    "Jan": "01",
    "January": "01",
    "Feb": "02",
    "February": "02",
    "Mar": "03",
    "March": "03",
    "Apr": "04",
    "April": "04",
    "May": "05",
    "Jun": "06",
    "June": "06",
    "Jul": "07",
    "July": "07",
    "Aug": "08",
    "August": "08",
    "Sep": "09",
    "September": "09",
    "Oct": "10",
    "October": "10",
    "Nov": "11",
    "November": "11",
    "Dec": "12",
    "December": "12",
}


def parse_folder_name(folder_name):
    """Try to extract year and month from folder name. Returns (year, month, event_name)."""
    name = folder_name.replace(" ", "_")

    # Pattern: YYYY-MM-DD at start
    match = re.match(r"(20[12]\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", name)
    if match:
        event = re.sub(r"^\d{4}-\d{2}-\d{2}_?", "", name).replace("_", " ").strip()
        return int(match.group(1)), int(match.group(2)), event or "Misc"

    # Pattern: YYYY-MM at start
    match = re.match(r"(20[12]\d)-(0[1-9]|1[0-2])", name)
    if match:
        event = re.sub(r"^\d{4}-\d{2}_?", "", name).replace("_", " ").strip()
        return int(match.group(1)), int(match.group(2)), event or "Misc"

    # Pattern: YYYY_MonthName or YYYY-MonthName
    match = re.match(r"(20[12]\d)[_-](\w+)", name)
    if match:
        year = int(match.group(1))
        month_str = match.group(2)
        if month_str in MONTH_NAMES:
            event = name[match.end() :].replace("_", " ").strip(" -_")
            return year, int(MONTH_NAMES[month_str]), event or "Misc"
        else:
            # Year + event name (no month), default to January
            event = month_str + name[match.end() :]
            event = event.replace("_", " ").strip()
            return year, 1, event

    # Pattern: YYYY_EventName (underscore separated)
    match = re.match(r"(20[12]\d)[_-](.+)", name)
    if match:
        year = int(match.group(1))
        event = match.group(2).replace("_", " ").strip()
        return year, 1, event

    # No date in name
    return None, None, name.replace("_", " ")


def get_event_name(folder_name, parsed_event):
    """Clean up the event name, using known event mappings."""
    for key, clean_name in KNOWN_EVENTS.items():
        if key.lower() in folder_name.lower():
            return clean_name
    return parsed_event or folder_name.replace("_", " ")


# ============================================================
# Main sorting logic
# ============================================================

MEDIA_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".heic",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".insv",
    ".MP4",
    ".MOV",
    ".JPG",
    ".JPEG",
    ".PNG",
    ".HEIC",
    ".raw",
    ".cr2",
    ".nef",
    ".dng",
}


def scan_folder(source_dir):
    """Scan all files in subdirectories, return list of (file_path, best_date)."""
    results = []
    source = Path(source_dir)

    for item in sorted(source.iterdir()):
        if item.name.startswith(".") or item.name.startswith("._"):
            continue
        if not item.is_dir():
            continue

        # Parse folder name for date hints
        folder_year, folder_month, folder_event = parse_folder_name(item.name)
        event_name = get_event_name(item.name, folder_event)

        # Scan files in this folder (including subdirectories)
        file_count = 0
        for root, dirs, files in os.walk(item):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if fname.startswith("."):
                    continue
                fpath = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1].lower()
                if ext not in {e.lower() for e in MEDIA_EXTENSIONS}:
                    continue

                file_date = get_file_date(fpath)

                # Use folder date as fallback if file date seems wrong
                if file_date and folder_year:
                    if file_date.year < 2000 or file_date.year > 2030:
                        file_date = datetime(folder_year, folder_month or 1, 1)
                elif not file_date and folder_year:
                    file_date = datetime(folder_year, folder_month or 1, 1)

                results.append(
                    {
                        "source": fpath,
                        "date": file_date,
                        "event": event_name,
                        "folder_year": folder_year,
                        "folder_month": folder_month,
                    }
                )
                file_count += 1

        print(f"  Scanned: {item.name} -> {event_name} ({file_count} files)")

    return results


def generate_target_path(file_info, output_dir):
    """Generate the target path for a file based on its date and event."""
    date = file_info["date"]
    event = file_info["event"]

    if date:
        year = date.year
        month = date.month
    elif file_info["folder_year"]:
        year = file_info["folder_year"]
        month = file_info["folder_month"] or 1
    else:
        year = 9999
        month = 1

    month_str = f"{month:02d}"
    folder_name = f"{year}-{month_str}_{event}"

    # Clean folder name
    folder_name = re.sub(r'[<>:"/\\|?*]', "-", folder_name)
    folder_name = re.sub(r"\s+", "-", folder_name)
    folder_name = re.sub(r"-+", "-", folder_name).strip("-")

    target_dir = os.path.join(output_dir, str(year), folder_name)

    # Preserve subdirectory structure within the event
    source = file_info["source"]
    # Find relative path from the JeepContent event folder
    parts = Path(source).parts
    jeep_idx = None
    for i, p in enumerate(parts):
        if "JeepContent" in p:
            jeep_idx = i
            break

    if jeep_idx is not None and jeep_idx + 3 < len(parts):
        # There's a subdirectory after the event folder
        subpath = os.path.join(*parts[jeep_idx + 2 : -1])
        target_dir = os.path.join(target_dir, subpath)

    filename = os.path.basename(source)
    return os.path.join(target_dir, filename)


def main():
    parser = argparse.ArgumentParser(
        description="Sort JeepContent into organized folder structure"
    )
    parser.add_argument("source", help="Path to JeepContent folder")
    parser.add_argument(
        "--output", "-o", help="Output directory (default: source/../Sorted)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would happen without moving files (default)",
    )
    parser.add_argument(
        "--execute", action="store_true", help="Actually move/copy the files"
    )
    parser.add_argument(
        "--copy", action="store_true", help="Copy files instead of moving them"
    )
    args = parser.parse_args()

    source = os.path.abspath(args.source)
    if not os.path.isdir(source):
        print(f"Error: {source} is not a directory")
        sys.exit(1)

    output = args.output or os.path.join(os.path.dirname(source), "Sorted")
    dry_run = not args.execute

    print(f"Source:  {source}")
    print(f"Output:  {output}")
    print(f"Mode:    {'DRY RUN' if dry_run else ('COPY' if args.copy else 'MOVE')}")
    print()

    # Scan
    print("Scanning files...")
    files = scan_folder(source)
    print(f"\nFound {len(files)} media files\n")

    if not files:
        print("No files found!")
        sys.exit(0)

    # Generate target paths
    operations = []
    for f in files:
        target = generate_target_path(f, output)
        operations.append((f["source"], target, f["date"], f["event"]))

    # Show preview
    print("=" * 70)
    print("PLANNED ORGANIZATION:")
    print("=" * 70)

    # Group by target folder
    by_folder = {}
    for src, tgt, date, event in operations:
        folder = os.path.dirname(tgt)
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append((src, tgt))

    for folder in sorted(by_folder.keys()):
        items = by_folder[folder]
        print(f"\n  {folder}/")
        print(f"    ({len(items)} files)")
        # Show first 3 as examples
        for src, tgt in items[:3]:
            print(f"    <- {os.path.basename(src)}")
        if len(items) > 3:
            print(f"    ... and {len(items) - 3} more")

    print("\n" + "=" * 70)
    print(f"Total: {len(operations)} files -> {len(by_folder)} folders")

    if dry_run:
        print("\nDRY RUN - No files were moved.")
        print("Run with --execute to actually move files.")
        print("Run with --execute --copy to copy instead of move.")
        return

    # Execute
    print("\nOrganizing files...")
    errors = 0
    for i, (src, tgt, date, event) in enumerate(operations):
        try:
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            if args.copy:
                shutil.copy2(src, tgt)
            else:
                shutil.move(src, tgt)
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(operations)}...")
        except Exception as e:
            print(f"  ERROR: {src} -> {e}")
            errors += 1

    print(f"\nDone! {len(operations) - errors} files organized, {errors} errors.")


if __name__ == "__main__":
    main()
