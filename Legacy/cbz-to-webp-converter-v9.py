def print_lifetime_stats(stats_tracker, logger):
    """Print lifetime statistics."""
    stats = stats_tracker.get_lifetime_stats()
    
    logger.info("\n" + "=" * 80)
    logger.info("LIFETIME STATISTICS")
    logger.info("=" * 80)
    logger.info(f"Files Processed: {stats['files_processed']} (across {stats['run_count']} runs)")
    logger.info(f"First Run: {stats['first_run']}")
    logger.info(f"Last Run: {stats['last_run']}")
    logger.info("\nTotal Space:")
    logger.info(f"Original size: {stats['original_size']}")
    logger.info(f"New size: {stats['new_size']}")
    logger.info(f"Space saved: {stats['space_saved']} ({stats['savings_percentage']})")
    logger.info("=" * 80)

class StatsTracker:
    """Tracks and persists lifetime statistics for the converter."""
    
    def __init__(self, stats_file=None):
        """Initialize the stats tracker with an optional stats file path."""
        if stats_file is None:
            # Default to a stats file in the user's home directory
            self.stats_file = Path.home() / '.cbz_webp_stats.json'
        else:
            self.stats_file = Path(stats_file)
        
        # Initialize stats
        self.stats = self._load_stats()
    
    def _load_stats(self):
        """Load stats from file or initialize if not exists."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load stats file: {e}", file=sys.stderr)
                # Return default stats if file is corrupt
                return self._get_default_stats()
        else:
            return self._get_default_stats()
    
    def _get_default_stats(self):
        """Return default stats structure."""
        return {
            "total_files_processed": 0,
            "total_original_size_bytes": 0,
            "total_new_size_bytes": 0,
            "total_bytes_saved": 0,
            "first_run": datetime.datetime.now().isoformat(),
            "last_run": datetime.datetime.now().isoformat(),
            "run_count": 0,
            "runs": []
        }
    
    def save_stats(self):
        """Save stats to the stats file."""
        try:
            # Create parent directories if they don't exist
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
                
        except IOError as e:
            print(f"Warning: Could not save stats file: {e}", file=sys.stderr)
    
    def add_run(self, files_processed, original_size, new_size, execution_time):
        """Add statistics from a new run."""
        # Update run-specific stats
        bytes_saved = original_size - new_size
        
        run_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "files_processed": files_processed,
            "original_size_bytes": original_size,
            "new_size_bytes": new_size,
            "bytes_saved": bytes_saved,
            "execution_time_seconds": execution_time
        }
        
        # Update lifetime stats
        self.stats["total_files_processed"] += files_processed
        self.stats["total_original_size_bytes"] += original_size
        self.stats["total_new_size_bytes"] += new_size
        self.stats["total_bytes_saved"] += bytes_saved
        self.stats["last_run"] = run_data["timestamp"]
        self.stats["run_count"] += 1
        
        # Add this run to the runs list, keeping most recent 20
        self.stats["runs"].append(run_data)
        self.stats["runs"] = self.stats["runs"][-20:]  # Keep only the most recent 20 runs
        
        # Save the updated stats
        self.save_stats()
    
    def get_lifetime_stats(self):
        """Get the lifetime statistics in a readable format."""
        if self.stats["total_original_size_bytes"] > 0:
            lifetime_savings_pct = (self.stats["total_bytes_saved"] / 
                                   self.stats["total_original_size_bytes"]) * 100
        else:
            lifetime_savings_pct = 0
        
        # Convert bytes to human-readable formats
        total_original = get_file_size_formatted(Path('', self.stats["total_original_size_bytes"]))[0]
        total_new = get_file_size_formatted(Path('', self.stats["total_new_size_bytes"]))[0]
        total_saved = get_file_size_formatted(Path('', self.stats["total_bytes_saved"]))[0]
        
        # Format dates more nicely
        try:
            first_run = datetime.datetime.fromisoformat(self.stats["first_run"]).strftime("%Y-%m-%d")
            last_run = datetime.datetime.fromisoformat(self.stats["last_run"]).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            first_run = self.stats["first_run"]
            last_run = self.stats["last_run"]
        
        return {
            "files_processed": self.stats["total_files_processed"],
            "original_size": total_original,
            "new_size": total_new,
            "space_saved": total_saved,
            "savings_percentage": f"{lifetime_savings_pct:.1f}%",
            "first_run": first_run,
            "last_run": last_run,
            "run_count": self.stats["run_count"]
        }

def print_summary_report(processed_files, total_original_size, total_new_size, logger):
    """Print a summary report of all processed files and total space savings."""
    if not processed_files:
        return
    
    # Calculate total savings
    total_diff = total_original_size - total_new_size
    if total_original_size > 0:
        total_percentage = (total_diff / total_original_size) * 100
    else:
        total_percentage = 0
    
    # Convert to human-readable formats
    total_original_formatted, _ = get_file_size_formatted(Path('', total_original_size))
    total_new_formatted, _ = get_file_size_formatted(Path('', total_new_size))
    total_diff_formatted, _ = get_file_size_formatted(Path('', abs(total_diff)))
    
    # Print the header
    logger.info("\n" + "=" * 80)
    logger.info("CONVERSION SUMMARY REPORT")
    logger.info("=" * 80)
    
    # Print the individual file reports
    if len(processed_files) > 1:  # Only show detailed breakdown for multiple files
        logger.info("\nDetailed breakdown:")
        logger.info(f"{'File':<30} {'Original':<10} {'New':<10} {'Diff':<10} {'Savings':<10}")
        logger.info("-" * 80)
        
        for filename, orig_size, new_size in processed_files:
            if new_size > 0:  # Skip if no new file was created (e.g., with --no-cbz)
                orig_fmt, _ = get_file_size_formatted(Path('', orig_size))
                new_fmt, _ = get_file_size_formatted(Path('', new_size))
                diff = orig_size - new_size
                diff_fmt, _ = get_file_size_formatted(Path('', abs(diff)))
                
                if orig_size > 0:
                    pct = (diff / orig_size) * 100
                    pct_str = f"{pct:.1f}%"
                    if diff < 0:
                        pct_str = f"-{pct_str}"
                else:
                    pct_str = "N/A"
                
                logger.info(f"{filename[:30]:<30} {orig_fmt:<10} {new_fmt:<10} {diff_fmt:<10} {pct_str:<10}")
    
    # Print the totals
    logger.info("\nTotal space:")
    logger.info(f"Original size: {total_original_formatted}")
    logger.info(f"New size: {total_new_formatted}")
    
    if total_diff > 0:
        logger.info(f"Space saved: {total_diff_formatted} ({total_percentage:.1f}%)")
    else:
        logger.info(f"Space increased: {total_diff_formatted} ({abs(total_percentage):.1f}% larger)")
    
    logger.info("=" * 80)

def get_file_size_formatted(file_path):
    """Get file size in a human-readable format."""
    size_bytes = file_path.stat().st_size
    
    # Define size units
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size_unit_index = 0
    
    # Convert to appropriate unit for readability
    size = float(size_bytes)
    while size >= 1024 and size_unit_index < len(units) - 1:
        size /= 1024
        size_unit_index += 1
    
    return f"{size:.2f} {units[size_unit_index]}", size_bytesdef process_archive_files(archives, output_dir, args, logger):
    """Process multiple archive files, optionally in parallel."""
    total_original_size = 0
    total_new_size = 0
    processed_files = []
    
    if args.threads != 1 and len(archives) > 1:
        # Process multiple archives in parallel
        num_workers = min(args.threads if args.threads > 0 else multiprocessing.cpu_count(), len(archives))
        logger.info(f"Processing {len(archives)} comics in parallel using {num_workers} workers")
        
        success_count = 0
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for archive in archives:
                # Create a separate output dir for each archive to avoid conflicts
                archive_output_dir = output_dir / archive.stem
                archive_output_dir.mkdir(parents=True, exist_ok=True)
                
                future = executor.submit(
                    process_single_file,
                    archive, 
                    output_dir,
                    args.quality, 
                    args.max_width, 
                    args.max_height,
                    args.no_cbz, 
                    args.keep_originals,
                    1,  # Use 1 thread within each process
                    logging.getLogger(archive.name)  # Create a separate logger
                )
                futures.append((archive, future))
            
            # Process results as they complete
            for i, (archive, future) in enumerate(futures, 1):
                logger.info(f"[{i}/{len(archives)}] Waiting for {archive.name}...")
                success, original_size, new_size = future.result()
                if success:
                    success_count += 1
                    total_original_size += original_size
                    total_new_size += new_size
                    processed_files.append((archive.name, original_size, new_size))
    else:
        # Process archives sequentially
        success_count = 0
        for i, archive in enumerate(archives, 1):
            logger.info(f"\n[{i}/{len(archives)}] Processing: {archive}")
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
                success_count += 1
                total_original_size += original_size
                total_new_size += new_size
                processed_files.append((archive.name, original_size, new_size))
    
    return success_count, total_original_size, total_new_size, processed_filesdef setup_logging(verbose, silent):
    """Configure logging based on verbosity settings."""
    if silent:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
        
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    return logging.getLogger(__name__)#!/usr/bin/env python3
"""
CBZ/CBR to WebP Converter

