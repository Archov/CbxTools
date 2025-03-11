# CBZ to WebP Converter - Installation and Usage

## Installation

1. Create a directory for the project:
   ```
   mkdir cbz_webp_converter
   cd cbz_webp_converter
   ```

2. Create the package structure as shown below:
   ```
   cbz_webp_converter/
   ├── __init__.py
   ├── cbz_webp_converter.py   
   ├── utils.py                
   ├── archive_utils.py        
   ├── conversion.py           
   └── stats.py                
   ```

3. Install dependencies:
   ```
   pip install pillow rarfile patool concurrent-log-handler
   ```

## Usage

You can run the script directly:

```
python cbz_webp_converter.py /path/to/comics /path/to/output --quality 80
```

### Command-line Options

- `input_path`: Path to CBZ/CBR file or directory containing multiple archives
- `output_dir`: Output directory for WebP images
- `--quality`: WebP compression quality (0-100, default: 80)
- `--max-width`: Maximum width in pixels. 0 means no width restriction (default: 0)
- `--max-height`: Maximum height in pixels. 0 means no height restriction (default: 0)
- `--no-cbz`: Do not create a CBZ file with the WebP images (by default, CBZ is created)
- `--keep-originals`: Keep the extracted WebP files after creating the CBZ
- `--recursive`: Recursively search for CBZ/CBR files in subdirectories
- `--threads`: Number of parallel threads to use. 0 means auto-detect (default: 0)
- `--verbose`, `-v`: Enable verbose output
- `--silent`, `-s`: Suppress all output except errors
- `--stats-file`: Path to stats file for lifetime statistics (default: ~/.cbz_webp_stats.json)
- `--no-stats`: Do not update or display lifetime statistics
- `--stats-only`: Display lifetime statistics and exit

### Example Commands

Convert a single file:
```
python cbz_webp_converter.py my_comic.cbz ./output --quality 85
```

Convert all comics in a directory:
```
python cbz_webp_converter.py ./my_comics ./converted --recursive
```

Max resolution limit (useful for tablets/e-readers):
```
python cbz_webp_converter.py ./my_comics ./converted --max-width 1920 --max-height 1080
```

View lifetime statistics:
```
python cbz_webp_converter.py --stats-only
```
