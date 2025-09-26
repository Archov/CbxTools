#!/usr/bin/env python3
"""
Archive handling functions for CBZ/CBR/CB7 to WebP converter.
Now uses consolidated ArchiveHandler.
"""

from .core.archive_handler import ArchiveHandler
from .core.image_analyzer import ImageAnalyzer


# Re-export main functions for backward compatibility
def extract_archive(archive_path, extract_dir, logger):
    """Extract CBZ/CBR/CB7 archive to temporary directory."""
    return ArchiveHandler.extract_archive(archive_path, extract_dir, logger)


def create_cbz(source_dir, output_file, logger, compresslevel=9):
    """Create a new CBZ file from the contents of source_dir."""
    return ArchiveHandler.create_cbz(source_dir, output_file, logger, compresslevel)


def find_comic_archives(directory, recursive=False):
    """Find all CBZ/CBR/CB7 files in the given directory."""
    return ArchiveHandler.find_archives(directory, recursive)


def find_image_files(directory, recursive=False):
    """Find all image files in the given directory."""
    return ImageAnalyzer.find_image_files(directory, recursive)


def is_image_file(file_path):
    """Check if a file is an image based on its extension."""
    return ImageAnalyzer.is_image_file(file_path)


def is_archive_file(file_path):
    """Check if a file is a supported archive based on its extension."""
    return ArchiveHandler.is_supported_archive(file_path)