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
    sharp_yuv = options.get('sharp_yuv', False)
    preprocessing = options.get('preprocessing')
    lossless = options.get('lossless', False)
    auto_optimize = options.get('auto_optimize', False)
    
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

            # Advanced WebP parameters
            webp_options = {
                'quality': quality,
                'method': method,
                'lossless': lossless,
            }
            
            # Add sharp_yuv option for better text rendering if specified
            if sharp_yuv:
                webp_options['sharp_yuv'] = True
            
            # Auto-optimize: try both lossy and lossless, use smaller file
            if auto_optimize and not lossless:
                import tempfile
                temp_dir = tempfile.gettempdir()
                lossy_path = Path(temp_dir) / f"lossy_{webp_path.name}"
                lossless_path = Path(temp_dir) / f"lossless_{webp_path.name}"
                
                # Save lossy version
                lossy_options = webp_options.copy()
                lossy_options['lossless'] = False
                img.save(lossy_path, 'WEBP', **lossy_options)
                
                # Save lossless version
                lossless_options = webp_options.copy()
                lossless_options['lossless'] = True
                if 'quality' in lossless_options:
                    del lossless_options['quality']  # Lossless doesn't use quality
                img.save(lossless_path, 'WEBP', **lossless_options)
                
                # Compare sizes and use the smaller one
                lossy_size = lossy_path.stat().st_size
                lossless_size = lossless_path.stat().st_size
                
                if lossy_size <= lossless_size:
                    # Lossy is smaller or equal, use it
                    shutil.copy2(lossy_path, webp_path)
                else:
                    # Lossless is smaller, use it
                    shutil.copy2(lossless_path, webp_path)
                
                # Clean up temp files
                try:
                    lossy_path.unlink()
                    lossless_path.unlink()
                except Exception:
                    pass  # Ignore cleanup errors
            else:
                # Standard saving with specified options
                img.save(webp_path, 'WEBP', **webp_options)

        return (img_path, webp_path, True, None)
    except Exception as e:
        return (img_path, webp_path, False, str(e))


def convert_to_webp(extract_dir, output_dir, quality, max_width=0, max_height=0, 
               num_threads=0, method=4, sharp_yuv=False, preprocessing=None, 
               lossless=False, auto_optimize=False, logger=None):
    """Convert all images in extract_dir to WebP format, saving to output_dir with optimized parameters."""
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    source_files = []

    for root, _, files in os.walk(extract_dir):
        for file in files:
            if Path(file).suffix.lower() in image_exts:
                source_files.append(Path(root) / file)

    source_files.sort()
    output_dir.mkdir(parents=True, exist_ok=True)

    if num_threads <= 0:
        num_threads = multiprocessing.cpu_count()

    logger.info(f"Converting {len(source_files)} images to WebP using {num_threads} threads...")
    logger.info(f"WebP parameters: quality={quality}, method={method}, sharp_yuv={sharp_yuv}, "
               f"preprocessing={preprocessing}, lossless={lossless}, auto_optimize={auto_optimize}")

    # Package options for each image
    conversion_args = []
    for img_path in source_files:
        rel_path = img_path.relative_to(extract_dir)
        webp_path = output_dir / rel_path.with_suffix('.webp')
        
        # Create options dictionary for this image
        options = {
            'quality': quality,
            'max_width': max_width,
            'max_height': max_height,
            'method': method,
            'sharp_yuv': sharp_yuv,
            'preprocessing': preprocessing,
            'lossless': lossless,
            'auto_optimize': auto_optimize
        }
        
        conversion_args.append((img_path, webp_path, options))

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
                        f"[{i}/{len(source_files)}] Converted: {img_path.name} -> {webp_path.name} "
                        f"({savings_pct:.1f}% smaller, {orig_size/1024:.1f}KB → {webp_size/1024:.1f}KB)"
                    )
                except Exception as e:
                    logger.debug(f"[{i}/{len(source_files)}] Converted: {img_path.name} -> {webp_path.name}")
                    logger.debug(f"Error calculating file size: {e}")
                    success_count += 1
            else:
                logger.error(f"Error converting {img_path.name}: {error}")

    # Report overall compression ratio
    if total_orig_size > 0:
        overall_savings = (1 - total_webp_size / total_orig_size) * 100
        logger.info(f"Successfully converted {success_count}/{len(source_files)} images.")
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
    sharp_yuv=True,        # Better text rendering by default
    preprocessing=None,    # Optional preprocessing
    zip_compresslevel=9,   # Maximum ZIP compression by default
    lossless=False,        # Use lossy by default
    auto_optimize=False    # Don't auto-optimize by default
):
    """Process a single CBZ/CBR file with optimized parameters from presets."""
    from .utils import get_file_size_formatted

    file_output_dir = output_dir / input_file.stem
    orig_size_str, orig_size_bytes = get_file_size_formatted(input_file)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        try:
            extract_archive(input_file, temp_path, logger)
            convert_to_webp(
                temp_path, 
                file_output_dir, 
                quality, 
                max_width, 
                max_height, 
                num_threads, 
                method,
                sharp_yuv,
                preprocessing,
                lossless,
                auto_optimize,
                logger
            )

            if not no_cbz:
                cbz_output = output_dir / f"{input_file.stem}.cbz"
                # If using pipelined approach
                if packaging_queue is not None:
                    result_dict = {"success": False, "new_size": 0}
                    # Include the compression level in the queue item
                    packaging_queue.put((file_output_dir, cbz_output, input_file, result_dict, zip_compresslevel))
                    logger.info(f"Queued {input_file.name} for packaging")
                    return True, orig_size_bytes, result_dict
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

            logger.info(f"Conversion of {input_file.name} completed successfully!")
            return True, orig_size_bytes, 0 if no_cbz else new_size_bytes

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
    sharp_yuv = args.sharp_yuv
    preprocessing = args.preprocessing
    zip_compression = args.zip_compression
    lossless = args.lossless
    auto_optimize = args.auto_optimize
    
    # Report which parameters we're using
    logger.info(f"Processing with parameters: method={method}, sharp_yuv={sharp_yuv}, "
               f"preprocessing={preprocessing}, zip_compression={zip_compression}, "
               f"lossless={lossless}, auto_optimize={auto_optimize}")

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
            success, orig_size, result_dict = process_single_file(
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
                sharp_yuv=sharp_yuv,
                preprocessing=preprocessing,
                zip_compresslevel=zip_compression,
                lossless=lossless,
                auto_optimize=auto_optimize
            )
            if success:
                success_count += 1
                total_original_size += orig_size
                result_dicts.append((archive.name, orig_size, result_dict))

        # Send sentinel to stop packager
        packaging_queue.put(None)
        packaging_queue.join()
        packaging_thread.join()

        # Gather results
        for filename, orig_size, rd in result_dicts:
            if rd["success"]:
                new_sz = rd["new_size"]
                total_new_size += new_sz
                processed_files.append((filename, orig_size, new_sz))

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
                sharp_yuv=sharp_yuv,
                preprocessing=preprocessing,
                zip_compresslevel=zip_compression,
                lossless=lossless,
                auto_optimize=auto_optimize
            )
            if success:
                success_count += 1
                total_original_size += orig_size
                total_new_size += new_sz
                processed_files.append((archive.name, orig_size, new_sz))

    return success_count, total_original_size, total_new_size, processed_files
