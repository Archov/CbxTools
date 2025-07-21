#!/usr/bin/env python3
"""
Command-line interface for CBZ/CBR to WebP converter.
Enhanced with automatic greyscale detection, conversion, and dependency management.
"""

import sys
import time
import argparse
import subprocess
import shutil
import os
from pathlib import Path

from .utils import setup_logging, remove_empty_dirs, log_effective_parameters
from .archives import find_comic_archives
from .conversion import process_single_file, process_archive_files
from .stats_tracker import StatsTracker, print_summary_report, print_lifetime_stats
from .watchers import watch_directory, cleanup_empty_directories
from .presets import (list_available_presets, apply_preset_with_overrides, 
                     export_preset_from_args, save_preset, import_presets_from_file)
from .debug_utils import (debug_single_file_greyscale, test_threshold_ranges, 
                         analyze_directory_for_auto_greyscale)


def check_and_install_dependencies(logger, auto_install=False):
    """
    Check for required and optional dependencies and offer to install missing ones.
    
    Args:
        logger: Logger instance
        auto_install: If True, automatically install missing dependencies
    
    Returns:
        dict: Status of dependencies
    """
    dependencies = {
        'required': {
            'PIL': {
                'import_name': 'PIL',
                'package_name': 'pillow',
                'description': 'Required for image processing',
                'available': False
            },
            'rarfile': {
                'import_name': 'rarfile',
                'package_name': 'rarfile',
                'description': 'Required for CBR archive extraction',
                'available': False
            },
            'patoolib': {
                'import_name': 'patoolib',
                'package_name': 'patool',
                'description': 'Required for general archive extraction',
                'available': False
            }
        },
        'optional': {
            'numpy': {
                'import_name': 'numpy',
                'package_name': 'numpy',
                'description': 'Optional for auto-greyscale image analysis (enhances performance)',
                'available': False
            },
            'matplotlib': {
                'import_name': 'matplotlib',
                'package_name': 'matplotlib',
                'description': 'Optional for debug histogram visualizations',
                'available': False
            }
        }
    }
    
    # Check which dependencies are available
    for category, deps in dependencies.items():
        for name, info in deps.items():
            try:
                __import__(info['import_name'])
                info['available'] = True
            except ImportError:
                info['available'] = False
    
    # Report status
    missing_required = []
    missing_optional = []
    
    for name, info in dependencies['required'].items():
        if info['available']:
            logger.debug(f"✓ {name} is available")
        else:
            logger.warning(f"✗ {name} is missing - {info['description']}")
            missing_required.append(info)
    
    for name, info in dependencies['optional'].items():
        if info['available']:
            logger.debug(f"✓ {name} is available")
        else:
            logger.info(f"○ {name} is missing - {info['description']}")
            missing_optional.append(info)
    
    # Handle missing dependencies
    if missing_required or missing_optional:
        if missing_required:
            logger.error(f"Missing {len(missing_required)} required dependencies!")
        if missing_optional:
            logger.info(f"Missing {len(missing_optional)} optional dependencies")
        
        # Offer to install
        missing_all = missing_required + missing_optional
        if missing_all:
            if auto_install:
                return install_dependencies(missing_all, logger)
            else:
                return offer_to_install_dependencies(missing_all, logger)
    
    # If no missing dependencies, return success status
    return {
        'all_required_available': True,
        'missing_required': [],
        'missing_optional': []
    }


