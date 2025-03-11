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
    Get size in a human-readable format.
    
    Args:
        file_path_or_size: Either a Path object or a size in bytes
    """
    if isinstance(file_path_or_size, (int, float)):
        size_bytes = file_path_or_size
    else:
        size_bytes = file_path_or_size.stat().st_size
    
    # Define size units
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size_unit_index = 0
    
    # Convert to appropriate unit for readability
    size = float(size_bytes)
    while size >= 1024 and size_unit_index < len(units) - 1:
        size /= 1024
        size_unit_index += 1
    
    return f"{size:.2f} {units[size_unit_index]}", size_bytes
