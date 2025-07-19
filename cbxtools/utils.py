#!/usr/bin/env python3
"""
Utility functions for CBZ/CBR to WebP converter.
Enhanced with auto-greyscale parameter logging.
"""

import logging
from pathlib import Path


def setup_logging(verbose, silent):
    """Configure logging based on verbosity settings."""
    if silent:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger(__name__)


def get_file_size_formatted(file_path_or_size):
    """
    Return a tuple of (human_readable_size, size_in_bytes).
    If given a path, we take the file size from disk;
    if given an int, we interpret it as raw bytes.
    """
    if isinstance(file_path_or_size, (int, float)):
        size_bytes = file_path_or_size
    else:
        size_bytes = file_path_or_size.stat().st_size

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    idx = 0

    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1

    return f"{size:.2f} {units[idx]}", size_bytes


def remove_empty_dirs(directory, root_dir, logger):
    """
    Recursively removes empty directories starting from directory up to root_dir.
    Stops if a non-empty directory is encountered.
    
    Args:
        directory: The directory to check and potentially remove
        root_dir: The root directory to stop at (won't be removed)
        logger: Logger instance for logging messages
    """
    # Convert to Path objects if they aren't already
    directory = Path(directory)
    root_dir = Path(root_dir)
    
    # Don't attempt to remove the root directory or any directory outside the root
    if directory == root_dir or not str(directory).startswith(str(root_dir)):
        return
    
    # Check if directory exists and is a directory
    if not directory.is_dir():
        return
    
    # Check if directory is empty
    if not any(directory.iterdir()):
        try:
            directory.rmdir()
            logger.info(f"Removed empty directory: {directory}")
            
            # Recursively check parent directories
            remove_empty_dirs(directory.parent, root_dir, logger)
        except Exception as e:
            logger.error(f"Error removing directory {directory}: {e}")


def log_effective_parameters(args, logger, recursive=False):
    """
    Log the effective parameters being used for conversion.
    
    Args:
        args: Parsed command line arguments
        logger: Logger instance
        recursive: Whether recursive mode is enabled
    """
    params_str = f"quality={args.quality}, max_width={args.max_width}, " \
                f"max_height={args.max_height}, method={args.method}, " \
                f"preprocessing={args.preprocessing}, " \
                f"zip_compression={args.zip_compression}, lossless={args.lossless}"
    
    # Add transformation parameters to logging
    transformation_params = []
    if hasattr(args, 'grayscale') and args.grayscale:
        transformation_params.append(f"grayscale={args.grayscale}")
    if hasattr(args, 'auto_contrast') and args.auto_contrast:
        transformation_params.append(f"auto_contrast={args.auto_contrast}")
    if hasattr(args, 'auto_greyscale') and args.auto_greyscale:
        pixel_thresh = getattr(args, 'auto_greyscale_pixel_threshold', 16)
        percent_thresh = getattr(args, 'auto_greyscale_percent_threshold', 0.01)
        transformation_params.append(f"auto_greyscale={args.auto_greyscale} (pixel_threshold={pixel_thresh}, percent_threshold={percent_thresh})")
    
    if transformation_params:
        params_str += f", {', '.join(transformation_params)}"
    
    logger.info(f"Using parameters: {params_str}")
    
    # Log recursive mode status
    if recursive:
        logger.info("Recursive mode enabled")