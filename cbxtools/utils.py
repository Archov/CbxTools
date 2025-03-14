#!/usr/bin/env python3
"""
Utility functions for CBZ/CBR to WebP converter.
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

def get_preset_parameters(preset):
    """Get optimized parameters based on preset name."""
    presets = {
        'default': {
            'method': 4,
            'sharp_yuv': False,
            'preprocessing': None,
            'zip_compression': 6,
            'quality_adjustment': 0
        },
        'comic': {
            'method': 6,                # Best compression method
            'sharp_yuv': True,          # Better text rendering
            'preprocessing': 'unsharp_mask', # Enhance line art
            'zip_compression': 9,       # Maximum ZIP compression
            'quality_adjustment': -5    # Slightly lower quality for better compression
        },
        'photo': {
            'method': 4,
            'sharp_yuv': False,         # Not needed for photos
            'preprocessing': None,      # No preprocessing for photos
            'zip_compression': 6,
            'quality_adjustment': 5     # Higher quality for photos
        },
        'maximum': {
            'method': 6,                # Best compression method
            'sharp_yuv': True,          # Better text rendering
            'preprocessing': None,      # No preprocessing
            'zip_compression': 9,       # Maximum ZIP compression
            'quality_adjustment': -10   # Lower quality for maximum compression
        }
    }
    
    return presets.get(preset, presets['default'])
