#!/usr/bin/env python3
"""
Image conversion functions for CBZ/CBR to WebP converter with optimized parallel processing.
"""

import os
import shutil
import tempfile
import multiprocessing
from pathlib import Path
from PIL import Image
import queue
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from .utils import get_file_size_formatted
from .archives import extract_archive, create_cbz


def convert_single_image(args):
    """Convert a single image to WebP format with optimized parameters. Runs in a separate process."""
    img_path, webp_path, options = args
    
    # Unpack options
    quality = options.get('quality', 80)
    max_width = options.get('max_width', 0)
    max_height = options.get('max_height', 0)
    method = options.get('method', 4)
    preprocessing = options.get('preprocessing')
    lossless = options.get('lossless', False)
    
    try:
        webp_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(img_path) as img:
            # Check if image needs to be converted from CMYK or other modes
            if img.mode not in ('RGB', 'RGBA', 'L', 'LA'):
                img = img.convert('RGB')
                
            # Resize if needed
            width, height = img.size
            scale_factor = 1.0

            if max_width > 0 and width > max_width:
                scale_factor = min(scale_factor, max_width / width)
            if max_height > 0 and height > max_height:
                scale_factor = min(scale_factor, max_height / height)

            if scale_factor < 1.0:
                new_w = int(width * scale_factor)
                new_h = int(height * scale_factor)
                img = img.resize((new_w, new_h), Image.LANCZOS)
            
            # Apply preprocessing if requested
            if preprocessing == 'unsharp_mask':
                try:
                    from PIL import ImageFilter
                    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=50, threshold=3))
                except (ImportError, AttributeError):
                    pass  # Skip if not available
            elif preprocessing == 'reduce_noise':
                try:
                    from PIL import ImageFilter
                    # Apply slight blur to reduce noise, then sharpen for detail
                    blurred = img.filter(ImageFilter.GaussianBlur(radius=0.5))
                    img = Image.blend(img, blurred, 0.1).filter(ImageFilter.SHARPEN)
                except (ImportError, AttributeError):
                    pass  # Skip if not available

            # WebP parameters
            webp_options = {
                'quality': quality,
                'method': method,
                'lossless': lossless,
            }
            
            # Standard saving with specified options
            img.save(webp_path, 'WEBP', **webp_options)

        return (img_path, webp_path, True, None)
    except Exception as e:
        return (img_path, webp_path, False, str(e))


def convert_to_webp(extract_dir, output_dir, quality, max_width=0, max_height=0, 
               num_threads=0, method=4, preprocessing=None, 
               lossless=False, logger=None):
    """Convert all images in extract_dir to WebP format and copy all non-image files to output_dir."""
    import os
    import shutil
    from pathlib import Path
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor, as_completed
    
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    image_files = []
    non_image_files = []

    for root, _, files in os.walk(extract_dir):
        for file in files:
            file_path = Path(root) / file
            if Path(file).suffix.lower() in image_exts:
                image_files.append(file_path)
            else:
                non_image_files.append(file_path)

    image_files.sort()
    non_image_files.sort()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process non-image files first - simply copy them to output directory
    copied_count = 0
    for file_path in non_image_files:
        rel_path = file_path.relative_to(extract_dir)
        output_path = output_dir / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, output_path)
        copied_count += 1

    if copied_count > 0:
        logger.info(f"Copied {copied_count} non-image files to preserve metadata and auxiliary content")

    # Continue with image conversion as before
    if num_threads <= 0:
        num_threads = multiprocessing.cpu_count()

    logger.info(f"Converting {len(image_files)} images to WebP using {num_threads} threads...")
    logger.info(f"WebP parameters: quality={quality}, method={method}, "
               f"preprocessing={preprocessing}, lossless={lossless}")

    # Package options for each image
    conversion_args = []
    for img_path in image_files:
        rel_path = img_path.relative_to(extract_dir)
        webp_path = output_dir / rel_path.with_suffix('.webp')
        
        # Create options dictionary for this image
        options = {
            'quality': quality,
            'max_width': max_width,
            'max_height': max_height,
            'method': method,
            'preprocessing': preprocessing,
            'lossless': lossless
        }
        
        conversion_args.append((img_path, webp_path, options))

    # Rest of the function remains the same
    success_count = 0
    total_orig_size = 0
    total_webp_size = 0
    
    with ProcessPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(convert_single_image, args) for args in conversion_args]
        for i, fut in enumerate(as_completed(futures), 1):
            img_path, webp_path, success, error = fut.result()
            if success:
                # Calculate compression ratio for reporting
                try:
                    orig_size = img_path.stat().st_size
                    webp_size = webp_path.stat().st_size
                    total_orig_size += orig_size
                    total_webp_size += webp_size
                    
                    savings_pct = (1 - webp_size / orig_size) * 100 if orig_size > 0 else 0
                    
                    success_count += 1
                    logger.debug(
                        f"[{i}/{len(image_files)}] Converted: {img_path.name} -> {webp_path.name} "
                        f"({savings_pct:.1f}% smaller, {orig_size/1024:.1f}KB → {webp_size/1024:.1f}KB)"
                    )
                except Exception as e:
                    logger.debug(f"[{i}/{len(image_files)}] Converted: {img_path.name} -> {webp_path.name}")
                    logger.debug(f"Error calculating file size: {e}")
                    success_count += 1
            else:
                logger.error(f"Error converting {img_path.name}: {error}")

    # Report overall compression ratio
    if total_orig_size > 0:
        overall_savings = (1 - total_webp_size / total_orig_size) * 100
        logger.info(f"Successfully converted {success_count}/{len(image_files)} images.")
        logger.info(f"Overall image size reduction: {overall_savings:.1f}% " +
                   f"({total_orig_size / (1024*1024):.2f}MB → {total_webp_size / (1024*1024):.2f}MB)")
    
    return output_dir


