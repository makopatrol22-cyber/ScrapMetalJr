#!/usr/bin/env python3
"""
Batch upload images to Cloudinary.
Requires: pip install cloudinary
"""

import os
import sys
import cloudinary
import cloudinary.uploader
from concurrent.futures import ThreadPoolExecutor, as_completed

# Your Cloudinary config
cloudinary.config(
    cloud_name="dp34ykdrn",
    api_key="",  # Get from Cloudinary Dashboard > Settings > API Key
    api_secret="",  # Get from Cloudinary Dashboard > Settings > API Secret
)

# Directories to upload from
UPLOAD_DIRS = [
    "/Volumes/12TBook/website/Images",
]


def upload_file(filepath):
    """Upload a single file to Cloudinary."""
    filename = os.path.basename(filepath)
    # Use relative path as folder in Cloudinary
    relpath = os.path.relpath(filepath, "/Volumes/12TBook/website/Images")
    folder = (
        os.path.dirname(relpath).replace(os.sep, "/")
        if os.path.dirname(relpath)
        else ""
    )

    try:
        result = cloudinary.uploader.upload(
            filepath,
            public_id=os.path.splitext(filename)[0],
            folder=folder if folder else None,
            overwrite=True,
            resource_type="image",
        )
        return filename, "OK", result.get("secure_url", "")
    except Exception as e:
        return filename, "ERROR", str(e)


def main():
    if not cloudinary.config().api_key:
        print("ERROR: Set your API key and secret at the top of this script.")
        print("Get them from: https://cloudinary.com/console -> Settings (gear icon)")
        sys.exit(1)

    # Collect all image files
    files = []
    for upload_dir in UPLOAD_DIRS:
        for root, dirs, filenames in os.walk(upload_dir):
            # Skip hidden dirs and large source folders
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ("JeepContent", "builds", "events")
            ]
            for fname in filenames:
                if fname.startswith(".") or fname.startswith("._"):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic"):
                    files.append(os.path.join(root, fname))

    print(f"Found {len(files)} images to upload")

    if len(files) == 0:
        print("No images found!")
        return

    # Upload with 5 concurrent threads
    uploaded = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(upload_file, f): f for f in files}
        for future in as_completed(futures):
            filename, status, msg = future.result()
            if status == "OK":
                uploaded += 1
                print(f"  [{uploaded}/{len(files)}] OK: {filename}")
            else:
                errors += 1
                print(f"  ERROR: {filename} -> {msg}")

    print(f"\nDone! {uploaded} uploaded, {errors} errors")


if __name__ == "__main__":
    main()
