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
    parser.add_argument('--watch', action='store_true',
                        help='Watch input directory for new files and process them automatically')
    parser.add_argument('--watch-interval', type=int, default=5,
                        help='Interval in seconds to check for new files in watch mode (default: 5)')
    parser.add_argument('--delete-originals', action='store_true',
                        help='Delete original files after successful conversion in watch mode')
    parser.add_argument('--clear-history', action='store_true',
                        help='Clear the history of processed files before starting watch mode')
    return parser.parse_args()

def watch_directory(input_dir, output_dir, args, logger):
    """
    Watch a directory for new CBZ/CBR files and process them as they appear.
    Maintains a persistent record of processed files across script executions.
    
    Args:
        input_dir: Path to the directory to watch
        output_dir: Path to the output directory
        args: Command line arguments
        logger: Logger instance
    """
    import time
    
    # Define path for the history file
    history_file = Path(output_dir) / '.cbz_webp_processed_files.json'
    
    logger.info(f"Watching directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Checking every {args.watch_interval} seconds")
    logger.info(f"Using history file: {history_file}")
    logger.info("Press Ctrl+C to stop watching")
    
    # Initialize the processed files set from history file
    processed_files = set()
    
    # Load history file if it exists
    if history_file.exists():
        try:
            with open(history_file, 'r') as f:
                history_data = json.load(f)
                processed_paths = history_data.get('processed_files', [])
                # Convert string paths to Path objects
                processed_files = set(Path(p) for p in processed_paths)
                logger.info(f"Loaded {len(processed_files)} previously processed files from history")
        except Exception as e:
            logger.error(f"Error loading history file: {e}")
            logger.info("Starting with empty history")
    
    def save_history():
        """Save the processed files to the history file."""
        try:
            # Convert Path objects to strings for JSON serialization
            history_data = {
                'processed_files': [str(p) for p in processed_files],
                'last_updated': datetime.datetime.now().isoformat()
            }
            
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
            logger.debug(f"Saved {len(processed_files)} processed files to history")
        except Exception as e:
            logger.error(f"Error saving history file: {e}")
    
    try:
        while True:
            # Find all comic archives in the directory
            archives = find_comic_archives(input_dir, recursive=False)
            
            # Filter out already processed files
            new_archives = [a for a in archives if a not in processed_files]
            
            if new_archives:
                logger.info(f"Found {len(new_archives)} new file(s) to process")
                
                # Process each new file
                for archive in new_archives:
                    logger.info(f"Processing: {archive}")
                    
                    # Process the file
                    success, original_size, new_size = process_single_file(
                        archive, 
                        output_dir,
                        args.quality, 
                        args.max_width, 
                        args.max_height,
                        args.no_cbz, 
                        args.keep_originals,
                        args.threads,
                        logger
                    )
                    
                    if success:
                        # Mark file as processed
                        processed_files.add(archive)
                        # Save history after each successful processing
                        save_history()
                        
                        # Delete the original file if processing was successful and deletion is enabled
                        if args.delete_originals:
                            try:
                                archive.unlink()
                                logger.info(f"Deleted original file: {archive}")
                            except Exception as e:
                                logger.error(f"Error deleting file {archive}: {e}")
                    else:
                        logger.error(f"Failed to process {archive}")
            
            # Wait before checking again
            time.sleep(args.watch_interval)
            
    except KeyboardInterrupt:
        logger.info("\nWatchdog mode stopped by user")
        # Save history on clean exit
        save_history()
    except Exception as e:
        logger.error(f"Error in watchdog mode: {e}")
        # Still try to save history on error
        save_history()
        return 1
    
    return 0


def main():
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

    input_path = Path(args.input_path).resolve()
    output_dir = Path(args.output_dir).resolve()
    
    if not input_path.exists():
        logger.error(f"Input path not found: {input_path}")
        return 1
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we need to clear history
    if args.clear_history:
        history_file = Path(output_dir) / '.cbz_webp_processed_files.json'
        if history_file.exists():
            try:
                history_file.unlink()
                logger.info(f"Cleared history file: {history_file}")
            except Exception as e:
                logger.error(f"Error clearing history file: {e}")
    
    # Check if watch mode is enabled
    if args.watch:
        if not input_path.is_dir():
            logger.error("Watch mode requires an input directory")
            return 1
        
        return watch_directory(input_path, output_dir, args, logger)
    
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
