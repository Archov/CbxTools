#!/usr/bin/env python3
"""
Command-line interface for CBZ/CBR to WebP converter.
Enhanced with automatic greyscale detection, conversion, and dependency management.
"""
import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

from .core.file_processor import find_processable_items
from .presets import (
    apply_preset_with_overrides,
    list_available_presets,
)
from .stats_tracker import StatsTracker
from .utils import setup_logging

SAFE_PIP_REQUIREMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-\[\],=<>!~+]*$")


def sanitize_pip_requirement(requirement):
    """Validate requirement strings passed to ``pip install``.

    Returns the sanitized requirement string when it is safe to forward to
    ``pip``. ``None`` is returned when the value is empty, resembles a pip
    option, or contains potentially unsafe characters.
    """

    requirement = requirement.strip()
    if not requirement:
        return None
    # Prevent passing pip options (which begin with '-') as package names.
    if requirement.startswith("-"):
        return None
    if not SAFE_PIP_REQUIREMENT_PATTERN.fullmatch(requirement):
        return None
    return requirement

# Global settings management
DEFAULT_CONFIG_DIR = Path.home() / ".cbxtools"
DEFAULT_SETTINGS_FILE = DEFAULT_CONFIG_DIR / "settings.json"


def load_global_settings():
    """Load global settings from JSON file."""
    if DEFAULT_SETTINGS_FILE.exists():
        try:
            with open(DEFAULT_SETTINGS_FILE, encoding="utf-8") as f:
                return json.load(f), None
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in settings file: {e}"
            print(f"Warning: {error_msg}", file=sys.stderr)
            return {}, error_msg
        except OSError as e:
            error_msg = f"Error reading settings file: {e}"
            print(f"Warning: {error_msg}", file=sys.stderr)
            return {}, error_msg
    return {}, None


def save_global_settings(settings):
    """Save global settings to JSON file."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(DEFAULT_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        return True, None
    except OSError as e:
        error_msg = f"Error saving settings file: {e}"
        print(f"Error: {error_msg}", file=sys.stderr)
        return False, error_msg


def apply_global_settings(args, logger=None):
    """Apply global settings from saved configuration, but don't override explicit args."""
    settings, error = load_global_settings()
    if error and logger:
        logger.warning(f"Could not load global settings: {error}")
    # Add settings as attributes only if not already set by command line
    if (not hasattr(args, "verbose") or not args.verbose) and settings.get("verbose", False):
        args.verbose = True
    if (not hasattr(args, "silent") or not args.silent) and settings.get("silent", False):
        args.silent = True
    unset_threads = not hasattr(args, "threads") or args.threads in (None, 0)
    if unset_threads and "threads" in settings:
        args.threads = settings["threads"]
    return args


def parse_requirements_file(requirements_path):
    """
    Parse requirements.txt file and categorize dependencies.
    Args:
        requirements_path: Path to requirements.txt file
    Returns:
        dict: Categorized dependencies with package info
    """
    dependencies = {"required": {}, "optional": {}}
    try:
        with open(requirements_path, encoding="utf-8") as f:
            current_category = "optional"  # Default category
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Split line into requirement and comment parts
                if "#" in line:
                    parts = line.split("#", 1)
                    requirement_part = parts[0].strip()
                    comment_part = parts[1].strip() if len(parts) > 1 else ""
                else:
                    requirement_part = line
                    comment_part = ""
                # Check for section markers (comment-only lines with section
                # headers)
                if not requirement_part and comment_part:
                    if "required" in comment_part.lower():
                        current_category = "required"
                        continue
                    elif "optional" in comment_part.lower():
                        current_category = "optional"
                        continue
                # Skip pure comment lines (no requirement part)
                if not requirement_part or requirement_part.startswith("#"):
                    continue
                # Use current category (set by section markers)
                category = current_category
                # Preserve full requirement spec with version pins
                package_name = requirement_part
                # Compute import-lookup key by stripping extras and version operators
                # Remove extras in [...] and version specifiers to get base
                # package name
                import_lookup_key = re.split(r"[\[\]>=<~=!]+", requirement_part)[
                    0
                ].strip()
                # Map package names to import names
                import_name_map = {
                    "pillow": "PIL",
                    "rarfile": "rarfile",
                    "py7zr": "py7zr",
                    "numpy": "numpy",
                    "matplotlib": "matplotlib",
                    "patool": "patoolib",
                }
                import_name = import_name_map.get(
                    import_lookup_key.lower(), import_lookup_key.lower()
                )
                dependencies[category][import_name] = {
                    "import_name": import_name,
                    "package_name": package_name,
                    "description": comment_part or f"{import_lookup_key} package",
                    "available": False,
                }
    except FileNotFoundError:
        # Fallback to minimal hardcoded list if requirements.txt not found
        dependencies = {
            "required": {
                "PIL": {
                    "import_name": "PIL",
                    "package_name": "pillow",
                    "description": "Required for image processing",
                    "available": False,
                }
            },
            "optional": {},
        }
    return dependencies


