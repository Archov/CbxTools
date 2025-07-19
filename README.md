# CBXTools - Comic Book Archive to WebP Converter

A powerful tool for converting CBZ/CBR comic archives to WebP format, focusing on size reduction while maintaining quality. This tool preserves all non-image files, including metadata like ComicInfo.xml.

## Features

- Convert CBZ, CBR and CB7 archives (ZIP/RAR/7z) to WebP-based CBZ files
- Process individual images and entire folders
- Preserve metadata and all non-image files from the original archives
- Multi-threaded conversion with optional asynchronous packaging
- Support for batch processing
- Customizable WebP compression parameters and preprocessing filters
- Manual grayscale and auto-contrast options
- Optional automatic greyscale detection with configurable thresholds
- Directory watching mode to automatically process new archives, images and image folders
- Built-in dependency checker with optional automatic installation
- Persistent lifetime statistics tracking and detailed reports
- Debug utilities for analysing greyscale detection


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

### Watch Mode Options

- `--watch`: Watch input directory for new files and process automatically
- `--watch-interval SECONDS`: Interval to check for new files in watch mode (default: 5)
- `--delete-originals`: Delete original files after successful conversion in watch mode
- `--clear-history`: Clear watch history file before starting watch mode

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

## Examples

Convert a single CBZ file with the "comic" preset:

```bash
cbxtools my_comic.cbz output/ --preset comic
```

Convert with custom quality and compression settings:

```bash
cbxtools my_comic.cbz output/ --quality 85 --method 6
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

Contributions welcome! See the [GitHub repository](https://github.com/username/cbxtools) for details.