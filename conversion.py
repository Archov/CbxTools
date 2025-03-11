#!/usr/bin/env python3
"""
Image conversion functions for CBZ/CBR to WebP converter.
"""

import os
import shutil
import tempfile
import multiprocessing
from pathlib import Path
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

from cbz_webp_converter.utils import get_file_size_formatted
from cbz_webp_converter.archive_utils import extract_archive, create_cbz


def convert_single_image(args):
    """Convert a single image to WebP format. This function runs in a separate process."""
    img_path, webp_path, quality, max_width, max_height = args
    
    try:
        # Create parent directories if they don't exist
        webp_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Open and convert image
        with Image.open(img_path) as img:
            # Resize if needed
            width, height = img.size
            resize_needed = False
            scale_factor = 1.0
            
            # Check if we need to resize based on max width
            if max_width > 0 and width > max_width:
                scale_factor = min(scale_factor, max_width / width)
                resize_needed = True
            
            # Check if we need to resize based on max height
            if max_height > 0 and height > max_height:
                scale_factor = min(scale_factor, max_height / height)
                resize_needed = True
            
            # Apply resize if needed
            if resize_needed:
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Save as WebP
            img.save(webp_path, 'WEBP', quality=quality)
        
        return (img_path, webp_path, True, None)
    except Exception as e:
        return (img_path, webp_path, False, str(e))


def convert_to_webp(extract_dir, output_dir, quality, max_width=0, max_height=0, num_threads=0, logger=None):
    """Convert all images in extract_dir to WebP format and save to output_dir."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    source_files = []
    
    # Find all image files in extract_dir and its subdirectories
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if Path(file).suffix.lower() in image_extensions:
                source_files.append(Path(root) / file)
    
    # Sort files to maintain order
    source_files.sort()
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate default number of threads
    if num_threads <= 0:
        num_threads = multiprocessing.cpu_count()
    
    logger.info(f"Converting {len(source_files)} images to WebP format using {num_threads} threads...")
    
    # Prepare arguments for parallel processing
    conversion_args = []
    for img_path in source_files:
        # Use relative path for output, preserving directory structure
        rel_path = img_path.relative_to(extract_dir)
        webp_path = output_dir / rel_path.with_suffix('.webp')
        conversion_args.append((img_path, webp_path, quality, max_width, max_height))
    
    # Process images in parallel
    success_count = 0
    with ProcessPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(convert_single_image, args) for args in conversion_args]
        
        for i, future in enumerate(as_completed(futures), 1):
            img_path, webp_path, success, error = future.result()
            rel_path = img_path.relative_to(extract_dir)
            
            if success:
                logger.debug(f"[{i}/{len(source_files)}] Converted: {rel_path} -> {webp_path.name}")
                success_count += 1
            else:
                logger.error(f"Error converting {rel_path}: {error}")
    
    logger.info(f"Successfully converted {success_count}/{len(source_files)} images")
    return output_dir


def process_single_file(input_file, output_dir, quality, max_width, max_height, no_cbz, keep_originals, num_threads, logger):
    """Process a single CBZ/CBR file."""
    # Create a file-specific output directory
    file_output_dir = output_dir / input_file.stem
    
    # Get original file size
    original_size_formatted, original_size_bytes = get_file_size_formatted(input_file)
    
    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Extract archive
            extract_archive(input_file, temp_path, logger)
            
            # Convert images to WebP
            convert_to_webp(temp_path, file_output_dir, quality, max_width, max_height, num_threads, logger)
            
            # Create CBZ unless --no-cbz is specified
            if not no_cbz:
                cbz_output = output_dir / f"{input_file.stem}.cbz"
                create_cbz(file_output_dir, cbz_output, logger)
                
                # Get new file size and calculate savings
                new_size_formatted, new_size_bytes = get_file_size_formatted(cbz_output)
                size_diff_bytes = original_size_bytes - new_size_bytes
                
                if original_size_bytes > 0:
                    percentage_saved = (size_diff_bytes / original_size_bytes) * 100
                    size_diff_formatted, _ = get_file_size_formatted(size_diff_bytes)
                    
                    # Print compression report
                    logger.info(f"Compression Report for {input_file.name}:")
                    logger.info(f"  Original size: {original_size_formatted}")
                    logger.info(f"  New size: {new_size_formatted}")
                    
                    if size_diff_bytes > 0:
                        logger.info(f"  Space saved: {size_diff_formatted} ({percentage_saved:.1f}%)")
                    else:
                        logger.info(f"  Space increased: {abs(size_diff_formatted)} " +
                                  f"({abs(percentage_saved):.1f}% larger)")
                
                # Delete the extracted files if --keep-originals is not specified
                if not keep_originals:
                    shutil.rmtree(file_output_dir)
                    logger.debug(f"Removed extracted files from {file_output_dir}")
            
            logger.info(f"Conversion of {input_file.name} completed successfully!")
            return True, original_size_bytes, new_size_bytes if not no_cbz else 0
            
        except Exception as e:
            logger.error(f"Error processing {input_file}: {e}")
            return False, original_size_bytes, 0


def process_archive_files(archives, output_dir, args, logger):
    """Process multiple archive files sequentially, using all available threads for each file."""
    total_original_size = 0
    total_new_size = 0
    processed_files = []
    
    # Process archives sequentially (but use all threads for each file)
    success_count = 0
    for i, archive in enumerate(archives, 1):
        logger.info(f"\n[{i}/{len(archives)}] Processing: {archive}")
        success, original_size, new_size = process_single_file(
            archive, 
            output_dir,
            args.quality, 
            args.max_width, 
            args.max_height,
            args.no_cbz, 
            args.keep_originals,
            args.threads,  # Use all available threads for each file
            logger
        )
        if success:
            success_count += 1
            total_original_size += original_size
            total_new_size += new_size
            processed_files.append((archive.name, original_size, new_size))
    
    return success_count, total_original_size, total_new_size, processed_files
