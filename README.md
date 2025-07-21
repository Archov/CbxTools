# CBXTools - Comic Book Archive to WebP Converter

A powerful tool for converting CBZ/CBR comic archives to WebP format, focusing on size reduction while maintaining quality. This tool preserves all non-image files, including metadata like ComicInfo.xml.

## Features

- Convert CBZ, CBR and CB7 archives (ZIP/RAR/7z) to WebP-based CBZ files
- Process individual images and entire folders
- Preserve metadata and all non-image files from the original archives
- Multi-threaded conversion with optional asynchronous packaging
- Customizable WebP compression parameters and preprocessing filters
- Manual grayscale and auto-contrast options
- Optional automatic greyscale detection with configurable thresholds (works in watch mode)
- Directory watching mode to automatically process new archives, images and image folders
- Built-in dependency checker with optional automatic installation
- Persistent lifetime statistics tracking and detailed reports
- Debug utilities for analysing greyscale detection
- Near greyscale scan mode to identify archives with mostly greyscale pages
- Support for batch processing with recursive directory scanning

## Installation

```bash
pip install cbxtools
```

## Quick Start

Convert a single comic archive:

```bash
cbxtools input.cbz output_directory/
```

Convert all comics in a directory:

```bash
cbxtools comics_directory/ output_directory/
```

Use a specific preset:

```bash
cbxtools input.cbz output_directory/ --preset comic
```

## Command Line Options

### Basic Options

```
cbxtools input_path output_dir [options]
```

- `input_path`: Path to a CBZ/CBR file or directory containing multiple archives
- `output_dir`: Output directory for WebP images and new CBZ files

### Quality Options

- `--quality VALUE`: WebP compression quality (0-100, default: 80 or from preset)
- `--max-width PIXELS`: Maximum width in pixels (0 = no restriction)
- `--max-height PIXELS`: Maximum height in pixels (0 = no restriction)

### Image Transformation Options

- `--grayscale`: Convert images to grayscale before compression
- `--no-grayscale`: Disable grayscale conversion even if preset enables it
- `--auto-contrast`: Apply automatic contrast enhancement before compression
- `--no-auto-contrast`: Disable auto-contrast even if preset enables it
- `--auto-greyscale`: Automatically detect and convert near-greyscale images to greyscale
- `--no-auto-greyscale`: Disable auto-greyscale even if preset enables it
- `--auto-greyscale-pixel-threshold VALUE`: Pixel difference threshold for auto-greyscale detection (default: 16)
- `--auto-greyscale-percent-threshold VALUE`: Percentage of colored pixels threshold for auto-greyscale (default: 0.01)
- `--preserve-auto-greyscale-png`: Preserve the intermediate PNG file during auto-greyscale conversion for debugging

### Advanced Compression Options

- `--method VALUE`: WebP compression method (0-6): higher = better compression but slower
- `--preprocessing {none, unsharp_mask, reduce_noise}`: Apply preprocessing to images before compression
- `--zip-compression VALUE`: ZIP compression level for CBZ (0-9)
- `--lossless`: Use lossless WebP compression (larger but perfect quality)
- `--no-lossless`: Disable lossless compression even if preset enables it

### Preset Options

- `--preset {default, comic, etc}`: Use a preset profile
- `--save-preset NAME`: Save current settings as a new preset
- `--import-preset FILE`: Import presets from a JSON file
- `--list-presets`: List all available presets and exit
- `--overwrite-preset`: Overwrite existing presets when saving or importing

### Output Options

- `--no-cbz`: Do not create a CBZ file with the WebP images
- `--keep-originals`: Keep the extracted WebP files after creating the CBZ
- `--recursive`: Recursively search for CBZ/CBR files in subdirectories
- `--threads NUM`: Number of parallel threads to use (0 = auto-detect)

### Logging/Stats Options

- `--verbose`, `-v`: Enable verbose output
- `--silent`, `-s`: Suppress all output except errors
- `--stats-file PATH`: Path to stats file (default: ~/.cbx-tools-stats.json)
- `--no-stats`: Do not update or display lifetime statistics
- `--stats-only`: Display lifetime statistics and exit

### Near Greyscale Scan Options

- `--scan-near-greyscale {dryrun,move,process}`: Scan archives for near-greyscale images and take action
  - `dryrun`: Generate a list of archives containing near-greyscale content
  - `move`: Move identified archives to a specified destination directory
  - `process`: Convert identified archives using current settings
- `--scan-output PATH`: Output file for dryrun mode or destination directory for move mode
  - For dryrun: If PATH is a directory, `near_greyscale_list.txt` will be created in that directory
  - For move: Destination directory where archives will be moved
  - When omitted in dryrun mode, creates `near_greyscale_list.txt` in the current directory

Scanning respects the `--threads` option for parallel processing and uses the current auto-greyscale threshold settings.

### Watch Mode Options

- `--watch`: Watch input directory for new files and process automatically
- `--watch-interval SECONDS`: Interval to check for new files in watch mode (default: 5)
- `--delete-originals`: Delete original files after successful conversion in watch mode
- `--clear-history`: Clear watch history file before starting watch mode

### Debug Options

