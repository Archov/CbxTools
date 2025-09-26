#!/usr/bin/env python3
"""
Watch mode logic for CBZ/CBR/CB7 to WebP converter.
Now uses consolidated utilities.
"""

import time
import json
import datetime
import multiprocessing
import queue
import threading
import sys 
from pathlib import Path

from .archives import find_comic_archives, is_image_file
from .core.archive_handler import ArchiveHandler
from .core.image_analyzer import ImageAnalyzer
from .core.filesystem_utils import FileSystemUtils
from .core.packaging_worker import WatchModePackagingWorker
from .conversion import process_single_file, convert_single_image, convert_to_webp
from .stats_tracker import print_lifetime_stats


def find_all_watchable_items(directory, recursive=False):
    """Find all items that can be watched and processed (archives, images, and image folders)."""
    items = []
    
    # Find archives
    archives = find_comic_archives(directory, recursive)
    items.extend(archives)
    
    # Find individual images in the root directory
    if directory.is_dir():
        direct_images = [f for f in directory.iterdir() if f.is_file() and ImageAnalyzer.is_image_file(f)]
        items.extend(direct_images)
    
    # Find image folders
    if recursive:
        import os
        for root, dirs, files in os.walk(directory):
            root_path = Path(root)
            # Skip the input directory itself (we handled direct images above)
            if root_path == directory:
                continue
            
            # Check if this directory contains images but no archives
            has_images = any(ImageAnalyzer.is_image_file(Path(root) / f) for f in files)
            has_archives = any(ArchiveHandler.is_supported_archive(Path(root) / f) for f in files)
            
            if has_images and not has_archives:
                # This is an image-only directory
                items.append(root_path)
    else:
        # For non-recursive, check immediate subdirectories
        if directory.is_dir():
            for item in directory.iterdir():
                if item.is_dir():
                    try:
                        # Check if this subdirectory contains images but no archives
                        has_images = any(ImageAnalyzer.is_image_file(f) for f in item.iterdir() if f.is_file())
                        has_archives = any(ArchiveHandler.is_supported_archive(f) for f in item.iterdir() if f.is_file())
                        
                        if has_images and not has_archives:
                            items.append(item)
                    except PermissionError:
                        continue
    
    return sorted(set(items))


def cleanup_empty_directories(root_dir, logger):
    """Remove all empty directories under root_dir (bottom-up traversal)."""
    return FileSystemUtils.cleanup_empty_directories(root_dir, logger)


def detect_new_image_folders(input_dir, processed_items, recursive=False):
    """
    Detect new image folders that have been created or now contain enough images to process.
    This is more complex than just checking for new files since folders can be gradually filled.
    """
    current_folders = set()
    
    if recursive:
        import os
        for root, dirs, files in os.walk(input_dir):
            root_path = Path(root)
            if root_path == input_dir:
                continue
                
            # Check if this directory contains images but no archives
            has_images = any(ImageAnalyzer.is_image_file(Path(root) / f) for f in files)
            has_archives = any(ArchiveHandler.is_supported_archive(Path(root) / f) for f in files)
            
            if has_images and not has_archives:
                current_folders.add(root_path)
    else:
        # Check immediate subdirectories
        for item in input_dir.iterdir():
            if item.is_dir():
                try:
                    has_images = any(ImageAnalyzer.is_image_file(f) for f in item.iterdir() if f.is_file())
                    has_archives = any(ArchiveHandler.is_supported_archive(f) for f in item.iterdir() if f.is_file())
                    
                    if has_images and not has_archives:
                        current_folders.add(item)
                except PermissionError:
                    continue
    
    # Return folders that weren't processed before
    return current_folders - processed_items