def offer_to_install_dependencies(missing_deps, logger):
    """
    Offer to install missing dependencies interactively.
    
    Args:
        missing_deps: List of missing dependency info dicts
        logger: Logger instance
    
    Returns:
        dict: Installation results
    """
    logger.info("\nMissing dependencies detected:")
    
    for dep in missing_deps:
        logger.info(f"  - {dep['package_name']}: {dep['description']}")
    
    logger.info("\nOptions:")
    logger.info("  1. Install all missing dependencies automatically")
    logger.info("  2. Install only required dependencies")
    logger.info("  3. Install manually with: pip install " + " ".join(dep['package_name'] for dep in missing_deps))
    logger.info("  4. Continue without installing (some features may not work)")
    
    try:
        choice = input("\nChoose an option (1-4): ").strip()
        
        if choice == '1':
            return install_dependencies(missing_deps, logger)
        elif choice == '2':
            # Filter for required dependencies only
            required_packages = ['pillow', 'rarfile', 'patool']
            required_deps = [dep for dep in missing_deps if dep['package_name'] in required_packages]
            return install_dependencies(required_deps, logger)
        elif choice == '3':
            packages = " ".join(dep['package_name'] for dep in missing_deps)
            logger.info(f"\nTo install manually, run this command:")
            logger.info(f"  pip install {packages}")
            logger.info("\nOr use the built-in installer:")
            logger.info(f"  {sys.argv[0]} --install-dependencies")
            return {'all_required_available': False, 'user_declined': True}
        else:
            logger.info("Continuing without installing dependencies...")
            return {'all_required_available': False, 'user_declined': True}
            
    except (KeyboardInterrupt, EOFError):
        logger.info("\nInstallation cancelled by user.")
        return {'all_required_available': False, 'user_declined': True}


def install_dependencies(deps_to_install, logger):
    """
    Install dependencies using pip.
    
    Args:
        deps_to_install: List of dependency info dicts to install
        logger: Logger instance
    
    Returns:
        dict: Installation results
    """
    packages = [dep['package_name'] for dep in deps_to_install]
    logger.info(f"\nInstalling dependencies: {', '.join(packages)}")
    
    # Check if pip is available
    try:
        subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                      capture_output=True, check=True, timeout=30)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error("pip is not available or not working properly")
        logger.error("Please install pip first or install packages manually:")
        logger.error(f"  pip install {' '.join(packages)}")
        return {'all_required_available': False, 'pip_unavailable': True}
    
    try:
        # Use subprocess to install packages
        cmd = [sys.executable, '-m', 'pip', 'install'] + packages
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("✓ Dependencies installed successfully!")
            logger.info("Note: You may need to restart the application for changes to take effect.")
            return {'all_required_available': True, 'installation_success': True}
        else:
            logger.error(f"Failed to install dependencies:")
            if result.stdout.strip():
                logger.error(f"STDOUT: {result.stdout.strip()}")
            if result.stderr.strip():
                logger.error(f"STDERR: {result.stderr.strip()}")
            logger.error("You may need to install packages manually or with elevated privileges.")
            return {'all_required_available': False, 'installation_failed': True}
            
    except subprocess.TimeoutExpired:
        logger.error("Installation timed out after 5 minutes")
        return {'all_required_available': False, 'installation_timeout': True}
    except Exception as e:
        logger.error(f"Error during installation: {e}")
        return {'all_required_available': False, 'installation_error': str(e)}


