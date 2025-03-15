#!/usr/bin/env python3
"""
Archive handling functions for CBZ/CBR to WebP converter.
"""

import os
import zipfile
import patoolib
from pathlib import Path


def extract_archive(archive_path, extract_dir, logger):
    """Extract CBZ/CBR archive to temporary directory."""
    file_ext = archive_path.suffix.lower()
    logger.info(f"Extracting {archive_path} to {extract_dir}...")

    if file_ext in ('.cbz', '.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    elif file_ext in ('.cbr', '.rar'):
        patoolib.extract_archive(str(archive_path), outdir=str(extract_dir))
    else:
        raise ValueError(f"Unsupported archive format: {file_ext}")


def create_cbz(source_dir, output_file, logger, compresslevel=9):
    """Create a new CBZ file from the contents of source_dir with optimized compression."""
    import os
    import zipfile
    from pathlib import Path
    
    logger.info(f"Creating CBZ file: {output_file} (compression level: {compresslevel})")

    # Count file types for reporting
    image_count = 0
    other_count = 0

    # Collect all files and sort them for proper ordering
    all_files = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            file_path = Path(root) / file
            all_files.append((file_path, file_path.relative_to(source_dir)))
            
            # Count file types
            if file_path.suffix.lower() == '.webp':
                image_count += 1
            else:
                other_count += 1
    
    # Sort files - typically comic pages are numbered sequentially
    all_files.sort(key=lambda x: str(x[1]))

    # Use maximum compression for smaller files
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=compresslevel) as zipf:
        file_count = 0
        for file_path, rel_path in all_files:
            zipf.write(file_path, rel_path)
            file_count += 1

        if other_count > 0:
            logger.debug(f"Added {file_count} files to {output_file} "
                       f"({image_count} WebP images, {other_count} other files)")
        else:
            logger.debug(f"Added {file_count} WebP images to {output_file}")


def find_comic_archives(directory, recursive=False):
    """Find all CBZ/CBR (or ZIP/RAR) files in the given directory."""
    valid_extensions = {'.cbz', '.cbr', '.zip', '.rar'}
    archives = []

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if Path(file).suffix.lower() in valid_extensions:
                    archives.append(Path(root) / file)
    else:
        for file in os.listdir(directory):
            file_path = Path(directory) / file
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                archives.append(file_path)

    return sorted(archives)
