# CbxTools

A collection of tools for working with comic book archives (CBZ/CBR), including a WebP converter for reduced file size.

## Features

- Convert CBZ/CBR files to WebP format
- Preserve directory structure and file order
- Configurable compression quality
- Resize images to maximum dimensions
- Track statistics across multiple conversions
- Parallel processing for speed

## Installation

### From source

```bash
git clone https://github.com/yourusername/cbxtools.git
cd cbxtools
pip install -e .
```

## Usage

### Basic Usage

```bash
cbxtools /path/to/comics /path/to/output
```

### Options

```
cbxtools [options] input_path output_dir

positional arguments:
  input_path            Path to CBZ/CBR file or directory containing multiple archives
  output_dir            Output directory for WebP images

optional arguments:
  -h, --help            show this help message and exit
  --quality QUALITY     WebP compression quality (0-100, default: 80)
  --max-width MAX_WIDTH
                        Maximum width in pixels. 0 means no width restriction (default: 0)
  --max-height MAX_HEIGHT
                        Maximum height in pixels. 0 means no height restriction (default: 0)
  --no-cbz              Do not create a CBZ file with the WebP images (by default, CBZ is created)
  --keep-originals      Keep the extracted WebP files after creating the CBZ
  --recursive           Recursively search for CBZ/CBR files in subdirectories
  --threads THREADS     Number of parallel threads to use. 0 means auto-detect (default: 0)
  --verbose, -v         Enable verbose output
  --silent, -s          Suppress all output except errors
  --stats-file STATS_FILE
                        Path to stats file for lifetime statistics (default: ~/.cbx_stats.json)
  --no-stats            Do not update or display lifetime statistics
  --stats-only          Display lifetime statistics and exit
```

### Examples

Convert a single file:
```bash
cbxtools my_comic.cbz ./output --quality 85
```

Convert all comics in a directory:
```bash
cbxtools ./my_comics ./converted --recursive
```

Max resolution limit (useful for tablets/e-readers):
```bash
cbxtools ./my_comics ./converted --max-width 1920 --max-height 1080
```

View lifetime statistics:
```bash
cbxtools --stats-only
```

## Dependencies

- Python 3.6+
- Pillow
- rarfile
- patool
