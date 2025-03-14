#!/usr/bin/env python3
"""
Command-line interface for CBZ/CBR to WebP converter.
"""

import sys
import time
import argparse
from pathlib import Path

from .utils import setup_logging
from .archives import find_comic_archives
from .conversion import process_single_file, process_archive_files
from .stats_tracker import StatsTracker, print_summary_report, print_lifetime_stats
from .watchers import watch_directory
from .utils import get_preset_parameters


def parse_arguments():
    """Parse command line arguments with optimization options."""
    parser = argparse.ArgumentParser(description='Convert CBZ/CBR images to WebP format')
    parser.add_argument('input_path', help='Path to CBZ/CBR file or directory containing multiple archives')
    parser.add_argument('output_dir', help='Output directory for WebP images')
    
    # Basic options
    parser.add_argument('--quality', type=int, default=80, 
                        help='WebP compression quality (0-100, default: 80)')
    parser.add_argument('--max-width', type=int, default=0,
                        help='Max width in pixels (0 = no restriction)')
    parser.add_argument('--max-height', type=int, default=0,
                        help='Max height in pixels (0 = no restriction)')
    
    # Advanced compression options
    compression_group = parser.add_argument_group('Advanced Compression Options')
    compression_group.add_argument('--method', type=int, choices=range(0, 7), default=4,
                        help='WebP compression method (0-6): higher = better compression but slower (default: 4)')
    compression_group.add_argument('--sharp-yuv', action='store_true',
                        help='Use sharp YUV conversion for better text quality')
    compression_group.add_argument('--preprocessing', choices=['none', 'unsharp_mask', 'reduce_noise'], default='none',
                        help='Apply preprocessing to images before compression (default: none)')
    compression_group.add_argument('--zip-compression', type=int, choices=range(0, 10), default=6,
                        help='ZIP compression level for CBZ (0-9, default: 6)')
    compression_group.add_argument('--preset', choices=['default', 'comic', 'photo', 'maximum'], default='default',
                        help='Preset profiles: default, comic (optimized for comics), photo, maximum (default: default)')
    
    # Output options
    parser.add_argument('--no-cbz', action='store_true',
                        help='Do not create a CBZ file with the WebP images')
    parser.add_argument('--keep-originals', action='store_true',
                        help='Keep the extracted WebP files after creating the CBZ')
    parser.add_argument('--recursive', action='store_true',
                        help='Recursively search for CBZ/CBR files in subdirectories')
    parser.add_argument('--threads', type=int, default=0,
                        help='Number of parallel threads to use (0 = auto-detect)')
    
    # Logging/stats options
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--silent', '-s', action='store_true',
                        help='Suppress all output except errors')
    parser.add_argument('--stats-file', type=str, default=None,
                        help='Path to stats file (default: ~/.cbx-tools-stats.json)')
    parser.add_argument('--no-stats', action='store_true',
                        help='Do not update or display lifetime statistics')
    parser.add_argument('--stats-only', action='store_true',
                        help='Display lifetime statistics and exit')
    
    # Watch mode options
    parser.add_argument('--watch', action='store_true',
                        help='Watch input directory for new files and process automatically')
    parser.add_argument('--watch-interval', type=int, default=5,
                        help='Interval (seconds) to check for new files in watch mode')
    parser.add_argument('--delete-originals', action='store_true',
                        help='Delete original files after successful conversion in watch mode')
    parser.add_argument('--clear-history', action='store_true',
                        help='Clear watch history file before starting watch mode')
    
    return parser.parse_args()
    """Get optimized parameters based on preset name."""
    presets = {
        'default': {
            'method': 4,
            'sharp_yuv': False,
            'preprocessing': None,
            'zip_compression': 6,
            'quality_adjustment': 0
        },
        'comic': {
            'method': 6,                # Best compression method
            'sharp_yuv': True,          # Better text rendering
            'preprocessing': 'unsharp_mask', # Enhance line art
            'zip_compression': 9,       # Maximum ZIP compression
            'quality_adjustment': -5    # Slightly lower quality for better compression
        },
        'photo': {
            'method': 4,
            'sharp_yuv': False,         # Not needed for photos
            'preprocessing': None,      # No preprocessing for photos
            'zip_compression': 6,
            'quality_adjustment': 5     # Higher quality for photos
        },
        'maximum': {
            'method': 6,                # Best compression method
            'sharp_yuv': True,          # Better text rendering
            'preprocessing': None,      # No preprocessing
            'zip_compression': 9,       # Maximum ZIP compression
            'quality_adjustment': -10   # Lower quality for maximum compression
        }
    }
    
    return presets.get(preset, presets['default'])