- `--debug-auto-greyscale`: Enable detailed debugging for auto-greyscale detection
- `--debug-auto-greyscale-single FILE_PATH`: Analyze a single image or CBZ/CBR file for auto-greyscale debugging and exit
- `--debug-output-dir PATH`: Output directory for debug files (default: same as output_dir)
- `--debug-test-thresholds IMAGE_PATH`: Test multiple threshold combinations on a single image and exit
- `--debug-analyze-directory DIRECTORY_PATH`: Analyze all images and archives in directory with current thresholds and exit

### Dependency Management Options

- `--check-dependencies`: Check for required and optional dependencies and exit
- `--install-dependencies`: Automatically install missing dependencies and exit
- `--skip-dependency-check`: Skip dependency checking on startup

## Presets

CBXTools includes several built-in presets optimized for different types of content:

- `default`: Balanced settings for most comic types
- `comic`: Optimized for comic books with line art and text
- `photo`: Higher quality for photographic images
- `maximum_compression`: Maximum compression (lower quality)
- `maximum_quality`: Highest quality with optional lossless compression
- `manga`: Optimized for manga content with aggressive greyscale detection

You can view available presets with:

```bash
cbxtools --list-presets
```

## Auto-Greyscale Detection

CBXTools includes sophisticated auto-greyscale detection that can automatically identify and convert near-greyscale images to true greyscale with enhanced contrast. This feature is particularly useful for comics and manga that appear to be in color but are actually near-greyscale.

### How Auto-Greyscale Works

1. **Color Analysis**: Each image is analyzed pixel-by-pixel to detect color variation
2. **Threshold Evaluation**: Images with colored pixels below the specified thresholds are flagged for conversion
3. **Enhanced Conversion**: Flagged images undergo grayscale conversion + auto-contrast enhancement
4. **Quality Pipeline**: Images are processed through an intermediate PNG stage for optimal quality

### Debugging Auto-Greyscale

When debugging auto-greyscale behavior, use the `--preserve-auto-greyscale-png` option to save the intermediate PNG files alongside the final WebP output. This allows you to:

- Compare the intermediate PNG with your manual B&W.py output
- Verify the grayscale conversion quality
- Understand why results might differ between manual and automatic processing
- Analyze the exact state of images after the enhanced B&W conversion

The preserved PNG files will have the same name as the WebP files but with a `.png` extension.

### Tuning Auto-Greyscale Parameters

- `--auto-greyscale-pixel-threshold`: Lower values are more sensitive to color differences (default: 16)
- `--auto-greyscale-percent-threshold`: Lower values convert more images to greyscale (default: 0.01 = 1%)

## Near Greyscale Scanning

CBXTools can analyze your comic collection to identify archives that contain mostly near-greyscale content, helping you optimize your conversion strategy.

### Scan Modes

**Dry Run Mode**: Generate a list of archives with near-greyscale content
```bash
cbxtools --scan-near-greyscale dryrun manga_collection/
cbxtools --scan-near-greyscale dryrun --scan-output results/ manga_collection/
```

**Move Mode**: Relocate identified archives to a separate directory
```bash
cbxtools --scan-near-greyscale move --scan-output near_grey_archives/ manga_collection/
```

**Process Mode**: Convert identified archives immediately
```bash
cbxtools --scan-near-greyscale process manga_collection/ --preset manga
```

### Customizing Scan Thresholds

Use the same threshold options to control sensitivity:
```bash
cbxtools --scan-near-greyscale dryrun \
  --auto-greyscale-pixel-threshold 20 \
  --auto-greyscale-percent-threshold 0.02 \
  manga_collection/
```

## Examples

Convert a single CBZ file with the "comic" preset:

```bash
cbxtools my_comic.cbz output/ --preset comic
```

Convert with custom quality and compression settings:

```bash
cbxtools my_comic.cbz output/ --quality 85 --method 6
```

Convert with auto-greyscale detection and preserve intermediate PNG files for debugging:

```bash
cbxtools my_comic.cbz output/ --auto-greyscale --preserve-auto-greyscale-png
```

Convert all CBZ/CBR files in a directory recursively:

```bash
cbxtools comics/ output/ --recursive
```

Watch a directory for new files and convert them automatically:

```bash
cbxtools incoming/ output/ --watch --delete-originals
```

Show lifetime statistics:

```bash
cbxtools --stats-only
```

Scan a directory for near-greyscale archives without moving them:

```bash
cbxtools --scan-near-greyscale dryrun --scan-output "D:\Manga Backup" "D:\Manga Backup"
```

This creates `near_greyscale_list.txt` inside `D:\Manga Backup`.

Debug auto-greyscale detection on a specific archive:

```bash
cbxtools --debug-auto-greyscale-single test_comic.cbz
```

Test different threshold combinations on a problematic image:

```bash
cbxtools --debug-test-thresholds problem_image.jpg
```

Analyze an entire directory for auto-greyscale potential:

```bash
cbxtools --debug-analyze-directory manga_collection/
```

## Metadata Preservation

CBXTools automatically preserves all non-image files found in the original archive, including:

- ComicInfo.xml and other metadata files
- Info text files
- Cover images
- Any other auxiliary content

This ensures that comic readers can still access series information, publication details, and other metadata after conversion.

## License

MIT

## Contributing

Contributions welcome! See the [GitHub repository](https://github.com/Archov/CbxTools) for details.