def process_single_image_file(image_file, output_dir, args, logger):
    """Convert an individual image to WebP using convert_single_image."""
    options = {
        'quality': args.quality,
        'max_width': args.max_width,
        'max_height': args.max_height,
        'method': args.method,
        'preprocessing': args.preprocessing,
        'lossless': args.lossless,
        'grayscale': args.grayscale,
        'auto_contrast': args.auto_contrast,
        'auto_greyscale': getattr(args, 'auto_greyscale', False),
        'auto_greyscale_pixel_threshold': getattr(args, 'auto_greyscale_pixel_threshold', 16),
        'auto_greyscale_percent_threshold': getattr(args, 'auto_greyscale_percent_threshold', 0.01),
        'preserve_auto_greyscale_png': getattr(args, 'preserve_auto_greyscale_png', False),
        'output_dir': output_dir,
        'verbose': args.verbose,
    }

    webp_output = output_dir / f"{image_file.stem}.webp"
    try:
        _, _, success, error, _ = convert_single_image((image_file, webp_output, options))
        if success:
            orig_size = image_file.stat().st_size
            new_size = webp_output.stat().st_size
            logger.info(f"Converted image: {image_file.name}")
            return True, orig_size, new_size
        else:
            logger.error(f"Error converting {image_file}: {error}")
            return False, 0, 0
    except (IOError, OSError, ValueError) as e:
        logger.exception(f"Error processing {image_file}: {e}")
        return False, 0, 0
    except Exception as e:
        logger.exception(f"Unexpected error processing {image_file}: {e}")
        return False, 0, 0


def process_image_directory(image_dir, output_dir, args, logger, packaging_queue=None):
    """Convert an image directory using convert_to_webp and optionally package."""
    import shutil

    file_output_dir = output_dir / image_dir.name

    try:
        convert_to_webp(
            image_dir,
            file_output_dir,
            args.quality,
            args.max_width,
            args.max_height,
            args.threads,
            args.method,
            args.preprocessing,
            args.lossless,
            logger,
            args.grayscale,
            args.auto_contrast,
            getattr(args, 'auto_greyscale', False),
            getattr(args, 'auto_greyscale_pixel_threshold', 16),
            getattr(args, 'auto_greyscale_percent_threshold', 0.01),
            getattr(args, 'preserve_auto_greyscale_png', False),
            verbose=args.verbose,
        )

        orig_size = sum(f.stat().st_size for f in image_dir.rglob('*') if f.is_file())

        if not args.no_cbz:
            cbz_output = output_dir / f"{image_dir.name}.cbz"
            if packaging_queue is not None:
                result_dict = {"success": False, "new_size": 0}
                packaging_queue.put((file_output_dir, cbz_output, image_dir, result_dict, args.zip_compression))
                logger.info(f"Queued {image_dir.name} for packaging")
                return True, orig_size, 0
            else:
                from .archives import create_cbz
                create_cbz(file_output_dir, cbz_output, logger, args.zip_compression)
                new_size = cbz_output.stat().st_size
                if not args.keep_originals:
                    shutil.rmtree(file_output_dir)
                logger.info(f"Converted folder: {image_dir.name}")
                return True, orig_size, new_size
        else:
            new_size = sum(f.stat().st_size for f in file_output_dir.rglob('*') if f.is_file())
            logger.info(f"Converted folder: {image_dir.name}")
            return True, orig_size, new_size

    except (IOError, OSError, ValueError) as e:
        logger.exception(f"Error processing folder {image_dir}: {e}")
        return False, 0, 0
    except Exception as e:
        logger.exception(f"Unexpected error processing folder {image_dir}: {e}")
        return False, 0, 0


