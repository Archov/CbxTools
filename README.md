# CBXTools - Comic Book Archive to WebP Converter

A powerful tool for converting CBZ/CBR comic archives to WebP format, focusing on size reduction while maintaining quality. This tool preserves all non-image files, including metadata like ComicInfo.xml.

## Features

- Convert CBZ/CBR comic archives to WebP-based CBZ files
- Preserve metadata and all non-image files from the original archives
- Significantly reduce file sizes (typically 30-70%)
- Multi-threaded processing for fast conversion
- Customizable WebP compression parameters
- Support for presets to quickly apply optimized settings
- Directory watching mode to automatically process new files
- Detailed statistics tracking for optimization results
- Support for batch processing

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
- `--sharp-yuv`: Use sharp YUV conversion for better text quality
- `--no-sharp-yuv`: Disable sharp YUV conversion even if preset enables it
- `--preprocessing {none, unsharp_mask, reduce_noise}`: Apply preprocessing to images before compression
- `--zip-compression VALUE`: ZIP compression level for CBZ (0-9)
- `--lossless`: Use lossless WebP compression (larger but perfect quality)
- `--no-lossless`: Disable lossless compression even if preset enables it
- `--auto-optimize`: Try both lossy and lossless and use smaller file
- `--no-auto-optimize`: Disable auto-optimization even if preset enables it

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
- `comic`: Optimized for comic books with text and line art
- `photo`: Better quality for photorealistic images
- `maximum`: Maximum compression (lower quality)

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
cbxtools my_comic.cbz output/ --quality 85 --method 6 --sharp-yuv
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
