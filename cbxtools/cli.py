#!/usr/bin/env python3
"""
Command-line interface for CBZ/CBR to WebP converter.
"""

import sys
import time
import argparse
from pathlib import Path

from cbxtools.utils import setup_logging
from cbxtools.archive_utils import find_comic_archives
from cbxtools.conversion import process_single_file, process_archive_files
from cbxtools.stats import StatsTracker, print_summary_report, print_lifetime_stats


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Convert CBZ/CBR images to WebP format')
    parser.add_argument('input_path', help='Path to CBZ/CBR file or directory containing multiple archives')
    parser.add_argument('output_dir', help='Output directory for WebP images')
    parser.add_argument('--quality', type=int, default=80, 
                        help='WebP compression quality (0-100, default: 80)')
    parser.add_argument('--max-width', type=int, default=0,
                        help='Maximum width in pixels. 0 means no width restriction (default: 0)')
    parser.add_argument('--max-height', type=int, default=0,
                        help='Maximum height in pixels. 0 means no height restriction (default: 0)')
    parser.add_argument('--no-cbz', action='store_true',
                        help='Do not create a CBZ file with the WebP images (by default, CBZ is created)')
    parser.add_argument('--keep-originals', action='store_true',
                        help='Keep the extracted WebP files after creating the CBZ')
    parser.add_argument('--recursive', action='store_true',
                        help='Recursively search for CBZ/CBR files in subdirectories')
    parser.add_argument('--threads', type=int, default=0,
                        help='Number of parallel threads to use. 0 means auto-detect (default: 0)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--silent', '-s', action='store_true',
                        help='Suppress all output except errors')
    parser.add_argument('--stats-file', type=str, default=None,
                        help='Path to stats file for lifetime statistics (default: ~/.cbz_webp_stats.json)')
    parser.add_argument('--no-stats', action='store_true',
                        help='Do not update or display lifetime statistics')
    parser.add_argument('--stats-only', action='store_true',
                        help='Display lifetime statistics and exit')
    return parser.parse_args()


def main():
    """Main entry point for the command-line interface."""
    args = parse_arguments()
    
    # Set up logging
    logger = setup_logging(args.verbose, args.silent)
    
    # Initialize stats tracker
    stats_tracker = StatsTracker(args.stats_file) if not args.no_stats else None
    
    # If only showing stats, display and exit
    if args.stats_only:
        if stats_tracker:
            print_lifetime_stats(stats_tracker, logger)
        else:
            logger.error("Cannot show stats when --no-stats is specified")
        return 0
    
    # Check if args is missing either positional argument when not in stats-only mode
    if args.stats_only == False and (not hasattr(args, 'input_path') or not hasattr(args, 'output_dir')):
        logger.error("Both input_path and output_dir are required when not in stats-only mode")
        return 1
    
    input_path = Path(args.input_path).resolve()
    output_dir = Path(args.output_dir).resolve()
    
    if not input_path.exists():
        logger.error(f"Input path not found: {input_path}")
        return 1
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    total_files_processed = 0
    total_original_size = 0
    total_new_size = 0
    
    # Process single file or directory
    if input_path.is_file():
        # Process single file
        success, original_size, new_size = process_single_file(
            input_path, output_dir, 
            args.quality, args.max_width, args.max_height, 
            args.no_cbz, args.keep_originals, args.threads, logger
        )
        
        if success:
            total_files_processed = 1
            total_original_size = original_size
            total_new_size = new_size
            
            if not args.no_cbz:
                processed_files = [(input_path.name, original_size, new_size)]
                print_summary_report(processed_files, original_size, new_size, logger)
        
        return_code = 0 if success else 1
        
    elif input_path.is_dir():
        # Process directory of files
        archives = find_comic_archives(input_path, args.recursive)
        
        if not archives:
            logger.error(f"No CBZ/CBR files found in {input_path}")
            return 1
        
        logger.info(f"Found {len(archives)} comic archives to process")
        
        # Process archives
        success_count, total_original_size, total_new_size, processed_files = process_archive_files(
            archives, output_dir, args, logger
        )
        
        total_files_processed = success_count
        
        # Calculate and display execution time
        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        
        logger.info(f"\nProcessed {success_count} of {len(archives)} archives successfully")
        logger.info(f"Total execution time: {int(minutes)}m {seconds:.1f}s")
        
        # Print summary report if we created CBZ files
        if not args.no_cbz and processed_files:
            print_summary_report(processed_files, total_original_size, total_new_size, logger)
            
        return_code = 0
    else:
        logger.error(f"{input_path} is neither a file nor a directory")
        return 1
    
    # Update lifetime stats if successful and stats tracking is enabled
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
