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
    
    # Format to extension mapping
    FORMAT_EXTENSIONS: ClassVar[dict[str, str]] = {
        'zip': '.zip',
        'cbz': '.cbz', 
        'rar': '.rar',
        'cbr': '.cbr',
        '7z': '.7z',
        'cb7': '.cb7'
    }
    
    @classmethod
    def is_supported_archive(cls, file_path):
        """Check if file is a supported archive format."""
        return Path(file_path).suffix.lower() in cls.SUPPORTED_EXTENSIONS
    
    @classmethod
    def get_extension_for_format(cls, format_type):
        """Get the file extension for a given format type."""
        return cls.FORMAT_EXTENSIONS.get(format_type.lower(), '.cbz')
    
    @classmethod
    def get_supported_formats(cls) -> tuple[str, ...]:
        """Get tuple of supported format types."""
        return tuple(cls.FORMAT_EXTENSIONS.keys())
    
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
                if os.path.commonpath([str(dest), str(target)]) != str(dest):
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
                if os.path.commonpath([str(dest), str(target)]) != str(dest):
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
                if os.path.commonpath([str(dest), str(target)]) != str(dest):
                    raise ValueError(f"Path traversal detected in 7z entry: {name}")
                safe.append(name)
            if safe:
                z.extract(targets=safe, path=str(dest))
    
    @classmethod
    def create_cbz(cls, source_dir, output_file, logger=None, compresslevel=9):
        """Create CBZ archive from directory with optimized compression."""
        return cls.create_archive(source_dir, output_file, 'cbz', logger, compresslevel)
    
    @classmethod
    def create_archive(cls, source_dir, output_file, format_type, logger=None, compresslevel=9):
        """Create archive from directory in specified format."""
        if logger:
            logger.info(f"Creating {format_type.upper()} file: {output_file} (compression level: {compresslevel})")

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

        # Create archive based on format using dispatch dict
        creators = {
            'zip': cls._create_zip_archive, 'cbz': cls._create_zip_archive,
            'rar': cls._create_rar_archive, 'cbr': cls._create_rar_archive,
            '7z': cls._create_7z_archive,  'cb7': cls._create_7z_archive,
        }
        creator = creators.get(format_type)
        if not creator:
            supported_formats = tuple(creators.keys())
            raise ValueError(f"Unsupported output format: {format_type}. Supported formats are: {', '.join(supported_formats)}")
        creator(output_file, all_files, compresslevel, logger, image_count, other_count)
    
    @staticmethod
    def _create_zip_archive(output_file, all_files, compresslevel, logger, image_count, other_count):
        """Create ZIP/CBZ archive."""
        if not all_files:
            logger.warning(f"No files to archive for {output_file}. Skipping ZIP/CBZ creation.")
            return
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
    
    @staticmethod
    def _create_rar_archive(_output_file, _all_files, _compresslevel, logger, _image_count, _other_count):
        """Create RAR/CBR archive (not supported)."""
        msg = (
            "RAR/CBR output is not supported: Python rarfile does not provide creation. "
            "Please choose 'cbz/zip' or '7z/cb7' for output."
        )
        if logger:
            logger.error(msg)
        raise NotImplementedError(msg)
    
    @staticmethod
    def _create_7z_archive(output_file, all_files, compresslevel, logger, image_count, other_count):
        """Create 7Z/CB7 archive."""
        try:
            import py7zr
            # Map compresslevel (0-9) to py7zr preset levels
            filters = [{'id': py7zr.FILTER_LZMA2, 'preset': min(9, max(0, compresslevel))}]
            with py7zr.SevenZipFile(output_file, 'w', filters=filters) as archive:
                file_count = 0
                for file_path, rel_path in all_files:
                    archive.write(file_path, rel_path)
                    file_count += 1

                if logger:
                    if other_count > 0:
                        logger.debug(f"Added {file_count} files to {output_file} "
                                   f"({image_count} WebP images, {other_count} other files)")
                    else:
                        logger.debug(f"Added {file_count} WebP images to {output_file}")
        except ImportError as e:
            raise ImportError("py7zr is required for 7Z/CB7 output format") from e
    
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