def watch_directory(input_dir, output_dir, args, logger, stats_tracker=None):
    """
    Watch a directory for new CBZ/CBR/CB7 files, images, and image folders and process them.
    Updates lifetime statistics when files are processed.
    Supports recursive monitoring and preserves directory structure.
    
    Args:
        input_dir: Directory to watch for new files
        output_dir: Directory to output processed files
        args: Command line arguments
        logger: Logger instance
        stats_tracker: Optional StatsTracker instance for lifetime stats
    """
    
    history_file = output_dir / '.cbx_webp_processed_files.json'
    logger.info(f"Watching directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Checking every {args.watch_interval} seconds")
    logger.info(f"Recursive mode: {'enabled' if args.recursive else 'disabled'}")
    logger.info(f"Using history file: {history_file}")
    logger.info("Now watching for: archives (CBZ/CBR/CB7), individual images, and image folders")
    
    # Clean up any pre-existing empty directories if delete_originals is enabled
    if args.delete_originals and args.recursive:
        logger.info("Checking for pre-existing empty directories...")
        cleanup_empty_directories(input_dir, logger)
    
    # Track whether statistics are enabled
    stats_enabled = stats_tracker is not None
    if stats_enabled:
        logger.info("Lifetime statistics tracking is enabled")
    else:
        logger.info("Lifetime statistics tracking is disabled")
    
    # Log the effective parameters being used
    logger.info(f"Using parameters: quality={args.quality}, max_width={args.max_width}, "
               f"max_height={args.max_height}, method={args.method}, "
               f"preprocessing={args.preprocessing}, "
               f"zip_compression={args.zip_compression}, lossless={args.lossless}")
    if args.grayscale:
        logger.info(f"Image transformations: grayscale={args.grayscale}")
    if args.auto_contrast:
        logger.info(f"Image transformations: auto_contrast={args.auto_contrast}")
    if getattr(args, 'auto_greyscale', False):
        pixel_thresh = getattr(args, 'auto_greyscale_pixel_threshold', 16)
        percent_thresh = getattr(args, 'auto_greyscale_percent_threshold', 0.01)
        logger.info(
            "Image transformations: auto_greyscale=%s (pixel_threshold=%s, percent_threshold=%s)"
            % (args.auto_greyscale, pixel_thresh, percent_thresh)
        )
    logger.info("Press Ctrl+C to stop watching")

    processed_files = set()
    pending_results = {}  # Track files that are being processed

    # Load history file if it exists
    if history_file.exists():
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                processed_paths = history_data.get('processed_files', [])
                processed_files = set(Path(p) for p in processed_paths)
                logger.info(f"Loaded {len(processed_files)} previously processed items from history")
        except Exception as e:
            logger.error(f"Error loading history file: {e}")
            logger.info("Starting with empty history")

    def save_history():
        """Save the processed files to the history file."""
        try:
            history_data = {
                'processed_files': [str(p) for p in processed_files],
                'last_updated': datetime.datetime.now().isoformat()
            }
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2)
            logger.debug(f"Saved {len(processed_files)} processed items to history")
        except Exception as e:
            logger.error(f"Error saving history file: {e}")

    # Result queue for stats tracking
    result_queue = queue.Queue()
    
    # Set up a dedicated packaging queue and thread if we are creating CBZ files
    packaging_queue = None
    packaging_thread = None

    if not args.no_cbz:
        packaging_queue = queue.Queue()

        # Modified packaging worker that puts results in our result queue
        def enhanced_packaging_worker(packaging_queue, result_queue, logger, keep_originals):
            """Start a packaging worker with an enhanced loop for watch mode."""
            worker = WatchModePackagingWorker(logger, keep_originals, result_queue)

            def _enhanced_worker_loop(packaging_queue):
                """Enhanced worker loop implementation."""
                while True:
                    item = packaging_queue.get()
                    if item is None:  # sentinel
                        packaging_queue.task_done()
                        break

                    if len(item) >= 5:
                        file_output_dir, cbz_output, input_file, result_dict, zip_compresslevel = item
                    else:
                        file_output_dir, cbz_output, input_file, result_dict = item
                        zip_compresslevel = 9

                    success, new_size = worker.package_single(
                        file_output_dir, cbz_output, input_file, zip_compresslevel
                    )

                    result_dict["success"] = success
                    result_dict["new_size"] = new_size

                    # Put the result in our queue for stats tracking
                    if worker.result_queue:
                        worker.result_queue.put({
                            "file": input_file,
                            "success": success,
                            "new_size": new_size,
                        })

                    packaging_queue.task_done()

            # Attach the enhanced loop to the worker
            worker._enhanced_worker_loop = _enhanced_worker_loop
            worker._worker_loop = lambda: worker._enhanced_worker_loop(packaging_queue)
            worker._enhanced_worker_loop(packaging_queue)
        
        # Start the enhanced packaging worker
        packaging_thread = threading.Thread(
            target=enhanced_packaging_worker,
            args=(packaging_queue, result_queue, logger, args.keep_originals),
            daemon=True
        )
        packaging_thread.start()

    # Reserve 1 thread for packaging, use (threads - 1) for image conversion
    if args.threads > 0:
        conversion_threads = max(1, args.threads - 1)
    else:
        conversion_threads = max(1, multiprocessing.cpu_count() - 1)

    # Statistics to track during this watch session
    session_start_time = time.time()
    session_files_processed = 0
    session_original_size = 0
    session_new_size = 0
    
    try:
        while True:
            # Check for completed results from packaging
            completed_files = 0
            total_original_size = 0
            total_new_size = 0
            
            # Process all available results without blocking
            while not result_queue.empty():
                try:
                    result = result_queue.get_nowait()
                    input_file = result["file"]
                    
                    if result["success"] and input_file in pending_results:
                        original_size = pending_results[input_file]
                        new_size = result["new_size"]
                        
                        # Update session stats
                        session_files_processed += 1
                        session_original_size += original_size
                        session_new_size += new_size
                        
                        # Update batch stats
                        completed_files += 1
                        total_original_size += original_size
                        total_new_size += new_size
                        
                        # Remove from pending
                        del pending_results[input_file]
                        
                        # Mark task as done
                        result_queue.task_done()
                except queue.Empty:
                    break
            
            # Update lifetime stats if any files were completed
            if completed_files > 0 and stats_enabled:
                stats_tracker.add_run(
                    completed_files,
                    total_original_size,
                    total_new_size,
                    0  # Execution time not relevant for stats tracking in watch mode
                )
                print_lifetime_stats(stats_tracker, logger)
                logger.info(f"Session summary: Processed {session_files_processed} items, "
                           f"saved {(session_original_size - session_new_size) / (1024*1024):.2f}MB")
            
            # Check for new items to process
            new_items = find_all_watchable_items(input_dir, recursive=args.recursive)
            unprocessed_items = [item for item in new_items if item not in processed_files]

            if unprocessed_items:
                logger.info(f"Found {len(unprocessed_items)} new item(s) to process")

                for item in unprocessed_items:
                    # Determine the relative path structure to preserve
                    if item.is_dir():
                        rel_path = item.parent.relative_to(input_dir)
                        logger.info(f"Processing image folder: {item}")
                    else:
                        rel_path = item.parent.relative_to(input_dir)
                        logger.info(f"Processing: {item}")

                    target_output_dir = output_dir / rel_path
                    target_output_dir.mkdir(parents=True, exist_ok=True)

                    logger.debug(f"Output directory: {target_output_dir}")

                    if item.is_file() and ArchiveHandler.is_supported_archive(item):
                        success, original_size, result = process_single_file(
                            input_file=item,
                            output_dir=target_output_dir,
                            quality=args.quality,
                            max_width=args.max_width,
                            max_height=args.max_height,
                            no_cbz=args.no_cbz,
                            keep_originals=args.keep_originals,
                            num_threads=conversion_threads,
                            logger=logger,
                            packaging_queue=packaging_queue,
                            method=args.method,
                            preprocessing=args.preprocessing,
                            zip_compresslevel=args.zip_compression,
                            lossless=args.lossless,
                            grayscale=args.grayscale,
                            auto_contrast=args.auto_contrast,
                            auto_greyscale=getattr(args, 'auto_greyscale', False),
                            auto_greyscale_pixel_threshold=getattr(
                                args,
                                'auto_greyscale_pixel_threshold',
                                16,
                            ),
                            auto_greyscale_percent_threshold=getattr(
                                args,
                                'auto_greyscale_percent_threshold',
                                0.01,
                            ),
                            verbose=args.verbose,
                        )
                    elif item.is_file() and ImageAnalyzer.is_image_file(item):
                        success, original_size, result = process_single_image_file(
                            item,
                            target_output_dir,
                            args,
                            logger,
                        )
                    elif item.is_dir():
                        success, original_size, result = process_image_directory(
                            item,
                            target_output_dir,
                            args,
                            logger,
                            packaging_queue=packaging_queue,
                        )
                    else:
                        logger.warning(f"Unsupported item: {item}")
                        processed_files.add(item)
                        save_history()
                        continue

                    if success:
                        # Handle direct result vs async result
                        if not args.no_cbz and not is_image_file(item):
                            # Track the pending result for later statistics update (archives and folders)
                            pending_results[item] = original_size
                        else:
                            # Direct result for no_cbz or individual images - update stats immediately
                            session_files_processed += 1
                            session_original_size += original_size
                            session_new_size += result if isinstance(result, (int, float)) else 0
                            
                            # Update lifetime stats for no_cbz results
                            if stats_enabled:
                                stats_tracker.add_run(
                                    1,
                                    original_size,
                                    result if isinstance(result, (int, float)) else 0,
                                    0  # Execution time not relevant for stats tracking in watch mode
                                )
                                print_lifetime_stats(stats_tracker, logger)
                        
                        processed_files.add(item)
                        save_history()

                        if args.delete_originals:
                            try:
                                if item.is_file():
                                    # Delete the original file
                                    item.unlink()
                                    logger.info(f"Deleted original file: {item}")
                                    
                                    # Check if parent directory is now empty and remove if it is
                                    FileSystemUtils.remove_empty_dirs(item.parent, input_dir, logger)
                                elif item.is_dir():
                                    # Delete the original image folder
                                    import shutil
                                    shutil.rmtree(item)
                                    logger.info(f"Deleted original folder: {item}")
                                    
                                    # Check if parent directory is now empty and remove if it is
                                    FileSystemUtils.remove_empty_dirs(item.parent, input_dir, logger)
                            except Exception as e:
                                logger.error(f"Error deleting {item}: {e}")
                    else:
                        logger.error(f"Failed to process {item}")

            # Sleep before next check
            time.sleep(args.watch_interval)

    except KeyboardInterrupt:
        logger.info("\nWatch mode stopped by user.")
    except Exception as e:
        logger.error(f"Error in watch mode: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Wait for all pending operations to complete
        if packaging_queue is not None:
            # Add sentinel to stop the packaging thread
            packaging_queue.put(None)
            
            # Wait for packaging to complete
            logger.info("Waiting for packaging to complete...")
            packaging_queue.join()
            if packaging_thread is not None:
                packaging_thread.join(timeout=10)
            
            # Process any remaining results
            try:
                while not result_queue.empty():
                    result = result_queue.get_nowait()
                    input_file = result["file"]
                    
                    if result["success"] and input_file in pending_results:
                        original_size = pending_results[input_file]
                        new_size = result["new_size"]
                        
                        # Update session stats
                        session_files_processed += 1
                        session_original_size += original_size
                        session_new_size += new_size
                        
                        # Remove from pending
                        del pending_results[input_file]
                        
                        # Update lifetime stats for the final batch
                        if stats_enabled:
                            stats_tracker.add_run(
                                1,
                                original_size,
                                new_size,
                                0  # Execution time not relevant for stats tracking in watch mode
                            )
                    
                    result_queue.task_done()
            except queue.Empty:
                pass
        
        # Final statistics update
        if stats_enabled and session_files_processed > 0:
            session_execution_time = time.time() - session_start_time
            logger.info(f"\nWatch session summary:")
            logger.info(f"Total items processed: {session_files_processed}")
            logger.info(f"Total session time: {session_execution_time/60:.1f} minutes")
            logger.info(f"Total space saved: {(session_original_size - session_new_size) / (1024*1024):.2f}MB")
            print_lifetime_stats(stats_tracker, logger)
            
        save_history()
        logger.info("Watch mode terminated")

    return 0