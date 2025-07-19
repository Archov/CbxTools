"""Utilities for scanning archives for near greyscale images."""

from pathlib import Path
import os
import tempfile

from PIL import Image
import numpy as np

from .archives import extract_archive, find_comic_archives
from .conversion import should_convert_to_greyscale


IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}


def archive_contains_near_greyscale(archive_path, pixel_threshold=16, percent_threshold=0.01, logger=None):
    """Return True if any image in the archive would be converted to greyscale."""
    archive_path = Path(archive_path)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        try:
            extract_archive(archive_path, temp_path, logger)
        except Exception as e:
            if logger:
                logger.error(f"Error extracting {archive_path}: {e}")
            return False

        for root, _, files in os.walk(temp_path):
            for file in files:
                img_path = Path(root) / file
                if img_path.suffix.lower() in IMAGE_EXTS:
                    try:
                        with Image.open(img_path) as img:
                            if img.mode not in ('RGB', 'RGBA'):
                                continue
                            img_array = np.array(img)
                            if should_convert_to_greyscale(img_array, pixel_threshold, percent_threshold):
                                return True
                    except Exception as e:
                        if logger:
                            logger.warning(f"Failed to analyze {img_path}: {e}")
                        continue
    return False


def scan_directory_for_near_greyscale(directory, recursive=False, pixel_threshold=16, percent_threshold=0.01, logger=None):
    """Return a list of archives that contain near greyscale images."""
    directory = Path(directory)
    archives = find_comic_archives(directory, recursive)
    results = []
    for archive in archives:
        if logger:
            logger.info(f"Scanning {archive} for near greyscale images")
        try:
            if archive_contains_near_greyscale(archive, pixel_threshold, percent_threshold, logger):
                results.append(archive)
        except Exception as e:
            if logger:
                logger.error(f"Error scanning {archive}: {e}")
    return results
