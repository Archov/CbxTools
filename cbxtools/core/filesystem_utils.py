#!/usr/bin/env python3
"""
Unified file system utilities for cbxtools.
Consolidates path handling, directory cleanup, and file operations.
"""

import os
from pathlib import Path


class FileSystemUtils:
    """Centralized file system operations."""
    
    @staticmethod
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
    
    @staticmethod
    def remove_empty_dirs(directory, root_dir, logger=None):
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

        # Resolve and ensure directory is under root_dir; never remove the root itself
        directory = directory.resolve()
        root_dir = root_dir.resolve()
        if directory == root_dir:
            return
        import os
        if os.path.commonpath([str(directory), str(root_dir)]) != str(root_dir):
            return
        
        # Check if directory exists and is a directory
        if not directory.is_dir():
            return
        
        # Check if directory is empty
        if not any(directory.iterdir()):
            try:
                directory.rmdir()
                if logger:
                    logger.info(f"Removed empty directory: {directory}")
                
                # Recursively check parent directories
                FileSystemUtils.remove_empty_dirs(directory.parent, root_dir, logger)
            except Exception as e:
                if logger:
                    logger.error(f"Error removing directory {directory}: {e}")
    
    @staticmethod
    def cleanup_empty_directories(root_dir, logger=None):
        """
        Remove all empty directories under root_dir (bottom-up traversal).
        
        Args:
            root_dir: The root directory to clean up
            logger: Logger instance for logging messages
        """
        root_dir = Path(root_dir)
        removed_count = 0
        
        # Get all subdirectories (excluding root) as Path objects
        all_dirs = []
        for dirpath, dirnames, _ in os.walk(root_dir, topdown=False):
            for dirname in dirnames:
                all_dirs.append(Path(dirpath) / dirname)
        
        # Sort by depth (deepest first) to ensure we process child directories before parents
        all_dirs.sort(key=lambda p: len(p.parts), reverse=True)
        
        # Remove empty directories
        for directory in all_dirs:
            if not any(directory.iterdir()):
                try:
                    directory.rmdir()
                    removed_count += 1
                    if logger:
                        logger.debug(f"Removed empty directory: {directory}")
                except Exception as e:
                    if logger:
                        logger.error(f"Error removing directory {directory}: {e}")
        
        if logger:
            if removed_count > 0:
                logger.info(f"Removed {removed_count} pre-existing empty directories")
            else:
                logger.info("No empty directories found")
    
    
    @staticmethod
    def ensure_directory_exists(directory_path):
        """Ensure directory exists, creating it if necessary."""
        directory_path = Path(directory_path)
        directory_path.mkdir(parents=True, exist_ok=True)
        return directory_path
    
    @staticmethod
    def calculate_compression_stats(original_size, new_size):
        """Calculate compression statistics."""
        if original_size <= 0:
            return {
                'savings_bytes': 0,
                'savings_percentage': 0.0,
                'compression_ratio': 1.0,
                'increased': False
            }
        
        savings_bytes = original_size - new_size
        savings_percentage = (savings_bytes / original_size) * 100
        compression_ratio = new_size / original_size if original_size > 0 else 1.0
        increased = savings_bytes < 0
        
        return {
            'savings_bytes': savings_bytes,
            'savings_percentage': savings_percentage,
            'compression_ratio': compression_ratio,
            'increased': increased
        }
