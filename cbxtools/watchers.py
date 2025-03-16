#!/usr/bin/env python3
"""
Watch mode logic for CBZ/CBR to WebP converter.
Reserves one thread for CBZ packaging and uses the rest for image conversion.
Supports recursive directory watching and preserves source directory structure.
"""

import time
import json
import datetime
import multiprocessing
import queue
import threading
import sys 
from pathlib import Path

from .archives import find_comic_archives
from .conversion import process_single_file, cbz_packaging_worker
from .stats_tracker import print_lifetime_stats


def _remove_empty_dirs(directory, root_dir, logger):
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
    
    # Don't attempt to remove the root directory or any directory outside the root
    if directory == root_dir or not str(directory).startswith(str(root_dir)):
        return
    
    # Check if directory exists and is a directory
    if not directory.is_dir():
        return
    
    # Check if directory is empty
    if not any(directory.iterdir()):
        try:
            directory.rmdir()
            logger.info(f"Removed empty directory: {directory}")
            
            # Recursively check parent directories
            _remove_empty_dirs(directory.parent, root_dir, logger)
        except Exception as e:
            logger.error(f"Error removing directory {directory}: {e}")


def cleanup_empty_directories(root_dir, logger):
    """
    Remove all empty directories under root_dir (bottom-up traversal).
    
    Args:
        root_dir: The root directory to clean up
        logger: Logger instance for logging messages
    """
    import os
    
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
                logger.debug(f"Removed empty directory: {directory}")
            except Exception as e:
                logger.error(f"Error removing directory {directory}: {e}")
    
    if removed_count > 0:
        logger.info(f"Removed {removed_count} pre-existing empty directories")
    else:
        logger.info("No empty directories found")

def watch_directory(input_dir, output_dir, args, logger, stats_tracker=None):
    """
    Watch a directory for new CBZ/CBR files and process them with optimized parameters.
    Updates lifetime statistics when files are processed.
    Supports recursive monitoring and preserves directory structure.
    
    Args:
        input_dir: Directory to watch for new files
        output_dir: Directory to output processed files
        args: Command line arguments
        logger: Logger instance
        stats_tracker: Optional StatsTracker instance for lifetime stats
    """
    
    history_file = output_dir / '.cbz_webp_processed_files.json'
    logger.info(f"Watching directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Checking every {args.watch_interval} seconds")
    logger.info(f"Recursive mode: {'enabled' if args.recursive else 'disabled'}")
    logger.info(f"Using history file: {history_file}")
    
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
    logger.info("Press Ctrl+C to stop watching")

    processed_files = set()
    pending_results = {}  # Track files that are being processed

    # Load history file if it exists
    if history_file.exists():
        try:
            with open(history_file, 'r') as f:
                history_data = json.load(f)
                processed_paths = history_data.get('processed_files', [])
                processed_files = set(Path(p) for p in processed_paths)
                logger.info(f"Loaded {len(processed_files)} previously processed files from history")
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
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
            logger.debug(f"Saved {len(processed_files)} processed files to history")
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
                
                try:
                    from .archives import create_cbz
                    from .utils import get_file_size_formatted
                    
                    create_cbz(file_output_dir, cbz_output, logger, zip_compresslevel)
                    _, new_size_bytes = get_file_size_formatted(cbz_output)
                    result_dict["success"] = True
                    result_dict["new_size"] = new_size_bytes
                    
                    # Put the result in our queue for stats tracking
                    result_queue.put({
                        "file": input_file,
                        "success": True,
                        "new_size": new_size_bytes
                    })

                    if not keep_originals:
                        import shutil
                        shutil.rmtree(file_output_dir)
                        logger.debug(f"Removed extracted files from {file_output_dir}")

                    logger.info(f"Packaged {input_file.name} successfully")
                except Exception as e:
                    logger.error(f"Error packaging {input_file.name}: {e}")
                    result_dict["success"] = False
                    result_queue.put({
                        "file": input_file,
                        "success": False,
                        "new_size": 0
                    })

                packaging_queue.task_done()
        
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
                logger.info(f"Session summary: Processed {session_files_processed} files, "
                           f"saved {(session_original_size - session_new_size) / (1024*1024):.2f}MB")
            
            # Check for new files to process
            archives = find_comic_archives(input_dir, recursive=args.recursive)
            new_archives = [a for a in archives if a not in processed_files]

            if new_archives:
                logger.info(f"Found {len(new_archives)} new file(s) to process")

                for archive in new_archives:
                    # Determine the relative path structure to preserve
                    rel_path = archive.parent.relative_to(input_dir)
                    target_output_dir = output_dir / rel_path
                    target_output_dir.mkdir(parents=True, exist_ok=True)
                    
                    logger.info(f"Processing: {archive}")
                    logger.debug(f"Output directory: {target_output_dir}")

                    success, original_size, result = process_single_file(
                        input_file=archive,
                        output_dir=target_output_dir,  # Use the mirrored directory structure
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
                        lossless=args.lossless
                    )

                    if success:
                        # Handle direct result vs async result
                        if not args.no_cbz:
                            # Track the pending result for later statistics update
                            pending_results[archive] = original_size
                        else:
                            # Direct result for no_cbz - update stats immediately
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
                        
                        processed_files.add(archive)
                        save_history()

                        if args.delete_originals:
                            try:
                                # Delete the original file
                                archive.unlink()
                                logger.info(f"Deleted original file: {archive}")
                                
                                # Check if parent directory is now empty and remove if it is
                                _remove_empty_dirs(archive.parent, input_dir, logger)
                            except Exception as e:
                                logger.error(f"Error deleting file {archive}: {e}")
                    else:
                        logger.error(f"Failed to process {archive}")

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
            try:
                logger.info("Waiting for packaging to complete...")
                packaging_queue.join(timeout=10)
            except:
                pass  # Timeout is fine
            
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
            logger.info(f"Total files processed: {session_files_processed}")
            logger.info(f"Total session time: {session_execution_time/60:.1f} minutes")
            logger.info(f"Total space saved: {(session_original_size - session_new_size) / (1024*1024):.2f}MB")
            print_lifetime_stats(stats_tracker, logger)
            
        save_history()
        logger.info("Watch mode terminated")

    return 0