This script extracts images from CBZ/CBR files and converts them to WebP format
with configurable compression quality and maximum dimensions.

Requirements:
    - Python 3.6+
    - pip install pillow rarfile patool concurrent-log-handler
"""

import os
import sys
import shutil
import tempfile
import argparse
import logging
import time
import json
import datetime
from pathlib import Path
import zipfile
import patoolib
import rarfile
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

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

def extract_archive(archive_path, extract_dir, logger):
    """Extract CBZ/CBR archive to temporary directory."""
    file_ext = archive_path.suffix.lower()
    
    logger.info(f"Extracting {archive_path} to {extract_dir}...")
    
    if file_ext == '.cbz' or file_ext == '.zip':
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    elif file_ext == '.cbr' or file_ext == '.rar':
        patoolib.extract_archive(str(archive_path), outdir=str(extract_dir))
    else:
        raise ValueError(f"Unsupported archive format: {file_ext}")

def convert_single_image(args):
    """Convert a single image to WebP format. This function runs in a separate process."""
    img_path, webp_path, quality, max_width, max_height = args
    
    try:
        # Create parent directories if they don't exist
        webp_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Open and convert image
        with Image.open(img_path) as img:
            # Resize if needed
            width, height = img.size
            resize_needed = False
            scale_factor = 1.0
            
            # Check if we need to resize based on max width
            if max_width > 0 and width > max_width:
                scale_factor = min(scale_factor, max_width / width)
                resize_needed = True
            
            # Check if we need to resize based on max height
            if max_height > 0 and height > max_height:
                scale_factor = min(scale_factor, max_height / height)
                resize_needed = True
            
            # Apply resize if needed
            if resize_needed:
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Save as WebP
            img.save(webp_path, 'WEBP', quality=quality)
        
        return (img_path, webp_path, True, None)
    except Exception as e:
        return (img_path, webp_path, False, str(e))

def convert_to_webp(extract_dir, output_dir, quality, max_width=0, max_height=0, num_threads=0, logger=None):
    """Convert all images in extract_dir to WebP format and save to output_dir."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    source_files = []
    
    # Find all image files in extract_dir and its subdirectories
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if Path(file).suffix.lower() in image_extensions:
                source_files.append(Path(root) / file)
    
    # Sort files to maintain order
    source_files.sort()
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate default number of threads
    if num_threads <= 0:
        num_threads = multiprocessing.cpu_count()
    
    logger.info(f"Converting {len(source_files)} images to WebP format using {num_threads} threads...")
    
    # Prepare arguments for parallel processing
    conversion_args = []
    for img_path in source_files:
        # Use relative path for output, preserving directory structure
        rel_path = img_path.relative_to(extract_dir)
        webp_path = output_dir / rel_path.with_suffix('.webp')
        conversion_args.append((img_path, webp_path, quality, max_width, max_height))
    
    # Process images in parallel
    success_count = 0
    with ProcessPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(convert_single_image, args) for args in conversion_args]
        
        for i, future in enumerate(as_completed(futures), 1):
            img_path, webp_path, success, error = future.result()
            rel_path = img_path.relative_to(extract_dir)
            
            if success:
                logger.debug(f"[{i}/{len(source_files)}] Converted: {rel_path} -> {webp_path.name}")
                success_count += 1
            else:
                logger.error(f"Error converting {rel_path}: {error}")
    
    logger.info(f"Successfully converted {success_count}/{len(source_files)} images")
    return output_dir

