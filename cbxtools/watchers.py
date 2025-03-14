#!/usr/bin/env python3
"""
Watch mode logic for CBZ/CBR to WebP converter.
Reserves one thread for CBZ packaging and uses the rest for image conversion.
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


def watch_directory(input_dir, output_dir, args, logger, stats_tracker=None):
    """
    Watch a directory for new CBZ/CBR files and process them with optimized parameters.
    Updates lifetime statistics when files are processed.
    
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
    logger.info(f"Using history file: {history_file}")
    
    # Track whether statistics are enabled
    stats_enabled = stats_tracker is not None
    if stats_enabled:
        logger.info("Lifetime statistics tracking is enabled")
    else:
        logger.info("Lifetime statistics tracking is disabled")
    
    # Log the effective parameters being used
    logger.info(f"Using parameters: quality={args.quality}, max_width={args.max_width}, "
               f"max_height={args.max_height}, method={args.method}, "
               f"sharp_yuv={args.sharp_yuv}, preprocessing={args.preprocessing}, "
               f"zip_compression={args.zip_compression}, lossless={args.lossless}, "
               f"auto_optimize={args.auto_optimize}")
    logger.info("Press Ctrl+C to stop watching")

    processed_files = set()

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

    # Set up a dedicated packaging queue and thread if we are creating CBZ files
    packaging_queue = None
    packaging_thread = None

    if not args.no_cbz:
        packaging_queue = queue.Queue()
        packaging_thread = threading.Thread(
            target=cbz_packaging_worker,
            args=(packaging_queue, logger, args.keep_originals),
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
    batch_start_time = time.time()
    total_files_processed = 0
    total_original_size = 0
    total_new_size = 0
    batch_files_processed = 0
    batch_original_size = 0
    batch_new_size = 0
    
    # Store results from async tasks
    async_results = {}

    try:
        while True:
            archives = find_comic_archives(input_dir, recursive=False)
            new_archives = [a for a in archives if a not in processed_files]

            if new_archives:
                logger.info(f"Found {len(new_archives)} new file(s) to process")
                batch_start_time = time.time()  # Reset batch timer
                batch_files_processed = 0
                batch_original_size = 0
                batch_new_size = 0

                for archive in new_archives:
                    logger.info(f"Processing: {archive}")

                    success, original_size, result = process_single_file(
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
                        method=args.method,
                        sharp_yuv=args.sharp_yuv,
                        preprocessing=args.preprocessing,
                        zip_compresslevel=args.zip_compression,
                        lossless=args.lossless,
                        auto_optimize=args.auto_optimize
                    )

                    if success:
                        # Store async results for CBZ packaging
                        if isinstance(result, dict) and not args.no_cbz:
                            async_results[archive] = {
                                "result_dict": result,
                                "original_size": original_size
                            }
                        else:
                            # Direct result for no_cbz or sync mode
                            total_original_size += original_size
                            total_new_size += result if isinstance(result, (int, float)) else 0
                            total_files_processed += 1
                            batch_original_size += original_size
                            batch_new_size += result if isinstance(result, (int, float)) else 0
                            batch_files_processed += 1
                        
                        processed_files.add(archive)
                        save_history()

                        if args.delete_originals:
                            try:
                                archive.unlink()
                                logger.info(f"Deleted original file: {archive}")
                            except Exception as e:
                                logger.error(f"Error deleting file {archive}: {e}")
                    else:
                        logger.error(f"Failed to process {archive}")
                
                # Check for completed async tasks
                completed_archives = []
                for archive, data in async_results.items():
                    result_dict = data["result_dict"]
                    if result_dict.get("success", False):
                        # Add to statistics
                        new_size = result_dict.get("new_size", 0)
                        total_original_size += data["original_size"]
                        total_new_size += new_size
                        total_files_processed += 1
                        batch_original_size += data["original_size"]
                        batch_new_size += new_size
                        batch_files_processed += 1
                        completed_archives.append(archive)
                
                # Remove completed tasks from tracking
                for archive in completed_archives:
                    async_results.pop(archive, None)
                
                # Update lifetime statistics if any files were processed in this batch
                if batch_files_processed > 0 and stats_enabled:
                    batch_execution_time = time.time() - batch_start_time
                    stats_tracker.add_run(
                        batch_files_processed,
                        batch_original_size,
                        batch_new_size,
                        batch_execution_time
                    )
                    # Only print stats occasionally to avoid log spam
                    if total_files_processed % 5 == 0 or len(new_archives) < 5:
                        print_lifetime_stats(stats_tracker, logger)
                    
                    logger.info(f"Session summary: Processed {total_files_processed} files, "
                               f"saved {(total_original_size - total_new_size) / (1024*1024):.2f}MB")

            # Sleep before next check
            time.sleep(args.watch_interval)

    except KeyboardInterrupt:
        logger.info("\nWatch mode stopped by user.")
    except Exception as e:
        logger.error(f"Error in watch mode: {e}")
    finally:
        # Final statistics update if needed
        if stats_enabled and total_files_processed > 0:
            session_execution_time = time.time() - session_start_time
            logger.info(f"\nWatch session summary:")
            logger.info(f"Total files processed: {total_files_processed}")
            logger.info(f"Total session time: {session_execution_time/60:.1f} minutes")
            print_lifetime_stats(stats_tracker, logger)
        
        # Cleanly shut down packaging thread if active
        if packaging_queue is not None:
            packaging_queue.put(None)  # sentinel for worker
            packaging_queue.join()
            logger.info("Packaging thread shut down")
        save_history()

    return 0
