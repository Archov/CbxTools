#!/usr/bin/env python3
"""
Statistics tracking and reporting for CBZ/CBR to WebP converter.
"""

import sys
import json
import datetime
from pathlib import Path

from .utils import get_file_size_formatted


class StatsTracker:
    """Tracks and persists lifetime statistics for the converter."""
    
    def __init__(self, stats_file=None):
        if stats_file is None:
            self.stats_file = Path.home() / '.cbxtools//.cbx-tools-stats.json'
        else:
            self.stats_file = Path(stats_file)
        self.stats = self._load_stats()

    def _load_stats(self):
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load stats file: {e}", file=sys.stderr)
                return self._get_default_stats()
        else:
            return self._get_default_stats()

    def _get_default_stats(self):
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
        try:
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save stats file: {e}", file=sys.stderr)

    def add_run(self, files_processed, original_size, new_size, execution_time):
        bytes_saved = original_size - new_size
        run_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "files_processed": files_processed,
            "original_size_bytes": original_size,
            "new_size_bytes": new_size,
            "bytes_saved": bytes_saved,
            "execution_time_seconds": execution_time
        }

        self.stats["total_files_processed"] += files_processed
        self.stats["total_original_size_bytes"] += original_size
        self.stats["total_new_size_bytes"] += new_size
        self.stats["total_bytes_saved"] += bytes_saved
        self.stats["last_run"] = run_data["timestamp"]
        self.stats["run_count"] += 1

        self.stats["runs"].append(run_data)
        self.stats["runs"] = self.stats["runs"][-20:]
        self.save_stats()

    def get_lifetime_stats(self):
        if self.stats["total_original_size_bytes"] > 0:
            lifetime_savings_pct = (self.stats["total_bytes_saved"] / 
                                    self.stats["total_original_size_bytes"]) * 100
        else:
            lifetime_savings_pct = 0
        
        total_original = get_file_size_formatted(self.stats["total_original_size_bytes"])[0]
        total_new = get_file_size_formatted(self.stats["total_new_size_bytes"])[0]
        total_saved = get_file_size_formatted(self.stats["total_bytes_saved"])[0]

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

    total_diff = total_original_size - total_new_size
    if total_original_size > 0:
        total_pct = (total_diff / total_original_size) * 100
    else:
        total_pct = 0

    total_original_fmt, _ = get_file_size_formatted(total_original_size)
    total_new_fmt, _ = get_file_size_formatted(total_new_size)
    diff_fmt, _ = get_file_size_formatted(abs(total_diff))

    logger.info("\n" + "=" * 80)
    logger.info("CONVERSION SUMMARY REPORT")
    logger.info("=" * 80)

    if len(processed_files) > 1:
        logger.info("\nDetailed breakdown:")
        logger.info(f"{'File':<30} {'Original':<10} {'New':<10} {'Diff':<10} {'Savings':<10}")
        logger.info("-" * 80)
        for filename, orig_size, new_size in processed_files:
            if new_size > 0:
                orig_fmt, _ = get_file_size_formatted(orig_size)
                new_fmt, _ = get_file_size_formatted(new_size)
                diff = orig_size - new_size
                diff_fmt_item, _ = get_file_size_formatted(abs(diff))
                if orig_size > 0:
                    pct = (diff / orig_size) * 100
                    pct_str = f"{pct:.1f}%"
                    if diff < 0:
                        pct_str = f"-{pct_str}"
                else:
                    pct_str = "N/A"
                logger.info(
                    f"{filename[:30]:<30} {orig_fmt:<10} {new_fmt:<10} "
                    f"{diff_fmt_item:<10} {pct_str:<10}"
                )

    logger.info("\nTotal space:")
    logger.info(f"Original size: {total_original_fmt}")
    logger.info(f"New size:      {total_new_fmt}")

    if total_diff > 0:
        logger.info(f"Space saved:   {diff_fmt} ({total_pct:.1f}%)")
    else:
        logger.info(f"Space increased: {diff_fmt} ({abs(total_pct):.1f}% larger)")

    logger.info("=" * 80)


def print_lifetime_stats(stats_tracker, logger):
    """Print lifetime statistics."""
    s = stats_tracker.get_lifetime_stats()

    logger.info("\n" + "=" * 80)
    logger.info("LIFETIME STATISTICS")
    logger.info("=" * 80)
    logger.info(f"Files Processed: {s['files_processed']} (across {s['run_count']} runs)")
    logger.info(f"First Run:       {s['first_run']}")
    logger.info(f"Last Run:        {s['last_run']}")
    logger.info("\nTotal Space:")
    logger.info(f"Original size:   {s['original_size']}")
    logger.info(f"New size:        {s['new_size']}")
    logger.info(f"Space saved:     {s['space_saved']} ({s['savings_percentage']})")
    logger.info("=" * 80)