def parse_arguments():
    """Parse command line arguments with support for presets and auto-greyscale."""
    parser = argparse.ArgumentParser(
        description='Convert CBZ/CBR images to WebP format',
        epilog='Use --check-dependencies to verify all required packages are installed, '
               'or --install-dependencies to automatically install missing packages.'
    )
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
    
    # Image transformation options
    transform_group = parser.add_argument_group('Image Transformation Options')
    transform_group.add_argument('--grayscale', action='store_true', default=None,
                        help='Convert images to grayscale before compression')
    transform_group.add_argument('--no-grayscale', action='store_true',
                        help='Disable grayscale conversion even if preset enables it')
    transform_group.add_argument('--auto-contrast', action='store_true', default=None,
                        help='Apply automatic contrast enhancement before compression')
    transform_group.add_argument('--no-auto-contrast', action='store_true',
                        help='Disable auto-contrast even if preset enables it')
    transform_group.add_argument('--auto-greyscale', action='store_true', default=None,
                        help='Automatically detect and convert near-greyscale images to greyscale')
    transform_group.add_argument('--no-auto-greyscale', action='store_true',
                        help='Disable auto-greyscale even if preset enables it')
    transform_group.add_argument('--auto-greyscale-pixel-threshold', type=int, default=None,
                        help='Pixel difference threshold for auto-greyscale detection (default: 16)')
    transform_group.add_argument('--auto-greyscale-percent-threshold', type=float, default=None,
                        help='Percentage of colored pixels threshold for auto-greyscale (default: 0.01)')
    transform_group.add_argument('--preserve-auto-greyscale-png', action='store_true', default=None,
                        help='Preserve the intermediate PNG file during auto-greyscale conversion for debugging')
    
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
    
    # Debug options
    debug_group = parser.add_argument_group('Debug Options')
    debug_group.add_argument('--debug-auto-greyscale', action='store_true',
                        help='Enable detailed debugging for auto-greyscale detection (saves analysis files and visualizations)')
    debug_group.add_argument('--debug-auto-greyscale-single', type=str, metavar='FILE_PATH',
                        help='Analyze a single image or CBZ/CBR file for auto-greyscale debugging and exit')
    debug_group.add_argument('--debug-output-dir', type=str, default=None,
                        help='Output directory for debug files (default: same as output_dir)')
    debug_group.add_argument('--debug-test-thresholds', type=str, metavar='IMAGE_PATH',
                        help='Test multiple threshold combinations on a single image and exit')
    debug_group.add_argument('--debug-analyze-directory', type=str, metavar='DIRECTORY_PATH',
                        help='Analyze all images in directory with current thresholds and exit')

    scan_group = parser.add_argument_group('Near Greyscale Scan')
    scan_group.add_argument('--scan-near-greyscale', choices=['dryrun','move','process'],
                        help='Scan archives for near-greyscale images and take action')
    scan_group.add_argument('--scan-output', type=str, default=None,
                        help='Output file for dryrun or destination directory for move mode')
    
    # Dependency management options
    dep_group = parser.add_argument_group('Dependency Management Options')
    dep_group.add_argument('--check-dependencies', action='store_true',
                        help='Check for dependencies and exit')
    dep_group.add_argument('--install-dependencies', action='store_true',
                        help='Automatically install missing dependencies and exit')
    dep_group.add_argument('--skip-dependency-check', action='store_true',
                        help='Skip dependency checking on startup')
    
    args = parser.parse_args()
    
    # Check if any debug operations are requested
    debug_operations = any([
        args.debug_auto_greyscale_single,
        args.debug_test_thresholds,
        args.debug_analyze_directory
    ])
    
    # Check if any dependency operations are requested
    dependency_operations = any([
        args.check_dependencies,
        args.install_dependencies
    ])
    
    # Validate required arguments based on actions
    if not args.list_presets and args.input_path is None and not args.import_preset and not debug_operations and not dependency_operations and not args.stats_only:
        parser.error("input_path is required unless --list-presets, --import-preset, --stats-only, dependency operations, or debug operations are specified")
    
    if (
        not args.list_presets
        and not args.stats_only
        and args.input_path is not None
        and args.output_dir is None
        and not args.import_preset
        and not debug_operations
        and not dependency_operations
        and not args.scan_near_greyscale
    ):
        parser.error(
            "output_dir is required unless --list-presets, --stats-only, --import-preset, dependency operations, debug operations, or --scan-near-greyscale is specified"
        )
    
    # Handle negation flags
    if args.no_lossless:
        args.lossless = False
    if args.no_grayscale:
        args.grayscale = False
    if args.no_auto_contrast:
        args.auto_contrast = False
    if args.no_auto_greyscale:
        args.auto_greyscale = False
    
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


