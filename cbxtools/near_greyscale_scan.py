"""Utilities for scanning archives for near greyscale images.

The scanning functions return both the number of pages that would trigger
auto-greyscale conversion and the total pages inspected, and support
multi-threaded execution.
"""

from pathlib import Path
import os
import tempfile

from PIL import Image
import numpy as np

from concurrent.futures import ThreadPoolExecutor, as_completed

from .archives import extract_archive, find_comic_archives
from .conversion import should_convert_to_greyscale


IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}


def archive_contains_near_greyscale(archive_path, pixel_threshold=16, percent_threshold=0.01, logger=None):
    """Check if an archive contains near greyscale images.

    Returns a tuple ``(contains, near_count, total_count)`` where ``contains`` is
    ``True`` if any image would be converted by the auto-greyscale logic.
    """
    archive_path = Path(archive_path)
    near_count = 0
    total_count = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        try:
            extract_archive(archive_path, temp_path, logger)
        except Exception as e:
            if logger:
                logger.error(f"Error extracting {archive_path}: {e}")
            return False, 0, 0

        for root, _, files in os.walk(temp_path):
            for file in files:
                img_path = Path(root) / file
                if img_path.suffix.lower() in IMAGE_EXTS:
                    try:
                        with Image.open(img_path) as img:
                            if img.mode not in ('RGB', 'RGBA'):
                                continue
                            total_count += 1
                            img_array = np.array(img)
                            if should_convert_to_greyscale(img_array, pixel_threshold, percent_threshold):
                                near_count += 1
                    except Exception as e:
                        if logger:
                            logger.warning(f"Failed to analyze {img_path}: {e}")
                        continue

    return near_count > 0, near_count, total_count


def scan_directory_for_near_greyscale(
    directory,
    recursive=False,
    pixel_threshold=16,
    percent_threshold=0.01,
    threads=1,
    logger=None,
):
    """Return a list of ``(archive, near_count, total_count)`` tuples."""
    directory = Path(directory)
    archives = find_comic_archives(directory, recursive)
    results = []

    max_workers = threads or 1

    def scan(archive):
        if logger:
            logger.info(f"Scanning {archive} for near greyscale images")
        contains, near, total = archive_contains_near_greyscale(
            archive, pixel_threshold, percent_threshold, logger
        )
        return archive, contains, near, total

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_archive = {executor.submit(scan, a): a for a in archives}
        for future in as_completed(future_to_archive):
            archive, contains, near, total = future.result()
            if contains:
                results.append((archive, near, total))

    return results