def main():
    args = parse_arguments()
    logger = setup_logging(args.verbose, args.silent)

    # Initialize stats tracker if not disabled
    stats_tracker = StatsTracker(args.stats_file) if not args.no_stats else None
    
    # If only showing stats, display and exit
    if args.stats_only:
        if stats_tracker:
            print_lifetime_stats(stats_tracker, logger)
        else:
            logger.error("Cannot show stats when --no-stats is specified")
        return 0

    # Resolve paths
    input_path = Path(args.input_path).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not input_path.exists():
        logger.error(f"Input path not found: {input_path}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get preset parameters
    preset_params = get_preset_parameters(args.preset)
    
    # Apply preset parameters, but let explicit command-line arguments override them
    method = args.method if args.method != 4 else preset_params['method']
    sharp_yuv = args.sharp_yuv or preset_params['sharp_yuv']
    preprocessing = args.preprocessing if args.preprocessing != 'none' else preset_params['preprocessing']
    zip_compression = args.zip_compression if args.zip_compression != 6 else preset_params['zip_compression']
    
    # Apply quality adjustment from preset
    # Check if the quality was explicitly set by the user
    quality_explicitly_set = any(arg == '--quality' for arg in sys.argv)
    quality = args.quality

    # Only apply preset quality adjustment if quality wasn't explicitly set
    if not quality_explicitly_set and preset_params.get('quality_adjustment'):
        quality += preset_params.get('quality_adjustment', 0)
        quality = max(1, min(100, quality))
    
    # Log the effective parameters being used
    logger.info(f"Using compression parameters: quality={quality}, method={method}, "
               f"sharp_yuv={sharp_yuv}, preprocessing={preprocessing}, "
               f"zip_compression={zip_compression}")

    # Handle watch mode
    if args.watch:
        # Watch mode requires an input directory
        if not input_path.is_dir():
            logger.error("Watch mode requires an input directory")
            return 1

        # Optionally clear watch history
        if args.clear_history:
            history_file = output_dir / '.cbz_webp_processed_files.json'
            if history_file.exists():
                try:
                    history_file.unlink()
                    logger.info(f"Cleared history file: {history_file}")
                except Exception as e:
                    logger.error(f"Error clearing history file: {e}")

        # We need to modify args to include the new parameters
        args.method = method
        args.sharp_yuv = sharp_yuv
        args.preprocessing = preprocessing
        args.zip_compression = zip_compression
        args.quality = quality
        
        return watch_directory(input_path, output_dir, args, logger)

    # If not watch mode, process single file or directory
    start_time = time.time()
    total_files_processed = 0
    total_original_size = 0
    total_new_size = 0

    if input_path.is_file():
        success, original_size, new_size = process_single_file(
            input_file=input_path, 
            output_dir=output_dir,
            quality=quality,
            max_width=args.max_width,
            max_height=args.max_height,
            no_cbz=args.no_cbz,
            keep_originals=args.keep_originals,
            num_threads=args.threads,
            logger=logger,
            method=method,
            sharp_yuv=sharp_yuv,
            preprocessing=preprocessing,
            zip_compresslevel=zip_compression
        )

        if success:
            total_files_processed = 1
            total_original_size = original_size
            total_new_size = new_size
            if not args.no_cbz:
                processed = [(input_path.name, original_size, new_size)]
                print_summary_report(processed, original_size, new_size, logger)

        return_code = 0 if success else 1

    elif input_path.is_dir():
        from .archives import find_comic_archives
        archives = find_comic_archives(input_path, args.recursive)
        if not archives:
            logger.error(f"No CBZ/CBR files found in {input_path}")
            return 1

        logger.info(f"Found {len(archives)} comic archives to process.")

        # We need to modify args to include the new parameters
        args.method = method
        args.sharp_yuv = sharp_yuv
        args.preprocessing = preprocessing
        args.zip_compression = zip_compression
        args.quality = quality
        
        # Process the archives
        success_count, total_original_size, total_new_size, processed_files = process_archive_files(
            archives, output_dir, args, logger
        )
        total_files_processed = success_count

        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        logger.info(f"\nProcessed {success_count} of {len(archives)} archives successfully")
        logger.info(f"Total execution time: {int(minutes)}m {seconds:.1f}s")

        if not args.no_cbz and processed_files:
            print_summary_report(processed_files, total_original_size, total_new_size, logger)

        return_code = 0
    else:
        logger.error(f"{input_path} is neither a file nor a directory")
        return 1

    # Update lifetime stats if successful
    execution_time = time.time() - start_time
    if return_code == 0 and stats_tracker and total_files_processed > 0:
        stats_tracker.add_run(
            total_files_processed,
            total_original_size,
            total_new_size,
            execution_time
        )
        print_lifetime_stats(stats_tracker, logger)

    return return_code
