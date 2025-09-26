"""
Unified archive handling for CBZ/CBR/CB7 files.
Consolidates extraction and creation logic.
"""

import os
import zipfile
import tempfile
from pathlib import Path
from typing import ClassVar


class ArchiveHandler:
    """Centralized archive handling for comic book formats."""

    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = {'.cbz', '.cbr', '.cb7', '.zip', '.rar', '.7z'}
    
    @classmethod
    def is_supported_archive(cls, file_path):
        """Check if file is a supported archive format."""
        return Path(file_path).suffix.lower() in cls.SUPPORTED_EXTENSIONS
    
    @classmethod
    def extract_archive(cls, archive_path, extract_dir, logger=None):
        """Extract archive to directory using appropriate method."""
        file_ext = Path(archive_path).suffix.lower()
        
        if logger:
            logger.info(f"Extracting {archive_path} to {extract_dir}...")

        if file_ext in ('.cbz', '.zip'):
            cls._extract_zip(archive_path, extract_dir)
        elif file_ext in ('.cbr', '.rar'):
            cls._extract_rar(archive_path, extract_dir)
        elif file_ext in ('.cb7', '.7z'):
            cls._extract_7z(archive_path, extract_dir)
        else:
            raise ValueError(f"Unsupported archive format: {file_ext}")
    
    @staticmethod
    def _extract_zip(archive_path, extract_dir):
        """Extract ZIP/CBZ archive with path validation."""
        import shutil

        with zipfile.ZipFile(archive_path, 'r') as z:
            dest = Path(extract_dir).resolve()
            for m in z.infolist():
                name = Path(m.filename)
                # Disallow absolute paths
                if name.is_absolute():
                    raise ValueError(f"Unsafe absolute path in ZIP entry: {m.filename}")
                target = (dest / name).resolve()
                # Disallow traversal outside dest
                if not str(target).startswith(str(dest) + os.sep):
                    raise ValueError(f"Path traversal detected in ZIP entry: {m.filename}")
                if m.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(m, 'r') as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
    
    @staticmethod
    def _extract_rar(archive_path, extract_dir):
        """Extract RAR/CBR archive with path validation."""
        import rarfile
        import shutil

        dest = Path(extract_dir).resolve()
        with rarfile.RarFile(archive_path) as rf:
            for m in rf.infolist():
                name = Path(m.filename)
                if name.is_absolute():
                    raise ValueError(f"Unsafe absolute path in RAR entry: {m.filename}")
                target = (dest / name).resolve()
                if not str(target).startswith(str(dest) + os.sep):
                    raise ValueError(f"Path traversal detected in RAR entry: {m.filename}")
                if m.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with rf.open(m) as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
    
    @staticmethod
    def _extract_7z(archive_path, extract_dir):
        """Extract 7Z/CB7 archive with path validation."""
        import py7zr

        dest = Path(extract_dir).resolve()
        with py7zr.SevenZipFile(archive_path, mode='r') as z:
            members = z.getnames()
            safe = []
            for name in members:
                p = Path(name)
                if p.is_absolute():
                    raise ValueError(f"Unsafe absolute path in 7z entry: {name}")
                target = (dest / p).resolve()
                if not str(target).startswith(str(dest) + os.sep):
                    raise ValueError(f"Path traversal detected in 7z entry: {name}")
                safe.append(name)
            if safe:
                z.extract(targets=safe, path=str(dest))
    
    @classmethod
    def create_cbz(cls, source_dir, output_file, logger=None, compresslevel=9):
        """Create CBZ archive from directory with optimized compression."""
        if logger:
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

            if logger:
                if other_count > 0:
                    logger.debug(f"Added {file_count} files to {output_file} "
                               f"({image_count} WebP images, {other_count} other files)")
                else:
                    logger.debug(f"Added {file_count} WebP images to {output_file}")
    
    @classmethod
    def find_archives(cls, directory, recursive=False):
        """Find all supported archives in directory."""
        archives = []

        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = Path(root) / file
                    if cls.is_supported_archive(file_path):
                        archives.append(file_path)
        else:
            for file in os.listdir(directory):
                file_path = Path(directory) / file
                if file_path.is_file() and cls.is_supported_archive(file_path):
                    archives.append(file_path)

        return sorted(archives)
    
    @classmethod
    def extract_with_temp_dir(cls, archive_path, logger=None):
        """Extract archive to temporary directory. Returns temp directory path."""
        temp_dir = tempfile.mkdtemp()
        try:
            cls.extract_archive(archive_path, temp_dir, logger)
        except Exception:
            # Clean up on failure
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        else:
            return temp_dir
