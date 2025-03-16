#!/usr/bin/env python3
"""
Command-line interface for CBZ/CBR to WebP converter.
"""

import sys
import time
import argparse
from pathlib import Path

from .utils import setup_logging, remove_empty_dirs, log_effective_parameters
from .archives import find_comic_archives
from .conversion import process_single_file, process_archive_files
from .stats_tracker import StatsTracker, print_summary_report, print_lifetime_stats
from .watchers import watch_directory, cleanup_empty_directories
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
    compression_group.add_argument('--preprocessing', choices=['none', 'unsharp_mask', 'reduce_noise'], default=None,
                        help='Apply preprocessing to images before compression')
    compression_group.add_argument('--zip-compression', type=int, choices=range(0, 10), default=None,
                        help='ZIP compression level for CBZ (0-9)')
    compression_group.add_argument('--lossless', action='store_true', default=None,
                        help='Use lossless WebP compression (larger but perfect quality)')
    compression_group.add_argument('--no-lossless', action='store_true',
                        help='Disable lossless compression even if preset enables it')
    
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
    if args.no_lossless:
        args.lossless = False
    
    return args


def handle_preset_listing(logger):
    """Handle the --list-presets option."""
    presets = list_available_presets()
    logger.info("\nAvailable presets:")
    for preset in presets:
        logger.info(f"  - {preset}")
    return 0


def handle_preset_importing(args, logger):
    """Handle the --import-preset option."""
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
    
    return None  # Continue with normal processing


def handle_preset_saving(args, logger):
    """Handle the --save-preset option."""
    try:
        # Export current parameters to a preset
        preset_params = export_preset_from_args(args)
        # Add a description field
        preset_params['description'] = f"Custom preset created on {time.strftime('%Y-%m-%d')}"
        save_preset(args.save_preset, preset_params, args.overwrite_preset, logger)
        return 0
    except Exception as e:
        logger.error(f"Error saving preset: {e}")
        return 1


def handle_stats_only(stats_tracker, logger):
    """Handle the --stats-only option."""
    if stats_tracker:
        print_lifetime_stats(stats_tracker, logger)
    else:
        logger.error("Cannot show stats when --no-stats is specified")
    return 0


def handle_watch_mode(input_path, output_dir, args, logger, stats_tracker):
    """Handle watch mode operation."""
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
    
    # Pass recursive flag to watch_directory function
    return watch_directory(input_path, output_dir, args, logger, stats_tracker)


def process_single_archive_file(input_path, output_dir, args, logger):
    """Process a single comic archive file."""
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
        preprocessing=args.preprocessing,
        zip_compresslevel=args.zip_compression,
        lossless=args.lossless
    )

    if success and not args.no_cbz:
        processed = [(input_path.name, original_size, new_size)]
        print_summary_report(processed, original_size, new_size, logger)

    return success, original_size, new_size


def process_directory_non_recursive(input_path, output_dir, args, logger):
    """Process all comics in a directory (non-recursive mode)."""
    archives = find_comic_archives(input_path, args.recursive)
    if not archives:
        logger.error(f"No CBZ/CBR files found in {input_path}")
        return 0, 0, 0, []

    logger.info(f"Found {len(archives)} comic archives to process.")
    
    # Use the original process_archive_files for non-recursive mode
    success_count, total_original_size, total_new_size, processed_files = process_archive_files(
        archives, output_dir, args, logger
    )
    
    return success_count, len(archives), total_original_size, total_new_size, processed_files


