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
from .presets import (list_available_presets, apply_preset_with_overrides, 
                     export_preset_from_args, save_preset, import_presets_from_file)


def parse_arguments():
    """Parse command line arguments with support for presets."""
    parser = argparse.ArgumentParser(description='Convert CBZ/CBR images to WebP format')
    parser.add_argument('input_path', nargs='?', default=None,
                        help='Path to CBZ/CBR file or directory containing multiple archives')
    parser.add_argument('output_dir', nargs='?', default=None,
                        help='Output directory for WebP images')
    
    # Basic options - with None as default to detect if explicitly set
    parser.add_argument('--quality', type=int, default=None, 
                        help='WebP compression quality (0-100, default: 80 or from preset)')
    parser.add_argument('--max-width', type=int, default=None,
                        help='Max width in pixels (0 = no restriction)')
    parser.add_argument('--max-height', type=int, default=None,
                        help='Max height in pixels (0 = no restriction)')
    
    # Advanced compression options
    compression_group = parser.add_argument_group('Advanced Compression Options')
    compression_group.add_argument('--method', type=int, choices=range(0, 7), default=None,
                        help='WebP compression method (0-6): higher = better compression but slower')
    compression_group.add_argument('--sharp-yuv', action='store_true', default=None,
                        help='Use sharp YUV conversion for better text quality')
    compression_group.add_argument('--no-sharp-yuv', action='store_true',
                        help='Disable sharp YUV conversion even if preset enables it')
    compression_group.add_argument('--preprocessing', choices=['none', 'unsharp_mask', 'reduce_noise'], default=None,
                        help='Apply preprocessing to images before compression')
    compression_group.add_argument('--zip-compression', type=int, choices=range(0, 10), default=None,
                        help='ZIP compression level for CBZ (0-9)')
    compression_group.add_argument('--lossless', action='store_true', default=None,
                        help='Use lossless WebP compression (larger but perfect quality)')
    compression_group.add_argument('--no-lossless', action='store_true',
                        help='Disable lossless compression even if preset enables it')
    compression_group.add_argument('--auto-optimize', action='store_true', default=None,
                        help='Try both lossy and lossless and use smaller file')
    compression_group.add_argument('--no-auto-optimize', action='store_true',
                        help='Disable auto-optimization even if preset enables it')
    
    # Preset options
    preset_group = parser.add_argument_group('Preset Options')
    available_presets = list_available_presets()
    preset_group.add_argument('--preset', choices=available_presets, default='default',
                        help=f'Use a preset profile (available: {", ".join(available_presets)})')
    preset_group.add_argument('--save-preset', type=str, metavar='NAME',
                        help='Save current settings as a new preset')
    preset_group.add_argument('--import-preset', type=str, metavar='FILE',
                        help='Import presets from a JSON file')
    preset_group.add_argument('--list-presets', action='store_true',
                        help='List all available presets and exit')
    preset_group.add_argument('--overwrite-preset', action='store_true',
                        help='Overwrite existing presets when saving or importing')
    
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
    
    args = parser.parse_args()
    
    # Validate required arguments based on actions
    if not args.list_presets and args.input_path is None and not args.import_preset:
        parser.error("input_path is required unless --list-presets or --import-preset is specified")
    
    if not args.list_presets and not args.stats_only and args.input_path is not None and args.output_dir is None and not args.import_preset:
        parser.error("output_dir is required unless --list-presets, --stats-only, or --import-preset is specified")
    
    # Handle negation flags
    if args.no_sharp_yuv:
        args.sharp_yuv = False
    if args.no_lossless:
        args.lossless = False
    if args.no_auto_optimize:
        args.auto_optimize = False
    
    return args


def main():
    args = parse_arguments()
    logger = setup_logging(args.verbose, args.silent)

    # Handle preset listing
    if args.list_presets:
        presets = list_available_presets()
        print("\nAvailable presets:")
        for preset in presets:
            print(f"  - {preset}")
        return 0
    
    # Handle preset importing
    if args.import_preset:
        import_path = Path(args.import_preset).resolve()
        if not import_path.exists():
            logger.error(f"Import preset file not found: {import_path}")
            return 1
        
        result = import_presets_from_file(
            import_path, 
            overwrite=args.overwrite_preset,
            logger=logger
        )
        
        if result > 0:
            logger.info(f"Successfully imported {result} presets")
            if args.input_path is None:  # If we're only importing, exit
                return 0
        else:
            logger.error("Failed to import presets")
            if args.input_path is None:  # If we're only importing, exit
                return 1
    
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
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None

    if not input_path.exists():
        logger.error(f"Input path not found: {input_path}")
        return 1

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get command-line overrides to apply on top of preset
    overrides = {}
    for param in [
        'quality', 'max_width', 'max_height', 
        'method','sharp_yuv','preprocessing',
        'zip_compression','lossless','auto_optimize'
    ]:
        value = getattr(args, param)
    # Only override if the user explicitly set it 
        if value is not None:
            overrides[param] = value

    
    # Apply preset with overrides
    params = apply_preset_with_overrides(args.preset, overrides, logger)
    
    # Update args with the final parameters
    for key, value in params.items():
        setattr(args, key, value)
    
    # Save preset if requested
    if args.save_preset:
        try:
            # Export current parameters to a preset
            preset_params = export_preset_from_args(args)
            # Add a description field
            preset_params['description'] = f"Custom preset created on {time.strftime('%Y-%m-%d')}"
            save_preset(args.save_preset, preset_params, args.overwrite_preset, logger)
        except Exception as e:
            logger.error(f"Error saving preset: {e}")
            return 1
    
    # Log the effective parameters being used
    logger.info(f"Using parameters: quality={args.quality}, max_width={args.max_width}, "
               f"max_height={args.max_height}, method={args.method}, "
               f"sharp_yuv={args.sharp_yuv}, preprocessing={args.preprocessing}, "
               f"zip_compression={args.zip_compression}, lossless={args.lossless}, "
               f"auto_optimize={args.auto_optimize}")

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
        
        return watch_directory(input_path, output_dir, args, logger, stats_tracker)

    # If not watch mode, process single file or directory
    start_time = time.time()
    total_files_processed = 0
    total_original_size = 0
    total_new_size = 0

    if input_path.is_file():
        success, original_size, new_size = process_single_file(
            input_file=input_path, 
            output_dir=output_dir,
            quality=args.quality,
            max_width=args.max_width,
            max_height=args.max_height,
            no_cbz=args.no_cbz,
            keep_originals=args.keep_originals,
            num_threads=args.threads,
            logger=logger,
            method=args.method,
            sharp_yuv=args.sharp_yuv,
            preprocessing=args.preprocessing,
            zip_compresslevel=args.zip_compression,
            lossless=args.lossless,
            auto_optimize=args.auto_optimize
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
