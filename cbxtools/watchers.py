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
from .utils import get_preset_parameters


def watch_directory(input_dir, output_dir, args, logger):
    """
    Watch a directory for new CBZ/CBR files and process them with optimized parameters.
    """

    
    history_file = output_dir / '.cbz_webp_processed_files.json'
    logger.info(f"Watching directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Checking every {args.watch_interval} seconds")
    logger.info(f"Using history file: {history_file}")
    
    # Get preset parameters
    preset = getattr(args, 'preset', 'default')
    preset_params = get_preset_parameters(preset)
    
    # Extract optimization parameters, with overrides from command line
    method = getattr(args, 'method', 4)
    if method == 4:  # If using default, use preset value
        method = preset_params['method']
    
    sharp_yuv = getattr(args, 'sharp_yuv', False) or preset_params['sharp_yuv']
    
    preprocessing = getattr(args, 'preprocessing', 'none')
    if preprocessing == 'none':
        preprocessing = preset_params['preprocessing']
    
    zip_compression = getattr(args, 'zip_compression', 6)
    if zip_compression == 6:
        zip_compression = preset_params['zip_compression']
    
    # Check for explicitly set quality using sys.argv
    quality = args.quality
    # Only apply quality adjustment if quality wasn't explicitly set
    if '--quality' not in ' '.join(sys.argv):
        quality_adjustment = preset_params.get('quality_adjustment', 0)
        quality += quality_adjustment
        quality = max(1, min(100, quality))  # Ensure quality is between 1-100
    
    logger.info(f"Using optimization parameters: method={method}, sharp_yuv={sharp_yuv}, "
               f"preprocessing={preprocessing}, zip_compression={zip_compression}, quality={quality}")
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

    try:
        while True:
            archives = find_comic_archives(input_dir, recursive=False)
            new_archives = [a for a in archives if a not in processed_files]

            if new_archives:
                logger.info(f"Found {len(new_archives)} new file(s) to process")

                for archive in new_archives:
                    logger.info(f"Processing: {archive}")

                    success, original_size, result_dict_or_newsize = process_single_file(
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
                        zip_compresslevel=zip_compression
                    )

                    if success:
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

            time.sleep(args.watch_interval)

    except KeyboardInterrupt:
        logger.info("\nWatch mode stopped by user.")
    except Exception as e:
        logger.error(f"Error in watch mode: {e}")
    finally:
        # Cleanly shut down packaging thread if active
        if packaging_queue is not None:
            packaging_queue.put(None)  # sentinel for worker
            packaging_queue.join()
            logger.info("Packaging thread shut down")
        save_history()

    return 0