def cbz_packaging_worker(packaging_queue, logger, keep_originals):
    """Worker function to package WebP images into CBZ files with optimized compression."""
    while True:
        item = packaging_queue.get()
        if item is None:  # sentinel
            packaging_queue.task_done()
            break

        # Check if we have the compression level parameter
        if len(item) >= 5:
            file_output_dir, cbz_output, input_file, result_dict, zip_compresslevel = item
        else:
            # Backward compatibility
            file_output_dir, cbz_output, input_file, result_dict = item
            zip_compresslevel = 9  # Default to maximum compression
        
        try:
            create_cbz(file_output_dir, cbz_output, logger, zip_compresslevel)
            _, new_size_bytes = get_file_size_formatted(cbz_output)
            result_dict["success"] = True
            result_dict["new_size"] = new_size_bytes

            if not keep_originals:
                shutil.rmtree(file_output_dir)
                logger.debug(f"Removed extracted files from {file_output_dir}")

            logger.info(f"Packaged {input_file.name} successfully")
        except Exception as e:
            logger.error(f"Error packaging {input_file.name}: {e}")
            result_dict["success"] = False

        packaging_queue.task_done()


def process_single_file(
    input_file,
    output_dir,
    quality,
    max_width,
    max_height,
    no_cbz,
    keep_originals,
    num_threads,
    logger,
    packaging_queue=None,
    method=6,              # Use higher compression method by default
    preprocessing=None,    # Optional preprocessing
    zip_compresslevel=9,   # Maximum ZIP compression by default
    lossless=False        # Use lossy by default
):
    """Process a single CBZ/CBR file with optimized parameters from presets."""
    from .utils import get_file_size_formatted
    import os
    import shutil
    import tempfile
    from pathlib import Path

    # Create file-specific output directory within the output_dir
    file_output_dir = output_dir / input_file.stem
    orig_size_str, orig_size_bytes = get_file_size_formatted(input_file)
    new_size_bytes = 0  # Default value

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        try:
            from .archives import extract_archive, create_cbz
            extract_archive(input_file, temp_path, logger)
            convert_to_webp(
                temp_path, 
                file_output_dir, 
                quality, 
                max_width, 
                max_height, 
                num_threads, 
                method,
                preprocessing,
                lossless,
                logger
            )

            if not no_cbz:
                # Create the CBZ file with the same name as input file but in output_dir
                cbz_output = output_dir / f"{input_file.stem}.cbz"
                # If using pipelined approach
                if packaging_queue is not None:
                    result_dict = {"success": False, "new_size": 0}
                    # Include the compression level in the queue item
                    packaging_queue.put((file_output_dir, cbz_output, input_file, result_dict, zip_compresslevel))
                    logger.info(f"Queued {input_file.name} for packaging")
                    # Return the orig_size_bytes and a placeholder for new_size
                    # The actual size will be determined by the packaging worker
                    logger.info(f"Conversion of {input_file.name} completed successfully!")
                    return True, orig_size_bytes, 0  # Return 0 for new_size, will be updated by worker
                else:
                    # Synchronous approach - use the compression level
                    create_cbz(file_output_dir, cbz_output, logger, zip_compresslevel)
                    new_size_str, new_size_bytes = get_file_size_formatted(cbz_output)
                    size_diff_bytes = orig_size_bytes - new_size_bytes

                    if orig_size_bytes > 0:
                        pct_saved = (size_diff_bytes / orig_size_bytes) * 100
                        diff_str, _ = get_file_size_formatted(abs(size_diff_bytes))
                        logger.info(f"Compression Report for {input_file.name}:")
                        logger.info(f"  Original size: {orig_size_str}")
                        logger.info(f"  New size: {new_size_str}")

                        if size_diff_bytes > 0:
                            logger.info(f"  Space saved: {diff_str} ({pct_saved:.1f}%)")
                        else:
                            logger.info(f"  Space increased: {diff_str} ({abs(pct_saved):.1f}% larger)")

                    if not keep_originals:
                        shutil.rmtree(file_output_dir)
                        logger.debug(f"Removed extracted files from {file_output_dir}")
            else:
                # For no_cbz mode, we still want to count the size of the extracted files
                # This is not perfect but provides an estimate
                new_size_bytes = sum(f.stat().st_size for f in file_output_dir.glob('**/*') if f.is_file())

            logger.info(f"Conversion of {input_file.name} completed successfully!")
            return True, orig_size_bytes, new_size_bytes

        except Exception as e:
            logger.error(f"Error processing {input_file}: {e}")
            return False, orig_size_bytes, 0
