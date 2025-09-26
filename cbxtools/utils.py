#!/usr/bin/env python3
"""
Utility functions for CBZ/CBR to WebP converter.
Now uses consolidated FileSystemUtils.
"""

import logging
from pathlib import Path
from .core.filesystem_utils import FileSystemUtils


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


# Re-export filesystem utilities for backward compatibility
def get_file_size_formatted(file_path_or_size):
    """Return a tuple of (human_readable_size, size_in_bytes)."""
    if isinstance(file_path_or_size, (int, float)):
        return FileSystemUtils.get_file_size_formatted(file_path_or_size)
    return FileSystemUtils.get_file_size_formatted(Path(file_path_or_size))


def remove_empty_dirs(directory, root_dir, logger):
    """Recursively remove empty directories."""
    return FileSystemUtils.remove_empty_dirs(directory, root_dir, logger)


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