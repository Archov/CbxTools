#!/usr/bin/env python3
"""
Unified file processor for CBXTools.
Handles all file types (archives, images, image folders) with a single interface.
Eliminates duplication between regular processing and watch mode.
"""

import shutil
from pathlib import Path
from typing import Optional, Tuple, Any

from .archive_handler import ArchiveHandler
from .image_analyzer import ImageAnalyzer
from .filesystem_utils import FileSystemUtils


class FileProcessor:
    """
    Unified processor for all file types in CBXTools.
    Handles archives, individual images, and image folders with consistent interface.
    """
    
    def __init__(self, logger, packaging_queue=None):
        """
        Initialize the file processor.
        
        Args:
            logger: Logger instance for output
            packaging_queue: Optional packaging queue for asynchronous processing
        """
        self.logger = logger
        self.packaging_queue = packaging_queue
    
    def process_item(self, item: Path, output_dir: Path, args: Any, 
                    preserve_directory_structure: bool = False, 
                    input_base_dir: Optional[Path] = None) -> Tuple[bool, int, int]:
        """
        Process a single item (file or directory) with the given parameters.
        
        Args:
            item: Path to the item to process (file or directory)
            output_dir: Base output directory
            args: Arguments object containing all processing parameters
            preserve_directory_structure: Whether to preserve directory structure
            input_base_dir: Base input directory for relative path calculation
            
        Returns:
            Tuple of (success, original_size, new_size)
        """
        try:
            # Determine the target output directory
            if preserve_directory_structure and input_base_dir and item.parent != input_base_dir:
                rel_path = item.parent.relative_to(input_base_dir)
                target_output_dir = output_dir / rel_path
            else:
                target_output_dir = output_dir
            
            target_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process based on item type
            if item.is_file() and ArchiveHandler.is_supported_archive(item):
                return self._process_archive_file(item, target_output_dir, args)
            elif item.is_file() and ImageAnalyzer.is_image_file(item):
                return self._process_single_image(item, target_output_dir, args)
            elif item.is_dir() and self._is_image_folder(item):
                return self._process_image_folder(item, target_output_dir, args)
            else:
                self.logger.warning(f"Skipping unsupported item: {item}")
                return False, 0, 0
                
        except Exception as e:
            self.logger.exception(f"Error processing {item}: {e}")
            return False, 0, 0
    
    def _process_archive_file(self, archive_file: Path, output_dir: Path, args: Any) -> Tuple[bool, int, int]:
        """Process a single archive file."""
        from ..conversion import process_single_file
        return process_single_file(
            input_file=archive_file,
            output_dir=output_dir,
            quality=args.quality,
            max_width=args.max_width,
            max_height=args.max_height,
            no_cbz=args.no_cbz,
            keep_originals=args.keep_originals,
            num_threads=getattr(args, 'threads', 0),
            logger=self.logger,
            packaging_queue=self.packaging_queue,
            method=args.method,
            preprocessing=args.preprocessing,
            zip_compresslevel=args.zip_compression,
            lossless=args.lossless,
            grayscale=args.grayscale,
            auto_contrast=args.auto_contrast,
            auto_greyscale=args.auto_greyscale,
            auto_greyscale_pixel_threshold=args.auto_greyscale_pixel_threshold,
            auto_greyscale_percent_threshold=args.auto_greyscale_percent_threshold,
            preserve_auto_greyscale_png=args.preserve_auto_greyscale_png,
            output_format=getattr(args, 'output', 'cbz'),
            verbose=args.verbose
        )
    
    def _process_single_image(self, image_file: Path, output_dir: Path, args: Any) -> Tuple[bool, int, int]:
        """Process a single image file."""
        from ..conversion import convert_single_image
        try:
            # Get original file size
            _orig_size_str, orig_size_bytes = FileSystemUtils.get_file_size_formatted(image_file)
            
            # Convert the image
            convert_single_image(
                image_file=image_file,
                output_dir=output_dir,
                quality=args.quality,
                max_width=args.max_width,
                max_height=args.max_height,
                grayscale=args.grayscale,
                auto_contrast=args.auto_contrast,
                auto_greyscale=args.auto_greyscale,
                auto_greyscale_pixel_threshold=args.auto_greyscale_pixel_threshold,
                auto_greyscale_percent_threshold=args.auto_greyscale_percent_threshold,
                preserve_auto_greyscale_png=args.preserve_auto_greyscale_png,
                verbose=args.verbose,
            )
            
            # Calculate new size
            output_file = output_dir / f"{image_file.stem}.webp"
            if output_file.exists():
                _new_size_str, new_size_bytes = FileSystemUtils.get_file_size_formatted(output_file)
                self.logger.info(f"Converted single image: {image_file.name}")
                return True, orig_size_bytes, new_size_bytes
            else:
                self.logger.error(f"Output file not created: {output_file}")
                return False, orig_size_bytes, 0
                
        except Exception as e:
            self.logger.exception(f"Error processing single image {image_file}: {e}")
            return False, 0, 0
    
    def _process_image_folder(self, image_dir: Path, output_dir: Path, args: Any) -> Tuple[bool, int, int]:
        """Process a folder containing images."""
        from ..conversion import convert_to_webp
        try:
            # Get original size
            orig_size = sum(f.stat().st_size for f in image_dir.rglob('*') if f.is_file())
            
            # Create file-specific output directory
            file_output_dir = output_dir / image_dir.name
            
            # Convert images in the folder
            convert_to_webp(
                source_dir=image_dir,
                output_dir=file_output_dir,
                quality=args.quality,
                max_width=args.max_width,
                max_height=args.max_height,
                num_threads=getattr(args, 'threads', 0),
                logger=self.logger,
                method=args.method,
                preprocessing=args.preprocessing,
                lossless=args.lossless,
                grayscale=args.grayscale,
                auto_contrast=args.auto_contrast,
                auto_greyscale=args.auto_greyscale,
                auto_greyscale_pixel_threshold=args.auto_greyscale_pixel_threshold,
                auto_greyscale_percent_threshold=args.auto_greyscale_percent_threshold,
                preserve_auto_greyscale_png=args.preserve_auto_greyscale_png,
                verbose=args.verbose,
            )
            
            # Create archive if requested
            if not args.no_cbz:
                # Validate output format
                output_format = getattr(args, 'output', 'cbz')
                if output_format.lower() not in ArchiveHandler.FORMAT_EXTENSIONS:
                    raise ValueError(f"Unsupported output format: {output_format}. Supported: {', '.join(ArchiveHandler.FORMAT_EXTENSIONS)}")
                
                # Get the correct extension for the output format
                extension = ArchiveHandler.get_extension_for_format(output_format)
                archive_output = output_dir / f"{image_dir.name}{extension}"
                
                if self.packaging_queue is not None:
                    result_dict = {"success": False, "new_size": 0}
                    self.packaging_queue.put((file_output_dir, archive_output, image_dir, result_dict, 
                                            getattr(args, 'output', 'cbz'), args.zip_compression))
                    self.logger.info(f"Queued {image_dir.name} for packaging")
                    return True, orig_size, 0
                else:
                    from ..archives import create_archive
                    create_archive(file_output_dir, archive_output, getattr(args, 'output', 'cbz'), 
                                 self.logger, args.zip_compression)
                    new_size = archive_output.stat().st_size
                    if not args.keep_originals:
                        shutil.rmtree(file_output_dir)
                    self.logger.info(f"Converted folder: {image_dir.name}")
                    return True, orig_size, new_size
            else:
                new_size = sum(f.stat().st_size for f in file_output_dir.rglob('*') if f.is_file())
                self.logger.info(f"Converted folder: {image_dir.name}")
                return True, orig_size, new_size
                
        except Exception as e:
            self.logger.exception(f"Error processing image folder {image_dir}: {e}")
            return False, 0, 0
    
    def _is_image_folder(self, directory: Path) -> bool:
        """Check if a directory contains images."""
        if not directory.is_dir():
            return False
        
        # Check if directory contains image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp'}
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                return True
        
        return False
    
    def cleanup_after_processing(self, item: Path, success: bool, args: Any, 
                               input_base_dir: Optional[Path] = None) -> None:
        """
        Clean up after processing (delete originals if requested).
        
        Args:
            item: The processed item
            success: Whether processing was successful
            args: Arguments object
            input_base_dir: Base input directory for cleanup
        """
        if not success or not getattr(args, 'delete_originals', False):
            return
        
        try:
            if item.is_file():
                # Delete the original file
                item.unlink()
                self.logger.info(f"Deleted original file: {item}")
                
                # Check if parent directory is now empty and remove if it is
                if input_base_dir:
                    FileSystemUtils.remove_empty_dirs(item.parent, input_base_dir, self.logger)
            elif item.is_dir():
                # Delete the original image folder
                shutil.rmtree(item)
                self.logger.info(f"Deleted original folder: {item}")
                
                # Check if parent directory is now empty and remove if it is
                if input_base_dir:
                    FileSystemUtils.remove_empty_dirs(item.parent, input_base_dir, self.logger)
        except Exception as e:
            self.logger.exception(f"Error deleting {item}: {e}")


def find_processable_items(directory: Path, recursive: bool = False) -> list[Path]:
    """
    Find all items that can be processed (archives, images, and image folders).
    
    Args:
        directory: Directory to search
        recursive: Whether to search recursively
        
    Returns:
        List of processable items
    """
    items = []
    
    # Find archives
    archives = ArchiveHandler.find_archives(directory, recursive)
    items.extend(archives)
    
    # Find individual images in the root directory
    if directory.is_dir():
        direct_images = [f for f in directory.iterdir() 
                        if f.is_file() and ImageAnalyzer.is_image_file(f)]
        items.extend(direct_images)
    
    # Find image folders
    if recursive:
        for subdir in directory.rglob('*'):
            if subdir.is_dir() and subdir != directory:
                # Check if this directory contains images
                has_images = any(ImageAnalyzer.is_image_file(f) for f in subdir.iterdir() if f.is_file())
                if has_images:
                    items.append(subdir)
    
    return sorted(items)