def handle_dependency_operations(args, logger):
    """Handle dependency checking and installation operations."""
    if args.check_dependencies:
        logger.info("Checking dependencies...")
        dep_status = check_and_install_dependencies(logger, auto_install=False)
        
        if dep_status['all_required_available']:
            logger.info("✓ All required dependencies are available")
            if not dep_status.get('missing_optional'):
                logger.info("✓ All optional dependencies are available")
            else:
                logger.info(f"○ {len(dep_status['missing_optional'])} optional dependencies are missing")
            return 0
        else:
            logger.error(f"✗ {len(dep_status['missing_required'])} required dependencies are missing")
            return 1
    
    elif args.install_dependencies:
        logger.info("Installing missing dependencies...")
        dep_status = check_and_install_dependencies(logger, auto_install=True)
        
        if dep_status.get('installation_success'):
            logger.info("✓ Dependencies installed successfully")
            return 0
        elif dep_status.get('all_required_available'):
            logger.info("✓ All required dependencies were already available")
            return 0
        else:
            logger.error("✗ Failed to install dependencies")
            return 1
    
    return None


def handle_debug_operations(args, logger):
    """
    Handle all debug operations. Returns exit code or None to continue normal processing.
    """
    from pathlib import Path
    
    # Handle single file debug (image or CBZ/CBR)
    if args.debug_auto_greyscale_single:
        file_path = Path(args.debug_auto_greyscale_single).resolve()
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return 1
        
        output_dir = Path(args.debug_output_dir).resolve() if args.debug_output_dir else file_path.parent
        
        # Get thresholds from args or defaults - need to handle preset application
        pixel_threshold = getattr(args, 'auto_greyscale_pixel_threshold', None)
        percent_threshold = getattr(args, 'auto_greyscale_percent_threshold', None)
        
        # If thresholds are None, apply preset defaults
        if pixel_threshold is None or percent_threshold is None:
            # Apply preset to get defaults
            from .presets import apply_preset_with_overrides
            preset_params = apply_preset_with_overrides(getattr(args, 'preset', 'default'), {}, logger)
            
            if pixel_threshold is None:
                pixel_threshold = preset_params.get('auto_greyscale_pixel_threshold', 16)
            if percent_threshold is None:
                percent_threshold = preset_params.get('auto_greyscale_percent_threshold', 0.01)
        
        result = debug_single_file_greyscale(
            file_path, output_dir, pixel_threshold, percent_threshold, logger
        )
        
        if result:
            logger.info(f"\nDebug files saved to: {output_dir / 'debug_auto_greyscale'}")
            return 0
        else:
            return 1
    
    # Handle threshold testing
    if args.debug_test_thresholds:
        image_path = Path(args.debug_test_thresholds).resolve()
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return 1
        
        output_dir = Path(args.debug_output_dir).resolve() if args.debug_output_dir else image_path.parent
        
        result = test_threshold_ranges(image_path, output_dir, logger)
        if result:
            return 0
        else:
            return 1
    
    # Handle directory analysis
    if args.debug_analyze_directory:
        directory_path = Path(args.debug_analyze_directory).resolve()
        if not directory_path.exists() or not directory_path.is_dir():
            logger.error(f"Directory not found: {directory_path}")
            return 1
        
        # Get thresholds from args or defaults - need to handle preset application
        pixel_threshold = getattr(args, 'auto_greyscale_pixel_threshold', None)
        percent_threshold = getattr(args, 'auto_greyscale_percent_threshold', None)
        
        # If thresholds are None, apply preset defaults
        if pixel_threshold is None or percent_threshold is None:
            # Apply preset to get defaults
            from .presets import apply_preset_with_overrides
            preset_params = apply_preset_with_overrides(getattr(args, 'preset', 'default'), {}, logger)
            
            if pixel_threshold is None:
                pixel_threshold = preset_params.get('auto_greyscale_pixel_threshold', 16)
            if percent_threshold is None:
                percent_threshold = preset_params.get('auto_greyscale_percent_threshold', 0.01)
        
        result = analyze_directory_for_auto_greyscale(
            directory_path, pixel_threshold, percent_threshold, logger
        )
        if result:
            return 0
        else:
            return 1
    
    # No debug operations requested
    return None


