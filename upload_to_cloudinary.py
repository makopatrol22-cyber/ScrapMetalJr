#!/usr/bin/env python3
"""
Batch upload images to Cloudinary with auto-compression.
Compresses large images before uploading to stay under 10MB limit.
"""

import os
import sys
import tempfile
import cloudinary
import cloudinary.uploader
from concurrent.futures import ThreadPoolExecutor, as_completed

cloudinary.config(
    cloud_name="dp34ykdrn",
    api_key="247677974376225",
    api_secret="uwgZK0wWMs_Uwc6XFcFWU4rOFXI",
)

UPLOAD_DIRS = ["/Volumes/12TBook/website/Images"]
MAX_SIZE = 10 * 1024 * 1024  # 10MB Cloudinary free tier limit


def compress_image(filepath, target_size=8 * 1024 * 1024):
    """Compress image to fit under target size using sips (macOS built-in)."""
    file_size = os.path.getsize(filepath)
    if file_size <= target_size:
        return filepath

    # Try progressive quality reduction with sips
    for quality in [85, 75, 65, 55, 45]:
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.close()
        os.system(
            f'sips -s format jpeg -s formatOptions {quality} "{filepath}" --out "{tmp.name}" > /dev/null 2>&1'
        )
        if os.path.getsize(tmp.name) <= target_size:
            return tmp.name
        os.unlink(tmp.name)

    # Last resort: resize to 50%
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.close()
    os.system(
        f'sips -s format jpeg -s formatOptions 60 -Z 3000 "{filepath}" --out "{tmp.name}" > /dev/null 2>&1'
    )
    return tmp.name


def upload_file(filepath):
    """Upload a single file to Cloudinary."""
    filename = os.path.basename(filepath)
    relpath = os.path.relpath(filepath, "/Volumes/12TBook/website/Images")
    folder = (
        os.path.dirname(relpath).replace(os.sep, "/")
        if os.path.dirname(relpath)
        else ""
    )

    original_size = os.path.getsize(filepath)
    upload_path = filepath
    compressed = False

    if original_size > MAX_SIZE:
        upload_path = compress_image(filepath)
        compressed = True

    try:
        result = cloudinary.uploader.upload(
            upload_path,
            public_id=os.path.splitext(filename)[0],
            folder=folder if folder else None,
            overwrite=True,
            resource_type="image",
        )
        if compressed and upload_path != filepath:
            os.unlink(upload_path)
        return filename, "OK", result.get("secure_url", "")
    except Exception as e:
        if compressed and upload_path != filepath:
            os.unlink(upload_path)
        return filename, "ERROR", str(e)


def main():
    files = []
    for upload_dir in UPLOAD_DIRS:
        for root, dirs, filenames in os.walk(upload_dir):
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

    uploaded = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=3) as executor:
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
