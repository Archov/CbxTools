#!/usr/bin/env python3
"""
Statistics tracking and reporting for CBZ/CBR to WebP converter.
"""

import sys
import json
import datetime
from pathlib import Path

from cbz_webp_converter.utils import get_file_size_formatted


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
        total_original = get_file_size_formatted(self.stats["total_original_size_bytes"])[0]
        total_new = get_file_size_formatted(self.stats["total_new_size_bytes"])[0]
        total_saved = get_file_size_formatted(self.stats["total_bytes_saved"])[0]
        
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
    total_original_formatted, _ = get_file_size_formatted(total_original_size)
    total_new_formatted, _ = get_file_size_formatted(total_new_size)
    total_diff_formatted, _ = get_file_size_formatted(abs(total_diff))
    
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
                orig_fmt, _ = get_file_size_formatted(orig_size)
                new_fmt, _ = get_file_size_formatted(new_size)
                diff = orig_size - new_size
                diff_fmt, _ = get_file_size_formatted(abs(diff))
                
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