def create_cbz(source_dir, output_file, logger):
    """Create a new CBZ file from the contents of source_dir."""
    logger.info(f"Creating CBZ file: {output_file}")
    
    # Use default compression level 6 for better speed/size tradeoff
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        file_count = 0
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                zipf.write(file_path, file_path.relative_to(source_dir))
                file_count += 1
                
        logger.debug(f"Added {file_count} files to {output_file}")

def find_comic_archives(directory, recursive=False):
    """Find all CBZ/CBR files in the given directory."""
    valid_extensions = {'.cbz', '.cbr', '.zip', '.rar'}
    archives = []
    
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if Path(file).suffix.lower() in valid_extensions:
                    archives.append(Path(root) / file)
    else:
        for file in os.listdir(directory):
            file_path = Path(directory) / file
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
                archives.append(file_path)
    
    return sorted(archives)

def process_single_file(input_file, output_dir, quality, max_width, max_height, no_cbz, keep_originals, num_threads, logger):
    """Process a single CBZ/CBR file."""
    # Create a file-specific output directory
    file_output_dir = output_dir / input_file.stem
    
    # Get original file size
    original_size_formatted, original_size_bytes = get_file_size_formatted(input_file)
    
    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Extract archive
            extract_archive(input_file, temp_path, logger)
            
            # Convert images to WebP
            convert_to_webp(temp_path, file_output_dir, quality, max_width, max_height, num_threads, logger)
            
            # Create CBZ unless --no-cbz is specified
            if not no_cbz:
                cbz_output = output_dir / f"{input_file.stem}.webp.cbz"
                create_cbz(file_output_dir, cbz_output, logger)
                
                # Get new file size and calculate savings
                new_size_formatted, new_size_bytes = get_file_size_formatted(cbz_output)
                size_diff_bytes = original_size_bytes - new_size_bytes
                
                if original_size_bytes > 0:
                    percentage_saved = (size_diff_bytes / original_size_bytes) * 100
                    size_diff_formatted, _ = get_file_size_formatted(Path('', size_diff_bytes))
                    
                    # Print compression report
                    logger.info(f"Compression Report for {input_file.name}:")
                    logger.info(f"  Original size: {original_size_formatted}")
                    logger.info(f"  New size: {new_size_formatted}")
                    
                    if size_diff_bytes > 0:
                        logger.info(f"  Space saved: {size_diff_formatted} ({percentage_saved:.1f}%)")
                    else:
                        logger.info(f"  Space increased: {abs(size_diff_formatted)} " +
                                  f"({abs(percentage_saved):.1f}% larger)")
                
                # Delete the extracted files if --keep-originals is not specified
                if not keep_originals:
                    shutil.rmtree(file_output_dir)
                    logger.debug(f"Removed extracted files from {file_output_dir}")
            
            logger.info(f"Conversion of {input_file.name} completed successfully!")
            return True, original_size_bytes, new_size_bytes if not no_cbz else 0
            
        except Exception as e:
            logger.error(f"Error processing {input_file}: {e}")
            return False, original_size_bytes, 0

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