def process_directory_recursive(input_path, output_dir, args, logger):
    """Process all comics in a directory with subdirectories (recursive mode)."""
    archives = find_comic_archives(input_path, args.recursive)
    if not archives:
        logger.error(f"No CBZ/CBR files found in {input_path}")
        return 0, 0, 0, 0, []

    logger.info(f"Found {len(archives)} comic archives to process.")
    
    # Check for pre-existing empty directories if delete_originals is enabled
    if args.delete_originals:
        logger.info("Checking for pre-existing empty directories...")
        cleanup_empty_directories(input_path, logger)
        
    # Process each file separately to maintain directory structure
    success_count = 0
    total_original_size = 0
    total_new_size = 0
    processed_files = []
    
    # Store list of archives to process
    archives_to_process = list(archives)
    
    for archive in archives_to_process:
        # Calculate relative path to maintain directory structure
        rel_path = archive.parent.relative_to(input_path)
        target_output_dir = output_dir / rel_path
        target_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Processing: {archive}")
        logger.debug(f"Output directory: {target_output_dir}")
        
        success, orig_size, new_size = process_single_file(
            input_file=archive, 
            output_dir=target_output_dir,
            quality=args.quality,
            max_width=args.max_width,
            max_height=args.max_height,
            no_cbz=args.no_cbz,
            keep_originals=args.keep_originals,
            num_threads=args.threads,
            logger=logger,
            method=args.method,
            preprocessing=args.preprocessing,
            zip_compresslevel=args.zip_compression,
            lossless=args.lossless
        )
        
        if success:
            success_count += 1
            total_original_size += orig_size
            total_new_size += new_size
            processed_files.append((str(rel_path / archive.name), orig_size, new_size))
            
            # Delete original and clean up empty directories if requested
            if args.delete_originals:
                try:
                    archive.unlink()
                    logger.info(f"Deleted original file: {archive}")
                    
                    # Check if parent directory is now empty and remove if it is
                    remove_empty_dirs(archive.parent, input_path, logger)
                except Exception as e:
                    logger.error(f"Error deleting file {archive}: {e}")
    
    return success_count, len(archives), total_original_size, total_new_size, processed_files


def main():
    args = parse_arguments()
    logger = setup_logging(args.verbose, args.silent)

    # Handle preset listing
    if args.list_presets:
        return handle_preset_listing(logger)
    
    # Handle preset importing
    if args.import_preset:
        result = handle_preset_importing(args, logger)
        if result is not None:  # If function returned a status code
            return result
    
    # Initialize stats tracker if not disabled
    stats_tracker = StatsTracker(args.stats_file) if not args.no_stats else None
    
    # If only showing stats, display and exit
    if args.stats_only:
        return handle_stats_only(stats_tracker, logger)

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
        'method','preprocessing',
        'zip_compression','lossless'
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
        return handle_preset_saving(args, logger)
    
    # Log the effective parameters being used
    log_effective_parameters(args, logger, args.recursive)
    
    # Handle watch mode
    if args.watch:
        return handle_watch_mode(input_path, output_dir, args, logger, stats_tracker)

    # If not watch mode, process single file or directory
    start_time = time.time()
    total_files_processed = 0
    total_original_size = 0
    total_new_size = 0
    processed_files = []
    return_code = 0

    if input_path.is_file():
        # For single file, output directory is just the base output_dir
        success, original_size, new_size = process_single_archive_file(
            input_path, output_dir, args, logger
        )

        if success:
            total_files_processed = 1
            total_original_size = original_size
            total_new_size = new_size

        return_code = 0 if success else 1

    elif input_path.is_dir():
        if args.recursive:
            success_count, total_archives, total_original_size, total_new_size, processed_files = (
                process_directory_recursive(input_path, output_dir, args, logger)
            )
        else:
            success_count, total_archives, total_original_size, total_new_size, processed_files = (
                process_directory_non_recursive(input_path, output_dir, args, logger)
            )
        
        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        logger.info(f"\nProcessed {success_count} of {total_archives} archives successfully")
        logger.info(f"Total execution time: {int(minutes)}m {seconds:.1f}s")

        if not args.no_cbz and processed_files:
            print_summary_report(processed_files, total_original_size, total_new_size, logger)

        total_files_processed = success_count
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


if __name__ == "__main__":
    sys.exit(main())
