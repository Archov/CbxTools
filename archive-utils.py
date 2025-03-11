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
    
    if file_ext == '.cbz' or file_ext == '.zip':
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    elif file_ext == '.cbr' or file_ext == '.rar':
        patoolib.extract_archive(str(archive_path), outdir=str(extract_dir))
    else:
        raise ValueError(f"Unsupported archive format: {file_ext}")


def create_cbz(source_dir, output_file, logger):
    """Create a new CBZ file from the contents of source_dir."""
    logger.info(f"Creating CBZ file: {output_file}")
    
    # Use default compression level 6 for better speed/size tradeoff
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        file_count = 0
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                zipf.write(file_path, file_path.relative_to(source_dir))
                file_count += 1
                
        logger.debug(f"Added {file_count} files to {output_file}")


def find_comic_archives(directory, recursive=False):
    """Find all CBZ/CBR files in the given directory."""
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