def check_and_install_dependencies(logger, auto_install=False):
    """
    Check for required and optional dependencies and offer to install missing ones.
    Parses requirements.txt for dependency information instead of using hardcoded lists.
    Args:
        logger: Logger instance
        auto_install: If True, automatically install missing dependencies
    Returns:
        dict: Status of dependencies
    """
    # Parse requirements.txt for dependency information
    requirements_path = Path(__file__).parent.parent / "requirements.txt"
    dependencies = parse_requirements_file(requirements_path)
    # Check which dependencies are available
    for _category, deps in dependencies.items():
        for _name, info in deps.items():
            try:
                __import__(info["import_name"])
                info["available"] = True
            except ImportError:
                info["available"] = False
    # Report status
    missing_required = []
    missing_optional = []
    for name, info in dependencies["required"].items():
        if info["available"]:
            logger.debug(f"✓ {name} is available")
        else:
            logger.warning(f"✗ {name} is missing - {info['description']}")
            missing_required.append(info)
    for name, info in dependencies["optional"].items():
        if info["available"]:
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
        # For optional dependencies, just log and continue
        if missing_optional:
            logger.info(
                f"Missing {len(missing_optional)} optional dependencies; continuing without them."
            )
        # Only prompt for required dependencies
        if missing_required:
            if auto_install:
                return install_dependencies(missing_required, logger)
            else:
                return offer_to_install_dependencies(missing_required, logger)
    # If no missing dependencies, return success status
    return {
        "all_required_available": True,
        "missing_required": [],
        "missing_optional": [],
    }


def normalize_package_name(package_name):
    """
    Normalize a package name by lowercasing and stripping version specifiers.
    Args:
        package_name: Package name string, potentially with version specifiers
    Returns:
        str: Normalized package name (lowercase, no version specifiers)
    """
    # Remove extras in [...] and version specifiers to get base package name
    normalized = re.split(r"[\[\]>=<~=!]+", package_name)[0].strip().lower()
    return normalized


def offer_to_install_dependencies(missing_deps, logger, all_dependencies=None):
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
    logger.info(
        "  3. Install manually with: pip install "
        + " ".join(dep["package_name"] for dep in missing_deps)
    )
    logger.info("  4. Continue without installing (some features may not work)")
    try:
        choice = input("\nChoose an option (1-4): ").strip()
        if choice == "1":
            return install_dependencies(missing_deps, logger)
        elif choice == "2":
            # Filter for required dependencies only
            if all_dependencies and "required" in all_dependencies:
                # Derive required packages from parsed dependencies
                required_package_names = [
                    normalize_package_name(dep["package_name"])
                    for dep in all_dependencies["required"].values()
                ]
                required_deps = [
                    dep
                    for dep in missing_deps
                    if normalize_package_name(dep["package_name"])
                    in required_package_names
                ]
            else:
                # Parse requirements.txt to get required packages dynamically
                requirements_path = Path(__file__).parent.parent / "requirements.txt"
                try:
                    dependencies = parse_requirements_file(requirements_path)
                    required_package_names = [
                        normalize_package_name(dep["package_name"])
                        for dep in dependencies["required"].values()
                    ]
                    required_deps = [
                        dep
                        for dep in missing_deps
                        if normalize_package_name(dep["package_name"])
                        in required_package_names
                    ]
                except Exception:
                    # Ultimate fallback to minimal hardcoded list
                    required_package_names_lower = ["pillow"]
                    required_deps = [
                        dep
                        for dep in missing_deps
                        if normalize_package_name(dep["package_name"])
                        in required_package_names_lower
                    ]
            if not required_deps:
                logger.info(
                    "No required dependencies found in missing dependencies list."
                )
                logger.info("Continuing without installing dependencies...")
                return {"all_required_available": False, "user_declined": True}
            return install_dependencies(required_deps, logger)
        elif choice == "3":
            packages = " ".join(dep["package_name"] for dep in missing_deps)
            logger.info("\nTo install manually, run this command:")
            logger.info(f"  pip install {packages}")
            logger.info("\nOr use the built-in installer:")
            logger.info(f"  {sys.argv[0]} --install-dependencies")
            return {"all_required_available": False, "user_declined": True}
        else:
            logger.info("Continuing without installing dependencies...")
            return {"all_required_available": False, "user_declined": True}
    except (KeyboardInterrupt, EOFError):
        logger.info("\nInstallation cancelled by user.")
        return {"all_required_available": False, "user_declined": True}