def handle_scan_near_greyscale(input_path, args, logger):
    """Scan archives for near greyscale images and take the requested action."""
    from .near_greyscale_scan import scan_directory_for_near_greyscale
    pixel_threshold = getattr(args, 'auto_greyscale_pixel_threshold', 16)
    percent_threshold = getattr(args, 'auto_greyscale_percent_threshold', 0.01)
    threads = args.threads if args.threads != 0 else os.cpu_count() or 1

    list_file = None
    if args.scan_near_greyscale == 'dryrun':
        if args.scan_output:
            candidate = Path(args.scan_output)
            if candidate.exists() and candidate.is_dir():
                list_file = candidate / 'near_greyscale_list.txt'
            else:
                list_file = candidate
        else:
            list_file = Path('near_greyscale_list.txt')

    results, output_path = scan_directory_for_near_greyscale(
        input_path,
        args.recursive,
        pixel_threshold,
        percent_threshold,
        threads,
        logger,
        list_file,
    )

    if args.scan_near_greyscale == 'dryrun':
        for a, near, total in results:
            logger.info(f"{a}\t{near}/{total}")
        if output_path:
            logger.info(f"Listed {len(results)} archives to {output_path}")
        return 0

    if args.scan_near_greyscale == 'move':
        if not args.scan_output:
            logger.error("--scan-output is required for move mode")
            return 1
        dest_dir = Path(args.scan_output).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
        moved = 0
        for a, near, total in results:
            target = dest_dir / a.name
            shutil.move(str(a), target)
            logger.info(f"Moved {a} ({near}/{total}) -> {target}")
            moved += 1
        logger.info(f"Moved {moved} archives")
        return 0

    if args.scan_near_greyscale == 'process':
        processed = 0
        for a, near, total in results:
            success, _, _ = process_single_archive_file(a, a.parent, args, logger)
            if success and a.suffix.lower() != '.cbz':
                try:
                    a.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete {a}: {e}")
            if success:
                processed += 1
        logger.info(f"Processed {processed} archives")
        return 0 if processed == len(results) else 1

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
        lossless=args.lossless,
        grayscale=args.grayscale,
        auto_contrast=args.auto_contrast,
        auto_greyscale=args.auto_greyscale,
        auto_greyscale_pixel_threshold=args.auto_greyscale_pixel_threshold,
        auto_greyscale_percent_threshold=args.auto_greyscale_percent_threshold,
        preserve_auto_greyscale_png=args.preserve_auto_greyscale_png
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
            lossless=args.lossless,
            grayscale=args.grayscale,
            auto_contrast=args.auto_contrast,
            auto_greyscale=args.auto_greyscale,
            auto_greyscale_pixel_threshold=args.auto_greyscale_pixel_threshold,
            auto_greyscale_percent_threshold=args.auto_greyscale_percent_threshold,
            preserve_auto_greyscale_png=args.preserve_auto_greyscale_png
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
    
    # Handle dependency operations first
    dependency_result = handle_dependency_operations(args, logger)
    if dependency_result is not None:
        return dependency_result
    
    # Check dependencies early unless user explicitly wants to skip
    if not getattr(args, 'skip_dependency_check', False):
        dep_status = check_and_install_dependencies(logger, auto_install=False)
        if not dep_status['all_required_available']:
            if not dep_status.get('user_declined', False):
                logger.error("Required dependencies are missing. Please install them and try again.")
                return 1

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
    
    # Handle debug operations (check for debug modes early)
    debug_exit_code = handle_debug_operations(args, logger)
    if debug_exit_code is not None:
        return debug_exit_code

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
        'method', 'preprocessing',
        'zip_compression', 'lossless',
        'grayscale', 'auto_contrast',
        'auto_greyscale', 'auto_greyscale_pixel_threshold', 'auto_greyscale_percent_threshold',
        'preserve_auto_greyscale_png'
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

    if args.scan_near_greyscale:
        return handle_scan_near_greyscale(input_path, args, logger)
    
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