def process_archive_files(archives, output_dir, args, logger):
    """Process multiple archives with pipelining for improved performance."""
    total_original_size = 0
    total_new_size = 0
    processed_files = []

    # Extract all parameters from args
    method = args.method
    preprocessing = args.preprocessing
    zip_compression = args.zip_compression
    lossless = args.lossless
    
    # Report which parameters we're using
    logger.info(f"Processing with parameters: method={method}, "
               f"preprocessing={preprocessing}, zip_compression={zip_compression}, "
               f"lossless={lossless}")

    if not args.no_cbz and len(archives) > 1:
        logger.info(f"Processing {len(archives)} comics with pipelined approach...")
        # Reserve 1 thread for packaging, the rest for conversion
        conversion_threads = max(1, args.threads - 1) if args.threads > 0 else max(1, multiprocessing.cpu_count() - 1)
        packaging_queue = queue.Queue()
        packaging_thread = threading.Thread(
            target=cbz_packaging_worker,
            args=(packaging_queue, logger, args.keep_originals),
            daemon=True
        )
        packaging_thread.start()

        success_count = 0
        result_dicts = []

        for i, archive in enumerate(archives, 1):
            logger.info(f"\n[{i}/{len(archives)}] Processing: {archive}")
            success, orig_size, _ = process_single_file(
                input_file=archive,
                output_dir=output_dir,
                quality=args.quality,
                max_width=args.max_width,
                max_height=args.max_height,
                no_cbz=args.no_cbz,
                keep_originals=args.keep_originals,
                num_threads=conversion_threads,
                logger=logger,
                packaging_queue=packaging_queue,
                method=method,
                preprocessing=preprocessing,
                zip_compresslevel=zip_compression,
                lossless=lossless
            )
            if success:
                success_count += 1
                total_original_size += orig_size
                # We'll get the new_size from the result_dict later
                result_dicts.append((archive.name, orig_size))

        # Send sentinel to stop packager
        packaging_queue.put(None)
        packaging_queue.join()
        packaging_thread.join()

        # For pipelined approach, we don't have accurate size information yet
        # since packaging happens asynchronously
        logger.warning("Note: Size statistics may be incomplete for pipelined processing")
        processed_files = [(filename, orig_size, 0) for filename, orig_size in result_dicts]

    else:
        success_count = 0
        for i, archive in enumerate(archives, 1):
            logger.info(f"\n[{i}/{len(archives)}] Processing: {archive}")
            success, orig_size, new_sz = process_single_file(
                input_file=archive,
                output_dir=output_dir,
                quality=args.quality,
                max_width=args.max_width,
                max_height=args.max_height,
                no_cbz=args.no_cbz,
                keep_originals=args.keep_originals,
                num_threads=args.threads,
                logger=logger,
                method=method,
                preprocessing=preprocessing,
                zip_compresslevel=zip_compression,
                lossless=lossless
            )
            if success:
                success_count += 1
                total_original_size += orig_size
                total_new_size += new_sz
                processed_files.append((archive.name, orig_size, new_sz))

    return success_count, total_original_size, total_new_size, processed_files