def install_dependencies(deps_to_install, logger):
    """
    Install dependencies using pip.
    Args:
        deps_to_install: List of dependency info dicts to install
        logger: Logger instance
    Returns:
        dict: Installation results
    """
    # Accept package requirements as-is (including version pins) while
    # validating they cannot be interpreted as pip options or contain unsafe
    # characters. This prevents command injection when invoking pip through
    # subprocess.
    packages = []
    for dep in deps_to_install:
        package_name = dep["package_name"]
        sanitized = sanitize_pip_requirement(package_name)
        if sanitized is None:
            logger.warning(
                "Skipping potentially unsafe package requirement: %s",
                package_name,
            )
            continue
        packages.append(sanitized)
    if not packages:
        logger.error("No valid packages to install")
        return {
            "all_required_available": False,
            "installation_error": "No valid packages",
        }
    logger.info("\nInstalling dependencies: %s", ", ".join(packages))
    # Check if pip is available
    try:
        # SECURITY: Static command - no user input involved
        subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            check=True,
            timeout=30,
        )
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        logger.error("pip is not available or not working properly")
        logger.error("Please install pip first or install packages manually:")
        logger.error(f"  pip install {' '.join(shlex.quote(pkg) for pkg in packages)}")
        return {"all_required_available": False, "pip_unavailable": True}
    try:
        # Use subprocess to install packages. Arguments are passed as a list to
        # avoid shell interpretation and package names are validated above to
        # block option-style injections.
        cmd_prefix = [sys.executable, "-m", "pip", "install"]
        cmd = cmd_prefix + packages
        logger.info("Running: %s", " ".join(shlex.quote(part) for part in cmd))
        # Explicitly disable shell to ensure no shell interpretation
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, shell=False)
        if result.returncode == 0:
            logger.info("✓ Dependencies installed successfully!")
            logger.info(
                "Note: You may need to restart the application for changes to take effect."
            )
            return {
                "all_required_available": True,
                "installation_success": True,
            }
        else:
            logger.error("Failed to install dependencies:")
            if result.stdout.strip():
                logger.error(f"STDOUT: {result.stdout.strip()}")
            if result.stderr.strip():
                logger.error(f"STDERR: {result.stderr.strip()}")
            logger.error(
                "You may need to install packages manually or with elevated privileges."
            )
            return {
                "all_required_available": False,
                "installation_failed": True,
            }
    except subprocess.TimeoutExpired:
        logger.error("Installation timed out after 5 minutes")
        return {"all_required_available": False, "installation_timeout": True}
    except Exception as e:
        logger.error(f"Error during installation: {e}")
        return {"all_required_available": False, "installation_error": str(e)}


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom formatter that provides better line wrapping for the usage line."""

    def _format_usage(self, usage, actions, groups, prefix):
        """Override to provide better usage line formatting."""
        if prefix is None:
            prefix = "usage: "
        # Get the program name
        if self._prog:
            prog = self._prog
        else:
            prog = "%(prog)s"
        # Create a more readable usage line for the new subcommand structure
        usage_text = f"{prefix}{prog} [GLOBAL_OPTIONS] <command> [COMMAND_OPTIONS]"
        return usage_text


def parse_arguments():
    """Parse command line arguments using subcommands for better organization."""
    # Main parser
    parser = argparse.ArgumentParser(
        prog="cbxtools",
        epilog="""CBXTools - Convert CBZ/CBR comic archives to WebP format with automatic greyscale detection
Examples:
  %(prog)s convert input.cbz output/
  %(prog)s convert --quality 85 --auto-greyscale comics/ output/
  %(prog)s watch --delete-originals input/ output/
  %(prog)s debug analyze image.jpg
  %(prog)s config presets --list
For help on a specific command, use: %(prog)s <command> --help""",
        formatter_class=CustomHelpFormatter,
        add_help=False,
    )
    # Global options (minimal set)
    # Note: stats-related options moved to stats subcommand
    # Add help argument (appears last in options list)
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    # Subparsers for commands
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", metavar="COMMAND"
    )
    # Convert command (default/main command)
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert comic archives to WebP format",
        description="Convert comic archives to WebP format with automatic greyscale detection.",
        usage="cbxtools [GLOBAL_OPTIONS] convert [OPTIONS] input_path [output_dir]",
        add_help=False,
    )
    convert_parser.set_defaults(
        func=handle_convert_command,
        verbose=False,
        silent=False,
        threads=0,
        keep_originals=False,
        no_cbz=False,
        zip_compression=6,
    )
    _add_convert_arguments(convert_parser)
    # Watch command
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch directory for new files and process automatically",
        description="Watch directory for new comic files and process them automatically.",
        usage="cbxtools [GLOBAL_OPTIONS] watch [OPTIONS] input_path output_dir",
        add_help=False,
    )
    watch_parser.set_defaults(func=handle_watch_command)
    _add_watch_arguments(watch_parser)
    # Debug command with subcommands
    debug_parser = subparsers.add_parser(
        "debug",
        help="Debug and analysis tools for greyscale detection",
        description="Debug and analysis tools for greyscale detection.",
        usage="cbxtools [GLOBAL_OPTIONS] debug [OPTIONS] SUBCOMMAND ...",
        add_help=False,
    )
    debug_parser.set_defaults(func=handle_debug_command)
    _add_debug_arguments(debug_parser)
    # Scan command with subcommands
    scan_parser = subparsers.add_parser(
        "scan",
        help="Bulk scanning and processing operations",
        description="Bulk scanning and processing operations.",
        usage="cbxtools [GLOBAL_OPTIONS] scan [OPTIONS] SUBCOMMAND ...",
        add_help=False,
    )
    scan_parser.set_defaults(func=handle_scan_command)
    _add_scan_arguments(scan_parser)
    # Config command with subcommands
    config_parser = subparsers.add_parser(
        "config",
        help="Manage presets and settings files",
        description="Manage presets and settings files.",
        usage="cbxtools [GLOBAL_OPTIONS] config [OPTIONS] SUBCOMMAND ...",
        add_help=False,
    )
    config_parser.set_defaults(func=handle_config_command)
    _add_config_arguments(config_parser)
    # Stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Display and manage usage statistics",
        description="Display and manage usage statistics.",
        usage="cbxtools [GLOBAL_OPTIONS] stats [--file FILE] [SUBCOMMAND]",
        add_help=False,
    )
    stats_parser.set_defaults(func=handle_stats_command)
    _add_stats_arguments(stats_parser)
    args = parser.parse_args()
    # If no command specified, show help
    if args.command is None:
        parser.print_help()
        return None
    return args


def _add_convert_arguments(parser):
    """Add arguments for the convert command."""
    # Quality & Compression
    quality_group = parser.add_argument_group("Quality & Compression")
    quality_group.add_argument(
        "--quality",
        "-q",
        type=int,
        default=80,
        help="WebP compression quality (0-100, default: 80)",
    )
    quality_group.add_argument(
        "--lossless",
        action="store_true",
        help="Use lossless WebP compression (higher quality, larger files)",
    )
    quality_group.add_argument(
        "--method",
        type=int,
        choices=range(7),
        default=4,
        help="WebP compression method (0-6, higher = better/slower, default: 4)",
    )
    # Image Processing
    processing_group = parser.add_argument_group("Image Processing")
    processing_group.add_argument(
        "--max-width", type=int, help="Maximum width in pixels (0 = unlimited)"
    )
    processing_group.add_argument(
        "--max-height",
        type=int,
        help="Maximum height in pixels (0 = unlimited)",
    )
    processing_group.add_argument(
        "--preprocessing",
        choices=["none", "unsharp_mask", "reduce_noise"],
        help="Apply preprocessing before compression",
    )
    # Transformations
    transform_group = parser.add_argument_group("Transformations")
    transform_group.add_argument(
        "--grayscale",
        action="store_true",
        help="Convert all images to grayscale",
    )
    transform_group.add_argument(
        "--auto-contrast",
        action="store_true",
        help="Apply automatic contrast enhancement",
    )
    transform_group.add_argument(
        "--auto-greyscale",
        action="store_true",
        help="Auto-detect and convert near-greyscale images",
    )
    transform_group.add_argument(
        "--greyscale-threshold-pixel",
        type=int,
        default=16,
        dest="auto_greyscale_pixel_threshold",
        help="Pixel difference threshold for auto-greyscale (default: 16)",
    )
    transform_group.add_argument(
        "--greyscale-threshold-percent",
        type=float,
        default=0.01,
        dest="auto_greyscale_percent_threshold",
        help="Percentage threshold for auto-greyscale (default: 0.01)",
    )
    # Output
    output_group = parser.add_argument_group("Output")
    output_group.add_argument(
        "--output",
        "-o",
        choices=["folder", "cbz", "zip", "cb7", "7z"],
        default="cbz",
        help="Output format (default: cbz)",
    )
    output_group.add_argument(
        "--compression",
        type=int,
        choices=range(10),
        default=6,
        dest="zip_compression",
        help="Archive compression level (0-9, default: 6)",
    )
    # General Processing
    general_group = parser.add_argument_group("General Processing")
    available_presets = list_available_presets()
    general_group.add_argument(
        "--preset",
        choices=available_presets,
        default="default",
        help=f'Use preset profile (available: {", ".join(available_presets)})',
    )
    general_group.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Process subdirectories recursively",
    )
    general_group.add_argument(
        "--threads",
        type=int,
        default=0,
        help="Number of worker threads to use (0 = auto-detect)",
    )
    general_group.add_argument(
        "--keep-originals",
        action="store_true",
        help="Keep source archives after successful conversion",
    )
    general_group.add_argument(
        "--no-cbz",
        dest="no_cbz",
        action="store_true",
        help="Skip creating CBZ/ZIP output archives",
    )
    general_group.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    # Positional arguments
    parser.add_argument(
        "input_path",
        help="Path to CBZ/CBR file or directory containing multiple archives",
    )
    parser.add_argument(
        "output_dir", nargs="?", help="Output directory for processed files"
    )


def _add_watch_arguments(parser):
    """Add arguments for the watch command."""
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Check interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--delete-originals",
        action="store_true",
        help="Delete source files after successful processing",
    )
    parser.add_argument(
        "--clear-history",
        action="store_true",
        help="Clear processing history before starting",
    )
    # Positional arguments
    parser.add_argument("input_path", help="Directory to watch for new files")
    parser.add_argument("output_dir", help="Output directory for processed files")
    # Add help argument last
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )


def _add_debug_arguments(parser):
    """Add arguments for the debug command."""
    # Global debug options
    parser.add_argument(
        "--debug-output", type=str, help="Output directory for debug files"
    )
    parser.add_argument(
        "--preserve-png",
        action="store_true",
        help="Keep intermediate PNG files from auto-greyscale conversion",
    )
    # Debug subcommands
    subparsers = parser.add_subparsers(
        dest="debug_command", help="Debug operations", metavar="SUBCOMMAND"
    )
    # Analyze subcommand
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze images/archives for greyscale content"
    )
    analyze_parser.add_argument("input", help="Image, archive, or directory to analyze")
    # Test-thresholds subcommand
    test_parser = subparsers.add_parser(
        "test-thresholds",
        help="Test different threshold combinations on an image",
    )
    test_parser.add_argument("image", help="Image file to test")
    # Add help argument last
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )


def _add_scan_arguments(parser):
    """Add arguments for the scan command."""
    # Scan subcommands
    subparsers = parser.add_subparsers(
        dest="scan_command", help="Scan operations", metavar="SUBCOMMAND"
    )
    # Greyscale scan subcommand
    greyscale_parser = subparsers.add_parser(
        "greyscale", help="Scan for near-greyscale archives"
    )
    greyscale_parser.add_argument(
        "--action",
        choices=["list", "move", "process"],
        default="list",
        help="Action to take (default: list)",
    )
    greyscale_parser.add_argument(
        "--output",
        type=str,
        help="Output file (for list) or directory (for move)",
    )
    greyscale_parser.add_argument("input_path", help="Directory to scan for archives")
    # Add help argument last
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )


def _add_config_arguments(parser):
    """Add arguments for the config command."""
    # Configurable global options
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output globally",
    )
    parser.add_argument(
        "--silent",
        "-s",
        action="store_true",
        help="Suppress all output except errors globally",
    )
    parser.add_argument(
        "--threads",
        type=int,
        help="Set default number of parallel threads to use (0 = auto-detect)",
    )
    # Config subcommands
    subparsers = parser.add_subparsers(
        dest="config_command",
        help="Configuration operations",
        metavar="SUBCOMMAND",
    )
    # Presets subcommand
    presets_parser = subparsers.add_parser("presets", help="Manage conversion presets")
    presets_parser.add_argument(
        "--list", action="store_true", help="List all available presets"
    )
    presets_parser.add_argument(
        "--save",
        type=str,
        metavar="NAME",
        help="Save current settings as a new preset",
    )
    presets_parser.add_argument(
        "--import-file",
        type=str,
        metavar="FILE",
        dest="import_file",
        help="Import presets from JSON file",
    )
    presets_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing presets when saving/importing",
    )
    # Settings subcommand
    settings_parser = subparsers.add_parser("settings", help="Manage settings files")
    settings_parser.add_argument(
        "--init",
        type=str,
        nargs="?",
        const="cbxtools-settings.json",
        help="Create a settings template file",
    )
    settings_parser.add_argument(
        "--save",
        type=str,
        metavar="FILE",
        help="Save current settings to file",
    )
    # Add help argument last
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )


def _add_stats_arguments(parser):
    """Add arguments for the stats command."""
    # Stats configuration options
    parser.add_argument(
        "--file", type=str, metavar="FILE", help="Specify stats file path"
    )
    parser.add_argument(
        "--disable", action="store_true", help="Disable statistics tracking"
    )
    # Stats subcommands
    subparsers = parser.add_subparsers(
        dest="stats_command",
        help="Statistics operations",
        metavar="SUBCOMMAND",
    )
    # Show subcommand (default)
    subparsers.add_parser("show", help="Show lifetime statistics", add_help=False)
    # Reset subcommand
    subparsers.add_parser("reset", help="Reset all statistics", add_help=False)
    # Disable subcommand
    subparsers.add_parser("disable", help="Disable statistics tracking", add_help=False)
    # Add help argument last
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )


def handle_convert_command(args, logger, stats_tracker=None):
    """Handle the convert command."""
    from pathlib import Path

    # Apply preset if specified
    if hasattr(args, "preset") and args.preset != "default":
        try:
            parser_defaults = {
                "quality": 80,
                "lossless": False,
                "method": 4,
                "max_width": None,
                "max_height": None,
                "preprocessing": None,
                "grayscale": False,
                "auto_contrast": False,
                "auto_greyscale": False,
                "auto_greyscale_pixel_threshold": 16,
                "auto_greyscale_percent_threshold": 0.01,
                "output": "cbz",
               "zip_compression": 6,
                "recursive": False,
            }
            overrides = {
                key: getattr(args, key)
                for key, default in parser_defaults.items()
                if hasattr(args, key) and getattr(args, key) != default
            }
            
            # Apply preset with overrides
            preset_params_dict = apply_preset_with_overrides(args.preset, overrides, logger=logger)
            
            # Merge the returned dict into the existing args namespace
            for key, value in preset_params_dict.items():
                setattr(args, key, value)
            
            logger.debug(f"Applied preset: {args.preset}")
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to apply preset '{args.preset}': {e}")
            return 1
    # Validate input path
    try:
        input_path = Path(args.input_path).resolve()
        if not input_path.exists():
            logger.error(f"Input path does not exist: {input_path}")
            return 1
    except (OSError, ValueError) as e:
        logger.error(f"Invalid input path: {e}")
        return 1
    # Determine output directory
    if hasattr(args, "output_dir") and args.output_dir:
        output_dir = Path(args.output_dir).resolve()
    else:
        # Default to current directory with _converted suffix
        if input_path.is_file():
            output_dir = input_path.parent / f"{input_path.stem}_converted"
        else:
            output_dir = input_path.parent / f"{input_path.name}_converted"
    # Create output directory if it doesn't exist
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create output directory {output_dir}: {e}")
        return 1
    logger.info(f"Converting: {input_path}")
    logger.info(f"Output to: {output_dir}")
    # Find archives to process
    try:
        if input_path.is_file():
            # Single file
            archives = [input_path]
        else:
            # Directory - find all processable items
            recursive = getattr(args, "recursive", False)
            archives = find_processable_items(input_path, recursive=recursive)
        if not archives:
            logger.warning("No archives found to process")
            return 0
        logger.info(f"Found {len(archives)} items to process")
    except (OSError, ValueError) as e:
        logger.error(f"Failed to find archives: {e}")
        return 1
    # Process archives
    try:
        start_time = time.time()
        # Call the conversion function
        from .conversion import process_archive_files

        (
            success_count,
            total_original_size,
            total_new_size,
            _processed_files,
        ) = process_archive_files(archives, output_dir, args, logger)
        # Calculate execution time
        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        # Print summary
        if success_count > 0:
            logger.info(
                f"\n✓ Successfully processed {success_count} of {len(archives)} archives"
            )
            logger.info(f"Execution time: {int(minutes)}m {seconds:.1f}s")
            if total_original_size > 0 and total_new_size > 0:
                compression_ratio = (1 - total_new_size / total_original_size) * 100
                logger.info(f"Space saved: {compression_ratio:.1f}%")
            # Update stats if available
            if stats_tracker:
                stats_tracker.add_run(
                    files_processed=success_count,
                    original_size=total_original_size,
                    new_size=total_new_size,
                    execution_time=execution_time,
                )
        else:
            logger.warning("No archives were successfully processed")
        return 0 if success_count > 0 else 1
    except (OSError, ValueError, ImportError) as e:
        logger.error(f"Error during conversion: {e}")
        return 1


def handle_watch_command(args, logger, stats_tracker=None):
    """Handle the watch command."""
    logger.error("Watch command not yet implemented")
    return 1


def handle_debug_command(args, logger, stats_tracker=None):
    """Handle the debug command."""
    if hasattr(args, "debug_command") and args.debug_command:
        if args.debug_command == "analyze":
            return handle_debug_analyze(args, logger)
        elif args.debug_command == "test-thresholds":
            return handle_debug_test_thresholds(args, logger)
    else:
        logger.error("No debug subcommand specified")
        return 1


def handle_scan_command(args, logger, stats_tracker=None):
    """Handle the scan command."""
    if hasattr(args, "scan_command") and args.scan_command:
        if args.scan_command == "greyscale":
            return handle_scan_greyscale(args, logger)
    else:
        logger.error("No scan subcommand specified")
        return 1


def handle_debug_analyze(args, logger):
    """Handle debug analyze subcommand."""
    logger.error("Debug analyze not yet implemented")
    return 1


def handle_debug_test_thresholds(args, logger):
    """Handle debug test-thresholds subcommand."""
    logger.error("Debug test-thresholds not yet implemented")
    return 1


def handle_scan_greyscale(args, logger):
    """Handle scan greyscale subcommand."""
    logger.error("Scan greyscale not yet implemented")
    return 1


def handle_config_presets(args, logger):
    """Handle config presets subcommand."""
    if hasattr(args, "list") and args.list:
        # Import here to avoid circular imports
        from .presets import list_available_presets

        presets = list_available_presets()
        logger.info("\nAvailable presets:")
        for preset in presets:
            logger.info(f"  - {preset}")
        return 0
    elif hasattr(args, "save") and args.save:
        logger.error("Saving presets from command line not yet implemented")
        return 1
    elif hasattr(args, "import_file") and args.import_file:
        from pathlib import Path

        from .presets import import_presets_from_file

        import_path = Path(args.import_file).resolve()
        if not import_path.exists():
            logger.error(f"Import file not found: {import_path}")
            return 1
        try:
            result = import_presets_from_file(
                import_path,
                overwrite=getattr(args, "overwrite", False),
                logger=logger,
            )
            if result > 0:
                logger.info(f"Successfully imported {result} presets")
                return 0
            else:
                logger.error("Failed to import presets")
                return 1
        except Exception as e:
            logger.error(f"Error importing presets from {import_path}: {e}")
            return 1
    else:
        logger.error("No preset operation specified")
        return 1


def handle_config_settings(args, logger):
    """Handle config settings subcommand."""
    if args.init:
        logger.error("Settings file creation not yet implemented")
        return 1
    elif args.save:
        logger.error("Settings file saving not yet implemented")
        return 1
    else:
        logger.error("No settings operation specified")
        return 1


def handle_config_command(args, logger, stats_tracker=None):
    """Handle the config command."""
    # Handle subcommands
    if hasattr(args, "config_command") and args.config_command:
        if args.config_command == "presets":
            return handle_config_presets(args, logger)
        elif args.config_command == "settings":
            return handle_config_settings(args, logger)
    else:
        # Save global configuration options (explicit save-globals behavior)
        settings, _ = load_global_settings()
        settings = settings.copy()
        if hasattr(args, "verbose") and args.verbose:
            settings["verbose"] = True
        if hasattr(args, "silent") and args.silent:
            settings["silent"] = True
        if hasattr(args, "threads") and args.threads is not None:
            settings["threads"] = args.threads
        if settings:
            logger.info("Saving global settings...")
            success, error = save_global_settings(settings)
            if success:
                logger.info("✓ Global settings saved successfully")
                return 0
            else:
                logger.error(f"Failed to save global settings: {error}")
                return 1
        else:
            logger.info(
                "No settings to save. Use --verbose, --silent, or --threads to set global options."
            )
            logger.info("Note: This command now explicitly saves global settings when options are provided.")
            return 0


def handle_stats_command(args, logger, stats_tracker=None):
    """Handle the stats command."""
    # Handle --file option (global for stats command)
    if hasattr(args, "file") and args.file:
        # Would create/use a different stats tracker
        logger.info(f"Using custom stats file: {args.file}")
    # Handle --disable option
    if hasattr(args, "disable") and args.disable:
        logger.info("Statistics tracking disabled")
        return 0
    # Handle subcommands
    stats_command = getattr(args, "stats_command", None)
    if stats_command == "show" or stats_command is None:
        # Default behavior - show stats
        if stats_tracker:
            from .stats_tracker import print_lifetime_stats

            print_lifetime_stats(stats_tracker, logger)
            return 0
        else:
            logger.error("Statistics tracking is disabled")
            return 1
    elif stats_command == "reset":
        logger.error("Stats reset not yet implemented")
        return 1
    elif stats_command == "disable":
        logger.info("Statistics tracking disabled")
        return 0


def main():
    """Main entry point with new subcommand dispatch logic."""
    args = parse_arguments()
    # If parse_arguments returned None (invalid args), exit
    if args is None:
        return 1
    # Validate required arguments for each command
    if args.command == "convert":
        if not hasattr(args, "input_path") or args.input_path is None:
            print(
                "Error: input_path is required for convert command",
                file=sys.stderr,
            )
            return 1
    elif args.command == "watch":
        if not hasattr(args, "input_path") or args.input_path is None:
            print(
                "Error: input_path is required for watch command",
                file=sys.stderr,
            )
            return 1
        if not hasattr(args, "output_dir") or args.output_dir is None:
            print(
                "Error: output_dir is required for watch command",
                file=sys.stderr,
            )
            return 1
    # Apply global settings before configuring logging so verbosity is respected
    global_settings, _ = load_global_settings()
    args = apply_global_settings(args)
    effective_verbose = getattr(args, "verbose", False) or global_settings.get("verbose", False)
    effective_silent = getattr(args, "silent", False) or global_settings.get("silent", False)
    logger = setup_logging(effective_verbose, effective_silent)
    # Check dependencies early (automatic, no CLI control)
    # Skip dependency checks for commands that don't need them (config, stats,
    # help-like commands)
    skip_dep_check_commands = {"config", "stats"}
    if args.command not in skip_dep_check_commands:
        dep_status = check_and_install_dependencies(logger, auto_install=False)
        if not dep_status["all_required_available"] and not dep_status.get("user_declined", False):
            logger.error(
                "Required dependencies are missing. Please install them and try again."
            )
            return 1
    # Initialize stats tracker
    # For stats command, check its options; for other commands, enable by
    # default
    if args.command == "stats":
        # Stats command handles its own options
        stats_file = getattr(args, "file", None)
        disable_stats = getattr(args, "disable", False)
        stats_tracker = None if disable_stats else StatsTracker(stats_file)
    else:
        # Enable stats by default for other commands
        stats_tracker = StatsTracker()
    # Dispatch to appropriate command handler using func attribute
    return args.func(args, logger, stats_tracker)


if __name__ == "__main__":
    sys.exit(main())
